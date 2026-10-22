"""Port alur browse-and-play hianime.at (terinspirasi cara kerja pemain CLI)."""
import os, sys, re, json, base64, html as htmlmod, threading, time as _time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import HI_BASE, HI_UA, XOR_KEY

SEARCH_API = HI_BASE + "/search?keyword={}"
EPISODES_API = HI_BASE + "/api/theme/episode/list/{}"
SERVERS_API = HI_BASE + "/api/theme/episode/servers?episodeId={}"
BROWSE_API = HI_BASE + "/browse"

# Negative cache:
#   _neg_cache        : host -> expires_at_epoch (host mati global, skip semua)
#   _neg_pair_cache   : (host|slug|ep) -> expires_at_epoch (host mati untuk episode
#                       spesifik, misal zokoanime 404 untuk anime baru)
# TTL default 1 jam. Per-(host,slug,ep) cache bikin request berikut langsung skip
# server yang tidak punya episode tsb, tanpa biaya probe network.
# Catatan: per Oct 2026, hls.dramahot.top (CDN ZokoAnime) sudah bisa dijangkau
# lagi (TLS handshake sukses, HTTP 404 untuk path dummy). Tidak masuk _DEAD_HOSTS.
# Kalau host mati lagi nanti, _mark_dead() akan menambahkannya otomatis via
# negative cache (lihat _probe_master()).
_DEAD_HOSTS = set()  # daftar host yang SELALU dianggap mati (skip probe).

_neg_lock = threading.Lock()
_neg_cache = {}        # host -> expires_at_epoch
_neg_pair_cache = {}   # "host|slug|ep" -> expires_at_epoch


def _is_dead_host(host):
    base = (host or "").lower()
    for d in _DEAD_HOSTS:
        if d in base:
            return True
    with _neg_lock:
        exp = _neg_cache.get(base)
        if exp and exp > _time.time():
            return True
    return False


def _is_dead_pair(host, slug, ep):
    """Cek negative cache per-(host, slug, ep)."""
    base = (host or "").lower()
    key = f"{base}|{slug or ''}|{ep}"
    with _neg_lock:
        exp = _neg_pair_cache.get(key)
        return bool(exp and exp > _time.time())


def _mark_dead(host, ttl=300):
    base = (host or "").lower()
    with _neg_lock:
        _neg_cache[base] = int(_time.time()) + ttl


def _mark_dead_pair(host, slug, ep, ttl=600):
    """Tandai (host, slug, ep) gagal. Request berikut skip tanpa probe (TTL 10 menit agar pulih jika CDN update)."""
    base = (host or "").lower()
    key = f"{base}|{slug or ''}|{ep}"
    with _neg_lock:
        _neg_pair_cache[key] = int(_time.time()) + ttl


def _host_from(url):
    m = re.match(r"https?://([^/]+)", url or "", re.I)
    return m.group(1).lower() if m else ""


_BLOCKED_DPI_HOSTS = {"hls.dramahot.top", "drama1.cfd", "hls1.drama1.cfd", "puterin.biz", "putarin.xyz", "stream121.space"}
_BLOCKED_DPI_KEYWORDS = ("dramahot", "drama1", "zokoanime", "puterin", "putarin", "stream121")


def _is_dpi_blocked_host(host: str) -> bool:
    if not host:
        return False
    h = host.lower()
    if h in _BLOCKED_DPI_HOSTS:
        return True
    return any(k in h for k in _BLOCKED_DPI_KEYWORDS)


def _probe_master(master_url, referer):
    """Probe cepat master.m3u8:
    100% Direct TCP port 443 tanpa VPN.
    Bypass DPI ISP menggunakan TLS Client-Hello record fragmentation (desync)."""
    if not master_url or not master_url.startswith("http"):
        raise RuntimeError("invalid master url")
    host = _host_from(master_url)
    if _is_dead_host(host):
        raise RuntimeError(f"host dead: {host}")
    headers = {"User-Agent": HI_UA,
               **({"Referer": referer} if referer else {})}
    
    # Jika host terdeteksi diblokir DPI ISP, gunakan TLS desync langsung
    if _is_dpi_blocked_host(host):
        try:
            from api.desync import tls_desync_request
            content = tls_desync_request(master_url, headers=headers, timeout=8.0)
            if content and b"#EXTM3U" in content:
                return content
        except Exception:
            pass

    # Direct connection biasa untuk semua host normal
    try:
        try:
            from curl_cffi import requests as creq
            kw = dict(headers=headers, impersonate="chrome124", timeout=10)
            r = creq.get(master_url, **kw)
        except Exception:
            import httpx
            r = httpx.get(master_url, headers=headers, timeout=10, follow_redirects=True)
        if r.status_code == 200 and r.content:
            return r.content
        if r.status_code >= 400:
            raise RuntimeError(f"upstream {r.status_code} for {host}")
    except Exception as e:
        err_str = str(e).lower()
        is_known_dpi = any(k in host for k in ("dramahot", "zokoanime"))
        is_rst = any(w in err_str for w in ("reset", "ssl", "recv failure"))
        if is_known_dpi or is_rst:
            _BLOCKED_DPI_HOSTS.add(host)
            try:
                from api.desync import tls_desync_request
                content = tls_desync_request(master_url, headers=headers, timeout=8.0)
                if content and b"#EXTM3U" in content:
                    return content
            except Exception:
                pass
        _mark_dead(host)
        raise RuntimeError(f"probe fail {host}: {type(e).__name__}")

FILTERS = {
    "type": ["tv", "movie", "ova", "ona", "special", "music"],
    "status": ["releasing", "completed", "not_yet_aired", "currently_airing", "airing", "ongoing"],
    "rating": ["g", "pg", "pg_13", "r_17", "r_plus", "rx"],
    "score": ["10", "9", "8", "7", "6", "5", "4", "3", "2", "1"],
    "season": ["spring", "summer", "fall", "winter"],
    "language": ["sub", "dub"],
    "sort": ["popularity", "trending", "score", "latest", "az", "most_favorite"],
}


def scrape_genres():
    """Ambil list genre dari sidebar widget hianime /browse. Return [{slug,title}]."""
    html = _fetch(BROWSE_API)
    out, seen = [], set()
    for m in re.finditer(
        r'<a href="https?://hianime\.at/genres/([a-z0-9-]+)"\s+title="([^"]+)"',
        html):
        slug = m.group(1).lower()
        title = htmlmod.unescape(m.group(2)).strip()
        if slug in seen or not slug or not title:
            continue
        # Sembunyikan genre hentai dari list
        if slug == "hentai" or "hentai" in title.lower():
            continue
        seen.add(slug)
        out.append({"slug": slug, "title": title})
    return out


