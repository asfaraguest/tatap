"""
Test suite for Main Page Mouse and Keyboard Interaction Polish:
- #search-sec scroll isolation and styling
- Keyboard :focus-visible rules for sidebar, statusbar, chips
- Statusbar hint accessibility (role="button", tabindex, click/keydown handlers)
- Enter & Space hijack prevention for focused interactive targets
- Main page number shortcuts (1-6) and Home/End/PageUp/PageDown grid acceleration
- Mouse hover selection sync and click debounce
- TV mode isolation on desktop
- Sidebar arrow navigation and Escape/Tab traps in modals
- Tui export parity (pageNext, pagePrev, cycleView)
"""

import os
import re
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_search_sec_scroll_container_styling():
    css_path = os.path.join(REPO_ROOT, "frontend", "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Must contain #search-sec with proper overflow-y and flex bounds
    match = re.search(r"#search-sec\s*\{([^}]+)\}", content)
    assert match, "#search-sec rule missing in style.css"
    sec_body = match.group(1)
    assert "overflow-y: auto" in sec_body
    assert "min-height: 0" in sec_body
    assert "flex: 1 1 auto" in sec_body


def test_focus_visible_styling_for_keyboard_nav():
    css_path = os.path.join(REPO_ROOT, "frontend", "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert ".sidebar-nav-item:focus-visible" in content
    assert ".sb-shortcut-btn:focus-visible" in content
    assert ".sb-view-btn:focus-visible" in content
    assert ".cf-chip:focus-visible" in content


def test_statusbar_accessibility_attributes_in_html():
    html_path = os.path.join(REPO_ROOT, "frontend", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert 'id="sb-hint-pager"' in content
    assert 'id="sb-view"' in content
    assert 'class="sb-view-btn"' in content
    # Check tabindex="0" on interactive statusbar elements
    assert 'id="sb-hint-pager" class="sb-shortcut-btn" style="cursor:pointer;" tabindex="0" role="button"' in content or (
        'id="sb-hint-pager"' in content and 'tabindex="0"' in content and 'role="button"' in content
    )


def test_term_enter_space_hijack_prevention():
    term_path = os.path.join(REPO_ROOT, "frontend", "js", "term.js")
    with open(term_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "isInteractiveTarget" in content
    # Ensures Enter and Space check isInteractiveTarget before openSelected()
    assert 'if(e.key==="Enter")' in content
    assert "if(isInteractiveTarget && !isCatalogCard)" in content
    assert 'if(e.key===" ")' in content


def test_term_grid_shortcuts_and_number_keys():
    term_path = os.path.join(REPO_ROOT, "frontend", "js", "term.js")
    with open(term_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Number keys 1-6 view switching
    assert 'e.key >= "1" && e.key <= "6"' in content
    assert '"1":"katalog"' in content
    assert '"6":"favorit"' in content

    # Home, End, PageUp, PageDown
    assert 'e.key==="Home"' in content
    assert 'e.key==="End"' in content
    assert 'e.key==="PageDown"' in content
    assert 'e.key==="PageUp"' in content

    # ArrowLeft to sidebar
    assert 'e.key==="ArrowLeft"' in content
    assert "sidebar-nav-item" in content


def test_term_mouse_selection_sync_and_debounce():
    term_path = os.path.join(REPO_ROOT, "frontend", "js", "term.js")
    with open(term_path, "r", encoding="utf-8") as f:
        content = f.read()

    # mouseenter listener on card
    assert "mouseenter" in content
    # Debounce guard on card click
    assert "_lastCardClick" in content


def test_desktop_tv_mode_isolation():
    term_path = os.path.join(REPO_ROOT, "frontend", "js", "term.js")
    with open(term_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ensures TvNavigationManager calls check isTvMode
    assert "TvNavigationManager.isTvMode" in content


def test_sidebar_and_statusbar_interactivity_in_app_js():
    app_path = os.path.join(REPO_ROOT, "frontend", "js", "app.js")
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Sidebar internal ArrowDown / ArrowUp / ArrowRight
    assert 'sb.addEventListener("keydown"' in content
    assert 'e.key === "ArrowDown"' in content
    assert 'e.key === "ArrowRight"' in content
    assert "window.Tui.moveSel(0)" in content

    # Statusbar Pager and View buttons
    assert "sbHintPager" in content
    assert "sbView" in content
    assert "window.Tui.pageNext" in content
    assert "window.Tui.cycleView" in content


def test_modals_focus_trap_and_escape():
    term_path = os.path.join(REPO_ROOT, "frontend", "js", "term.js")
    with open(term_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Genre modal Tab trap and Escape
    assert "genreModalEl.addEventListener(\"keydown\"" in content
    assert "closeGenreModal" in content

    # Catalog filter modal Tab trap and Escape
    assert "cfModal.addEventListener(\"keydown\"" in content
    assert "closeCatalogFilterModal" in content


def test_tui_exports_parity():
    term_path = os.path.join(REPO_ROOT, "frontend", "js", "term.js")
    with open(term_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Export object must include pageNext, pagePrev, cycleView
    assert "pageNext:pageNext" in content
    assert "pagePrev:pagePrev" in content
    assert "cycleView:cycleView" in content
