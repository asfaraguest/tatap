"""Ambil daftar anime per-season dari AniList GraphQL."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import HI_UA
import httpx

ANILIST_URL = "https://graphql.anilist.co"
UA = HI_UA

# Pelacak backoff rate-limit AniList (HTTP 429) in-memory
_al_rate_limit_until = 0.0

def _is_rate_limited() -> bool:
    """Mengembalikan True jika sedang dalam masa cooldown rate limit 429 AniList."""
    global _al_rate_limit_until
    return time.time() < _al_rate_limit_until

def _record_rate_limit(resp) -> None:
    """Mencatat waktu penalti 429 dari header Retry-After atau default 60 detik."""
    global _al_rate_limit_until
    if resp is not None and getattr(resp, "status_code", 0) == 429:
        retry = resp.headers.get("Retry-After") if hasattr(resp, "headers") else None
        wait_sec = 60.0
        if retry:
            try:
                wait_sec = max(5.0, min(float(retry), 300.0))
            except Exception:
                pass
        _al_rate_limit_until = time.time() + wait_sec

QUERY = """
query ($season: MediaSeason, $year: Int, $page: Int, $perPage: Int, $statusIn: [MediaStatus]) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { total perPage currentPage lastPage hasNextPage }
    media(season: $season, seasonYear: $year, status_in: $statusIn, type: ANIME, sort: POPULARITY_DESC) {
      id
      idMal
      status
      title { romaji english }
      format
      episodes
      duration
      averageScore
      season
      seasonYear
      source
      genres
      studios(isMain: true) {
        nodes {
          name
        }
      }
      coverImage { large medium }
      siteUrl
      description(asHtml: false)
      nextAiringEpisode {
        episode
        airingAt
        timeUntilAiring
      }
    }
  }
}
"""

def clean_synopsis_text(desc: str) -> str:
    """Bersihkan tag HTML, unescape entitas, dan normalkan spasi tanpa memotong panjang narasi."""
    if not desc:
        return ""
    import html as _html, re
    text = re.sub(r'<br\s*/?>', '\n', desc, flags=re.I)
    text = re.sub(r'</?p>', '\n\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = _html.unescape(text)
    text = re.sub(r'\n*\(Source:[^)]*\)', '', text, flags=re.I)
    text = re.sub(r'\n*\[Written by MAL Rewrite\]', '', text, flags=re.I)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text

def compute_episode_counts(m: dict) -> tuple:
    """Menghitung (eps_released, eps_total) dari objek media AniList.
    Jika anime ongoing dan memiliki nextAiringEpisode, episode rilis = next_episode - 1."""
    total = m.get("episodes") or 0
    status = (m.get("status") or "").upper()
    next_air = m.get("nextAiringEpisode")
    if next_air and isinstance(next_air, dict) and next_air.get("episode"):
        released = max(0, int(next_air.get("episode")) - 1)
    elif status in ("FINISHED", "COMPLETED"):
        released = total
    else:
        released = total
    return released, total

RECENTLY_FINISHED_QUERY = """
query AiringFinished($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { total perPage currentPage lastPage hasNextPage }
    media(format: TV, status: FINISHED, type: ANIME, sort: [END_DATE_DESC, POPULARITY_DESC]) {
      id
      idMal
      status
      title { romaji english }
      format
      episodes
      duration
      averageScore
      season
      seasonYear
      source
      genres
      studios(isMain: true) {
        nodes {
          name
        }
      }
      startDate { year month day }
      endDate { year month day }
      coverImage { large medium }
      siteUrl
      description(asHtml: false)
    }
  }
}
"""

def current_season():
    """Return (year, season_name) untuk bulan hari ini."""
    import datetime as _dt
    m = _dt.date.today().month
    name = "winter" if m in (1,2,3) else "spring" if m in (4,5,6) \
          else "summer" if m in (7,8,9) else "fall"
    return _dt.date.today().year, name

def prev_season(name, year):
    order = ["winter", "spring", "summer", "fall"]
    idx = order.index(name)
    if idx == 0:
        return year - 1, "fall"
    return year, order[idx - 1]

_al_client = None

def _get_al_client():
    global _al_client
    if _al_client is None:
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=60.0)
        _al_client = httpx.Client(
            timeout=httpx.Timeout(12.0, connect=5.0),
            limits=limits,
            headers={"Content-Type": "application/json", "User-Agent": UA}
        )
    return _al_client

def close_al_client():
    """Tutup persistent client AniList saat aplikasi shutdown."""
    global _al_client
    if _al_client is not None:
        try:
            _al_client.close()
        except Exception:
            pass
        _al_client = None

def season_page(name, year, page=1, per_page=25, status_in=None):
    """Fetch satu halaman AniList untuk season/year tertentu. Return {pageInfo, media:[]}."""
    if _is_rate_limited():
        return {"pageInfo": {"total": 0, "perPage": per_page, "currentPage": page,
                             "lastPage": 1, "hasNextPage": False}, "media": []}
    try:
        c = _get_al_client()
        variables = {
            "season": name.upper(),
            "year": year,
            "page": page,
            "perPage": per_page
        }
        if status_in:
            variables["statusIn"] = status_in
        r = c.post(ANILIST_URL, json={
            "query": QUERY,
            "variables": variables
        })
        if r.status_code != 200:
            _record_rate_limit(r)
            return {"pageInfo": {"total": 0, "perPage": per_page, "currentPage": page,
                                 "lastPage": 1, "hasNextPage": False}, "media": []}
        d = r.json().get("data", {}).get("Page", {})
        d.setdefault("pageInfo", {})
        d.setdefault("media", [])
        # AniList PageInfo untuk season-filter sering over-report (total=5000, lastPage=200).
        # Batas didasarkan pada item terisi — kalau page ini < per_page, tidak ada next.
        items = d.get("media") or []
        pi = d.get("pageInfo") or {}
        has_next = bool(pi.get("hasNextPage")) and len(items) >= per_page
        pi["hasNextPage"] = has_next
        if has_next:
            raw_last = pi.get("lastPage") or 1
            pi["lastPage"] = max(page + 1, min(raw_last, 20))
        else:
            pi["lastPage"] = max(1, page)
        pi["perPage"] = per_page
        d["pageInfo"] = pi
        return d
    except Exception:
        return {"pageInfo": {"total": 0, "perPage": per_page, "currentPage": page,
                             "lastPage": 1, "hasNextPage": False}, "media": []}


def recently_finished_page(page=1, per_page=20):
    """Fetch anime musiman yang baru saja tamat dari AniList, diurutkan dari yang paling baru tamat."""
    if _is_rate_limited():
        return {"pageInfo": {"total": 0, "perPage": per_page, "currentPage": page,
                             "lastPage": 1, "hasNextPage": False}, "media": []}
    try:
        c = _get_al_client()
        r = c.post(ANILIST_URL, json={
            "query": RECENTLY_FINISHED_QUERY,
            "variables": {"page": page, "perPage": per_page}
        })
        if r.status_code != 200:
            _record_rate_limit(r)
            return {"pageInfo": {"total": 0, "perPage": per_page, "currentPage": page,
                                 "lastPage": 1, "hasNextPage": False}, "media": []}
        d = r.json().get("data", {}).get("Page", {})
        d.setdefault("pageInfo", {})
        d.setdefault("media", [])
        items = d.get("media") or []
        pi = d.get("pageInfo") or {}
        has_next = bool(pi.get("hasNextPage")) and len(items) >= per_page
        pi["hasNextPage"] = has_next
        if has_next:
            raw_last = pi.get("lastPage") or 1
            pi["lastPage"] = max(page + 1, min(raw_last, 15))
        else:
            pi["lastPage"] = max(1, page)
        pi["perPage"] = per_page
        d["pageInfo"] = pi
        return d
    except Exception:
        return {"pageInfo": {"total": 0, "perPage": per_page, "currentPage": page,
                             "lastPage": 1, "hasNextPage": False}, "media": []}


SCHEDULE_QUERY = """
query ($now: Int, $end: Int, $perPage: Int) {
  Page(perPage: $perPage) {
    airingSchedules(airingAt_greater: $now, airingAt_lesser: $end, sort: TIME) {
      id airingAt episode
      media {
        id idMal title { romaji english }
        season seasonYear format
        coverImage { large medium }
      }
    }
  }
}
"""



SCHEDULE_PAGED_QUERY = """
query GetSchedule($page: Int, $now: Int, $end: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo { hasNextPage currentPage }
    airingSchedules(airingAt_greater: $now, airingAt_lesser: $end, sort: TIME) {
      id airingAt episode
      media {
        id idMal title { romaji english }
        season seasonYear format
        genres averageScore
        coverImage { large medium }
      }
    }
  }
}
"""

def anilist_schedules(now_ts, end_ts, per_page=50):
    """Episode yang tayang antara now_ts..end_ts (unix detik). Return list schedule.
    Longgar: anime apapun, tidak difilter by season. Caller yang filter matched."""
    if _is_rate_limited():
        return []
    try:
        c = _get_al_client()
        r = c.post(ANILIST_URL, json={
            "query": SCHEDULE_QUERY,
            "variables": {"now": now_ts, "end": end_ts, "perPage": per_page}
        })
        if r.status_code != 200:
            _record_rate_limit(r)
            return []
        return r.json().get("data", {}).get("Page", {}).get("airingSchedules", []) or []
    except Exception:
        return []

def anilist_schedules_range(start_ts: int, end_ts: int, max_pages: int = 6):
    """Episode yang tayang dalam rentang waktu (start_ts..end_ts) dengan pagination."""
    if _is_rate_limited():
        return []
    all_schedules = []
    c = _get_al_client()
    for page in range(1, max_pages + 1):
        if _is_rate_limited():
            break
        try:
            r = c.post(ANILIST_URL, json={
                "query": SCHEDULE_PAGED_QUERY,
                "variables": {"page": page, "now": start_ts, "end": end_ts, "perPage": 50}
            })
            if r.status_code != 200:
                _record_rate_limit(r)
                break
            d = r.json().get("data", {}).get("Page", {})
            schedules = d.get("airingSchedules") or []
            all_schedules.extend(schedules)
            if not d.get("pageInfo", {}).get("hasNextPage"):
                break
        except Exception:
            break
    return all_schedules


RELATIONS_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    idMal
    title { romaji english }
    format
    seasonYear
    relations {
      edges {
        relationType
        node {
          id
          idMal
          title { romaji english }
          format
          seasonYear
          status
          coverImage { medium large }
        }
      }
    }
  }
}
"""