def browse(params: dict = None, page: int = 1):
    """GET /browse?{filter} — kartu + total halaman. Maksimal sesuai form filter."""
    from urllib.parse import urlencode
    q = dict(params or {})
    q["page"] = max(1, int(page or 1))
    clean = {}
    for k, v in q.items():
        if k == "page":
            clean[k] = v
            continue
        v = str(v or "").strip().lower()
        if not v:
            continue
        if k == "status" and v in ("currently_airing", "airing", "ongoing"):
            v = "releasing"
        if k in FILTERS and v in FILTERS[k]:
            clean[k] = v
        elif k in ("keyword", "sy", "sm", "ey", "em", "genre"):
            clean[k] = v
    if clean.get("genre") == "hentai" or "hentai" in str(clean.get("genre", "")):
        return {"items": [], "page": clean["page"], "total_pages": 1, "params": clean}
    url = BROWSE_API + "?" + urlencode(clean)
    page_html = _fetch(url)
    clean_html = page_html.split('id="sidebar"')[0].split('class="sidebar"')[0].split('id="main-sidebar"')[0]
    items = _parse_browse_cards(clean_html)
    last = 1
    for m in re.finditer(r"page=(\d+)", page_html):
        try:
            last = max(last, int(m.group(1)))
        except ValueError:
            pass
    return {"items": items, "page": clean["page"], "total_pages": last, "params": clean}


def _parse_browse_cards(html: str):
    # Pangkas sidebar agar kartu anime terakhir tidak menyerap metadata widget sidebar
    clean_html = html.split('id="sidebar"')[0].split('class="sidebar"')[0].split('id="main-sidebar"')[0]
    blocks = clean_html.split("flw-item")
    out = []
    for raw_b in blocks[1:]:
        c_end = raw_b.find('<div class="clearfix">')
        b = raw_b[:c_end] if c_end != -1 else raw_b[:3000]
        m = re.search(r"film-name.*?href=\"[^\"]*/([^\"]+)\"[^>]*title=\"([^\"]*)\"", b, re.S)
        if not m:
            continue
        slug = m.group(1)
        if slug.startswith("watch/"):
            slug = slug[len("watch/"):]
        title = _clean(m.group(2))
        if "hentai" in slug.lower() or "hentai" in title.lower():
            continue
        img = re.search(r"<img[^>]*src=\"([^\"]+)\"", b)
        poster = img.group(1) if img else ""
        sub = re.search(r"tick-sub.*?(\d+)<", b, re.S)
        dub = re.search(r"tick-dub.*?(\d+)<", b, re.S)
        eps = re.search(r"tick-eps.*?(\d+)<", b, re.S)
        typ = re.search(r"fdi-item\">(TV|Movie|OVA|ONA|Special|Music)<", b)
        dur = re.search(r"fdi-duration\">([^<]*)<", b)
        desc = re.search(r"class=\"description\">(.*?)</div>", b, re.S)
        sub_cnt = int(sub.group(1)) if sub else 0
        dub_cnt = int(dub.group(1)) if dub else 0
        eps_cnt = int(eps.group(1)) if eps else 0
        rel_cnt = sub_cnt if sub_cnt > 0 else (eps_cnt if eps_cnt > 0 else 0)
        tot_cnt = eps_cnt if eps_cnt > 0 else 0
        if tot_cnt > 0:
            cnt_str = f"{rel_cnt}/{tot_cnt}"
        elif rel_cnt > 0:
            cnt_str = f"{rel_cnt}/?"
        else:
            cnt_str = ""
        is_fin = (tot_cnt > 0 and rel_cnt >= tot_cnt)
        out.append({
            "id": slug, "title": title,
            "poster": poster,
            "sub": sub_cnt,
            "dub": dub_cnt,
            "eps": eps_cnt,
            "eps_released": rel_cnt,
            "eps_total": tot_cnt,
            "eps_counter": cnt_str,
            "type": typ.group(1) if typ else "",
            "duration": _clean(dur.group(1)) if dur else "",
            "synopsis": _clean(re.sub(r"<[^>]+>", "", desc.group(1)))[:220] if desc else "",
            "is_finished": is_fin,
            "status": "finished" if is_fin else "releasing",
            "badge": "TAMAT" if is_fin else ("ONGOING" if rel_cnt > 0 else ""),
        })
    return out

def hianime_synopsis(slug: str) -> str:
    """Ambil sinopsis anime dari halaman detail HiAnime jika ada."""
    d = hianime_details(slug)
    return d.get("synopsis", "")

def hianime_details(slug: str) -> dict:
    """Ambil metadata detail lengkap (sinopsis, skor, genre, studio, status, durasi, musim) dari halaman film HiAnime."""
    out = {
        "synopsis": "",
        "score": 0.0,
        "status": "",
        "season": "",
        "year": 0,
        "duration": "",
        "studio": "",
        "genres": [],
        "source": "",
        "poster": ""
    }
    try:
        if not slug or "hentai" in slug.lower():
            return out
        html_txt = _fetch(HI_BASE + "/" + slug)
        if not html_txt:
            return out
        import html as _html

        # Poster
        m_post = re.search(r'class="film-poster-img"[^>]*src="([^"]+)"', html_txt)
        if not m_post:
            m_post = re.search(r'class="film-poster"[^>]*>.*?<img[^>]*src="([^"]+)"', html_txt, re.S)
        if m_post:
            out["poster"] = m_post.group(1).strip()

        # Synopsis
        m = re.search(r'class="film-description[^\"]*"[^>]*>(.*?)</div>', html_txt, re.S)
        if not m:
            m = re.search(r'class="description[^\"]*"[^>]*>(.*?)</div>', html_txt, re.S)
        if m:
            clean = re.sub(r'<br\s*/?>', '\n', m.group(1), flags=re.I)
            clean = re.sub(r'<[^>]+>', '', clean).strip()
            out["synopsis"] = _html.unescape(clean)

        # Score
        m_score = re.search(r'class="item-head">MAL Score:</span>\s*<span[^>]*class="name"[^>]*>([^<]+)</span>', html_txt)
        if m_score:
            try:
                out["score"] = float(m_score.group(1).strip())
            except ValueError:
                pass

        # Status
        m_stat = re.search(r'class="item-head">Status:</span>\s*<span[^>]*class="name"[^>]*>([^<]+)</span>', html_txt)
        if m_stat:
            out["status"] = m_stat.group(1).strip()

        # Premiered / Season / Year
        m_prem = re.search(r'class="item-head">Premiered:</span>\s*<span[^>]*class="name"[^>]*>([^<]+)</span>', html_txt)
        if not m_prem:
            m_prem = re.search(r'class="item-head">Premiered:</span>\s*<a[^>]*>([^<]+)</a>', html_txt)
        if m_prem:
            out["season"] = m_prem.group(1).strip()
            m_yr = re.search(r'\b(19\d\d|20\d\d)\b', out["season"])
            if m_yr:
                try:
                    out["year"] = int(m_yr.group(1))
                except Exception:
                    pass

        # Fallback Aired jika Premiered / Season kosong
        if not out.get("season"):
            m_aired = re.search(r'class="item-head">Aired:</span>\s*<span[^>]*class="name"[^>]*>([^<]+)</span>', html_txt)
            if not m_aired:
                m_aired = re.search(r'class="item-head">Aired:</span>\s*<a[^>]*>([^<]+)</a>', html_txt)
            if m_aired:
                aired_str = m_aired.group(1).strip()
                m_yr = re.search(r'\b(19\d\d|20\d\d)\b', aired_str)
                yr = int(m_yr.group(1)) if m_yr else 0
                if yr:
                    out["year"] = yr
                    m_mth = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*', aired_str, re.I)
                    if m_mth:
                        m_str = m_mth.group(1).title()
                        month_seasons = {
                            "Jan": "Winter", "Feb": "Winter", "Mar": "Winter",
                            "Apr": "Spring", "May": "Spring", "Jun": "Spring",
                            "Jul": "Summer", "Aug": "Summer", "Sep": "Summer",
                            "Oct": "Fall", "Nov": "Fall", "Dec": "Fall"
                        }
                        s_name = month_seasons.get(m_str, "")
                        if s_name:
                            out["season"] = f"{s_name} {yr}"
                        else:
                            out["season"] = str(yr)
                    else:
                        out["season"] = str(yr)

        # Duration
        m_dur = re.search(r'class="item-head">Duration:</span>\s*<span[^>]*class="name"[^>]*>([^<]+)</span>', html_txt)
        if m_dur:
            out["duration"] = m_dur.group(1).strip()

        # Studios
        studios = []
        m_stu = re.search(r'class="item-head">Studios?:</span>\s*(.*?)(?:</div>|<span class="item-head")', html_txt, re.S)
        if m_stu:
            for s in re.finditer(r'<a[^>]*class="name"[^>]*>([^<]+)</a>', m_stu.group(1)):
                studios.append(s.group(1).strip())
        if studios:
            out["studio"] = ", ".join(studios)

        # Genres
        genres = []
        m_gen = re.search(r'class="item-head">Genres?:</span>\s*(.*?)(?:</div>|<span class="item-head")', html_txt, re.S)
        if m_gen:
            for g in re.finditer(r'<a[^>]*href="[^\"]*/genres/[^\"]*"[^>]*>([^<]+)</a>', m_gen.group(1)):
                gtxt = g.group(1).strip()
                if gtxt.lower() != 'hentai' and gtxt not in genres:
                    genres.append(gtxt)
        if genres:
            out["genres"] = genres

    except Exception:
        pass
    return out

