import sys, os, re, time, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asyncio, subprocess, tempfile
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from config import APP_PORT, APP_HOST, HI_BASE, HI_UA
from database import init_db, get_search_cache, set_search_cache, get_episode_cache, get_episode_cache_modes, set_episode_cache, delete_episode_cache, clear_episode_cache_for_slug, get_cached_episode, cache_episode, add_history, get_history, clear_history, save_progress, get_progress, clear_progress, add_bookmark, remove_bookmark, get_bookmarks, is_bookmarked, clear_bookmarks, get_setting, get_settings_bulk, set_setting, get_browse_cache, set_browse_cache, get_slug_map, set_slug_map, get_mal_map, set_mal_map, get_subtitle_cache, set_subtitle_cache, delete_subtitle_cache, get_today_char_count, add_today_char_count
from api import hianime as hi
from api import anilist as al
from api import otakudesu as otaku
from api import aniskip
from api import anichan
import httpx

# ---------------------------------------------------------------------------
# Cache master m3u8 (body, bukan cuma URL).
#
# SEBELUMNYA master playlist diunduh DUA KALI per siklus putar:
#   1. Resolver (hianime.py) mengunduh master untuk mem-parse variants,
#      lalu body-nya dibuang.
#   2. Player (/api/player/video?url=<master>) mengunduh master LAGI dari CDN
#      hanya untuk menulis ulang URL segmen.
# Cache body master dengan TTL pendek eliminating round-trip kedua.
# ---------------------------------------------------------------------------
_MASTER_CACHE: dict = {}          # master_url -> (expires_at, text)
_MASTER_CACHE_TTL = 120           # 2 menit — playlist master relatif statis
_MASTER_CACHE_MAX = 64


def _master_cache_get(url: str):
    """Ambil body master m3u8 dari cache (None bila miss/expired)."""
    if not url:
        return None
    item = _MASTER_CACHE.get(url)
    if not item:
        return None
    exp, txt = item
    if exp < time.time():
        _MASTER_CACHE.pop(url, None)
        return None
    return txt


def _master_cache_set(url: str, text: str):
    """Simpan body master m3u8 ke cache dengan batas jumlah entri."""
    if not url or not text:
        return
    _MASTER_CACHE[url] = (time.time() + _MASTER_CACHE_TTL, text)
    if len(_MASTER_CACHE) > _MASTER_CACHE_MAX:
        for k in list(_MASTER_CACHE.keys())[:len(_MASTER_CACHE) - _MASTER_CACHE_MAX]:
            _MASTER_CACHE.pop(k, None)


# Failover per-judul: mapping slug -> sumber alternatif. Nilai SELALU "anichan".
# Dibatasi jumlah entri agar tidak tumbuh tanpa batas pada sesi panjang.
_ANIME_FAILOVER_CACHE: dict = {}
_ANIME_FAILOVER_MAX = 512


def _set_failover(slug: str, source: str = "anichan"):
    """Simpan sumber fallback per-judul dengan batas jumlah entri."""
    _ANIME_FAILOVER_CACHE[slug] = source
    if len(_ANIME_FAILOVER_CACHE) > _ANIME_FAILOVER_MAX:
        # Buang entri terlama (insertion order) sampai di bawah batas.
        for k in list(_ANIME_FAILOVER_CACHE.keys())[:len(_ANIME_FAILOVER_CACHE) - _ANIME_FAILOVER_MAX]:
            _ANIME_FAILOVER_CACHE.pop(k, None)


# Registry task background agar tidak di-GC sebelum selesai.
# asyncio hanya menyimpan reference lemah ke task yang dibuat via
# create_task(); tanpa registry ini task bisa hilang sebelum selesai.
_BACKGROUND_TASKS: set = set()


def _spawn_background(coro):
    """Jalankan coroutine di background dengan reference yang aman dari GC."""
    try:
        task = asyncio.create_task(coro)
    except Exception:
        return None
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return task

frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Bersihkan cache kedaluwarsa saat startup. Semua TTL di modul database
    # bersifat "ignore on read" — tanpa sweeper ini tabel cache (terutama
    # subtitle_cache yang menyimpan payload VTT utuh) tumbuh tanpa batas.
    try:
        from database import purge_expired_caches
        removed = await purge_expired_caches()
        total = sum(v for v in removed.values() if v)
        if total:
            print(f"[tatap] purge cache kedaluwarsa: {removed}", flush=True)
    except Exception:
        pass
    yield
    # Graceful shutdown: tutup connection pool video dan persistent client API
    global _direct_client
    if _direct_client is not None:
        try:
            await _direct_client.aclose()
        except Exception:
            pass
        _direct_client = None
    try:
        from database import close_db_pool
        await close_db_pool()
    except Exception:
        pass
    try:
        from api.anilist import close_al_client
        close_al_client()
    except Exception:
        pass
    try:
        from api.hianime import close_shared_client
        close_shared_client()
    except Exception:
        pass
    try:
        from api.otakudesu import close_otaku_client
        close_otaku_client()
    except Exception:
        pass
    try:
        from api.anichan import close_anichan_client
        close_anichan_client()
    except Exception:
        pass
    try:
        from api.translate import close_gtx_client
        close_gtx_client()
    except Exception:
        pass

from version import __version__ as CURRENT_VERSION
app = FastAPI(title="Tatap", version=CURRENT_VERSION, lifespan=lifespan)

def ok(data):
    return {"success": True, "data": data}
def fail(msg):
    return JSONResponse({"success": False, "error": msg}, status_code=200)

def _clean(s: str) -> str:
    return html.unescape(s or "").strip()

def _parse_safe_mode(val) -> int:
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        val = val.strip().lower()
        if val in ("0", "false", "off", "mati"):
            return 0
        return 1
    if hasattr(val, "default"):
        return _parse_safe_mode(val.default)
    return 1

@app.get("/api/ping")
async def ping():
    return ok({"status": "running"})

@app.get("/api/version")
async def get_version():
    return ok({"version": CURRENT_VERSION})

@app.get("/api/update/check")
async def check_update(force: bool = False):
    """Pemeriksaan pembaruan versi Tatap secara on-demand via GitHub Releases API & Multi-Tier Fallback.
    Memfilter 4 berkas resmi sesuai aturan paten agent.md:
    1. tatap-release-v<VER>.apk (Official Signed Mobile APK)
    2. tatap-tv-release-v<VER>.apk (Official Signed Android/Google TV APK)
    3. tatap-windows-x64-portable.zip (Windows Portable)
    4. Tatap-x86_64.AppImage (Linux AppImage)
    """
    cache_key = "github_latest_release"
    if not force:
        cached = await get_browse_cache(cache_key, ttl=300)
        if cached and isinstance(cached, dict):
            return ok(cached)

    def parse_ver(v_str):
        nums = []
        for part in (v_str or "").split("."):
            m = re.match(r"^\d+", part)
            nums.append(int(m.group(0)) if m else 0)
        return tuple(nums)

    def build_official_assets(ver_clean):
        tag = f"v{ver_clean}" if not ver_clean.startswith("v") else ver_clean
        base = f"https://github.com/asfaraguest/tatap/releases/download/{tag}"
        return {
            "android": f"{base}/tatap-release-{tag}.apk",
            "android_tv": f"{base}/tatap-tv-release-{tag}.apk",
            "windows": f"{base}/tatap-windows-x64-portable.zip",
            "linux": f"{base}/Tatap-x86_64.AppImage"
        }

    curr_clean = re.sub(r"^v", "", CURRENT_VERSION)
    headers = {
        "User-Agent": f"Tatap-App/{CURRENT_VERSION} (https://github.com/asfaraguest/tatap)",
        "Accept": "application/vnd.github.v3+json, text/html;q=0.9, */*;q=0.8"
    }

    out_payload = None
    err_detail = None

    # TIER 1: GitHub REST API
    try:
        url_api = "https://api.github.com/repos/asfaraguest/tatap/releases/latest"
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url_api, headers=headers)
        if resp.status_code == 200:
            rel_data = resp.json()
            tag_name = (rel_data.get("tag_name") or "").strip()
            latest_clean = re.sub(r"^v", "", tag_name)
            has_update = False
            try:
                has_update = parse_ver(latest_clean) > parse_ver(curr_clean)
            except Exception:
                has_update = latest_clean != curr_clean and bool(latest_clean)

            assets_out = {
                "android": "",
                "android_tv": "",
                "windows": "",
                "linux": ""
            }
            raw_assets = rel_data.get("assets") or []
            for a in raw_assets:
                fname = (a.get("name") or "").lower()
                dl_url = a.get("browser_download_url") or ""
                if "tatap-tv-release-" in fname and fname.endswith(".apk") and not fname.endswith(".idsig"):
                    assets_out["android_tv"] = dl_url
                elif "tatap-release-" in fname and fname.endswith(".apk") and not fname.endswith(".idsig"):
                    assets_out["android"] = dl_url
                elif "windows" in fname and fname.endswith(".zip"):
                    assets_out["windows"] = dl_url
                elif fname.endswith(".appimage"):
                    assets_out["linux"] = dl_url

            if not assets_out["android"]:
                assets_out = build_official_assets(latest_clean)

            notes_body = rel_data.get("body") or ""
            out_payload = {
                "current_version": CURRENT_VERSION,
                "latest_version": latest_clean or tag_name,
                "tag_name": tag_name,
                "has_update": has_update,
                "release_name": rel_data.get("name") or tag_name,
                "notes": notes_body,
                "body": notes_body,
                "published_at": rel_data.get("published_at") or "",
                "release_url": rel_data.get("html_url") or f"https://github.com/asfaraguest/tatap/releases/tag/{tag_name}",
                "assets": assets_out
            }
        else:
            err_detail = f"GitHub API HTTP {resp.status_code}"
    except Exception as e:
        err_detail = f"API: {str(e)}"

    # TIER 2: GitHub Web Releases Redirect (Bypasses API rate-limits 403 on CGNAT / cellular)
    if not out_payload:
        try:
            url_web = "https://github.com/asfaraguest/tatap/releases/latest"
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                r_web = await client.get(url_web, headers=headers)
            if r_web.status_code == 200:
                final_url = str(r_web.url)
                m = re.search(r"/tag/v?([0-9]+\.[0-9]+\.[0-9]+)", final_url)
                if m:
                    latest_clean = m.group(1)
                    tag_name = f"v{latest_clean}"
                    has_update = False
                    try:
                        has_update = parse_ver(latest_clean) > parse_ver(curr_clean)
                    except Exception:
                        has_update = latest_clean != curr_clean and bool(latest_clean)

                    html_text = r_web.text
                    notes_match = re.search(r'<div[^>]*class="[^"]*markdown-body[^"]*"[^>]*>(.*?)</div>', html_text, re.DOTALL)
                    notes_extracted = ""
                    if notes_match:
                        raw_html = notes_match.group(1)
                        notes_extracted = re.sub(r"<[^>]+>", "", raw_html).strip()

                    out_payload = {
                        "current_version": CURRENT_VERSION,
                        "latest_version": latest_clean,
                        "tag_name": tag_name,
                        "has_update": has_update,
                        "release_name": f"Tatap {tag_name}",
                        "notes": notes_extracted or f"Pembaruan rilis Tatap {tag_name} tersedia di GitHub.",
                        "body": notes_extracted or f"Pembaruan rilis Tatap {tag_name} tersedia di GitHub.",
                        "published_at": "",
                        "release_url": final_url,
                        "assets": build_official_assets(latest_clean)
                    }
        except Exception as e:
            if not err_detail:
                err_detail = f"Web: {str(e)}"

    # TIER 3: GitHub Raw Fastly CDN (VERSION & CHANGELOG.md)
    if not out_payload:
        try:
            url_raw_ver = "https://raw.githubusercontent.com/asfaraguest/tatap/main/VERSION"
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                r_raw = await client.get(url_raw_ver, headers=headers)
            if r_raw.status_code == 200 and r_raw.text.strip():
                latest_clean = r_raw.text.strip()
                tag_name = f"v{latest_clean}" if not latest_clean.startswith("v") else latest_clean
                latest_clean = re.sub(r"^v", "", latest_clean)
                has_update = False
                try:
                    has_update = parse_ver(latest_clean) > parse_ver(curr_clean)
                except Exception:
                    has_update = latest_clean != curr_clean and bool(latest_clean)

                out_payload = {
                    "current_version": CURRENT_VERSION,
                    "latest_version": latest_clean,
                    "tag_name": tag_name,
                    "has_update": has_update,
                    "release_name": f"Tatap {tag_name}",
                    "notes": f"Pembaruan rilis Tatap {tag_name} terdeteksi dari repositori resmi.",
                    "body": f"Pembaruan rilis Tatap {tag_name} terdeteksi dari repositori resmi.",
                    "published_at": "",
                    "release_url": f"https://github.com/asfaraguest/tatap/releases/tag/{tag_name}",
                    "assets": build_official_assets(latest_clean)
                }
        except Exception as e:
            if not err_detail:
                err_detail = f"Raw: {str(e)}"

    # TIER 4: Stale Cache Fallback (If all network calls fail)
    if not out_payload:
        try:
            cached_stale = await get_browse_cache(cache_key, ttl=86400 * 30)
            if cached_stale and isinstance(cached_stale, dict):
                cached_stale["cached"] = True
                return ok(cached_stale)
        except Exception:
            pass

    if out_payload:
        await set_browse_cache(cache_key, out_payload)
        return ok(out_payload)

    return fail(f"Gagal memeriksa update ({err_detail or 'Periksa koneksi internet Anda'}).")

@app.get("/api/health")
async def health():
    try:
        from curl_cffi import requests as creq
        r = creq.get(HI_BASE + "/", impersonate="chrome124", timeout=10)
        reachable = r.status_code < 500
    except Exception:
        try:
            r = httpx.get(HI_BASE + "/", timeout=10, follow_redirects=True, headers={"User-Agent": HI_UA})
            reachable = r.status_code < 500
        except Exception:
            reachable = False
    return ok({"hianime": HI_BASE, "reachable": reachable})

_META_STOPWORDS = {
    'the', 'a', 'an', 'of', 'in', 'to', 'and', 'und', 'der', 'die', 'das',
    'no', 'wa', 'ga', 'ni', 'de', 'part', 'season', 'arc', 'cour', 'hen',
    'chapter', 'edition', 'series', 'ver', 'version'
}

