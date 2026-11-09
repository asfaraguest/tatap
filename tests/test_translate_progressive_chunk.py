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


@pytest.mark.asyncio
async def test_ai_and_gtxplus_cache_isolation():
    """Memastikan cache subtitle mode AI Fansub (key_llm) dan mode GTX+ (key_gtxplus)
    terisolasi secara mutlak dan tidak saling menimpa saat check_cache=true."""
    import time
    unique_id = time.time()
    test_url = f"https://example.com/subs/isolation_test_{unique_id}.vtt"
    gtx_content = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.500\nIni terjemahan teks dari mesin GTX+ dan siap tayang\n"
    ai_content = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.500\nIni terjemahan teks dari model AI Fansub dan siap tayang\n"

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Simpan terjemahan GTX+
        r1 = await client.post("/api/player/sub_cache_save", json={
            "url": test_url,
            "lang": "id",
            "mode": "gtx+",
            "vtt_text": gtx_content
        })
        assert r1.status_code == 200

        # 2. Periksa cache untuk mode AI -> WAJIB 404 (tidak boleh terisi teks GTX+!)
        r2 = await client.get(f"/api/player/sub?url={test_url}&lang=id&mode=ai&check_cache=true")
        assert r2.status_code == 404

        # 3. Simpan terjemahan AI
        r3 = await client.post("/api/player/sub_cache_save", json={
            "url": test_url,
            "lang": "id",
            "mode": "ai",
            "vtt_text": ai_content
        })
        assert r3.status_code == 200

        # 4. Periksa cache mode AI -> WAJIB 200 dengan konten AI
        r4 = await client.get(f"/api/player/sub?url={test_url}&lang=id&mode=ai&check_cache=true")
        assert r4.status_code == 200
        assert "model AI Fansub" in r4.text
        assert "cached-llm" in r4.headers.get("X-Translate-Tier", "").lower()

        # 5. Periksa cache mode GTX+ -> WAJIB tetap 200 dengan konten GTX+ asli (tidak tertimpa AI!)
        r5 = await client.get(f"/api/player/sub?url={test_url}&lang=id&mode=gtx+&check_cache=true")
        assert r5.status_code == 200
        assert "mesin GTX+" in r5.text
        assert "cached-gtx+" in r5.headers.get("X-Translate-Tier", "").lower()


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
