"""Tests for OpenSubtitles integration, Smart Merge with anime subtitles, and Android PiP lifecycle."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from api.desync import _decode_http_body
from api.opensubtitles import (
    clean_title_And_season,
    is_opensubtitles_ad_text,
    strip_opensubtitles_ads,
    _score_subtitle_candidate,
)
from api.translate import (
    estimate_optimal_offset,
    find_unmatched_builtin_cues,
    merge_opensubtitles_with_builtin,
    build_vtt,
)


def test_desync_http_chunked_and_gzip_decode():
    """Pastikan _decode_http_body mampu mendekode Transfer-Encoding chunked dan gzip."""
    # Chunked payload: "5\r\nHello\r\n6\r\n World\r\n0\r\n\r\n"
    chunked = b"5\r\nHello\r\n6\r\n World\r\n0\r\n\r\n"
    hdr_chunked = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
    decoded = _decode_http_body(hdr_chunked, chunked)
    assert decoded == b"Hello World"

    # Gzip payload
    import gzip
    gz_body = gzip.compress(b"WEBVTT\n\n00:00.000 --> 00:02.000\nTest Sub")
    hdr_gz = b"HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\n\r\n"
    decompressed = _decode_http_body(hdr_gz, gz_body)
    assert b"WEBVTT" in decompressed


def test_opensubtitles_clean_title_and_season():
    """Pastikan parser judul & season mengekstrak season dengan akurat."""
    t1, s1 = clean_title_And_season("Sousou no Frieren Season 2")
    assert s1 == 2
    assert "frieren" in t1.lower()

    t2, s2 = clean_title_And_season("Mushoku Tensei II: Isekai Ittara Honki Dasu Part 2")
    assert s2 == 2

    t3, s3 = clean_title_And_season("", "jujutsu-kaisen-2nd-season-sub-indo")
    assert s3 == 2


def test_opensubtitles_ad_stripper():
    """Pastikan watermark dan iklan OpenSubtitles dibersihkan secara mutlak."""
    assert is_opensubtitles_ad_text("Iklankan produk atau merek dagang Anda di sini")
    assert is_opensubtitles_ad_text("Support us and become VIP member to remove ads")
    assert is_opensubtitles_ad_text("Subtitles downloaded from OpenSubtitles.org")
    assert not is_opensubtitles_ad_text("Halo, nama saya Frieren.")

    cues = [
        {"start": 1.0, "end": 4.0, "text": "Iklankan produk atau merek dagang Anda di sini"},
        {"start": 5.0, "end": 8.0, "text": "\u202aHalo dunia!\u202c"},
        {"start": 9.0, "end": 12.0, "text": "Subtitles by OpenSubtitles.com"},
    ]
    cleaned = strip_opensubtitles_ads(cues)
    assert len(cleaned) == 1
    assert cleaned[0]["text"] == "Halo dunia!"


def test_opensubtitles_candidate_scoring():
    """Pastikan rilis anime terpercaya dan nomor episode yang cocok mendapat skor tertinggi."""
    s_good = _score_subtitle_candidate("Frieren.S01E01.JAPANESE.WEBRip.NF.id.srt", ep=1, season=1, target_lang="id", cand_lang="id", downloads=500)
    s_diff_ep = _score_subtitle_candidate("Frieren.S01E02.WEBRip.id.srt", ep=1, season=1, target_lang="id", cand_lang="id", downloads=500)
    assert s_good > 150
    assert s_good > s_diff_ep


def test_smart_merge_optimal_offset_and_gap_filling():
    """Pastikan kalkulasi offset otomatis dan gap-filling (Signs/OP/ED) bekerja presisi."""
    # Subtitle bawaan stream anime (English)
    builtin_cues = [
        {"start": 10.0, "end": 13.0, "text": "Good morning."},
        {"start": 15.0, "end": 18.0, "text": "Where are we going?"},
        {"start": 25.0, "end": 28.0, "text": "[SIGN: Northern Territory]"},
        {"start": 30.0, "end": 33.0, "text": "It is cold outside."},
    ]
    # Subtitle OpenSubtitles (Indonesian) yang bergeser +2.0 detik dan tidak punya [SIGN]
    os_cues = [
        {"start": 8.0, "end": 11.0, "text": "Selamat pagi."},
        {"start": 13.0, "end": 16.0, "text": "Kita mau pergi ke mana?"},
        {"start": 28.0, "end": 31.0, "text": "Di luar dingin sekali."},
    ]

    offset = estimate_optimal_offset(builtin_cues, os_cues)
    assert abs(offset - 2.0) <= 0.25

    unmatched_idx, unmatched = find_unmatched_builtin_cues(builtin_cues, os_cues, offset=offset)
    assert len(unmatched_idx) == 1
    assert "[SIGN: Northern Territory]" in unmatched[0]["text"]

    translated_gaps = {unmatched_idx[0]: "[PAPAN: Wilayah Utara]"}
    merged, stats = merge_opensubtitles_with_builtin(
        builtin_cues=builtin_cues,
        os_cues=os_cues,
        merge_mode="hybrid",
        translated_gaps=translated_gaps,
        offset=offset,
    )

    assert len(merged) == 4
    texts = [c["text"] for c in merged]
    assert "Selamat pagi." in texts
    assert "Kita mau pergi ke mana?" in texts
    assert "[PAPAN: Wilayah Utara]" in texts
    assert "Di luar dingin sekali." in texts
    # Timestamp cue pertama snapped ke 10.0
    assert abs(merged[0]["start"] - 10.0) <= 0.05
    assert stats["gap_filled"] == 1


def test_smart_merge_bilingual_mode():
    """Pastikan mode bilingual menyusun OpenSubtitles di atas dan teks bawaan di bawah."""
    builtin = [{"start": 5.0, "end": 8.0, "text": "Let us go."}]
    os_sub = [{"start": 5.0, "end": 8.0, "text": "Ayo kita pergi."}]
    merged, stats = merge_opensubtitles_with_builtin(builtin, os_sub, merge_mode="bilingual")
    assert len(merged) == 1
    assert "Ayo kita pergi.\nLet us go." in merged[0]["text"]


def test_android_pip_dismiss_protection_in_code():
    """Pastikan PlayerActivity.java tidak memiliki early return pada onStop saat PiP ditutup."""
    player_java = (ROOT / "android" / "app" / "src" / "main" / "java" / "id" / "tatap" / "app" / "PlayerActivity.java").read_text(encoding="utf-8")

    # onStop tidak boleh me-return early isInPictureInPictureMode
    on_stop_pos = player_java.find("protected void onStop()")
    assert on_stop_pos > 0
    on_stop_block = player_java[on_stop_pos:on_stop_pos + 600]
    assert "isInPictureInPictureMode()) return;" not in on_stop_block
    assert "player.pause()" in on_stop_block

    # onPictureInPictureModeChanged mendeteksi isRestored
    pip_changed_pos = player_java.find("onPictureInPictureModeChanged(")
    assert pip_changed_pos > 0
    pip_block = player_java[pip_changed_pos:pip_changed_pos + 2500]
    assert "isRestored" in pip_block
    assert "finish()" in pip_block
