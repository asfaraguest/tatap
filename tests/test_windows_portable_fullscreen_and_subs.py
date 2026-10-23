"""Automated tests for Windows Portable launcher fullscreen & subtitle overlay fix."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_launcher_go_has_fullscreen_win32_bridge():
    launcher_go = ROOT / "launcher" / "main.go"
    assert launcher_go.exists()
    content = launcher_go.read_text(encoding="utf-8")

    # Win32 APIs and constants
    assert "procGetWindowPlacement" in content
    assert "procSetWindowPlacement" in content
    assert "procMonitorFromWindow" in content
    assert "procGetMonitorInfoW" in content
    assert "procSetWindowPos" in content
    assert "WS_POPUP" in content
    assert "WS_OVERLAPPEDWINDOW" in content
    assert "MONITOR_DEFAULTTONEAREST" in content

    # Native fullscreen implementation
    assert "func setNativeFullscreen(hwnd uintptr, fullscreen bool)" in content
    assert "setNativeFullscreen(hwnd, fullscreen)" in content
    assert 'w.Bind("tatap_set_fullscreen"' in content


def test_launcher_go_compiles_for_windows():
    launcher_dir = ROOT / "launcher"
    env = os.environ.copy()
    env["GOOS"] = "windows"
    env["GOARCH"] = "amd64"
    res = subprocess.run(
        ["go", "vet", "."],
        cwd=str(launcher_dir),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"go vet failed: {res.stdout}\n{res.stderr}"


def test_frontend_js_handles_desktop_fullscreen_and_subtitles():
    app_js = ROOT / "frontend" / "js" / "app.js"
    assert app_js.exists()
    content = app_js.read_text(encoding="utf-8")

    # isDesktopEnv helper
    assert "function isDesktopEnv()" in content
    assert "tatap_set_fullscreen" in content

    # syncFullscreenSubtitles invokes tatap_set_fullscreen
    assert 'window.tatap_set_fullscreen(isFs)' in content or 'window.tatap_set_fullscreen' in content

    # Track mode is hidden on desktop to avoid Windows CC hijacking
    assert "!isDesktopEnv()" in content
    assert 't.mode=(isVidFs && !isDesktopEnv())?"showing":"hidden"' in content

    # paintCue preserves #pm-subs-overlay on desktop
    assert 'if(isVideoFullscreen() && !isDesktopEnv())' in content


def test_frontend_html_has_controls_list():
    index_html = ROOT / "frontend" / "index.html"
    assert index_html.exists()
    content = index_html.read_text(encoding="utf-8")
    assert 'controlsList="nodownload nofullscreen noremoteplayback"' in content
    assert 'disablePictureInPicture' in content


def test_frontend_css_suppresses_native_cue_hijack():
    style_css = ROOT / "frontend" / "css" / "style.css"
    assert style_css.exists()
    content = style_css.read_text(encoding="utf-8")
    assert "video::cue" in content
    assert "visibility: hidden !important" in content
    assert "font-size: 0px !important" in content
