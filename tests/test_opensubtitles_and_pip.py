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
    apply_universal_lexicon_id,
    automate_opensubtitles_pronouns,
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


def test_smart_merge_clean_single_language():
    """Pastikan merge menghasilkan subtitle tunggal bersih (non-bilingual) sesuai preferensi pengguna."""
    builtin = [{"start": 5.0, "end": 8.0, "text": "Let us go."}]
    os_sub = [{"start": 5.0, "end": 8.0, "text": "Ayo kita pergi."}]
    merged, stats = merge_opensubtitles_with_builtin(builtin, os_sub, merge_mode="hybrid")
    assert len(merged) == 1
    assert merged[0]["text"] == "Ayo kita pergi."


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


def test_opensubtitles_universal_lexicon_and_tag_cleaning():
    """Pastikan Kamus Istilah Anime Universal diterapkan pada OpenSubtitles merge,
    tag ASS & HTML dibersihkan, dan persona asli fansub (saya/Anda) tetap terjaga."""
    # 1. Test direct apply_universal_lexicon_id
    raw_anime_term = "Kita harus pergi ke penjara bawah tanah dan mendaftar di serikat petualang."
    normalized = apply_universal_lexicon_id(raw_anime_term)
    assert "dungeon" in normalized
    assert "guild petualang" in normalized

    # Pastikan persona formal/sopan tetap terjaga (TIDAK diubah menjadi aku/kamu/nggak)
    polite_text = "Saya tidak tahu apa yang Anda bicarakan."
    assert apply_universal_lexicon_id(polite_text) == "Saya tidak tahu apa yang Anda bicarakan."

    # 2. Test inside merge_opensubtitles_with_builtin
    builtin_cues = [
        {"start": 10.0, "end": 14.0, "text": "Let's explore the dungeon."},
    ]
    os_cues_dirty = [
        {"start": 10.0, "end": 14.0, "text": "{\\an8}<i>Ayo jelajahi</i> penjara bawah tanah bersama serikat petualang &amp; kumpulkan energi spiritual.\\N{\\pos(192,200)}Saya siap, Tuan."},
    ]

    merged, stats = merge_opensubtitles_with_builtin(
        builtin_cues=builtin_cues,
        os_cues=os_cues_dirty,
        merge_mode="hybrid",
        target_lang="id",
    )

    assert len(merged) == 1
    cleaned_txt = merged[0]["text"]

    # Tag ASS dan HTML harus bersih
    assert "{\\an8}" not in cleaned_txt
    assert "{\\pos" not in cleaned_txt
    assert "<i>" not in cleaned_txt
    assert "&amp;" not in cleaned_txt
    assert "\\N" not in cleaned_txt

    # Istilah anime harus ternormalisasi
    assert "dungeon" in cleaned_txt
    assert "guild petualang" in cleaned_txt
    assert "qi spiritual" in cleaned_txt.lower()

    # Persona sopan asli tetap terjaga
    assert "Saya siap, Tuan." in cleaned_txt


def test_game_titles_anti_literal_protection():
    """Pastikan judul game anime tidak diterjemahkan mentah dan dipulihkan ke nama resminya."""
    # Satisfy (Overgeared) - variasi Puaskan / Memuaskan / Puas
    assert "game Satisfy" in apply_universal_lexicon_id("Aku bermain game memuaskan setiap malam.")
    assert "Di Satisfy" in apply_universal_lexicon_id("Di memuaskan, dia adalah pemain legendaris.")
    assert "Satisfy adalah" in apply_universal_lexicon_id("Memuaskan adalah game realitas virtual terbaik.")
    assert "Satisfy, game realitas virtual" in apply_universal_lexicon_id("Puaskan, game realitas virtual terhebat di dunia.")
    assert "Satisfy, game realitas virtual" in apply_universal_lexicon_id("Memuaskan, game realitas virtual terhebat di dunia.")
    assert "Satisfy, game realitas virtual" in apply_universal_lexicon_id("Puas, game realitas virtual terhebat di dunia.")
    assert "Berita Satisfy!" in apply_universal_lexicon_id("- Berita Memuaskan! Hari ini, semua orang")
    assert "Berita Satisfy!" in apply_universal_lexicon_id("Berita yang Memuaskan!")
    assert "Satisfy Times" in apply_universal_lexicon_id("Memuaskan Times")
    assert "Satisfy!" in apply_universal_lexicon_id("Puaskan!")
    assert "Satisfy!" in apply_universal_lexicon_id("Memuaskan!")
    assert "Satisfy! Siap?" in apply_universal_lexicon_id("Puaskan! Siap?")
    assert "Bukan Satisfy!" in apply_universal_lexicon_id("Tidak Memuaskan!")
    assert "Bukan Satisfy!" in apply_universal_lexicon_id("Bukan Memuaskan!")
    assert "Mengakses Satisfy." in apply_universal_lexicon_id("Mengakses Puas.")
    assert "Satisfy pengguna pertama" in apply_universal_lexicon_id("Puaskan pengguna pertama dengan dua pekerjaan.")

    # SAO, GGO, ShanFro, Full Dive, Glory
    assert "Sword Art Online" in apply_universal_lexicon_id("Dia terjebak di seni pedang daring.")
    assert "Gun Gale Online" in apply_universal_lexicon_id("Turnamen badai senjata daring akan dimulai.")
    assert "Shangri-La Frontier" in apply_universal_lexicon_id("Perbatasan Shangri-La sangat menantang.")
    assert "Full Dive" in apply_universal_lexicon_id("Teknologi penyelaman penuh sangat canggih.")
    assert "pemain pro Glory" in apply_universal_lexicon_id("Ye Xiu adalah pemain pro kejayaan.")
    assert "Brain Burst" in apply_universal_lexicon_id("Program ledakan otak terpasang di neuro-linker.")


