"""Contract tests: Android history mode persistence (sub/dub) & mobile-safe back debounce (v2.11.5)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JAVA_DIR = ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app"


def _read(name):
    return (JAVA_DIR / name).read_text(encoding="utf-8")


def test_no_hardcoded_sub_mode_in_history_posts():
    for name in ("DetailActivity.java", "PlayerActivity.java"):
        content = _read(name)
        assert 'b.put("mode", "sub");' not in content, f"{name} masih hardcode mode 'sub' di body history"


def test_detail_history_uses_selected_mode():
    content = _read("DetailActivity.java")
    assert 'b.put("mode", mode != null ? mode : "sub");' in content


def test_player_history_carries_mode_poster_type():
    content = _read("PlayerActivity.java")
    idx = content.index("// Rekam episode baru ke riwayat")
    block = content[idx: idx + 1200]
    assert "requestMode" in block
    assert 'b.put("poster"' in block
    assert 'b.put("type"' in block


def test_detail_back_debounce_is_tv_only():
    content = _read("DetailActivity.java")
    m = re.search(r"public boolean dispatchKeyEvent\(KeyEvent event\)\s*\{(.*?)return super\.dispatchKeyEvent", content, re.S)
    assert m, "dispatchKeyEvent tidak ditemukan"
    body = m.group(1)
    assert "TvFocusHelper.isTv(this)" in body
    assert "lastResumeTimeMs < 450" in body


def test_tv_task_root_fallback_rebuilds_home_stack():
    content = _read("PlayerActivity.java")
    idx = content.index("private void handleBackAction()")
    block = content[idx: idx + 2500]
    assert "new Intent(this, MainActivity.class)" in block
    assert "startActivities(new Intent[]{home, intent})" in block
    assert "FLAG_ACTIVITY_CLEAR_TASK" in block
