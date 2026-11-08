"""Test suite untuk perbaikan sidebar UI, keselarasan warna tema, dan kehadiran icon SVG."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def test_sidebar_svg_icons_present_in_index_html():
    """Memastikan seluruh icon yang digunakan oleh sidebar terdefinisi di sprite SVG."""
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    # 1. Pastikan symbol-symbol yang sebelumnya hilang kini tersedia
    assert '<symbol id="icon-grid"' in index_html
    assert '<symbol id="icon-calendar"' in index_html
    assert '<symbol id="icon-zap"' in index_html

    # 2. Ekstrak seluruh ikon yang digunakan di app-sidebar
    sidebar_match = re.search(r'<aside class="app-sidebar".*?</aside>', index_html, re.DOTALL)
    assert sidebar_match, "app-sidebar tidak ditemukan di index.html"
    sidebar_html = sidebar_match.group(0)

    used_icons = re.findall(r'<use href="#([^"]+)"/>', sidebar_html)
    assert len(used_icons) >= 14, f"Ditemukan {len(used_icons)} icon di sidebar"

    # 3. Pastikan setiap icon yang dipakai memiliki <symbol id="..."> yang sesuai
    for icon_id in set(used_icons):
        assert f'<symbol id="{icon_id}"' in index_html, f"Symbol #{icon_id} tidak terdefinisi di index.html"


def test_sidebar_color_harmony_in_style_css():
    """Memastikan CSS sidebar menggunakan variabel warna terintegrasi dan styling selaras UI."""
    style_css = (ROOT / "frontend" / "css" / "style.css").read_text(encoding="utf-8")

    # Pastikan .app-sidebar menggunakan var(--bg-elevated) dan var(--border)
    sidebar_block = re.search(r'\.app-sidebar\s*\{([^}]+)\}', style_css)
    assert sidebar_block, ".app-sidebar CSS block tidak ditemukan"
    content = sidebar_block.group(1)

    assert "var(--bg-elevated)" in content
    assert "var(--border)" in content

    # Pastikan styling tema terang sidebar terdefinisi
    assert '[data-theme="light"] .app-sidebar' in style_css
    assert '[data-theme="light"] .sidebar-nav-item' in style_css

    # Pastikan hover dan active state icon terdefinisi
    assert ".sidebar-nav-item:hover .ui-icon" in style_css
    assert ".sidebar-nav-item.active .ui-icon" in style_css


def test_sidebar_theme_and_source_sync_in_app_js():
    """Memastikan app.js menyinkronkan tema dan label sumber video ke sidebar."""
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    assert "sidebar-theme-icon" in app_js
    assert "sidebar-theme-label" in app_js
    assert "sidebar-src-val" in app_js


def test_sidebar_performance_and_anti_lag_enforcement():
    """Memastikan struktur sidebar fluid, bersih, dan konsisten dengan SemVer."""
    style_css = (ROOT / "frontend" / "css" / "style.css").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    # 1. Pastikan sidebar menggunakan layout containment anti-lag dan dimensi presisi
    sidebar_block = re.search(r'\.app-sidebar\s*\{([^}]+)\}', style_css)
    assert sidebar_block, ".app-sidebar tidak ditemukan di style.css"
    assert "width: 220px" in sidebar_block.group(1)
    assert "contain: layout;" in sidebar_block.group(1)

    # 2. Pastikan kelas collapsed tersedia dengan ukuran kompak
    assert ".app-sidebar.collapsed" in style_css
    collapsed_block = re.search(r'\.app-sidebar\.collapsed\s*\{([^}]+)\}', style_css)
    assert collapsed_block
    assert "width: 60px" in collapsed_block.group(1)


def test_sidebar_cursor_focus_unzooms_anime_cards():
    """Memastikan bahwa saat kursor/fokus masuk ke sidebar, efek zoom pada kartu anime ditiadakan."""
    style_css = (ROOT / "frontend" / "css" / "style.css").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    term_js = (ROOT / "frontend" / "js" / "term.js").read_text(encoding="utf-8")

    # CSS meniadakan zoom dan reset transform saat sidebar di-hover atau difokuskan
    assert ".app-container:has(.app-sidebar:hover) .poster-card" in style_css
    assert "body.sidebar-hovered .poster-card" in style_css
    assert "transform: none !important;" in style_css

    # JS meng-handle mouseenter, mouseleave, focusin, dan pemanggilan blurCards
    assert 'sb.addEventListener("mouseenter"' in app_js
    assert 'document.body.classList.add("sidebar-hovered")' in app_js
    assert 'window.Tui.blurCards' in app_js
    assert 'function blurCards()' in term_js


    # 3. Pastikan toggle sidebar tersimpan ke localStorage dan terikat ke tombol
    assert "btn-toggle-sidebar" in app_js
    assert "tatap_sidebar_collapsed" in app_js