def _failover_proxies():
    """Direct dulu, warp proxy hanya failover. Urutan: [tanpa proxy, warp proxy]."""
    import os
    out = [None]
    host = os.getenv("WARP_PROXY", "").strip()
    if host:
        if "://" not in host:
            host = "http://" + host
        out.append({"http": host, "https": host})
    return out


_shared_client = None

def _get_shared_client():
    global _shared_client
    if _shared_client is None:
        import httpx
        limits = httpx.Limits(max_connections=30, max_keepalive_connections=15, keepalive_expiry=60.0)
        _shared_client = httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(12.0, connect=5.0),
            limits=limits,
            headers={
                "User-Agent": HI_UA,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1"
            }
        )
    return _shared_client


def close_shared_client():
    """Tutup shared client HiAnime saat aplikasi shutdown."""
    global _shared_client
    if _shared_client is not None:
        try:
            _shared_client.close()
        except Exception:
            pass
        _shared_client = None


def _fetch(url, referer=None, timeout=12):
    last_err = ""
    # 1. Coba via curl_cffi impersonate Chrome jika tersedia di lingkungan
    for px in _failover_proxies():
        try:
            from curl_cffi import requests as creq
            try:
                kw = dict(
                    headers={"User-Agent": HI_UA, "Accept": "text/html,application/json,*/*", **({"Referer": referer} if referer else {})},
                    impersonate="chrome124",
                    timeout=timeout
                )
                if px:
                    kw["proxies"] = px
                r = creq.get(url, **kw)
                if r.status_code == 200:
                    return r.text
                if "Just a moment" in r.text or "cf-challenge" in r.text:
                    last_err = "Blocked by cloudflare (cf-challenge)."
                    continue
                last_err = f"HTTP {r.status_code} from {url}"
                continue
            except Exception as e:
                last_err = str(e)
                continue
        except ImportError:
            last_err = "curl_cffi missing"
            break

    # 2. Coba via persistent httpx pool
    try:
        client = _get_shared_client()
        h = {"Referer": referer} if referer else {}
        r = client.get(url, headers=h, timeout=timeout)
        if r.status_code == 200:
            if "Just a moment" in r.text or "cf-challenge" in r.text:
                last_err = "Blocked by cloudflare (cf-challenge)."
            else:
                return r.text
        else:
            last_err = f"HTTP {r.status_code} from {url}"
    except Exception as e:
        last_err = str(e)

    # 3. Fallback: TLS Desync request (bypass DPI ISP block)
    # Jangan desync jika error-nya timeout pada pemanggilan timeout pendek (hemat latensi failover server)
    is_timeout = any(t in last_err.lower() for t in ("timeout", "timed out"))
    if not (is_timeout and timeout <= 6):
        try:
            from api.desync import tls_desync_request
            desync_to = min(float(timeout), 5.0) if is_timeout else float(timeout)
            raw = tls_desync_request(url, headers={"Referer": referer} if referer else {}, timeout=desync_to)
            txt = raw.decode("utf-8", errors="replace")
            if txt and ("<html" in txt.lower() or "{" in txt or "#EXTM3U" in txt):
                return txt
        except Exception:
            pass

    raise RuntimeError(f"Gagal memuat URL: {last_err or 'unknown error'}")

def deobfuscate_blob(b64: str) -> str:
    raw = base64.b64decode(b64.strip())
    return bytes(b ^ XOR_KEY[i % len(XOR_KEY)] for i, b in enumerate(raw)).decode("utf-8", errors="strict")

def _clean(s: str) -> str:
    return htmlmod.unescape(s or "").strip()

_SEARCH_ALIASES = {
    "ghost at school": "ghost stories",
    "ghost in school": "ghost stories",
    "ghosts at school": "ghost stories",
    "gakkou no kaidan": "ghost stories",
    "girls und panzer": "girls & panzer",
    "girls and panzer": "girls & panzer",
    "garupan": "girls & panzer",
}

def hianime_search_page(query: str, limit: int = 24, page: int = 1) -> dict:
    q_str = (query or "").strip()
    page = max(1, int(page or 1))
    if not q_str or q_str.lower() == "hentai" or "hentai" in q_str.lower().split():
        return {"results": [], "page": page, "total_pages": 1, "has_next": False}
    q_lower = q_str.lower()
    canonical = _SEARCH_ALIASES.get(q_lower)
    if not canonical:
        if "girls und panzer" in q_lower and "film" not in q_lower and "movie" not in q_lower:
            canonical = re.sub(r"\bgirls\s+und\s+panzer\b", "girls & panzer", q_str, flags=re.I)
        elif "girls and panzer" in q_lower and "film" not in q_lower and "movie" not in q_lower:
            canonical = re.sub(r"\bgirls\s+and\s+panzer\b", "girls & panzer", q_str, flags=re.I)
    q_val = canonical or q_str
    q_encoded = urllib.parse.quote_plus(q_val)
    url = f"{HI_BASE}/search?keyword={q_encoded}&page={page}" if page > 1 else SEARCH_API.format(q_encoded)
    page_html = _fetch(url)
    if "<title>Just a moment" in page_html:
        raise RuntimeError("Blocked by cloudflare.")
    clean_html = page_html.split('id="main-sidebar"')[0]
    out = _parse_browse_cards(clean_html)
    if out:
        out = [x for x in out if "hentai" not in (x.get("id") or "").lower() and "hentai" not in (x.get("title") or "").lower()]
    else:
        # Fallback jika layout flw-item tidak cocok
        out = []
        for m in re.finditer(r'<h3 class="film-name">\s*<a href="[^"]*/([^"/]*)"\s*title="([^"]*)"', clean_html):
            slug, title = m.group(1), _clean(m.group(2))
            if slug and title and (not limit or len(out) < limit):
                if "hentai" in slug.lower() or "hentai" in title.lower():
                    continue
                out.append({"id": slug, "title": title, "poster": ""})

    # Ekstraksi total halaman dari pagination links
    last = page
    for m in re.finditer(r"page=(\d+)", page_html):
        try:
            last = max(last, int(m.group(1)))
        except ValueError:
            pass
    has_next = (page < last) or bool(re.search(r'title="Next"', page_html))
    res_items = out[:limit] if (limit and limit > 0) else out
    return {
        "results": res_items,
        "page": page,
        "total_pages": last,
        "has_next": has_next
    }

