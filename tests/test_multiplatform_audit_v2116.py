from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def test_web_desktop_fixes_w1_to_w8():
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")
    term_js = (ROOT / "frontend" / "js" / "term.js").read_text(encoding="utf-8")

    # W1: #pop-update calls checkForUpdate(true)
    assert "checkUpdate(true)" not in app_js
    assert 'var popUpdate = $("pop-update");' in app_js
    assert "checkForUpdate(true);" in app_js

    # W2: #pop-help uses window.Tui.cmdUsage() instead of undefined HELP_TEXT
    assert "HELP_TEXT" not in app_js
    assert "window.Tui.cmdUsage()" in app_js

    # W3: formatTimeSec exported on window.App
    assert "formatTimeSec:formatTimeSec" in app_js

    # W4: toggleModalBookmark checks window.Tui.view() === "favorit"
    assert 'window.Tui.view === "favorit"' not in app_js
    assert 'window.Tui.view() === "favorit"' in app_js

    # W5: renderSourceUI syncs #pop-src-badge and #drawer-src-badge for 3 sources
    assert '$("pop-src-badge")' in app_js
    assert '$("drawer-src-badge")' in app_js
    assert "AniChan" in app_js

    # W6: openTitle restores meta.mode and calls syncSeg("mode-seg", "mode", cur.mode)
    assert 'meta.mode === "dub" || meta.mode === "sub"' in app_js
    assert 'syncSeg("mode-seg", "mode", cur.mode);' in app_js

    # W7: isModalOpen in term.js checks help-overlay
    assert '$("help-overlay")' in term_js

    # W8: No duplicate case "filter": in term.js
    assert len(re.findall(r'case\s+"filter"\s*:', term_js)) == 1


def test_windows_launcher_and_fullscreen_fixes_p1_to_p3():
    main_go = (ROOT / "launcher" / "main.go").read_text(encoding="utf-8")
    app_js = (ROOT / "frontend" / "js" / "app.js").read_text(encoding="utf-8")

    # P1: procDone channel via pyCmd.Wait() instead of GetExitCodeProcess(Pid)
    assert "GetExitCodeProcess(syscall.Handle(pyCmd.Process.Pid)" not in main_go
    assert "procDone := make(chan error, 1)" in main_go
    assert "procDone <- pyCmd.Wait()" in main_go

    # P2: closePlayer exits native fullscreen
    assert "window.tatap_set_fullscreen(false);" in app_js

    # P3: Graceful POST /api/shutdown on launcher exit
    assert "/api/shutdown" in main_go


def test_linux_apprun_env_sanitization_l1():
    apprun = (ROOT / "linux" / "AppRun").read_text(encoding="utf-8")

    # L1: run_sys helper strips PYTHONHOME and PYTHONPATH and restores host PATH/LD_LIBRARY_PATH
    assert "run_sys()" in apprun
    assert "-u PYTHONHOME -u PYTHONPATH" in apprun
    assert "SYS_LD_LIBRARY_PATH" in apprun
    assert 'run_sys "$BROWSER_CMD"' in apprun
    assert "run_sys xdg-open" in apprun


def test_android_mobile_and_tv_fixes_a1_to_a6():
    update_mgr = (
        ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app" / "AppUpdateManager.java"
    ).read_text(encoding="utf-8")
    main_act = (
        ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app" / "MainActivity.java"
    ).read_text(encoding="utf-8")
    detail_act = (
        ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app" / "DetailActivity.java"
    ).read_text(encoding="utf-8")
    player_act = (
        ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app" / "PlayerActivity.java"
    ).read_text(encoding="utf-8")

    # A1: Dynamic getInstalledVersion(context) instead of hardcoded "2.9.2"
    assert "2.9.2" not in update_mgr
    assert "public static String getInstalledVersion(Context context)" in update_mgr

    # A2: MainActivity.onResume refreshes favorit/riwayat and adapter badges; :favorit uses resetFiltersToTab
    assert "protected void onResume()" in main_act
    assert 'resetFiltersToTab("favorit");' in main_act

    # A3: switchDefaultSource supports 3 sources (hianime, otakudesu, anichan) and clears tabDataCache
    assert '"anichan"' in main_act
    assert "tabDataCache.clear();" in main_act
    assert 'switchDefaultSource("");' in main_act

    # A4: showCommandHelpDialog uses activateSearchInput() for TV compatibility
    assert main_act.count("activateSearchInput();") >= 5

    # A5: DetailActivity SeasonAdapter passes mode extra
    assert 'intent.putExtra("mode", mode);' in detail_act

    # A6: PlayerActivity updates btnPortraitQuality & btnPortraitSub and uses currentMode in executePreResolveNeighbors
    assert "btnPortraitQuality.setText(" in player_act
    assert 'btnPortraitSub.setText("Sub: "' in player_act
    assert '"&mode=" + URLEncoder.encode(currentMode, "UTF-8")' in player_act
