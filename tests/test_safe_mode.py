import os
import sys
import pytest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, "backend"))
import main  # noqa: E402


def test_parse_safe_mode_values():
    assert main._parse_safe_mode(1) == 1
    assert main._parse_safe_mode(0) == 0
    assert main._parse_safe_mode("1") == 1
    assert main._parse_safe_mode("0") == 0
    assert main._parse_safe_mode("true") == 1
    assert main._parse_safe_mode("false") == 0
    assert main._parse_safe_mode("on") == 1
    assert main._parse_safe_mode("off") == 0
    assert main._parse_safe_mode("mati") == 0
    assert main._parse_safe_mode(None) == 1


@pytest.mark.asyncio
async def test_safe_mode_settings_api():
    # Test set safe_mode to 0
    res = await main.set_set({"safe_mode": "0"})
    assert res.get("success") is True

    # Test get settings
    get_res = await main.get_set()
    assert get_res.get("success") is True
    assert get_res["data"].get("safe_mode") == "0"

    # Reset back to 1
    res = await main.set_set({"safe_mode": "1"})
    assert res.get("success") is True


@pytest.mark.asyncio
async def test_genres_safe_mode_filtering():
    # 1. safe_mode = 1 (default / active)
    res_safe = await main.genres(safe_mode=1)
    assert res_safe.get("success") is True
    genres_safe = res_safe["data"]["list"]
    safe_slugs = [g.get("slug", "").lower() for g in genres_safe]
    assert "hentai" not in safe_slugs
    assert "ecchi" not in safe_slugs
    assert "erotica" not in safe_slugs
    assert "magical-sex-shift" not in safe_slugs

    # 2. safe_mode = 0 (inactive)
    res_off = await main.genres(safe_mode=0)
    assert res_off.get("success") is True
    genres_off = res_off["data"]["list"]
    off_slugs = [g.get("slug", "").lower() for g in genres_off]
    # Hentai must STILL be blacklisted 100% per master directive #4
    assert "hentai" not in off_slugs


@pytest.mark.asyncio
async def test_search_safe_mode_filtering():
    # Vulgar search query in safe mode
    res_safe = await main.search(q="ecchi", safe_mode=1)
    assert res_safe.get("success") is True
    assert res_safe["data"]["results"] == []

    # Hentai query must always return empty regardless of safe_mode
    res_h1 = await main.search(q="hentai", safe_mode=1)
    res_h0 = await main.search(q="hentai", safe_mode=0)
    assert res_h1["data"]["results"] == []
    assert res_h0["data"]["results"] == []


def test_android_safe_mode_declarations_and_layout():
    help_xml = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "layout", "dialog_command_help.xml")
    assert os.path.exists(help_xml)
    with open(help_xml, "r", encoding="utf-8") as f:
        xml = f.read()

    assert "cmd_item_safemode" in xml
    assert "tv_safemode_badge" in xml
    assert "tv_safemode_desc" in xml
    assert ":safemode" in xml


def test_android_main_activity_safe_mode_integration():
    main_java = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "MainActivity.java")
    assert os.path.exists(main_java)
    with open(main_java, "r", encoding="utf-8") as f:
        java = f.read()

    assert "isSafeModeEnabled()" in java
    assert "pref_safemode" in java
    assert "isAdultAnime(" in java
    assert "isVulgarKeyword(" in java
    assert "handleSafeModeCommand(" in java
    assert "syncBackendSafeMode(" in java
    assert 'case "safemode":' in java
    assert "R.id.cmd_item_safemode" in java


def test_android_detail_activity_safe_mode_integration():
    detail_java = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "DetailActivity.java")
    assert os.path.exists(detail_java)
    with open(detail_java, "r", encoding="utf-8") as f:
        java = f.read()

    assert "pref_safemode" in java
    assert "ecchi" in java
    assert "erotica" in java