def test_overgeared_lexicon_enrichment():
    """Pastikan istilah khusus anime Overgeared (Ep 1-4) dinormalisasi akurat."""
    t1 = apply_universal_lexicon_id("Shin Youngwoo adalah Pagma's Successor yang baru.")
    assert "Keturunan Pagma" in t1

    t2 = apply_universal_lexicon_id("Kami membutuhkan Blue Orichalcum dan Pavranium untuk menempanya.")
    assert "Orichalcum Biru" in t2
    assert "Pavranium" in t2

    t3 = apply_universal_lexicon_id("Tzedakah Guild diundang oleh Earl Steim ke Winston Village.")
    assert "Guild Tzedakah" in t3
    assert "Earl Steim" in t3
    assert "Desa Winston" in t3

    t4 = apply_universal_lexicon_id("Paus Drevigo mengincar Kitab Langka Pagma.")
    assert "Paus Drevigo" in t4
    assert "Kitab Langka Pagma" in t4


def test_automated_pronoun_disambiguation_saya_vs_aku():
    """Pastikan otomasi kata ganti saya vs aku bekerja presisi sesuai konteks adegan."""
    # 1. Monolog batin & kemarahan pertarungan beralih ke aku / kau
    casual_cues = [
        {"start": 10.0, "end": 12.0, "text": "Sialan! Saya tidak percaya NPC ini memberikan quest mustahil!"},
        {"start": 13.0, "end": 15.0, "text": "(Saya harus mengumpulkan uang untuk membayar utang.)"},
        {"start": 16.0, "end": 18.0, "text": "Beraninya Anda menghina saya, bajingan!"},
        {"start": 19.0, "end": 21.0, "text": "Menurut saya, ini pedang terbaik milik saya."},
    ]
    res_casual = automate_opensubtitles_pronouns(casual_cues, target_lang="id")
    txts_casual = [c["text"] for c in res_casual]

    assert "Aku nggak percaya" in txts_casual[0]
    assert "(Aku harus mengumpulkan uang" in txts_casual[1]
    assert "Beraninya Kau menghina aku" in txts_casual[2]
    assert "Menurutku" in txts_casual[3]
    assert "milikku" in txts_casual[3]

    # 2. Adegan formal menghadap bangsawan / raja / wawancara siaran TV tetap mempertahankan saya / Anda
    formal_cues = [
        {"start": 50.0, "end": 53.0, "text": "Yang Mulia Paduka Earl Steim, saya datang menghadap untuk melapor."},
        {"start": 54.0, "end": 57.0, "text": "Saya telah menyelesaikan tugas yang Anda berikan."},
        {"start": 58.0, "end": 61.0, "text": "Siaran langsung: Bersama saya pembawa acara siaran Satisfy."},
    ]
    res_formal = automate_opensubtitles_pronouns(formal_cues, target_lang="id")
    txts_formal = [c["text"] for c in res_formal]

    assert "Paduka Earl Steim, saya datang" in txts_formal[0]
    assert "Saya telah menyelesaikan tugas yang Anda berikan" in txts_formal[1]
    assert "Bersama saya pembawa acara" in txts_formal[2]
