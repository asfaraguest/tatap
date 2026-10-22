import os
import sys
import pytest
import asyncio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import (
    init_db,
    add_bookmark,
    remove_bookmark,
    get_bookmarks,
    is_bookmarked,
    clear_bookmarks,
    get_episode_cache,
    set_episode_cache,
    clear_episode_cache_for_slug
)

@pytest.mark.asyncio
async def test_bookmark_lifecycle():
    await init_db()
    # Bersihkan dulu data uji
    await remove_bookmark("test-frieren-slug")
    assert await is_bookmarked("test-frieren-slug") is False

    # 1. Tambah bookmark
    await add_bookmark(
        slug="test-frieren-slug",
        title="Sousou no Frieren",
        poster="https://example.com/frieren.jpg",
        type="TV",
        sub="28",
        eps="28",
        score=9.35
    )

    # 2. Cek status
    assert await is_bookmarked("test-frieren-slug") is True
    assert await is_bookmarked("non-existent-slug") is False

    # 3. Ambil daftar dan verifikasi kompatibilitas id = slug
    bookmarks = await get_bookmarks(limit=10)
    found = [b for b in bookmarks if b.get("slug") == "test-frieren-slug"]
    assert len(found) == 1
    item = found[0]
    assert item["id"] == "test-frieren-slug"
    assert item["title"] == "Sousou no Frieren"
    assert item["score"] == 9.35

    # 4. Hapus bookmark spesifik
    await remove_bookmark("test-frieren-slug")
    assert await is_bookmarked("test-frieren-slug") is False
    bookmarks_after = await get_bookmarks(limit=10)
    assert not any(b.get("slug") == "test-frieren-slug" for b in bookmarks_after)


@pytest.mark.asyncio
async def test_bookmark_invalidates_episode_cache():
    await init_db()
    slug = "test-cache-invalidation-slug"

    # Pre-kondisi: buat entri episode cache
    await set_episode_cache(
        slug=slug,
        ep=1,
        mode="sub",
        master="https://cdn.example.com/master.m3u8",
        variants=[{"q": "HD", "url": "https://cdn.example.com/ep1.mp4"}],
        sub="https://cdn.example.com/ep1.vtt",
        sub_lang="English",
        referer="https://example.com",
        server="megacloud",
        subtitles=[{"url": "https://cdn.example.com/ep1.vtt", "lang": "English", "label": "English"}]
    )
    # Verifikasi cache hit
    cached = await get_episode_cache(slug, 1, "sub")
    assert cached is not None
    assert cached["master"] == "https://cdn.example.com/master.m3u8"

    # 1. Menambahkan bookmark harus menginvalidasi episode_cache untuk slug tersebut
    await add_bookmark(slug, "Test Title", poster="", type="TV", sub="12", eps="12", score=8.5)
    assert await get_episode_cache(slug, 1, "sub") is None

    # Simpan kembali cache untuk pengujian penghapusan bookmark
    await set_episode_cache(
        slug=slug,
        ep=1,
        mode="sub",
        master="https://cdn.example.com/master.m3u8",
        variants=[],
        sub="https://cdn.example.com/ep1.vtt",
        sub_lang="English",
        referer="https://example.com",
        server="megacloud"
    )
    assert await get_episode_cache(slug, 1, "sub") is not None

    # 2. Menghapus bookmark (unbookmark) harus menginvalidasi episode_cache
    await remove_bookmark(slug)
    assert await get_episode_cache(slug, 1, "sub") is None

    # 3. Verifikasi helper clear_episode_cache_for_slug secara langsung
    await set_episode_cache(slug=f"hianime:{slug}", ep=2, mode="sub", master="http://m.m3u8", variants=[], sub="", sub_lang="", referer="", server="")
    assert await get_episode_cache(f"hianime:{slug}", 2, "sub") is not None
    cleared = await clear_episode_cache_for_slug(slug)
    assert cleared >= 1
    assert await get_episode_cache(f"hianime:{slug}", 2, "sub") is None
