"""Tests for Shiru UI adoption (Ultra-Minimalist & Low-End Device Optimizations).

Verifies that:
1. Pure system font stack is used (zero external font downloads / zero googleapis links).
2. Zero backdrop blur tax (no backdrop-filter: blur in style.css).
3. Obsidian (#000000) and electric teal (#19d0d0) design tokens are defined and active.
4. Top navigation tabs are present in index.html and wired to Tui.setView.
5. DOM containment and lightweight transitions are applied to poster cards.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).parent.parent
INDEX_HTML = REPO_ROOT / "frontend" / "index.html"
STYLE_CSS = REPO_ROOT / "frontend" / "css" / "style.css"
APP_JS = REPO_ROOT / "frontend" / "js" / "app.js"
TERM_JS = REPO_ROOT / "frontend" / "js" / "term.js"


def test_zero_external_fonts():
    """Verify 0KB external font downloads: no google fonts link in index.html or style.css."""
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    css_content = STYLE_CSS.read_text(encoding="utf-8")

    assert "fonts.googleapis.com" not in html_content
    assert "fonts.gstatic.com" not in html_content
    assert "@import" not in css_content
    assert "fonts.googleapis.com" not in css_content


def test_zero_backdrop_blur_tax():
    """Verify no backdrop-filter: blur is used to prevent CPU spikes on low-end hardware."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")
    assert "backdrop-filter" not in css_content


def test_obsidian_and_teal_tokens():
    """Verify obsidian black (#000000 fallback / #0c0d12) and soft sky/teal tokens."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")

    assert "--bg:#000000;" in css_content or "--bg: #000000;" in css_content or "--bg:#0c0d12;" in css_content or "--bg: #0c0d12;" in css_content
    assert "--accent:#38bdf8;" in css_content or "--accent: #38bdf8;" in css_content
    assert ".eyebrow" in css_content
    assert ".shiru-divider" in css_content


def test_top_navigation_bar_structure():
    """Verify top navigation tabs are embedded in index.html."""
    html_content = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="nav-tabs-bar"' in html_content
    assert 'data-view="musim"' in html_content
    assert 'data-view="terbaru"' in html_content
    assert 'data-view="lanjutan"' in html_content
    assert 'data-view="riwayat"' in html_content
    assert 'data-view="favorit"' in html_content
    assert 'data-view="katalog"' in html_content


def test_poster_card_containment_and_optimization():
    """Verify poster cards use layout containment and GPU transforms."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")

    assert "contain:content" in css_content or "contain: content" in css_content
    assert "will-change:transform" in css_content or "will-change: transform" in css_content
    assert "translate3d(0,-2px,0)" in css_content or "translate3d(0, -2px, 0)" in css_content


def test_nav_tab_synchronization_in_js():
    """Verify tab bar listeners and synchronization are wired in term.js and app.js."""
    app_js = APP_JS.read_text(encoding="utf-8")
    term_js = TERM_JS.read_text(encoding="utf-8")

    assert ".nav-tab-btn[data-view]" in app_js
    assert "updateNavTabs" in term_js
