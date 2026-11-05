"""OpenSubtitles Public API & Scraper Engine for Tatap.

Menggabungkan 3 metode pengambilan subtitle dari OpenSubtitles tanpa wajib API key:
  1. Public API v3 (opensubtitles-v3.strem.io) dengan resolusi IMDb ID otomatis
  2. Official Legacy Public REST API (rest.opensubtitles.org via DoH + TLS Desync)
  3. HTML/XML Web Scraper fallback (www.opensubtitles.org & dl.opensubtitles.org)

Dilengkapi pembersih watermark/iklan OpenSubtitles dan sistem scoring rilisan anime.
"""
import gzip
import html
import json
import re
import time
import urllib.parse
import httpx

from config import HI_UA
from api.desync import tls_desync_request

# Cache in-memory untuk resolusi IMDb ID & hasil pencarian OpenSubtitles
_IMDB_CACHE = {}
_OS_SEARCH_CACHE = {}
_OS_TEXT_CACHE = {}

_LANG_TO_ISO639_2 = {
    "id": "ind",
    "ind": "ind",
    "en": "eng",
    "eng": "eng",
    "ja": "jpn",
    "jpn": "jpn",
    "es": "spa",
    "fr": "fre",
    "de": "ger",
    "pt": "por",
    "ko": "kor",
    "zh": "chi",
    "ar": "ara",
    "ru": "rus",
}

_ISO639_2_TO_LANG = {
    "ind": "id",
    "id": "id",
    "may": "ms",
    "msa": "ms",
    "ms": "ms",
    "eng": "en",
    "en": "en",
    "jpn": "ja",
    "ja": "ja",
    "spa": "es",
    "fre": "fr",
    "ger": "de",
    "por": "pt",
    "pob": "pt",
    "kor": "ko",
    "chi": "zh",
    "zho": "zh",
    "zht": "zh",
}

# Daftar pola iklan/watermark bawaan OpenSubtitles yang wajib dihapus
_OS_AD_PATTERNS = [
    re.compile(r"iklankan\s+produk\s+atau\s+merek\s+dagang", re.I),
    re.compile(r"advertise\s+your\s+product\s+or\s+brand", re.I),
    re.compile(r"support\s+us\s+and\s+become\s+vip\s+member", re.I),
    re.compile(r"become\s+vip\s+member\s+to\s+remove\s+all\s+ads", re.I),
    re.compile(r"opensubtitles\.org", re.I),
    re.compile(r"opensubtitles\.com", re.I),
    re.compile(r"osdb\.link", re.I),
    re.compile(r"americascardroom", re.I),
    re.compile(r"subtitles?\s+downloaded\s+from\s+opensubtitles", re.I),
]


def is_opensubtitles_ad_text(text: str) -> bool:
    """True jika teks cue merupakan sisipan iklan atau watermark OpenSubtitles."""
    if not text:
        return False
    clean = text.strip()
    for pat in _OS_AD_PATTERNS:
        if pat.search(clean):
            return True
    return False


def strip_opensubtitles_ads(cues: list) -> list:
    """Bersihkan daftar cue dari sisipan iklan/watermark OpenSubtitles dan karakter bidi tersembunyi."""
    if not cues:
        return []
    cleaned = []
    for c in cues:
        txt = (c.get("text") or "").strip()
        # Hapus karakter directional formatting Unicode (U+202A..U+202E, U+200E, U+200F, BOM)
        txt = re.sub(r"[\u200b-\u200f\u202a-\u202e\ufeff]", "", txt).strip()
        if not txt or is_opensubtitles_ad_text(txt):
            continue
        lines = [ln.strip() for ln in txt.split("\n") if ln.strip() and not is_opensubtitles_ad_text(ln)]
        if not lines:
            continue
        cleaned.append({
            "start": float(c["start"]),
            "end": float(c["end"]),
            "text": "\n".join(lines),
        })
    return cleaned


