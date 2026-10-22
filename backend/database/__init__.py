import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import aiosqlite
import time
import json
from contextlib import asynccontextmanager
from config import DATABASE_PATH

DB_PATH = DATABASE_PATH

@asynccontextmanager
async def _connect_db():
    async with aiosqlite.connect(DB_PATH) as db:
        if os.environ.get("TATAP_IS_TV") == "1":
            await db.execute("PRAGMA cache_size = -500;")
            await db.execute("PRAGMA temp_store = FILE;")
            await db.execute("PRAGMA mmap_size = 0;")
        yield db

async def init_db():
    async with _connect_db() as db:
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
    async with _connect_db() as db:
        await db.execute("INSERT OR REPLACE INTO search_cache(query,payload,fetched_at) VALUES(?,?,?)",
                         (query, json.dumps(payload), _now()))
        await db.commit()

async def get_episode_cache(slug: str, ep: int, mode: str, ttl=2*3600):
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM episode_cache WHERE slug=? AND ep=? AND mode=?",
                              (slug, ep, mode)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            d = dict(row)
            if _now() - d["fetched_at"] > ttl:
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

async def delete_episode_cache(slug: str, ep: int = None, mode: str = None):
    """Hapus cache episode tertentu jika stream basi atau mengalami timeout."""
    async with _connect_db() as db:
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
    async with _connect_db() as db:
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
    async with _connect_db() as db:
        cur = await db.execute("DELETE FROM episode_cache WHERE slug = ? OR slug LIKE ? OR slug LIKE ?",
                              (clean, f"{clean}:%", f"%:{clean}"))
        await db.commit()
        return cur.rowcount

get_cached_episode = get_episode_cache
cache_episode = set_episode_cache

async def add_history(slug, title, episode, mode="sub", progress=0, poster="", type=""):
    async with _connect_db() as db:
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
    async with _connect_db() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM watch_history ORDER BY played_at DESC LIMIT ?", (limit,)) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
            needs_commit = False
            for r in rows:
                if "slug" in r and r["slug"]:
                    r["id"] = r["slug"]
                # Backfill poster jika belum ada tapi tersedia di bookmarks
                if not r.get("poster") and r.get("slug"):
                    async with db.execute("SELECT poster, type FROM bookmarks WHERE slug=? AND poster != ''", (r["slug"],)) as c_bm:
                        bm_row = await c_bm.fetchone()
                        if bm_row and bm_row[0]:
                            r["poster"] = bm_row[0]
                            if not r.get("type") and bm_row[1]:
                                r["type"] = bm_row[1]
                            await db.execute("UPDATE watch_history SET poster=?, type=? WHERE slug=?", (r["poster"], r.get("type", ""), r["slug"]))
                            needs_commit = True
            if needs_commit:
                await db.commit()
            return rows

async def clear_history():
    async with _connect_db() as db:
        await db.execute("DELETE FROM watch_history")
        await db.commit()

async def save_progress(slug: str, episode: int, progress: int, duration: int = 0):
    """Simpan posisi menit & detik tontonan per episode, serta sinkronkan ke watch_history."""
    if not slug or episode is None:
        return
    async with _connect_db() as db:
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
    async with _connect_db() as db:
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
    async with _connect_db() as db:
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
    async with _connect_db() as db:
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
    async with _connect_db() as db:
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
    async with _connect_db() as db:
        await db.execute("INSERT OR REPLACE INTO browse_cache(key,payload,fetched_at) VALUES(?,?,?)",
                         (key, json.dumps(payload), _now()))
        await db.commit()

async def get_setting(key, default=""):
    async with _connect_db() as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default

async def set_setting(key, value):
    async with _connect_db() as db:
        await db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
        await db.commit()


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
    async with _connect_db() as db:
        await db.execute("INSERT OR REPLACE INTO slug_map(title,slug,fetched_at) VALUES(?,?,?)",
                         (key, slug, _now()))
        await db.commit()


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
    async with _connect_db() as db:
        await db.execute("DELETE FROM subtitle_cache WHERE key=?", (key,))
        await db.commit()


async def set_subtitle_cache(key, payload):
    """Cache translated VTT TEXT."""
    async with _connect_db() as db:
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
    async with _connect_db() as db:
        await db.execute(
            "INSERT INTO mychar_counts(day,total) VALUES(?,?) "
            "ON CONFLICT(day) DO UPDATE SET total=total+?",
            (day, n, n),
        )
        await db.commit()
        async with db.execute("SELECT total FROM mychar_counts WHERE day=?", (day,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else n
