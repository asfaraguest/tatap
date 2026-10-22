"""Tests for Apple UI x OG Tatap refinement on Desktop and Web.

Verifies:
1. Apple UI specular inset highlights and spring easing curves in :root.
2. 4 independent corner badge placements in .poster-card (zero collision).
3. Desktop poster card hover lift with spring animation.
4. Desktop anime detail sheet modal bounding, flex column, and 44px uniform episode buttons.
5. Desktop video player HUD layering, smooth auto-hide transition, and floating AniSkip pill.
6. Strict preservation of mobile responsive breakpoints (<= 768px and <= 480px).
7. Strict preservation of TV 10-foot UI (.tv-focus) without interference.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE_CSS = ROOT / "frontend" / "css" / "style.css"


def test_apple_ui_tokens_and_spring_curves():
    """Verify specular highlights and Apple spring curves exist in :root."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert "--specular-inset" in css
    assert "inset 0 1px 0 rgba(255,255,255,0.08)" in css or "inset 0 1px 0 rgba(255, 255, 255, 0.08)" in css
    assert "--ease-spring" in css
    assert "cubic-bezier(0.22,1,0.36,1)" in css or "cubic-bezier(0.22, 1, 0.36, 1)" in css
    assert "--ease-out-smooth" in css
    assert "--accent:#38bdf8;" in css or "--accent: #38bdf8;" in css


def test_four_corner_independent_badges():
    """Verify badges are positioned in 4 separate corners to eliminate collision."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    # Top-Left: .pc-idx
    assert ".pc-idx{top:8px;left:8px" in css or ".pc-idx { top: 8px; left: 8px" in css or ".pc-idx{top: 8px; left: 8px" in css or ".pc-idx{top:8px;left:8px;" in css
    # Top-Right: .pc-score
    assert ".pc-score{top:8px;right:8px" in css or ".pc-score { top: 8px; right: 8px" in css or ".pc-score{top: 8px; right: 8px" in css or ".pc-score{top:8px;right:8px;" in css
    # Bottom-Left: .pc-badge-tag
    assert ".pc-badge-tag{bottom:12px;left:8px" in css or ".pc-badge-tag { bottom: 12px; left: 8px" in css or ".pc-badge-tag{bottom: 12px; left: 8px" in css
    # Bottom-Right: .pc-badge-type
    assert ".pc-badge-type{bottom:12px;right:8px" in css or ".pc-badge-type { bottom: 12px; right: 8px" in css or ".pc-badge-type{bottom: 12px; right: 8px" in css
    # Bottom baseline: .pc-progress-track
    assert ".pc-progress-track{position:absolute;bottom:0;left:0;right:0;height:3px" in css or ".pc-progress-track{position:absolute;bottom:0" in css


def test_desktop_poster_card_hover_spring():
    """Verify desktop hover lift uses spring transition."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert "var(--ease-spring)" in css
    assert "scale(1.015)" in css
    assert "border-radius:var(--r-card)" in css


def test_detail_sheet_desktop_bounding_and_ep_grid():
    """Verify detail modal sheet uses max-height bound and uniform 44px buttons."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert "max-height:min(86vh,780px)" in css or "max-height: min(86vh, 780px)" in css
    assert "border-radius:16px" in css
    assert "height:44px" in css
    assert "min-height:44px" in css
    assert "max-height:44px" in css


def test_desktop_player_hud_and_skip_btn():
    """Verify player shell specular shadow, auto-hide transition, and skip button styling."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    assert "box-shadow:0 32px 80px rgba(0,0,0,0.9),var(--specular-inset)" in css or "0 32px 80px" in css
    assert "transition:opacity 220ms var(--ease-out-smooth)" in css
    assert ".pm-skip-btn" in css
    assert "border-radius:24px" in css


def test_mobile_breakpoints_and_tv_focus_preserved():
    """Verify mobile breakpoints and TV D-pad focus are strictly preserved."""
    css = STYLE_CSS.read_text(encoding="utf-8")

    # Mobile breakpoints preserved
    assert "@media (max-width:480px)" in css
    assert "@media (max-width:768px)" in css

    # TV D-Pad focus preserved
    assert ".tv-focus" in css
    assert "outline: 3px solid var(--accent, #38bdf8) !important;" in css
    assert "scroll-margin: 72px !important;" in css