def _extract_season_from_title(t: str) -> int:
    t = (t or '').lower()
    m = re.search(r'\b(?:season|s)\s*(\d+)\b', t)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    m_roman = re.search(r'\b(ii|iii|iv|v|vi)\b', t)
    if m_roman:
        return {'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6}.get(m_roman.group(1), 1)
    return 1

def _clean_title_tokens_for_meta(t: str) -> set:
    t = (t or '').lower()
    t = re.sub(r'[^a-zA-Z0-9\s]', ' ', t)
    return {w for w in t.split() if w and w not in _META_STOPWORDS}

def _calculate_title_match_score(target: str, candidate: str) -> float:
    # 1. Exact normalized alphanumeric match
    norm_t = re.sub(r'[^a-zA-Z0-9]', '', target.lower())
    norm_c = re.sub(r'[^a-zA-Z0-9]', '', candidate.lower())
    if norm_t and norm_t == norm_c:
        return 1.0

    # 2. Season isolation (mencegah Season 2 match ke Season 1)
    s_t = _extract_season_from_title(target)
    s_c = _extract_season_from_title(candidate)
    if (s_t > 1 or s_c > 1) and s_t != s_c:
        return 0.0

    tok_t = _clean_title_tokens_for_meta(target)
    tok_c = _clean_title_tokens_for_meta(candidate)
    if not tok_t or not tok_c:
        return 0.0

    common = tok_t & tok_c
    if not common:
        return 0.0

    union = tok_t | tok_c
    jaccard = len(common) / len(union)

    # 3. Subtitle / Arc penalty: jika salah satu memiliki kata penting yang tidak dimiliki yang lain
    if (tok_t - tok_c) and (len(common) / len(tok_t) < 0.85):
        return jaccard * 0.5
    if (tok_c - tok_t) and (len(common) / len(tok_c) < 0.85):
        return jaccard * 0.5

    return jaccard

async def _enrich_search_results_with_metadata(items: list, al_meta_list: list):
    """Perkaya item hasil pencarian dengan metadata season dan tahun akurat tanpa salah mencocokkan."""
    if not items:
        return
    for it in items:
        if it.get("season") and it.get("year"):
            continue

        slug = it.get("id") or it.get("slug") or ""
        # 1. Cek detail lokal dari browse_cache jika pernah dibuka
        if slug:
            try:
                cached = await get_browse_cache(f"detail_v2|{slug}")
                if cached and cached.get("year"):
                    it["year"] = cached["year"]
                    it["season"] = cached.get("season") or str(cached["year"])
                    continue
            except Exception:
                pass

        # 2. Cocokkan dengan AniList secara presisi (Jaccard >= 0.70)
        title = (it.get("title") or "").strip()
        best_match = None
        best_score = 0.0
        if al_meta_list and title:
            for al_m in al_meta_list:
                t_obj = al_m.get("title") or {}
                al_titles = [t_obj.get("english"), t_obj.get("romaji"), t_obj.get("native")]
                for at in al_titles:
                    if not at:
                        continue
                    score = _calculate_title_match_score(title, at)
                    if score > best_score:
                        best_score = score
                        best_match = al_m

        if best_match and best_score >= 0.70:
            s_name = (best_match.get("season") or "").title()
            s_year = best_match.get("seasonYear") or (best_match.get("startDate") or {}).get("year") or 0
            if s_name and s_year:
                it["season"] = f"{s_name} {s_year}".strip()
                it["year"] = s_year
            elif s_year:
                it["year"] = s_year
                it["season"] = str(s_year)
            elif s_name:
                it["season"] = s_name

        # 3. Cek tahun parentesis eksplisit di judul (misal '(2023)')
        if not it.get("year"):
            m_yr = re.search(r'[\(\[]\s*(19\d\d|20\d\d)\s*[\)\]]', title)
            if m_yr:
                it["year"] = int(m_yr.group(1))
                if not it.get("season"):
                    it["season"] = str(it["year"])

@app.get("/api/search")
async def search(q: str = Query(""), page: int = Query(1, ge=1, le=100), limit: int = 24, source: str = Query(""), safe_mode: int = Query(1)):
    q = (q if isinstance(q, str) else "").strip()
    if not q:
        return fail("missing q")
    if q.lower() == "hentai" or "hentai" in q.lower().split():
        return ok({"results": [], "page": page, "total_pages": 1, "has_next": False, "cached": False})
    
    safe_mode_int = _parse_safe_mode(safe_mode)
    if safe_mode_int == 1:
        vulgar_words = {"ecchi", "erotica", "hentai", "magical-sex-shift"}
        if any(w in q.lower() for w in vulgar_words):
            return ok({"results": [], "page": page, "total_pages": 1, "has_next": False, "cached": False})

    src = (source if isinstance(source, str) else "").strip().lower()
    c_page = page if isinstance(page, int) and page >= 1 else 1
    c_limit = limit if isinstance(limit, int) and limit >= 1 else 24
    cache_key = f"{src}|{q.lower()}|p{c_page}|l{c_limit}" if src else f"{q.lower()}|p{c_page}|l{c_limit}"
    try:
        hit = await get_search_cache(cache_key)
        if hit:
            if isinstance(hit, dict) and any(bool(x.get("poster")) for x in hit.get("results", [])):
                hit_copy = dict(hit)
                if safe_mode_int == 1 and hit_copy.get("results"):
                    adult_tags = ("ecchi", "erotica", "hentai", "magical-sex-shift")
                    hit_copy["results"] = [
                        it for it in hit_copy["results"]
                        if not any(tag in (it.get("id") or "").lower() or tag in (it.get("title") or "").lower() for tag in adult_tags)
                    ]
                hit_copy["cached"] = True
                return ok(hit_copy)
            elif isinstance(hit, list) and any(bool(x.get("poster")) for x in hit):
                results = list(hit)
                if safe_mode_int == 1:
                    adult_tags = ("ecchi", "erotica", "hentai", "magical-sex-shift")
                    results = [
                        it for it in results
                        if not any(tag in (it.get("id") or "").lower() or tag in (it.get("title") or "").lower() for tag in adult_tags)
                    ]
                return ok({"results": results, "page": c_page, "total_pages": 1, "has_next": False, "cached": True})
        
        loop = asyncio.get_running_loop()
        al_meta_task = loop.run_in_executor(None, lambda: al.search_anime_metadata(q, per_page=15))
        paged_res = None
        if src == "otakudesu":
            from api import otakudesu as ot
            res = await loop.run_in_executor(None, lambda: ot.search(q, c_limit))
            paged_res = {"results": res, "page": c_page, "total_pages": 1, "has_next": False}
        else:
            try:
                paged_res = await loop.run_in_executor(None, lambda: hi.hianime_search_page(q, limit=c_limit, page=c_page))
            except Exception:
                paged_res = None
            if not paged_res or not paged_res.get("results"):
                # Fallback ke Otakudesu jika di halaman 1 dan HiAnime tidak menemukan hasil
                if c_page == 1:
                    try:
                        from api import otakudesu as ot
                        res = await loop.run_in_executor(None, lambda: ot.search(q, c_limit))
                        if res:
                            paged_res = {"results": res, "page": 1, "total_pages": 1, "has_next": False}
                    except Exception:
                        pass
        
        if not paged_res:
            paged_res = {"results": [], "page": c_page, "total_pages": 1, "has_next": False}

        if paged_res.get("results"):
            try:
                al_meta_list = await al_meta_task
                await _enrich_search_results_with_metadata(paged_res["results"], al_meta_list)
            except Exception:
                pass
            
        paged_res["cached"] = False
        if paged_res.get("results"):
            await set_search_cache(cache_key, paged_res)
        if safe_mode_int == 1 and paged_res.get("results"):
            adult_tags = ("ecchi", "erotica", "hentai", "magical-sex-shift")
            paged_res = dict(paged_res)
            paged_res["results"] = [
                it for it in paged_res["results"]
                if not any(tag in (it.get("id") or "").lower() or tag in (it.get("title") or "").lower() for tag in adult_tags)
            ]
        return ok(paged_res)
    except Exception as e:
        return fail(str(e))

@app.get("/api/filters")
async def filters():
    return ok(hi.FILTERS)

@app.get("/api/catalog")
async def catalog(page: int = Query(1, ge=1, le=100), safe_mode: int = Query(1)):
    """Katalog umum: semua judul, default urut populer."""
    try:
        import json as _json
        key = f"catalog|page={page}"
        hit = await get_browse_cache(key)
        if hit:
            res = dict(hit)
            res["cached"] = True
        else:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, lambda: hi.browse({}, page))
            await set_browse_cache(key, res)
            res = dict(res)
            res["cached"] = False
        safe_mode_int = _parse_safe_mode(safe_mode)
        if safe_mode_int == 1 and res and res.get("items"):
            adult_tags = ("ecchi", "erotica", "magical-sex-shift")
            res["items"] = [
                it for it in res["items"]
                if not any(tag in (it.get("id") or "").lower() or tag in (it.get("title") or "").lower() for tag in adult_tags)
            ]
        return ok(res)
    except Exception as e:
        return fail(str(e))

@app.get("/api/genres")
async def genres(safe_mode: int = 1):
    """Daftar genre dari hianime /browse sidebar. Cache 24 jam."""
    try:
        key = "genres|list"
        hit = await get_browse_cache(key, ttl=24*3600)
        if hit and hit.get("list"):
            base_list = hit["list"]
            cached = True
        else:
            loop = asyncio.get_running_loop()
            out = await loop.run_in_executor(None, hi.scrape_genres)
            base_list = out
            await set_browse_cache(key, {"list": out})
            cached = False

        filtered = [g for g in base_list if (g.get("slug") or "").lower() != "hentai" and "hentai" not in (g.get("title") or "").lower()]
        safe_mode_int = _parse_safe_mode(safe_mode)
        if safe_mode_int == 1:
            adult_tags = {"ecchi", "erotica", "magical-sex-shift"}
            filtered = [g for g in filtered if (g.get("slug") or "").lower() not in adult_tags and not any(tag in (g.get("title") or "").lower() for tag in adult_tags)]
        return ok({"list": filtered, "cached": cached})
    except Exception as e:
        return fail(str(e))

def _is_long_running(title: str, episodes: int = 0, start_year: int = 0, sub_count: int = 0, slug: str = "") -> bool:
    """Klasifikasi apakah anime tergolong serial panjang kontinu (non-musiman)."""
    t = (title or "").lower()
    s = (slug or "").lower()
    known = ("one-piece", "one piece", "detective conan", "case closed", "pokemon", "crayon shin-chan",
             "shin-chan", "doraemon", "chibi maruko-chan", "chibi-maruko", "boruto", "sazae-san", "sazae",
             "dragon ball", "naruto")
    if any(k in t or k in s for k in known):
        return True
    # Guard: jika sub_count kecil (<= 24 ep) tapi episodes tinggi tanpa kecocokan serial legendaris
    if sub_count and sub_count <= 24 and episodes and episodes > 50 and not any(k in t or k in s for k in known):
        return False
    if sub_count > 30:
        return True
    if episodes and episodes > 30:
        return True
    if (episodes is None or episodes == 0) and start_year and start_year < 2024:
        return True
    return False


@app.get("/api/seasonal")
async def seasonal(which: str = Query("", pattern="^(now|prev|airing)$|^$"),
                   season: str = Query("", pattern="^(winter|spring|summer|fall)$|^$"),
                   year: int = Query(0, ge=0, le=2100),
                   page: int = Query(1, ge=1, le=100)):
    """Daftar anime per musim / ongoing (AniList dengan fallback HiAnime).
    which=now|prev|airing = musim saat ini / sebelumnya / sedang tayang.
    season+year = musim spesifik (contoh: season=fall year=2024)."""
    try:
        loop = asyncio.get_running_loop()

        # Kasus khusus: Masih Tayang / Airing Ongoing dengan Dual-Lane (Musiman vs Panjang)
        if which == "airing":
            key = f"airing_lanes_v4|page={page}"
            hit = await get_browse_cache(key, ttl=3600)
            if hit:
                hit["cached"] = True
                return ok(hit)

            # 1. Ambil anime musiman yang baru saja tamat dari AniList (diurutkan paling baru tamat)
            finished_data = await loop.run_in_executor(None, lambda: al.recently_finished_page(page, 16))
            finished_media = (finished_data or {}).get("media") or []

            title_pairs = []
            finished_by_title = {}
            for m in finished_media:
                t_en = (m.get("title") or {}).get("english") or ""
                t_ro = (m.get("title") or {}).get("romaji") or ""
                primary_title = t_en or t_ro or ""
                if not primary_title or "hentai" in primary_title.lower():
                    continue
                alt_title = t_ro if primary_title != t_ro else ""
                title_pairs.append((primary_title, alt_title))
                finished_by_title[primary_title] = m

            slug_pairs = await _match_slug_batch(title_pairs) if title_pairs else []
            slug_by_title = {t: s for t, s in slug_pairs}

            seasonal_items = []
            seen_slugs = set()
            for title, m in finished_by_title.items():
                slug = slug_by_title.get(title)
                if not slug or slug in seen_slugs:
                    continue
                seen_slugs.add(slug)
                m_mal_id = str(m.get("idMal") or "")
                if m_mal_id:
                    aniskip.store_mal_id(slug, m_mal_id)
                    aniskip.store_mal_id(title, m_mal_id)
                cover = (m.get("coverImage") or {})
                tot = m.get("episodes") or 0
                studio_nodes = (m.get("studios") or {}).get("nodes") or []
                studio_name = studio_nodes[0].get("name", "") if studio_nodes else ""
                seasonal_items.append({
                    "id": slug,
                    "title": title,
                    "poster": cover.get("large") or cover.get("medium") or "",
                    "type": _format_to_type(m.get("format")),
                    "eps": tot,
                    "sub": tot,
                    "eps_released": tot,
                    "eps_total": tot,
                    "eps_counter": f"{tot}/{tot}" if tot > 0 else "?/?",
                    "duration": (str(m.get("duration") or "") + "m") if m.get("duration") else "",
                    "score": round((m.get("averageScore") or 0) / 10.0, 1) if m.get("averageScore") else 0.0,
                    "genres": m.get("genres") or [],
                    "studio": studio_name,
                    "season": f"{(m.get('season') or '').capitalize()} {m.get('seasonYear') or ''}".strip(),
                    "source": (m.get("source") or "").replace("_", " ").title(),
                    "status": "finished",
                    "badge": "TAMAT",
                    "is_finished": True,
                    "is_long_running": False,
                    "lane": "seasonal",
                    "synopsis": al.clean_synopsis_text(m.get("description") or ""),
                    "anilist_id": m.get("id"),
                    "mal_id": m_mal_id,
                    "matched": True,
                })

            # 2. Ambil data releasing dari HiAnime (diurutkan sort=latest untuk episode terbaru)
            hi_data = await loop.run_in_executor(None, lambda: hi.browse({"status": "releasing", "sort": "latest"}, page))
            hi_items = (hi_data or {}).get("items") or []

            long_running_items = []
            for item in hi_items:
                slug = item.get("id", "")
                if not slug or slug in seen_slugs:
                    continue
                title = item.get("title", "")
                if "hentai" in title.lower() or "hentai" in slug.lower():
                    continue
                eps = item.get("eps") or 0
                sub = item.get("sub") or 0
                rel_cnt = item.get("eps_released") or (sub if sub > 0 else (eps if eps > 0 else 0))
                tot_cnt = item.get("eps_total") or (eps if eps > 0 else 0)
                if tot_cnt > 0:
                    cnt_str = f"{rel_cnt}/{tot_cnt}"
                elif rel_cnt > 0:
                    cnt_str = f"{rel_cnt}/?"
                else:
                    cnt_str = ""

                if _is_long_running(title, eps, 0, sub, slug):
                    item_copy = dict(item)
                    item_copy["badge"] = "SERIAL PANJANG"
                    item_copy["is_long_running"] = True
                    item_copy["is_finished"] = False
                    item_copy["lane"] = "long_running"
                    item_copy["eps_released"] = rel_cnt
                    item_copy["eps_total"] = tot_cnt
                    item_copy["eps_counter"] = cnt_str
                    seen_slugs.add(slug)
                    long_running_items.append(item_copy)
                else:
                    item_copy = dict(item)
                    is_fin = bool(item.get("is_finished")) or (tot_cnt > 0 and rel_cnt >= tot_cnt)
                    item_copy["badge"] = "TAMAT" if is_fin else "ONGOING"
                    item_copy["is_long_running"] = False
                    item_copy["is_finished"] = is_fin
                    item_copy["status"] = "finished" if is_fin else "releasing"
                    item_copy["lane"] = "seasonal"
                    item_copy["eps_released"] = rel_cnt
                    item_copy["eps_total"] = tot_cnt
                    item_copy["eps_counter"] = cnt_str
                    seen_slugs.add(slug)
                    seasonal_items.append(item_copy)

            # 3. Rakit items dengan section headers pembatas dua jalur
            items_dual_lane = []
            if seasonal_items:
                items_dual_lane.append({
                    "is_header": True,
                    "id": "header-seasonal",
                    "title": "ANIME MUSIMAN (BARU TAMAT / BERJALAN)",
                    "header_title": "ANIME MUSIMAN (BARU TAMAT / BERJALAN)",
                    "lane": "seasonal",
                    "matched": False
                })
                items_dual_lane.extend(seasonal_items)

            if long_running_items:
                items_dual_lane.append({
                    "is_header": True,
                    "id": "header-long-running",
                    "title": "ANIME PANJANG BERKELANJUTAN (CONTINUOUS ON-GOING)",
                    "header_title": "ANIME PANJANG BERKELANJUTAN (CONTINUOUS ON-GOING)",
                    "lane": "long_running",
                    "matched": False
                })
                items_dual_lane.extend(long_running_items)

            response_payload = {
                "which": "airing",
                "page": page,
                "total_pages": max((hi_data or {}).get("total_pages", 1), 5),
                "seasonal": seasonal_items,
                "long_running": long_running_items,
                "items": items_dual_lane,
                "cached": False
            }
            await set_browse_cache(key, response_payload)
            return ok(response_payload)

        is_future = False
        if season and year >= 1900:
            season_name = season
            season_year = year
            cache_id = f"{season}_{year}"
            cur_year, cur_season = al.current_season()
            order = ["winter", "spring", "summer", "fall"]
            try:
                if year > cur_year or (year == cur_year and order.index(season.lower()) > order.index(cur_season.lower())):
                    is_future = True
            except ValueError:
                pass
        else:
            year_cur, name_cur = al.current_season()
            if which == "now":
                season_name, season_year = name_cur, year_cur
            elif which == "prev":
                season_year, season_name = al.prev_season(name_cur, year_cur)
            else:
                season_name, season_year = name_cur, year_cur
            cache_id = which or "now"

        key = f"seasonal_v4|{cache_id}|page={page}"
        hit = await get_browse_cache(key)
        if hit:
            hit["cached"] = True
            hit["season"] = season_name
            hit["year"] = season_year
            if hit.get("has_next") and hit.get("total_pages", 1) <= page:
                hit["total_pages"] = page + 1
            return ok(hit)

        status_in = ["RELEASING"] if which == "now" else (None if is_future else ["RELEASING", "FINISHED"])
        page_data = await loop.run_in_executor(
            None, lambda: al.season_page(season_name, season_year, page, 25, status_in=status_in))

        # Kumpulkan judul dulu, lalu batch-match slug paralel dengan validasi judul & season.
        media_list = (page_data or {}).get("media") or []
        title_pairs = []
        media_by_title = {}
        for m in media_list:
            if not is_future and m.get("status") == "NOT_YET_RELEASED":
                continue
            t_en = (m.get("title") or {}).get("english") or ""
            t_ro = (m.get("title") or {}).get("romaji") or ""
            primary_title = t_en or t_ro or ""
            if not primary_title:
                continue
            alt_title = t_ro if primary_title != t_ro else ""
            title_pairs.append((primary_title, alt_title))
            media_by_title[primary_title] = m
        slug_pairs = await _match_slug_batch(title_pairs) if title_pairs else []
        slug_by_title = {t: s for t, s in slug_pairs}

        items_out = []
        for title, m in media_by_title.items():
            slug = slug_by_title.get(title)
            if not slug:
                continue
            cover = (m.get("coverImage") or {})
            eps_rel, eps_tot = al.compute_episode_counts(m)
            status_str = (m.get("status") or "").lower()
            is_finished = status_str in ("finished", "completed") or (eps_tot > 0 and eps_rel >= eps_tot)
            if which == "now" and (is_finished or status_str in ("finished", "completed")):
                continue
            if is_finished:
                status_str = "finished"
                eps_cnt = f"{eps_tot}/{eps_tot}" if eps_tot > 0 else "?/?"
                badge = "TAMAT"
            else:
                eps_cnt = f"{eps_rel}/{eps_tot}" if eps_tot > 0 else (f"{eps_rel}/?" if eps_rel > 0 else "")
                badge = "ONGOING"
            m_mal_id = str(m.get("idMal") or "")
            if m_mal_id:
                aniskip.store_mal_id(slug, m_mal_id)
                aniskip.store_mal_id(title, m_mal_id)
            studio_nodes = (m.get("studios") or {}).get("nodes") or []
            studio_name = studio_nodes[0].get("name", "") if studio_nodes else ""
            items_out.append({
                "id": slug,
                "title": title,
                "poster": cover.get("large") or cover.get("medium") or "",
                "type": _format_to_type(m.get("format")),
                "eps": eps_tot,
                "sub": eps_rel,
                "eps_released": eps_rel,
                "eps_total": eps_tot,
                "eps_counter": eps_cnt,
                "duration": (str(m.get("duration") or "") + "m") if m.get("duration") else "",
                "score": round((m.get("averageScore") or 0) / 10.0, 1) if m.get("averageScore") else 0.0,
                "genres": m.get("genres") or [],
                "studio": studio_name,
                "season": f"{(m.get('season') or '').capitalize()} {m.get('seasonYear') or ''}".strip(),
                "source": (m.get("source") or "").replace("_", " ").title(),
                "status": status_str,
                "badge": badge,
                "is_finished": is_finished,
                "synopsis": al.clean_synopsis_text(m.get("description") or ""),
                "anilist_id": m.get("id"),
                "mal_id": m_mal_id,
                "site": m.get("siteUrl") or "",
                "matched": True,
            })

        # Fallback jika AniList diblokir ISP / offline / kosong
        hi_total_pages = 1
        if not items_out:
            fallback_filter = {"status": "releasing", "sort": "trending"} if which == "now" else {}
            if season and year:
                fallback_filter["season"] = str(season_name).lower()
                fallback_filter["sy"] = str(season_year)
                fallback_filter["ey"] = str(season_year)
                if is_future:
                    fallback_filter["status"] = "upcoming"
            elif which == "now":
                fallback_filter = {"status": "releasing", "sort": "trending"}
            elif which == "prev":
                fallback_filter = {"season": str(season_name).lower(), "sy": str(season_year), "ey": str(season_year)}
            hi_data = await loop.run_in_executor(None, lambda: hi.browse(fallback_filter, page))
            if hi_data and hi_data.get("items"):
                items_out = hi_data.get("items")
                hi_total_pages = hi_data.get("total_pages", 1)

        if which == "now" and items_out:
            items_out = [it for it in items_out if it.get("badge") != "TAMAT" and it.get("is_finished") is not True and (it.get("status") or "").lower() != "finished"]

        page_info = (page_data or {}).get("pageInfo") or {}
        has_next = bool(page_info.get("hasNextPage"))
        total_p = max(1, page_info.get("lastPage") or 1)
        if hi_total_pages > 1:
            total_p = max(total_p, hi_total_pages)
            has_next = total_p > page
        if has_next and total_p <= page:
            total_p = page + 1
        result = {
            "season": season_name,
            "year": season_year,
            "which": which,
            "items": items_out,
            "page": page,
            "total_pages": total_p,
            "total_items": len(items_out),
            "has_next": has_next,
            "cached": False,
        }
        await set_browse_cache(key, result)
        return ok(result)
    except Exception as e:
        return fail(str(e))