def hianime_search(query: str, limit: int = 15, page: int = 1):
    return hianime_search_page(query, limit=limit, page=page).get("results", [])

_EPISODES_MEM_CACHE = {}
_EPISODES_MEM_TTL = 6 * 3600  # 6 jam

def hianime_episodes(slug: str):
    if "hentai" in (slug or "").lower():
        raise RuntimeError("Anime ini diblokir (genre hentai)")
    now = _time.time()
    cached = _EPISODES_MEM_CACHE.get(slug)
    if cached and (now - cached[0] < _EPISODES_MEM_TTL):
        return cached[1]

    numeric = slug.rsplit("-", 1)[-1]
    raw_page = _fetch(EPISODES_API.format(numeric))
    page = raw_page
    if not page.startswith("{") and "{" in page:
        page = page[page.find("{"):]
    if page.endswith("0\r\n\r\n"):
        page = page[:page.rfind("}") + 1]

    html = ""
    try:
        data = json.loads(page)
        html = data.get("html", "")
    except Exception:
        html = raw_page.replace("\\", "")

    eps = []
    for m in re.finditer(r'data-number="([0-9]+)"[^>]*?data-id="([0-9]+)"', html):
        eps.append({"ep": int(m.group(1)), "ep_id": m.group(2)})
    if not eps:
        # Fallback pola urutan alternatif jika struktur berubah
        for m in re.finditer(r'data-number="([^"]*)"[^>]*data-id="([0-9]+)"', html):
            try:
                ep_no = int(m.group(1))
            except ValueError:
                continue
            eps.append({"ep": ep_no, "ep_id": m.group(2)})

    seen = {}
    for e in eps:
        seen[e["ep"]] = e["ep_id"]
    result = [{"ep": k, "ep_id": v} for k, v in sorted(seen.items())]
    if result:
        _EPISODES_MEM_CACHE[slug] = (now, result)
    return result

def _parse_servers(html: str, mode: str):
    items = html.replace('\\"', '"').split("server-item")
    servers = []
    for it in items:
        if f'data-type="{mode}"' not in it:
            continue
        mh = re.search(r'data-hash="([^"]*)"', it)
        mn = re.search(r'data-server-name="([^"]*)"', it)
        if not mh:
            continue
        try:
            embed = base64.b64decode(mh.group(1)).decode("utf-8", errors="strict")
        except Exception:
            continue
        if not embed.startswith("http"):
            continue
        servers.append({"name": mn.group(1) if mn else "unknown", "embed": embed})
    def score(s):
        n, e = s["name"].lower(), s["embed"].lower()
        if "megaplay" in e:
            return 0
        if "zokoanime.video" in e:
            return 5
        if "zokoanime" in n:
            return 6
        return 9
    servers.sort(key=score)
    return servers

def _b64url_decode(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)


MEGA_KEY = b"i?LMTAx0Q6,:}50U" + b"\x00" * 16
MEGA_IV = b"W0;27ToaUpl_P%'c"

# SegmentDecrypt (newclient.min.js): segmen playlist berbentuk /segment/{token}
# -> AES-CBC decrypt token -> URL .ts asli. Key/IV tertanam di JS.
SEG_KEY = MEGA_KEY
SEG_IV = MEGA_IV
SEG_RE = re.compile(r"/segment/([A-Za-z0-9_-]+)")
# SegmentStrip: 252 byte pertama segmen dari host ini dibuang
STRIP_BYTES = 252
STRIP_RE = re.compile(r"ibyteimg\.com|tiktokcdn\.com|ipstatp\.com|yoot\.akirax\.buzz", re.I)


def _mega_decrypt(enc: str) -> str:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    raw = _b64url_decode(enc.strip())
    d = Cipher(algorithms.AES(MEGA_KEY), modes.CBC(MEGA_IV)).decryptor()
    pt = d.update(raw) + d.finalize()
    # strip PKCS7-ish padding
    pad = pt[-1] if pt else 0
    if 1 <= pad <= 16 and all(b == pad for b in pt[-pad:]):
        pt = pt[:-pad]
    return pt.decode("utf-8", errors="strict")


