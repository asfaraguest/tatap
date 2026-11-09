"""Unit test untuk Progressive Chunking Lazy Load Translate (AI & GTX+)."""
import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

import main  # noqa: E402


@pytest.mark.asyncio
async def test_sub_chunk_gtxplus_translate(monkeypatch):
    """Memastikan endpoint /api/player/sub_chunk berhasil menerjemahkan chunk cues via mode gtx+."""
    async def fake_translate_with_fallback(cues, src, tgt, requested_mode="gtx"):
        out = []
        for c in cues:
            out.append({
                "start": c["start"],
                "end": c["end"],
                "text": f"Terjemahan: {c['text']}"
            })
        return {"cues": out, "level": "tier2", "engine": "gtx+"}

    monkeypatch.setattr(main, "_translate_with_fallback", fake_translate_with_fallback)

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "cues": [
                {"start": 1.0, "end": 2.5, "text": "Hello world"},
                {"start": 3.0, "end": 4.5, "text": "Good morning"}
            ],
            "mode": "gtx+",
            "src": "en",
            "tgt": "id"
        }
        res = await client.post("/api/player/sub_chunk", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["data"]["cues"]) == 2
        assert "Terjemahan: Hello world" in data["data"]["cues"][0]["text"]
        assert data["data"]["tier"] == "tier2"


@pytest.mark.asyncio
async def test_sub_chunk_ai_translate(monkeypatch):
    """Memastikan endpoint /api/player/sub_chunk mendukung mode ai dengan metadata engine."""
    async def fake_translate_with_fallback(cues, src, tgt, requested_mode="gtx"):
        out = []
        for c in cues:
            out.append({
                "start": c["start"],
                "end": c["end"],
                "text": f"AI Fansub: {c['text']}"
            })
        return {"cues": out, "level": "tier3", "engine": "ai", "model": "gemini-2.0-flash"}

    monkeypatch.setattr(main, "_translate_with_fallback", fake_translate_with_fallback)

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "cues": [
                {"start": 0.0, "end": 1.5, "text": "Let's go to school"}
            ],
            "mode": "ai",
            "src": "en",
            "tgt": "id"
        }
        res = await client.post("/api/player/sub_chunk", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "AI Fansub:" in data["data"]["cues"][0]["text"]
        assert data["data"]["engine"] == "ai"


@pytest.mark.asyncio
async def test_sub_cache_save_and_check_cache():
    """Memastikan /api/player/sub_cache_save menyimpan hasil rakitan WebVTT ke cache,
    dan /api/player/sub dengan check_cache=true mengembalikan cache hit atau 404 cache miss."""
    import time
    test_url = f"https://example.com/subs/progressive_test_sub_{time.time()}.vtt"
    vtt_content = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.500\nHalo ini dunia dari progressive chunking dan subtitle siap\n"

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Sebelum disimpan, periksa check_cache -> wajib 404 cache miss
        miss_res = await client.get(f"/api/player/sub?url={test_url}&lang=id&mode=gtx+&check_cache=true")
        assert miss_res.status_code == 404
        assert miss_res.json().get("cached") is False

        # 2. Simpan hasil rakitan chunk
        save_res = await client.post("/api/player/sub_cache_save", json={
            "url": test_url,
            "lang": "id",
            "mode": "gtx+",
            "vtt_text": vtt_content
        })
        assert save_res.status_code == 200
        assert save_res.json()["success"] is True

        # 3. Sesudah disimpan, periksa check_cache -> wajib 200 cache hit dengan konten WebVTT
        hit_res = await client.get(f"/api/player/sub?url={test_url}&lang=id&mode=gtx+&check_cache=true")
        assert hit_res.status_code == 200
        assert "Halo ini dunia dari progressive chunking" in hit_res.text
        assert "cached" in hit_res.headers.get("X-Translate-Tier", "").lower()


def test_frontend_progressive_chunk_components():
    """Memastikan fungsi dan styling progressive chunking terpasang lengkap di frontend."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    app_js = (root / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    style_css = (root / "frontend" / "css" / "style.css").read_text(encoding="utf-8")

    assert "function startProgressiveChunkTranslate(" in app_js
    assert "function prioritizeChunkForTime(" in app_js
    assert "/api/player/sub_chunk" in app_js
    assert "/api/player/sub_cache_save" in app_js
    assert "sub-translating" in style_css
    assert "subPulse" in style_css
    assert "[Menerjemahkan...]" in app_js
