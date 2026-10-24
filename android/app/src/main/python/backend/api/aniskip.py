"""Client ringan AniSkip API (v2) untuk deteksi opening (OP) dan ending (ED).

API: https://api.aniskip.com/v2/skip-times/{mal_id}/{episode_num}?types=op&types=ed
Dokumentasi & Schema:
- results: list of { skipType: 'op'|'ed'|'mixed-op'|'mixed-ed', interval: { startTime, endTime } }
"""
import time
import re
import httpx

# _CACHE format:
# key -> (data_dict, timestamp, ttl_seconds)
_CACHE = {}
_CACHE_TTL = 86400         # 24 jam untuk hasil valid
_NEGATIVE_CACHE_TTL = 900  # 15 menit untuk 404 / empty (belum ada data di AniSkip)
_TITLE_TO_MAL = {}         # Cache in-memory pemetaan slug/judul -> mal_id


def store_mal_id(identifier: str, mal_id) -> None:
    """Simpan pemetaan judul atau slug ke mal_id di memori."""
    if not identifier or not mal_id or not isinstance(identifier, str):
        return
    try:
        m_int = int(str(mal_id).strip())
        if m_int <= 0:
            return
        clean_raw = str(identifier).strip().lower()
        if clean_raw:
            _TITLE_TO_MAL[clean_raw] = m_int
            no_id = re.sub(r"-\d+$", "", clean_raw)
            if no_id != clean_raw:
                _TITLE_TO_MAL[no_id] = m_int
        norm = normalize_title(identifier)
        if norm:
            _TITLE_TO_MAL[norm] = m_int
    except Exception:
        pass


def get_mal_id_from_cache(identifier: str) -> int:
    """Ambil mal_id dari cache in-memory berdasarkan identifier (slug atau judul)."""
    if not identifier or not isinstance(identifier, str):
        return 0
    clean_raw = str(identifier).strip().lower()
    if clean_raw in _TITLE_TO_MAL:
        return _TITLE_TO_MAL[clean_raw]
    no_id = re.sub(r"-\d+$", "", clean_raw)
    if no_id in _TITLE_TO_MAL:
        return _TITLE_TO_MAL[no_id]
    norm = normalize_title(identifier)
    if norm and norm in _TITLE_TO_MAL:
        return _TITLE_TO_MAL[norm]
    return 0


def is_valid_interval(start, end) -> bool:
    """Validasi interval waktu opening/ending anime.
    Memastikan start dan end adalah angka valid, end > start, end > 0, dan durasi minimal 5.0 detik."""
    try:
        s = float(start)
        e = float(end)
        return e > s and e > 0 and (e - s) >= 5.0
    except (ValueError, TypeError):
        return False


def normalize_title(title: str) -> str:
    """Normalisasi judul anime untuk pencocokan cache lintas provider.
    Menghilangkan prefix provider (otakudesu/hianime), tag sub indo, nomor episode, batch, trailing numeric ID, dan karakter non-alphanumeric."""
    if not title or not isinstance(title, str):
        return ""
    s = title.lower().replace("&", "and")
    # Ganti separator umum dengan spasi
    s = re.sub(r"[:\-_/.]+", " ", s)
    # Hapus provider prefix dan tag umum
    s = re.sub(r"\b(otakudesu|hianime|sub\s*indo|episode\s*\d+|ep\s*\d+|batch|complete|bd|season\s*\d+|s\d+)\b", " ", s)
    # Hapus trailing numeric ID (seperti ID 19319 pada hianime slug)
    s = re.sub(r"\s+\d+\s*$", " ", s)
    return re.sub(r"[^a-z0-9]", "", s).strip()


def store_skip_times(mal_id=None, title: str = "", ep: int = 1, intro: dict = None, outro: dict = None, ttl: int = _CACHE_TTL):
    """Menyimpan interval OP/ED yang valid ke cache memori lintas provider.
    Mendukung penguncian ganda via mal_id dan normalized_title."""
    now = time.time()
    try:
        ep_int = int(str(ep).strip())
    except Exception:
        ep_int = 1

    valid_intro = {"start": 0, "end": 0}
    valid_outro = {"start": 0, "end": 0}
    has_valid = False

    if isinstance(intro, dict) and is_valid_interval(intro.get("start"), intro.get("end")):
        valid_intro = {"start": round(float(intro["start"]), 2), "end": round(float(intro["end"]), 2)}
        has_valid = True

    if isinstance(outro, dict) and is_valid_interval(outro.get("start"), outro.get("end")):
        valid_outro = {"start": round(float(outro["start"]), 2), "end": round(float(outro["end"]), 2)}
        has_valid = True

    if not has_valid:
        return

    data = {"intro": valid_intro, "outro": valid_outro}

    # 1. Simpan berdasarkan mal_id jika ada
    if mal_id:
        try:
            m_id = int(str(mal_id).strip())
            _CACHE[("mal", m_id, ep_int)] = (data, now, ttl)
            _CACHE[(m_id, ep_int)] = (data, now, ttl)
        except Exception:
            pass

    # 2. Simpan berdasarkan normalized_title jika ada
    norm_t = normalize_title(title)
    if norm_t:
        _CACHE[("title", norm_t, ep_int)] = (data, now, ttl)