def _normalize_subtitles(raw_tracks, referer: str = ""):
    """Normalisasi track subtitle mentah (Megaplay 'tracks[]' / ZokoAnime 'subtitles')
    menjadi list[{label, lang, url, default}] yang siap kirim ke client.

    - Filter track yang bukan subtitle (kind=thumbnails, kind=video, dsb.).
    - Bersihkan URL track relatif jadi absolut.
    - Ekstrak bahasa dengan akurat (_label_to_lang).
    - JANGAN PERNAH izinkan track Arabic menjadi 'default' otomatis dari CDN.
    - Utamakan English (atau Indonesian jika ada) sebagai default track.
    """
    out = []
    if not raw_tracks or not isinstance(raw_tracks, list):
        return out
    # Helper: ubah URL relatif jadi absolut terhadap referer.
    def _abs(u):
        u = (u or "").strip()
        if not u:
            return ""
        if u.startswith("//"):
            # protocol-relative → pakai scheme dari referer (biasanya https).
            return "https:" + u
        if u.startswith("/") and referer:
            m = re.match(r"^(https?://[^/]+)", referer)
            if m:
                return m.group(1) + u
        return u
    for i, t in enumerate(raw_tracks):
        if not isinstance(t, dict):
            continue
        # Skip non-subtitle tracks (thumbnail, video, audio descriptions, dll.).
        kind = (t.get("kind") or "").lower()
        if kind and kind not in ("subtitles", "subtitle", "captions", "caption"):
            continue
        # Megaplay/Zokoanime kadang pakai 'src' atau 'file' untuk URL subtitle.
        url = _abs(t.get("src") or t.get("file") or t.get("url") or "")
        if not url or not url.startswith("http"):
            continue
        raw_label = (t.get("label") or t.get("lang") or t.get("language")
                     or f"Subtitle {i + 1}").strip()
        raw_default = bool(t.get("default"))

        # Ekstraksi bahasa: Dahulukan inferensi dari label asli agar dummy 'lang: en'
        # dari CDN upstream tidak membajak bahasa non-Inggris (seperti Czech/Danish pada ZokoAnime).
        inferred = _label_to_lang(raw_label)
        if not inferred:
            # Hanya infer dari field lang/srclang jika label tidak mengindikasikan bahasa non-Inggris
            if not any(k in raw_label.lower() for k in _NON_ENGLISH_KEYWORDS):
                inferred = (
                    _label_to_lang(t.get("lang") or "")
                    or _label_to_lang(t.get("language") or "")
                    or _label_to_lang(t.get("srclang") or "")
                )

        # Jika raw_label menyebut bahasa non-Inggris, jangan biarkan lang jatuh ke 'en'
        upstream_lang = (t.get("lang") or t.get("language") or t.get("srclang") or "").strip().lower()
        if any(k in raw_label.lower() for k in _NON_ENGLISH_KEYWORDS) and upstream_lang == "en":
            lang = inferred or ""
        else:
            lang = inferred or upstream_lang

        # Format label readable
        label = raw_label
        if len(label) <= 3 and label.lower() in _LANG_NAME:
            label = _LANG_NAME[label.lower()]
        elif lang in _LANG_NAME and (not label or label.lower().startswith("sub")):
            label = _LANG_NAME[lang]

        out.append({
            "label": label,
            "lang": lang,
            "url": url,
            "default": False,
            "raw_default": raw_default,
        })

    if not out:
        return out

    # Tetapkan tepat 1 track default:
    # Prioritas 1: Indonesian (jika ada native)
    # Prioritas 2: English track dengan upstream default == True (misal ZokoAnime)
    # Prioritas 3: Exact "English" label
    # Prioritas 4: Any English track (misal "English 2", "English [Signs & Songs]")
    # Prioritas 5: Track non-Arabic pertama
    # Prioritas 6: Track 0 jika semua track adalah Arabic
    def is_exact_en(o):
        lbl = (o.get("label") or "").strip().lower()
        l = (o.get("lang") or "").strip().lower()
        if any(k in lbl for k in _NON_ENGLISH_KEYWORDS):
            return False
        return lbl in ("english", "english [full]", "english (full)", "eng") or (l == "en" and lbl == "english")

    def is_any_en(o):
        lbl = (o.get("label") or "").strip().lower()
        l = (o.get("lang") or "").strip().lower()
        if any(k in lbl for k in _NON_ENGLISH_KEYWORDS):
            return False
        return l == "en" or "english" in lbl or lbl.startswith("eng")

    def is_id(o):
        l = (o.get("lang") or "").lower()
        lbl = (o.get("label") or "").lower()
        return l == "id" or "indonesia" in lbl or "bahasa" in lbl

    def is_ar(o):
        l = (o.get("lang") or "").lower()
        lbl = (o.get("label") or "").lower()
        return l == "ar" or "arabic" in lbl or "arab" in lbl

    def_track = next((o for o in out if is_id(o)), None)
    if not def_track:
        def_track = next((o for o in out if o.get("raw_default") and is_any_en(o)), None)
    if not def_track:
        def_track = next((o for o in out if is_exact_en(o)), None)
    if not def_track:
        def_track = next((o for o in out if is_any_en(o)), None)
    if not def_track:
        def_track = next((o for o in out if not is_ar(o)), None)
    if not def_track:
        def_track = out[0]

    def_track["default"] = True

    for item in out:
        item.pop("raw_default", None)

    return out


# Kata kunci bahasa non-Inggris untuk mencegah dummy 'lang: en' dari CDN upstream
# salah diidentifikasi sebagai track bahasa Inggris.
_NON_ENGLISH_KEYWORDS = (
    "arabic", "arab", "indonesia", "bahasa", "spanish", "espanol", "español",
    "portuguese", "português", "french", "français", "francais", "german", "deutsch",
    "italian", "italiano", "korean", "chinese", "russian", "thai", "vietnamese",
    "turkish", "hindi", "czech", "danish", "dutch", "finnish", "greek",
    "hungarian", "norwegian", "polish", "romanian", "slovak", "swedish",
    "malay", "tagalog", "filipino", "ukrainian", "bulgarian", "croatian",
    "japanese", "japan",
)

# Peta kode bahasa 2-3 char → nama readable (untuk label dropdown).
_LANG_NAME = {
    "en": "English", "eng": "English",
    "id": "Indonesian", "ind": "Indonesian",
    "ja": "Japanese", "jpn": "Japanese",
    "es": "Spanish", "spa": "Spanish",
    "pt": "Portuguese", "por": "Portuguese",
    "fr": "French", "fra": "French", "fre": "French",
    "de": "German", "deu": "German", "ger": "German",
    "it": "Italian", "ita": "Italian",
    "ko": "Korean", "kor": "Korean",
    "zh": "Chinese", "chi": "Chinese", "zho": "Chinese",
    "ar": "Arabic", "ara": "Arabic",
    "ru": "Russian", "rus": "Russian",
    "th": "Thai", "tha": "Thai",
    "vi": "Vietnamese", "vie": "Vietnamese",
    "tr": "Turkish", "tur": "Turkish",
    "hi": "Hindi", "hin": "Hindi",
    "cs": "Czech", "ces": "Czech", "cze": "Czech",
    "da": "Danish", "dan": "Danish",
    "nl": "Dutch", "nld": "Dutch", "dut": "Dutch",
    "fi": "Finnish", "fin": "Finnish",
    "el": "Greek", "ell": "Greek", "gre": "Greek",
    "hu": "Hungarian", "hun": "Hungarian",
    "no": "Norwegian", "nor": "Norwegian", "nob": "Norwegian",
    "pl": "Polish", "pol": "Polish",
    "ro": "Romanian", "ron": "Romanian", "rum": "Romanian",
    "sk": "Slovak", "slk": "Slovak", "slo": "Slovak",
    "sv": "Swedish", "swe": "Swedish",
    "ms": "Malay", "msa": "Malay", "may": "Malay",
    "tl": "Tagalog", "fil": "Filipino",
    "uk": "Ukrainian", "ukr": "Ukrainian",
    "bg": "Bulgarian", "bul": "Bulgarian",
    "hr": "Croatian", "hrv": "Croatian",
}


