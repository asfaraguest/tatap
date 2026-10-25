"""
tests/test_android_tv_perf_and_typography.py - Test suite to prevent regressions
on Android TV low-end performance optimizations, D-Pad player navigation, and semantic typography.
"""

import os
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res")
JAVA_DIR = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java")
PYTHON_DIR = os.path.join(ROOT_DIR, "android", "app", "src", "main", "python")


def test_python_server_launcher_no_gc_thrashing():
    """Memastikan gc.set_threshold(100, 5, 5) tidak ada di server_launcher.py."""
    launcher_path = os.path.join(PYTHON_DIR, "server_launcher.py")
    assert os.path.exists(launcher_path), f"File {launcher_path} tidak ditemukan"
    with open(launcher_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "gc.set_threshold(100" not in content, "gc.set_threshold(100, 5, 5) dilarang karena memicu CPU thrashing di TV Stick!"


def test_imageloader_background_priority_and_tv_direct_bitmap():
    """Memastikan ImageLoader menggunakan THREAD_PRIORITY_BACKGROUND dan direct bitmap di TV."""
    loader_path = os.path.join(JAVA_DIR, "id", "tatap", "app", "ImageLoader.java")
    with open(loader_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "THREAD_PRIORITY_BACKGROUND" in content, "ImageLoader wajib mengatur THREAD_PRIORITY_BACKGROUND agar tidak mengganggu UI thread"
    assert "if (isTv)" in content, "ImageLoader wajib membedakan TV untuk menghindari alpha animation overhead"


def test_tv_focus_helper_zero_layout_pass():
    """Memastikan TvFocusHelper tidak mengubah strokeWidth secara dinamis pada MaterialCardView."""
    helper_path = os.path.join(JAVA_DIR, "id", "tatap", "app", "TvFocusHelper.java")
    with open(helper_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "card.setStrokeWidth" not in content, "card.setStrokeWidth dilarang di TvFocusHelper karena memicu requestLayout() & outline thrashing"
    assert "withLayer()" in content, "v.animate() wajib menggunakan withLayer() untuk hardware layer rendering di TV"


def test_main_activity_tv_cache_and_no_layout_anim():
    r"""Memastikan MainActivity mematikan layout animation di TV dan mengatur cache $\ge 10$."""
    main_path = os.path.join(JAVA_DIR, "id", "tatap", "app", "MainActivity.java")
    with open(main_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "rvGrid.setLayoutAnimation(null)" in content, "MainActivity wajib mematikan layoutAnimation di Android TV"
    assert "setItemViewCacheSize(10)" in content, "MainActivity wajib menyediakan view cache 10 item di Android TV"
    assert "!TvFocusHelper.isTv(MainActivity.this)" in content, "scheduleLayoutAnimation wajib diskip di Android TV"


def test_player_dpad_navigation_on_paused_tv():
    """Memastikan PlayerActivity memiliki navigasi D-pad Kiri/Kanan/Atas/Bawah saat video di-pause di TV."""
    player_path = os.path.join(JAVA_DIR, "id", "tatap", "app", "PlayerActivity.java")
    with open(player_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "btnExoNext" in content
    assert "btnExoPrev" in content
    assert "btnSkipOpEd" in content
    # Verifikasi logika khusus DPAD LEFT, RIGHT, UP, DOWN saat paused di TV
    assert "isTvLeft && !isPlayingLeft" in content
    assert "isTvRight && !isPlayingRight" in content
    assert "btnSubSelector.requestFocus()" in content


def test_player_tv_seek_and_timebar_navigation():
    """Memastikan fallback ID rewind/ffwd dan konfigurasi D-Pad TimeBar untuk Android TV."""
    player_path = os.path.join(JAVA_DIR, "id", "tatap", "app", "PlayerActivity.java")
    with open(player_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Verifikasi dual ID fallback untuk rewind dan fast forward
    assert "androidx.media3.ui.R.id.exo_rew_with_amount" in content
    assert "androidx.media3.ui.R.id.exo_ffwd_with_amount" in content
    # Verifikasi increment D-Pad TimeBar murni 10 detik tanpa override proporsional (keyCountIncrement)
    assert "dtb.setKeyTimeIncrement(10000)" in content
    assert "dtb.setKeyCountIncrement" not in content
    # Verifikasi pengecualian DPAD_LEFT/RIGHT agar DefaultTimeBar.onKeyDown bisa mengeksekusi scrub
    assert "isTimeBarFocusedLeft" in content
    assert "isTimeBarFocusedRight" in content
    # Verifikasi D-Pad UP dan DOWN melewati timeBar
    assert "timeBarUp.requestFocus()" in content
    assert "timeBarDown.requestFocus()" in content


def test_semantic_typography_dimens():
    """Memastikan file values/dimens.xml, values-television/dimens.xml, dan values-sw600dp-land/dimens.xml valid dan konsisten."""
    default_dimens = os.path.join(RES_DIR, "values", "dimens.xml")
    tv_dimens = os.path.join(RES_DIR, "values-television", "dimens.xml")
    sw_dimens = os.path.join(RES_DIR, "values-sw600dp-land", "dimens.xml")

    assert os.path.exists(default_dimens)
    assert os.path.exists(tv_dimens)
    assert os.path.exists(sw_dimens)

    for p in [default_dimens, tv_dimens, sw_dimens]:
        tree = ET.parse(p)
        root = tree.getroot()
        names = {item.attrib.get("name") for item in root.findall("dimen")}
        assert "tv_card_title_text_size" in names
        assert "tv_card_title_height" in names
        assert "tv_badge_text_size" in names
        assert "section_title_text_size" in names
        assert "tab_text_size" in names
        assert "detail_title_text_size" in names

    # Verifikasi skala 10-Foot UI TV lebih besar daripada default mobile
    tree_def = ET.parse(default_dimens)
    tree_tv = ET.parse(tv_dimens)
    def_map = {item.attrib.get("name"): item.text for item in tree_def.getroot().findall("dimen")}
    tv_map = {item.attrib.get("name"): item.text for item in tree_tv.getroot().findall("dimen")}

    def resolve_val(m, k):
        v = m[k]
        if v.startswith("@dimen/"):
            return resolve_val(m, v.replace("@dimen/", ""))
        return float(v.replace("sp", "").replace("dp", ""))

    assert resolve_val(tv_map, "tv_card_title_text_size") > resolve_val(def_map, "tv_card_title_text_size")
    assert resolve_val(tv_map, "tv_card_title_height") > resolve_val(def_map, "tv_card_title_height")
    assert resolve_val(tv_map, "detail_title_text_size") > resolve_val(def_map, "detail_title_text_size")
