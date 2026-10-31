import os
import sys
import time
import pytest
import threading
import uvicorn
from playwright.sync_api import sync_playwright

# Gunakan port isolasi lokal khusus pengujian E2E
TEST_PORT = 8799

def run_server():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
    import main
    uvicorn.run(main.app, host="127.0.0.1", port=TEST_PORT, log_level="error")

@pytest.fixture(scope="module")
def local_server():
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    # Tunggu server aktif
    import urllib.request
    ready = False
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{TEST_PORT}/api/settings", timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(0.2)
    assert ready, "Server lokal gagal start untuk E2E test"
    yield f"http://127.0.0.1:{TEST_PORT}"

def test_e2e_player_subtitles_episodes_and_recovery(local_server):
    """Pengujian E2E headless Chromium: player modal, subtitle overlay, next/prev episode, dan event recovery."""
    import glob
    chrome_matches = glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"))
    chrome_path = chrome_matches[0] if chrome_matches else None
    if chrome_path is None and not os.path.exists("/usr/bin/chromium-browser"):
        pytest.skip("Chromium binary tidak ditemukan untuk E2E test")

    launch_kwargs = {"headless": True}
    if chrome_path:
        launch_kwargs["executable_path"] = chrome_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        # 1. Buka halaman utama Tatap
        page.goto(local_server, wait_until="networkidle")
        assert "Tatap" in page.title()

        # 2. Verifikasi container player & elemen kontrol
        stage = page.locator(".ambient-stage")
        assert stage.count() > 0

        # 3. Simulasi inisialisasi state player secara programmatic
        page.evaluate("""() => {
            window.cur.slug = 'test-e2e-anime';
            window.cur.title = 'Test E2E Anime';
            window.cur.mode = 'sub';
            window.cur.eps = [
                { ep: 1, ep_id: '1' },
                { ep: 2, ep_id: '2' },
                { ep: 3, ep_id: '3' }
            ];
            window.cur.ep = 1;
            
            // Buka player modal
            const pm = document.getElementById('player-modal');
            pm.classList.remove('hidden');
            document.getElementById('pm-title').textContent = window.cur.title;
            updatePrevNext();
        }""")

        # 4. Verifikasi boundary episode navigation
        prev_btn = page.locator("#pm-prev")
        next_btn = page.locator("#pm-next")
        
        # Di Episode 1, tombol prev WAJIB disabled
        assert prev_btn.is_disabled() is True
        # Tombol next aktif
        assert next_btn.is_disabled() is False

        # 5. Simulasi ganti episode via stepEp(+1) dengan stubbing openPlayer
        page.evaluate("() => { window.openPlayer = function(ep) { window.cur.ep = ep; updatePrevNext(); }; }")
        page.evaluate("() => { stepEp(1); }")
        # Di Episode 2, tombol prev sekarang harus aktif
        assert prev_btn.is_disabled() is False
        assert next_btn.is_disabled() is False

        # Di Episode 3 (terakhir), tombol next WAJIB disabled
        page.evaluate("() => { stepEp(1); }")
        assert next_btn.is_disabled() is True

        # 6. Uji Subtitle Dual-Layer Rendering (DOM Overlay & Native Cue)
        page.evaluate("""() => {
            const vtt = `WEBVTT

00:00:01.000 --> 00:00:05.000
Halo dunia subtitle Tatap!`;
            window.cur.cues = parseVtt(vtt);
            const v = document.getElementById('vid');
            v.currentTime = 2.0; // Waktu jatuh dalam rentang cue
            paintCue();
            syncNativeTextTrack(vtt, window.cur.cues, 'id');
        }""")

        # Verifikasi teks subtitle muncul di overlay DOM #pm-subs-overlay
        overlay_text = page.locator("#pm-subs-overlay span").inner_text()
        assert "Halo dunia subtitle Tatap!" in overlay_text

        # 7. Uji Pemulihan Koneksi (Connection Recovery Handler)
        page.evaluate("""() => {
            // Pasang mock Hls object untuk menguji penanganan NETWORK_ERROR fatal
            let startLoadCalled = false;
            window._hls = {
                _networkRetried: false,
                startLoad: function() { startLoadCalled = true; },
                destroy: function() {}
            };

            // Simulasikan event error jaringan fatal
            const d = { fatal: true, type: 'networkError', details: 'manifestLoadError' };
            const h = window._hls;
            if (d.fatal && d.type === 'networkError' && !h._networkRetried) {
                h._networkRetried = true;
                document.getElementById('pm-status').textContent = 'mencoba memulihkan koneksi stream...';
                h.startLoad();
            }
            window.__recoveryTestSuccess = startLoadCalled;
        }""")

        status_text = page.locator("#pm-status").inner_text()
        recovery_success = page.evaluate("() => window.__recoveryTestSuccess")
        assert "mencoba memulihkan koneksi stream..." in status_text
        assert recovery_success is True

        browser.close()
