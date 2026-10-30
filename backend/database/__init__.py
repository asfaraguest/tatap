import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aiosqlite
import time
import json
import asyncio
from contextlib import asynccontextmanager
from config import DATABASE_PATH

DB_PATH = DATABASE_PATH

# ---------------------------------------------------------------------------
# Connection pool + PRAGMA tuning.
#
# SEBELUMNYA: setiap fungsi publik membuka koneksi aiosqlite BARU. Itu berarti
# satu sqlite3_open + satu thread aiosqlite + N round-trip queue + sqlite3_close
# per operasi — bahkan untuk SELECT 1 baris. Pada hot path (get_setting dipanggil
# 24x di main.py, get_episode_cache 1-3x per resolve) ini murni pemborosan.
#
# SEKARANG: satu koneksi bersama yang di-reuse + asyncio.Lock untuk serialize
# write. Read tetap paralel karena SQLite WAL mengizinkan banyak reader.
#
# PRAGMA yang diterapkan:
#   journal_mode=WAL   -> persistent di header DB, reader tidak blocking writer
#   synchronous=NORMAL -> WAL+NORMAL crash-safe terhadap crash aplikasi,
#                          tidak fsync penuh di tiap commit (default FULL = lambat)
#   busy_timeout=5000  -> writer menunggu lock, bukan langsung error "database is locked"
#   cache_size         -> cache page lebih besar (TV dikecilkan untuk hemat RAM)
#   mmap_size          -> baca page via memory-map (lebih cepat di Linux)
# ---------------------------------------------------------------------------
_pool_lock = asyncio.Lock()
_pool = []            # daftar koneksi aiosqlite yang tersedia
_pool_max = 4
_write_lock = asyncio.Lock()


async def _apply_pragmas(db):
    """Terapkan PRAGMA optimal untuk koneksi database Tatap."""
    # WAL + NORMAL: standar produksi untuk WAL. NORMAL tetap aman terhadap crash
    # aplikasi (hanya risiko power-loss/OS-crash yang bisa kehilangan commit terakhir).
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA synchronous=NORMAL;")
    await db.execute("PRAGMA busy_timeout=5000;")
    if os.environ.get("TATAP_IS_TV") == "1":
        # TV: RAM terbatas — cache kecil, temp store ke file, tanpa mmap.
        await db.execute("PRAGMA cache_size = -500;")
        await db.execute("PRAGMA temp_store = FILE;")
        await db.execute("PRAGMA mmap_size = 0;")
    else:
        await db.execute("PRAGMA cache_size = -8000;")
        await db.execute("PRAGMA temp_store = MEMORY;")
        await db.execute("PRAGMA mmap_size = 67108864;")


async def _open_pooled_db():
    """Buat satu koneksi baru untuk pool + terapkan PRAGMA."""
    db = await aiosqlite.connect(DB_PATH)
    await _apply_pragmas(db)
    return db


@asynccontextmanager
async def _connect_db():
    """Ambil koneksi dari pool (atau buat baru bila pool kosong).

    Koneksi dikembalikan ke pool saat keluar dari context manager sehingga
    koneksi dipakai ulang antar request — tidak ada open/close per operasi.
    """
    db = None
    async with _pool_lock:
        if _pool:
            db = _pool.pop()
    if db is None:
        db = await _open_pooled_db()
    try:
        yield db
    finally:
        try:
            async with _pool_lock:
                if len(_pool) < _pool_max:
                    _pool.append(db)
                    db = None
        finally:
            if db is not None:
                try:
                    await db.close()
                except Exception:
                    pass


@asynccontextmanager
async def _write_db():
    """Konteks untuk operasi tulis: serialize lewat _write_lock.

    SQLite hanya mengizinkan satu writer pada satu waktu. Dengan WAL, reader
    tetap bisa berjalan paralel, tapi writer harus di-serialize agar tidak
    kena SQLITE_BUSY. Lock ini memastikan hanya satu writer aktif.
    """
    async with _write_lock:
        async with _connect_db() as db:
            yield db


async def close_db_pool():
    """Tutup seluruh koneksi pada pool (dipanggil saat shutdown app)."""
    global _pool
    async with _pool_lock:
        conns = list(_pool)
        _pool = []
    for c in conns:
        try:
            await c.close()
        except Exception:
            pass