MEDIA_BY_ID_QUERY = """
query ($id: Int) {
  Media(id: $id, type: ANIME) {
    id
    idMal
    title { romaji english }
    format
    seasonYear
    status
    coverImage { medium large }
    relations {
      edges {
        relationType
        node {
          id
          idMal
          title { romaji english }
          format
          seasonYear
          status
          coverImage { medium large }
        }
      }
    }
  }
}
"""


def anime_relations(search_query: str):
    """Ambil relasi franchise anime (Prequel, Sequel, Parent, Side Story, dll) dari AniList,
    termasuk menelusuri rantai prekuel ke belakang untuk menemukan karya awal (Season 1)."""
    if not search_query or not search_query.strip():
        return []
    if _is_rate_limited():
        return []
    try:
        c = _get_al_client()
        r = c.post(ANILIST_URL, json={
            "query": RELATIONS_QUERY,
            "variables": {"search": search_query.strip()}
        })
        if r.status_code != 200:
            _record_rate_limit(r)
            return []
        data = r.json().get("data", {}).get("Media", {})
        if not data or not data.get("id"):
            return []

        current_id = data.get("id")
        edges = data.get("relations", {}).get("edges", []) or []
        out = []
        seen_ids = {current_id}

        # 1. Kumpulkan relasi langsung (1-hop)
        direct_prequel_node = None
        for edge in edges:
            rel = edge.get("relationType", "")
            node = edge.get("node", {})
            n_id = node.get("id")
            fmt = (node.get("format") or "").upper()
            if rel in ("PREQUEL", "SEQUEL", "PARENT", "SIDE_STORY", "ALTERNATIVE", "SUMMARY") and fmt in ("TV", "MOVIE", "OVA", "ONA", "SPECIAL"):
                if n_id and n_id not in seen_ids:
                    seen_ids.add(n_id)
                    t_obj = node.get("title", {}) or {}
                    t_eng = t_obj.get("english") or ""
                    t_rom = t_obj.get("romaji") or ""
                    title = t_eng if t_eng else t_rom
                    img = (node.get("coverImage") or {}).get("medium") or ""
                    entry = {
                        "id": n_id,
                        "relation": rel,
                        "format": fmt,
                        "title": title,
                        "title_romaji": t_rom,
                        "year": node.get("seasonYear"),
                        "status": node.get("status"),
                        "poster": img
                    }
                    out.append(entry)
                    if rel in ("PREQUEL", "PARENT") and direct_prequel_node is None:
                        direct_prequel_node = node

        # 2. Telusuri rantai prekuel ke belakang (hingga 3 langkah) untuk menemukan Season 1 / Origin
        curr_prequel = direct_prequel_node
        deepest_prequel = None
        for _ in range(3):
            if not curr_prequel or not curr_prequel.get("id"):
                break
            if _is_rate_limited():
                break
            # Query node prekuel ini untuk melihat prekuel sebelumnya
            r_prev = c.post(ANILIST_URL, json={
                "query": MEDIA_BY_ID_QUERY,
                "variables": {"id": curr_prequel.get("id")}
            })
            if r_prev.status_code != 200:
                _record_rate_limit(r_prev)
                break
            prev_data = r_prev.json().get("data", {}).get("Media", {})
            prev_edges = prev_data.get("relations", {}).get("edges", []) or []

            next_prequel = None
            for e in prev_edges:
                p_rel = e.get("relationType", "")
                p_node = e.get("node", {})
                p_id = p_node.get("id")
                p_fmt = (p_node.get("format") or "").upper()
                if p_rel in ("PREQUEL", "PARENT") and p_id not in seen_ids and p_fmt in ("TV", "MOVIE", "OVA", "ONA", "SPECIAL"):
                    seen_ids.add(p_id)
                    p_t_obj = p_node.get("title", {}) or {}
                    p_t_eng = p_t_obj.get("english") or ""
                    p_t_rom = p_t_obj.get("romaji") or ""
                    p_title = p_t_eng if p_t_eng else p_t_rom
                    p_img = (p_node.get("coverImage") or {}).get("medium") or ""
                    p_entry = {
                        "id": p_id,
                        "relation": "PREQUEL",
                        "format": p_fmt,
                        "title": p_title,
                        "title_romaji": p_t_rom,
                        "year": p_node.get("seasonYear"),
                        "status": p_node.get("status"),
                        "poster": p_img
                    }
                    out.append(p_entry)
                    next_prequel = p_node
                    deepest_prequel = p_entry
                    break
            curr_prequel = next_prequel

        # Jika ditemukan prekuel paling awal (Season 1 / Origin), tandai secara eksplisit
        if deepest_prequel:
            deepest_prequel["is_origin"] = True

        return out
    except Exception:
        return []


