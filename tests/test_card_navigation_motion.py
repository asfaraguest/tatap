"""
Tests for Card-to-Card Motion, Transition Fluidity, and Spatial Navigation Parity:
1. Spatial 2D navigation algorithm (preserves column consistency, prevents jumps to col 0).
2. ArrowLeft / ArrowRight directional accuracy on dual-lane grids with header banners.
3. Left-edge transition to sidebar without index-offset bugs.
4. CSS motion synchronization (unified 200ms cubic-bezier transitions, layout containment, static GPU layer).
5. Scroll-into-view optimization (skips reflow when element is already in viewport).
"""

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
STYLE_CSS = FRONTEND_DIR / "css" / "style.css"
TERM_JS = FRONTEND_DIR / "js" / "term.js"


def test_spatial_target_algorithm_math():
    """Simulate spatialTarget algorithm in Python to verify exact directional math."""
    # Dual-lane layout mimicking 'lanjutan' (Masih Tayang):
    # Banner 1 at top 0..40
    # Seasonal row 0 (top 50, idx 1..6)
    # Seasonal row 1 (top 250, idx 7..12)
    # Banner 2 at top 420..460
    # Long-running row 0 (top 480, idx 14..19)
    geom = [
        {'idx': 1, 'top': 50, 'left': 0, 'w': 100, 'h': 150},
        {'idx': 2, 'top': 50, 'left': 120, 'w': 100, 'h': 150},
        {'idx': 3, 'top': 50, 'left': 240, 'w': 100, 'h': 150},
        {'idx': 4, 'top': 50, 'left': 360, 'w': 100, 'h': 150},
        {'idx': 5, 'top': 50, 'left': 480, 'w': 100, 'h': 150},
        {'idx': 6, 'top': 50, 'left': 600, 'w': 100, 'h': 150},
        {'idx': 7, 'top': 250, 'left': 0, 'w': 100, 'h': 150},
        {'idx': 8, 'top': 250, 'left': 120, 'w': 100, 'h': 150},
        {'idx': 9, 'top': 250, 'left': 240, 'w': 100, 'h': 150},
        {'idx': 10, 'top': 250, 'left': 360, 'w': 100, 'h': 150},
        {'idx': 11, 'top': 250, 'left': 480, 'w': 100, 'h': 150},
        {'idx': 12, 'top': 250, 'left': 600, 'w': 100, 'h': 150},
        {'idx': 14, 'top': 480, 'left': 0, 'w': 100, 'h': 150},
        {'idx': 15, 'top': 480, 'left': 120, 'w': 100, 'h': 150},
        {'idx': 16, 'top': 480, 'left': 240, 'w': 100, 'h': 150},
        {'idx': 17, 'top': 480, 'left': 360, 'w': 100, 'h': 150},
        {'idx': 18, 'top': 480, 'left': 480, 'w': 100, 'h': 150},
        {'idx': 19, 'top': 480, 'left': 600, 'w': 100, 'h': 150},
    ]

    def spatial_target(idx, direction):
        cur = next((g for g in geom if g['idx'] == idx), None)
        if not cur:
            return None
        curCX = cur['left'] + cur['w'] / 2
        curCY = cur['top'] + cur['h'] / 2
        candidates = [g for g in geom if g['idx'] != idx]
        for c in candidates:
            c['cx'] = c['left'] + c['w'] / 2
            c['cy'] = c['top'] + c['h'] / 2
            c['bottom'] = c['top'] + c['h']

        if direction == 'left':
            cands = [c for c in candidates if abs(c['cy'] - curCY) < cur['h'] * 0.48 and c['cx'] < curCX]
            if not cands:
                return None
            cands.sort(key=lambda c: curCX - c['cx'])
            return cands[0]['idx']

        if direction == 'right':
            cands = [c for c in candidates if abs(c['cy'] - curCY) < cur['h'] * 0.48 and c['cx'] > curCX]
            if not cands:
                return None
            cands.sort(key=lambda c: c['cx'] - curCX)
            return cands[0]['idx']

        if direction == 'down':
            below = [c for c in candidates if (c['top'] >= cur['top'] + cur['h'] - 8) or (c['cy'] > curCY + cur['h'] * 0.4)]
            if not below:
                return None
            minTop = min(c['top'] for c in below)
            nextRow = [c for c in below if c['top'] <= minTop + 28]
            if not nextRow:
                return None
            nextRow.sort(key=lambda c: abs(c['cx'] - curCX))
            return nextRow[0]['idx']

        if direction == 'up':
            above = [c for c in candidates if (c['bottom'] <= cur['top'] + 8) or (c['cy'] < curCY - cur['h'] * 0.4)]
            if not above:
                return None
            maxBottom = max(c['bottom'] for c in above)
            prevRow = [c for c in above if c['bottom'] >= maxBottom - 28]
            if not prevRow:
                return None
            prevRow.sort(key=lambda c: abs(c['cx'] - curCX))
            return prevRow[0]['idx']
        return None

    # Step-by-step horizontal navigation
    assert spatial_target(4, 'left') == 3, "Left from Col 3 must step to Col 2"
    assert spatial_target(3, 'left') == 2, "Left from Col 2 must step to Col 1"
    assert spatial_target(2, 'left') == 1, "Left from Col 1 must step to Col 0"
    assert spatial_target(1, 'left') is None, "Left from Col 0 has no card to the left (Left Edge)"

    # Horizontal right
    assert spatial_target(1, 'right') == 2
    assert spatial_target(2, 'right') == 3
    assert spatial_target(6, 'right') is None, "Right from Col 5 has no card to the right"

    # Vertical column preservation (Down)
    assert spatial_target(4, 'down') == 10, "Down from Col 3 (idx 4) must stay in Col 3 (idx 10), not jump to col 0"
    assert spatial_target(6, 'down') == 12, "Down from Col 5 (idx 6) must stay in Col 5 (idx 12)"
    assert spatial_target(1, 'down') == 7, "Down from Col 0 (idx 1) goes to Col 0 (idx 7)"

    # Cross-banner vertical transition (Row 1 of seasonal to Row 0 of long-running)
    assert spatial_target(10, 'down') == 17, "Down across banner from idx 10 (col 3) must hit idx 17 (col 3)"

    # Vertical column preservation (Up)
    assert spatial_target(17, 'up') == 10, "Up across banner from idx 17 (col 3) must hit idx 10 (col 3)"
    assert spatial_target(10, 'up') == 4, "Up from idx 10 (col 3) must hit idx 4 (col 3)"
    assert spatial_target(4, 'up') is None, "Up from top row has no card above"