def _format_to_type(f):
    return {"TV": "TV", "TV_SHORT": "TV", "MOVIE": "Movie", "OVA": "OVA",
            "ONA": "ONA", "SPECIAL": "Special", "MUSIC": "Music"}.get(f or "", "")


def _slug_norm_match(title):
    """Normalisasi judul untuk perbandingan dengan hasil hianime_search.
    Import dari database agar konsisten dengan key yang dipakai slug_map."""
    from database import _slug_norm
    return _slug_norm(title)


def _extract_season_num(t: str) -> int:
    import re
    t = (t or "").lower()
    m = re.search(r"\b(?:season\s*(\d+)|(\d+)(?:nd|rd|th|st)\s*season|part\s*(\d+)|s(\d+)|saishuushou\s*(\d+)|finale\s*(\d+))\b|(?:\b|\s)(\d+)$", t)
    if m:
        for g in m.groups():
            if g:
                try:
                    return int(g)
                except ValueError:
                    pass
    m_roman = re.search(r"\b(ii|iii|iv|v|vi)\b", t)
    if m_roman:
        return {"ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6}[m_roman.group(1)]
    return 1


def _clean_title_tokens(t: str) -> set:
    import re
    t = (t or "").replace("&", " and ")
    t = re.sub(r"\b(?:season\s*\d+|\d+(?:nd|rd|th|st)\s*season|part\s*\d+|s\d+|saishuushou\s*\d+|finale\s*\d+|ii|iii|iv|v|vi)\b|(?:\b|\s)\d+$", "", t, flags=re.I)
    t = re.sub(r"[^a-zA-Z0-9\s]", " ", t)
    tokens = set()
    for tok in t.lower().split():
        if tok == "ovas": tok = "ova"
        elif tok == "specials": tok = "special"
        elif tok == "movies": tok = "movie"
        elif tok == "finale": tok = "saishuushou"
        tokens.add(tok)
    return tokens


def _is_title_match(target_title: str, candidate_title: str) -> bool:
    import re
    if not target_title or not candidate_title:
        return False
    # 1. Exact normalized match (tanpa spasi & simbol)
    def _norm(s):
        s = (s or "").lower().replace("&", "and")
        s = re.sub(r"\bund\b", "and", s)
        return re.sub(r"[^a-zA-Z0-9]", "", s)
    if _norm(target_title) == _norm(candidate_title):
        return True

    # 2. Validasi nomor season / part (mencegah Season 2 match ke Season 1)
    season_a = _extract_season_num(target_title)
    season_b = _extract_season_num(candidate_title)
    if (season_a > 1 or season_b > 1) and season_a != season_b:
        return False

    # 3. Validasi token overlap
    tokens_a = _clean_title_tokens(target_title)
    tokens_b = _clean_title_tokens(candidate_title)
    if not tokens_a or not tokens_b:
        return False

    # 4. Isolasi format Movie/Film vs Serial
    movie_keywords = {"movie", "film", "gekijouban"}
    if bool(tokens_a.intersection(movie_keywords)) != bool(tokens_b.intersection(movie_keywords)):
        return False

    # 5. Isolasi format OVA/Special vs Serial
    ova_keywords = {"ova", "special", "oad"}
    if bool(tokens_a.intersection(ova_keywords)) != bool(tokens_b.intersection(ova_keywords)):
        return False

    # 6. Validasi kata pembeda spesifik franchise
    distinct_tags = {"anzio", "taiyaki", "saishuushou", "alice"}
    for tag in distinct_tags:
        if (tag in tokens_a) != (tag in tokens_b):
            return False

    stopwords = {"the", "a", "an", "of", "in", "to", "and", "und", "der", "die", "das", "no", "wa", "ga", "ni", "de", "series"}
    sig_common = tokens_a.intersection(tokens_b) - stopwords
    sig_a = tokens_a - stopwords
    sig_b = tokens_b - stopwords

    if not sig_a or not sig_b:
        return (len(tokens_a.intersection(tokens_b)) / max(len(tokens_a), len(tokens_b))) >= 0.75

    overlap = len(sig_common) / max(len(sig_a), len(sig_b))
    return overlap >= 0.60


async def _match_slug_one(loop, title, alt_title=""):
    """Resolve 1 judul -> slug hianime via cache get/set. Return None jika gagal atau tidak cocok."""
    slug = await get_slug_map(title)
    if slug:
        return slug
    try:
        res = await loop.run_in_executor(None, lambda t=title: hi.hianime_search(t, 5))
        picked = None
        if res:
            for c in res:
                c_title = c.get("title", "")
                if _is_title_match(title, c_title) or (alt_title and _is_title_match(alt_title, c_title)):
                    picked = c
                    break

        # Fallback pencarian tanpa kata generik "series" atau tanpa subtitle setelah ":" jika belum cocok
        if not picked and (" series" in title.lower() or ":" in title):
            clean_q = re.sub(r"\bseries\b", "", title, flags=re.I).strip()
            clean_q = re.sub(r"\s+", " ", clean_q).strip()
            if clean_q and clean_q.lower() != title.lower():
                res2 = await loop.run_in_executor(None, lambda t=clean_q: hi.hianime_search(t, 5))
                if res2:
                    for c in res2:
                        c_title = c.get("title", "")
                        if _is_title_match(title, c_title) or (alt_title and _is_title_match(alt_title, c_title)):
                            picked = c
                            break

        # Validasi ketat: HANYA gunakan jika benar-benar cocok.
        # JANGAN PERNAH fallback ke res[0] secara buta agar judul & thumbnail tidak tertukar!
        if picked:
            await set_slug_map(title, picked["id"])
            return picked["id"]
    except Exception:
        pass
    return None


# Batas request paralel ke hianime per scrape (mencegah rate-limit).
_SLUG_MATCH_CONCURRENCY = 8


async def _match_slug_batch(items):
    """Match banyak judul ke slug hianime secara paralel.
    Input: list of (primary_title, alt_title) atau list of titles."""
    items = list(items)
    if not items:
        return []
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(_SLUG_MATCH_CONCURRENCY)
    async def one(item):
        if isinstance(item, tuple):
            t, alt = item
        else:
            t, alt = item, ""
        async with sem:
            return t, await _match_slug_one(loop, t, alt)
    pairs = await asyncio.gather(*(one(it) for it in items))
    return pairs


DAYS_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAYS_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
EN_TO_ID = dict(zip(DAYS_KEYS, DAYS_ID))
ID_TO_EN = {
    "senin": "monday", "selasa": "tuesday", "rabu": "wednesday",
    "kamis": "thursday", "jumat": "friday", "sabtu": "saturday", "minggu": "sunday"
}

@app.get("/api/schedule")
async def anime_schedule(day: str = Query("today")):
    """Jadwal rilis anime 7 hari mingguan (Senin - Minggu) waktu WIB.
    HANYA menampilkan anime yang tersedia di aplikasi Tatap (memiliki slug valid).
    Anime yang tidak ada di aplikasi Tatap otomatis di-remove."""
    try:
        import datetime as _dt
        loop = asyncio.get_running_loop()
        tz_offset = 7 * 3600  # WIB (UTC+7)
        now_utc = int(time.time())
        now_wib = now_utc + tz_offset
        now_dt_wib = _dt.datetime.fromtimestamp(now_utc, _dt.timezone(_dt.timedelta(hours=7)))
        cur_weekday = now_dt_wib.weekday()  # 0=Monday, ..., 6=Sunday
        today_key = DAYS_KEYS[cur_weekday]
        yesterday_key = DAYS_KEYS[(cur_weekday - 1) % 7]
        tomorrow_key = DAYS_KEYS[(cur_weekday + 1) % 7]

        today_mid_wib = (now_wib // 86400) * 86400
        mon_mid_wib = today_mid_wib - (cur_weekday * 86400)
        mon_mid_utc = mon_mid_wib - tz_offset
        sun_end_wib = mon_mid_wib + (7 * 86400) - 1
        sun_end_utc = sun_end_wib - tz_offset

        cache_key = f"schedule_7days_v1_{mon_mid_wib}"
        cached_data = await get_browse_cache(cache_key, ttl=3600 * 2)

        if not cached_data:
            schedules = await loop.run_in_executor(
                None, lambda: al.anilist_schedules_range(mon_mid_utc, sun_end_utc, max_pages=6)
            )

            pending = []
            seen_ids = set()
            for s in schedules:
                m = s.get("media") or {}
                mid = m.get("id")
                if not mid or mid in seen_ids:
                    continue
                seen_ids.add(mid)
                t_en = (m.get("title") or {}).get("english") or ""
                t_ro = (m.get("title") or {}).get("romaji") or ""
                primary_title = t_en or t_ro or ""
                if not primary_title:
                    continue
                alt_title = t_ro if primary_title != t_ro else ""
                pending.append((s, primary_title, alt_title))

            slug_pairs = await _match_slug_batch([(t, alt) for _, t, alt in pending]) if pending else []
            slug_by_title = {t: sl for t, sl in slug_pairs}

            buckets = {k: [] for k in DAYS_KEYS}

            for s, title, _ in pending:
                slug = slug_by_title.get(title)
                # FILTER KETAT: Yang tidak ada di dalam app Tatap di-REMOVE dari jadwal
                if not slug:
                    continue

                s_mal = str((s.get("media") or {}).get("idMal") or "")
                if s_mal:
                    aniskip.store_mal_id(slug, s_mal)
                    aniskip.store_mal_id(title, s_mal)

                airing_at = int(s["airingAt"])
                dt_wib = _dt.datetime.fromtimestamp(airing_at, _dt.timezone(_dt.timedelta(hours=7)))
                time_str = dt_wib.strftime("%H:%M WIB")
                date_str = dt_wib.strftime("%d %b")
                item_weekday = dt_wib.weekday()
                day_cat = DAYS_KEYS[item_weekday]
                day_name = EN_TO_ID.get(day_cat, "Senin")

                cover = (s.get("media") or {}).get("coverImage", {})
                fmt = (s.get("media") or {}).get("format") or "TV"
                score = (s.get("media") or {}).get("averageScore") or 0

                item = {
                    "id": slug,
                    "title": title,
                    "episode": s.get("episode") or 0,
                    "airing_at": airing_at,
                    "time": time_str,
                    "date": date_str,
                    "day": day_cat,
                    "day_name": day_name,
                    "poster": cover.get("large") or cover.get("medium") or "",
                    "type": _format_to_type(fmt),
                    "score": round(score / 10.0, 1) if score else 0.0,
                    "mal_id": s_mal,
                    "matched": True,
                }
                buckets[day_cat].append(item)

            for k in buckets:
                buckets[k].sort(key=lambda x: x["airing_at"])

            cached_data = {
                "week_start": mon_mid_utc,
                "week_end": sun_end_utc,
                "current_day": today_key,
                "current_day_name": EN_TO_ID[today_key],
                "days": {k: buckets[k] for k in DAYS_KEYS},
                "monday": buckets["monday"],
                "tuesday": buckets["tuesday"],
                "wednesday": buckets["wednesday"],
                "thursday": buckets["thursday"],
                "friday": buckets["friday"],
                "saturday": buckets["saturday"],
                "sunday": buckets["sunday"],
                "today": buckets[today_key],
                "yesterday": buckets[yesterday_key],
                "tomorrow": buckets[tomorrow_key],
                "counts": {
                    **{k: len(buckets[k]) for k in DAYS_KEYS},
                    "today": len(buckets[today_key]),
                    "yesterday": len(buckets[yesterday_key]),
                    "tomorrow": len(buckets[tomorrow_key]),
                },
                "total": sum(len(v) for v in buckets.values()),
                "cached": False,
            }
            await set_browse_cache(cache_key, cached_data)

        req_day = (day or "today").strip().lower()
        if req_day == "all":
            return ok(cached_data)

        if req_day == "today":
            target_day = today_key
        elif req_day == "yesterday":
            target_day = yesterday_key
        elif req_day == "tomorrow":
            target_day = tomorrow_key
        elif req_day in ID_TO_EN:
            target_day = ID_TO_EN[req_day]
        elif req_day in DAYS_KEYS:
            target_day = req_day
        else:
            target_day = today_key

        resp_day = req_day if req_day in ("today", "yesterday", "tomorrow") else target_day
        target_items = cached_data.get(target_day, [])
        return ok({
            "items": target_items,
            "day": resp_day,
            "weekday": target_day,
            "day_name": EN_TO_ID.get(target_day, target_day.capitalize()),
            "current_day": today_key,
            "is_today": (target_day == today_key),
            "total": len(target_items),
            "counts": cached_data.get("counts", {}),
            "cached": cached_data.get("cached", True),
        })
    except Exception as e:
        return fail(str(e))

@app.get("/api/upcoming-episodes")
async def upcoming_episodes(days: int = Query(7, ge=1, le=30), day: str = Query("today")):
    """Penyempurnaan upcoming-episodes yang disinkronkan dengan endpoint schedule 7 hari."""
    try:
        sch_res = await anime_schedule(day=day)
        data = sch_res.get("data") if isinstance(sch_res, dict) else None
        if data and "items" in data:
            return ok({
                "items": data["items"],
                "day": data.get("day", "today"),
                "day_name": data.get("day_name", ""),
                "current_day": data.get("current_day", ""),
                "is_today": data.get("is_today", False),
                "total": data.get("total", len(data["items"])),
                "counts": data.get("counts", {}),
                "cached": data.get("cached", False),
            })
        return sch_res
    except Exception as e:
        return fail(str(e))

@app.get("/api/browse")
async def browse_ep(
    type: str = Query(""), status: str = Query(""), rating: str = Query(""),
    score: str = Query(""), season: str = Query(""), language: str = Query(""),
    sort: str = Query(""), genre: str = Query(""), keyword: str = Query(""),
    sy: str = Query(""), sm: str = Query(""), ey: str = Query(""), em: str = Query(""),
    year: str = Query(""), month: str = Query(""),
    page: int = Query(1, ge=1, le=100),
    safe_mode: int = Query(1),
):
    """Filter bebas — semua parameter sesuai form filter (mendukung cross-filter sort, year, month)."""
    try:
        def _to_str(val):
            return val.strip() if isinstance(val, str) else ""

        safe_mode_int = _parse_safe_mode(safe_mode)
        c_genre = _to_str(genre)
        if c_genre.lower() == "hentai" or "hentai" in c_genre.lower():
            return ok({"items": [], "page": 1, "total_pages": 1, "params": {"genre": "hentai"}, "cached": False})

        if safe_mode_int == 1 and c_genre.lower() in ("ecchi", "erotica", "magical-sex-shift"):
            return ok({"items": [], "page": 1, "total_pages": 1, "params": {"genre": c_genre}, "cached": False})

        c_sy = _to_str(sy)
        c_ey = _to_str(ey)
        c_sm = _to_str(sm)
        c_em = _to_str(em)
        clean_year = _to_str(year)
        clean_month = _to_str(month)

        if clean_year and not c_sy:
            if "-" in clean_year:
                y_parts = clean_year.split("-", 1)
                c_sy = y_parts[0].strip()
                c_ey = y_parts[1].strip()
            elif clean_year.startswith("<"):
                raw_y = clean_year[1:].strip()
                try:
                    c_ey = str(int(raw_y) - 1)
                except Exception:
                    c_ey = raw_y
                c_sy = "1970"
            else:
                c_sy = clean_year
                c_ey = clean_year
        if clean_month and not c_sm:
            c_sm = clean_month
            c_em = clean_month

        c_page = page if isinstance(page, int) and page >= 1 else 1

        import json as _json
        params = {k: v for k, v in
                  {"type": _to_str(type), "status": _to_str(status), "rating": _to_str(rating),
                   "score": _to_str(score), "season": _to_str(season), "language": _to_str(language),
                   "sort": _to_str(sort), "genre": c_genre, "keyword": _to_str(keyword),
                   "sy": c_sy, "sm": c_sm, "ey": c_ey, "em": c_em}.items() if v}
        key = "browse|" + _json.dumps(params, sort_keys=True) + f"|page={c_page}"
        hit = await get_browse_cache(key)
        if hit:
            hit["cached"] = True
            return ok(hit)
        loop = asyncio.get_running_loop()
        res = await loop.run_in_executor(None, lambda: hi.browse(params, c_page))
        await set_browse_cache(key, res)
        res["cached"] = False
        if safe_mode_int == 1 and res and res.get("items"):
            adult_tags = ("ecchi", "erotica", "magical-sex-shift")
            res["items"] = [
                it for it in res["items"]
                if not any(tag in (it.get("id") or "").lower() or tag in (it.get("title") or "").lower() for tag in adult_tags)
            ]
        return ok(res)
    except Exception as e:
        return fail(str(e))

@app.get("/api/anime/{slug}/episodes")
async def episodes(slug: str):
    try:
        if "hentai" in (slug or "").lower():
            return fail("Konten genre Hentai diblokir")
        cache_key = f"episodes_v1|{slug}"
        cached = await get_browse_cache(cache_key, ttl=6 * 3600)
        if cached:
            cached["cached"] = True
            return ok(cached)
        loop = asyncio.get_running_loop()
        eps = []
        try:
            eps = await loop.run_in_executor(None, lambda: hi.hianime_episodes(slug))
        except Exception:
            try:
                otaku_slug = slug[len("otakudesu:"):] if slug.startswith("otakudesu:") else slug
                otaku_eps = await loop.run_in_executor(None, lambda: otaku.get_episodes(otaku_slug))
                if otaku_eps:
                    eps = [{"ep": e["ep"], "ep_id": str(e["ep"])} for e in otaku_eps]
            except Exception:
                pass
            if not eps:
                try:
                    anichan_eps = await loop.run_in_executor(None, lambda: anichan.get_episodes(slug))
                    if anichan_eps:
                        eps = anichan_eps
                except Exception:
                    pass
        if not eps:
            return fail("Daftar episode tidak ditemukan")
        syn_val = ""
        detail_data = {}
        try:
            if not slug.startswith("otakudesu:"):
                # Ambil metadata detail lengkap via hi.hianime_details (fallback ke hi.hianime_synopsis)
                detail_data = await loop.run_in_executor(None, lambda: hi.hianime_details(slug))
                if detail_data:
                    syn_val = detail_data.get("synopsis", "") or hi.hianime_synopsis(slug)
                else:
                    syn_val = await loop.run_in_executor(None, lambda: hi.hianime_synopsis(slug))
        except Exception:
            pass
        data = {
            "slug": slug,
            "episodes": eps,
            "total": len(eps),
            "synopsis": syn_val,
            "detail": detail_data,
            "poster": (detail_data.get("poster", "") if isinstance(detail_data, dict) else "")
        }
        await set_browse_cache(cache_key, data)
        data["cached"] = False
        return ok(data)
    except Exception as e:
        return fail(str(e))

@app.get("/api/anime/{slug}/detail")
async def anime_detail_endpoint(slug: str):
    """Ambil informasi metadata detail anime (sinopsis, score, genres, studio, musim, dll)."""
    try:
        if "hentai" in (slug or "").lower():
            return fail("Konten genre Hentai diblokir")
        cache_key = f"detail_v2|{slug}"
        cached = await get_browse_cache(cache_key, ttl=86400)
        if cached:
            cached["cached"] = True
            return ok(cached)
        loop = asyncio.get_running_loop()
        detail_data = await loop.run_in_executor(None, lambda: hi.hianime_details(slug))
        await set_browse_cache(cache_key, detail_data)
        detail_data["cached"] = False
        return ok(detail_data)
    except Exception as e:
        return fail(str(e))

@app.get("/api/anime/{slug}/relations")
async def anime_relations_endpoint(slug: str, title: str = Query("")):
    """Ambil daftar season/prekuel/sekuel terkait untuk anime yang sedang dibuka."""
    try:
        if "hentai" in (slug or "").lower() or "hentai" in (title or "").lower():
            return fail("Konten genre Hentai diblokir")
        
        loop = asyncio.get_running_loop()
        cache_key = f"relations_v1|{slug}"
        cached = await get_browse_cache(cache_key, ttl=86400 * 3) # Cache 3 hari
        if cached:
            return ok(cached)

        # Gunakan title dari query parameter atau tebak dari slug
        search_query = title.strip() if title else slug.rsplit("-", 1)[0].replace("-", " ")
        raw_relations = await loop.run_in_executor(None, lambda: al.anime_relations(search_query))

        results = []
        if not raw_relations:
            # Fallback jika AniList API offline / 403 / rate limited:
            # Cari franchise langsung via HiAnime search
            clean_q = re.sub(r'(?i)\s*[:\-]?\s*\b(der film|the movie|movie|season \d+|part \d+|ova|special|saishuushou)\b.*', '', search_query).strip()
            franchise_q = clean_q if len(clean_q) >= 3 else search_query
            hi_candidates = await loop.run_in_executor(None, lambda: hi.hianime_search(franchise_q, limit=20))
            if not hi_candidates and franchise_q != search_query:
                hi_candidates = await loop.run_in_executor(None, lambda: hi.hianime_search(search_query, limit=20))
            
            seen_cand = set()
            for cand in (hi_candidates or []):
                c_slug = cand.get("id") or ""
                if not c_slug or c_slug == slug or c_slug in seen_cand:
                    continue
                seen_cand.add(c_slug)
                c_title = cand.get("title") or ""
                if c_slug == "girls-und-panzer-2670" or c_title == "Girls & Panzer":
                    c_title = "Girls und Panzer"
                c_poster = cand.get("poster") or ""
                c_type = (cand.get("type") or "").upper()
                if "film" in c_slug or "movie" in c_title.lower() or "film" in c_title.lower():
                    c_fmt = "MOVIE"
                elif c_type in ("MOVIE", "OVA", "ONA", "SPECIAL", "TV"):
                    c_fmt = c_type
                else:
                    c_fmt = "TV"

                c_label = "Terkait"
                c_season = _extract_season_num(c_title)
                if c_fmt == "MOVIE":
                    part_m = re.search(r'\bpart\s*(\d+)\b', c_title, re.I)
                    c_label = f"Movie Part {part_m.group(1)}" if part_m else "Movie"
                elif c_fmt in ("OVA", "ONA", "SPECIAL"):
                    c_label = "Special" if c_fmt == "SPECIAL" else c_fmt
                elif c_season and c_season > 1:
                    c_label = f"Season {c_season}"
                else:
                    c_label = "Season 1"

                results.append({
                    "relation": "ALTERNATIVE" if c_fmt == "MOVIE" else "SIDE_STORY",
                    "label": c_label,
                    "title": c_title,
                    "title_romaji": c_title,
                    "year": None,
                    "format": c_fmt,
                    "poster": c_poster,
                    "slug": c_slug,
                    "is_origin": (c_label == "Season 1")
                })
        else:
            for r in raw_relations:
                rel_type = r.get("relation", "")
                r_title = r.get("title", "")
                r_romaji = r.get("title_romaji", "")
                r_year = r.get("year")
                r_fmt = r.get("format", "TV")
                r_poster = r.get("poster", "")
                is_origin = r.get("is_origin", False)

                # Cari slug HiAnime yang cocok untuk relasi ini
                matched_slug = await _match_slug_one(loop, r_title, r_romaji)
                if not matched_slug and r_romaji:
                    matched_slug = await _match_slug_one(loop, r_romaji, r_title)

                # Jika sekuel belum memiliki video atau belum rilis (tidak punya slug), lewati agar tidak menyesatkan
                if rel_type in ("SEQUEL", "ALTERNATIVE", "SUMMARY") and not matched_slug:
                    continue

                # Buat label yang mudah dimengerti user (misal: "Season 1", "Prekuel", "Sekuel", "Movie", "OVA")
                label = "Terkait"
                season_num = _extract_season_num(r_title) or _extract_season_num(r_romaji)
                if r_fmt == "MOVIE":
                    part_m = re.search(r'\bpart\s*(\d+)\b', r_title, re.I)
                    label = f"Movie Part {part_m.group(1)}" if part_m else "Movie"
                elif r_fmt in ("OVA", "ONA", "SPECIAL"):
                    label = "Special" if r_fmt == "SPECIAL" else r_fmt
                elif is_origin or (rel_type == "PREQUEL" and season_num == 1 and "season" not in r_title.lower()):
                    label = "Season 1"
                elif rel_type == "PREQUEL":
                    label = f"Season {season_num}" if season_num > 1 else "Prekuel"
                elif rel_type == "SEQUEL":
                    label = f"Season {season_num}" if season_num > 1 else "Sekuel"

                results.append({
                    "relation": rel_type,
                    "label": label,
                    "title": r_title,
                    "title_romaji": r_romaji,
                    "year": r_year,
                    "format": r_fmt,
                    "poster": r_poster,
                    "slug": matched_slug,
                    "is_origin": is_origin
                })

        # Urutkan: Season 1 / Origin paling pertama (-1), disusul PREQUEL berurutan tahun (2018 -> 2021), SEQUEL, MOVIE
        def sort_key(x):
            if x.get("is_origin") or x.get("label") == "Season 1":
                return (-1, x.get("year") or 0)
            order_map = {"PREQUEL": 0, "PARENT": 1, "SEQUEL": 2, "ALTERNATIVE": 3, "SIDE_STORY": 4, "SUMMARY": 5}
            return (order_map.get(x["relation"], 9), x.get("year") or 9999)

        results.sort(key=sort_key)

        data = {"current_slug": slug, "relations": results}
        await set_browse_cache(cache_key, data)
        return ok(data)
    except Exception as e:
        return fail(str(e))


def _has_valid_subtitles(ep_data: dict) -> bool:
    """Periksa apakah data episode memiliki daftar track subtitle yang valid (bukan angka/kosong)."""
    if not isinstance(ep_data, dict):
        return False
    subs = ep_data.get("subtitles")
    if isinstance(subs, list) and len(subs) > 0:
        for s in subs:
            if isinstance(s, dict):
                u = str(s.get("url") or "").strip()
                if u.startswith("http://") or u.startswith("https://") or u.startswith("/"):
                    return True
    sub = str(ep_data.get("sub") or "").strip()
    if sub.startswith("http://") or sub.startswith("https://") or sub.startswith("/"):
        return True
    return False


async def _resolve_mal_id(slug: str, title: str = "", anilist_id: str = "") -> str:
    """Mencari MAL ID dari cache in-memory, anilist_id, slug, atau pencarian AniList GraphQL."""
    if not slug and not title and not anilist_id:
        return ""
    clean_slug = slug.split(":", 1)[1] if ":" in slug else slug
    # 1. Cek cache in-memory aniskip
    cached_mal = aniskip.get_mal_id_from_cache(slug) or aniskip.get_mal_id_from_cache(clean_slug)
    if not cached_mal and title:
        cached_mal = aniskip.get_mal_id_from_cache(title)
    if cached_mal:
        return str(cached_mal)

    # 2. Cek database SQLite mal_map
    try:
        db_mal = await get_mal_map(slug) or await get_mal_map(clean_slug)
        if not db_mal and title:
            db_mal = await get_mal_map(title)
        if db_mal:
            m_id = str(db_mal)
            aniskip.store_mal_id(slug, m_id)
            aniskip.store_mal_id(clean_slug, m_id)
            if title:
                aniskip.store_mal_id(title, m_id)
            return m_id
    except Exception:
        pass

    loop = asyncio.get_running_loop()
    # 3. Cek anilist_id jika tersedia
    if anilist_id:
        try:
            al_id_int = int(str(anilist_id).strip())
            c = al._get_al_client()
            r = await loop.run_in_executor(None, lambda: c.post(al.ANILIST_URL, json={
                "query": al.MEDIA_BY_ID_QUERY,
                "variables": {"id": al_id_int}
            }))
            if r and r.status_code == 200:
                m_data = r.json().get("data", {}).get("Media", {}) or {}
                if m_data.get("idMal"):
                    m_id = str(m_data["idMal"])
                    aniskip.store_mal_id(slug, m_id)
                    aniskip.store_mal_id(clean_slug, m_id)
                    await set_mal_map(slug, m_id)
                    await set_mal_map(clean_slug, m_id)
                    if title:
                        aniskip.store_mal_id(title, m_id)
                        await set_mal_map(title, m_id)
                    return m_id
        except Exception:
            pass

    # 4. Ekstraksi search query dari title atau slug
    search_q = title.strip() if title else ""
    if not search_q:
        cs = clean_slug
        cs = re.sub(r"-\d+$", "", cs)
        cs = re.sub(r"-(sub-indo|episode-\d+|batch|complete)", "", cs, flags=re.I)
        cs = re.sub(r"-s-(?=[a-z])", "'s-", cs)
        search_q = cs.replace("-", " ").strip()
        search_q = re.sub(r"\b(\w+)\s+s\b", r"\1's", search_q)

    if search_q:
        try:
            found_mal = await loop.run_in_executor(None, lambda: al.resolve_mal_id_by_title(search_q))
            if found_mal:
                m_id = str(found_mal)
                aniskip.store_mal_id(slug, m_id)
                aniskip.store_mal_id(clean_slug, m_id)
                await set_mal_map(slug, m_id)
                await set_mal_map(clean_slug, m_id)
                if title:
                    aniskip.store_mal_id(title, m_id)
                    await set_mal_map(title, m_id)
                return m_id
        except Exception:
            pass

    return ""


@app.get("/api/stream/resolve")
@app.get("/api/episode")
async def resolve(slug: str = Query(""), ep: int = Query(1), mode: str = Query("sub"), q: str = Query("best"), source: str = Query(""), force: bool = Query(False), refresh: bool = Query(False), title: str = Query(""), mal_id: str = Query(""), anilist_id: str = Query("")):
    try:
        slug_str = str(slug or "") if isinstance(slug, str) else ""
        if "hentai" in slug_str.lower():
            return fail("Konten genre Hentai diblokir")
        mode = "dub" if (isinstance(mode, str) and str(mode).lower() == "dub") else "sub"
        title = title if isinstance(title, str) else ""
        mal_id = mal_id if isinstance(mal_id, str) else ""
        anilist_id = anilist_id if isinstance(anilist_id, str) else ""
        source = source if isinstance(source, str) else ""
        q = q if isinstance(q, str) else "best"

        def _is_truthy(v):
            return v is True or (isinstance(v, str) and v.strip().lower() in ("true", "1", "yes"))
        should_refresh = _is_truthy(force) or _is_truthy(refresh)
        pref_source = (await get_setting("preferred_source", "hianime")).lower()
        title_failover = _ANIME_FAILOVER_CACHE.get(slug)
        active_source = (source or title_failover or pref_source or "hianime").lower()

        # Cache key mencakup source agar stream tidak tertukar
        cache_slug = f"{active_source}:{slug}" if active_source != "hianime" else slug
        if should_refresh:
            await delete_episode_cache(cache_slug, ep)
            hit = None
        else:
            # Ambil cache mode utama + mode fallback dalam SATU query SQLite
            # (sebelumnya 2 round-trip: 'sub' lalu 'dub' atau sebaliknya).
            try:
                _modes_needed = [mode] if mode == "sub" else [mode, "sub"]
                _cache_hits = await get_episode_cache_modes(cache_slug, ep, _modes_needed)
            except Exception:
                _cache_hits = {}
            hit = _cache_hits.get(mode)
            if mode == "sub":
                # Cegah negative caching dan kontaminasi dub cache pada mode sub.
                # Jika cache hit tidak memiliki subtitle valid, bersihkan dan anggap cache miss.
                if hit and not _has_valid_subtitles(hit):
                    await delete_episode_cache(cache_slug, ep, mode="sub")
                    hit = None
            elif mode == "dub":
                if not hit:
                    hit = _cache_hits.get("sub")
        async def _check_and_prewarm(ep_data):
            try:
                sub_lang = (await get_setting("sub_lang", "Indonesian")).strip().lower()
                auto_tr = await get_setting("tatap_translate", "1")
                # Jika preferensi pengguna adalah Indonesia atau auto-translate aktif
                if sub_lang in ("indonesian", "id") or auto_tr in ("1", "true"):
                    subs = ep_data.get("subtitles") or []
                    en_url = ""
                    # 1. Cari exact English
                    for s in subs:
                        l = (s.get("lang") or "").lower().strip()
                        lbl = (s.get("label") or "").lower().strip()
                        if any(k in lbl for k in hi._NON_ENGLISH_KEYWORDS):
                            continue
                        if lbl in ("english", "english [full]", "english (full)", "eng"):
                            en_url = s.get("url") or ""
                            break
                    # 2. Cari varian English jika exact tidak ditemukan
                    if not en_url:
                        for s in subs:
                            l = (s.get("lang") or "").lower().strip()
                            lbl = (s.get("label") or "").lower().strip()
                            if any(k in lbl for k in hi._NON_ENGLISH_KEYWORDS):
                                continue
                            if "english" in lbl or lbl.startswith("eng") or l == "en":
                                en_url = s.get("url") or ""
                                break
                    if not en_url and ep_data.get("sub"):
                        sub_l = (ep_data.get("sub_lang") or "").lower().strip()
                        if not any(k in sub_l for k in hi._NON_ENGLISH_KEYWORDS):
                            en_url = ep_data.get("sub") or ""
                    if en_url:
                        _spawn_background(_prewarm_sub_translation(en_url, ep_data.get("referer") or "", "en", "id"))
            except Exception:
                pass

        if hit:
            # Pastikan subtitle yang tersimpan di cache lama dinormalisasi ulang
            # sehingga tidak pernah mengembalikan Arabic sebagai default track.
            if hit.get("subtitles"):
                hit["subtitles"] = hi._normalize_subtitles(hit["subtitles"], referer=hit.get("referer") or "")
                def_track = next((s for s in hit["subtitles"] if s.get("default")), None)
                if def_track:
                    hit["sub"] = def_track["url"]
                    hit["sub_lang"] = def_track["label"]
            elif hit.get("sub_lang", "").lower().startswith("ar") or "arab" in hit.get("sub_lang", "").lower():
                hit["sub"] = None
                hit["sub_lang"] = None

            # Self-heal cache: jika subtitles kosong, coba panen dari HiAnime
            if not hit.get("subtitles"):
                clean_slug = slug.split(":", 1)[1] if ":" in slug else slug
                hi_slug = clean_slug
                if active_source == "otakudesu" or clean_slug.startswith("otakudesu"):
                    raw_title = clean_slug.replace("-sub-indo", "").replace("-episode", "").replace("-", " ").strip()
                    try:
                        loop = asyncio.get_running_loop()
                        matched = await _match_slug_one(loop, raw_title)
                        if matched:
                            hi_slug = matched
                    except Exception:
                        pass
                try:
                    loop = asyncio.get_running_loop()
                    harvested = await loop.run_in_executor(None, lambda: hi.hianime_subtitles_for_episode(hi_slug, ep))
                    if harvested and harvested.get("subtitles"):
                        hit["subtitles"] = harvested["subtitles"]
                        hit["sub"] = harvested.get("sub")
                        hit["sub_lang"] = harvested.get("sub_lang")
                except Exception:
                    pass

            picked = hi.select_quality(hit["variants"], q)
            hit["picked"] = picked
            hit["cached"] = True
            hit["subtitles"] = hit.get("subtitles") or []
            hit["source"] = active_source
            hit["intro"] = hit.get("intro") or {"start": 0, "end": 0}
            hit["outro"] = hit.get("outro") or {"start": 0, "end": 0}

            # Cek cross-provider cache jika intro/outro belum lengkap
            clean_slug_hit = slug.split(":", 1)[1] if ":" in slug else slug
            raw_title_hit = clean_slug_hit.replace("-sub-indo", "").replace("-episode", "").replace("-", " ").strip() if (active_source == "otakudesu" or clean_slug_hit.startswith("otakudesu")) else ""
            eff_title_hit = title or raw_title_hit or clean_slug_hit
            eff_mal_id = str(hit.get("mal_id") or mal_id or "").strip()
            if not eff_mal_id:
                eff_mal_id = await _resolve_mal_id(slug=slug, title=eff_title_hit, anilist_id=anilist_id)
                if eff_mal_id:
                    hit["mal_id"] = eff_mal_id

            cached_sk = aniskip.get_cached_skip_times(mal_id=eff_mal_id, title=eff_title_hit, ep=ep)
            if cached_sk:
                if hit["intro"].get("end", 0) == 0 and cached_sk.get("intro", {}).get("end", 0) > 0:
                    hit["intro"] = cached_sk["intro"]
                if hit["outro"].get("end", 0) == 0 and cached_sk.get("outro", {}).get("end", 0) > 0:
                    hit["outro"] = cached_sk["outro"]

            if (hit["intro"].get("end", 0) == 0 or hit["outro"].get("end", 0) == 0) and eff_mal_id:
                try:
                    loop = asyncio.get_running_loop()
                    sk = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: aniskip.get_skip_times(eff_mal_id, ep, episode_length=0)),
                        timeout=1.8
                    )
                    has_updated_sk = False
                    if sk.get("intro", {}).get("end", 0) > 0 and hit["intro"].get("end", 0) == 0:
                        hit["intro"] = sk["intro"]
                        has_updated_sk = True
                    if sk.get("outro", {}).get("end", 0) > 0 and hit["outro"].get("end", 0) == 0:
                        hit["outro"] = sk["outro"]
                        has_updated_sk = True
                    if has_updated_sk:
                        await set_episode_cache(cache_slug, ep, hit.get("mode") or mode, hit["master"], hit["variants"],
                                                hit.get("sub"), hit.get("sub_lang"),
                                                hit.get("referer"), hit.get("server"),
                                                subtitles=hit.get("subtitles"),
                                                intro=hit["intro"], outro=hit["outro"])
                except Exception:
                    pass

            aniskip.store_skip_times(
                mal_id=eff_mal_id,
                title=eff_title_hit,
                ep=ep,
                intro=hit["intro"],
                outro=hit["outro"]
            )
            await _check_and_prewarm(hit)
            return ok(hit)

        loop = asyncio.get_running_loop()
        got = None
        last_error = None
        is_failover = False
        failover_from = None

        if active_source == "anichan":
            try:
                got = await loop.run_in_executor(None, lambda: anichan.resolve_stream(slug, ep, mode, q))
            except Exception as e:
                last_error = e
                if source == "auto" or not source:
                    try:
                        maps = await loop.run_in_executor(None, lambda: hi.hianime_episodes(slug))
                        got = await loop.run_in_executor(None, lambda: hi.hianime_m3u8(maps, ep, mode, slug))
                        active_source = "hianime"
                        cache_slug = slug
                    except Exception:
                        pass
        elif active_source == "otakudesu":
            try:
                got = await loop.run_in_executor(None, lambda: otaku.resolve_stream(slug, ep))
            except Exception as e:
                last_error = e
                # Fallback ke hianime kalau user pakai auto
                if source == "auto" or not source:
                    try:
                        maps = await loop.run_in_executor(None, lambda: hi.hianime_episodes(slug))
                        got = await loop.run_in_executor(None, lambda: hi.hianime_m3u8(maps, ep, mode, slug))
                        active_source = "hianime"
                        cache_slug = slug
                    except Exception:
                        pass
                    if not got:
                        try:
                            got = await loop.run_in_executor(None, lambda: anichan.resolve_stream(slug, ep, mode, q))
                            active_source = "anichan"
                            cache_slug = f"anichan:{slug}"
                            is_failover = True
                            failover_from = "otakudesu"
                            _set_failover(slug, "anichan")
                        except Exception:
                            pass
        else:
            try:
                maps = await loop.run_in_executor(None, lambda: hi.hianime_episodes(slug))
                got = await loop.run_in_executor(None, lambda: hi.hianime_m3u8(maps, ep, mode, slug))
            except Exception as e:
                last_error = e
                # Fallback ke otakudesu jika hianime gagal
                if source == "auto" or not source:
                    try:
                        got = await loop.run_in_executor(None, lambda: otaku.resolve_stream(slug, ep))
                        active_source = "otakudesu"
                        cache_slug = f"otakudesu:{slug}"
                    except Exception:
                        pass
                    # JIKA HIANIME & OTAKUDESU GAGAL (KASUS EYESHIELD 21):
                    # Failover otomatis per-judul ke AniChan langsung ke HLS M3U8
                    if not got:
                        try:
                            got = await loop.run_in_executor(None, lambda: anichan.resolve_stream(slug, ep, mode, q))
                            active_source = "anichan"
                            cache_slug = f"anichan:{slug}"
                            is_failover = True
                            failover_from = "hianime"
                            _set_failover(slug, "anichan")
                        except Exception as anichan_err:
                            last_error = anichan_err

        if not got:
            raise last_error or RuntimeError("Stream gagal di-resolve dari semua sumber")

        got["source"] = active_source
        if is_failover:
            got["is_failover"] = True
            got["failover_from"] = failover_from
        got["picked"] = hi.select_quality(got["variants"], q)
        got["cached"] = False
        got["subtitles"] = got.get("subtitles") or []
        clean_slug = slug.split(":", 1)[1] if ":" in slug else slug
        hi_slug = clean_slug
        raw_title = ""
        if not got["subtitles"]:
            if active_source == "otakudesu" or clean_slug.startswith("otakudesu"):
                raw_title = clean_slug.replace("-sub-indo", "").replace("-episode", "").replace("-", " ").strip()
                try:
                    matched = await _match_slug_one(loop, raw_title)
                    if matched:
                        hi_slug = matched
                except Exception:
                    pass
            try:
                harvested = await loop.run_in_executor(None, lambda: hi.hianime_subtitles_for_episode(hi_slug, ep))
                if harvested and harvested.get("subtitles"):
                    got["subtitles"] = harvested["subtitles"]
                    got["sub"] = harvested.get("sub")
                    got["sub_lang"] = harvested.get("sub_lang")
            except Exception:
                pass
        actual_mode = got.get("mode") or mode
        got["mode"] = actual_mode
        got["intro"] = got.get("intro") or {"start": 0, "end": 0}
        got["outro"] = got.get("outro") or {"start": 0, "end": 0}

        # Resolusi mal_id jika belum tersedia
        eff_title = title or raw_title or clean_slug
        eff_mal_id = str(got.get("mal_id") or mal_id or "").strip()
        if not eff_mal_id:
            eff_mal_id = await _resolve_mal_id(slug=slug, title=eff_title, anilist_id=anilist_id)
            if eff_mal_id:
                got["mal_id"] = eff_mal_id

        # 1. Cek cross-provider cache terlebih dahulu
        cached_sk = aniskip.get_cached_skip_times(mal_id=eff_mal_id, title=eff_title, ep=ep)
        if not cached_sk and hi_slug and hi_slug != clean_slug:
            cached_sk = aniskip.get_cached_skip_times(title=hi_slug, ep=ep)
        if cached_sk:
            if got["intro"].get("end", 0) == 0 and cached_sk.get("intro", {}).get("end", 0) > 0:
                got["intro"] = cached_sk["intro"]
            if got["outro"].get("end", 0) == 0 and cached_sk.get("outro", {}).get("end", 0) > 0:
                got["outro"] = cached_sk["outro"]

        if (got["intro"].get("end", 0) == 0 or got["outro"].get("end", 0) == 0) and eff_mal_id:
            try:
                sk = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: aniskip.get_skip_times(eff_mal_id, ep, episode_length=0)),
                    timeout=1.8
                )
                if sk.get("intro", {}).get("end", 0) > 0 and got["intro"].get("end", 0) == 0:
                    got["intro"] = sk["intro"]
                if sk.get("outro", {}).get("end", 0) > 0 and got["outro"].get("end", 0) == 0:
                    got["outro"] = sk["outro"]
            except Exception:
                pass

        # 2. Simpan ke cross-provider cache jika valid
        aniskip.store_skip_times(
            mal_id=eff_mal_id,
            title=eff_title,
            ep=ep,
            intro=got["intro"],
            outro=got["outro"]
        )
        if hi_slug and hi_slug != clean_slug:
            aniskip.store_skip_times(
                mal_id=eff_mal_id,
                title=hi_slug,
                ep=ep,
                intro=got["intro"],
                outro=got["outro"]
            )

        # Simpan cache episode (Cegah negative subtitle caching jika mode sub namun subtitle kosong)
        can_cache_sub = (mode != "sub") or _has_valid_subtitles(got)
        if can_cache_sub:
            await set_episode_cache(cache_slug, ep, mode, got["master"], got["variants"],
                                    got.get("sub"), got.get("sub_lang"),
                                    got.get("referer"), got.get("server"),
                                    subtitles=got["subtitles"],
                                    intro=got["intro"], outro=got["outro"])
        if actual_mode != mode:
            can_cache_actual = (actual_mode != "sub") or _has_valid_subtitles(got)
            if can_cache_actual:
                await set_episode_cache(cache_slug, ep, actual_mode, got["master"], got["variants"],
                                        got.get("sub"), got.get("sub_lang"),
                                        got.get("referer"), got.get("server"),
                                        subtitles=got["subtitles"],
                                        intro=got["intro"], outro=got["outro"])
        await _check_and_prewarm(got)
        return ok(got)
    except Exception as e:
        return fail(str(e))