SEARCH_METADATA_QUERY = """
query ($search: String, $perPage: Int) {
  Page(page: 1, perPage: $perPage) {
    media(search: $search, type: ANIME, sort: SEARCH_MATCH) {
      id
      idMal
      title { romaji english native }
      season
      seasonYear
      startDate { year }
    }
  }
}
"""


def search_anime_metadata(search_query: str, per_page: int = 12) -> list:
    """Cari metadata anime (season, year, title, idMal) dari AniList untuk memperkaya hasil pencarian."""
    if not search_query or not search_query.strip() or _is_rate_limited():
        return []
    try:
        c = _get_al_client()
        r = c.post(ANILIST_URL, json={
            "query": SEARCH_METADATA_QUERY,
            "variables": {"search": search_query.strip(), "perPage": per_page}
        })
        if r.status_code != 200:
            _record_rate_limit(r)
            return []
        data = r.json().get("data", {}).get("Page", {}).get("media", [])
        return data or []
    except Exception:
        return []


def _match_title_tokens(target_q: str, candidate_title: str) -> bool:
    """Validasi kemiripan judul berbasis token untuk mencegah false positive pada pencarian metadata."""
    if not target_q or not candidate_title:
        return False
    import re
    stopwords = {"the", "a", "an", "of", "in", "to", "and", "und", "der", "die", "das", "no", "wa", "ga", "ni", "de", "series"}
    tok_q = {w for w in re.sub(r"[^\w']", " ", target_q.lower()).split() if w} - stopwords
    tok_c = {w for w in re.sub(r"[^\w']", " ", candidate_title.lower()).split() if w} - stopwords
    if not tok_q or not tok_c:
        return False
    overlap = len(tok_q & tok_c) / max(len(tok_q), 1)
    return overlap >= 0.50