def _label_to_lang(label):
    """Infer kode bahasa 2 huruf dari label atau kode bahasa."""
    if not label:
        return ""
    lab = (label or "").strip().lower()
    if not lab:
        return ""
    if "english" in lab or lab.startswith("eng") or lab == "en":
        return "en"
    if "indonesia" in lab or "bahasa" in lab or lab.startswith("ind") or lab == "id":
        return "id"
    if "japanese" in lab or lab.startswith("jpn") or lab == "ja":
        return "ja"
    if "arabic" in lab or lab.startswith("ara") or lab == "ar":
        return "ar"
    if "spanish" in lab or lab.startswith("spa") or lab == "es":
        return "es"
    if "portuguese" in lab or lab.startswith("por") or lab == "pt":
        return "pt"
    if "french" in lab or lab.startswith("fra") or lab.startswith("fre") or lab == "fr":
        return "fr"
    if "german" in lab or lab.startswith("ger") or lab.startswith("deu") or lab == "de":
        return "de"
    if "italian" in lab or lab.startswith("ita") or lab == "it":
        return "it"
    if "korean" in lab or lab.startswith("kor") or lab == "ko":
        return "ko"
    if "chinese" in lab or lab.startswith("chi") or lab.startswith("zho") or lab == "zh":
        return "zh"
    if "russian" in lab or lab.startswith("rus") or lab == "ru":
        return "ru"
    if "thai" in lab or lab.startswith("tha") or lab == "th":
        return "th"
    if "vietnamese" in lab or lab.startswith("vie") or lab == "vi":
        return "vi"
    if "turkish" in lab or lab.startswith("tur") or lab == "tr":
        return "tr"
    if "hindi" in lab or lab.startswith("hin") or lab == "hi":
        return "hi"
    if "czech" in lab or lab.startswith("cze") or lab.startswith("ces") or lab == "cs":
        return "cs"
    if "danish" in lab or lab.startswith("dan") or lab == "da":
        return "da"
    if "dutch" in lab or lab.startswith("nld") or lab.startswith("dut") or lab == "nl":
        return "nl"
    if "finnish" in lab or lab.startswith("fin") or lab == "fi":
        return "fi"
    if "greek" in lab or lab.startswith("ell") or lab.startswith("gre") or lab == "el":
        return "el"
    if "hungarian" in lab or lab.startswith("hun") or lab == "hu":
        return "hu"
    if "norwegian" in lab or lab.startswith("nor") or lab.startswith("nob") or lab == "no":
        return "no"
    if "polish" in lab or lab.startswith("pol") or lab == "pl":
        return "pl"
    if "romanian" in lab or lab.startswith("ron") or lab.startswith("rum") or lab == "ro":
        return "ro"
    if "slovak" in lab or lab.startswith("slk") or lab.startswith("slo") or lab == "sk":
        return "sk"
    if "swedish" in lab or lab.startswith("swe") or lab == "sv":
        return "sv"
    if "malay" in lab or lab.startswith("msa") or lab.startswith("may") or lab == "ms":
        return "ms"
    if "tagalog" in lab or "filipino" in lab or lab.startswith("fil") or lab == "tl":
        return "tl"
    if "ukrainian" in lab or lab.startswith("ukr") or lab == "uk":
        return "uk"
    if "bulgarian" in lab or lab.startswith("bul") or lab == "bg":
        return "bg"
    if "croatian" in lab or lab.startswith("hrv") or lab == "hr":
        return "hr"
    return ""


def _try_megaplay(embed: str):
    """embed = https://megaplay.buzz/stream/s-2/{realid}/{sub|dub}.
    Flow (from newclient.min.js): GET embed page -> data-id -> GET
    /stream/getSourcesNew?id={data-id} (Referer=embed) -> {enc} ->
    AES-CBC decrypt -> {file: master.m3u8} + tracks[]."""
    page = _fetch(embed, referer="https://hianime.at/")
    m = re.search(r'data-id="(\d+)"', page)
    if not m:
        raise RuntimeError("megaplay data-id not found")
    data_id = m.group(1)
    origin = re.sub(r"^(https?://[^/]*).*", r"\1", embed)
    api_url = origin + f"/stream/getSourcesNew?id={data_id}"
    try:
        txt = _fetch(api_url, referer=embed)
    except Exception:
        txt = _fetch(origin + f"/stream/getSources?id={data_id}", referer=embed)
    cfg = json.loads(txt)
    master = ""
    if isinstance(cfg.get("sources"), list) and cfg["sources"]:
        master = cfg["sources"][0].get("file", "")
    elif isinstance(cfg.get("sources"), dict):
        master = cfg["sources"].get("file", "")
    if not master and cfg.get("enc"):
        dec = json.loads(_mega_decrypt(cfg["enc"]))
        master = dec.get("file", "")
    if not master:
        raise RuntimeError("getSources gave no file")
    # master may be relative
    if master.startswith("/"):
        master = origin + master

    master_host = _host_from(master)
    if master_host and _is_dead_host(master_host):
        raise RuntimeError(f"master cdn host dead: {master_host}")

    # Multi-subtitle: normalisasi seluruh tracks Megaplay untuk dropdown & pemilihan default
    subs = cfg.get("tracks") or []
    subtitles = _normalize_subtitles(subs, referer=origin + "/")
    default_track = next((s for s in subtitles if s.get("default")), subtitles[0] if subtitles else None)
    sub_url = default_track["url"] if default_track else None
    if sub_url:
        sub_url = _validate_sub_url(sub_url, referer=origin + "/")
    sub_lang = default_track["label"] if default_track else None

    variants = []
    text = ""
    try:
        text = _fetch_media(master, referer=origin + "/", timeout=5.0)
        base = master.rsplit("/", 1)[0] + "/"
        lines = text.splitlines()
        for i, ln in enumerate(lines):
            if ln.startswith("#EXT-X-STREAM-INF"):
                rm = re.search(r"RESOLUTION=\d+x(\d+)", ln)
                q = (rm.group(1) + "p") if rm else "auto"
                url = (lines[i + 1].strip() if i + 1 < len(lines) else "")
                if url and not url.startswith("#"):
                    if not url.startswith("http"):
                        url = base + url
                    variants.append({"q": q, "url": url})
    except Exception as e:
        if master_host:
            _mark_dead(master_host, ttl=600)
        raise RuntimeError(f"megaplay master: {e}")
    variants.sort(key=lambda v: int(re.sub(r"\D", "", v["q"]) or 0), reverse=True)
    if not variants:
        variants = [{"q": "auto", "url": master}]
    if "#EXTM3U" not in text:
        raise RuntimeError("megaplay playlist: not m3u8")

    intro = cfg.get("intro") or {"start": 0, "end": 0}
    outro = cfg.get("outro") or {"start": 0, "end": 0}

    return {"master": master, "variants": variants,
            "sub": sub_url,
            "sub_lang": sub_lang,
            "referer": origin + "/", "mal_id": "",
            "tracks": subs,
            "subtitles": subtitles,
            "intro": intro,
            "outro": outro}

def _order_servers(servers):
    def score(s):
        n, e = s["name"].lower(), s["embed"].lower()
        # Megaplay dulu: lebih stabil & tidak bergantung CDN dramahot.top.
        if "megaplay" in e:
            return 0
        if "zokoanime.video" in e:
            return 5
        if "zokoanime" in n:
            return 6
        return 9
    return sorted(servers, key=score)


def _fetch_media(url: str, referer: str = None, timeout: int = 10) -> str:
    """Fetch teks/playlist/sub:
    - Host biasa: 100% direct.
    - Host terblokir ISP: bypass via TLS desync tanpa VPN."""
    host = _host_from(url)
    headers = {"User-Agent": HI_UA, **({"Referer": referer} if referer else {})}
    if _is_dpi_blocked_host(host):
        try:
            from api.desync import tls_desync_request
            b = tls_desync_request(url, headers=headers, timeout=timeout)
            if b:
                return b.decode("utf-8", errors="ignore")
        except Exception:
            pass
    try:
        from curl_cffi import requests as creq
        kw = dict(headers=headers, impersonate="chrome124", timeout=timeout)
        r = creq.get(url, **kw)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return _fetch(url, referer=referer, timeout=timeout)


