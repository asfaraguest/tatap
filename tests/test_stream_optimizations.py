"""Unit test untuk verifikasi optimasi resolving dan buffering stream video."""
import pytest
import os
import sys
import asyncio
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

import main
from database import init_db, set_episode_cache, get_episode_cache
from api import aniskip
from api import hianime as hi


@pytest.mark.asyncio
async def test_master_cache_seeding():
    """Master m3u8 body harus tersimpan dan dapat diambil kembali tanpa re-fetch."""
    test_url = "https://example.com/hls/master.m3u8"
    test_body = "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=2000000,RESOLUTION=1920x1080\n1080.m3u8"
    
    main._master_cache_set(test_url, test_body)
    cached = main._master_cache_get(test_url)
    assert cached == test_body


@pytest.mark.asyncio
async def test_segment_ring_cache():
    """Segmen video (.ts) harus tersimpan di ring buffer RAM dan ter-evict jika melebihi batas."""
    seg_url = "https://example.com/hls/ep1_seg1.ts"
    seg_bytes = b"G@\x11\x10" + b"\x00" * 1024
    
    main._segment_cache_set(seg_url, "video/mp2t", seg_bytes)
    res = main._segment_cache_get(seg_url)
    assert res is not None
    media_type, data = res
    assert media_type == "video/mp2t"
    assert data == seg_bytes


@pytest.mark.asyncio
async def test_skip_times_endpoint():
    """Endpoint /api/episode/skip_times harus mengembalikan intro/outro ter-cache."""
    await init_db()
    aniskip.store_skip_times(mal_id="99887", title="Test Anime Skip", ep=1,
                            intro={"start": 12.0, "end": 102.0},
                            outro={"start": 1300.0, "end": 1390.0})
    
    res = await main.episode_skip_times(mal_id="99887", title="Test Anime Skip", ep=1)
    assert res["success"] is True
    assert res["data"]["intro"]["end"] == 102.0
    assert res["data"]["outro"]["start"] == 1300.0


@pytest.mark.asyncio
async def test_non_blocking_aniskip_on_resolve(monkeypatch):
    """Resolve stream harus segera selesai tanpa menunggu AniSkip jika lambat."""
    await init_db()
    slug = "fast-resolve-anime"
    ep = 1
    
    # Mock hi resolver
    mock_episodes = lambda s: [{"ep": 1, "ep_id": "888"}]
    mock_m3u8 = lambda maps, e, m, s: {
        "master": "https://example.com/fast.m3u8",
        "master_body": "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000\n720.m3u8",
        "variants": [{"q": "720p", "url": "https://example.com/fast.m3u8"}],
        "sub": "https://example.com/sub.vtt",
        "sub_lang": "English",
        "referer": "https://megaplay.buzz/",
        "server": "MegaCloud",
        "subtitles": [{"label": "English", "url": "https://example.com/sub.vtt", "default": True}],
        "intro": {"start": 0, "end": 0},
        "outro": {"start": 0, "end": 0},
        "mal_id": ""
    }
    monkeypatch.setattr(hi, "hianime_episodes", mock_episodes)
    monkeypatch.setattr(main.hi, "hianime_episodes", mock_episodes)
    monkeypatch.setattr(hi, "hianime_m3u8", mock_m3u8)
    monkeypatch.setattr(main.hi, "hianime_m3u8", mock_m3u8)
    
    # Mock AniSkip slow response (simulate hang)
    def slow_aniskip(*args, **kwargs):
        import time
        time.sleep(1.0)
        return {"intro": {"start": 10, "end": 90}, "outro": {"start": 1200, "end": 1290}}
    
    monkeypatch.setattr(main.aniskip, "get_skip_times", slow_aniskip)
    
    t0 = asyncio.get_event_loop().time()
    res = await main.resolve(slug=slug, ep=ep, mode="sub", force=True, title="Fast Anime", source="hianime")
    t1 = asyncio.get_event_loop().time()
    
    assert res["success"] is True
    # Waktu resolve harus jauh di bawah timeout lama (1.8s)
    assert (t1 - t0) < 1.5
    assert res["data"]["master"] == "https://example.com/fast.m3u8"
    # Pastikan master_body otomatis mem-prime _MASTER_CACHE
    assert main._master_cache_get("https://example.com/fast.m3u8") is not None


@pytest.mark.asyncio
async def test_master_cache_with_bytes_payload():
    """_master_cache_set dan _rewrite_m3u8_content harus kebal terhadap payload bytes (anti TypeError)."""
    test_url = "https://example.com/hls/binary_master.m3u8"
    test_bytes = b"#EXTM3U\n#EXT-X-VERSION:4\n#EXT-X-STREAM-INF:BANDWIDTH=900000,RESOLUTION=640x360\n360/index.m3u8\n"

    # 1. Simpan payload bytes
    main._master_cache_set(test_url, test_bytes)
    cached = main._master_cache_get(test_url)
    assert isinstance(cached, str)
    assert "#EXTM3U" in cached

    # 2. Rewrite m3u8 dengan argumen bytes langsung
    rewritten = main._rewrite_m3u8_content(test_bytes, test_url, "https://example.com/")
    assert isinstance(rewritten, str)
    assert "/api/player/video?url=" in rewritten
    assert 'CODECS="avc1.64001f,mp4a.40.2"' in rewritten


@pytest.mark.asyncio
async def test_proxy_video_m3u8_atomic_response():
    """Proxy m3u8 harus mengembalikan Response standar ber-Content-Length (bukan StreamingResponse chunked)."""
    from fastapi import Response
    test_url = "https://example.com/hls/atomic_test.m3u8"
    test_txt = "#EXTM3U\n#EXT-X-VERSION:4\n#EXT-X-STREAM-INF:BANDWIDTH=1200000\nindex.m3u8\n"
    main._master_cache_set(test_url, test_txt)

    resp = await main.proxy_video(url=test_url, referer="https://example.com/")
    assert isinstance(resp, Response)
    assert not hasattr(resp, "body_iterator")  # Bukan StreamingResponse
    assert resp.status_code == 200
    assert "Content-Length" in resp.headers
    assert int(resp.headers["Content-Length"]) > 0
    assert resp.headers["Cache-Control"] == "no-cache, no-transform"
    assert resp.headers["content-type"] == "application/vnd.apple.mpegurl"
    assert b"/api/player/video?url=" in resp.body

