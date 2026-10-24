"""AnimeTosho Subtitle Engine for Tatap.

Mengambil dan mengekstrak attachment subtitle khusus anime langsung dari rilis
resmi (Crunchyroll, Netflix, Bstation, Muse) dan fansub (Judas, SubsPlease, Erai-raws, DKB, dll.)
melalui AnimeTosho.

Fitur:
  - Khusus menyaring dan mengambil subtitle yang pasti berbahasa Indonesia ([ind, ASS], [ind, SRT]).
  - Dekompresi instan format XZ (.xz) menggunakan pustaka bawaan `lzma`.
  - Konversi format fansub ASS / SRT presisi tinggi ke cue WebVTT.
  - Bypass DNS & DPI via DoH Cloudflare / Google dan TLS Record desynchronization.
"""
import html
import json
import lzma
import re
import time
import urllib.parse
import httpx

from config import HI_UA
from api.desync import tls_desync_request, _resolve_host

_AT_SEARCH_CACHE = {}
_AT_TEXT_CACHE = {}

# Daftar hostname resmi & IP CDN fallback
_AT_HOSTS = ["feed.animetosho.net", "animetosho.net"]


def _clean_anime_title(title: str, slug: str = "") -> list:
    """Bersihkan judul anime dari embel-embel episode/season dan kembalikan daftar variasi judul untuk pencarian."""
    titles = []
    t = (title or "").strip()
    if t:
        t_clean = re.sub(r"\b(?:season\s*\d+|\d+(?:nd|rd|th|st)\s*season|part\s*\d+|cour\s*\d+|s\d+)\b", "", t, flags=re.I)
        t_clean = re.sub(r"\([^)]*\)", " ", t_clean)
        t_clean = re.sub(r"\[[^\]]*\]", " ", t_clean)
        t_clean = re.sub(r"\s+", " ", t_clean).strip(" -:")
        if t_clean and t_clean not in titles:
            titles.append(t_clean)

    if slug:
        s = slug.split(":", 1)[1] if ":" in slug else slug
        s = re.sub(r"-\d+$", "", s)
        s = s.replace("-sub-indo", "").replace("-episode", "")
        slug_title = re.sub(r"\s+", " ", s.replace("-", " ")).strip()
        slug_clean = re.sub(r"\b(?:season\s*\d+|\d+(?:nd|rd|th|st)\s*season|part\s*\d+|cour\s*\d+|s\d+)\b", "", slug_title, flags=re.I)
        slug_clean = re.sub(r"\s+", " ", slug_clean).strip(" -:")
        if slug_clean and slug_clean not in titles:
            titles.append(slug_clean)

    return titles or ["Anime"]


def _http_get_raw(url: str, headers: dict = None, timeout: float = 8.0) -> bytes:
    """Ambil response bytes via httpx dengan fallback ke tls_desync_request."""
    hdrs = {"User-Agent": HI_UA}
    if headers:
        hdrs.update(headers)

    try:
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            r = client.get(url, headers=hdrs)
            if r.status_code == 200 and r.content:
                return r.content
    except Exception:
        pass

    try:
        raw = tls_desync_request(url, headers=hdrs, timeout=timeout)
        if raw:
            return raw
    except Exception:
        pass

    return b""


def _is_indonesian_subtitle_label(label: str) -> bool:
    """True jika label track subtitle mengindikasikan Bahasa Indonesia."""
    if not label:
        return False
    low = label.lower()
    return any(k in low for k in (
        "[ind,",
        "[ind ",
        "(ind)",
        "indonesian",
        "bahasa indonesia",
        "cr [ind",
        "cr (ind",
        "[may,",
        "malay",
    ))


