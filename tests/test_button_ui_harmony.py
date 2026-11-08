import re
from pathlib import Path

def test_button_squircle_tokens():
    css_path = Path(__file__).resolve().parent.parent / "frontend" / "css" / "style.css"
    content = css_path.read_text(encoding="utf-8")

    # 1. Main navigation tab buttons
    assert re.search(r'\.nav-tab-btn\s*\{[^}]*border-radius:\s*8px', content), ".nav-tab-btn must have 8px squircle radius"

    # 2. Pager buttons
    assert re.search(r'\.pager-btn\s*\{[^}]*border-radius:\s*8px', content), ".pager-btn must have 8px squircle radius"

    # 3. Quick Play primary CTA
    assert re.search(r'\.btn-quick-play\s*\{[^}]*border-radius:\s*8px', content), ".btn-quick-play must have 8px squircle radius"
    assert re.search(r'\.btn-quick-play\s*\{[^}]*color:\s*#04101c', content), ".btn-quick-play must have #04101c dark contrast text"

    # 4. Detail action buttons & chips
    assert re.search(r'\.detail-action-btn\s*\{[^}]*border-radius:\s*8px', content), ".detail-action-btn must have 8px squircle radius"
    assert re.search(r'\.ep-range-chip\s*\{[^}]*border-radius:\s*8px', content), ".ep-range-chip must have 8px squircle radius"

    # 5. Artplayer controls dock
    assert re.search(r'\.art-ctrl-btn\s*\{[^}]*border-radius:\s*8px', content), ".art-ctrl-btn must have 8px squircle radius"

    # 6. AniSkip buttons
    assert re.search(r'\.art-aniskip-btn\s*\{[^}]*border-radius:\s*8px', content), ".art-aniskip-btn must have 8px squircle radius"
    assert re.search(r'\.art-aniskip-btn\s*\{[^}]*color:\s*#04101c', content), ".art-aniskip-btn must have #04101c text"
    assert re.search(r'\.pm-skip-btn\s*\{[^}]*border-radius:\s*8px', content), ".pm-skip-btn must have 8px squircle radius"
    assert re.search(r'\.pm-skip-btn\s*\{[^}]*color:\s*#04101c', content), ".pm-skip-btn must have #04101c text"

    # 7. Modal Buttons
    assert re.search(r'\.ai-actions-row\s+\.btn-primary[^{]*\{[^}]*border-radius:\s*8px', content), ".btn-primary must have 8px squircle radius"
    assert re.search(r'\.ai-actions-row\s+\.btn-secondary[^{]*\{[^}]*border-radius:\s*8px', content), ".btn-secondary must have 8px squircle radius"
    assert re.search(r'\.ai-actions-row\s+\.btn-danger[^{]*\{[^}]*border-radius:\s*8px', content), ".btn-danger must have 8px squircle radius"
    assert re.search(r'\.btn-resume-primary\s*\{[^}]*border-radius:\s*8px', content), ".btn-resume-primary must have 8px squircle radius"

def test_toast_and_art_notice_hud():
    css_path = Path(__file__).resolve().parent.parent / "frontend" / "css" / "style.css"
    content = css_path.read_text(encoding="utf-8")

    # Global Toast HUD (Top Right Corner)
    assert re.search(r'\.toast\s*\{[^}]*border-radius:\s*8px', content), ".toast must have 8px radius"
    assert re.search(r'\.toast\s*\{[^}]*background:\s*rgba\(13,\s*17,\s*26', content), ".toast must have obsidian dark background"
    assert re.search(r'\.toast\s*\{[^}]*border:\s*1px solid rgba\(56,\s*189,\s*248,\s*0\.45\)', content), ".toast must have cyan border"
    assert re.search(r'\.toast\s*\{[^}]*top:\s*72px', content), ".toast must float at top: 72px"
    assert re.search(r'\.toast\s*\{[^}]*right:\s*24px', content), ".toast must align to right: 24px"

    # In-player Art Notice HUD (Top Right Corner)
    assert re.search(r'\.art-video-player\s+\.art-notice\s*\{[^}]*top:\s*20px', content), ".art-notice must float at top: 20px"
    assert re.search(r'\.art-video-player\s+\.art-notice\s*\{[^}]*right:\s*20px', content), ".art-notice must align to right: 20px"
    assert re.search(r'\.art-video-player\s+\.art-notice-inner\s*\{[^}]*border-radius:\s*8px', content), ".art-notice-inner must have 8px radius"
    assert re.search(r'\.art-video-player\s+\.art-notice-inner\s*\{[^}]*border:\s*1px solid rgba\(56,\s*189,\s*248,\s*0\.45\)', content), ".art-notice-inner must have cyan border"

def test_button_spring_micro_physics():
    css_path = Path(__file__).resolve().parent.parent / "frontend" / "css" / "style.css"
    content = css_path.read_text(encoding="utf-8")

    # Micro-physics scale feedback on click (:active)
    assert re.search(r'\.art-ctrl-btn:active\s*\{[^}]*scale\(0\.9[67]\)', content), ".art-ctrl-btn:active must have spring scale"
    assert re.search(r'\.art-aniskip-btn:active\s*\{[^}]*scale\(0\.9[67]\)', content), ".art-aniskip-btn:active must have spring scale"
    assert re.search(r'\.btn-quick-play:active\s*\{[^}]*scale\(0\.9[67]\)', content), ".btn-quick-play:active must have spring scale"
    assert re.search(r'\.pager-btn:active[^{]*\{[^}]*scale\(0\.9[67]\)', content), ".pager-btn:active must have spring scale"

def test_toast_vector_icons_and_anti_duplicate_routing():
    css_path = Path(__file__).resolve().parent.parent / "frontend" / "css" / "style.css"
    css_content = css_path.read_text(encoding="utf-8")
    app_js_path = Path(__file__).resolve().parent.parent / "frontend" / "js" / "app.js"
    app_js_content = app_js_path.read_text(encoding="utf-8")

    # 1. CSS styling for vector icon wrap & HUD animation
    assert ".toast-icon-wrap" in css_content
    assert "hudSpringIn" in css_content
    assert "toastBottomIn" in css_content
    assert re.search(r'\.toast\s*\{[^}]*gap:\s*8px', css_content)
    assert re.search(r'\.art-notice-inner\s*\{[^}]*gap:\s*8px', css_content)

    # 2. Anti-duplicate toast routing & vector icon engine in app.js
    assert "function isPlayerOpen()" in app_js_content
    assert "function parseToastContent(" in app_js_content
    assert "function showArtNotice(" in app_js_content
    assert "if(isPlayerOpen()){" in app_js_content
    assert 'tBox.classList.add("hidden");' in app_js_content
    assert "icon-skip" in app_js_content
    assert "icon-rewind" in app_js_content
    assert "icon-forward" in app_js_content
    assert "icon-check" in app_js_content