def _validate_master_playlist(master_url: str, referer: str, variants: list, body_content=None):
    """Validasi master playlist: harus (a) mulainya #EXTM3U, (b) minimal ada 1
    URL segment/variant pada body. Return list variants yang sudah tervalidasi:
    - Kalau caller sudah punya variants dan minimal 1 URL absolute → pakai itu.
    - Kalau tidak, fallback ke single-variant dari master playlist.
    Raise RuntimeError kalau playlist tidak punya konten yang bisa diputar."""
    if not master_url or not master_url.startswith("http"):
        raise RuntimeError("invalid master url")
    if body_content:
        body = body_content
    else:
        body = _fetch_media(master_url, referer=referer, timeout=8.0)
    txt = body if isinstance(body, str) else body.decode("utf-8", errors="ignore")
    if "#EXTM3U" not in txt:
        raise RuntimeError("master playlist: not m3u8")
    # Hitung jumlah stream-inf / segment lines yang valid, dan ekstrak variants jika ada STREAM-INF
    base = master_url.rsplit("/", 1)[0] + "/"
    valid_count = 0
    parsed_variants = []
    lines = txt.splitlines()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("#"):
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
                        import urllib.parse as _up
                        v_url = _up.urljoin(master_url, v_url)
                    parsed_variants.append({"q": q, "url": v_url})
            continue
        # Absolute atau relative URL ke segment/variant playlist.
        if s.startswith("http") or "/" in s or s.endswith(".m3u8") or s.endswith(".ts"):
            valid_count += 1
    if valid_count == 0 and not parsed_variants:
        raise RuntimeError("master playlist: no segments")
    # Urutkan parsed variants dari resolusi tertinggi ke terendah
    if parsed_variants:
        parsed_variants.sort(key=lambda v: int(re.sub(r"\D", "", v["q"]) or 0), reverse=True)

    # Caller punya variants (misal multi-bitrate dari megaplay) → filter URL valid.
    if variants:
        out = [v for v in variants if v.get("url", "").startswith("http")]
        if out and len(out) > 1:
            return out
        if out and out[0].get("q") != "auto" and not parsed_variants:
            return out

    if parsed_variants:
        return parsed_variants

    # Single-variant fallback: pakai master playlist langsung.
    return [{"q": "auto", "url": master_url}]



def _validate_sub_url(sub_url: str, referer: str):
    """Soft-validasi subtitle URL:
    Untuk CDN terpercaya (megaplay, broforgotsave, stellarfrontier, megacloud, dsb),
    langsung return URL agar tidak menambah latency berlebih saat resolve.
    Untuk host lainnya, lakukan validasi cepat."""
    if not sub_url or not sub_url.startswith("http"):
        return None
    try:
        host = _host_from(sub_url)
        if any(k in host for k in ("megaplay", "broforgotsave", "stellarfrontier", "megacloud", "akamaized", "rabbitstream")):
            return sub_url
        headers = {"User-Agent": HI_UA, **({"Referer": referer} if referer else {})}
        if _is_dpi_blocked_host(host):
            from api.desync import tls_desync_request
            b = tls_desync_request(sub_url, headers=headers, timeout=4.0)
            if b and len(b) >= 10:
                return sub_url
            return None
        try:
            from curl_cffi import requests as creq
            kw = dict(headers=headers, impersonate="chrome124", timeout=5)
            r = creq.get(sub_url, **kw)
            if r.status_code == 200 and r.content and len(r.content) >= 10:
                return sub_url
            return None
        except Exception:
            import httpx
            with httpx.Client(timeout=5, follow_redirects=True, headers=headers) as c:
                r = c.get(sub_url)
                if r.status_code == 200 and r.content and len(r.content) >= 10:
                    return sub_url
                if any(k in host for k in ("broforgotsave", "stellarfrontier", "megaplay")):
                    headers["Referer"] = "https://megaplay.buzz/"
                    r2 = c.get(sub_url, headers=headers)
                    if r2.status_code == 200 and r2.content and len(r2.content) >= 10:
                        return sub_url
                return None
    except Exception:
        return None


def _try_embed_legacy(embed: str):
    referer = re.sub(r"^(https?://[^/]*).*", r"\1/", embed)
    page = _fetch(embed)
    # Deteksi halaman 404 ZokoAnime (server return HTML page, bukan markdown())
    # Page signature: ada "<title>Player</title>" + "Not" + "found." pada body.
    # Skip regex window.__P kalau 404 — raise sebagai "anime not on server"
    # sehingga caller skip server ini (jangan fallback dalam loop yang sama).
    if "<title>Player</title>" in page and "Not " in page and "found." in page:
        raise RuntimeError("404 page (anime not on server)")
    m = re.search(r'window\.__P\s*=\s*"([^"]*)"', page)
    if not m:
        raise RuntimeError("window.__P not found")
    try:
        cfg = json.loads(deobfuscate_blob(m.group(1)))
    except Exception:
        raise RuntimeError("deobfuscate failed")
    master = cfg.get("src") or ""
    if not master and isinstance(cfg.get("sources"), list) and cfg["sources"]:
        master = cfg["sources"][0].get("src", "")
    if ".m3u8" not in master:
        return None
    # Probe master — kalau host mati, return None agar caller fall-through.
    probe_content = None
    try:
        probe_content = _probe_master(master, referer=referer)
    except Exception as e:
        raise RuntimeError(f"zokoanime probe: {e}")
    # Multi-subtitle: normalisasi seluruh tracks ZokoAnime untuk dropdown & pemilihan default
    subs = cfg.get("subtitles") or []
    subtitles = _normalize_subtitles(subs, referer=referer)
    default_track = next((s for s in subtitles if s.get("default")), subtitles[0] if subtitles else None)
    sub_url = default_track["url"] if default_track else None
    if sub_url:
        sub_url = _validate_sub_url(sub_url, referer=referer)
    sub_lang = default_track["label"] if default_track else None

    try:
        variants = _validate_master_playlist(master, referer=referer, variants=[], body_content=probe_content)
    except Exception as e:
        raise RuntimeError(f"zokoanime playlist: {e}")
    mal_id = ""
    mm = re.search(r"/mal/([0-9]+)/", embed)
    if mm:
        mal_id = mm.group(1)

    intro = cfg.get("intro") or {"start": 0, "end": 0}
    outro = cfg.get("outro") or {"start": 0, "end": 0}

    return {"master": master, "variants": variants,
            "sub": sub_url,
            "sub_lang": sub_lang,
            "referer": referer, "mal_id": mal_id,
            "subtitles": subtitles,
            "intro": intro,
            "outro": outro}


