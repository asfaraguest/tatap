"""
tests/test_android_tv_dialog_and_focus.py - Test suite verifying Android TV
dialog focus restoration, ListView selection calibration, DetailActivity focus
chains, and local subtitle file isolation.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JAVA_DIR = ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app"


def test_tv_focus_helper_checked_position_and_edittext_focus():
    """Memastikan TvFocusHelper mempertahankan checked position pada single choice dialog dan auto-focus EditText."""
    tv_focus_file = JAVA_DIR / "TvFocusHelper.java"
    assert tv_focus_file.exists()
    content = tv_focus_file.read_text(encoding="utf-8")

    # Checked position recognition
    assert "int checkedPos = lv.getCheckedItemPosition();" in content
    assert "lv.setSelection(checkedPos);" in content
    assert "lv.setSelection(0);" in content

    # EditText auto-focusing for custom input dialogs (e.g. Subtitle URL)
    assert "findEditText" in content
    assert "if (et != null && et.getVisibility() == View.VISIBLE)" in content
    assert "et.requestFocus();" in content


def test_player_activity_sub_picker_focus_restoration():
    """Memastikan seluruh sub-picker subtitle di PlayerActivity mengembalikan fokus ke player control saat ditutup."""
    player_file = JAVA_DIR / "PlayerActivity.java"
    assert player_file.exists()
    content = player_file.read_text(encoding="utf-8")

    # Helper method restoreSubPickerTvFocus
    assert "void restoreSubPickerTvFocus()" in content
    assert "isNavigatingToSubDialog = false;" in content
    assert "playerView.showController();" in content

    # OnDismissListener in sub pickers
    assert "setOnDismissListener(d -> restoreSubPickerTvFocus())" in content
    assert "dialog.setOnDismissListener(d -> restoreSubPickerTvFocus())" in content

    # Isolation of local file subtitle picker on TV
    assert "!TvFocusHelper.isTv(this)" in content
    assert "options.add(\"[+] Pilih File Subtitle Lokal" in content

    # Safe fallback if file picker fails
    assert "restoreSubPickerTvFocus();" in content


def test_detail_activity_dynamic_focus_chains():
    """Memastikan DetailActivity mengatur nextFocus secara dinamis agar tidak tersangkut di view GONE."""
    detail_file = JAVA_DIR / "DetailActivity.java"
    assert detail_file.exists()
    content = detail_file.read_text(encoding="utf-8")

    # updateTvFocusChains method
    assert "void updateTvFocusChains()" in content

    # Dynamic seasons chaining
    assert "btnBack.setNextFocusRightId(hasSeasons ? R.id.rv_detail_seasons : R.id.btn_sort_order);" in content
    assert "btnSortOrder.setNextFocusUpId(hasSeasons ? R.id.rv_detail_seasons : R.id.btn_back);" in content

    # Dynamic ranges chaining
    assert "btnSortOrder.setNextFocusDownId(hasRanges ? R.id.rv_episode_ranges : R.id.rv_episodes);" in content
    assert "rvEpisodes.setNextFocusUpId(hasRanges ? R.id.rv_episode_ranges : R.id.btn_sort_order);" in content

    # Invocations
    assert "updateTvFocusChains();" in content
