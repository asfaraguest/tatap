import pytest
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from database import init_db, set_episode_cache, get_episode_cache, delete_episode_cache
from api import hianime as hi
import main

@pytest.mark.asyncio
async def test_delete_episode_cache():
    await init_db()
    slug = "test-timeout-anime"
    ep = 1
    mode = "sub"
    master = "https://example.com/master.m3u8"
    variants = [{"q": "HD", "url": master}]
    
    await set_episode_cache(slug, ep, mode, master, variants, None, None, "https://example.com/", "TestServer")
    hit = await get_episode_cache(slug, ep, mode)
    assert hit is not None
    assert hit["master"] == master
    
    # Delete and verify
    await delete_episode_cache(slug, ep, mode)
    hit_after = await get_episode_cache(slug, ep, mode)
    assert hit_after is None

@pytest.mark.asyncio
async def test_resolve_force_refresh(monkeypatch):
    await init_db()
    slug = "test-timeout-force"
    ep = 1
    mode = "sub"
    master = "https://example.com/stale_master.m3u8"
    variants = [{"q": "HD", "url": master}]
    
    # Pre-populate stale cache with valid subtitles
    await set_episode_cache(slug, ep, mode, master, variants, "https://example.com/sub.vtt", "English", "https://example.com/", "StaleServer",
                            subtitles=[{"url": "https://example.com/sub.vtt", "lang": "en"}])
    
    # When force=False, returns cached
    res_cached = await main.resolve(slug=slug, ep=ep, mode=mode, q="best", source="hianime", force=False)
    assert res_cached["success"] is True
    assert res_cached["data"]["cached"] is True
    assert res_cached["data"]["master"] == master
    
    # Mock fresh fetch
    new_master = "https://example.com/fresh_master.m3u8"
    def fake_hianime_episodes(s):
        return [{"ep": 1, "ep_id": "9999"}]
    def fake_hianime_m3u8(maps, ep_no, m, s):
        return {
            "master": new_master,
            "variants": [{"q": "1080p", "url": new_master}],
            "sub": "https://fresh.example.com/sub.vtt", "sub_lang": "en", "referer": "https://fresh.example.com/",
            "server": "FreshZoko", "subtitles": [{"url": "https://fresh.example.com/sub.vtt", "lang": "en"}], "intro": {"start": 0, "end": 0}, "outro": {"start": 0, "end": 0}
        }
    monkeypatch.setattr(hi, "hianime_episodes", fake_hianime_episodes)
    monkeypatch.setattr(hi, "hianime_m3u8", fake_hianime_m3u8)
    
    # When force=True, stale cache is purged and fresh stream is returned
    res_fresh = await main.resolve(slug=slug, ep=ep, mode=mode, q="best", source="hianime", force=True)
    assert res_fresh["success"] is True
    assert res_fresh["data"]["cached"] is False
    assert res_fresh["data"]["master"] == new_master
    assert res_fresh["data"]["server"] == "FreshZoko"

def test_validate_master_playlist_with_body_content():
    sample_m3u8 = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=1280x720\n720p.m3u8\n"
    variants = hi._validate_master_playlist("https://cdn.example.com/master.m3u8", "https://example.com/", [], body_content=sample_m3u8)
    assert len(variants) == 1
    assert variants[0]["q"] == "720p"
    assert variants[0]["url"] == "https://cdn.example.com/720p.m3u8"

def test_dead_host_marking():
    test_host = "test-dead-cdn-987.top"
    assert not hi._is_dead_host(test_host)
    hi._mark_dead(test_host, ttl=300)
    assert hi._is_dead_host(test_host)
