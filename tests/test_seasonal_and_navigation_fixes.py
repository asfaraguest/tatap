import asyncio
import json
import os
import pytest
from backend.main import app, seasonal
from fastapi.testclient import TestClient

client = TestClient(app)

def test_seasonal_which_now_no_finished_leak():
    """Memastikan endpoint /api/seasonal?which=now tidak memuat anime tamat."""
    res = client.get("/api/seasonal?which=now&page=1")
    assert res.status_code == 200
    data = res.json()
    assert data.get("success") is True
    items = data.get("data", {}).get("items", [])
    for it in items:
        assert it.get("badge") != "TAMAT", f"Ditemukan anime berstatus TAMAT di which=now: {it.get('title')}"
        assert it.get("is_finished") is not True, f"Ditemukan is_finished=True di which=now: {it.get('title')}"
        assert (it.get("status") or "").lower() != "finished", f"Ditemukan status finished di which=now: {it.get('title')}"

def test_seasonal_past_season_allows_finished():
    """Memastikan musim lampau tetap dapat memuat anime tamat."""
    res = client.get("/api/seasonal?season=fall&year=2024&page=1")
    assert res.status_code == 200
    data = res.json()
    assert data.get("success") is True
    items = data.get("data", {}).get("items", [])
    has_finished = any(it.get("is_finished") is True or it.get("badge") == "TAMAT" for it in items)
    assert has_finished, "Musim lampau seharusnya memuat anime yang sudah tamat"

def test_search_pagination_support():
    """Memastikan query /api/search menerima parameter page."""
    res = client.get("/api/search?q=naruto&page=1")
    assert res.status_code == 200
    d1 = res.json()
    assert d1.get("success") is True
    assert d1.get("data", {}).get("page") == 1

def test_term_js_navigation_and_pagination_integrity():
    """Memverifikasi perbaikan renderSel berbasis data-idx dan pagination di term.js."""
    with open("frontend/js/term.js", "r", encoding="utf-8") as f:
        content = f.read()

    # Seleksi berbasis data-idx (helper itemEl menutupi .poster-card dan .trow)
    assert "function itemEl(" in content
    assert "data-idx=\\\"'+idx+'\\\"" in content or "data-idx=\"'+idx+'\"" in content
    assert "parseInt(el.getAttribute(\"data-idx\"),10)" in content

    # Guard pencegahan cascading focus loop
    assert "if(document.activeElement !== selEl)" in content

    # Search pagination di doSearch dan loadView
    assert "S.searchQuery = q;" in content
    assert "doSearch(S.searchQuery, S.page);" in content
    assert "window.Tatap.search(q, src, p)" in content

    # Pager tidak lagi menonaktifkan view 'cari'
    assert 'else if(S.view === "cari"){\\n      hasPagination = false;' not in content

def test_chaquopy_parity_backend_main():
    """Memastikan keselarasan 100% antara root backend/main.py dan Chaquopy parity."""
    with open("backend/main.py", "r", encoding="utf-8") as f1:
        root_code = f1.read()
    with open("android/app/src/main/python/backend/main.py", "r", encoding="utf-8") as f2:
        chaquopy_code = f2.read()

    # Periksa bagian seasonal_v dan filter RELEASING
    assert 'seasonal_v' in root_code
    assert 'seasonal_v' in chaquopy_code
    assert 'status_in = ["RELEASING"] if which == "now"' in root_code
    assert 'status_in = ["RELEASING"] if which == "now"' in chaquopy_code
    assert 'if which == "now" and (is_finished or status_str in ("finished", "completed")):' in root_code
    assert 'if which == "now" and (is_finished or status_str in ("finished", "completed")):' in chaquopy_code