def get_cached_skip_times(mal_id=None, title: str = "", ep: int = 1) -> dict:
    """Mencari interval OP/ED dari cache memori lintas provider."""
    now = time.time()
    try:
        ep_int = int(str(ep).strip())
    except Exception:
        ep_int = 1

    # 1. Cek kunci mal_id
    if mal_id:
        try:
            m_id = int(str(mal_id).strip())
            for key in [("mal", m_id, ep_int), (m_id, ep_int)]:
                if key in _CACHE:
                    entry, ts, ttl = _CACHE[key]
                    if now - ts < ttl:
                        return entry
        except Exception:
            pass

    # 2. Cek kunci title
    norm_t = normalize_title(title)
    if norm_t:
        key = ("title", norm_t, ep_int)
        if key in _CACHE:
            entry, ts, ttl = _CACHE[key]
            if now - ts < ttl:
                return entry

    return None


def get_skip_times(mal_id, episode_num: int, episode_length: float = 0, timeout: float = 4.0) -> dict:
    """Mengambil interval opening dan ending dari AniSkip API.

    Returns:
        dict dengan key 'intro' dan 'outro', masing-masing memiliki 'start' dan 'end' (detik float/int).
    """
    empty_result = {
        "intro": {"start": 0, "end": 0},
        "outro": {"start": 0, "end": 0}
    }
    if not mal_id or not episode_num:
        return empty_result

    try:
        mal_int = int(str(mal_id).strip())
        ep_int = int(str(episode_num).strip())
    except Exception:
        return empty_result

    now = time.time()
    for cache_key in [("mal", mal_int, ep_int), (mal_int, ep_int)]:
        if cache_key in _CACHE:
            entry, ts, ttl = _CACHE[cache_key]
            if now - ts < ttl:
                return entry

    # AniSkip API v2 mewajibkan parameter episodeLength (default 0 jika durasi belum diketahui)
    ep_len_val = 0.0
    try:
        if episode_length is not None:
            ep_len_val = max(0.0, float(episode_length))
    except Exception:
        ep_len_val = 0.0
    ep_len_param = str(round(ep_len_val, 2)) if ep_len_val > 0 else "0"
    url = f"https://api.aniskip.com/v2/skip-times/{mal_int}/{ep_int}?types=op&types=ed&types=mixed-op&types=mixed-ed&episodeLength={ep_len_param}"

    headers = {
        "User-Agent": "Tatap (https://github.com/asfaraguest/tatap)",
        "Accept": "application/json"
    }

    intro = {"start": 0, "end": 0}
    outro = {"start": 0, "end": 0}
    should_cache = False
    cache_ttl = _CACHE_TTL

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                body = resp.json()
                if body.get("found") and isinstance(body.get("results"), list):
                    for item in body["results"]:
                        st = (item.get("skipType") or "").lower()
                        interval = item.get("interval") or {}
                        start = round(float(interval.get("startTime") or 0), 2)
                        end = round(float(interval.get("endTime") or 0), 2)
                        if is_valid_interval(start, end):
                            if "op" in st and intro["end"] == 0:
                                intro = {"start": start, "end": end}
                            elif "ed" in st and outro["end"] == 0:
                                outro = {"start": start, "end": end}
                    should_cache = True
                    cache_ttl = _CACHE_TTL
                else:
                    # 200 tapi found false: negative cache pendek
                    should_cache = True
                    cache_ttl = _NEGATIVE_CACHE_TTL
            elif resp.status_code == 404:
                # 404 belum ada data di AniSkip: negative cache pendek
                should_cache = True
                cache_ttl = _NEGATIVE_CACHE_TTL
            elif resp.status_code >= 500 or resp.status_code == 429:
                # Server error atau rate limit: jangan cache sama sekali
                should_cache = False
    except Exception:
        # Network exception, timeout, DNS error: jangan simpan ke cache
        should_cache = False

    res = {"intro": intro, "outro": outro}
    if should_cache:
        _CACHE[("mal", mal_int, ep_int)] = (res, now, cache_ttl)
        _CACHE[(mal_int, ep_int)] = (res, now, cache_ttl)
    return res
