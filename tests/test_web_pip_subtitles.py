"""Test suite untuk sinkronisasi WebVTT Subtitles pada mode Picture-in-Picture (PiP) dan perataan grid detail hero actions."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def test_web_pip_subtitles_in_app_js():
    """Memastikan app.js memiliki mekanisme Direct Native Video PiP hardware-accelerated dengan sinkronisasi WebVTT Subtitles."""
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    # 1. Pastikan Direct Native Picture-in-Picture diimplementasikan tanpa overhead canvas
    assert "async function toggleSmartPip()" in app_js
    assert "sourceVideo.requestPictureInPicture()" in app_js
    assert "syncNativeTextTrack" in app_js

    # 2. Pastikan generateVttWithOffset memformat nomor urut cue
    assert "function generateVttWithOffset(" in app_js
    assert "(i + 1).toString()" in app_js

    # 3. Pastikan getActiveVideos mengumpulkan window.art.video dan fallback vid
    assert "function getActiveVideos()" in app_js
    assert "window.art.video" in app_js

    # 4. Pastikan kind captions dan VTTCue digunakan
    assert 'trackEl.kind = "captions"' in app_js
    assert "VTTCue" in app_js

    # 5. Pastikan shortcut i dan event listener PiP terpasang
    assert 'e.key==="i"||e.key==="I"' in app_js
    assert "toggleSmartPip()" in app_js
    assert 'art.on("pip"' in app_js
    assert "pip-focus-overlay" in app_js
    assert "pip-focus-restore-btn" in app_js

    # 6. Pastikan Document PiP dan Direct Native Video PiP diprioritaskan
    pip_fn_start = app_js.find("async function toggleSmartPip()")
    pip_fn_end = app_js.find("function syncFullscreenSubtitles()")
    assert pip_fn_start > 0 and pip_fn_end > pip_fn_start
    pip_fn = app_js[pip_fn_start:pip_fn_end]
    doc_pip_pos = pip_fn.find("window.documentPictureInPicture")
    direct_req_pos = pip_fn.find("sourceVideo.requestPictureInPicture()")
    assert doc_pip_pos > 0, "Document Picture-in-Picture API must be present"
    assert direct_req_pos > 0, "Direct sourceVideo.requestPictureInPicture must be present"
    assert doc_pip_pos < direct_req_pos, "Doc PiP -> Direct PiP hierarchy must be maintained"


def test_player_loading_animation_hides_on_artplayer_ready():
    """Memastikan animasi loading aktif saat inisiasi dan langsung hilang begitu Artplayer muncul/siap."""
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    style_css = (ROOT / "frontend" / "css" / "style.css").read_text(encoding="utf-8")

    # 1. Pastikan CSS spinner berada di top layer z-index 100 dengan efek glow
    assert "z-index: 100 !important" in style_css or "z-index:100!important" in style_css.replace(" ", "")
    assert ".ring{" in style_css.replace(" ", "") or ".ring {" in style_css
    assert "animation:spin" in style_css.replace(" ", "")

    # 2. Pastikan animasi loading hilang begitu Artplayer muncul / siap
    assert 'art.on("ready", hideSpinner)' in app_js
    assert 'hideSpinner();' in app_js
    assert 'art.once("video:canplay"' in app_js



def test_webview2_hardware_acceleration_flags():
    """Memastikan launcher Windows Go menyetel argumen browser WebView2 hardware accelerated dan DocumentPictureInPictureAPI."""
    main_go = (ROOT / "launcher" / "main.go").read_text(encoding="utf-8")
    assert "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS" in main_go
    assert "--enable-gpu-rasterization" in main_go
    assert "--enable-zero-copy" in main_go
    assert "--enable-features=DocumentPictureInPictureAPI" in main_go


def test_web_pip_subtitles_css_rule():
    """Memastikan CSS mendefinisikan aturan visual ::cue saat jendela PiP aktif serta efek blur panggung utama."""
    style_css = (ROOT / "frontend" / "css" / "style.css").read_text(encoding="utf-8")

    # Pastikan selector PiP ::cue ada dan visible
    assert "video::cue" in style_css
    assert "visibility: visible !important;" in style_css
    assert "opacity: 1 !important;" in style_css
    assert "rgba(0, 0, 0, 0.78)" in style_css

    # Pastikan efek blur & focus overlay di window utama saat PiP aktif
    assert "body.is-pip #artplayer-container" in style_css
    assert "blur(18px)" in style_css
    assert ".pip-focus-overlay" in style_css


def test_pip_focus_overlay_in_index_html():
    """Memastikan elemen pip-focus-overlay terpasang pada index.html."""
    index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert 'id="pip-focus-overlay"' in index_html
    assert 'id="pip-focus-restore-btn"' in index_html
    assert "Memutar di Picture-in-Picture" in index_html


def test_detail_hero_actions_three_column_grid():
    """Memastikan wadah detail-hero-actions menggunakan tata letak grid 3 kolom yang presisi."""
    style_css = (ROOT / "frontend" / "css" / "style.css").read_text(encoding="utf-8")

    match = re.search(r'\.detail-hero-actions\s*\{([^}]+)\}', style_css)
    assert match, "Rule .detail-hero-actions tidak ditemukan di style.css"
    content = match.group(1)

    assert "display:grid" in content.replace(" ", "") or "display: flex" in content
    assert "grid-template-columns:1.35fr 1fr 1fr" in content.replace(" ", "") or "grid-template-columns" in content