def _validate_external_proxy_url(url: str) -> None:
    """Validasi keamanan URL proxy eksternal untuk mencegah SSRF (Server-Side Request Forgery).
    Menolak skema non-HTTP(S), IP private, loopback, link-local, multicast, dan localhost."""
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=400, detail="URL proxy tidak valid")
    clean_u = url.strip()
    import urllib.parse as _up
    import ipaddress as _ipa
    import socket as _sock

    p = _up.urlsplit(clean_u)
    if p.scheme.lower() not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Skema URL hanya boleh http atau https")
    hostname = (p.hostname or "").strip().lower()
    if not hostname:
        raise HTTPException(status_code=400, detail="Hostname URL tidak ditemukan")

    if hostname in ("localhost", "0.0.0.0", "127.0.0.1", "::1") or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise HTTPException(status_code=403, detail="Akses ke host lokal dilarang (SSRF protection)")

    # Pengecekan IP numerik langsung
    try:
        ip = _ipa.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise HTTPException(status_code=403, detail="Akses ke IP privat/lokal dilarang (SSRF protection)")
        return
    except ValueError:
        pass

    # Resolusi DNS untuk mendeteksi domain yang menunjuk ke IP lokal/privat
    try:
        addr_info = _sock.getaddrinfo(hostname, None, _sock.AF_UNSPEC, _sock.SOCK_STREAM)
        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            ip = _ipa.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
                # ISP DNS Poisoning bypass:
                # Bila DNS ISP lokal meresolusi domain publik ke IP sinkhole privat (10.x / 127.x / 0.0.0.0),
                # verifikasi ulang menggunakan DoH publik (_resolve_host).
                # Jika DoH meresolusi ke IP publik asli, izinkan (bukan serangan SSRF lokal).
                try:
                    from api.desync import _resolve_host
                    real_ip = _resolve_host(hostname)
                    if real_ip and real_ip != hostname:
                        rip = _ipa.ip_address(real_ip)
                        if not (rip.is_private or rip.is_loopback or rip.is_link_local or rip.is_multicast or rip.is_reserved or rip.is_unspecified):
                            continue
                except Exception:
                    pass
                raise HTTPException(status_code=403, detail=f"Resolusi domain mengarah ke IP privat/lokal ({ip_str})")
    except (_sock.gaierror, _sock.herror):
        pass


