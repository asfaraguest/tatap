import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from fastapi import HTTPException
from main import _validate_external_proxy_url
from api.hianime import _is_dpi_blocked_host


def test_is_dpi_blocked_host_wildcards():
    """Memastikan deteksi host DPI ISP mencakup subdomain wildcard dan base domains."""
    # Subdomain ZokoAnime / DramaHot
    assert _is_dpi_blocked_host("hls.dramahot.top") is True
    assert _is_dpi_blocked_host("drama1.cfd") is True
    assert _is_dpi_blocked_host("hls1.drama1.cfd") is True
    assert _is_dpi_blocked_host("hls2.drama1.cfd") is True
    assert _is_dpi_blocked_host("s1.drama1.cfd") is True
    assert _is_dpi_blocked_host("zokoanime.video") is True

    # Subdomain Puterin / Stream121
    assert _is_dpi_blocked_host("puterin.biz") is True
    assert _is_dpi_blocked_host("putarin.xyz") is True
    assert _is_dpi_blocked_host("stream121.space") is True
    assert _is_dpi_blocked_host("lowhls9.stream121.space") is True

    # Host normal tidak terpengaruh
    assert _is_dpi_blocked_host("fetch.nexabloom.top") is False
    assert _is_dpi_blocked_host("to8n3.eclipseharbor.space") is False
    assert _is_dpi_blocked_host("anichan.to") is False


def test_validate_external_proxy_url_ssrf_protection():
    """Memastikan proteksi SSRF tetap aktif menolak host lokal privat."""
    # Localhost & Loopback dilarang (HTTP 403)
    with pytest.raises(HTTPException) as exc:
        _validate_external_proxy_url("http://127.0.0.1:8767/api/stream")
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        _validate_external_proxy_url("http://localhost:8080/evil")
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        _validate_external_proxy_url("http://192.168.1.1/admin")
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        _validate_external_proxy_url("http://0.0.0.0/")
    assert exc.value.status_code == 403


def test_validate_external_proxy_url_public_cdns():
    """Memastikan URL CDN publik valid lolos tanpa melempar exception 403."""
    valid_urls = [
        "https://fetch.nexabloom.top/anime/d60e6dacf1c89065aa8738b5c569967b/master.m3u8",
        "https://to8n3.eclipseharbor.space/anime/d60e6dacf1c89065aa8738b5c569967b/seg-1-f1-v1-a1.jpg",
        "https://j1i9s.embermeadow.world/anime/d60e6dacf1c89065aa8738b5c569967b/subtitles/test.vtt",
        "https://hls.dramahot.top/p/scxqicy/master.m3u8",
        "https://puterin.biz/api/hls?t=xyz",
        "https://anichan.to/embed/test",
    ]
    for u in valid_urls:
        _validate_external_proxy_url(u)  # Tidak boleh raise


def test_android_recovery_loop_guard():
    """Memverifikasi guard anti-looping pada PlayerActivity.java."""
    with open("android/app/src/main/java/id/tatap/app/PlayerActivity.java", "r", encoding="utf-8") as f:
        src = f.read()

    assert "MAX_RECOVERY_ATTEMPTS" in src
    assert "consecutiveRecoveryAttempts" in src
    assert "if (!forceRefresh) {\n                        consecutiveRecoveryAttempts = 0;" in src
    assert "playbackState == Player.STATE_READY) {\n                    consecutiveRecoveryAttempts = 0;" in src


def test_episode_cache_ttl():
    """Memverifikasi TTL cache episode di backend/database/__init__.py adalah 2 jam (bukan 12 jam)."""
    with open("backend/database/__init__.py", "r", encoding="utf-8") as f:
        src = f.read()
    assert "async def get_episode_cache(slug: str, ep: int, mode: str, ttl=2*3600):" in src
