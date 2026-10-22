"""
tests/test_android_tv_sidebar_autohide.py - Test suite verifying Android TV
sidebar autohide (rail collapse 64dp <-> expand 210dp), duplicate icon fix,
and remote D-Pad focus chaining.
"""

import os
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TV_LAYOUT = os.path.join(ROOT_DIR, "android", "app", "src", "tv", "res", "layout", "activity_main.xml")
TELEVISION_LAYOUT = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "layout-television", "activity_main.xml")
MAIN_ACTIVITY = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "MainActivity.java")


def test_tv_layouts_exist_and_in_sync():
    """Memastikan kedua layout TV ada dan 100% identik."""
    assert os.path.exists(TV_LAYOUT), f"{TV_LAYOUT} must exist"
    assert os.path.exists(TELEVISION_LAYOUT), f"{TELEVISION_LAYOUT} must exist"
    with open(TV_LAYOUT, "r", encoding="utf-8") as f1, open(TELEVISION_LAYOUT, "r", encoding="utf-8") as f2:
        assert f1.read() == f2.read(), "TV layout and layout-television MUST be 100% in sync"


def test_no_duplicate_genre_icon_in_tv_layouts():
    """Memastikan btn_tab_genre menggunakan ic_tab_genre (bukan ic_filter duplicate)."""
    tree = ET.parse(TV_LAYOUT)
    root = tree.getroot()
    android_ns = "{http://schemas.android.com/apk/res/android}"

    genre_tab = None
    for elem in root.iter("TextView"):
        if elem.attrib.get(f"{android_ns}id") == "@+id/btn_tab_genre":
            genre_tab = elem
            break

    assert genre_tab is not None, "btn_tab_genre must be found in TV activity_main.xml"
    drawable_start = genre_tab.attrib.get(f"{android_ns}drawableStart")
    assert drawable_start == "@drawable/ic_tab_genre", f"btn_tab_genre must use @drawable/ic_tab_genre, got {drawable_start}"


def test_tv_sidebar_structure_ids():
    """Memastikan layout_tv_sidebar, layout_tv_brand, tv_badge_tv, layout_tv_bottom_controls ada di layout TV."""
    tree = ET.parse(TV_LAYOUT)
    root = tree.getroot()
    android_ns = "{http://schemas.android.com/apk/res/android}"

    ids = set()
    for elem in root.iter():
        elem_id = elem.attrib.get(f"{android_ns}id")
        if elem_id:
            ids.add(elem_id.replace("@+id/", "").replace("@id/", ""))

    assert "layout_tv_sidebar" in ids
    assert "layout_tv_brand" in ids
    assert "tv_app_logo" in ids
    assert "tv_badge_tv" in ids
    assert "layout_tv_bottom_controls" in ids
    assert "btn_tab_musim" in ids
    assert "btn_tab_airing" in ids
    assert "btn_tab_jadwal" in ids
    assert "btn_tab_riwayat" in ids
    assert "btn_tab_favorit" in ids
    assert "btn_tab_katalog" in ids
    assert "btn_tab_genre" in ids
    assert "btn_status_power" in ids
    assert "btn_toggle_menu" in ids


def test_main_activity_zero_duplicate_tab_imagespan_on_vertical_sidebar():
    """Memastikan MainActivity tidak memanggil updateTvTabSpannable saat isVerticalSidebar aktif."""
    with open(MAIN_ACTIVITY, "r", encoding="utf-8") as f:
        content = f.read()

    assert "if (TvFocusHelper.isTv(this) && !isVerticalSidebar)" in content, \
        "updateTvTabSpannable must only run when !isVerticalSidebar to avoid duplicate icons on sidebar"
    assert "tab.setCompoundDrawableTintList(android.content.res.ColorStateList.valueOf(color));" in content


def test_main_activity_autohide_and_expand_methods():
    """Memastikan metode autohide (rail 64dp <-> expand 210dp) dan focus listener ada di MainActivity."""
    with open(MAIN_ACTIVITY, "r", encoding="utf-8") as f:
        content = f.read()

    assert "setTvSidebarExpanded(boolean expand, boolean animate)" in content
    assert "setupTvSidebarFocusListener()" in content
    assert "isViewDescendantOf(View child, View parent)" in content
    assert "dpToPx(210)" in content, "Expanded width must be 210dp"
    assert "dpToPx(64)" in content, "Collapsed rail width must be 64dp"
    assert "addOnGlobalFocusChangeListener" in content, "Must use OnGlobalFocusChangeListener for reactive D-Pad focus"


def test_tv_sidebar_collapsed_icons_centered():
    """Memastikan icon pada sidebar TV saat collapsed (rail 64dp) terpusat rapi di midline 24dp."""
    with open(MAIN_ACTIVITY, "r", encoding="utf-8") as f:
        content = f.read()

    # Search icon centering in rail
    assert "int searchPad = (dpToPx(48) - dpToPx(15)) / 2;" in content
    # Tab icons centering in rail
    assert "int tabPad = (dpToPx(48) - dpToPx(15)) / 2;" in content
    # Bottom controls square bounds & centering in rail
    assert "LinearLayout.LayoutParams lpPower = new LinearLayout.LayoutParams(dpToPx(38), dpToPx(38));" in content
    assert "LinearLayout.LayoutParams lpMenu = new LinearLayout.LayoutParams(dpToPx(38), dpToPx(38));" in content
    assert "int menuPad = (dpToPx(38) - dpToPx(15)) / 2;" in content
    # Tab appearance preservation when collapsed
    assert "int tabPad = isTvSidebarExpanded ? dpToPx(10) : (dpToPx(48) - dpToPx(15)) / 2;" in content