def _is_m3u8_url(url: str, ctype: str = "") -> bool:
    """Deteksi akurat apakah URL adalah playlist m3u8 atau segmen video/audio."""
    if "mpegurl" in (ctype or "").lower():
        return True
    path = url.split("?", 1)[0].lower()
    if path.endswith(".m3u8") or path.endswith("/m3u8"):
        return True
    if any(path.endswith(ext) for ext in (".ts", ".ts.jpg", ".jpg", ".jpeg", ".png", ".mp4", ".m4s", ".aac", ".mp3", ".vtt")):
        return False
    if any(p in url.lower() for p in ("/hls/playlist", "/api/hls", "format=m3u8", "output=m3u8", ".m3u8?")):
        return True
    return False


@app.get("/api/player/video")
async def proxy_video(url: str = Query(""), referer: str = Query(""), range: str = Query("")):
    # Proxy cepat: koneksi dipakai ulang, segmen di-stream (tanpa buffer penuh),
    # Range diteruskan ke upstream supaya seek tidak mengunduh ulang segmen dari awal.
    from fastapi import Request
    from fastapi.responses import StreamingResponse as _SR
    if not url.startswith("http"):
        return Response(status_code=400)
    # Sanitasi header Range: hanya izinkan bentuk "bytes=<start>-<end>" agar tidak
    # menjadi vektor request smuggling / header injection ke upstream CDN.
    range_header = ""
    if range:
        _rg = range.strip()
        if _rg.lower().startswith("bytes="):
            _rg = _rg[6:].strip()
            if _rg and all(c.isdigit() or c == "-" for c in _rg) and _rg.count("-") <= 1:
                range_header = f"bytes={_rg}"
    from api.hianime import SEG_RE, SEG_KEY, SEG_IV, STRIP_BYTES, STRIP_RE
    import re as _re
    m = SEG_RE.search(url)
    if m:
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            import base64 as _b64
            tok = m.group(1)
            s = tok.replace("-", "+").replace("_", "/")
            s += "=" * (-len(s) % 4)
            raw = _b64.b64decode(s)
            d = Cipher(algorithms.AES(SEG_KEY), modes.CBC(SEG_IV)).decryptor()
            pt = d.update(raw) + d.finalize()
            real = pt.decode("utf-8", errors="strict").strip().strip("\x00").strip()
            url = real if real.startswith("http") else url
        except Exception:
            pass

    _validate_external_proxy_url(url)

    is_m3u8 = _is_m3u8_url(url)
    media_type = "application/vnd.apple.mpegurl" if is_m3u8 else "video/mp2t"

    if not referer:
        u_low = url.lower()
        if any(h in u_low for h in ("dramahot", "drama1", "zokoanime")):
            referer = "https://zokoanime.video/"
        elif any(h in u_low for h in ("puterin", "putarin", "stream121")):
            referer = "https://puterin.biz/"
        elif any(h in u_low for h in ("anichan", "toroplay")):
            referer = "https://anichan.to/"
        elif any(h in u_low for h in ("phantomharbor", "nexabloom", "silverorbit", "megaplay", "vidtube", "vidplay",
                                      "shiora", "imgnex", "hiddenvertex", "broforgotsave", "eclipseharbor",
                                      "embermeadow", "megacloud", "rapid-cloud", "rabbitstream", "dokicloud")) or "/anime/" in u_low:
            referer = "https://megaplay.buzz/"

    # Jika host terdeteksi diblokir DPI ISP, gunakan TLS desync murni (aman dari Sangfor)
    from api.hianime import _host_from, _is_dpi_blocked_host
    host = _host_from(url)
    if _is_dpi_blocked_host(host):
        return _SR(_pipe_desync_video(url, referer, range_header=range_header), media_type=media_type,
                   headers={"Access-Control-Allow-Origin": "*"})

    return _SR(_pipe_video(url, referer, range_header=range_header), media_type=media_type,
               headers={"Access-Control-Allow-Origin": "*"})


def _rewrite_m3u8_content(txt: str, base_url: str, referer: str) -> str:
    """Tulis ulang m3u8 dan pastikan audio codec & sub-manifests (audio, subtitles, init) ter-proxy."""
    import urllib.parse as _up
    import re as _re
    base = base_url.rsplit("/", 1)[0] + "/"
    out = []
    for ln in txt.splitlines():
        s = ln.strip()
        if not s:
            out.append(ln)
            continue
        # Jika master playlist menyertakan STREAM-INF, pastikan audio codec (mp4a) ada di CODECS
        # agar browser/Hls.js tahu ada stream audio AAC dan menyiapkan audio SourceBuffer
        if s.startswith("#EXT-X-STREAM-INF:"):
            if "CODECS=" not in s:
                s += ',CODECS="avc1.64001f,mp4a.40.2"'
            elif not any(ac in s.lower() for ac in ("mp4a", "aac", "opus", "mp3")):
                s = _re.sub(r'CODECS="([^"]+)"', r'CODECS="\1,mp4a.40.2"', s)

        if s.startswith("#"):
            # Rewrite URI="..." di dalam tag seperti #EXT-X-MEDIA (audio/subtitles), #EXT-X-MAP, #EXT-X-KEY
            if "URI=" in s:
                def _rep_uri(m):
                    raw_uri = m.group(1) or m.group(2) or m.group(3)
                    absu = raw_uri if raw_uri.startswith("http") else _up.urljoin(base, raw_uri)
                    return f'URI="/api/player/video?url={_up.quote(absu, safe="")}&referer={_up.quote(referer or "", safe="")}"'
                s = _re.sub(r'URI=(?:"([^"]+)"|\'([^\']+)\'|([^,\s]+))', _rep_uri, s)
            out.append(s)
            continue

        absu = s if s.startswith("http") else _up.urljoin(base, s)
        out.append(f"/api/player/video?url={_up.quote(absu, safe='')}&referer={_up.quote(referer or '', safe='')}")
    return "\n".join(out)


async def _pipe_desync_video(url: str, referer: str, range_header: str = ""):
    """Streaming video via TLS Client Hello Desynchronization (Direct TCP 443 tanpa VPN)."""
    from api.desync import tls_desync_request, tls_desync_stream
    import asyncio
    import re as _re
    
    headers = {
        "User-Agent": HI_UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    }
    if range_header:
        headers["Range"] = range_header
    if referer:
        headers["Referer"] = referer
        orig = _re.sub(r"^(https?://[^/]+).*", r"\1", referer)
        if orig:
            headers["Origin"] = orig
    loop = asyncio.get_running_loop()
    
    # Playlist m3u8: baca penuh dan rewrite URL agar segmen tetap lewat proxy Tatap
    if _is_m3u8_url(url):
        cached_txt = _master_cache_get(url)
        if cached_txt is not None:
            yield _rewrite_m3u8_content(cached_txt, url, referer).encode("utf-8")
            return
        body = await loop.run_in_executor(None, lambda: tls_desync_request(url, headers=headers))
        try:
            txt = body.decode("utf-8", errors="strict")
        except Exception:
            raise HTTPException(status_code=502, detail="upstream desync m3u8 binary decode error")
        if "#EXTM3U" not in txt:
            raise HTTPException(status_code=502, detail="upstream desync response missing #EXTM3U")
        _master_cache_set(url, txt)
        yield _rewrite_m3u8_content(txt, url, referer).encode("utf-8")
        return

    # Segmen TS: stream per bongkah via desync TLS generator
    async for chunk in tls_desync_stream(url, headers=headers):
        if chunk:
            yield chunk


_direct_client = None

def _get_video_client(url: str):
    """Direct client murni untuk video normal (Megaplay, Otakudesu, dll.)."""
    global _direct_client
    import httpx as _hx
    if _direct_client is None:
        if os.environ.get("TATAP_IS_TV") == "1":
            limits = _hx.Limits(max_connections=30, max_keepalive_connections=20, keepalive_expiry=90.0)
        else:
            limits = _hx.Limits(max_connections=60, max_keepalive_connections=30, keepalive_expiry=90.0)
        _direct_client = _hx.AsyncClient(
            follow_redirects=True,
            timeout=_hx.Timeout(30.0, connect=15.0),
            limits=limits,
            http2=False
        )
    return _direct_client


