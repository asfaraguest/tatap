"""Automated tests for Android TV back navigation flow from PlayerActivity to DetailActivity."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JAVA_DIR = ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app"


def test_player_activity_consumes_back_key_on_tv():
    player_file = JAVA_DIR / "PlayerActivity.java"
    assert player_file.exists()
    content = player_file.read_text(encoding="utf-8")

    # KEYCODE_BACK handling in dispatchKeyEvent
    assert "if (keyCode == KeyEvent.KEYCODE_BACK)" in content
    assert "if (TvFocusHelper.isTv(this))" in content
    assert "if (event.getAction() == KeyEvent.ACTION_UP)" in content
    assert "handleBackAction();" in content

    # Fallback reconstruction guard when isTaskRoot() is true on TV
    assert "if (TvFocusHelper.isTv(this) && isTaskRoot() && slug != null && !slug.isEmpty())" in content
    assert "Intent intent = new Intent(this, DetailActivity.class);" in content


def test_detail_activity_has_back_debounce_and_tv_focus():
    detail_file = JAVA_DIR / "DetailActivity.java"
    assert detail_file.exists()
    content = detail_file.read_text(encoding="utf-8")

    # lastResumeTimeMs and onResume handling
    assert "lastResumeTimeMs = SystemClock.uptimeMillis();" in content
    assert "if (TvFocusHelper.isTv(this))" in content
    assert "btnQuickPlay.requestFocus();" in content or "rvEpisodes.requestFocus();" in content

    # dispatchKeyEvent debounce filter
    assert "public boolean dispatchKeyEvent(KeyEvent event)" in content
    assert "if (event.getKeyCode() == KeyEvent.KEYCODE_BACK)" in content
    assert "SystemClock.uptimeMillis() - lastResumeTimeMs < 450" in content
