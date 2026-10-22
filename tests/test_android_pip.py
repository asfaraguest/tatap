"""
tests/test_android_pip.py - Test suite verifying Picture-in-Picture (PiP)
support for Android Mobile in Tatap.
"""

import os
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(ROOT_DIR, "android", "app", "src", "main", "AndroidManifest.xml")
PLAYER_LAYOUT = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "layout", "activity_player.xml")
PLAYER_ACTIVITY = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "id", "tatap", "app", "PlayerActivity.java")
DRAWABLE_DIR = os.path.join(ROOT_DIR, "android", "app", "src", "main", "res", "drawable")


def test_manifest_supports_picture_in_picture():
    """Memastikan PlayerActivity memiliki android:supportsPictureInPicture='true' dan configChanges lengkap."""
    assert os.path.exists(MANIFEST_PATH), f"{MANIFEST_PATH} must exist"
    tree = ET.parse(MANIFEST_PATH)
    root = tree.getroot()
    android_ns = "{http://schemas.android.com/apk/res/android}"

    player_activity = None
    for app in root.iter("application"):
        for act in app.iter("activity"):
            if act.attrib.get(f"{android_ns}name") == ".PlayerActivity":
                player_activity = act
                break

    assert player_activity is not None, "PlayerActivity must be declared in AndroidManifest.xml"
    assert player_activity.attrib.get(f"{android_ns}supportsPictureInPicture") == "true", \
        "PlayerActivity must have android:supportsPictureInPicture='true'"

    config_changes = player_activity.attrib.get(f"{android_ns}configChanges", "")
    assert "orientation" in config_changes
    assert "screenSize" in config_changes
    assert "smallestScreenSize" in config_changes
    assert "screenLayout" in config_changes


def test_pip_vector_drawables_exist_and_valid():
    """Memastikan 4 aset drawable vektor PiP ada dan berformat XML vector valid."""
    pip_drawables = ["ic_pip.xml", "ic_pause.xml", "ic_replay_10.xml", "ic_forward_10.xml"]
    for d in pip_drawables:
        path = os.path.join(DRAWABLE_DIR, d)
        assert os.path.exists(path), f"Drawable {d} must exist at {path}"
        tree = ET.parse(path)
        root = tree.getroot()
        assert root.tag == "vector", f"Root tag of {d} must be <vector>"


def test_player_layout_contains_pip_buttons():
    """Memastikan activity_player.xml memuat tombol btn_pip dan btn_portrait_pip."""
    assert os.path.exists(PLAYER_LAYOUT), f"{PLAYER_LAYOUT} must exist"
    tree = ET.parse(PLAYER_LAYOUT)
    root = tree.getroot()
    android_ns = "{http://schemas.android.com/apk/res/android}"

    ids = set()
    for elem in root.iter():
        elem_id = elem.attrib.get(f"{android_ns}id")
        if elem_id:
            ids.add(elem_id.replace("@+id/", "").replace("@id/", ""))

    assert "btn_pip" in ids, "activity_player.xml must contain btn_pip in landscape top bar"
    assert "btn_portrait_pip" in ids, "activity_player.xml must contain btn_portrait_pip in portrait control bar"


def test_player_activity_pip_methods_and_lifecycle():
    """Memastikan PlayerActivity mengimplementasikan deteksi PiP, auto-enter, remote actions, dan lifecycle guards."""
    with open(PLAYER_ACTIVITY, "r", encoding="utf-8") as f:
        code = f.read()

    # 1. Detection & isolation
    assert "isPipSupported()" in code
    assert "!TvFocusHelper.isTv(this)" in code, "PiP must be strictly disabled on Android TV"
    assert "PackageManager.FEATURE_PICTURE_IN_PICTURE" in code

    # 2. Entry & parameters
    assert "enterPipMode()" in code
    assert "buildPipParams()" in code
    assert "setAutoEnterEnabled(player != null && player.isPlaying())" in code
    assert "setSeamlessResizeEnabled(true)" in code

    # 3. Remote actions & receiver
    assert "ACTION_PIP_CONTROL" in code
    assert "PIP_ACTION_REWIND" in code
    assert "PIP_ACTION_PLAY_PAUSE" in code
    assert "PIP_ACTION_FORWARD" in code
    assert "registerPipReceiver()" in code
    assert "unregisterReceiver(pipReceiver)" in code

    # 4. Lifecycle hooks & guards
    assert "onUserLeaveHint()" in code
    assert "onPictureInPictureModeChanged(boolean isInPictureInPictureMode" in code
    assert "isInPictureInPictureMode()" in code
    # onPause guard against stopping playback
    assert "if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N && isInPictureInPictureMode())" in code
