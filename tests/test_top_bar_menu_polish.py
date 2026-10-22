"""
Test Suite: Top Bar Menu Polish & Graphic Design Consistency (Desktop & Web)
Verifies:
1. Brand Logo Mark SVG symbol (#icon-brand-mark) and interactive #head-brand element.
2. Mathematical 3-column CSS Grid architecture (1fr auto 1fr) for true optical centering of tabs.
3. Optical center alignment of .nav-tabs-bar (justify-self: center).
4. Search is strictly and exclusively located at the bottom bar (#cmd), not in the top bar.
5. Consistent design language between top bar and bottom bar (matching obsidian gradients, borders, shadows).
6. Interactive event listeners in JavaScript for brand home navigation.
7. Zero Backdrop Blur compliance for low-end device performance.
"""

from pathlib import Path
import re
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT_DIR / "frontend" / "index.html"
STYLE_CSS = ROOT_DIR / "frontend" / "css" / "style.css"
APP_JS = ROOT_DIR / "frontend" / "js" / "app.js"
TERM_JS = ROOT_DIR / "frontend" / "js" / "term.js"


def test_brand_logo_mark_svg_and_interactive_element():
    """Verify brand mark vector symbol and interactive #head-brand container."""
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    css_content = STYLE_CSS.read_text(encoding="utf-8")

    # SVG Symbol
    assert 'id="icon-brand-mark"' in html_content
    # Interactive head brand
    assert 'id="head-brand"' in html_content
    assert 'class="brand-logo-mark"' in html_content
    assert 'href="#icon-brand-mark"' in html_content
    assert 'class="brand-name"' in html_content
    assert 'class="brand-ver"' in html_content

    # CSS styling
    assert ".brand-logo-mark" in css_content
    assert ".head-brand" in css_content
    assert "cursor:pointer" in css_content or "cursor: pointer" in css_content


def test_three_column_grid_and_optical_centering():
    """Verify .tui-head uses a 3-column grid to mathematically center tabs."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")

    # 3-column grid structure
    assert "grid-template-columns:1fr auto 1fr" in css_content or "grid-template-columns: 1fr auto 1fr" in css_content
    # Center alignment for tabs
    assert "justify-self:center" in css_content or "justify-self: center" in css_content
    # 56px modular scale height
    assert "height:56px" in css_content or "height: 56px" in css_content


def test_search_exclusively_at_bottom_bar():
    """Verify search is exclusively at bottom bar, removed from top bar."""
    html_content = INDEX_HTML.read_text(encoding="utf-8")
    css_content = STYLE_CSS.read_text(encoding="utf-8")

    # Not in top bar
    assert 'id="btn-head-search"' not in html_content

    # In bottom bar
    assert 'class="bottom-bar"' in html_content
    assert 'id="cmd"' in html_content
    assert 'search-lead-icon' in html_content
    assert 'search-kbd-hint' in html_content


def test_design_language_consistency_top_and_bottom():
    """Verify top bar and bottom bar share unified obsidian styling, borders, and shadows."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")

    # Top bar gradient & shadow
    assert "linear-gradient(180deg,rgba(14,16,21,0.98)" in css_content or "linear-gradient(180deg, rgba(14, 16, 21, 0.98)" in css_content
    assert "0 4px 20px" in css_content

    # Bottom bar symmetrical complementary gradient & upward shadow
    assert "linear-gradient(0deg,rgba(14,16,21,0.98)" in css_content or "linear-gradient(0deg, rgba(14, 16, 21, 0.98)" in css_content
    assert "0 -4px 20px" in css_content

    # Matching surface backgrounds for tabs and search input
    assert "background:rgba(18,21,28,0.85)" in css_content or "background: rgba(18, 21, 28, 0.85)" in css_content
    assert "border-radius:10px" in css_content or "border-radius: 10px" in css_content or "border-radius:9px" in css_content


def test_javascript_event_listeners_wired():
    """Verify event handlers for head-brand in app.js and forward slash shortcut in term.js."""
    app_js = APP_JS.read_text(encoding="utf-8")
    term_js = TERM_JS.read_text(encoding="utf-8")

    # Brand click handler
    assert "head-brand" in app_js
    assert 'setView("musim")' in app_js or "setView('musim')" in app_js

    # Forward slash keyboard shortcut in term.js focuses bottom search prompt
    assert 'e.key==="/"' in term_js or 'e.key === "/"' in term_js


def test_zero_backdrop_blur_on_header_and_footer():
    """Verify neither header nor footer introduces backdrop-filter: blur."""
    css_content = STYLE_CSS.read_text(encoding="utf-8")
    header_start = css_content.find(".tui-head{")
    drawer_start = css_content.find("/* ---- DRAWER", header_start)
    bars_section = css_content[header_start:drawer_start]

    assert "backdrop-filter" not in bars_section