async def _pipe_video(url: str, referer: str, range_header: str = ""):
    import urllib.parse as _up
    import asyncio as _asyncio
    import re as _re
    from api.hianime import STRIP_BYTES as _SB, STRIP_RE as _SR2
    c = _get_video_client(url)

    headers = {
        "User-Agent": HI_UA,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    }
    if range_header:
        # Teruskan Range ke upstream agar seek hanya mengunduh byte yang dibutuhkan.
        headers["Range"] = range_header
    if referer:
        headers["Referer"] = referer
        orig = _re.sub(r"^(https?://[^/]+).*", r"\1", referer)
        if orig:
            headers["Origin"] = orig

    for attempt in range(2):
        try:
            async with c.stream("GET", url, headers=headers) as r:
                if r.status_code >= 400:
                    if r.status_code in (401, 403) and attempt == 0:
                        await _asyncio.sleep(0.2)
                        from api.hianime import _host_from, _BLOCKED_DPI_HOSTS
                        _BLOCKED_DPI_HOSTS.add(_host_from(url))
                        continue
                    raise HTTPException(status_code=502, detail=f"upstream {r.status_code}")
                ctype = r.headers.get("content-type", "")
                is_playlist = _is_m3u8_url(url, ctype)
                if is_playlist:
                    # Cek cache master dulu: Hindari unduhan ulang dari CDN
                    # (resolver sudah pernah mengunduh master ini).
                    cached_txt = _master_cache_get(url)
                    if cached_txt is not None:
                        yield _rewrite_m3u8_content(cached_txt, url, referer).encode("utf-8")
                        return
                    body = await r.aread()
                    try:
                        txt = body.decode("utf-8", errors="strict")
                    except Exception:
                        raise HTTPException(status_code=502, detail="upstream m3u8 binary decode error")
                    if "#EXTM3U" not in txt:
                        raise HTTPException(status_code=502, detail="upstream response missing #EXTM3U")
                    _master_cache_set(url, txt)
                    yield _rewrite_m3u8_content(txt, url, referer).encode("utf-8")
                    return

                skipped = 0
                need_strip = bool(_SR2.search(url))
                async for chunk in r.aiter_bytes(65536):
                    if need_strip and skipped < _SB:
                        cut = min(len(chunk), _SB - skipped)
                        skipped += cut
                        chunk = chunk[cut:]
                        if not chunk:
                            continue
                    if chunk:
                        yield chunk
                return
        except HTTPException as he:
            if attempt == 0 and ("403" in str(he.detail) or "502" in str(he.detail)):
                await _asyncio.sleep(0.2)
                continue
            try:
                from api.hianime import _host_from, _BLOCKED_DPI_HOSTS
                host = _host_from(url)
                _BLOCKED_DPI_HOSTS.add(host)
                async for chunk in _pipe_desync_video(url, referer, range_header=range_header):
                    yield chunk
                return
            except Exception:
                raise he
        except Exception as e:
            if attempt == 0:
                await _asyncio.sleep(0.3)
                continue
            try:
                from api.hianime import _host_from, _BLOCKED_DPI_HOSTS
                host = _host_from(url)
                err_text = str(e).lower()
                is_known_dpi = any(k in host for k in ("dramahot", "zokoanime"))
                is_rst = any(w in err_text for w in ("connection reset", "connectionreseterror", "rst", "closed connection"))
                if is_known_dpi or is_rst:
                    _BLOCKED_DPI_HOSTS.add(host)
                async for chunk in _pipe_desync_video(url, referer, range_header=range_header):
                    yield chunk
                return
            except Exception:
                raise HTTPException(status_code=502, detail=f"upstream error: {type(e).__name__}")

async def _fetch_sub_text(target_url, ref):
    """Helper fetcher yang mendukung desync bila host terblokir DPI atau butuh referer khusus."""
    from api.hianime import _host_from, _BLOCKED_DPI_HOSTS
    h = _host_from(target_url)

    candidates = []
    t_low = target_url.lower()
    # Domain-specific smart prioritization (dramahot/zokoanime butuh origin zokoanime/dramahot)
    if any(k in t_low for k in ("dramahot", "zokoanime")) or "dramahot" in h or "zokoanime" in h:
        candidates.extend(["https://zokoanime.video/", "https://dramahot.top/"])
    if ref and ref not in candidates:
        candidates.append(ref)

    if any(k in t_low for k in ("toroplay", "anichan", "broforgotsave", "stellarfrontier", "megaplay", "megacloud", "eclipseharbor", "embermeadow", "nexabloom")) or "/anime/" in t_low:
        for m_ref in ("https://megaplay.buzz/", "https://anichan.to/", "https://megaplay.top/", "https://megacloud.tv/"):
            if m_ref not in candidates:
                candidates.append(m_ref)

    for f_ref in ("https://megaplay.buzz/", "https://megaplay.top/", "https://zokoanime.video/", "https://megacloud.blog/", "https://hianime.at/", "https://hianime.to/", ""):
        if f_ref not in candidates:
            candidates.append(f_ref)

    def _is_valid_sub(txt_str: str) -> bool:
        if not txt_str:
            return False
        t_clean = txt_str.strip()
        t_low_s = t_clean.lower()
        # Proteksi mutlak: jangan pernah menerima respons error HTML (403/502/404) sebagai subtitle
        if "<html" in t_low_s or "<head" in t_low_s or "<body" in t_low_s or "<!doctype" in t_low_s:
            return False
        if "WEBVTT" in t_clean or "-->" in t_clean:
            return True
        return len(t_clean) > 200

    last_err = None
    for r_head in candidates:
        headers = {"User-Agent": HI_UA}
        if r_head:
            headers["Referer"] = r_head

        # 1. Coba via TLS desync jika host masuk daftar DPI atau host CDN streaming
        if h in _BLOCKED_DPI_HOSTS or "dramahot" in h or "zokoanime" in h:
            try:
                from api.desync import tls_desync_request
                loop = asyncio.get_running_loop()
                raw = await loop.run_in_executor(None, lambda: tls_desync_request(target_url, headers=headers))
                txt = raw.decode("utf-8", errors="replace")
                if _is_valid_sub(txt):
                    return txt
            except Exception as e:
                last_err = e

        # 2. Coba direct request via httpx
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as c:
                r = await c.get(target_url, headers=headers)
                if r.status_code == 200 and _is_valid_sub(r.text):
                    return r.text
        except Exception as e:
            last_err = e
            # Jika direct gagal (koneksi terputus/RST), coba desync
            try:
                from api.desync import tls_desync_request
                _BLOCKED_DPI_HOSTS.add(h)
                loop = asyncio.get_running_loop()
                raw = await loop.run_in_executor(None, lambda: tls_desync_request(target_url, headers=headers))
                txt = raw.decode("utf-8", errors="replace")
                if _is_valid_sub(txt):
                    return txt
            except Exception as e2:
                last_err = e2

    if last_err:
        raise last_err
    raise RuntimeError("Gagal mengambil subtitle: upstream mengembalikan respons kosong atau tidak valid")


_SUB_INFLIGHT = {}


def _is_valid_id_subtitle(vtt_text: str) -> bool:
    """True jika subtitle memiliki kosakata bahasa Indonesia wajar (mencegah cache poisoning teks sumber atau kuota MyMemory)."""
    if not vtt_text or len(vtt_text.strip()) < 50:
        return True
    if "MYMEMORY WARNING" in vtt_text or "translated.net" in vtt_text:
        return False
    return bool(re.search(r"\b(yang|dan|tidak|aku|kamu|di|ini|itu|bisa|ada|nggak|udah|cuma|banget|siapa|kenapa)\b", vtt_text, re.IGNORECASE))


async def _get_validated_subtitle_cache(key: str, lang: str = "id", ttl: int = 7 * 24 * 3600):
    """Ambil cache subtitle dengan validasi anti-poisoning."""
    hit = await get_subtitle_cache(key, ttl=ttl)
    if hit:
        if (lang or "").lower() == "id" and not _is_valid_id_subtitle(hit):
            try:
                await delete_subtitle_cache(key)
            except Exception:
                pass
            return None
        if (lang or "").lower() == "id":
            from api.translate import apply_universal_lexicon_id
            hit = apply_universal_lexicon_id(hit)
        return hit
    return None


async def _prewarm_sub_translation(url: str, referer: str, src: str = "en", lang: str = "id", req_mode: str = "gtx+", dual: int = 0):
    """Prefetch subtitle translate di latar belakang jika belum ada di cache."""
    if not url or not url.startswith("http") or not lang or lang == src:
        return
    try:
        _validate_external_proxy_url(url)
    except HTTPException:
        return
    import hashlib
    base_hash = hashlib.sha1((url + "|" + (referer or "") + "|" + lang).encode("utf-8")).hexdigest()
    key_gtx = "sub2|gtx|" + base_hash
    key_gtxplus = "sub2|gtx+|" + base_hash
    key_llm = "sub2|llm|" + base_hash
    hit = await _get_validated_subtitle_cache(key_gtx, lang=lang)
    if hit is not None:
        return
    hit = await _get_validated_subtitle_cache(key_gtxplus, lang=lang)
    if hit is not None:
        return

    job_key = f"{base_hash}|{lang}|{req_mode}|dual={dual}"
    fut = _SUB_INFLIGHT.get(job_key)
    if fut is None:
        try:
            from api.translate import log_translate
            log_translate(f"Prefetch subtitle [{lang}] dimulai di background...")
        except Exception:
            pass
        fut = asyncio.ensure_future(_translate_sub_job(url, referer, src, lang, key_llm, key_gtxplus, _fetch_sub_text, key_gtx=key_gtx, requested_mode=req_mode))
        _SUB_INFLIGHT[job_key] = fut

        def _pop_and_retrieve(f, k=job_key):
            _SUB_INFLIGHT.pop(k, None)
            try:
                f.exception()
            except Exception:
                pass

        fut.add_done_callback(_pop_and_retrieve)


@app.get("/favicon.ico")
@app.head("/favicon.ico")
async def favicon():
    fav = os.path.join(frontend_dir, "favicon.ico")
    if os.path.exists(fav):
        return FileResponse(fav, media_type="image/x-icon")
    return Response(status_code=204)


@app.get("/api/player/sub")
async def proxy_sub(url: str = Query(""),
                   referer: str = Query(""),
                   lang: str = Query("", pattern="^(en|id|ja|es|fr|de|pt|ko|zh)$|^$"),
                   src: str = Query("en", pattern="^(en|ja|es|fr|de|pt|ko|zh)$"),
                   mode: str = Query("", pattern="^(gtx|gtx\\+|gtx\\+_dual|aigtx|ai|os_merge|os_dual|smart_merge|)$"),
                   dual: bool = Query(False),
                   title: str = Query(""),
                   slug: str = Query(""),
                   ep: int = Query(1),
                   os_file_id: str = Query(""),
                   refresh: bool = Query(False)):
    """Proxy subtitle VTT. Menjalankan translasi Smart Lexicon atau Smart Fansub & Merge
    dengan deduplikasi inflight dan proteksi cache poisoning."""
    if not url.startswith("http"):
        return Response(status_code=400)
    _validate_external_proxy_url(url)

    is_os_mode = mode in ("os_merge", "os_dual", "smart_merge")
    # Hapus mode bilingual dan opsi terjemahan mentah sesuai direktif
    is_dual = False
    clean_mode = "gtx+" if mode in ("gtx", "gtx+", "gtx+_dual", "aigtx") else (mode or "gtx+")

    # Lang kosong atau sama dengan sumber (dan bukan mode Smart Merge) -> return source apa adanya
    if (not lang or lang == src) and not is_os_mode:
        try:
            content = await _fetch_sub_text(url, referer)
            return Response(content=content, media_type="text/vtt")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"gagal mengambil subtitle: {e}")

    import hashlib
    base_hash = hashlib.sha1(
        (url + "|" + (referer or "") + "|" + (lang or "id")).encode("utf-8")
    ).hexdigest()
    os_ctx_hash = hashlib.sha1(
        f"{url}|{slug}|{title}|{ep}|{os_file_id}|{lang or 'id'}".encode("utf-8")
    ).hexdigest()
    key_gtxplus = "sub2|gtx+|" + base_hash
    key_aigtx = "sub2|aigtx|" + base_hash
    key_gtx = "sub2|gtx|" + base_hash
    key_llm = "sub2|llm|" + base_hash
    key_os_merge = "sub2|os_merge|" + os_ctx_hash

    if refresh:
        for k in (key_gtx, key_gtxplus, key_aigtx, key_llm, key_os_merge, "sub2|mt|" + base_hash):
            try:
                await delete_subtitle_cache(k)
            except Exception:
                pass

    if is_os_mode:
        target_os_key = key_os_merge
        if not refresh:
            hit_os = await _get_validated_subtitle_cache(target_os_key, lang=lang or "id")
            if hit_os:
                resp = Response(content=hit_os, media_type="text/vtt")
                resp.headers["X-Translate-Tier"] = "cached-os_merge"
                return resp

        os_job_key = f"os|{os_ctx_hash}"
        fut_os = _SUB_INFLIGHT.get(os_job_key)
        if fut_os is None:
            fut_os = asyncio.ensure_future(
                _opensubtitles_merge_sub_job(
                    url=url,
                    referer=referer,
                    src=src,
                    lang=lang or "id",
                    title=title,
                    slug=slug,
                    ep=ep,
                    os_file_id=os_file_id,
                    is_dual=False,
                    cache_key=target_os_key,
                    fallback_key_gtxplus=key_gtxplus,
                )
            )
            _SUB_INFLIGHT[os_job_key] = fut_os
            fut_os.add_done_callback(lambda _f, k=os_job_key: _SUB_INFLIGHT.pop(k, None))

        new_text, tier = await asyncio.shield(fut_os)
        resp = Response(content=new_text, media_type="text/vtt")
        resp.headers["X-Translate-Tier"] = tier.get("level", "os_merge")
        if tier.get("os_filename"):
            clean_fn = re.sub(r"[^\w.\-\[\]() ]", "", str(tier["os_filename"]))[:80]
            resp.headers["X-OpenSubtitles-File"] = clean_fn
        if tier.get("merge_stats"):
            st = tier["merge_stats"]
            resp.headers["X-OpenSubtitles-Merge"] = f"os={st.get('os_count',0)},snapped={st.get('snapped',0)},gaps={st.get('gap_filled',0)},offset={st.get('offset',0.0)}s"
        return resp

    req_mode = "gtx+" if clean_mode in ("gtx+", "aigtx") else (clean_mode or "gtx+")

    # Periksa cache lokal jika tidak dalam mode refresh
    if not refresh:
        if req_mode in ("gtx+", "aigtx"):
            hit = await _get_validated_subtitle_cache(key_gtxplus, lang=lang)
            if not hit:
                hit = await _get_validated_subtitle_cache(key_aigtx, lang=lang)
            if not hit:
                hit = await _get_validated_subtitle_cache("sub2|mt|" + base_hash, lang=lang)
            if hit:
                resp = Response(content=hit, media_type="text/vtt")
                resp.headers["X-Translate-Tier"] = "cached-gtx+"
                return resp
        elif req_mode == "ai":
            hit = await _get_validated_subtitle_cache(key_llm, lang=lang)
            if hit:
                resp = Response(content=hit, media_type="text/vtt")
                resp.headers["X-Translate-Tier"] = "cached-llm"
                return resp
        else:
            for k, label in ((key_gtxplus, "cached-gtx+"), (key_aigtx, "cached-gtx+"), (key_llm, "cached-llm")):
                hit = await _get_validated_subtitle_cache(k, lang=lang)
                if hit:
                    resp = Response(content=hit, media_type="text/vtt")
                    resp.headers["X-Translate-Tier"] = label
                    return resp

    # Satukan eksekusi translasi agar tidak menduplikasi request bersamaan untuk mode yang sama
    job_key = f"{base_hash}|{lang}|{req_mode}|dual=0"
    fut = _SUB_INFLIGHT.get(job_key)
    if fut is None:
        fut = asyncio.ensure_future(
            _translate_sub_job(url, referer, src, lang, key_llm, key_gtxplus, _fetch_sub_text, key_gtx=key_gtx, requested_mode=req_mode, is_dual=False, key_dual="")
        )
        _SUB_INFLIGHT[job_key] = fut

        def _pop_and_retrieve(f, k=job_key):
            _SUB_INFLIGHT.pop(k, None)
            try:
                f.exception()
            except Exception:
                pass

        fut.add_done_callback(_pop_and_retrieve)

    try:
        new_text, tier = await asyncio.shield(fut)
    except HTTPException:
        raise
    except Exception as e:
        # Fallback ke teks asli tanpa menyimpan ke cache
        try:
            raw_text = await _fetch_sub_text(url, referer)
            resp = Response(content=raw_text, media_type="text/vtt")
            resp.headers["X-Translate-Tier"] = "source-fallback"
            resp.headers["X-Translate-Error"] = str(e)[:120]
            return resp
        except Exception:
            raise HTTPException(status_code=502, detail=f"gagal memproses subtitle: {e}")

    resp = Response(content=new_text, media_type="text/vtt")
    resp.headers["X-Translate-Tier"] = tier.get("level", "source") + ("-dual" if is_dual else "")
    if tier.get("model"):
        resp.headers["X-Translate-Model"] = re.sub(r"[^\w.:/\-]", "", str(tier["model"]))[:60]
    if tier.get("gtx_lines"):
        resp.headers["X-Translate-Mixed"] = f'{tier.get("gtx_lines")}/{tier.get("total", 0)}'
    if tier.get("error"):
        clean_err = re.sub(r"[\r\n]+", " ", str(tier["error"])).strip()
        resp.headers["X-Translate-Error"] = clean_err.encode("latin-1", "replace").decode("latin-1")[:200]
    return resp


async def _llm_enabled():
    """Tier aktif kalau ada API key, atau endpoint LLM lokal (Ollama di localhost)."""
    from api.translate import is_local_llm
    apikey = await get_setting("translate_apikey", "")
    apiurl = await get_setting("translate_apiurl", "")
    return bool(apikey) or is_local_llm(apiurl)


