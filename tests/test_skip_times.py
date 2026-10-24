"""Test suite untuk verifikasi fitur skip opening dan ending anime."""
import pytest
import os
import sys
import tempfile
import asyncio
from unittest.mock import patch, MagicMock
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.api import aniskip
from backend.api import hianime as hi
from backend.database import init_db, get_episode_cache, set_episode_cache


def test_is_valid_interval():
    """Validasi interval waktu OP/ED: end > start, end > 0, dan durasi >= 5 detik."""
    assert aniskip.is_valid_interval(10.0, 100.0) is True
    assert aniskip.is_valid_interval(0.5, 90.5) is True
    assert aniskip.is_valid_interval(10.0, 15.0) is True

    # Tidak valid: durasi < 5.0 detik
    assert aniskip.is_valid_interval(10.0, 14.9) is False
    # Tidak valid: end <= start
    assert aniskip.is_valid_interval(100.0, 10.0) is False
    assert aniskip.is_valid_interval(50.0, 50.0) is False
    # Tidak valid: start/end 0 atau negatif
    assert aniskip.is_valid_interval(0, 0) is False
    assert aniskip.is_valid_interval(-10, 0) is False
    # Tidak valid: bukan angka
    assert aniskip.is_valid_interval("invalid", 100) is False
    assert aniskip.is_valid_interval(None, None) is False


def test_aniskip_empty_or_invalid():
    """AniSkip harus mengembalikan {start: 0, end: 0} jika parameter tidak valid."""
    res1 = aniskip.get_skip_times(None, 1)
    assert res1["intro"] == {"start": 0, "end": 0}
    assert res1["outro"] == {"start": 0, "end": 0}

    res2 = aniskip.get_skip_times("abc", 0)
    assert res2["intro"] == {"start": 0, "end": 0}
    assert res2["outro"] == {"start": 0, "end": 0}


def test_aniskip_query_episode_length_v2_spec():
    """AniSkip v2 mewajibkan parameter episodeLength (default 0 jika belum diketahui, atau nilai desimal jika ada)."""
    captured_urls = []

    def mock_get(url, **kwargs):
        captured_urls.append(url)
        resp = MagicMock()
        resp.status_code = 404
        return resp

    aniskip._CACHE.clear()
    with patch("httpx.Client.get", side_effect=mock_get):
        aniskip.get_skip_times(11111, 1, episode_length=0)
        assert len(captured_urls) == 1
        assert "episodeLength=0" in captured_urls[0]

        aniskip.get_skip_times(22222, 2, episode_length=1420.5)
        assert len(captured_urls) == 2
        assert "episodeLength=1420.5" in captured_urls[1]


def test_aniskip_caching_error_no_cache():
    """Error jaringan (timeout/exception) atau HTTP >= 500 / 429 tidak boleh disimpan ke cache."""
    aniskip._CACHE.clear()

    # Skenario 1: TimeoutException
    with patch("httpx.Client.get", side_effect=httpx.ConnectTimeout("Timeout connecting to aniskip")):
        res = aniskip.get_skip_times(33333, 1)
        assert res["intro"] == {"start": 0, "end": 0}
        assert (33333, 1) not in aniskip._CACHE
        assert ("mal", 33333, 1) not in aniskip._CACHE

    # Skenario 2: HTTP 500 Server Error
    mock_500 = MagicMock()
    mock_500.status_code = 500
    with patch("httpx.Client.get", return_value=mock_500):
        res = aniskip.get_skip_times(44444, 1)
        assert res["intro"] == {"start": 0, "end": 0}
        assert (44444, 1) not in aniskip._CACHE
        assert ("mal", 44444, 1) not in aniskip._CACHE


def test_aniskip_negative_cache_on_404():
    """HTTP 404 harus disimpan ke cache dengan TTL 900 detik (15 menit)."""
    aniskip._CACHE.clear()
    mock_404 = MagicMock()
    mock_404.status_code = 404

    with patch("httpx.Client.get", return_value=mock_404):
        res = aniskip.get_skip_times(55555, 1)
        assert res["intro"] == {"start": 0, "end": 0}
        assert ("mal", 55555, 1) in aniskip._CACHE
        entry, ts, ttl = aniskip._CACHE[("mal", 55555, 1)]
        assert ttl == 900


