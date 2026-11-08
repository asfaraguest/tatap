"""Test suite untuk pengaturan style subtitle Artplayer (Font, Background, Warna, Posisi, Ukuran) dan modal Subtitle Styler."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def test_subtitle_style_settings_in_app_js():
    """Memastikan app.js memiliki pengaturan style subtitle di menu settings Artplayer dan fungsi kustomisasinya."""
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    # 1. Pastikan item setting Artplayer terdefinisi lengkap
    assert 'name: "subtitle-styler-modal"' in app_js
    assert 'name: "subtitle-font"' in app_js
    assert 'name: "subtitle-size"' in app_js
    assert 'name: "subtitle-color"' in app_js
    assert 'name: "subtitle-bg"' in app_js
    assert 'name: "subtitle-pos"' in app_js

    # 2. Pastikan fungsi handler style tersedia
    assert "function syncSubStyle()" in app_js
    assert "function setSubFont(" in app_js
    assert "function setSubColor(" in app_js
    assert "function setSubBg(" in app_js
    assert "function setSubPos(" in app_js
    assert "function loadSubStylePrefs()" in app_js
    assert "function openSubStyleModal()" in app_js
    assert "function closeSubStyleModal()" in app_js
    assert "function updateSubStylePreview()" in app_js

    # 3. Pastikan FONT_MAP mencakup 6 jenis font preset
    assert "var FONT_MAP =" in app_js
    assert '"sans":' in app_js
    assert '"rounded":' in app_js
    assert '"tahoma":' in app_js
    assert '"serif":' in app_js
    assert '"mono":' in app_js
    assert '"impact":' in app_js

    # 4. Pastikan pilihan warna font mendukung putih, kuning emas, cyan cyber, hijau lembut, sakura pink
    assert "#ffffff" in app_js
    assert "#facc15" in app_js
    assert "#38bdf8" in app_js
    assert "#4ade80" in app_js
    assert "#f472b6" in app_js

    # 5. Pastikan pilihan background mendukung transparan, gelap pekat, tipis, frosted blur, tanpa kotak
    assert '"medium"' in app_js
    assert '"dark"' in app_js
    assert '"light"' in app_js
    assert '"frosted"' in app_js
    assert '"none"' in app_js

    # 6. Pastikan pilihan posisi mendukung low, normal, medium, high
    assert '"low"' in app_js
    assert '"normal"' in app_js
    assert '"medium"' in app_js
    assert '"high"' in app_js

    # 7. Pastikan drawCanvasSubtitles memanfaatkan setting style ini untuk True PiP termasuk font & frosted
    assert "cur.subFont" in app_js
    assert "cur.subColor" in app_js
    assert "cur.subBg" in app_js
    assert "cur.subPos" in app_js
    assert "cur.subSize" in app_js
    assert "FONT_MAP[cur.subFont" in app_js

    # 8. Pastikan buildSubtitleControl menyediakan trigger styler
    assert "sub-styler-trigger" in app_js
    assert "__open_styler__" in app_js


def test_subtitle_style_css_variables():
    """Memastikan CSS mendefinisikan variable --sub-font, --sub-color, --sub-bg, --sub-bottom, dan --sub-size."""
    style_css = (ROOT / "frontend" / "css" / "style.css").read_text(encoding="utf-8")

    assert "var(--sub-font" in style_css
    assert "var(--sub-bottom" in style_css
    assert "var(--sub-color" in style_css
    assert "var(--sub-bg" in style_css
    assert "var(--sub-size" in style_css

    # Pastikan class styling modal styler terdefinisi
    assert ".sub-style-sheet" in style_css
    assert ".sub-preview-box" in style_css
    assert ".sub-preview-text" in style_css
    assert ".sub-styler-opt" in style_css
    assert ".sub-frosted" in style_css


def test_subtitle_styler_modal_in_index_html():
    """Memastikan index.html memiliki modal Subtitle Styler dan tombol trigger popover & drawer."""
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert 'id="sub-style-modal"' in index_html
    assert 'id="sub-preview-box"' in index_html
    assert 'id="sub-preview-text"' in index_html
    assert 'id="pop-sub-style"' in index_html
    assert 'id="drawer-sub-style"' in index_html
    assert 'data-sub-font="sans"' in index_html
    assert 'data-sub-font="rounded"' in index_html
    assert 'data-sub-font="tahoma"' in index_html
    assert 'data-sub-bg="frosted"' in index_html


def test_subtitle_styler_in_term_js():
    """Memastikan term.js mendukung perintah terminal :substyle / :styler dan mendeteksi modal terbuka."""
    term_js = (ROOT / "frontend" / "js" / "term.js").read_text(encoding="utf-8")

    assert "sub-style-modal" in term_js
    assert ":substyle" in term_js
    assert ":styler" in term_js
    assert 'case "substyle":' in term_js