def resolve_mal_id_by_title(search_query: str) -> int:
    """Cari MAL ID (idMal) dari AniList berdasarkan judul anime.
    Mendukung penanganan apostrof slug dan fallback pemendekan kata dengan validasi kemiripan judul ketat."""
    if not search_query or not search_query.strip() or _is_rate_limited():
        return 0
    import re
    clean = search_query.strip()
    clean = re.sub(r"\b(\w+)\s+s\b", r"\1's", clean, flags=re.I)
    words = clean.split()
    c = _get_al_client()
    attempts = [clean]
    if len(words) > 3:
        attempts.append(" ".join(words[:4]))
        attempts.append(" ".join(words[:3]))
    for att in attempts:
        try:
            r = c.post(ANILIST_URL, json={
                "query": SEARCH_METADATA_QUERY,
                "variables": {"search": att, "perPage": 5}
            })
            if r.status_code != 200:
                _record_rate_limit(r)
                continue
            media_list = r.json().get("data", {}).get("Page", {}).get("media", []) or []
            for m in media_list:
                if m.get("idMal"):
                    t_obj = m.get("title") or {}
                    t_en = (t_obj.get("english") or "").strip()
                    t_ro = (t_obj.get("romaji") or "").strip()
                    if _match_title_tokens(clean, t_en) or _match_title_tokens(clean, t_ro) or _match_title_tokens(att, t_en) or _match_title_tokens(att, t_ro) or clean.lower() in t_en.lower() or clean.lower() in t_ro.lower():
                        try:
                            return int(m["idMal"])
                        except Exception:
                            pass
        except Exception:
            pass
    return 0