def test_cross_provider_skip_cache():
    """Timestamp OP/ED dari HiAnime/AniSkip dapat dibaca oleh Otakudesu via title/mal_id."""
    aniskip._CACHE.clear()
    mal_id = 52991
    title = "Sousou no Frieren"
    ep = 5
    intro = {"start": 85.0, "end": 175.0}
    outro = {"start": 1250.0, "end": 1340.0}

    # Simpan dari provider pertama (misal HiAnime)
    aniskip.store_skip_times(mal_id=mal_id, title=title, ep=ep, intro=intro, outro=outro)

    # Ambil via variasi slug Otakudesu
    cached_by_otaku_slug = aniskip.get_cached_skip_times(title="otakudesu:sousou-no-frieren-sub-indo", ep=ep)
    assert cached_by_otaku_slug is not None
    assert cached_by_otaku_slug["intro"] == {"start": 85.0, "end": 175.0}
    assert cached_by_otaku_slug["outro"] == {"start": 1250.0, "end": 1340.0}

    # Ambil via mal_id
    cached_by_mal = aniskip.get_cached_skip_times(mal_id=mal_id, ep=ep)
    assert cached_by_mal is not None
    assert cached_by_mal["intro"] == {"start": 85.0, "end": 175.0}


def test_aniskip_parsing_success():
    """AniSkip harus berhasil mem-parsing response yang berisi OP dan ED."""
    aniskip._CACHE.clear()
    mock_payload = {
        "found": True,
        "results": [
            {
                "skipType": "op",
                "interval": {"startTime": 12.5, "endTime": 102.5}
            },
            {
                "skipType": "ed",
                "interval": {"startTime": 1300.0, "endTime": 1390.0}
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_payload

    with patch("httpx.Client.get", return_value=mock_resp):
        res = aniskip.get_skip_times(99999, 1)
        assert res["intro"] == {"start": 12.5, "end": 102.5}
        assert res["outro"] == {"start": 1300.0, "end": 1390.0}
        # Verifikasi TTL 86400 (24 jam)
        assert ("mal", 99999, 1) in aniskip._CACHE
        entry, ts, ttl = aniskip._CACHE[("mal", 99999, 1)]
        assert ttl == 86400


@pytest.mark.asyncio
async def test_database_episode_cache_intro_outro():
    """Database episode_cache harus menyimpan dan memulihkan intro & outro secara utuh."""
    await init_db()
    slug = "test-skip-anime-cache"
    ep = 1
    mode = "sub"
    master = "https://example.com/master.m3u8"
    variants = [{"q": "1080p", "url": "https://example.com/1080.m3u8"}]
    intro = {"start": 85.0, "end": 175.0}
    outro = {"start": 1250.0, "end": 1340.0}

    await set_episode_cache(slug, ep, mode, master, variants,
                            "https://example.com/sub.vtt", "Indonesian",
                            "https://example.com/", "HD-1",
                            subtitles=[{"label": "Indonesian", "url": "https://example.com/sub.vtt", "default": True}],
                            intro=intro, outro=outro)

    cached = await get_episode_cache(slug, ep, mode)
    assert cached is not None
    assert cached["intro"] == {"start": 85.0, "end": 175.0}
    assert cached["outro"] == {"start": 1250.0, "end": 1340.0}


def test_aniskip_mal_id_in_memory_cache():
    """Cache in-memory pemetaan slug/judul -> mal_id harus bekerja dua arah."""
    aniskip._TITLE_TO_MAL.clear()
    assert aniskip.get_mal_id_from_cache("dandadan-19319") == 0

    aniskip.store_mal_id("dandadan-19319", 57334)
    assert aniskip.get_mal_id_from_cache("dandadan-19319") == 57334
    assert aniskip.get_mal_id_from_cache("dandadan") == 57334

    aniskip.store_mal_id("Bleach: Thousand-Year Blood War", "56784")
    assert aniskip.get_mal_id_from_cache("Bleach: Thousand-Year Blood War") == 56784
    assert aniskip.get_mal_id_from_cache("bleach thousand year blood war") == 56784


@pytest.mark.asyncio
async def test_resolve_mal_id_and_stream_skip_injection(monkeypatch):
    """Endpoint stream harus mampu menyelesaikan mal_id anime terbaru dan menginjeksi intro/outro dari AniSkip."""
    from backend import main
    await init_db()

    slug = "dandadan-19319"
    ep = 1

    # Mock AniList resolve_mal_id_by_title
    monkeypatch.setattr(main.al, "resolve_mal_id_by_title", lambda q: 57334)

    # Mock AniSkip get_skip_times
    def mock_get_skip(m_id, episode_num, episode_length=0, timeout=4.0):
        if int(m_id) == 57334 and int(episode_num) == 1:
            return {
                "intro": {"start": 2.65, "end": 92.65},
                "outro": {"start": 1348.45, "end": 1479.17}
            }
        return {"intro": {"start": 0, "end": 0}, "outro": {"start": 0, "end": 0}}

    monkeypatch.setattr(main.aniskip, "get_skip_times", mock_get_skip)
    monkeypatch.setattr(aniskip, "get_skip_times", mock_get_skip)

    # Mock hi resolver
    monkeypatch.setattr(hi, "hianime_episodes", lambda s: [{"ep": 1, "ep_id": "111"}])
    monkeypatch.setattr(hi, "hianime_m3u8", lambda maps, e, m, s: {
        "master": "https://example.com/dandadan.m3u8",
        "variants": [{"q": "1080p", "url": "https://example.com/dandadan.m3u8"}],
        "sub": "https://example.com/sub.vtt",
        "sub_lang": "English",
        "referer": "https://megaplay.buzz/",
        "server": "HD-1",
        "subtitles": [{"label": "English", "url": "https://example.com/sub.vtt", "default": True}],
        "intro": {"start": 0, "end": 0},
        "outro": {"start": 0, "end": 0},
        "mal_id": ""
    })

    res = await main.resolve(slug=slug, ep=ep, mode="sub", force=True, title="Dandadan")
    assert res["success"] is True
    data = res["data"]
    assert data["mal_id"] == "57334"
    assert data["intro"]["end"] == 92.65
    assert data["outro"]["start"] == 1348.45


@pytest.mark.asyncio
async def test_apostrophe_normalization_and_token_overlap():
    """Slug kepemilikan Inggris seperti -s- harus dinormalisasi menjadi 's dan mencocokkan token."""
    from backend import main
    from backend.api import anilist

    # Test token overlap helper
    assert anilist._match_title_tokens("The World's Strongest Witch", "The World's Strongest Witch") is True
    assert anilist._match_title_tokens("The World's Strongest Witch", "The World's Most Famous Tales") is False

    # Test apostrophe normalization in main._resolve_mal_id
    aniskip.store_mal_id("the world's strongest witch", "64084")
    resolved = await main._resolve_mal_id("the-world-s-strongest-witch-10525", title="")
    assert resolved == "64084"


def test_multi_season_normalization_no_collision():
    """Normalisasi judul harus membedakan Season 1, Season 2, dan Part tanpa tabrakan cache."""
    s1 = aniskip.normalize_title("Re:Zero kara Hajimeru Isekai Seikatsu")
    s2_hi = aniskip.normalize_title("Re:Zero kara Hajimeru Isekai Seikatsu 2nd Season")
    s2_otaku = aniskip.normalize_title("otakudesu:re-zero-kara-hajimeru-isekai-seikatsu-season-2-sub-indo")
    s3_hi = aniskip.normalize_title("Re:Zero kara Hajimeru Isekai Seikatsu 3rd Season")
    s3_otaku = aniskip.normalize_title("otakudesu:re-zero-kara-hajimeru-isekai-seikatsu-season-3-sub-indo")

    # Antar provider harus cocok untuk season yang sama
    assert s2_hi == s2_otaku
    assert s3_hi == s3_otaku

    # Antar season TIDAK boleh bertabrakan
    assert s1 != s2_hi
    assert s2_hi != s3_hi
    assert s1 != s3_hi

    # Part / Cour juga harus terlindungi dari tabrakan
    p2 = aniskip.normalize_title("Bleach: Thousand-Year Blood War Part 2")
    p3 = aniskip.normalize_title("Bleach: Thousand-Year Blood War Part 3")
    assert p2 != p3


def test_apostrophe_nouns_and_curly_quote_matching():
    """Kata kepemilikan tanpa spasi seperti journeys & heavens serta kutip lengkung harus cocok."""
    from backend.api import anilist

    assert anilist._match_title_tokens("frieren beyond journeys end", "Frieren: Beyond Journey’s End") is True
    assert anilist._match_title_tokens("fate stay night heavens feel i presage flower", "Fate/stay night [Heaven's Feel] I. presage flower") is True
    assert anilist._match_title_tokens("the worlds strongest witch", "The World's Strongest Witch") is True
    assert anilist._match_title_tokens("the worlds strongest witch", "The World's Most Famous Tales") is False


@pytest.mark.asyncio
async def test_persistent_sqlite_mal_map():
    """Pemetaan mal_map harus tersimpan persisten di database SQLite."""
    from backend.database import init_db, set_mal_map, get_mal_map
    await init_db()

    test_slug = "frieren-beyond-journeys-end-18542"
    await set_mal_map(test_slug, 52991)

    fetched = await get_mal_map(test_slug)
    assert fetched == 52991