def test_term_js_spatial_target_implementation():
    """Verify term.js implements the horizontal proximity sorting in spatialTarget."""
    content = TERM_JS.read_text(encoding="utf-8")
    assert "function spatialTarget(idx, direction)" in content
    # left/right sorts by cx distance
    assert "b.cx-a.cx" in content or "b.cx - a.cx" in content
    assert "a.cx-b.cx" in content or "a.cx - b.cx" in content
    # down/up sorts by abs(c.cx - curCX)
    assert "Math.abs(a.cx-curCX)-Math.abs(b.cx-curCX)" in content or "Math.abs(a.cx - curCX) - Math.abs(b.cx - curCX)" in content


def test_term_js_arrow_key_handlers_integrity():
    """Verify ArrowRight and ArrowLeft utilize spatial target and do not rely on broken modulo."""
    content = TERM_JS.read_text(encoding="utf-8")
    # ArrowRight uses rightTarget
    assert 'var geoRight = spatialTarget(S.sel, "right");' in content
    assert 'var rightTarget = ' in content
    # ArrowLeft uses leftTarget and checks isLeftEdge cleanly
    assert 'var geoLeft = spatialTarget(S.sel, "left");' in content
    assert 'if(isLeftEdge){' in content
    # Ensure broken (S.sel % cols) === 0 pattern is eliminated
    assert "(S.sel % cols) === 0" not in content


def test_term_js_render_sel_viewport_optimization():
    """Verify renderSel checks viewport bounding before calling scrollIntoView."""
    content = TERM_JS.read_text(encoding="utf-8")
    assert 'var container = $("search-sec");' in content
    assert 'eRect.top >= cRect.top' in content
    assert 'eRect.bottom <= cRect.bottom' in content
    assert 'selEl.scrollIntoView' in content


def test_style_css_smooth_transitions_and_containment():
    """Verify CSS transitions are synchronized, layout-contained, and GPU layer stabilized."""
    content = STYLE_CSS.read_text(encoding="utf-8")
    # Layout containment & static GPU layer on .poster-card
    assert ".poster-card{" in content
    assert "contain:layout style" in content or "contain: layout style" in content
    assert "transform:translate3d(0,0,0)" in content or "transform: translate3d(0, 0, 0)" in content
    assert "backface-visibility:hidden" in content or "backface-visibility: hidden" in content
    assert "will-change:transform" in content or "will-change: transform" in content

    # Unified 200ms cubic-bezier transitions
    assert "200ms cubic-bezier(0.16,1,0.3,1)" in content or "200ms cubic-bezier(0.16, 1, 0.3, 1)" in content