def _harvest_subtitles(servers, current_srv_name: str = ""):
    """Ambil track subtitle dari server alternatif jika server video utama tidak memiliki subtitle."""
    for srv in servers:
        if srv.get("name") == current_srv_name:
            continue
        host = _host_from(srv.get("embed", ""))
        if _is_dead_host(host):
            continue
        try:
            embed_low = (srv.get("embed") or "").lower()
            if "zokoanime.video" in embed_low or "vidtube.site" in embed_low or "vidplay" in srv.get("name", "").lower():
                alt_got = _try_embed_legacy(srv["embed"])
            else:
                alt_got = _try_megaplay(srv["embed"])
            if alt_got and alt_got.get("subtitles"):
                return {
                    "subtitles": alt_got["subtitles"],
                    "sub": alt_got.get("sub"),
                    "sub_lang": alt_got.get("sub_lang"),
                    "referer": alt_got.get("referer"),
                }
        except Exception:
            continue
    return None


def hianime_subtitles_for_episode(slug: str, ep_no: int) -> dict:
    """Ambil track subtitle softsub untuk episode tertentu tanpa perlu mengunduh master video m3u8.
    Berguna sebagai fallback untuk Otakudesu atau stream tanpa softsub.
    """
    try:
        maps = hianime_episodes(slug)
        ep_id = None
        for e in maps:
            if int(e.get("ep", -1)) == int(ep_no):
                ep_id = e.get("ep_id")
                break
        if not ep_id:
            return {"subtitles": [], "sub": None, "sub_lang": None}
        servers_html = _fetch(SERVERS_API.format(ep_id))
        sub_servers = _order_servers(_parse_servers(servers_html, "sub"))
        harvested = _harvest_subtitles(sub_servers)
        if not harvested:
            dub_servers = _order_servers(_parse_servers(servers_html, "dub"))
            harvested = _harvest_subtitles(dub_servers)
        return harvested or {"subtitles": [], "sub": None, "sub_lang": None}
    except Exception:
        return {"subtitles": [], "sub": None, "sub_lang": None}


def hianime_m3u8(episode_maps, ep_no: int, mode: str = "sub", slug: str = ""):
    req_mode = "dub" if str(mode).lower() == "dub" else "sub"
    ep_id = None
    for e in episode_maps:
        if int(e["ep"]) == int(ep_no):
            ep_id = e["ep_id"]
            break
    if not ep_id:
        raise RuntimeError(f"Episode {ep_no} not released!")
    servers_html = _fetch(SERVERS_API.format(ep_id))
    servers = _order_servers(_parse_servers(servers_html, req_mode))
    actual_mode = req_mode
    if not servers:
        # Fallback ke mode alternatif jika mode yang diminta tidak memiliki server sama sekali (misal anime dub-only atau sub-only)
        alt_mode = "dub" if req_mode == "sub" else "sub"
        alt_servers = _order_servers(_parse_servers(servers_html, alt_mode))
        if alt_servers:
            servers = alt_servers
            actual_mode = alt_mode

    if not servers:
        raise RuntimeError(f"No {req_mode} server found for ep {ep_no}")

    # Smart-fallback tier: megaplay dulu (HD-1, Vidstream-2), kalau gagal ke VidToglap
    # (vidtube.site), terakhir ke ZokoAnime.
    def tier_of(srv):
        e = srv["embed"].lower()
        if "megaplay" in e:
            return 0
        if "vidtube.site" in e:
            return 1
        if "zokoanime.video" in e:
            return 2
        return 3

    servers_sorted = sorted(servers, key=lambda sr: (tier_of(sr), sr["name"]))
    last_err = ""
    for srv in servers_sorted:
        host = _host_from(srv["embed"])
        # Skip host mati (global negative cache) tanpa re-fetch.
        if _is_dead_host(host):
            last_err = f"skip {srv['name']} (dead host)"
            continue
        # Skip per-(host, slug, ep): anime ini memang tidak ada di server ini
        # (misal ZokoAnime 404 untuk judul baru). Negative cache TTL 1 jam.
        if slug and _is_dead_pair(host, slug, ep_no):
            last_err = f"skip {srv['name']} (404 cached for ep {ep_no})"
            continue
        try:
            embed_low = srv["embed"].lower()
            if "zokoanime.video" in embed_low:
                got = _try_embed_legacy(srv["embed"])
            elif "vidtube.site" in embed_low or "vidplay" in srv["name"].lower():
                # VidPlay-1 (vidtube.site) juga pakai pola window.__P.
                got = _try_embed_legacy(srv["embed"])
            else:
                got = _try_megaplay(srv["embed"])
            if got:
                got["server"] = srv["name"]
                got["mode"] = actual_mode

                # Fallback Subtitle Tier 1 & 2:
                # Jika server video yang berhasil memutar video tidak memiliki subtitle (atau kosong):
                if not got.get("subtitles"):
                    # 1. Coba server alternatif di mode yang sama (Cross-Server)
                    alt_subs = _harvest_subtitles(servers_sorted, current_srv_name=srv["name"])
                    # 2. Jika masih kosong dan sedang mode DUB, pinjam dari mode SUB (Cross-Mode)
                    if not alt_subs and actual_mode == "dub":
                        sub_servers = _order_servers(_parse_servers(servers_html, "sub"))
                        alt_subs = _harvest_subtitles(sub_servers)
                    # 3. Jika masih kosong dan sedang mode SUB, pinjam dari mode DUB sebagai cadangan
                    if not alt_subs and actual_mode == "sub":
                        dub_servers = _order_servers(_parse_servers(servers_html, "dub"))
                        alt_subs = _harvest_subtitles(dub_servers)

                    if alt_subs:
                        got["subtitles"] = alt_subs["subtitles"]
                        got["sub"] = alt_subs.get("sub")
                        got["sub_lang"] = alt_subs.get("sub_lang")

                return got
            last_err = f"{srv['name']} gave no m3u8"
        except Exception as e:
            err_msg = str(e)
            last_err = f"{srv['name']}: {err_msg}"
            msg = err_msg.lower()
            # Tandai host mati kalau error-nya network (RST, ConnectError, probe fail).
            if any(t in msg for t in ("rst", "reset", "connect", "timeout", "dead", "upstream", "probe fail", "sslerror")):
                if "megaplay master" not in msg:
                    _mark_dead(host)
            # Tandai per-(host, slug, ep) kalau anime tidak ada di server ini.
            if any(t in msg for t in ("404 page", "not on server", "window.__p not found", "data-id not found")):
                if slug:
                    _mark_dead_pair(host, slug, ep_no)
            continue
    if "dramahot.top" in last_err.lower() or "zokoanime" in last_err.lower():
        raise RuntimeError(
            "Server video anime baru ini (ZokoAnime) diblokir DPI/ISP (hls.dramahot.top). "
            "Server utama (Megaplay) belum diunggah oleh penyedia. "
            "Aktifkan Cloudflare WARP (1.1.1.1) / VPN untuk memutar judul ini."
        )
    raise RuntimeError(last_err or "m3u8 not found")

def select_quality(variants, quality: str = "best"):
    if not variants:
        raise RuntimeError("no variants")
    q = (quality or "best").lower()
    if q == "best":
        return variants[0]
    if q == "worst":
        nums = [v for v in variants if re.match(r"^\d+", v["q"])]
        return nums[-1] if nums else variants[-1]
    for v in variants:
        if v["q"].lower() == q or v["q"].lower().startswith(q):
            return v
    return variants[0]