async def init_db():
    async with _write_db() as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""CREATE TABLE IF NOT EXISTS search_cache(
            query TEXT PRIMARY KEY, payload TEXT, fetched_at INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS episode_cache(
            slug TEXT, ep INTEGER, mode TEXT, master TEXT, variants TEXT,
            sub TEXT, sub_lang TEXT, referer TEXT, server TEXT, fetched_at INTEGER,
            PRIMARY KEY(slug, ep, mode))""")
        # Migrasi ringan: tambah kolom 'subtitles' (TEXT JSON array) untuk multi-track.
        # Gunakan pragma_table_info agar idempotent — kalau kolom sudah ada, skip.
        # Tidak ANDa ALTER TABLE di try/except supaya DB lama ter-upgrade otomatis.
        try:
            await db.execute("ALTER TABLE episode_cache ADD COLUMN subtitles TEXT DEFAULT '[]'")
        except Exception:
            # Duplicate column name → kolom sudah ada, aman di-skip.
            pass
        try:
            await db.execute("ALTER TABLE episode_cache ADD COLUMN intro TEXT DEFAULT '{}'")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE episode_cache ADD COLUMN outro TEXT DEFAULT '{}'")
        except Exception:
            pass
        try:
            # Sanitasi entri cache basi/cacat di mode sub tanpa softsub yang valid
            await db.execute("""DELETE FROM episode_cache 
                WHERE mode = 'sub' 
                  AND (sub IS NULL OR sub = '' OR (sub NOT LIKE 'http%' AND sub NOT LIKE '/%')) 
                  AND (subtitles IS NULL OR subtitles = '[]' OR subtitles = '')""")
        except Exception:
            pass
        await db.execute("""CREATE TABLE IF NOT EXISTS watch_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT, title TEXT,
            episode INTEGER, mode TEXT DEFAULT 'sub', progress INTEGER DEFAULT 0,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        try:
            await db.execute("ALTER TABLE watch_history ADD COLUMN poster TEXT DEFAULT ''")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE watch_history ADD COLUMN type TEXT DEFAULT ''")
        except Exception:
            pass
        await db.execute("""CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY, value TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS browse_cache(
            key TEXT PRIMARY KEY, payload TEXT, fetched_at INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS slug_map(
            title TEXT PRIMARY KEY, slug TEXT, fetched_at INTEGER)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS mal_map(
            identifier TEXT PRIMARY KEY, mal_id INTEGER, fetched_at INTEGER)""")
        # Cache translated VTT — key: hash(src_url+referer+lang). TTL 30 hari.
        await db.execute("""CREATE TABLE IF NOT EXISTS subtitle_cache(
            key TEXT PRIMARY KEY, payload TEXT, fetched_at INTEGER)""")
        # Quota counter MyMemory per-day (Tier 2). Soft limit 4500/5000 char/day per-IP.
        await db.execute("""CREATE TABLE IF NOT EXISTS mychar_counts(
            day TEXT PRIMARY KEY, total INTEGER DEFAULT 0)""")
        # Tabel bookmarks / favorit anime tersimpan mandiri & terisolasi
        await db.execute("""CREATE TABLE IF NOT EXISTS bookmarks(
            slug TEXT PRIMARY KEY,
            title TEXT,
            poster TEXT DEFAULT '',
            type TEXT DEFAULT '',
            sub TEXT DEFAULT '',
            eps TEXT DEFAULT '',
            score REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        # Tabel watch_progress: mencatat menit & detik tontonan per episode anime
        await db.execute("""CREATE TABLE IF NOT EXISTS watch_progress(
            slug TEXT,
            episode INTEGER,
            progress INTEGER DEFAULT 0,
            duration INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (slug, episode)
        )""")
        # Sanitasi satu kali relasi panzer yang salah ter-cache pada slug_map / cache
        try:
            await db.execute("DELETE FROM slug_map WHERE lower(title) LIKE '%panzer%' AND slug = 'girls-und-panzer-der-film-1161' AND lower(title) NOT LIKE '%film%'")
            await db.execute("DELETE FROM slug_map WHERE lower(title) LIKE '%alice war%'")
            await db.execute("DELETE FROM slug_map WHERE lower(title) LIKE '%finale%' OR lower(title) LIKE '%saishuushou%'")
            await db.execute("DELETE FROM search_cache WHERE lower(query) LIKE '%panzer%'")
            await db.execute("DELETE FROM browse_cache WHERE key LIKE '%panzer%'")
            await db.execute("DELETE FROM browse_cache WHERE key LIKE '%relations%'")
        except Exception:
            pass

        # ------------------------------------------------------------------
        # Index yang sebelumnya TIDAK ADA sama sekali.
        #
        # Tanpa index, query berikut melakukan FULL TABLE SCAN:
        #   - watch_history WHERE slug=?           (6 titik query: add_history,
        #     delete_history, backfill poster, save_progress, clear_progress)
        #   - watch_history ORDER BY played_at DESC LIMIT ?  (sort penuh tiap load)
        #   - bookmarks ORDER BY created_at DESC LIMIT ?    (sort penuh tiap load)
        #   - DELETE FROM episode_cache WHERE fetched_at < ? (sweeper TTL)
        #
        # SQLite membuat index otomatis untuk PRIMARY KEY, tapi tidak ada satu
        # pun CREATE INDEX di skema lama — sudah diverifikasi via sqlite_master.
        # ------------------------------------------------------------------
        await db.execute("CREATE INDEX IF NOT EXISTS idx_wh_slug ON watch_history(slug)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_wh_played_at ON watch_history(played_at DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bm_created_at ON bookmarks(created_at DESC)")
        # Index fetched_at untuk TTL sweeper pada seluruh tabel cache.
        await db.execute("CREATE INDEX IF NOT EXISTS idx_ec_fetched_at ON episode_cache(fetched_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sc_fetched_at ON search_cache(fetched_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_bc_fetched_at ON browse_cache(fetched_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sbc_fetched_at ON subtitle_cache(fetched_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sm_fetched_at ON slug_map(fetched_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_mm_fetched_at ON mal_map(fetched_at)")

        # Optimasi planner dengan statistik aktual.
        try:
            await db.execute("ANALYZE")
        except Exception:
            pass

        await db.commit()

def _now():
    return int(time.time())

async def get_search_cache(query: str, ttl=86400):
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT payload, fetched_at FROM search_cache WHERE query=?", (query,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            if _now() - row["fetched_at"] > ttl:
                return None
            try:
                return json.loads(row["payload"])
            except Exception:
                return None

async def set_search_cache(query: str, payload):
    async with _write_db() as db:
        await db.execute("INSERT OR REPLACE INTO search_cache(query,payload,fetched_at) VALUES(?,?,?)",
                         (query, json.dumps(payload), _now()))
        await db.commit()


# TTL sweeper: hapus baris cache yang sudah kedaluwarsa.
#
# SEBELUMNYA semua TTL di modul ini bersifat "ignore on read" — tidak ada
# satu pun baris expired yang pernah dihapus. Akibatnya DB tumbuh tanpa
# batas (subtitle_cache menyimpan payload VTT utuh, browse_cache/search_cache
# menyimpan JSON, slug_map/mal_map bertambah terus).
#
# Sweeper ini menghapus baris yang sudah lewat TTL. Index fetched_at pada
# seluruh tabel cache membuat DELETE ini O(matched rows), bukan full scan.
async def purge_expired_caches() -> dict:
    """Hapus entri cache yang sudah kedaluwarsa. Return jumlah baris per tabel."""
    now = _now()
    specs = [
        ("episode_cache", 2 * 3600),
        ("search_cache", 24 * 3600),
        ("browse_cache", 6 * 3600),
        ("subtitle_cache", 7 * 24 * 3600),
        ("slug_map", 7 * 24 * 3600),
        ("mal_map", 30 * 24 * 3600),
    ]
    removed = {}
    async with _write_db() as db:
        for table, ttl in specs:
            try:
                cutoff = now - ttl
                cur = await db.execute(f"DELETE FROM {table} WHERE fetched_at < ?", (cutoff,))
                removed[table] = cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0
            except Exception:
                removed[table] = 0
        await db.commit()
    return removed

def _parse_episode_row(row, ttl):
    """Parse satu baris episode_cache menjadi dict siap pakai.

    Dipisah agar bisa dipakai ulang oleh get_episode_cache() (mode tunggal)
    dan get_episode_cache_modes() (multi-mode dalam satu query).
    """
    if not row:
        return None
    d = dict(row)
    if _now() - (d.get("fetched_at") or 0) > ttl:
        return None
    try:
        d["variants"] = json.loads(d["variants"] or "[]")
    except Exception:
        d["variants"] = []
    # Multi-subtitle: parse kolom 'subtitles' (TEXT JSON array).
    # Fallback: kalau DB lama belum punya kolom (atau nil), dan 'sub' ada,
    # buat list 1-element dari 'sub' + 'sub_lang' agar client tetap punya
    # track untuk dropdown (kompatibel mundur dengan cache lama).
    try:
        d["subtitles"] = json.loads(d.get("subtitles") or "[]")
        if not isinstance(d["subtitles"], list):
            d["subtitles"] = []
    except Exception:
        d["subtitles"] = []
    if not d["subtitles"] and d.get("sub"):
        d["subtitles"] = [{
            "label": d.get("sub_lang") or "English",
            "lang": "",
            "url": d["sub"],
            "default": True,
        }]
    try:
        d["intro"] = json.loads(d.get("intro") or '{"start": 0, "end": 0}')
        if not isinstance(d["intro"], dict):
            d["intro"] = {"start": 0, "end": 0}
    except Exception:
        d["intro"] = {"start": 0, "end": 0}
    try:
        d["outro"] = json.loads(d.get("outro") or '{"start": 0, "end": 0}')
        if not isinstance(d["outro"], dict):
            d["outro"] = {"start": 0, "end": 0}
    except Exception:
        d["outro"] = {"start": 0, "end": 0}
    return d


async def get_episode_cache(slug: str, ep: int, mode: str, ttl=2*3600):
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM episode_cache WHERE slug=? AND ep=? AND mode=?",
                              (slug, ep, mode)) as cur:
            row = await cur.fetchone()
            return _parse_episode_row(row, ttl)


async def get_episode_cache_modes(slug: str, ep: int, modes, ttl=2*3600):
    """Ambil cache episode untuk SEKALIGUS beberapa mode dalam SATU query.

    Menghemat 1-2 round-trip SQLite per resolve, karena pemanggil sering
    butuh fallback dari mode 'sub' ke 'dub' (atau sebaliknya).
    Return: dict {mode: parsed_dict}
    """
    if not modes:
        return {}
    mode_list = list(modes)
    placeholders = ",".join("?" * len(mode_list))
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT * FROM episode_cache WHERE slug=? AND ep=? AND mode IN ({placeholders})",
            [slug, ep] + mode_list,
        ) as cur:
            rows = await cur.fetchall()
    out = {}
    for r in rows:
        parsed = _parse_episode_row(r, ttl)
        if parsed:
            out[parsed.get("mode") or r["mode"]] = parsed
    return out

async def delete_episode_cache(slug: str, ep: int = None, mode: str = None):
    """Hapus cache episode tertentu jika stream basi atau mengalami timeout."""
    async with _write_db() as db:
        if ep is not None and mode is not None:
            await db.execute("DELETE FROM episode_cache WHERE slug=? AND ep=? AND mode=?", (slug, ep, mode))
        elif ep is not None:
            await db.execute("DELETE FROM episode_cache WHERE slug=? AND ep=?", (slug, ep))
        else:
            await db.execute("DELETE FROM episode_cache WHERE slug=?", (slug,))
        await db.commit()

async def set_episode_cache(slug, ep, mode, master, variants, sub, sub_lang, referer, server,
                          subtitles=None, intro=None, outro=None):
    """Simpan cache episode. subtitles=list, intro={start,end}, outro={start,end}."""
    subs_json = json.dumps(subtitles or [])
    intro_json = json.dumps(intro or {"start": 0, "end": 0})
    outro_json = json.dumps(outro or {"start": 0, "end": 0})
    async with _write_db() as db:
        await db.execute("""INSERT OR REPLACE INTO episode_cache
            (slug,ep,mode,master,variants,sub,sub_lang,referer,server,subtitles,intro,outro,fetched_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (slug, ep, mode, master, json.dumps(variants), sub or "", sub_lang or "",
             referer or "", server or "", subs_json, intro_json, outro_json, _now()))
        await db.commit()

async def clear_episode_cache_for_slug(slug: str) -> int:
    """Hapus seluruh entri di episode_cache yang berkaitan dengan slug tersebut."""
    if not slug:
        return 0
    clean = slug.strip()
    async with _write_db() as db:
        cur = await db.execute("DELETE FROM episode_cache WHERE slug = ? OR slug LIKE ? OR slug LIKE ?",
                              (clean, f"{clean}:%", f"%:{clean}"))
        await db.commit()
        return cur.rowcount

get_cached_episode = get_episode_cache
cache_episode = set_episode_cache

async def add_history(slug, title, episode, mode="sub", progress=0, poster="", type=""):
    async with _write_db() as db:
        if not poster and slug:
            # Preservasi poster dari riwayat sebelumnya agar tidak terhapus saat pembaruan progres
            async with db.execute("SELECT poster, type FROM watch_history WHERE slug=? AND poster != ''", (slug,)) as cur:
                row = await cur.fetchone()
                if row:
                    if not poster and row[0]:
                        poster = row[0]
                    if not type and row[1]:
                        type = row[1]
        if not poster and slug:
            # Cari dari bookmarks jika ada
            async with db.execute("SELECT poster, type FROM bookmarks WHERE slug=? AND poster != ''", (slug,)) as cur:
                row = await cur.fetchone()
                if row:
                    if not poster and row[0]:
                        poster = row[0]
                    if not type and row[1]:
                        type = row[1]
        if slug:
            await db.execute("DELETE FROM watch_history WHERE slug=?", (slug,))
        await db.execute("INSERT INTO watch_history(slug,title,episode,mode,progress,poster,type,played_at) VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                         (slug, title, episode, mode, progress, poster or "", type or ""))
        await db.commit()

async def get_history(limit=50):
    async with _write_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM watch_history ORDER BY played_at DESC LIMIT ?", (limit,)) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
            needs_commit = False
            if rows:
                # Backfill poster dari bookmarks dalam SATU query (bukan N+1)
                slugs = [r["slug"] for r in rows if r.get("slug") and not r.get("poster")]
                bm_map = {}
                if slugs:
                    placeholders = ",".join("?" * len(slugs))
                    async with db.execute(
                        f"SELECT slug, poster, type FROM bookmarks WHERE slug IN ({placeholders}) AND poster != ''",
                        slugs,
                    ) as c_bm:
                        for br in await c_bm.fetchall():
                            bm_map[br["slug"]] = (br["poster"], br["type"])
                for r in rows:
                    if "slug" in r and r["slug"]:
                        r["id"] = r["slug"]
                    # Backfill poster jika belum ada tapi tersedia di bookmarks
                    if not r.get("poster") and r.get("slug") and r["slug"] in bm_map:
                        poster, btype = bm_map[r["slug"]]
                        r["poster"] = poster
                        if not r.get("type") and btype:
                            r["type"] = btype
                        await db.execute("UPDATE watch_history SET poster=?, type=? WHERE slug=?", (poster, r.get("type", ""), r["slug"]))
                        needs_commit = True
            if needs_commit:
                await db.commit()
            return rows

async def clear_history():
    async with _write_db() as db:
        await db.execute("DELETE FROM watch_history")
        await db.commit()

async def save_progress(slug: str, episode: int, progress: int, duration: int = 0):
    """Simpan posisi menit & detik tontonan per episode, serta sinkronkan ke watch_history."""
    if not slug or episode is None:
        return
    async with _write_db() as db:
        await db.execute("""INSERT OR REPLACE INTO watch_progress(slug, episode, progress, duration, updated_at)
            VALUES(?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (slug, int(episode), int(progress), int(duration)))
        # Update progress di watch_history jika anime dan episode cocok
        await db.execute("UPDATE watch_history SET progress=? WHERE slug=? AND episode=?",
                         (int(progress), slug, int(episode)))
        await db.commit()

async def get_progress(slug: str, episode: int):
    """Ambil posisi menit & detik terakhir yang tersimpan untuk episode tertentu."""
    if not slug or episode is None:
        return None
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT progress, duration, updated_at FROM watch_progress WHERE slug=? AND episode=?",
                              (slug, int(episode))) as cur:
            row = await cur.fetchone()
            if row:
                return dict(row)
            return None

async def clear_progress(slug: str, episode: int = None):
    """Hapus progres episode tertentu atau seluruh progres anime."""
    if not slug:
        return
    async with _write_db() as db:
        if episode is not None:
            await db.execute("DELETE FROM watch_progress WHERE slug=? AND episode=?", (slug, int(episode)))
            await db.execute("UPDATE watch_history SET progress=0 WHERE slug=? AND episode=?", (slug, int(episode)))
        else:
            await db.execute("DELETE FROM watch_progress WHERE slug=?", (slug,))
            await db.execute("UPDATE watch_history SET progress=0 WHERE slug=?", (slug,))
        await db.commit()

async def add_bookmark(slug: str, title: str, poster: str = "", type: str = "", sub: str = "", eps: str = "", score: float = 0.0):
    """Tambah atau update bookmark favorit anime.
    Otomatis membersihkan episode_cache yang berpotensi cacat untuk slug tersebut.
    """
    if not slug:
        return
    clean = slug.strip()
    async with _write_db() as db:
        await db.execute("""INSERT OR REPLACE INTO bookmarks(slug, title, poster, type, sub, eps, score, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (clean, title, poster or "", type or "", sub or "", eps or "", float(score or 0.0)))
        await db.execute("DELETE FROM episode_cache WHERE slug = ? OR slug LIKE ? OR slug LIKE ?",
                         (clean, f"{clean}:%", f"%:{clean}"))
        await db.commit()

async def remove_bookmark(slug: str):
    """Hapus bookmark berdasarkan slug dan bersihkan episode_cache terkait."""
    if not slug:
        return
    clean = slug.strip()
    async with _write_db() as db:
        await db.execute("DELETE FROM bookmarks WHERE slug=?", (clean,))
        await db.execute("DELETE FROM episode_cache WHERE slug = ? OR slug LIKE ? OR slug LIKE ?",
                         (clean, f"{clean}:%", f"%:{clean}"))
        await db.commit()

async def get_bookmarks(limit: int = 200):
    """Ambil daftar bookmark tersimpan terurut dari yang terbaru.
    Setiap row dilengkapi id=slug agar langsung kompatibel dengan grid adapter kartu anime.
    """
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM bookmarks ORDER BY created_at DESC LIMIT ?", (limit,)) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
            for r in rows:
                if "slug" in r and r["slug"]:
                    r["id"] = r["slug"]
            return rows

async def is_bookmarked(slug: str) -> bool:
    """Cek apakah anime dengan slug tertentu ada di bookmark."""
    if not slug:
        return False
    async with _connect_db() as db:
        async with db.execute("SELECT 1 FROM bookmarks WHERE slug=? LIMIT 1", (slug,)) as cur:
            row = await cur.fetchone()
            return bool(row)

async def clear_bookmarks():
    """Hapus seluruh bookmark favorit."""
    async with _write_db() as db:
        await db.execute("DELETE FROM bookmarks")
        await db.commit()


async def get_browse_cache(key: str, ttl=6*3600):
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT payload, fetched_at FROM browse_cache WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            if _now() - row["fetched_at"] > ttl:
                return None
            try:
                return json.loads(row["payload"])
            except Exception:
                return None

async def set_browse_cache(key: str, payload):
    async with _write_db() as db:
        await db.execute("INSERT OR REPLACE INTO browse_cache(key,payload,fetched_at) VALUES(?,?,?)",
                         (key, json.dumps(payload), _now()))
        await db.commit()

# ---------------------------------------------------------------------------
# In-process cache untuk tabel `settings`.
#
# Tabel settings hanya berisi ~6 baris (preferensi user) tapi dibaca 24x di
# backend/main.py dan 13x berurutan di endpoint settings. Setiap pembacaan
# berarti satu round-trip SQLite (walau kini lewat pool, tetap mahal).
# Karena settings jarang berubah (hanya saat user mengubah preferensi),
# cache write-through ini menghilangkan hampir semua query read.
# ---------------------------------------------------------------------------
_settings_cache = {}       # key -> value (populated lazily per key)
_settings_cache_loaded = False


async def _load_settings_cache(db):
    """Muat seluruh tabel settings ke cache in-process (sekali saja)."""
    global _settings_cache_loaded
    try:
        async with db.execute("SELECT key, value FROM settings") as cur:
            rows = await cur.fetchall()
        cache = {r[0]: r[1] for r in rows}
    except Exception:
        cache = {}
    _settings_cache.clear()
    _settings_cache.update(cache)
    _settings_cache_loaded = True
    return cache


async def get_setting(key, default=""):
    global _settings_cache_loaded
    # Fast path: sudah ada di cache in-process (tanpa lock, dict atomic di CPython).
    if _settings_cache_loaded and key in _settings_cache:
        val = _settings_cache.get(key)
        return val if val is not None else default
    async with _connect_db() as db:
        if not _settings_cache_loaded:
            await _load_settings_cache(db)
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            val = row[0] if row else None
            if val is not None:
                _settings_cache[key] = val
            return val if val is not None else default


async def get_settings_bulk() -> dict:
    """Ambil seluruh setting dalam SATU query (replacing 13 query terpisah)."""
    global _settings_cache_loaded
    if _settings_cache_loaded and _settings_cache:
        return dict(_settings_cache)
    async with _connect_db() as db:
        cache = await _load_settings_cache(db)
        return dict(cache)


async def set_setting(key, value):
    async with _write_db() as db:
        await db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
        await db.commit()
    # Write-through: perbarui cache in-process agar pembacaan berikutnya instan.
    _settings_cache[key] = str(value)


def _slug_norm(title):
    import re as _re
    s = (title or "").lower()
    s = _re.sub(r"[^\w\s]", " ", s)
    s = _re.sub(r"\s+", " ", s).strip()
    return s


async def get_slug_map(title, ttl=7*24*3600):
    key = _slug_norm(title)
    if not key:
        return None
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT slug, fetched_at FROM slug_map WHERE title=?", (key,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            if _now() - row["fetched_at"] > ttl:
                return None
            return row["slug"]


async def set_slug_map(title, slug):
    key = _slug_norm(title)
    if not key or not slug:
        return
    async with _write_db() as db:
        await db.execute("INSERT OR REPLACE INTO slug_map(title,slug,fetched_at) VALUES(?,?,?)",
                         (key, slug, _now()))
        await db.commit()


async def get_mal_map(identifier: str, ttl=30 * 24 * 3600) -> int:
    """Ambil mal_id tersimpan dari tabel mal_map SQLite (TTL 30 hari)."""
    if not identifier:
        return 0
    key = str(identifier).strip().lower()
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT mal_id, fetched_at FROM mal_map WHERE identifier=?", (key,)) as cur:
            row = await cur.fetchone()
            if not row:
                return 0
            if _now() - row["fetched_at"] > ttl:
                return 0
            return int(row["mal_id"])


async def set_mal_map(identifier: str, mal_id):
    """Simpan pemetaan identifier (slug/judul) ke mal_id di database SQLite."""
    if not identifier or not mal_id:
        return
    try:
        m_id = int(str(mal_id).strip())
        if m_id <= 0:
            return
        key = str(identifier).strip().lower()
        async with _write_db() as db:
            await db.execute("INSERT OR REPLACE INTO mal_map(identifier, mal_id, fetched_at) VALUES(?,?,?)",
                             (key, m_id, _now()))
            await db.commit()
    except Exception:
        pass


async def get_subtitle_cache(key, ttl=30 * 24 * 3600):
    """Return cached translated VTT TEXT atau None. TTL 30 hari."""
    async with _connect_db() as db:
        async with db.execute("SELECT payload, fetched_at FROM subtitle_cache WHERE key=?",
                              (key,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            if _now() - row[1] > ttl:
                return None
            return row[0]


async def delete_subtitle_cache(key):
    """Hapus entri subtitle cache spesifik."""
    async with _write_db() as db:
        await db.execute("DELETE FROM subtitle_cache WHERE key=?", (key,))
        await db.commit()


async def set_subtitle_cache(key, payload):
    """Cache translated VTT TEXT."""
    async with _write_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO subtitle_cache(key,payload,fetched_at) VALUES(?,?,?)",
            (key, payload, _now()),
        )
        await db.commit()


async def get_today_char_count(day):
    """Return MyMemory char count for today (UTC day string). 0 jika row missing."""
    async with _connect_db() as db:
        async with db.execute("SELECT total FROM mychar_counts WHERE day=?", (day,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def add_today_char_count(day, n):
    """Atomically add n to today's count. Return new total."""
    async with _write_db() as db:
        await db.execute(
            "INSERT INTO mychar_counts(day,total) VALUES(?,?) "
            "ON CONFLICT(day) DO UPDATE SET total=total+?",
            (day, n, n),
        )
        await db.commit()
        async with db.execute("SELECT total FROM mychar_counts WHERE day=?", (day,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else n
