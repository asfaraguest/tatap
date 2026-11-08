"""Modul Scraper & Stream Resolver AniChan (https://anichan.to/).
Menyelesaikan stream master HLS M3U8 langsung (zero iframe/embed),
mendekripsi payload AES-GCM server, dan menyediakan subtitle WEBVTT serta AniSkip skip times.
"""

import os
import re
import json
import base64
import hmac
import hashlib
import time
import urllib.parse
from typing import Optional, Tuple, List, Dict, Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import httpx

from config import HI_UA

ANICHAN_BASE = "https://anichan.to"

# Kunci statis bawaan bundle Next.js anichan.to
STATIC_K = "f7312859"
STATIC_O = "dF+YyX8ksuoyznJHUVeHE1yRdVJVwZM4/FEnWRi2Wbg="
STATIC_B = "Mh83TJtN3J8ZDnKT35ASzU31AL5zurEGSAsX9scP4Lk="

_crypto_keys = {
    "k": STATIC_K,
    "O": STATIC_O,
    "b": STATIC_B,
}

_session_cache = {
    "token_n": "",
    "cookies": {},
    "exp": 0,
}

_shared_anichan_client: Optional[httpx.Client] = None
_SLUG_ID_CACHE: Dict[str, int] = {}


def _get_client() -> httpx.Client:
    global _shared_anichan_client
    if _shared_anichan_client is None:
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=60.0)
        _shared_anichan_client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(12.0, connect=5.0),
            limits=limits,
            headers={
                "User-Agent": HI_UA,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
                "Referer": f"{ANICHAN_BASE}/",
                "Origin": ANICHAN_BASE,
            },
        )
    return _shared_anichan_client


def close_anichan_client():
    global _shared_anichan_client
    if _shared_anichan_client is not None:
        try:
            _shared_anichan_client.close()
        except Exception:
            pass
        _shared_anichan_client = None


def _refresh_keys_from_web() -> Tuple[str, str, str]:
    """Ekstraksi dinamis kunci dekripsi jika kunci statis mengalami rotasi."""
    global _crypto_keys
    try:
        c = _get_client()
        r = c.get(f"{ANICHAN_BASE}/", timeout=6.0)
        if r.status_code == 200:
            chunks = re.findall(r'src=["\'](/_next/static/chunks/[^"\']+)["\']', r.text)
            for chunk_path in chunks:
                chunk_url = f"{ANICHAN_BASE}{chunk_path}"
                rc = c.get(chunk_url, timeout=6.0)
                if rc.status_code == 200 and "watch/servers" in rc.text:
                    m = re.search(
                        r'([a-zA-Z0-9_\$]+)="([0-9a-f]{8})",([a-zA-Z0-9_\$]+)="([A-Za-z0-9+/=]{44})",([a-zA-Z0-9_\$]+)="([A-Za-z0-9+/=]{44})"',
                        rc.text,
                    )
                    if m:
                        _crypto_keys["k"] = m.group(2)
                        _crypto_keys["O"] = m.group(4)
                        _crypto_keys["b"] = m.group(6)
                        return _crypto_keys["k"], _crypto_keys["O"], _crypto_keys["b"]
    except Exception:
        pass
    return STATIC_K, STATIC_O, STATIC_B


def _get_session(client: Optional[httpx.Client] = None) -> Tuple[str, Dict[str, str]]:
    """Dapatkan token sesi 'n' dan cookie dari /api/watch/session."""
    global _session_cache
    now = time.time()
    if _session_cache["token_n"] and _session_cache["exp"] > now + 60:
        return _session_cache["token_n"], _session_cache["cookies"]

    c = client or _get_client()
    url = f"{ANICHAN_BASE}/api/watch/session"
    res = c.post(
        url,
        json={"token": ""},
        headers={
            "Content-Type": "application/json",
            "Referer": f"{ANICHAN_BASE}/",
            "Origin": ANICHAN_BASE,
        },
        timeout=8.0,
    )
    if res.status_code != 200:
        raise RuntimeError(f"Gagal inisialisasi sesi AniChan (status {res.status_code})")

    data = res.json()
    token_n = data.get("n") or ""
    exp = float(data.get("exp") or (now + 7200))
    cookies = {k: v for k, v in res.cookies.items()}

    _session_cache["token_n"] = token_n
    _session_cache["cookies"] = cookies
    _session_cache["exp"] = exp
    return token_n, cookies


