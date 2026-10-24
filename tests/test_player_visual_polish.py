from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
STYLE_CSS = ROOT / "frontend" / "css" / "style.css"
PLAYER_XML = ROOT / "android" / "app" / "src" / "main" / "res" / "layout" / "activity_player.xml"
PLAYER_JAVA = ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app" / "PlayerActivity.java"
TV_FOCUS_JAVA = ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app" / "TvFocusHelper.java"
DRAWABLE_DIR = ROOT / "android" / "app" / "src" / "main" / "res" / "drawable"


def test_web_desktop_player_cinema_polish():
    """Pastikan CSS video player Web & Desktop memiliki glassmorphic bar, segmented sub-picker, dan glowing OSD."""
    css = STYLE_CSS.read_text(encoding="utf-8")
    assert ".player-head{" in css
    assert "linear-gradient(180deg,rgba(255,255,255,0.06)" in css
    assert ".sub-size{display:inline-flex;gap:2px;background:rgba(255,255,255,0.05)" in css
    assert ".gesture-osd{" in css
    assert "box-shadow:0 0 8px rgba(56,189,248,0.55)" in css
    assert ".ambient-stage{position:relative;border-radius:10px;border:1px solid rgba(255,255,255,0.08)" in css


def test_android_player_drawables_valid_xml():
    """Pastikan drawable baru untuk ExoPlayer Android TV & Mobile valid dan terstruktur dengan benar."""
    shape_drawables = [
        "bg_player_top_scrim.xml",
        "bg_player_bottom_scrim.xml",
        "bg_player_hud_pill.xml",
        "bg_ripple_seek_left.xml",
        "bg_ripple_seek_right.xml",
    ]
    for name in shape_drawables:
        path = DRAWABLE_DIR / name
        assert path.exists(), f"Drawable {name} tidak ditemukan"
        tree = ET.parse(path)
        assert tree.getroot().tag == "shape"

    selector_drawables = [
        "bg_exo_icon_btn.xml",
        "bg_exo_play_center.xml",
    ]
    for name in selector_drawables:
        path = DRAWABLE_DIR / name
        assert path.exists(), f"Drawable {name} tidak ditemukan"
        tree = ET.parse(path)
        assert tree.getroot().tag == "selector"


def test_android_exoplayer_layout_and_timebar_polish():
    """Pastikan activity_player.xml dan PlayerActivity.java menyatukan fungsi top pill ke ExoPlayer bottom bar & mendukung D-Pad TV."""
    xml_text = PLAYER_XML.read_text(encoding="utf-8")
    assert '@drawable/bg_player_top_scrim' in xml_text
    assert '@drawable/bg_player_hud_pill' in xml_text
    assert '@drawable/bg_ripple_seek_left' in xml_text
    assert '@drawable/bg_ripple_seek_right' in xml_text
    assert '@+id/layout_legacy_top_pills' in xml_text
    assert '@drawable/bg_exo_icon_btn' in xml_text
    assert 'app:show_subtitle_button="true"' in xml_text
    assert 'app:show_vr_button="true"' in xml_text

    java_text = PLAYER_JAVA.read_text(encoding="utf-8")
    assert "DefaultTimeBar" in java_text
    assert "dtb.setPlayedColor(0xFF38BDF8)" in java_text
    assert "dtb.setScrubberColor(0xFF38BDF8)" in java_text
    assert "R.drawable.bg_player_bottom_scrim" in java_text
    assert "R.drawable.bg_exo_play_center" in java_text
    assert "R.drawable.bg_exo_icon_btn" in java_text
    assert "setupBottomBarFocusChain()" in java_text
    assert "navigateBottomBarHorizontal(" in java_text
    assert "Mode Picture-in-Picture (PiP)" in java_text
    assert "Sinkronisasi Waktu Subtitle (Offset:" in java_text
    assert "enforceExoCustomButtons()" in java_text
    assert "playerView.setShowSubtitleButton(true)" in java_text
    assert "playerView.setShowVrButton(!TvFocusHelper.isTv(this) && isPipSupported())" in java_text
    assert "LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS" in java_text
    assert "window.setDecorFitsSystemWindows(false)" in java_text
    assert "ScaleGestureDetector" in java_text

    tv_focus = TV_FOCUS_JAVA.read_text(encoding="utf-8")
    assert "btn.setBackgroundTintList" in tv_focus
    assert "R.drawable.bg_exo_play_center" in tv_focus
    assert "R.drawable.bg_exo_icon_btn" in tv_focus
