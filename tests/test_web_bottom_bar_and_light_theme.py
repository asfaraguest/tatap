"""Tests for Web Desktop Full-Width Bottom Bar, Mac Wallpaper Pattern, and Apple Light Theme."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT / "frontend" / "index.html"
STYLE_CSS = ROOT / "frontend" / "css" / "style.css"
APP_JS = ROOT / "frontend" / "js" / "app.js"


def test_index_html_mac_wallpaper_and_search_input():
    content = INDEX_HTML.read_text(encoding="utf-8")
    app_js = APP_JS.read_text(encoding="utf-8")
    
    # 1. Verify Mac Wallpaper SVG inside #bg-glow
    assert 'id="bg-glow"' in content
    assert 'class="mac-wallpaper-svg"' in content
    assert 'id="macWaveGrad1"' in content
    assert 'id="macWaveGrad2"' in content
    assert 'id="macWaveGrad3"' in content
    assert 'd="M0 340 C 380 180' in content
    assert 'var(--mac-contour-1)' in content
    assert 'var(--mac-contour-2)' in content
    assert 'var(--mac-contour-3)' in content
    
    # 2. Verify #cmd exists and app.js unlocks it on desktop while preserving TV baseline
    assert 'id="cmd"' in content
    assert 'readonly' in content
    assert 'cmdInput.removeAttribute("readonly")' in app_js


def test_style_css_mac_wallpaper_variables():
    content = STYLE_CSS.read_text(encoding="utf-8")
    
    # 1. Variables in :root
    assert "--mac-mesh:" in content
    assert "--mac-wave-1:" in content
    assert "--mac-wave-2:" in content
    assert "--mac-wave-3:" in content
    assert "--mac-contour-1:" in content
    
    # 2. Variables in [data-theme="light"]
    light_block_match = re.search(r'\[data-theme="light"\]\s*\{([^}]+)\}', content)
    assert light_block_match is not None
    light_vars = light_block_match.group(1)
    assert "--mac-mesh:" in light_vars
    assert "--mac-wave-1:" in light_vars
    assert "--head-bg:" in light_vars
    assert "--foot-bg:" in light_vars
    assert "--search-bg:" in light_vars
    assert "--popover-bg:" in light_vars
    
    # 3. #bg-glow uses var(--mac-mesh)
    assert re.search(r'#bg-glow\s*\{[^}]*background:\s*var\(--mac-mesh\)', content)
    assert ".mac-wallpaper-svg" in content


def test_style_css_bottom_bar_full_width():
    content = STYLE_CSS.read_text(encoding="utf-8")
    
    # Check media queries: .bottom-search-row and .statusbar must NOT be constrained to max-width: 1560px
    media_1024_matches = re.findall(r'@media\s*\([^)]*min-width:\s*1024px\)\s*\{([^}]+)\}', content)
    for m in media_1024_matches:
        assert ".bottom-search-row" not in m, ".bottom-search-row should not be restricted by max-width: 1560px in media query"
        assert ".statusbar" not in m, ".statusbar should not be restricted by max-width: 1560px in media query"

    # .bottom-bar, .bottom-search-row, .search-input-wrap must be width: 100%
    assert re.search(r'\.bottom-bar\s*\{[^}]*width:\s*100%', content)
    assert re.search(r'\.bottom-search-row\s*\{[^}]*width:\s*100%', content)
    assert re.search(r'\.search-input-wrap\s*\{[^}]*width:\s*100%', content)


def test_style_css_light_theme_components_and_no_duplicates():
    content = STYLE_CSS.read_text(encoding="utf-8")
    
    # Check that light theme overrides tui-head, bottom-bar, search-input-wrap, apple-popover
    assert re.search(r'\[data-theme="light"\]\s+\.tui-head\s*\{[^}]*background:\s*var\(--head-bg\)', content)
    assert re.search(r'\[data-theme="light"\]\s+\.bottom-bar\s*\{[^}]*background:\s*var\(--foot-bg\)', content)
    assert re.search(r'\[data-theme="light"\]\s+\.search-input-wrap\s*\{[^}]*background:\s*var\(--search-bg\)', content)
    assert re.search(r'\[data-theme="light"\]\s+\.apple-popover\s*\{[^}]*background:\s*var\(--popover-bg\)', content)
    
    # Zero backdrop blur tax
    assert "backdrop-filter" not in content

    # Check for no duplicate [data-theme="light"] #crt or component override blocks
    matches = re.findall(r'/\*\s*----\s*APPLE LIGHT MODE COMPONENT OVERRIDES\s*----\s*\*/', content)
    assert len(matches) == 1, "There should be exactly 1 Apple Light Mode component overrides block"

    # Verify video player modal remains cinema pitch black
    player_modal_match = re.search(r'#player-modal\s*\{[^}]*background:\s*rgba\(0,\s*0,\s*0,\s*0\.94\)\s*!important', content)
    assert player_modal_match is not None, "#player-modal must remain cinema pitch black with !important"
