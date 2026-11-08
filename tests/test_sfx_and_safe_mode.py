import os
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from backend.main import app, _parse_safe_mode
from starlette.testclient import TestClient

client = TestClient(app)

def test_parse_safe_mode_values():
    assert _parse_safe_mode(1) == 1
    assert _parse_safe_mode(0) == 0
    assert _parse_safe_mode("1") == 1
    assert _parse_safe_mode("0") == 0
    assert _parse_safe_mode("false") == 0
    assert _parse_safe_mode("off") == 0
    assert _parse_safe_mode("mati") == 0
    assert _parse_safe_mode("true") == 1
    assert _parse_safe_mode("on") == 1
    assert _parse_safe_mode("aktif") == 1
    assert _parse_safe_mode(None) == 1

def test_safe_mode_setting_endpoint():
    # Test setting safe_mode via /api/settings
    res = client.post("/api/settings", json={"safe_mode": "1"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    res_get = client.get("/api/settings")
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["success"] is True
    assert get_data["data"]["safe_mode"] in ("1", 1)

    # Toggle to 0
    res0 = client.post("/api/settings", json={"safe_mode": "0"})
    assert res0.status_code == 200
    res_get0 = client.get("/api/settings")
    assert res_get0.json()["data"]["safe_mode"] in ("0", 0)

    # Revert to 1
    client.post("/api/settings", json={"safe_mode": "1"})

def test_rule_4_hentai_blacklist_enforced_regardless_of_safe_mode():
    # Querying hentai must always return empty results even if safe_mode is 0
    res_hentai_unsafe = client.get("/api/search?q=hentai&safe_mode=0")
    assert res_hentai_unsafe.status_code == 200
    data = res_hentai_unsafe.json()
    assert data["success"] is True
    assert data["data"]["results"] == []

    # Safe mode = 1 also blocks ecchi in query
    res_ecchi_safe = client.get("/api/search?q=ecchi&safe_mode=1")
    assert res_ecchi_safe.status_code == 200
    assert res_ecchi_safe.json()["data"]["results"] == []

def test_frontend_sfx_and_safe_mode_dom_and_js():
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'id="icon-shield-check"' in html
    assert 'id="pop-toggle-safemode"' in html
    assert 'id="pop-toggle-sfx"' in html
    assert 'id="drawer-toggle-safemode"' in html
    assert 'id="drawer-toggle-sfx"' in html

    api_js = (ROOT / "frontend" / "js" / "api.js").read_text(encoding="utf-8")
    assert "getSafeMode:" in api_js
    assert "setSafeMode:" in api_js
    assert "safe_mode=" in api_js

    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "TatapSfx" in app_js
    assert "TatapSafeMode" in app_js
    assert 'TatapSfx.play("tick")' in app_js
    assert 'TatapSfx.play("select")' in app_js
    assert 'TatapSfx.play("back")' in app_js
    assert 'TatapSfx.play("notify")' in app_js

    term_js = (ROOT / "frontend" / "js" / "term.js").read_text(encoding="utf-8")
    assert 'TatapSfx.play("tab")' in term_js
    assert 'case "sfx":' in term_js
    assert 'case "safe":' in term_js
