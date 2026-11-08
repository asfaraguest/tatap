import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def test_spotlight_html_accessibility_and_attributes():
    """Memastikan struktur modal spotlight memiliki role accessibility dan tabindex yang valid."""
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'id="spotlight-modal"' in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'id="spotlight-esc-btn"' in html
    assert 'tabindex="0"' in html
    assert 'role="button"' in html


def test_spotlight_css_body_lock_and_focus_visible():
    """Memastikan CSS mengunci scroll body saat spotlight aktif dan menyediakan visual focus-visible."""
    css = (ROOT / "frontend" / "css" / "style.css").read_text(encoding="utf-8")
    assert "body.spotlight-open" in css
    assert "overflow: hidden !important" in css
    assert ".spotlight-esc-btn:focus-visible" in css
    assert ".spotlight-tag:focus-visible" in css


def test_spotlight_focus_trap_in_app_js():
    """Memastikan fungsi getSpotlightFocusableElements, trapSpotlightFocus, dan penguncian kursor di app.js."""
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    assert "function getSpotlightFocusableElements()" in app_js
    assert "function trapSpotlightFocus(shiftKey)" in app_js
    assert "document.body.classList.add(\"spotlight-open\")" in app_js
    assert "document.body.classList.remove(\"spotlight-open\")" in app_js
    assert "_lastActiveBeforeSpotlight" in app_js
    assert 'document.addEventListener("focusin"' in app_js
    assert "trapSpotlightFocus:trapSpotlightFocus" in app_js


def test_spotlight_key_isolation_in_term_js():
    """Memastikan term.js tidak membocorkan kursor ke katalog atau background saat spotlight aktif."""
    term_js = (ROOT / "frontend" / "js" / "term.js").read_text(encoding="utf-8")
    assert "isSpotlight && e.key===\"Tab\"" in term_js
    assert "App.trapSpotlightFocus(e.shiftKey)" in term_js
    assert "isSpotlight && (e.key===\"ArrowDown\" || e.key===\"ArrowUp\")" in term_js
    assert "cmdHistory" in term_js
    assert "App.closeSpotlight()" in term_js
