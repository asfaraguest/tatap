"""Unit tests verifying soft color palette and spacing refinement on Web & Desktop platform."""

from pathlib import Path
import re

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
STYLE_CSS = FRONTEND_DIR / "css" / "style.css"
APP_JS = FRONTEND_DIR / "js" / "app.js"


def test_style_css_soft_color_palette():
    content = STYLE_CSS.read_text(encoding="utf-8")

    # Assert modern soft colors in :root
    assert "--accent:#38bdf8;" in content or "--accent: #38bdf8;" in content
    assert "--bg:#0c0d12;" in content or "--bg: #0c0d12;" in content
    assert "--accent-deep:#0284c7;" in content or "--accent-deep: #0284c7;" in content
    assert "--accent-hover:#7dd3fc;" in content or "--accent-hover: #7dd3fc;" in content

    # Assert complete absence of electric cyan and swamp dark AI-slop colors
    ai_slop_colors = [
        "#19d0d0",
        "#38e8e8",
        "#0e9f9f",
        "#00363a",
        "#002428",
        "#0e281e",
        "#241b0d",
        "#78350f",
        "rgba(25, 208, 208",
        "rgba(25,208,208",
    ]
    for color in ai_slop_colors:
        assert color not in content, f"Found deprecated AI-slop color '{color}' in style.css"


def test_top_bar_dimensions_and_apple_concentric_geometry():
    content = STYLE_CSS.read_text(encoding="utf-8")

    # .tui-head height 58px on desktop, 52px on mobile
    assert "height:58px;" in content or "height: 58px;" in content
    assert "height:52px" in content

    # Concentric segmented control: container R=10px, button R=7px (R_inner = R_outer - padding)
    assert ".nav-tabs-bar" in content
    assert "border-radius:10px;" in content or "border-radius: 10px;" in content
    assert "height:38px;" in content or "height: 38px;" in content

    assert ".nav-tab-btn" in content
    assert "border-radius:7px;" in content or "border-radius: 7px;" in content
    assert "height:32px;" in content or "height: 32px;" in content

    # Gear menu button 38px x 38px with radius 10px (aligned with midline)
    assert ".header-drawer-btn" in content
    assert "width:38px;" in content or "width: 38px;" in content
    assert "height:38px;" in content or "height: 38px;" in content
    assert "border-radius:10px;" in content or "border-radius: 10px;" in content

    # Apple Popover vertical gap: 62px (58px header + 4px gap)
    assert "top:62px;" in content or "top: 62px;" in content


def test_spacing_padding_and_margins():
    content = STYLE_CSS.read_text(encoding="utf-8")
    content_no_space = re.sub(r"\s+", "", content)

    # main container padding
    assert "padding:clamp(22px,2.6vw,34px)var(--pad-x)calc(var(--status-h)+36px);" in content_no_space

    # Section head vertical rhythm and catalog spacing
    assert "margin:0 0 clamp(16px,2vw,22px);" in content or "margin: 0 0 clamp(16px, 2vw, 22px);" in content
    assert "#continue-sec .sec-head" in content

    # Poster grid top headroom and bottom spacing
    assert "margin-top:6px;" in content_no_space or "margin-top: 6px;" in content
    assert "margin-top:8px;" in content_no_space or "margin-top: 8px;" in content

    # Search wrap height and padding
    assert "height:44px;" in content or "height: 44px;" in content
    assert "padding:0 14px;" in content or "padding: 0 14px;" in content

    # Poster card body and history info padding
    assert "padding:8px6px4px" in content_no_space
    assert "padding:10px 12px;" in content or "padding: 10px 12px;" in content


def test_badges_and_active_chips_soft_styling():
    content = STYLE_CSS.read_text(encoding="utf-8")

    # Amber score badge
    assert "rgba(245, 158, 11, 0.12)" in content or "rgba(245,158,11,0.12)" in content
    assert "#fbbf24" in content

    # Emerald finished status
    assert "rgba(16, 185, 129, 0.12)" in content or "rgba(16,185,129,0.12)" in content
    assert "#34d399" in content

    # Soft sky ongoing status
    assert "rgba(56, 189, 248, 0.12)" in content or "rgba(56,189,248,0.12)" in content

    # Active chips & filters soft tint
    assert "rgba(56, 189, 248, 0.15)" in content or "rgba(56,189,248,0.15)" in content


def test_js_app_no_ai_slop_inline_styles():
    content = APP_JS.read_text(encoding="utf-8")

    ai_slop_strings = [
        "var(--cyan,#00dbeb)",
        "#00dbeb",
        "#19d0d0",
    ]
    for s in ai_slop_strings:
        assert s not in content, f"Found deprecated string '{s}' in app.js"