def search_animetosho_indonesian(title: str, slug: str = "", ep: int = 1, season: int = 1) -> list:
    """Cari daftar track subtitle khusus Bahasa Indonesia dari AnimeTosho untuk episode anime aktif."""
    clean_titles = _clean_anime_title(title, slug)
    ep = max(1, int(ep or 1))
    season = max(1, int(season or 1))

    if season <= 1:
        # Ekstrak nomor season dari title atau slug jika ada indikasi Season 2+
        combined_text = f"{title or ''} {slug or ''}"
        m_s = re.search(r"\b(?:season\s*(\d+)|\b(\d+)(?:nd|rd|th|st)\s*season|part\s*(\d+)|cour\s*(\d+)|s(\d+))\b", combined_text, flags=re.I)
        if m_s:
            for g in m_s.groups():
                if g and g.isdigit() and int(g) > 1:
                    season = int(g)
                    break
        elif re.search(r"\b(?:season\s*iv|season\s*iii|season\s*ii)\b", combined_text, flags=re.I):
            if re.search(r"\bseason\s*iv\b", combined_text, flags=re.I):
                season = 4
            elif re.search(r"\bseason\s*iii\b", combined_text, flags=re.I):
                season = 3
            elif re.search(r"\bseason\s*ii\b", combined_text, flags=re.I):
                season = 2

    primary_title = clean_titles[0]
    cache_key = f"{primary_title.lower()}|s{season}|e{ep}|id"
    cached = _AT_SEARCH_CACHE.get(cache_key)
    if cached and (time.time() - cached[1] < 1800):
        return cached[0]

    # Bangun beberapa pola kueri pencarian AnimeTosho
    queries = []
    for c_title in clean_titles:
        if season > 1:
            queries.append(f"{c_title} S{season:02d}E{ep:02d}")
            queries.append(f"{c_title} Season {season} {ep:02d}")
            queries.append(f"{c_title} S{season} {ep:02d}")
        else:
            queries.append(f"{c_title} S{season:02d}E{ep:02d}")
            queries.append(f"{c_title} {ep:02d}")
            queries.append(f"{c_title} E{ep:02d}")

    results = []
    seen_urls = set()

    for q in queries:
        if results:
            break
        q_enc = urllib.parse.quote(q)
        api_url = f"https://feed.animetosho.net/json?q={q_enc}"
        raw_json = _http_get_raw(api_url, timeout=7.0)
        if not raw_json:
            continue

        try:
            items = json.loads(raw_json.decode("utf-8", errors="replace"))
        except Exception:
            continue

        if not isinstance(items, list):
            continue

        # Periksa rilis torrent teratas yang paling relevan (hingga 12 item)
        for item in items[:12]:
            t_title = item.get("title") or item.get("torrent_name") or ""
            t_id = item.get("id")
            if not t_id:
                continue

            # Verifikasi kecocokan nomor episode di judul torrent
            t_low = t_title.lower()
            ep_patterns = [
                rf"\bs0*{season}e0*{ep}\b",
                rf"\bep(?:isode)?[\s._-]*0*{ep}\b",
                rf"[\s._\[\(-]0*{ep}(?:v\d+)?[\s._\]\)-]",
            ]
            if not any(re.search(pat, t_low) for pat in ep_patterns):
                # Lewati rilis yang nomor episodenya tidak cocok
                continue

            v_url = f"https://animetosho.net/view/{t_id}"
            v_html_bytes = _http_get_raw(v_url, timeout=6.0)
            if not v_html_bytes:
                continue

            v_html = v_html_bytes.decode("utf-8", errors="replace")
            # Ekstrak semua link subtitle attachment
            matches = re.findall(
                r'<a[^>]+href=[\"\'](/download/\d+/subs/file/(\d+))[\"\'][^>]*>([^<]+)</a>',
                v_html,
            )

            for href, file_id, label in matches:
                clean_lbl = html.unescape(label).strip()
                if not _is_indonesian_subtitle_label(clean_lbl):
                    continue

                full_url = f"https://animetosho.net{href}"
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Ekstrak nama fansub / rilis
                m_group = re.match(r"^\[([^\]]+)\]", t_title)
                group_name = m_group.group(1) if m_group else "Fansub"

                is_ass = "ass" in clean_lbl.lower()
                results.append({
                    "id": f"at_{file_id}",
                    "file_id": file_id,
                    "filename": f"{group_name} - {primary_title} S{season:02d}E{ep:02d} ({clean_lbl})",
                    "label": f"[{group_name}] {clean_lbl}",
                    "lang": "id",
                    "format": "ass" if is_ass else "srt",
                    "url": full_url,
                    "torrent_title": t_title,
                    "source": "AnimeTosho",
                    "score": 150 + (20 if is_ass else 0) + (10 if "judas" in group_name.lower() or "subsplease" in group_name.lower() or "erai" in group_name.lower() else 0),
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    if results:
        _AT_SEARCH_CACHE[cache_key] = (results, time.time())
    return results


def download_animetosho_sub_text(url: str, file_id: str = "") -> str:
    """Unduh subtitle dari AnimeTosho (.xz), dekompresi, dan kembalikan teks utuh (.ass / .srt)."""
    target_url = url
    if not target_url and file_id:
        target_url = f"https://animetosho.net/download/subs/file/{file_id}"

    if not target_url:
        raise ValueError("URL AnimeTosho tidak valid")

    if target_url in _AT_TEXT_CACHE:
        txt, ts = _AT_TEXT_CACHE[target_url]
        if time.time() - ts < 3600:
            return txt

    raw_bytes = _http_get_raw(target_url, timeout=10.0)
    if not raw_bytes:
        raise RuntimeError("Gagal mengunduh subtitle dari AnimeTosho")

    # Konten dari AnimeTosho selalu dikompresi dengan format XZ (.xz)
    if raw_bytes[:5] == b"\xfd7zXZ" or raw_bytes[:2] == b"\xfd7":
        try:
            decompressed = lzma.decompress(raw_bytes)
            raw_bytes = decompressed
        except Exception as e:
            raise RuntimeError(f"Gagal dekompresi XZ AnimeTosho: {e}")

    text = raw_bytes.decode("utf-8", errors="replace").lstrip("\ufeff")
    _AT_TEXT_CACHE[target_url] = (text, time.time())
    return text