async def _translate_sub_job(url, referer, src, lang, key_llm, key_gtxplus, fetcher, key_gtx=None, requested_mode="gtx", is_dual=False, key_dual=None):
    """Fetch + translate + cache. Return (vtt_text, tier_dict)."""
    if not key_gtx:
        import hashlib
        b_hash = hashlib.sha1((url + "|" + (referer or "") + "|" + lang).encode("utf-8")).hexdigest()
        key_gtx = "sub2|gtx|" + b_hash
    try:
        text = await fetcher(url, referer)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"gagal mengambil subtitle: {e}")
    try:
        from api.translate import parse_vtt, build_vtt, build_bilingual_vtt, merge_overlapping_cues
        raw_cues = parse_vtt(text)
        cues = merge_overlapping_cues(raw_cues)
        if not cues:
            return text, {"level": "source", "error": "Subtitle kosong atau format tidak didukung"}
        tier = await _translate_with_fallback(cues, src, lang, requested_mode=requested_mode)
        if is_dual:
            new_text = build_bilingual_vtt(tier["cues"], cues)
        else:
            new_text = build_vtt(tier["cues"])
    except Exception as e:
        return text, {"cues": None, "level": "source", "error": str(e)}

    lvl = tier.get("level")
    # PENTING: Dilarang menyimpan teks sumber (untranslated) atau hasil kaku MyMemory ke dalam cache berkualitas tinggi
    if lvl not in ("source", "source-fallback", "tier4", "mymemory"):
        if (lang or "").lower() != "id" or _is_valid_id_subtitle(new_text):
            if is_dual and key_dual:
                await set_subtitle_cache(key_dual, new_text)
            elif lvl in ("tier1", "gtx"):
                await set_subtitle_cache(key_gtx, new_text)
                await set_subtitle_cache(key_gtxplus, new_text)
            elif lvl in ("tier2", "gtx+", "aigtx"):
                await set_subtitle_cache(key_gtxplus, new_text)
                await set_subtitle_cache(key_gtx, new_text)
            elif lvl in ("tier3", "ai"):
                total = max(1, tier.get("total") or len(cues))
                if tier.get("llm_lines", 0) / total >= 0.8:
                    await set_subtitle_cache(key_llm, new_text)
                else:
                    await set_subtitle_cache(key_gtxplus, new_text)
                    await set_subtitle_cache(key_gtx, new_text)
    return new_text, tier


async def _translate_with_fallback(cues, src, tgt, requested_mode="gtx"):
    """Multi-tier translate dengan penanganan prioritas sesuai mode yang diminta:
    Mode AI:
      1. AI Fansub LLM (jika aktif)
      2. Fallback: Google Translate GTX+ (Smart Fansub & Scene Detection)
      3. Fallback: Google Translate GTX murni
    Mode GTX+ / AIGTX:
      1. Google Translate GTX+ (Smart Fansub & Scene Detection)
      2. Fallback: AI Fansub LLM (jika aktif)
      3. Fallback: Google Translate GTX murni
    Mode GTX:
      1. Google Translate GTX murni
      2. Fallback: Google Translate GTX+
      3. Fallback: AI Fansub LLM (jika aktif)
    Safety net: source original
    """
    from api.translate import call_openai_translate, call_gtx_translate
    last_err = ""

    if requested_mode == "ai":
        # 1. Coba AI Fansub jika ada API key atau LLM lokal
        if await _llm_enabled():
            apikey = await get_setting("translate_apikey", "")
            model = await get_setting("translate_model", "gemini-2.0-flash")
            apiurl = await get_setting("translate_apiurl", "https://generativelanguage.googleapis.com/v1beta/openai")
            try:
                translated, stats = await call_openai_translate(cues, src, tgt, apikey, model, apiurl)
                return {"cues": translated, "level": "tier3", "engine": "ai", **stats}
            except Exception as e:
                last_err = f"AI LLM error: {e}"
                print(f"[TRANSLATE AI LLM ERROR] {e}")
        else:
            last_err = "AI LLM belum disetel (masukkan API key di pengaturan)"
            print(f"[TRANSLATE AI LLM] {last_err}")

        # Fallback ke Google GTX+
        try:
            translated = await call_gtx_translate(cues, src, tgt, mode="gtx+")
            return {"cues": translated, "level": "tier2", "engine": "gtx+", "error": last_err}
        except Exception as e:
            last_err = f"{last_err} | GTX+ error: {e}"
            print(f"[TRANSLATE GTX+ ERROR] {e}")

        # Fallback ke Google GTX
        try:
            translated = await call_gtx_translate(cues, src, tgt, mode="gtx")
            return {"cues": translated, "level": "tier1", "engine": "gtx", "error": last_err}
        except Exception as e:
            last_err = f"{last_err} | GTX error: {e}"
            print(f"[TRANSLATE GTX ERROR] {e}")

    elif requested_mode in ("gtx+", "aigtx"):
        # 1. Coba Google GTX+ (Smart Fansub & Scene Detection)
        try:
            translated = await call_gtx_translate(cues, src, tgt, mode="gtx+")
            return {"cues": translated, "level": "tier2", "engine": "gtx+"}
        except Exception as e:
            last_err = f"GTX+ error: {e}"
            print(f"[TRANSLATE GTX+ ERROR] {e}")

        # 2. Coba AI jika aktif
        if await _llm_enabled():
            apikey = await get_setting("translate_apikey", "")
            model = await get_setting("translate_model", "gemini-2.0-flash")
            apiurl = await get_setting("translate_apiurl", "https://generativelanguage.googleapis.com/v1beta/openai")
            try:
                translated, stats = await call_openai_translate(cues, src, tgt, apikey, model, apiurl)
                return {"cues": translated, "level": "tier3", "engine": "ai", **stats}
            except Exception as e:
                last_err = f"{last_err} | AI LLM error: {e}"
                print(f"[TRANSLATE AI LLM ERROR] {e}")

        # 3. Fallback ke Google GTX
        try:
            translated = await call_gtx_translate(cues, src, tgt, mode="gtx")
            return {"cues": translated, "level": "tier1", "engine": "gtx", "error": last_err}
        except Exception as e:
            last_err = f"{last_err} | GTX error: {e}"
            print(f"[TRANSLATE GTX ERROR] {e}")

    else:
        # 1. Coba Google GTX murni
        try:
            translated = await call_gtx_translate(cues, src, tgt, mode="gtx")
            return {"cues": translated, "level": "tier1", "engine": "gtx"}
        except Exception as e:
            last_err = f"Google Translate error: {e}"
            print(f"[TRANSLATE GOOGLE GTX ERROR] {e}")

        # 2. Fallback ke Google GTX+
        try:
            translated = await call_gtx_translate(cues, src, tgt, mode="gtx+")
            return {"cues": translated, "level": "tier2", "engine": "gtx+", "error": last_err}
        except Exception as e:
            last_err = f"{last_err} | GTX+ error: {e}"
            print(f"[TRANSLATE GTX+ ERROR] {e}")

        # 3. Coba AI jika aktif
        if await _llm_enabled():
            apikey = await get_setting("translate_apikey", "")
            model = await get_setting("translate_model", "gemini-2.0-flash")
            apiurl = await get_setting("translate_apiurl", "https://generativelanguage.googleapis.com/v1beta/openai")
            try:
                translated, stats = await call_openai_translate(cues, src, tgt, apikey, model, apiurl)
                return {"cues": translated, "level": "tier3", "engine": "ai", **stats}
            except Exception as e:
                last_err = f"{last_err} | AI LLM error: {e}"
                print(f"[TRANSLATE AI LLM ERROR] {e}")

    # Return cues asli jika semua penerjemah gagal
    return {"cues": cues, "level": "source", "error": last_err}


async def _opensubtitles_merge_sub_job(
    url: str,
    referer: str,
    src: str,
    lang: str,
    title: str,
    slug: str,
    ep: int,
    os_file_id: str,
    is_dual: bool,
    cache_key: str,
    fallback_key_gtxplus: str,
):
    """Cari dan unduh subtitle khusus Bahasa Indonesia dari AnimeTosho (prioritas fansub & CR/Netflix resmi)
    atau OpenSubtitles, lalu lakukan Smart Merge + Smart Lexicon + Scene Detector dengan subtitle bawaan anime.
    Jika tidak tersedia di AnimeTosho/OpenSubtitles, fallback otomatis ke Smart GTX+."""
    from api.translate import (
        parse_vtt,
        build_vtt,
        merge_overlapping_cues,
        estimate_optimal_offset,
        find_unmatched_builtin_cues,
        merge_opensubtitles_with_builtin,
        call_gtx_translate,
        log_translate,
        automate_opensubtitles_pronouns,
        apply_universal_lexicon_id,
    )
    from api.animetosho import (
        search_animetosho_indonesian,
        download_animetosho_sub_text,
    )
    from api.opensubtitles import (
        search_opensubtitles,
        download_opensubtitle_text,
        strip_opensubtitles_ads,
    )

    loop = asyncio.get_running_loop()
    target_lang = (lang or "id").lower()

    # 1. Ambil subtitle bawaan anime (builtin_cues)
    builtin_text = ""
    builtin_cues = []
    if url and url.startswith("http"):
        try:
            builtin_text = await _fetch_sub_text(url, referer)
            builtin_cues = merge_overlapping_cues(parse_vtt(builtin_text))
        except Exception as e:
            log_translate(f"[Smart Fansub & Merge] Gagal mengambil subtitle bawaan: {e}")

    # 2. Cari & unduh subtitle khusus Bahasa Indonesia (AnimeTosho -> OpenSubtitles)
    picked_cand = None
    ext_cues = []

    # Kasus 2a: os_file_id diberikan secara spesifik
    if os_file_id:
        try:
            str_fid = str(os_file_id).strip()
            if str_fid.startswith("at_") or "animetosho" in str_fid:
                clean_fid = str_fid.replace("at_", "")
                raw_txt = await loop.run_in_executor(
                    None,
                    lambda: download_animetosho_sub_text("", clean_fid),
                )
                picked_cand = {"source": "AnimeTosho", "filename": f"AnimeTosho_{clean_fid}.ass", "file_id": clean_fid}
            else:
                raw_txt = await loop.run_in_executor(
                    None,
                    lambda: download_opensubtitle_text(file_id=str_fid),
                )
                picked_cand = {"source": "OpenSubtitles", "filename": f"OpenSubtitles_{str_fid}.srt", "file_id": str_fid}
            ext_cues = strip_opensubtitles_ads(parse_vtt(raw_txt))
        except Exception as e:
            log_translate(f"[Smart Fansub & Merge] Gagal unduh file_id={os_file_id}: {e}")

    # Kasus 2b: Pencarian otomatis AnimeTosho (prioritas 1) lalu OpenSubtitles (prioritas 2)
    if not ext_cues and target_lang == "id":
        try:
            # 2b.1 Cek AnimeTosho
            at_cands = await loop.run_in_executor(
                None,
                lambda: search_animetosho_indonesian(title=title, slug=slug, ep=ep),
            )
            if at_cands:
                picked_cand = at_cands[0]
                raw_txt = await loop.run_in_executor(
                    None,
                    lambda: download_animetosho_sub_text(picked_cand.get("url", ""), picked_cand.get("file_id", "")),
                )
                ext_cues = strip_opensubtitles_ads(parse_vtt(raw_txt))
                if ext_cues:
                    log_translate(f"[Smart Fansub & Merge] Ditemukan di AnimeTosho: {picked_cand.get('filename')}")
        except Exception as e:
            log_translate(f"[Smart Fansub & Merge] Gagal pencarian AnimeTosho: {e}")

        # 2b.2 Jika AnimeTosho belum tersedia, cari di OpenSubtitles (khusus ID)
        if not ext_cues:
            try:
                os_cands = await loop.run_in_executor(
                    None,
                    lambda: search_opensubtitles(title=title, slug=slug, ep=ep, lang="id"),
                )
                id_os_cands = [c for c in os_cands if (c.get("lang") or "").lower() in ("id", "ind", "indonesian")]
                if id_os_cands:
                    picked_cand = id_os_cands[0]
                    raw_txt = await loop.run_in_executor(
                        None,
                        lambda: download_opensubtitle_text(
                            file_id=picked_cand.get("file_id", ""),
                            url=picked_cand.get("url", ""),
                            backup_url=picked_cand.get("backup_url", ""),
                        ),
                    )
                    ext_cues = strip_opensubtitles_ads(parse_vtt(raw_txt))
                    if ext_cues:
                        log_translate(f"[Smart Fansub & Merge] Ditemukan di OpenSubtitles: {picked_cand.get('filename')}")
            except Exception as e:
                log_translate(f"[Smart Fansub & Merge] Gagal pencarian OpenSubtitles: {e}")

    # 3. Jika subtitle eksternal Bahasa Indonesia ditemukan, lakukan Smart Merge
    if ext_cues and target_lang == "id":
        # Jalankan Smart Scene Detector untuk kata ganti (saya vs aku)
        ext_cues = automate_opensubtitles_pronouns(ext_cues, target_lang="id")

        offset = estimate_optimal_offset(builtin_cues, ext_cues) if builtin_cues else 0.0
        translated_gaps = {}

        # Cari cue pada subtitle bawaan (Signs, OP/ED, Preview) yang tidak ada di external sub
        if builtin_cues:
            unmatched_idx, unmatched_cues = find_unmatched_builtin_cues(builtin_cues, ext_cues, offset=offset)
            if unmatched_cues and len(unmatched_cues) <= 180:
                try:
                    tr_gaps = await call_gtx_translate(unmatched_cues, src or "en", "id", mode="gtx+")
                    for idx_b, tr_c in zip(unmatched_idx, tr_gaps):
                        translated_gaps[idx_b] = tr_c.get("text", "")
                except Exception:
                    pass

        merged_cues, stats = merge_opensubtitles_with_builtin(
            builtin_cues=builtin_cues,
            os_cues=ext_cues,
            merge_mode="hybrid",
            translated_gaps=translated_gaps,
            offset=offset,
            target_lang="id",
        )
        new_text = build_vtt(merged_cues)
        if cache_key and _is_valid_id_subtitle(new_text):
            await set_subtitle_cache(cache_key, new_text)

        src_name = (picked_cand.get("source") or "Fansub") if picked_cand else "Fansub"
        fn = (picked_cand.get("filename") or "Subtitle") if picked_cand else "Subtitle"
        log_translate(
            f"[Smart Fansub & Merge] Sukses merge [{src_name}] '{fn}' "
            f"(Count={stats['os_count']}, Snapped={stats['snapped']}, GapsFilled={stats['gap_filled']}, Offset={stats['offset']}s)"
        )
        return new_text, {
            "level": "os_merge",
            "source": src_name,
            "os_filename": fn,
            "merge_stats": stats,
        }

    # 4. Fallback: Jika belum ada subtitle ID di AnimeTosho/OpenSubtitles, gunakan Smart GTX+ bawaan
    if builtin_cues:
        tier = await _translate_with_fallback(builtin_cues, src or "en", target_lang, requested_mode="gtx+")
        new_text = build_vtt(tier.get("cues") or builtin_cues)
        if fallback_key_gtxplus and (target_lang != "id" or _is_valid_id_subtitle(new_text)):
            await set_subtitle_cache(fallback_key_gtxplus, new_text)
        return new_text, {
            "level": "os_fallback_gtx+",
            "error": "Subtitle belum tersedia di AnimeTosho maupun OpenSubtitles, menggunakan Smart GTX+ Bawaan",
        }

    raise HTTPException(status_code=404, detail="Subtitle tidak ditemukan baik di AnimeTosho, OpenSubtitles, maupun bawaan stream")


@app.get("/api/subtitles/opensubtitles")
@app.get("/api/subtitles/external")
async def api_search_external_subtitles(
    title: str = Query(""),
    slug: str = Query(""),
    ep: int = Query(1),
    season: int = Query(0),
    lang: str = Query("id"),
):
    """Cari daftar subtitle khusus Bahasa Indonesia yang tersedia di AnimeTosho dan OpenSubtitles."""
    try:
        from api.animetosho import search_animetosho_indonesian
        from api.opensubtitles import search_opensubtitles
        loop = asyncio.get_running_loop()

        at_task = loop.run_in_executor(None, lambda: search_animetosho_indonesian(title=title, slug=slug, ep=ep, season=season or 1))
        os_task = loop.run_in_executor(None, lambda: search_opensubtitles(title=title, slug=slug, ep=ep, season=season, lang="id"))
        at_items, os_items = await asyncio.gather(at_task, os_task, return_exceptions=True)

        items = []
        if isinstance(at_items, list):
            items.extend(at_items)
        if isinstance(os_items, list):
            for it in os_items:
                if (it.get("lang") or "id").lower() in ("id", "ind", "indonesian"):
                    it["source"] = "OpenSubtitles"
                    items.append(it)

        return ok({"items": items, "count": len(items), "title": title, "slug": slug, "ep": ep})
    except Exception as e:
        return fail(f"Gagal mencari subtitle eksternal: {e}")


@app.post("/api/player/sub_opensubtitles_merge")
@app.post("/api/player/sub_external_merge")
async def api_merge_external_subtitle(body: dict = None):
    """Unduh subtitle spesifik dari AnimeTosho atau OpenSubtitles dan lakukan Smart Merge."""
    body = body or {}
    file_id = str(body.get("file_id") or body.get("id") or "").strip()
    os_url = str(body.get("os_url") or body.get("url") or "").strip()
    backup_url = str(body.get("backup_url") or "").strip()
    source = str(body.get("source") or "").strip().lower()
    filename = str(body.get("filename") or f"Subtitle_{file_id}.srt").strip()
    target_lang = str(body.get("lang") or "id").strip().lower()
    base_sub_url = str(body.get("base_sub_url") or "").strip()
    referer = str(body.get("referer") or "").strip()

    if not file_id and not os_url:
        return fail("file_id atau os_url subtitle wajib diisi")

    try:
        from api.translate import (
            parse_vtt,
            build_vtt,
            merge_overlapping_cues,
            estimate_optimal_offset,
            find_unmatched_builtin_cues,
            merge_opensubtitles_with_builtin,
            call_gtx_translate,
            automate_opensubtitles_pronouns,
            apply_universal_lexicon_id,
        )
        from api.opensubtitles import download_opensubtitle_text, strip_opensubtitles_ads
        from api.animetosho import download_animetosho_sub_text

        loop = asyncio.get_running_loop()
        is_animetosho = "animetosho" in source or "animetosho" in os_url or file_id.startswith("at_")

        if is_animetosho:
            clean_fid = file_id.replace("at_", "") if file_id.startswith("at_") else file_id
            raw_txt = await loop.run_in_executor(
                None,
                lambda: download_animetosho_sub_text(url=os_url, file_id=clean_fid),
            )
        else:
            raw_txt = await loop.run_in_executor(
                None,
                lambda: download_opensubtitle_text(file_id=file_id, url=os_url, backup_url=backup_url),
            )

        ext_cues = strip_opensubtitles_ads(parse_vtt(raw_txt))
        if not ext_cues:
            return fail("File subtitle kosong atau tidak valid")

        if target_lang == "id":
            ext_cues = automate_opensubtitles_pronouns(ext_cues, target_lang="id")

        builtin_cues = []
        if base_sub_url and base_sub_url.startswith("http"):
            try:
                _validate_external_proxy_url(base_sub_url)
                base_txt = await _fetch_sub_text(base_sub_url, referer)
                builtin_cues = merge_overlapping_cues(parse_vtt(base_txt))
            except Exception:
                pass

        offset = estimate_optimal_offset(builtin_cues, ext_cues) if builtin_cues else 0.0
        translated_gaps = {}
        if builtin_cues and target_lang == "id":
            unmatched_idx, unmatched_cues = find_unmatched_builtin_cues(builtin_cues, ext_cues, offset=offset)
            if unmatched_cues and len(unmatched_cues) <= 180:
                try:
                    tr_gaps = await call_gtx_translate(unmatched_cues, "en", "id", mode="gtx+")
                    for idx_b, tr_c in zip(unmatched_idx, tr_gaps):
                        translated_gaps[idx_b] = tr_c.get("text", "")
                except Exception:
                    pass

        merged_cues, stats = merge_opensubtitles_with_builtin(
            builtin_cues=builtin_cues,
            os_cues=ext_cues,
            merge_mode="hybrid",
            translated_gaps=translated_gaps,
            offset=offset,
            target_lang=target_lang,
        )
        norm_vtt = build_vtt(merged_cues)

        import hashlib
        sub_id = hashlib.sha1(f"ext_merged|{file_id}|{base_sub_url}".encode("utf-8")).hexdigest()[:16]
        await set_subtitle_cache(f"custom|{sub_id}", norm_vtt)

        prov_tag = "AnimeTosho" if is_animetosho else "OpenSubtitles"
        return ok({
            "id": sub_id,
            "url": f"/api/player/sub_custom?id={sub_id}",
            "cues_count": len(merged_cues),
            "lang": target_lang,
            "label": f"[{prov_tag}] {filename}",
            "stats": stats,
        })
    except Exception as e:
        return fail(f"Gagal mengunduh/merge subtitle eksternal: {e}")


