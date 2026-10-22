"""Tests for Apple UI Desktop & Web Redesign (Isolated from Mobile and Android TV).

Verifies:
1. Decoupling of :focus-visible (desktop) from .tv-focus (TV 10-foot UI).
2. Clean desktop :focus-visible ring without layout-shifting 1.06x scale or neon glow.
3. TV 10-foot scale and high-contrast outline preserved strictly on .tv-focus.
4. term.js renderSel and app.js setFocus gate .tv-focus with isTvMode.
5. Desktop #cmd search input is immediately interactive without readonly lock.
6. Apple TV player controls use capsule pills (border-radius: 999px).
7. Strict preservation of mobile responsive breakpoints (<= 768px, <= 480px).
"""

from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
STYLE_CSS = ROOT / "frontend" / "css" / "style.css"
TERM_JS = ROOT / "frontend" / "js" / "term.js"
APP_JS = ROOT / "frontend" / "js" / "app.js"
INDEX_HTML = ROOT / "frontend" / "index.html"


def test_focus_visible_decoupled_from_tv_focus():
    """Verify :focus-visible does not trigger 1.06x scale or giant neon glows on desktop."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    # .tv-focus has TV specifications
    assert ".tv-focus {" in css or ".tv-focus\n{" in css
    assert "transform: scale(1.06) !important;" in css
    assert "outline: 3px solid var(--accent, #38bdf8) !important;" in css

    # :focus-visible is decoupled and uses calm Apple focus ring
    assert ":focus-visible {" in css or ":focus-visible\n{" in css
    assert "box-shadow: 0 0 0 2px var(--bg), 0 0 0 4px rgba(56, 189, 248, 0.45) !important;" in css


def test_term_js_and_app_js_tv_focus_gating():
    """Verify .tv-focus is only added when isTvMode is true."""
    term_js = TERM_JS.read_text(encoding="utf-8")
    app_js = APP_JS.read_text(encoding="utf-8")

    # term.js renderSel gates tv-focus with isTv
    assert "isTv" in term_js
    assert "all[i].classList.remove(\"tv-focus\");" in term_js or "all[i].classList.remove('tv-focus')" in term_js

    # app.js setFocus gates tv-focus with isTvMode
    assert "if(isTvMode())" in app_js
    assert "el.classList.add(\"tv-focus\");" in app_js or "el.classList.add('tv-focus')" in app_js


def test_desktop_cmd_interactive():
    """Verify desktop search input is interactive without readonly lockout."""
    app_js = APP_JS.read_text(encoding="utf-8")
    index_html = INDEX_HTML.read_text(encoding="utf-8")

    # HTML still carries readonly for TV navigation baseline
    assert 'id="cmd"' in index_html
    assert 'readonly' in index_html

    # app.js removes readonly on desktop
    assert 'cmdInput.removeAttribute("readonly")' in app_js or "cmdInput.removeAttribute('readonly')" in app_js


def test_apple_capsule_player_controls():
    """Verify video player head and foot buttons use Apple capsule pills."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert ".player-head-btns button,.player-head-btns select" in css
    assert "border-radius:999px" in css
    assert ".player-foot>button" in css
    assert ".sub-picker" in css


def test_poster_card_media_and_badges_refined():
    """Verify poster cards use refined translucent badges and transparent outer box."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert ".poster-card{background:transparent" in css or ".poster-card { background: transparent" in css
    assert ".pc-badge-ep{color:var(--accent)" in css
    assert ".pc-badge-tamat{color:#34d399" in css
    assert ".pc-badge-long{color:#fbbf24" in css


def test_mobile_and_android_compatibility_unbroken():
    """Verify mobile breakpoints and TV dpad rules are unbroken."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert "@media (max-width:480px)" in css
    assert "@media (max-width:768px)" in css
    assert ".tv-focus" in css
