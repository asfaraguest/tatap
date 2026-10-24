"""
Test suite untuk memverifikasi keyboard navigation pada antarmuka Desktop dan Web Tatap.
Memastikan:
1. `renderSel()` dan `moveSel()` mendukung elemen grid `.poster-card` dan list `.trow`.
2. Perhitungan kolom grid responsif `getGridCols()`.
3. Navigasi panah 4 arah (ArrowLeft, ArrowRight, ArrowDown, ArrowUp) pada term.js.
4. Tombol Enter dan Space membuka anime yang sedang terpilih (`openSelected()`).
5. Transisi fokus dari search bar input (`#cmd`) ke hasil saat menekan ArrowDown.
6. Navigasi episode keyboard di modal detail anime (`handleTitleModalKey`).
7. Pengaturan volume keyboard di video player (`ArrowUp` / `ArrowDown`).
8. Dukungan styling focus-visible pada CSS untuk aksesibilitas keyboard.
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
STYLE_CSS = FRONTEND_DIR / "css" / "style.css"
TERM_JS = FRONTEND_DIR / "js" / "term.js"
APP_JS = FRONTEND_DIR / "js" / "app.js"
INDEX_HTML = FRONTEND_DIR / "index.html"


def test_term_js_rendersel_supports_poster_cards_and_trows():
    """Memastikan renderSel di term.js memilih kedua jenis item: .poster-card dan .trow."""
    content = TERM_JS.read_text(encoding="utf-8")
    assert 'box.querySelectorAll(".poster-card, .trow")' in content, (
        "renderSel() wajib mengueri .poster-card dan .trow agar navigasi keyboard bekerja pada tampilan katalog, musim, riwayat, dsb."
    )
    assert 'scrollIntoView' in content
    assert 'selEl.focus' in content or 'all[S.sel].focus' in content


def test_term_js_movesel_and_grid_cols():
    """Memastikan getGridCols dan moveSel mendukung navigasi grid 2D."""
    content = TERM_JS.read_text(encoding="utf-8")
    assert "function getGridCols()" in content
    assert 'cards[c].offsetTop > firstTop' in content
    assert "next = (d > 0) ? 0 : count - 1" in content, (
        "Saat S.sel < 0, moveSel harus memilih kartu pertama (0) jika bergerak maju atau kartu terakhir jika mundur."
    )


def test_term_js_onkey_four_way_arrow_and_enter():
    """Memastikan onKey mendukung navigasi panah 4 arah, Enter membuka selected, dan Space."""
    content = TERM_JS.read_text(encoding="utf-8")
    assert 'if(e.key==="ArrowRight")' in content
    assert 'if(e.key==="ArrowLeft")' in content
    assert 'if(e.key==="ArrowDown")' in content
    assert 'if(e.key==="ArrowUp")' in content
    # Enter membuka selected jika ada yang terpilih
    assert 'if(S.sel>=0){\n        openSelected();' in content or 'if(S.sel>=0){' in content
    assert "openSelected();" in content
    # Shift-Tab dan Tab cycleView
    assert "cycleView(e.shiftKey ? -1 : 1)" in content


def test_term_js_search_input_arrow_down_transitions_to_results():
    """Memastikan saat pengguna mengetik di search bar, ArrowDown memindahkan fokus ke hasil."""
    content = TERM_JS.read_text(encoding="utf-8")
    # Cek di handler inp.addEventListener("keydown"...)
    assert 'else if(e.key==="ArrowDown"){\n        if(S.items.length){\n          e.preventDefault();\n          inp.blur();\n          S.promptFoc=false;\n          moveSel(1);' in content


def test_app_js_title_modal_keyboard_navigation():
    """Memastikan app.js menangani navigasi keyboard di modal detail anime."""
    content = APP_JS.read_text(encoding="utf-8")
    assert "function getEpGridCols()" in content
    assert "function handleTitleModalKey(e)" in content
    assert "handleTitleModalKey(e);" in content
    assert 'box.querySelector(".ep.last-watch") || box.querySelector(".ep")' in content
    assert 'activeBtn.focus({preventScroll: true})' in content


def test_app_js_player_volume_keyboard_controls():
    """Memastikan onKeyPlayer di app.js mendukung ArrowUp dan ArrowDown untuk mengatur volume video."""
    content = APP_JS.read_text(encoding="utf-8")
    assert 'else if(e.key==="ArrowUp"){\n    e.preventDefault();\n    v.volume=Math.min(1,' in content
    assert 'else if(e.key==="ArrowDown"){\n    e.preventDefault();\n    v.volume=Math.max(0,' in content


def test_app_js_player_space_and_hotkey_handling():
    """Memastikan onKeyPlayer di app.js menangani tombol Space, Fullscreen, Mute, dan hotkey lainnya secara tangguh."""
    content = APP_JS.read_text(encoding="utf-8")
    
    # 1. Pastikan SELECT dan BUTTON tidak dihitung sebagai text editing yang memblokir shortcut
    assert 'isTextEditing' in content
    assert '["button","checkbox","color","file","hidden","image","radio","range","reset","submit"]' in content
    assert 't==="SELECT"' not in content[content.find("function onKeyPlayer"):content.find("function onKeyPlayer") + 800]
    
    # 2. Pastikan varian tombol spasi didukung penuh (Spacebar, code Space, keyCode 32)
    assert 'var isSpace = e.key===" " || e.key==="Spacebar" || e.code==="Space" || e.keyCode===32;' in content
    
    # 3. Pastikan penekanan Space atau Enter melakukan toggle play/pause dan un-focus elemen aktif
    assert 'if(v.paused) v.play(); else v.pause();' in content
    assert 'document.activeElement.blur()' in content
    
    # 4. Pastikan fullscreen dan hotkey player lainnya didukung
    assert 'else if(e.key==="f"||e.key==="F")' in content
    assert 'toggleFullscreen();' in content
    assert 'else if(e.key==="m"||e.key==="M")' in content
    assert 'else if(e.key==="s"||e.key==="S")' in content
    assert 'else if(e.key==="n"||e.key==="N")' in content
    assert 'else if(e.key==="p"||e.key==="P")' in content
    assert 'else if(e.key===","||e.key==="<")' in content
    assert 'else if(e.key==="."||e.key===">")' in content
    assert 'else if(e.key==="["||e.key==="{")' in content
    assert 'else if(e.key==="]"||e.key==="}")' in content
    
    # 5. Pastikan openPlayer pada Desktop tidak memaksakan fokus ke pm-speed-select
    assert 'if(TvNavigationManager.isTvMode())' in content
    assert 'TvNavigationManager.showPlayerControls($("pm-speed-select") || $("pm-close"));' in content


def test_style_css_focus_visible_styling():
    """Memastikan style.css menyediakan outline focus-visible untuk kartu anime dan tombol episode."""
    content = STYLE_CSS.read_text(encoding="utf-8")
    assert ".poster-card:focus-visible" in content
    assert ".ep:focus-visible" in content
    assert ".ep.last-watch:focus-visible" in content


def test_index_html_statusbar_key_hints():
    """Memastikan statusbar menampilkan indikator panah 4-arah ↑↓←→."""
    content = INDEX_HTML.read_text(encoding="utf-8")
    assert "<b>↑↓←→</b> pilih" in content