def clean_title_And_season(raw_title: str, slug: str = "") -> tuple:
    """Ekstrak (clean_base_title, season_num) dari judul anime atau slug HiAnime/Otakudesu."""
    source = (raw_title or "").strip()
    if not source and slug:
        s = slug.split(":", 1)[1] if ":" in slug else slug
        s = re.sub(r"-\d+$", "", s)
        s = s.replace("-sub-indo", "").replace("-episode", "")
        source = s.replace("-", " ").strip()

    season_num = 1
    m_s = re.search(
        r"\b(?:season\s*(\d+)|(\d+)(?:nd|rd|th|st)\s*season|part\s*(\d+)|s(\d+))\b",
        source,
        flags=re.I,
    )
    if m_s:
        for g in m_s.groups():
            if g and g.isdigit():
                season_num = max(1, int(g))
                break
    else:
        m_rom = re.search(r"\b(ii|iii|iv|v|vi)\b", source.lower())
        if m_rom:
            season_num = {"ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6}[m_rom.group(1)]

    base_title = re.sub(
        r"\b(?:season\s*\d+|\d+(?:nd|rd|th|st)\s*season|part\s*\d+|cour\s*\d+|s\d+)\b",
        "",
        source,
        flags=re.I,
    )
    base_title = re.sub(r"\([^)]*\)", " ", base_title)
    base_title = re.sub(r"\s+", " ", base_title).strip(" -:")
    return (base_title or source or "Anime", season_num)


def clean_anime_title_variations(raw_title: str, slug: str = "") -> list:
    """Bangun daftar variasi judul anime untuk pencarian multi-tier (lengkap, utama tanpa sub-arc, dan slug)."""
    titles = []

    def add(cand):
        c = re.sub(r"\s+", " ", (cand or "")).strip(" -:;,._")
        if c and len(c) > 1 and c.lower() not in [x.lower() for x in titles]:
            titles.append(c)

    t = (raw_title or "").strip()
    if t:
        add(t)
        t_nosub = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", " ", t)
        t_nosub = re.sub(r"\b(?:season\s*\d+|\d+(?:nd|rd|th|st)\s*season|part\s*\d+|cour\s*\d+|s\d+|ii|iii|iv|v|vi)\b", "", t_nosub, flags=re.I)
        add(t_nosub)
        for sep in [":", " - ", " – "]:
            if sep in t:
                left = t.split(sep)[0]
                left_clean = re.sub(r"\b(?:season\s*\d+|\d+(?:nd|rd|th|st)\s*season|part\s*\d+|cour\s*\d+|s\d+|ii|iii|iv|v|vi)\b", "", left, flags=re.I)
                add(left_clean)

    if slug:
        s = slug.split(":", 1)[1] if ":" in slug else slug
        s = re.sub(r"-\d+$", "", s)
        s = s.replace("-sub-indo", "").replace("-episode", "")
        slug_title = s.replace("-", " ")
        add(slug_title)
        slug_clean = re.sub(r"\b(?:season\s*\d+|\d+(?:nd|rd|th|st)\s*season|part\s*\d+|cour\s*\d+|s\d+|ii|iii|iv|v|vi)\b", "", slug_title, flags=re.I)
        add(slug_clean)
        for sep in [":", " - ", " – "]:
            if sep in slug_title:
                add(slug_title.split(sep)[0])

    return titles or ["Anime"]


def _extract_file_season_num(filename: str) -> int:
    """Ekstrak nomor season eksplisit dari nama file/rilis subtitle (return 0 jika tidak ada tanda season)."""
    fn_low = (filename or "").lower()
    m_s = re.search(r"\bs0*(\d+)e\d+\b", fn_low)
    if m_s:
        try:
            return int(m_s.group(1))
        except ValueError:
            pass
    m_season = re.search(r"\b(?:season\s*(\d+)|(\d+)(?:nd|rd|th|st)\s*season|s(\d+))\b", fn_low)
    if m_season:
        for g in m_season.groups():
            if g:
                try:
                    return int(g)
                except ValueError:
                    pass
    m_roman = re.search(r"\b(ii|iii|iv|v|vi)\b", fn_low)
    if m_roman:
        return {"ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6}[m_roman.group(1)]
    return 0


def _extract_file_episode_num(filename: str) -> int:
    """Ekstrak nomor episode sebenarnya dari nama file subtitle (return -1 jika tidak terdeteksi)."""
    fn_low = (filename or "").lower()
    m_se = re.search(r"\bs\d+e0*(\d+)\b", fn_low)
    if m_se:
        try:
            return int(m_se.group(1))
        except ValueError:
            pass
    m_ep = re.search(r"\bep(?:isode)?[\s._-]*0*(\d+)\b", fn_low)
    if m_ep:
        try:
            return int(m_ep.group(1))
        except ValueError:
            pass
    m_del = re.search(r"[\s._\[\(-]0*(\d+)(?:v\d+)?[\s._\]\)-]", fn_low)
    if m_del:
        try:
            return int(m_del.group(1))
        except ValueError:
            pass
    return -1


def _http_get_bytes(url: str, headers: dict = None, timeout: float = 9.0, prefer_desync: bool = False) -> bytes:
    """Ambil response bytes via httpx atau fallback ke tls_desync_request (DoH + DPI Bypass)."""
    hdrs = {"User-Agent": HI_UA}
    if headers:
        hdrs.update(headers)

    if prefer_desync:
        try:
            raw = tls_desync_request(url, headers=hdrs, timeout=timeout)
            if raw:
                return raw
        except Exception:
            pass

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            r = client.get(url, headers=hdrs)
            if r.status_code == 200 and r.content:
                return r.content
    except Exception:
        pass

    return tls_desync_request(url, headers=hdrs, timeout=timeout)


def _norm_tokens(s: str) -> set:
    s = re.sub(r"[^a-zA-Z0-9\s]", " ", (s or "").lower())
    stop = {
        "the", "a", "an", "wa", "ga", "ni", "to", "of", "in", "on", "animation",
        "tv", "series", "episode", "ep", "season", "sub", "indo", "indonesia",
        "subtitle", "srt", "ass", "vtt", "1080p", "720p", "webrip", "webdl", "bdrip",
    }
    return {t for t in s.split() if len(t) > 1 and t not in stop}


def _title_similarity(query_title: str, candidate_title: str) -> float:
    ta = _norm_tokens(query_title)
    tb = _norm_tokens(candidate_title)
    if not ta or not tb:
        return 0.0
    inter = ta.intersection(tb)
    if not inter:
        return 0.0
    cov = len(inter) / len(ta)
    jaccard = len(inter) / len(ta.union(tb))
    # Jika query pendek (<= 2 token seperti 'No Game', 'Solo Leveling')
    if len(ta) <= 2:
        # Semua token query wajib hadir (coverage 100%) dan jaccard minimal 0.28
        # untuk mencegah false positive pada spinoff atau franchise yang beda judul
        if cov >= 0.99 and (jaccard >= 0.28 or len(tb) <= len(ta) + 2):
            return cov
        return 0.0
    # Jika query panjang, butuh coverage >= 70% dan jaccard >= 0.20
    if cov >= 0.70 and jaccard >= 0.20:
        return cov
    return 0.0


def is_accurate_sub_title_match(anime_title: str, candidate_title: str, target_season: int = 1, target_ep: int = 0) -> bool:
    """True jika judul file/rilis subtitle cocok dengan judul anime yang dicari (termasuk verifikasi season, episode, dan batas franchise)."""
    if not anime_title or not candidate_title:
        return False

    cand_low = candidate_title.lower()
    anime_low = anime_title.lower()

    # 1. Cek pemisahan franchise / spinoff yang kerap salah tertaut (misal Naruto vs Boruto)
    offshoot_pairs = [
        ("naruto", "boruto"),
        ("inuyasha", "yashahime"),
        ("bleach", "burn the witch"),
    ]
    for parent, spinoff in offshoot_pairs:
        if parent in anime_low and spinoff not in anime_low and spinoff in cand_low:
            return False
        if spinoff in anime_low and parent not in anime_low and parent in cand_low and spinoff not in cand_low:
            return False

    # 2. Verifikasi kesamaan token judul di seluruh variasi judul anime
    variations = clean_anime_title_variations(anime_title)
    best_sim = 0.0
    for v in variations:
        sim = _title_similarity(v, candidate_title)
        if sim > best_sim:
            best_sim = sim
    if best_sim < 0.60:
        return False

    # 3. Verifikasi nomor season jika terdeteksi di candidate
    target_s = max(1, int(target_season or 1))
    cand_season = _extract_file_season_num(candidate_title)
    if cand_season > 0 and cand_season != target_s:
        return False

    # 4. Verifikasi nomor episode jika target_ep > 0 dan terdeteksi di candidate
    if target_ep > 0:
        cand_ep = _extract_file_episode_num(candidate_title)
        if cand_ep > 0 and cand_ep != int(target_ep):
            return False

    return True


def resolve_imdb_id(title: str, slug: str = "") -> tuple:
    """Resolusi judul anime / slug ke (imdb_id 'ttXXXXXXX', season_num) via Cinemeta & IMDb Suggestion API."""
    base_title, season_num = clean_title_And_season(title, slug)
    cache_key = base_title.lower().strip()
    if not cache_key:
        return ("", season_num)

    cached = _IMDB_CACHE.get(cache_key)
    if cached and (time.time() - cached[1] < 86400):
        return (cached[0], season_num)

    q_enc = urllib.parse.quote(base_title)

    # 1. Coba via Cinemeta Public Catalog API
    try:
        u_cin = f"https://v3-cinemeta.strem.io/catalog/series/top/search={q_enc}.json"
        raw = _http_get_bytes(u_cin, timeout=7.0)
        data = json.loads(raw.decode("utf-8", errors="replace"))
        for m in (data.get("metas") or [])[:6]:
            cand_id = (m.get("imdb_id") or m.get("id") or "").strip()
            cand_name = (m.get("name") or "").strip()
            if cand_id.startswith("tt") and _title_similarity(base_title, cand_name) >= 0.5:
                _IMDB_CACHE[cache_key] = (cand_id, time.time())
                return (cand_id, season_num)
    except Exception:
        pass

    # 2. Coba via IMDb Public Suggestion JSON Scraper
    try:
        first_ch = re.sub(r"[^a-z0-9]", "", base_title.lower())[:1] or "a"
        u_imdb = f"https://v3.sg.media-imdb.com/suggestion/{first_ch}/{q_enc}.json"
        raw = _http_get_bytes(u_imdb, timeout=7.0)
        data = json.loads(raw.decode("utf-8", errors="replace"))
        for item in (data.get("d") or [])[:8]:
            cand_id = (item.get("id") or "").strip()
            cand_name = (item.get("l") or "").strip()
            q_type = (item.get("q") or "").lower()
            if not cand_id.startswith("tt"):
                continue
            if "video game" in q_type:
                continue
            if _title_similarity(base_title, cand_name) >= 0.5:
                _IMDB_CACHE[cache_key] = (cand_id, time.time())
                return (cand_id, season_num)
    except Exception:
        pass

    return ("", season_num)


def _score_subtitle_candidate(filename: str, ep: int, season: int, target_lang: str, cand_lang: str, downloads: int = 0) -> int:
    """Beri skor relevansi untuk mengurutkan rilis subtitle OpenSubtitles terbaik."""
    fn_low = (filename or "").lower()
    target_s = max(1, int(season or 1))
    target_e = max(1, int(ep or 1))

    # Eliminasi mutlak jika season atau episode terdeteksi tapi tidak cocok
    cand_season = _extract_file_season_num(fn_low)
    if cand_season > 0 and cand_season != target_s:
        return -999

    cand_ep = _extract_file_episode_num(fn_low)
    if cand_ep > 0 and cand_ep != target_e:
        return -999

    # Eliminasi mutlak jika mencari Bahasa Indonesia namun rilisan berbahasa Melayu
    if target_lang == "id":
        if cand_lang in ("ms", "may", "msa") or any(m in fn_low for m in ("[may", "(may", "malay", "bahasa melayu")):
            return -999

    score = 50
    if cand_lang == target_lang:
        score += 100
    elif cand_lang == "en":
        score += 30

    if cand_season == target_s:
        score += 30
    if cand_ep == target_e:
        score += 50

    # Bonus grup rilis anime / webrip resmi yang timingnya rapi
    trusted_tags = ("nf", "netflix", "cr", "crunchyroll", "webrip", "web-dl", "bstation", "muse", "judas", "subsplease", "erai", "asw")
    for tag in trusted_tags:
        if tag in fn_low:
            score += 15

    score += min(30, int(downloads // 100))
    return score


def search_opensubtitles(title: str = "", slug: str = "", ep: int = 1, season: int = 0, lang: str = "id", imdb_id: str = "") -> list:
    """Cari daftar subtitle dari OpenSubtitles menggunakan kombinasi Public API (Stremio v3 + REST API) & Scraping."""
    ep = max(1, int(ep or 1))
    target_lang = (lang or "id").lower()
    if target_lang not in ("id", "en", "ja", "es", "fr", "de", "pt", "ko", "zh"):
        target_lang = "id"

    base_title, inferred_season = clean_title_And_season(title, slug)
    season_num = int(season) if int(season or 0) > 0 else inferred_season
    if not imdb_id:
        imdb_id, _ = resolve_imdb_id(base_title, slug)

    cache_key = f"{imdb_id}|{base_title.lower()}|s{season_num}|e{ep}|{target_lang}"
    cached = _OS_SEARCH_CACHE.get(cache_key)
    if cached and (time.time() - cached[1] < 1800):
        return cached[0]

    candidates_by_id = {}

    def _add_candidate(file_id: str, filename: str, raw_lang: str, dl_url: str, backup_url: str = "", downloads: int = 0, rating: float = 0.0, tier_name: str = "public_api", meta_title: str = ""):
        fid = str(file_id or "").strip()
        if not fid or not dl_url:
            return
        norm_lang = _ISO639_2_TO_LANG.get((raw_lang or "").lower(), (raw_lang or "").lower()[:2])
        if norm_lang != target_lang:
            return
        fname = (filename or f"OpenSubtitles_{fid}.srt").strip()

        # Validasi ketat kecocokan judul anime, season, dan episode jika base_title tersedia
        if base_title:
            combined_cand = f"{fname} {meta_title or ''}".strip()
            if not is_accurate_sub_title_match(base_title, combined_cand, target_season=season_num, target_ep=ep):
                return

        sc = _score_subtitle_candidate(fname, ep, season_num, target_lang, norm_lang, downloads)
        if sc < 0:
            return
        existing = candidates_by_id.get(fid)
        if not existing or sc > existing["score"]:
            candidates_by_id[fid] = {
                "id": fid,
                "file_id": fid,
                "filename": fname,
                "lang": norm_lang,
                "lang_iso": _LANG_TO_ISO639_2.get(norm_lang, raw_lang),
                "url": dl_url,
                "backup_url": backup_url or f"https://dl.opensubtitles.org/en/download/subencoding-utf8/file/{fid}",
                "downloads": int(downloads or 0),
                "rating": float(rating or 0.0),
                "source_tier": tier_name,
                "score": sc,
            }

    # =========================================================================
    # TIER 1: OpenSubtitles v3 Public API (opensubtitles-v3.strem.io)
    # =========================================================================
    if imdb_id and imdb_id.startswith("tt"):
        seasons_to_try = [season_num] if season_num == 1 else [season_num, 1]
        for s_try in seasons_to_try:
            try:
                u_v3 = f"https://opensubtitles-v3.strem.io/subtitles/series/{imdb_id}:{s_try}:{ep}.json"
                raw = _http_get_bytes(u_v3, timeout=8.0, prefer_desync=True)
                data = json.loads(raw.decode("utf-8", errors="replace"))
                for sub in (data.get("subtitles") or []):
                    raw_l = (sub.get("lang") or "").lower()
                    dl_u = (sub.get("url") or "").strip()
                    m_fid = re.search(r"/file/(\d+)", dl_u)
                    fid = m_fid.group(1) if m_fid else str(sub.get("id") or "")
                    fname = sub.get("subtitleFileName") or sub.get("movieReleaseName") or f"OpenSubtitles_{ s_try }x{ ep }_{ fid }.srt"
                    meta_name = sub.get("movieReleaseName") or sub.get("title") or ""
                    _add_candidate(
                        file_id=fid,
                        filename=fname,
                        raw_lang=raw_l,
                        dl_url=f"https://dl.opensubtitles.org/en/download/subencoding-utf8/file/{fid}" if fid.isdigit() else dl_u,
                        backup_url=dl_u,
                        downloads=int(sub.get("g") or 0),
                        tier_name="os_v3_api",
                        meta_title=meta_name,
                    )
            except Exception:
                pass

    # =========================================================================
    # TIER 2: Official Legacy REST Public API (rest.opensubtitles.org)
    # =========================================================================
    iso_langs = [_LANG_TO_ISO639_2.get(target_lang, "ind")]
    if target_lang != "id" and "eng" not in iso_langs:
        iso_langs.append("eng")

    num_imdb = imdb_id[2:] if imdb_id.startswith("tt") else ""
    for iso_l in iso_langs:
        # Jika kandidat bahasa target sudah cukup banyak dari Tier 1, hemat waktu request
        if iso_l == "eng" and any(c["lang"] == target_lang for c in candidates_by_id.values()):
            continue

        rest_urls = []
        if num_imdb:
            rest_urls.append(
                f"https://rest.opensubtitles.org/search/episode-{ep}/imdbid-{num_imdb}/season-{season_num}/sublanguageid-{iso_l}"
            )
        if base_title:
            for t_var in clean_anime_title_variations(base_title, slug)[:2]:
                q_slug = urllib.parse.quote(t_var.lower())
                rest_urls.append(
                    f"https://rest.opensubtitles.org/search/episode-{ep}/query-{q_slug}/season-{season_num}/sublanguageid-{iso_l}"
                )

        for u_rest in rest_urls:
            try:
                raw = _http_get_bytes(
                    u_rest,
                    headers={"User-Agent": "TemporaryUserAgent"},
                    timeout=8.0,
                    prefer_desync=True,
                )
                txt = raw.decode("utf-8", errors="replace").strip()
                if not txt.startswith("["):
                    continue
                items = json.loads(txt)
                for it in items[:25]:
                    fid = str(it.get("IDSubtitleFile") or "").strip()
                    fname = (it.get("SubFileName") or it.get("MovieReleaseName") or "").strip()
                    meta_name = (it.get("MovieName") or it.get("MovieReleaseName") or "").strip()
                    dl_cnt = 0
                    try:
                        dl_cnt = int(it.get("SubDownloadsCnt") or 0)
                    except ValueError:
                        pass
                    rating = 0.0
                    try:
                        rating = float(it.get("SubRating") or 0.0)
                    except ValueError:
                        pass
                    gz_link = (it.get("SubDownloadLink") or "").strip()
                    _add_candidate(
                        file_id=fid,
                        filename=fname,
                        raw_lang=it.get("SubLanguageID") or iso_l,
                        dl_url=f"https://dl.opensubtitles.org/en/download/subencoding-utf8/file/{fid}",
                        backup_url= f"https://subs5.strem.io/en/download/subencoding-stremio-utf8/src-api/file/{fid}" if fid else gz_link,
                        downloads=dl_cnt,
                        rating=rating,
                        tier_name="os_rest_api",
                        meta_title=meta_name,
                    )
                if any(c["lang"] == target_lang for c in candidates_by_id.values()):
                    break
            except Exception:
                pass

    # =========================================================================
    # TIER 3: HTML / XML Web Scraping Fallback (www.opensubtitles.org)
    # =========================================================================
    if not candidates_by_id and num_imdb:
        try:
            iso_l = _LANG_TO_ISO639_2.get(target_lang, "ind")
            u_scrape = f"https://www.opensubtitles.org/en/search/sublanguageid-{iso_l}/imdbid-{num_imdb}/season-{season_num}/episode-{ep}"
            raw_html = _http_get_bytes(u_scrape, timeout=8.0, prefer_desync=True).decode("utf-8", errors="replace")
            for m in re.finditer(r"/en/subtitleserve/sub/(\d+)", raw_html):
                sub_id = m.group(1)
                _add_candidate(
                    file_id=sub_id,
                    filename=f"{base_title} S{season_num:02d}E{ep:02d} ({iso_l.upper()} #{sub_id}).srt",
                    raw_lang=iso_l,
                    dl_url=f"https://dl.opensubtitles.org/en/download/sub/{sub_id}",
                    backup_url=f"https://www.opensubtitles.org/en/subtitleserve/sub/{sub_id}",
                    tier_name="os_html_scraper",
                )
        except Exception:
            pass

    results = sorted(
        candidates_by_id.values(),
        key=lambda x: (1 if x["lang"] == target_lang else 0, x["score"], x["downloads"]),
        reverse=True,
    )
    if results:
        _OS_SEARCH_CACHE[cache_key] = (results, time.time())
    return results


def _looks_like_subtitle(text: str) -> bool:
    if not text:
        return False
    t = text.strip()
    low = t.lower()
    if "<html" in low or "<!doctype" in low or "<body" in low:
        return False
    return ("-->" in t) or ("dialogue:" in low) or ("webvtt" in low)


def download_opensubtitle_text(file_id: str = "", url: str = "", backup_url: str = "") -> str:
    """Unduh isi teks subtitle (.srt / .vtt / .ass) dari OpenSubtitles dengan multi-endpoint failover."""
    fid = str(file_id or "").strip()
    cache_key = fid or url or backup_url
    if cache_key and cache_key in _OS_TEXT_CACHE:
        cached_txt, ts = _OS_TEXT_CACHE[cache_key]
        if time.time() - ts < 3600:
            return cached_txt

    urls_to_try = []
    if fid and fid.isdigit():
        urls_to_try.append(f"https://dl.opensubtitles.org/en/download/subencoding-utf8/file/{fid}")
        urls_to_try.append(f"https://subs5.strem.io/en/download/subencoding-stremio-utf8/src-api/file/{fid}")
    if url and url not in urls_to_try:
        urls_to_try.append(url)
    if backup_url and backup_url not in urls_to_try:
        urls_to_try.append(backup_url)

    for target_u in urls_to_try:
        if not target_u:
            continue
        try:
            hdrs = {"User-Agent": "TemporaryUserAgent" if "opensubtitles.org" in target_u else HI_UA}
            raw = _http_get_bytes(target_u, headers=hdrs, timeout=10.0, prefer_desync=True)
            if not raw:
                continue
            if raw[:2] == b"\x1f\x8b":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            txt = raw.decode("utf-8", errors="replace").lstrip("\ufeff")
            txt = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", txt)
            if _looks_like_subtitle(txt):
                if cache_key:
                    _OS_TEXT_CACHE[cache_key] = (txt, time.time())
                return txt
        except Exception:
            continue

    raise RuntimeError("Gagal mengunduh file subtitle dari OpenSubtitles")
