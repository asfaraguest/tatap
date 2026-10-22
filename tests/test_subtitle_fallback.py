import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from api import hianime as hi
from api.translate import parse_vtt, build_vtt
from main import app

client = TestClient(app)


def test_srt_parsing_and_webvtt_conversion():
    """Memastikan parse_vtt dan build_vtt mengonversi teks format SRT standar (dengan koma) ke WebVTT standar."""
    srt_content = """1
00:00:01,000 --> 00:00:04,500
Halo dunia anime!

2
00:00:05,200 --> 00:00:08,700
Ini subtitle baris kedua.
"""
    cues = parse_vtt(srt_content)
    assert len(cues) == 2
    assert cues[0]["start"] == 1.0
    assert cues[0]["end"] == 4.5
    assert "Halo dunia anime!" in cues[0]["text"]
    assert cues[1]["start"] == 5.2
    assert cues[1]["end"] == 8.7
    assert "Ini subtitle baris kedua." in cues[1]["text"]

    vtt_output = build_vtt(cues)
    assert "WEBVTT" in vtt_output
    assert "00:00:01.000 --> 00:00:04.500" in vtt_output
    assert "00:00:05.200 --> 00:00:08.700" in vtt_output


def test_harvest_subtitles_from_alternative_server(monkeypatch):
    """Simulasi pemanenan subtitle dari server alternatif ketika server aktif mengembalikan tracks kosong."""
    mock_servers = [
        {"name": "HD-1", "embed": "https://megaplay.buzz/embed/1"},
        {"name": "Vidstream-2", "embed": "https://megaplay.buzz/embed/2"}
    ]

    def mock_try_megaplay(embed):
        if "embed/2" in embed:
            return {
                "subtitles": [{"label": "English", "lang": "en", "url": "https://cdn.example.com/sub/en.vtt", "default": True}],
                "sub": "https://cdn.example.com/sub/en.vtt",
                "sub_lang": "English",
                "referer": "https://megaplay.buzz/"
            }
        return {"subtitles": [], "sub": None, "sub_lang": None}

    monkeypatch.setattr(hi, "_try_megaplay", mock_try_megaplay)

    harvested = hi._harvest_subtitles(mock_servers, current_srv_name="HD-1")
    assert harvested is not None
    assert len(harvested["subtitles"]) == 1
    assert harvested["subtitles"][0]["label"] == "English"
    assert harvested["sub"] == "https://cdn.example.com/sub/en.vtt"


def test_hianime_subtitles_for_episode(monkeypatch):
    """Memastikan helper hianime_subtitles_for_episode memanen subtitle dari episode tertentu."""
    monkeypatch.setattr(hi, "hianime_episodes", lambda slug: [{"ep": 1, "ep_id": "12345"}])
    monkeypatch.setattr(hi, "_fetch", lambda url, **kwargs: '<div class="server-item" data-type="sub" data-hash="aHR0cHM6Ly9tZWdhcGxheS5idXp6L2VtYmVkLzE=" data-server-name="HD-1"></div>')
    monkeypatch.setattr(hi, "_try_megaplay", lambda embed: {
        "subtitles": [{"label": "English", "lang": "en", "url": "https://cdn.example.com/sub/en.vtt", "default": True}],
        "sub": "https://cdn.example.com/sub/en.vtt",
        "sub_lang": "English",
        "referer": "https://megaplay.buzz/"
    })

    res = hi.hianime_subtitles_for_episode("test-slug", 1)
    assert res is not None
    assert len(res["subtitles"]) == 1
    assert res["subtitles"][0]["url"] == "https://cdn.example.com/sub/en.vtt"


def test_api_sub_custom_upload_and_get():
    """Uji alur lengkap endpoint /api/player/sub_custom: upload teks SRT, konversi ke WebVTT, dan fetch ulang."""
    srt_raw = """1
00:00:01,500 --> 00:00:04,000
Tes upload file subtitle lokal Tatap.
"""
    # 1. POST upload teks subtitle
    resp = client.post("/api/player/sub_custom", json={
        "text": srt_raw,
        "filename": "my_subs.srt",
        "lang": "en"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    sub_id = data["data"]["id"]
    sub_url = data["data"]["url"]
    assert data["data"]["cues_count"] == 1
    assert "my_subs.srt" in data["data"]["label"]

    # 2. GET subtitle yang baru di-upload
    resp_get = client.get(sub_url)
    assert resp_get.status_code == 200
    assert "text/vtt" in resp_get.headers.get("content-type", "")
    assert "WEBVTT" in resp_get.text
    assert "00:00:01.500 --> 00:00:04.000" in resp_get.text
    assert "Tes upload file subtitle lokal Tatap." in resp_get.text


def test_api_sub_custom_empty_error():
    """Memastikan penanganan error jika upload subtitle kosong atau tidak valid."""
    resp = client.post("/api/player/sub_custom", json={"text": "", "url": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "kosong" in data["error"].lower()


@pytest.mark.asyncio
async def test_episode_resolve_bypass_negative_and_refresh():
    """Uji bypass cache beracun (tanpa subtitle di mode sub), endpoint /api/episode alias, dan parameter refresh=True."""
    from database import set_episode_cache, get_episode_cache, init_db

    await init_db()
    test_slug = "test-negative-sub-slug"

    # 1. Simpan entri cache beracun dengan subtitles: [] dan sub: "28" (bentrokan metadata bookmark)
    await set_episode_cache(
        slug=test_slug,
        ep=1,
        mode="sub",
        master="https://cdn.example.com/stream.m3u8",
        variants=[],
        sub="28",
        sub_lang="",
        referer="",
        server="test",
        subtitles=[]
    )
    # Pastikan tersimpan di DB
    cached = await get_episode_cache(test_slug, 1, "sub")
    assert cached is not None
    assert cached["sub"] == "28"

    # 2. Panggil GET /api/episode (alias resolver). Resolver harus mendeteksi cache beracun tersebut,
    # menghapusnya dari episode_cache, dan bypass ke live scraper (yang akan mengembalikan response)
    resp = client.get(f"/api/episode?slug={test_slug}&ep=1&mode=sub")
    assert resp.status_code == 200
    # Cache beracun di DB wajib sudah dihapus
    cleaned = await get_episode_cache(test_slug, 1, "sub")
    # Jika scraper gagal karena mock/network, cleaned bernilai None (karena negative caching dicegah)
    if cleaned is not None:
        # Jika tersimpan, pastikan memiliki subtitle valid
        assert cleaned["sub"] != "28"

    # 3. Uji parameter refresh=True / refresh=1 pada /api/stream/resolve
    await set_episode_cache(
        slug=test_slug,
        ep=2,
        mode="sub",
        master="https://cdn.example.com/stream2.m3u8",
        variants=[],
        sub="https://cdn.example.com/sub2.vtt",
        sub_lang="en",
        referer="",
        server="test",
        subtitles=[{"url": "https://cdn.example.com/sub2.vtt", "lang": "en"}]
    )
    assert await get_episode_cache(test_slug, 2, "sub") is not None
    resp_refresh = client.get(f"/api/stream/resolve?slug={test_slug}&ep=2&mode=sub&refresh=1")
    assert resp_refresh.status_code == 200
