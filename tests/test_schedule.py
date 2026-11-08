"""Unit test untuk anime 3-day schedule API (/api/schedule dan /api/upcoming-episodes)."""
import asyncio
import os
import sys
import time
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

import main  # noqa: E402
import api.anilist as al  # noqa: E402


@pytest.mark.asyncio
async def test_schedule_endpoint_filter_and_3days(monkeypatch):
    """Pastikan /api/schedule hanya menyertakan anime yang valid di aplikasi dan dibagi dalam 3 hari."""

    now_utc = int(time.time())
    wib_offset = 7 * 3600
    today_wib = ((now_utc + wib_offset) // 86400) * 86400

    fake_schedules = [
        {
            "id": 101,
            "airingAt": today_wib - 40000,  # Kemarin WIB
            "episode": 1,
            "media": {
                "id": 1,
                "title": {"romaji": "Anime Kemarin Ada", "english": "Yesterday Anime Valid"},
                "format": "TV",
                "averageScore": 75,
                "coverImage": {"large": "https://example.com/cover1.jpg"},
            },
        },
        {
            "id": 102,
            "airingAt": today_wib + 10000,  # Hari Ini WIB
            "episode": 2,
            "media": {
                "id": 2,
                "title": {"romaji": "Anime Hari Ini Ada", "english": "Today Anime Valid"},
                "format": "TV",
                "averageScore": 82,
                "coverImage": {"large": "https://example.com/cover2.jpg"},
            },
        },
        {
            "id": 103,
            "airingAt": today_wib + 20000,  # Hari Ini WIB tapi TIDAK ADA di scraper (harus di-remove)
            "episode": 5,
            "media": {
                "id": 3,
                "title": {"romaji": "Anime Ghaib", "english": "Phantom Anime"},
                "format": "TV",
                "averageScore": 60,
                "coverImage": {"large": "https://example.com/cover3.jpg"},
            },
        },
        {
            "id": 104,
            "airingAt": today_wib + 100000,  # Besok WIB
            "episode": 3,
            "media": {
                "id": 4,
                "title": {"romaji": "Anime Besok Ada", "english": "Tomorrow Anime Valid"},
                "format": "TV",
                "averageScore": 88,
                "coverImage": {"large": "https://example.com/cover4.jpg"},
            },
        },
    ]

    def fake_schedules_range(start_ts, end_ts, max_pages=3):
        return fake_schedules

    async def fake_match_batch(items):
        # Anime Ghaib / Phantom Anime tidak ada match (None) -> harus di-remove oleh endpoint
        mapping = {
            "Yesterday Anime Valid": "anime-kemarin-ada-111",
            "Today Anime Valid": "anime-hari-ini-ada-222",
            "Tomorrow Anime Valid": "anime-besok-ada-444",
        }
        return [(t, mapping.get(t)) for t, _ in items]

    async def fake_get_cache(key, ttl=None):
        return None

    async def fake_set_cache(key, payload):
        return None

    monkeypatch.setattr(al, "anilist_schedules_range", fake_schedules_range)
    monkeypatch.setattr(main, "_match_slug_batch", fake_match_batch)
    monkeypatch.setattr(main, "get_browse_cache", fake_get_cache)
    monkeypatch.setattr(main, "set_browse_cache", fake_set_cache)

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as ac:
        # 1. Test 'today' (default)
        r_today = await ac.get("/api/schedule?day=today")
        assert r_today.status_code == 200
        res_today = r_today.json()
        assert res_today["success"] is True
        d_today = res_today["data"]
        assert d_today["day"] == "today"
        items_today = d_today["items"]
        assert len(items_today) == 1
        assert items_today[0]["title"] == "Today Anime Valid"
        assert items_today[0]["id"] == "anime-hari-ini-ada-222"
        assert "WIB" in items_today[0]["time"]
        assert items_today[0]["episode"] == 2
        assert d_today["counts"]["today"] == 1
        assert d_today["counts"]["yesterday"] == 1
        assert d_today["counts"]["tomorrow"] == 1

        # 2. Test 'yesterday'
        r_yesterday = await ac.get("/api/schedule?day=yesterday")
        assert r_yesterday.status_code == 200
        res_yesterday = r_yesterday.json()
        assert res_yesterday["success"] is True
        assert res_yesterday["data"]["day"] == "yesterday"
        assert len(res_yesterday["data"]["items"]) == 1
        assert res_yesterday["data"]["items"][0]["id"] == "anime-kemarin-ada-111"

        # 3. Test 'tomorrow'
        r_tomorrow = await ac.get("/api/schedule?day=tomorrow")
        assert r_tomorrow.status_code == 200
        res_tomorrow = r_tomorrow.json()
        assert res_tomorrow["success"] is True
        assert res_tomorrow["data"]["day"] == "tomorrow"
        assert len(res_tomorrow["data"]["items"]) == 1
        assert res_tomorrow["data"]["items"][0]["id"] == "anime-besok-ada-444"

        # 4. Pastikan 'Phantom Anime' 100% di-remove dari semua bucket
        r_all = await ac.get("/api/schedule?day=all")
        assert r_all.status_code == 200
        res_all = r_all.json()
        assert res_all["success"] is True
        all_titles = [x["title"] for b in ["yesterday", "today", "tomorrow"] for x in res_all["data"][b]]
        assert "Phantom Anime" not in all_titles
        assert len(all_titles) == 3


@pytest.mark.asyncio
async def test_upcoming_episodes_synced(monkeypatch):
    """Pastikan /api/upcoming-episodes juga memanggil jadwal 3 hari."""
    now_utc = int(time.time())
    wib_offset = 7 * 3600
    today_wib = ((now_utc + wib_offset) // 86400) * 86400

    fake_schedules = [
        {
            "id": 999,
            "airingAt": today_wib + 5000,
            "episode": 10,
            "media": {
                "id": 99,
                "title": {"romaji": "Anime Synced Title", "english": "Anime Synced English"},
                "format": "TV",
                "averageScore": 90,
                "coverImage": {"large": "https://example.com/cover99.jpg"},
            },
        }
    ]

    async def fake_batch_synced(items):
        return [("Anime Synced English", "anime-synced-slug-99")]

    async def fake_cache_synced(key, ttl=None):
        return None

    async def fake_set_synced(key, payload):
        return None

    monkeypatch.setattr(al, "anilist_schedules_range", lambda s, e, max_pages=3: fake_schedules)
    monkeypatch.setattr(main, "_match_slug_batch", fake_batch_synced)
    monkeypatch.setattr(main, "get_browse_cache", fake_cache_synced)
    monkeypatch.setattr(main, "set_browse_cache", fake_set_synced)

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as ac:
        r = await ac.get("/api/upcoming-episodes?day=today")
        assert r.status_code == 200
        res = r.json()
        assert res["success"] is True
        assert len(res["data"]["items"]) == 1
        assert res["data"]["items"][0]["id"] == "anime-synced-slug-99"


@pytest.mark.asyncio
async def test_schedule_7days_full_weekly(monkeypatch):
    """Pastikan seluruh 7 hari mingguan (Senin-Minggu / Monday-Sunday) terpetakan dengan benar."""
    import datetime as _dt
    now_utc = int(time.time())
    wib_offset = 7 * 3600
    now_dt = _dt.datetime.fromtimestamp(now_utc, _dt.timezone(_dt.timedelta(hours=7)))
    cur_weekday = now_dt.weekday()

    today_wib = ((now_utc + wib_offset) // 86400) * 86400
    mon_wib = today_wib - (cur_weekday * 86400)

    days_en = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    days_id = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]

    # Buat 1 anime mock untuk setiap hari dalam pekan (7 anime)
    fake_items = []
    mapping = {}
    for i in range(7):
        airing_ts = mon_wib + (i * 86400) + 3600  # 01:00 WIB di hari ke-i
        title = f"Anime Day {days_en[i].capitalize()}"
        slug = f"anime-day-{days_en[i]}-slug"
        mapping[title] = slug
        fake_items.append({
            "id": 200 + i,
            "airingAt": airing_ts,
            "episode": i + 1,
            "media": {
                "id": 200 + i,
                "title": {"romaji": title, "english": title},
                "format": "TV",
                "averageScore": 80,
                "coverImage": {"large": f"https://example.com/cover_{i}.jpg"},
            },
        })

    async def fake_batch_7(items):
        return [(t, mapping.get(t)) for t, _ in items]

    async def fake_get_cache_7(key, ttl=None):
        return None

    async def fake_set_cache_7(key, payload):
        return None

    monkeypatch.setattr(al, "anilist_schedules_range", lambda s, e, max_pages=6: fake_items)
    monkeypatch.setattr(main, "_match_slug_batch", fake_batch_7)
    monkeypatch.setattr(main, "get_browse_cache", fake_get_cache_7)
    monkeypatch.setattr(main, "set_browse_cache", fake_set_cache_7)

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as ac:
        # 1. Test semua 7 hari via nama Inggris
        for idx, day_name in enumerate(days_en):
            r = await ac.get(f"/api/schedule?day={day_name}")
            assert r.status_code == 200
            res = r.json()
            assert res["success"] is True
            d = res["data"]
            assert d["day"] == day_name
            assert len(d["items"]) == 1
            assert d["items"][0]["title"] == f"Anime Day {day_name.capitalize()}"
            assert d["items"][0]["id"] == f"anime-day-{day_name}-slug"
            assert d["counts"][day_name] == 1
            if idx == cur_weekday:
                assert d["is_today"] is True
            else:
                assert d["is_today"] is False

        # 2. Test semua 7 hari via nama Indonesia
        for idx, day_id in enumerate(days_id):
            r = await ac.get(f"/api/schedule?day={day_id}")
            assert r.status_code == 200
            res = r.json()
            assert res["success"] is True
            d = res["data"]
            assert d["day"] == days_en[idx]
            assert len(d["items"]) == 1
            assert d["items"][0]["title"] == f"Anime Day {days_en[idx].capitalize()}"

        # 3. Test day=all memuat semua 7 hari
        r_all = await ac.get("/api/schedule?day=all")
        assert r_all.status_code == 200
        res_all = r_all.json()
        assert res_all["success"] is True
        d_all = res_all["data"]
        assert d_all["total"] == 7
        for day_name in days_en:
            assert len(d_all[day_name]) == 1
