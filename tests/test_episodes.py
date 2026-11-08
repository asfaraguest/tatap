import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
import main
from database import init_db

@pytest.mark.asyncio
async def test_episodes_caching(monkeypatch):
    await init_db()
    from database import _write_db
    async with _write_db() as db:
        await db.execute("DELETE FROM browse_cache WHERE key LIKE '%test-long-anime-99999%'")
        await db.commit()
    # Mock hianime_episodes untuk kecepatan unit test offline yang konsisten
    fake_eps = [{"ep": i, "ep_id": str(i)} for i in range(1, 1101)]
    monkeypatch.setattr(main.hi, "hianime_episodes", lambda slug: fake_eps)

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as ac:
        r1 = await ac.get("/api/anime/test-long-anime-99999/episodes")
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["success"] is True
        assert d1["data"]["total"] == 1100
        assert d1["data"]["cached"] is False

        # Panggilan kedua harus cache hit
        r2 = await ac.get("/api/anime/test-long-anime-99999/episodes")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["success"] is True
        assert d2["data"]["cached"] is True
        assert d2["data"]["total"] == 1100
