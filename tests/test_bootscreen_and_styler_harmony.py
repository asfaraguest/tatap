import os
import sys
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from main import app

def test_bootscreen_html_exists_and_valid():
    bootscreen_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "bootscreen.html")
    assert os.path.isfile(bootscreen_path), "frontend/bootscreen.html must exist"
    
    with open(bootscreen_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "<!DOCTYPE html>" in content
    assert "Tatap Anime" in content
    assert "http://127.0.0.1:8767/api/ping" in content or "targetUrl + \"/api/ping\"" in content
    assert "window.location.replace" in content
    assert "progress-bar" in content
    assert "status-text" in content

def test_cors_middleware_enabled_and_ping_has_cors():
    client = TestClient(app)
    # Simulate a request from a file:// or other origin
    response = client.get("/api/ping", headers={"Origin": "null"})
    assert response.status_code == 200
    assert response.json() == {"success": True, "data": {"status": "running"}}
    # Check CORS header
    assert response.headers.get("access-control-allow-origin") == "*"

def test_apprun_has_bootscreen_support():
    apprun_path = os.path.join(os.path.dirname(__file__), "..", "linux", "AppRun")
    with open(apprun_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "bootscreen.html" in content
    assert 'APP_URL="file://${HERE}/frontend/bootscreen.html"' in content

def test_launcher_main_go_has_bootscreen_support():
    launcher_path = os.path.join(os.path.dirname(__file__), "..", "launcher", "main.go")
    with open(launcher_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "bootscreen.html" in content
    assert "runWebView(startURL" in content or "runWebView(startURL, dataPath)" in content

def test_subtitle_styler_buttons_in_index_html():
    index_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Must have reset, cancel, and apply buttons
    assert 'id="btn-sub-reset-style"' in content
    assert 'id="btn-sub-cancel-style"' in content
    assert 'id="btn-sub-apply-style"' in content
    assert "sub-reset-btn" in content
    assert "sub-cancel-btn" in content
    assert "sub-save-btn" in content
    assert "#icon-update" in content
    assert "#icon-check" in content

def test_css_z_index_and_button_harmony():
    css_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Both modals must be top z-index (2000000)
    assert "#sub-style-modal.overlay" in content
    assert "#ai-settings-modal.overlay" in content
    assert "2000000 !important" in content
    
    # Shared button harmony in sub-style-foot
    assert ".sub-style-foot .btn-primary" in content
    assert ".sub-style-foot .btn-secondary" in content
    assert ".sub-style-foot .btn-danger" in content

def test_app_js_styler_cancel_and_fullscreen():
    js_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "js", "app.js")
    with open(js_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "function cancelSubStyleModal()" in content
    assert "_subStyleSnapshot" in content
    assert "btn-sub-cancel-style" in content
    assert "attachModalToActiveLayer" in content
    assert "detachModalFromActiveLayer" in content
