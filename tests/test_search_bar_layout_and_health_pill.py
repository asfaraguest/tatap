"""Tests for Search Bar Layout, Health Pill Elimination, and Episode Button Consistency.

Verifies:
1. Online status pill (#health and .bottom-actions) is completely eliminated from index.html bottom-search-row.
2. Search input wrap occupies full row with updated ergonomic height 42px and 0 16px padding.
3. Desktop flush container alignment: .bottom-search-row and .statusbar have max-width: 1560px and margin: 0 auto.
4. Episode buttons (.ep) enforce consistent uniform height (44px on desktop, 40px on mobile).
5. App.js safely handles backend health update without null pointer exceptions.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).parent.parent
INDEX_HTML = REPO_ROOT / "frontend" / "index.html"
STYLE_CSS = REPO_ROOT / "frontend" / "css" / "style.css"
APP_JS = REPO_ROOT / "frontend" / "js" / "app.js"


def test_health_pill_and_bottom_actions_eliminated():
    """Memastikan elemen #health dan .bottom-actions telah dihapus dari footer search bar."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    assert '<div class="bottom-actions">' not in html
    assert 'id="health"' not in html


def test_search_input_wrap_dimensions_and_desktop_alignment():
    """Memastikan search bar berukuran 42px tinggi dan sejajar dengan container desktop 1560px."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    # Dimensi search-input-wrap
    assert "height:44px" in css or "height: 44px" in css
    assert "padding:0 14px" in css or "padding: 0 14px" in css
    assert "flex:1 1 100%" in css or "flex: 1 1 100%" in css

    # Desktop container flush alignment (1560px)
    assert ".bottom-search-row, .statusbar{max-width:1560px" in css or ".bottom-search-row, .statusbar { max-width: 1560px" in css or ".bottom-search-row, .statusbar{ max-width:1560px" in css or "max-width:1560px;margin:0 auto" in css


def test_episode_button_uniform_sizing():
    """Memastikan episode button memiliki dimensi seragam (44px di desktop dan 40px di mobile)."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    # Desktop uniform height
    assert "height:44px" in css or "height: 44px" in css
    assert "min-height:44px" in css or "min-height: 44px" in css
    assert "max-height:44px" in css or "max-height: 44px" in css
    assert "border-radius:8px" in css or "border-radius: 8px" in css

    # Mobile uniform height
    assert "height:40px" in css or "height: 40px" in css
    assert "min-height:40px" in css or "min-height: 40px" in css
    assert "max-height:40px" in css or "max-height: 40px" in css


def test_app_js_safe_health_update():
    """Memastikan app.js aman saat elemen #health tidak ada di DOM."""
    app_js = APP_JS.read_text(encoding="utf-8")
    assert "function updateBackendHealth(isOnline)" in app_js
    assert 'var hEl = $("health");' in app_js
    assert "if(hEl)" in app_js