@app.post("/api/player/sub_custom")
async def upload_custom_sub(body: dict = None):
    """Menerima subtitle kustom (.srt atau .vtt) dari teks upload atau URL eksternal,
    menormalisasikannya menjadi format WebVTT standar, dan mengembalikannya untuk diputar.
    """
    body = body or {}
    text = (body.get("text") or "").strip()
    url = (body.get("url") or "").strip()
    filename = (body.get("filename") or "").strip()
    lang = (body.get("lang") or "en").strip().lower()
    label = (body.get("label") or "").strip()

    if not text and url:
        try:
            _validate_external_proxy_url(url)
            text = await _fetch_sub_text(url, "")
        except Exception as e:
            return fail(f"Gagal mengunduh subtitle dari URL: {e}")

    if not text:
        return fail("Teks subtitle atau URL kosong")

    try:
        from api.translate import parse_vtt, build_vtt, merge_overlapping_cues
        raw_cues = parse_vtt(text)
        cues = merge_overlapping_cues(raw_cues)
        if not cues:
            return fail("Format subtitle tidak dikenali atau tidak memiliki cue valid (.srt / .vtt / .ass / .ssa)")
        norm_vtt = build_vtt(cues)
    except Exception as e:
        return fail(f"Gagal memproses format subtitle: {e}")

    import hashlib
    sub_id = hashlib.sha1(norm_vtt.encode("utf-8")).hexdigest()[:16]
    cache_key = f"custom|{sub_id}"
    await set_subtitle_cache(cache_key, norm_vtt)

    clean_label = label or (f"{filename}" if filename else "Subtitle Kustom")
    return ok({
        "id": sub_id,
        "url": f"/api/player/sub_custom?id={sub_id}",
        "cues_count": len(cues),
        "lang": lang,
        "label": clean_label
    })


@app.get("/api/player/sub_custom")
async def get_custom_sub(id: str = Query(""),
                         url: str = Query(""),
                         lang: str = Query(""),
                         src: str = Query("en"),
                         mode: str = Query(""),
                         refresh: bool = Query(False)):
    """Mengambil atau menerjemahkan subtitle kustom yang telah dinormalisasi."""
    vtt_text = None
    if id:
        vtt_text = await get_subtitle_cache(f"custom|{id}")
    elif url:
        _validate_external_proxy_url(url)
        try:
            vtt_text = await _fetch_sub_text(url, "")
            from api.translate import parse_vtt, build_vtt
            cues = parse_vtt(vtt_text)
            if cues:
                vtt_text = build_vtt(cues)
        except Exception:
            pass

    if not vtt_text:
        raise HTTPException(status_code=404, detail="Subtitle kustom tidak ditemukan")

    # Jika pengguna meminta translasi autosub (misal dari English ke Indonesian)
    if lang and lang.lower() != src.lower():
        from api.translate import parse_vtt, build_vtt
        import hashlib
        is_dual = False
        clean_mode = "gtx+" if mode in ("gtx", "gtx+", "gtx+_dual", "aigtx") else (mode or "gtx+")
        cache_id = id or hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        tr_hash = hashlib.sha1(f"custom_tr|{cache_id}|{lang}|{clean_mode}".encode("utf-8")).hexdigest()
        key_tr = f"sub2|custom|{tr_hash}"

        if not refresh:
            cached_tr = await _get_validated_subtitle_cache(key_tr, lang=lang)
            if cached_tr:
                resp = Response(content=cached_tr, media_type="text/vtt; charset=utf-8")
                resp.headers["X-Translate-Tier"] = "cached-custom-tr"
                return resp

        try:
            cues = parse_vtt(vtt_text)
            tier = await _translate_with_fallback(cues, src, lang, requested_mode=clean_mode or "gtx+")
            new_text = build_vtt(tier.get("cues") or cues)
            if tier.get("level") not in ("source", "source-fallback"):
                await set_subtitle_cache(key_tr, new_text)
            resp = Response(content=new_text, media_type="text/vtt; charset=utf-8")
            resp.headers["X-Translate-Tier"] = str(tier.get("level", "gtx+"))
            return resp
        except Exception as e:
            pass

    return Response(content=vtt_text, media_type="text/vtt; charset=utf-8")


def find_mpv_binary():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(root_dir, "bin", "mpv.exe"),
        os.path.join(root_dir, "bin", "mpv"),
        os.path.join(root_dir, "mpv", "mpv.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    import shutil
    return shutil.which("mpv.exe" if sys.platform == "win32" else "mpv")

@app.post("/api/play-mpv")
async def play_mpv(body: dict = None):
    body = body or {}
    slug, ep, mode = body.get("slug", ""), int(body.get("ep", 1)), body.get("mode", "sub")
    quality = body.get("quality") or await get_setting("quality", "best")
    # Opsional: user pilih subtitle spesifik via UI ("sub_url" berisi URL track
    # yang aktif). Backend tetap attach seluruh subtitles[] ke MPV (--sub-file
    # bisa lebih dari satu) supaya user bisa cycle lewat tombol 'j'.
    preferred_sub_url = body.get("sub_url") or ""
    try:
        mpv_bin = find_mpv_binary()
        if not mpv_bin:
            return fail("mpv tidak ditemukan. Taruh mpv.exe di folder 'bin/' atau install mpv ke sistem.")

        loop = asyncio.get_running_loop()
        hit = await get_episode_cache(slug, ep, mode)
        if not hit and mode == "sub":
            hit = await get_episode_cache(slug, ep, "dub")
        elif not hit and mode == "dub":
            hit = await get_episode_cache(slug, ep, "sub")
        if hit:
            got = dict(hit)
        else:
            maps = await loop.run_in_executor(None, lambda: hi.hianime_episodes(slug))
            got = await loop.run_in_executor(None, lambda: hi.hianime_m3u8(maps, ep, mode, slug))
        picked = hi.select_quality(got["variants"], quality)
        m_url = got.get("master", "")
        stream_target = m_url if (m_url and (".m3u8" in m_url or "/hls" in m_url)) else picked["url"]
        cmd = [mpv_bin, f"--referer={got.get('referer','')}", stream_target]
        # Kumpulkan subtitle files. Prioritas:
        #   1) preferred_sub_url (kalau client pilih spesifik), atau default 'sub'
        #   2) SELURUH subtitles[] dari cache/result, agar semua track terpasang
        #      dan user bisa cycle via 'j' di MPV.
        # File VTT didownload ke tempdir (mpv butuh path lokal). File yang gagal
        # didownload di-skip agar tidak menggagalkan playback.
        # Catatan: subs_all mengandung tracks unik saja — kalau 'sub' (default)
        # sudah ada di subtitles[] dengan URL sama, skip supaya tidak duplikat.
        subs_all = []
        seen_urls = set()
        for s in (got.get("subtitles") or []):
            url = (s or {}).get("url")
            if url and url not in seen_urls:
                subs_all.append(s)
                seen_urls.add(url)
        if preferred_sub_url and preferred_sub_url not in seen_urls:
            subs_all.append({"label": "Selected", "url": preferred_sub_url,
                             "lang": "", "default": False})
            seen_urls.add(preferred_sub_url)
        elif got.get("sub") and got["sub"] not in seen_urls:
            # Pakai default 'sub' hanya kalau belum ada di subtitles[].
            subs_all.append({"label": got.get("sub_lang") or "Default",
                             "url": got["sub"], "lang": "", "default": True})
            seen_urls.add(got["sub"])

        # Helper download async; return None kalau gagal (skip track).
        async def _download_sub(url):
            try:
                from api.hianime import _host_from, _BLOCKED_DPI_HOSTS
                h = _host_from(url)
                if h in _BLOCKED_DPI_HOSTS:
                    from api.desync import tls_desync_request
                    loop = asyncio.get_running_loop()
                    raw = await loop.run_in_executor(None, lambda: tls_desync_request(url, headers={"Referer": got.get("referer", "")}))
                    text = raw.decode("utf-8", errors="replace")
                else:
                    async with httpx.AsyncClient(timeout=15) as c:
                        sr = await c.get(url, headers={"User-Agent": HI_UA,
                                                        "Referer": got.get("referer", "")})
                        if sr.status_code != 200 or not sr.text:
                            return None
                        text = sr.text

                if not text:
                    return None
                fp = os.path.join(tempfile.gettempdir(),
                                  f"{slug}-ep{ep}-{abs(hash(url)) % 10**8}.vtt")
                open(fp, "w").write(text)
                return fp
            except Exception:
                return None

        downloaded = []
        for s in subs_all:
            url = (s or {}).get("url")
            if not url:
                continue
            fp = await _download_sub(url)
            if fp:
                downloaded.append(fp)

        # Masukkan --sub-file sebelum URL. mpv izinkan multiple --sub-file.
        # Sisip di posisi 2 (setelah mpv_bin + --referer=) agar tidak geser posisi URL.
        for fp in downloaded:
            cmd.insert(2, f"--sub-file={fp}")

        creationflags = 0
        if sys.platform == "win32":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=creationflags)
        await add_history(slug, body.get("title", slug), ep, mode, poster=body.get("poster", ""), type=body.get("type", ""))
        return ok({"cmd": cmd, "picked": picked, "subs_attached": len(downloaded)})
    except Exception as e:
        return fail(str(e))

@app.post("/api/shutdown")
async def shutdown():
    def _do_exit():
        import time
        time.sleep(0.3)
        os._exit(0)
    import threading
    threading.Thread(target=_do_exit, daemon=True).start()
    return ok({"message": "Server shutting down..."})

@app.get("/api/history")
async def history():
    return ok(await get_history())

@app.post("/api/history")
async def save_hist(body: dict = None):
    body = body or {}
    await add_history(
        body.get("slug", ""),
        body.get("title", ""),
        int(body.get("episode", 1)),
        body.get("mode", "sub"),
        int(body.get("progress", 0)),
        body.get("poster", ""),
        body.get("type", "")
    )
    return ok(True)

@app.delete("/api/history")
async def del_hist():
    await clear_history()
    return ok(True)

def _format_time_sec(sec: int) -> str:
    sec = max(0, int(sec or 0))
    m = sec // 60
    s = sec % 60
    if m >= 60:
        h = m // 60
        m = m % 60
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

@app.get("/api/progress")
async def get_watch_progress(slug: str = Query(""), ep: int = Query(None), episode: int = Query(None)):
    ep_num = ep if ep is not None else episode
    if not slug or ep_num is None:
        return fail("Parameter slug dan ep wajib diisi")
    row = await get_progress(slug, ep_num)
    if row:
        prog = int(row.get("progress", 0))
        dur = int(row.get("duration", 0))
        should_resume = (prog >= 15)
        if dur > 30 and prog >= (dur - 30):
            should_resume = False
        return ok({
            "slug": slug,
            "episode": ep_num,
            "progress": prog,
            "duration": dur,
            "formatted": _format_time_sec(prog),
            "should_resume": should_resume
        })
    return ok({
        "slug": slug,
        "episode": ep_num,
        "progress": 0,
        "duration": 0,
        "formatted": "00:00",
        "should_resume": False
    })

@app.post("/api/progress")
async def save_watch_progress(body: dict = None):
    body = body or {}
    slug = (body.get("slug") or "").strip()
    ep_val = body.get("episode") if body.get("episode") is not None else body.get("ep")
    if not slug or ep_val is None:
        return fail("Slug dan episode wajib diisi")
    progress = int(body.get("progress", 0))
    duration = int(body.get("duration", 0))
    await save_progress(slug, int(ep_val), progress, duration)
    return ok(True)

@app.delete("/api/progress")
async def delete_watch_progress(slug: str = Query(""), ep: int = Query(None), episode: int = Query(None), body: dict = None):
    body = body or {}
    s = slug or body.get("slug", "")
    e = ep if ep is not None else (episode if episode is not None else body.get("episode", body.get("ep")))
    if not s:
        return fail("Slug wajib diisi")
    await clear_progress(s, int(e) if e is not None else None)
    return ok(True)

@app.get("/api/bookmarks")
async def list_bookmarks():
    return ok(await get_bookmarks())

@app.post("/api/bookmarks")
async def save_bookmark(body: dict = None):
    body = body or {}
    slug = (body.get("slug") or body.get("id") or "").strip()
    if not slug:
        return err("Slug wajib diisi", 400)
    _ANIME_FAILOVER_CACHE.pop(slug, None)
    await add_bookmark(
        slug=slug,
        title=body.get("title", ""),
        poster=body.get("poster", ""),
        type=body.get("type", ""),
        sub=str(body.get("sub", "")),
        eps=str(body.get("eps", "")),
        score=float(body.get("score") or 0.0)
    )
    return ok(True)

@app.delete("/api/bookmarks/{slug}")
async def delete_one_bookmark(slug: str):
    slug_clean = (slug or "").strip()
    _ANIME_FAILOVER_CACHE.pop(slug_clean, None)
    await remove_bookmark(slug_clean)
    return ok(True)

@app.delete("/api/bookmarks")
async def del_all_bookmarks():
    _ANIME_FAILOVER_CACHE.clear()
    await clear_bookmarks()
    return ok(True)

@app.get("/api/bookmarks/check")
async def check_bookmark(slug: str = ""):
    return ok({"bookmarked": await is_bookmarked(slug)})


@app.get("/api/settings")
async def get_set():
    # Ambil seluruh setting dalam SATU query (get_settings_bulk) — sebelumnya
    # 13 query berurutan ke tabel yang hanya berisi ~6 baris.
    s = await get_settings_bulk()
    def _v(key, default=""):
        val = s.get(key)
        return default if val is None else val
    return ok({
        "quality": _v("quality", "best"),
        "mode": _v("mode", "sub"),
        "player": _v("player", "browser"),
        "preferred_source": _v("preferred_source", "hianime"),
        # Preferensi bahasa subtitle user. Default "English" karena sebagian besar
        # sumber (Megaplay, ZokoAnime) punya English sebagai track default. Kalau
        # user pernah pilih bahasa lain, disimpan di sini dan dipakai frontend
        # untuk auto-select track di episode berikutnya.
        "sub_lang": _v("sub_lang", "English"),
        # Translate API (opsional). User isi via settings panel. Fallback ke
        # MyMemory kalau kosong. translate_apikey tidak pernah di-log.
        "translate_apikey": _v("translate_apikey", ""),
        "translate_model": _v("translate_model", "gemini-2.0-flash"),
        "translate_apiurl": _v("translate_apiurl", "https://generativelanguage.googleapis.com/v1beta/openai"),
        "safe_mode": _v("safe_mode", "1"),
    })

@app.post("/api/settings")
async def set_set(body: dict = None):
    body = body or {}
    # Otomatis sesuaikan model & apiurl berdasarkan format apikey dari pengguna jika tidak dispesifikasikan eksplisit
    if "translate_apikey" in body:
        val = body["translate_apikey"]
        if isinstance(val, str):
            val = val.strip().strip("\"'").strip()
            body["translate_apikey"] = val
            if val:
                from api.translate import detect_provider_from_key
                _, inferred_model, inferred_url = detect_provider_from_key(val)
                if not body.get("translate_model"):
                    body["translate_model"] = inferred_model
                if not body.get("translate_apiurl"):
                    body["translate_apiurl"] = inferred_url

    for k in ("quality", "mode", "player", "sub_lang", "preferred_source", "safe_mode",
              "translate_apikey", "translate_model", "translate_apiurl"):
        if k in body:
            await set_setting(k, body[k])
    return await get_set()

@app.get("/api/translate/logs")
async def get_translate_logs_api():
    """Mengambil riwayat log aktivitas translasi subtitle terbaru."""
    from api.translate import get_translate_logs
    return {"success": True, "data": {"logs": get_translate_logs()}}

if os.path.isdir(os.path.join(frontend_dir, "js")):
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")
if os.path.isdir(os.path.join(frontend_dir, "css")):
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
if os.path.isdir(os.path.join(frontend_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

@app.get("/")
async def root():
    idx_path = os.path.join(frontend_dir, "index.html")
    if os.path.isfile(idx_path):
        return FileResponse(idx_path)
    return ok({"status": "running", "app": "Tatap Native Android Backend"})

if __name__ == "__main__":
    import uvicorn
    # Otomatis gunakan uvloop (libuv C-extension) dan httptools jika tersedia di Linux / desktop,
    # fallback aman ke asyncio dan h11 jika pustaka C tidak tersedia.
    loop_type = "asyncio"
    http_type = "h11"
    try:
        import uvloop
        loop_type = "uvloop"
    except Exception:
        pass
    try:
        import httptools
        http_type = "httptools"
    except Exception:
        pass
    uvicorn.run(
        app,
        host=APP_HOST,
        port=APP_PORT,
        loop=loop_type,
        http=http_type,
        access_log=False,
        log_level="warning"
    )