def _decrypt_payload(raw: dict, token_n: str) -> dict:
    """Dekripsi payload servers AniChan jika terenkripsi AES-GCM (v == 1)."""
    if raw.get("v") != 1 or "i" not in raw or "d" not in raw:
        return raw

    def _do_decrypt(k_val, o_val, b_val):
        iv = base64.b64decode(raw["i"])
        ciphertext = base64.b64decode(raw["d"])
        raw_O = base64.b64decode(o_val)
        raw_b = base64.b64decode(b_val)
        hmac_key = bytes([x ^ y for x, y in zip(raw_O, raw_b)])
        aes_key = hmac.new(hmac_key, token_n.encode("utf-8"), hashlib.sha256).digest()
        decrypted = AESGCM(aes_key).decrypt(iv, ciphertext, None)
        return json.loads(decrypted.decode("utf-8"))

    try:
        return _do_decrypt(_crypto_keys["k"], _crypto_keys["O"], _crypto_keys["b"])
    except Exception:
        # Coba refresh keys dari web
        k, o, b = _refresh_keys_from_web()
        return _do_decrypt(k, o, b)


def clean_title_for_search(slug_or_title: str) -> str:
    """Normalisasi slug atau judul anime menjadi kata kunci pencarian yang bersih."""
    s = slug_or_title.strip()
    # Hapus prefiks sumber jika ada
    if ":" in s:
        s = s.split(":", 1)[1]
    # Hapus suffix umum
    s = re.sub(r"-sub-indo$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"-episode$", "", s, flags=re.IGNORECASE)
    # Hapus suffix ID numerik HiAnime jika ada di ujung (misal: eyeshield-21-7505 -> eyeshield-21)
    s = re.sub(r"-\d+$", "", s)
    # Ganti tanda strip dengan spasi
    s = s.replace("-", " ")
    return re.sub(r"\s+", " ", s).strip()


def _is_title_match(target: str, candidate: str) -> bool:
    """Verifikasi kecocokan judul anime untuk mencegah salah anime."""
    if not target or not candidate:
        return False
    t_clean = re.sub(r"[^\w\s]", "", target.lower()).strip()
    c_clean = re.sub(r"[^\w\s]", "", candidate.lower()).strip()
    if t_clean == c_clean:
        return True
    # Token similarity
    t_tokens = set(t_clean.split())
    c_tokens = set(c_clean.split())
    if not t_tokens:
        return False
    overlap = len(t_tokens.intersection(c_tokens))
    return (overlap / len(t_tokens)) >= 0.7 or (overlap / max(1, len(c_tokens))) >= 0.7


def resolve_anilist_id(slug_or_title: str) -> int:
    """Resolusi slug/judul ke AniList ID dengan perlindungan blacklist hentai."""
    if not slug_or_title:
        raise RuntimeError("Slug anime tidak boleh kosong")

    raw_lower = slug_or_title.lower()
    if "hentai" in raw_lower:
        raise RuntimeError("Konten genre Hentai diblokir")

    # 1. Cek jika input sudah berupa ID numerik langsung
    if slug_or_title.isdigit():
        return int(slug_or_title)

    # 2. Cek in-memory cache
    if slug_or_title in _SLUG_ID_CACHE:
        return _SLUG_ID_CACHE[slug_or_title]

    clean_q = clean_title_for_search(slug_or_title)
    if "hentai" in clean_q.lower():
        raise RuntimeError("Konten genre Hentai diblokir")

    c = _get_client()
    url = f"{ANICHAN_BASE}/api/suggest?q={urllib.parse.quote(clean_q)}"
    try:
        r = c.get(url, timeout=7.0)
        if r.status_code == 200:
            data = r.json()
            results = data.get("results") or []
            for item in results:
                # Blacklist filter Hentai (Direktif #4 Master Directives)
                genres = [g.lower() for g in (item.get("genres") or [])]
                if "hentai" in genres:
                    continue

                item_id = item.get("id")
                item_title = item.get("title") or ""
                item_romaji = item.get("titleRomaji") or ""

                if not item_id:
                    continue

                if _is_title_match(clean_q, item_title) or _is_title_match(clean_q, item_romaji):
                    _SLUG_ID_CACHE[slug_or_title] = int(item_id)
                    return int(item_id)

            # Jika tidak ada yang exact match, tapi ada hasil pertama non-hentai
            if results:
                first = results[0]
                if "hentai" not in [g.lower() for g in (first.get("genres") or [])]:
                    first_id = first.get("id")
                    if first_id:
                        _SLUG_ID_CACHE[slug_or_title] = int(first_id)
                        return int(first_id)
    except Exception as e:
        if "hentai" in str(e).lower():
            raise

    # 3. Fallback: AniList GraphQL
    try:
        from api.anilist import anime_relations
        rels = anime_relations(clean_q)
        if rels and isinstance(rels, list) and len(rels) > 0:
            al_id = rels[0].get("id")
            if al_id:
                _SLUG_ID_CACHE[slug_or_title] = int(al_id)
                return int(al_id)
    except Exception:
        pass

    raise RuntimeError(f"Tidak dapat menemukan AniList ID untuk anime: '{slug_or_title}'")


def _unwrap_direct_m3u8(stream_url: str) -> Tuple[str, str]:
    """Ekstrak raw direct upstream M3U8 dari URL pembungkus jika ada.
    Mengembalikan (direct_m3u8_url, referer).
    """
    if not stream_url:
        return "", ""
    parsed = urllib.parse.urlsplit(stream_url)
    qs = urllib.parse.parse_qs(parsed.query)
    raw_upstream = qs.get("url", [""])[0]
    raw_ref = qs.get("ref", [""])[0]

    if raw_upstream and raw_upstream.startswith("http"):
        referer = raw_ref or "https://megaplay.buzz/"
        return raw_upstream, referer

    # Jika bukan pembungkus, gunakan stream_url langsung
    referer = "https://anichan.to/"
    return stream_url, referer


def _parse_m3u8_variants(master_url: str, m3u8_text: str) -> List[Dict[str, str]]:
    """Parse daftar varian resolusi dari manifest master playlist M3U8."""
    lines = m3u8_text.splitlines()
    variants = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("#EXT-X-STREAM-INF"):
            rm = re.search(r"RESOLUTION=\d+x(\d+)", s)
            name_m = re.search(r'NAME="([^"]+)"', s)
            q = (rm.group(1) + "p") if rm else ("auto" if not name_m else name_m.group(1))
            v_url = ""
            for j in range(i + 1, len(lines)):
                candidate = lines[j].strip()
                if candidate and not candidate.startswith("#"):
                    v_url = candidate
                    break
            if v_url:
                if not v_url.startswith("http"):
                    v_url = urllib.parse.urljoin(master_url, v_url)
                variants.append({"q": q, "url": v_url})

    if variants:
        # Urutkan dari resolusi tertinggi ke terendah
        variants.sort(key=lambda v: int(re.sub(r"\D", "", v["q"]) or 0), reverse=True)
        return variants

    # Single-variant fallback
    return [{"q": "auto", "url": master_url}]


def _validate_direct_hls_stream(url: str, referer: str) -> Tuple[str, List[Dict[str, str]]]:
    """Validasi bahwa URL benar-benar mengembalikan file manifest HLS m3u8 (#EXTM3U).
    Raise RuntimeError jika stream mati atau bukan HLS m3u8.
    """
    c = _get_client()
    headers = {"User-Agent": HI_UA}
    if referer:
        headers["Referer"] = referer
        headers["Origin"] = referer.rstrip("/")

    r = c.get(url, headers=headers, timeout=8.0)
    if r.status_code != 200:
        raise RuntimeError(f"Upstream stream error HTTP {r.status_code}")

    text = r.text
    if "#EXTM3U" not in text:
        raise RuntimeError("Stream response bukan manifest HLS M3U8 valid")

    variants = _parse_m3u8_variants(url, text)
    return text, variants


def resolve_stream(slug: str, ep: int = 1, mode: str = "sub", q: str = "best") -> dict:
    """Fungsi utama: menyelesaikan stream HLS M3U8 langsung dari AniChan.
    Dibatasi ketat hanya menerima server bertipe 'hls' dan menolak semua 'embed'.
    """
    if "hentai" in (slug or "").lower():
        raise RuntimeError("Konten genre Hentai diblokir")

    req_mode = "dub" if str(mode).lower() == "dub" else "sub"
    aid = resolve_anilist_id(slug)

    c = _get_client()
    token_n, cookies = _get_session(c)
    k_key = _crypto_keys.get("k", STATIC_K)

    # 1. Ambil server dari tier fast, fallback ke rest
    servers_list: List[dict] = []
    for tier in ("fast", "rest"):
        url = f"{ANICHAN_BASE}/api/watch/servers?anilistId={aid}&ep={ep}&category={req_mode}&tier={tier}"
        headers = {
            "User-Agent": HI_UA,
            "X-Wk": k_key,
            "Referer": f"{ANICHAN_BASE}/anime/{aid}",
            "Origin": ANICHAN_BASE,
        }
        res = c.get(url, headers=headers, cookies=cookies, timeout=8.0)
        if res.status_code == 401:
            # Refresh sesi
            _session_cache["exp"] = 0
            token_n, cookies = _get_session(c)
            res = c.get(url, headers=headers, cookies=cookies, timeout=8.0)

        if res.status_code == 200:
            raw = res.json()
            data = _decrypt_payload(raw, token_n)
            srvs = data.get("servers") or []
            if srvs:
                servers_list.extend(srvs)
                break

    # Fallback ke mode sub jika dub kosong
    if not servers_list and req_mode == "dub":
        for tier in ("fast", "rest"):
            url = f"{ANICHAN_BASE}/api/watch/servers?anilistId={aid}&ep={ep}&category=sub&tier={tier}"
            headers = {
                "User-Agent": HI_UA,
                "X-Wk": k_key,
                "Referer": f"{ANICHAN_BASE}/anime/{aid}",
                "Origin": ANICHAN_BASE,
            }
            res = c.get(url, headers=headers, cookies=cookies, timeout=8.0)
            if res.status_code == 200:
                raw = res.json()
                data = _decrypt_payload(raw, token_n)
                srvs = data.get("servers") or []
                if srvs:
                    servers_list.extend(srvs)
                    req_mode = "sub"
                    break

    if not servers_list:
        raise RuntimeError(f"Tidak ada server stream pada AniChan untuk episode {ep}")

    # 2. Strict Filter: HANYA izinkan type == 'hls' dan stream ada (DILARANG EMBED)
    hls_servers = [
        s for s in servers_list
        if str(s.get("type", "")).lower() == "hls" and s.get("stream")
    ]
    if not hls_servers:
        raise RuntimeError(f"Tidak ada server direct HLS M3U8 pada AniChan untuk ep {ep} (embeds diabaikan)")

    # Urutkan prioritas server: anikoto > megaplay_hd1 > megaplay_hd2 > aniwatchtv > echovideo
    def _server_priority(s: dict) -> int:
        name = str(s.get("name", "")).lower()
        if "anikoto" in name:
            return 0
        if "megaplay_hd1" in name:
            return 1
        if "megaplay_hd2" in name:
            return 2
        if "aniwatch" in name or "zoko" in name:
            return 3
        return 4

    hls_servers.sort(key=_server_priority)

    # 3. Probe dan dapatkan manifest HLS master hidup
    last_err = ""
    for srv in hls_servers:
        raw_stream_url = srv.get("stream") or ""
        direct_url, referer = _unwrap_direct_m3u8(raw_stream_url)

        # Coba raw upstream direct dulu (lebih kencang langsung ke CDN), jika gagal fallback ke wrapper
        test_candidates = [(direct_url, referer)]
        if direct_url != raw_stream_url:
            test_candidates.append((raw_stream_url, "https://anichan.to/"))

        for cand_url, cand_ref in test_candidates:
            try:
                m3u8_text, variants = _validate_direct_hls_stream(cand_url, cand_ref)
                if not variants:
                    continue

                # Normalisasi Subtitles
                raw_subs = srv.get("subtitles") or []
                subtitles = []
                for s in raw_subs:
                    s_url = s.get("url") or ""
                    if not s_url:
                        continue
                    # Normalisasi URL subtitle
                    if s_url.startswith("/"):
                        s_url = f"{ANICHAN_BASE}{s_url}"
                    lang = s.get("lang") or "English"
                    is_def = bool(s.get("default", False)) or (len(subtitles) == 0 and "english" in lang.lower())
                    subtitles.append({
                        "label": lang,
                        "lang": "en" if "english" in lang.lower() else "id" if "indonesia" in lang.lower() else lang.lower()[:2],
                        "url": s_url,
                        "default": is_def,
                    })

                default_sub = next((sb for sb in subtitles if sb.get("default")), subtitles[0] if subtitles else None)
                sub_url = default_sub["url"] if default_sub else None
                sub_lang = default_sub["label"] if default_sub else None

                intro = srv.get("intro") or {"start": 0, "end": 0}
                outro = srv.get("outro") or {"start": 0, "end": 0}

                # Sukses menghasilkan stream direct HLS M3U8 murni
                return {
                    "master": cand_url,
                    "variants": variants,
                    "sub": sub_url,
                    "sub_lang": sub_lang,
                    "subtitles": subtitles,
                    "referer": cand_ref,
                    "server": f"anichan:{srv.get('name', 'hls')}",
                    "mode": req_mode,
                    "intro": intro,
                    "outro": outro,
                    "source": "anichan",
                    "is_failover": True,
                    "cached": False,
                }
            except Exception as e:
                last_err = f"{srv.get('name')}: {e}"
                continue

    raise RuntimeError(f"Gagal memvalidasi direct HLS M3U8 dari server AniChan: {last_err}")


def get_episodes(slug: str) -> List[Dict[str, Any]]:
    """Fallback pengambilan daftar episode anime via AniChan."""
    aid = resolve_anilist_id(slug)
    c = _get_client()
    url = f"{ANICHAN_BASE}/api/watch/episodes?anilistId={aid}"
    try:
        r = c.get(url, timeout=7.0)
        if r.status_code == 200:
            data = r.json()
            total = int(data.get("episodes") or 0)
            if total > 0:
                return [{"ep": i, "ep_id": str(i)} for i in range(1, total + 1)]
    except Exception:
        pass

    # Coba catalog info
    try:
        url_cat = f"{ANICHAN_BASE}/api/catalog/anime/{aid}"
        r_cat = c.get(url_cat, timeout=7.0)
        if r_cat.status_code == 200:
            data_cat = r_cat.json()
            total = int(data_cat.get("episodes") or 0)
            if total > 0:
                return [{"ep": i, "ep_id": str(i)} for i in range(1, total + 1)]
    except Exception:
        pass

    return []
