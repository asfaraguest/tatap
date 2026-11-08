import os
import sys
import pytest
import asyncio

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.database import add_history, get_history, clear_history, add_bookmark, remove_bookmark, _connect_db


@pytest.mark.asyncio
async def test_watch_history_preserves_poster_on_progress_update():
    """Memastikan bahwa pembaruan progres riwayat tontonan tidak menghapus poster."""
    await clear_history()

    # 1. Simpan riwayat awal dengan poster dan type
    test_slug = "test-anime-preservation"
    test_poster = "https://img.hianime.to/poster/test123.jpg"
    test_title = "Test Anime Title"
    await add_history(test_slug, test_title, episode=1, mode="sub", progress=0, poster=test_poster, type="TV")

    h = await get_history()
    assert len(h) >= 1
    found = next((x for x in h if x["slug"] == test_slug), None)
    assert found is not None
    assert found["poster"] == test_poster
    assert found["type"] == "TV"
    assert found["episode"] == 1

    # 2. Update progres episode selanjutnya tanpa menyertakan poster (kasus default playback)
    await add_history(test_slug, test_title, episode=2, mode="sub", progress=450, poster="", type="")

    h2 = await get_history()
    found2 = next((x for x in h2 if x["slug"] == test_slug), None)
    assert found2 is not None
    # Poster dan type harus tetap dipertahankan, tidak tertimpa string kosong!
    assert found2["poster"] == test_poster
    assert found2["type"] == "TV"
    assert found2["episode"] == 2
    assert found2["progress"] == 450


@pytest.mark.asyncio
async def test_watch_history_backfills_poster_from_bookmarks():
    """Memastikan bahwa get_history dapat meng-backfill poster yang hilang jika ada di bookmarks."""
    await clear_history()
    test_slug = "test-anime-backfill"
    test_poster = "https://img.hianime.to/poster/bookmark123.jpg"
    test_title = "Bookmarked Anime Title"

    try:
        # Tambah bookmark dengan poster
        await add_bookmark(test_slug, test_title, poster=test_poster, type="MOVIE")

        # Tambah history tanpa poster
        async with _connect_db() as db:
            await db.execute("DELETE FROM watch_history WHERE slug=?", (test_slug,))
            await db.execute("INSERT INTO watch_history(slug,title,episode,mode,progress,poster,type,played_at) VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
                             (test_slug, test_title, 1, "sub", 100, "", ""))
            await db.commit()

        # Panggil get_history yang melakukan auto-backfill
        h = await get_history()
        found = next((x for x in h if x["slug"] == test_slug), None)
        assert found is not None
        assert found["poster"] == test_poster
        assert found["type"] == "MOVIE"
    finally:
        await remove_bookmark(test_slug)
        await clear_history()


def test_chaquopy_backend_parity():
    """Memastikan paritas 100% antara backend/ dan android/app/src/main/python/backend/."""
    files_to_check = [
        ("backend/database/__init__.py", "android/app/src/main/python/backend/database/__init__.py"),
        ("backend/api/hianime.py", "android/app/src/main/python/backend/api/hianime.py"),
        ("backend/main.py", "android/app/src/main/python/backend/main.py"),
    ]
    for src, dst in files_to_check:
        with open(src, "r", encoding="utf-8") as f_src:
            c_src = f_src.read()
        with open(dst, "r", encoding="utf-8") as f_dst:
            c_dst = f_dst.read()
        assert c_src == c_dst, f"Paritas Chaquopy gagal pada file: {src} != {dst}"


def test_frontend_markup_and_css_tokens():
    """Memastikan token kelas CSS dan struktur elemen thumbnail di frontend."""
    with open("frontend/js/app.js", "r", encoding="utf-8") as f:
        app_js = f.read()
    assert "hist-thumb-wrap" in app_js
    assert "hist-thumb" in app_js
    assert "hist-thumb-ph" in app_js
    assert "hist-ep-badge" in app_js
    assert "hist-play-badge" in app_js
    assert "hist-progress-track" in app_js
    assert "hist-progress-fill" in app_js

    with open("frontend/js/term.js", "r", encoding="utf-8") as f:
        term_js = f.read()
    assert "pc-thumb-ph" in term_js

    with open("frontend/css/style.css", "r", encoding="utf-8") as f:
        css = f.read()
    assert ".hist-thumb-wrap" in css
    assert ".hist-thumb" in css
    assert ".hist-ep-badge" in css
    assert ".hist-play-badge" in css
    assert ".hist-progress-track" in css
    assert ".hist-progress-fill" in css
    assert ".pc-thumb-ph" in css
