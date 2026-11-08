"""
Tests for Compact Dynamic Anime Card Sizing and Focused Card Zoom Effect:
- Viewport-aware dynamic sizing (vh-based clamp) in .poster-grid
- Max-height bounded .pc-media to ensure screen-fit without vertical scroll
- Prominent zoom transform on selected (.sel), focused (:focus-visible), hovered (:hover), and TV-focused (.tv-focus) cards
- High z-index elevation and illuminated border/shadow during zoom
- Uniform clamped body typography (2.5em height, line-clamp 2)
- Zero-padding/margin clean layout in .app-main-layout main
- Compact pager and sec-head margins
"""

import os
import re
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLE_CSS = os.path.join(REPO_ROOT, "frontend", "css", "style.css")


def test_poster_grid_viewport_aware_dynamic_sizing():
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        content = f.read()

    # .poster-grid uses clamp with vh in grid-template-columns
    assert ".poster-grid{display:grid;" in content
    assert "clamp(82px,11.2vh,126px)" in content or "11.2vh" in content
    # Wide screen dynamic grid
    assert "12vh" in content or "12.2vh" in content
    # Tablets & small desktop dynamic grid
    assert "@media (min-width:641px) and (max-width:900px)" in content
    assert "@media (min-width:1600px)" in content


def test_pc_media_max_height_screen_fit_constraint():
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        content = f.read()

    # .pc-media has max-height bound tied to viewport height
    assert ".pc-media{" in content
    assert "aspect-ratio:2/3" in content
    assert "max-height:clamp(100px,19.5vh,185px)" in content or "19.5vh" in content


def test_focused_card_zoom_transform_and_elevation():
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify zoom scale on selected/focused card
    assert ".poster-card.sel" in content
    assert "scale(1.20)" in content or "scale(1.15)" in content
    assert "scale(1.28)" in content
    assert "scale(1.30)" in content

    # Verify z-index elevation so zoomed card pops above adjacent cards
    assert "z-index:45" in content or "z-index: 45" in content or "z-index:25" in content
    assert "z-index:50" in content or "z-index: 50" in content or "z-index:30" in content

    # Verify fluid spring timing and transform-origin center
    assert "cubic-bezier(0.16,1,0.3,1)" in content or "cubic-bezier(0.16, 1, 0.3, 1)" in content
    assert "transform-origin:center center" in content


def test_zoomed_card_visual_glow_and_image_scale():
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        content = f.read()

    # Image scales smoothly inside zoomed card
    assert "scale(1.08)" in content or "scale(1.06)" in content
    # Box shadow glow
    assert "rgba(56,189,248" in content
    # TV focus zoom
    assert ".poster-card.tv-focus" in content
    # Light theme zoom
    assert '[data-theme="light"] .poster-card.sel' in content


def test_uniform_compact_body_typography():
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        content = f.read()

    # Clamped title height for uniform alignment
    assert "height:2.5em" in content
    assert "-webkit-line-clamp:2" in content
    assert "font-size:clamp(10.5px,1.35vh,12px)" in content or "1.35vh" in content


def test_app_main_layout_screen_fit_bounds():
    with open(STYLE_CSS, "r", encoding="utf-8") as f:
        content = f.read()

    # .app-main-layout main cleans legacy padding
    assert ".app-main-layout main" in content
    assert "overflow: hidden" in content

    # #search-sec has compact padding with comfortable top breathing room
    assert "padding: clamp(18px, 2.5vh, 28px) var(--pad-x) 8px var(--pad-x)" in content or "padding: 6px var(--pad-x) 8px var(--pad-x)" in content

    # .pager has compact margins
    assert "margin:4px 0 2px 0" in content or "margin: 4px 0 2px 0" in content
