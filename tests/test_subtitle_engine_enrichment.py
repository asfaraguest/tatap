import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from api.translate import (
    clean_ass_tags,
    parse_vtt,
    merge_overlapping_cues,
    build_bilingual_vtt,
    _pre_normalize_en_slang,
    _preprocess_stutter_en,
    _postprocess_stutter_id,
    _sanitize_gtxplus_id,
    sanitize_cues_with_context,
)


def test_clean_ass_tags():
    raw = r"{\an8\pos(320,50)}Perhatian!{\i0}\NBaris kedua\hspasi"
    cleaned = clean_ass_tags(raw)
    assert cleaned == "Perhatian!\nBaris kedua spasi"


def test_parse_ass_dialogue():
    ass_text = """[Script Info]
Title: Test Fansub
ScriptType: v4.00+

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.50,Default,,0,0,0,,{\\an8}Tanda Peringatan
Dialogue: 0,0:00:01.02,0:00:03.50,Default,,0,0,0,,Apa yang kau lakukan?!\\NMundurlah!
Dialogue: 0,0:00:05.00,0:00:07.00,Default,,0,0,0,,Serangan terakhir!
"""
    cues = parse_vtt(ass_text)
    assert len(cues) == 2
    assert "Tanda Peringatan" in cues[0]["text"]
    assert "Apa yang kau lakukan?!" in cues[0]["text"]
    assert "Mundurlah!" in cues[0]["text"]
    assert cues[1]["text"] == "Serangan terakhir!"


def test_merge_overlapping_cues():
    raw_cues = [
        {"start": 10.0, "end": 12.0, "text": "Baris Atas"},
        {"start": 10.02, "end": 12.0, "text": "Baris Bawah"},
        {"start": 15.0, "end": 17.0, "text": "Baris Berikutnya"},
    ]
    merged = merge_overlapping_cues(raw_cues)
    assert len(merged) == 2
    assert merged[0]["text"] == "Baris Atas\nBaris Bawah"
    assert merged[1]["text"] == "Baris Berikutnya"


def test_build_bilingual_vtt():
    id_cues = [{"start": 1.0, "end": 3.0, "text": "Aku tidak akan menyerah!"}]
    en_cues = [{"start": 1.0, "end": 3.0, "text": "I won't give up!"}]
    vtt = build_bilingual_vtt(id_cues, en_cues)
    assert "WEBVTT" in vtt
    assert "Aku tidak akan menyerah!" in vtt
    assert "I won't give up!" in vtt


def test_preprocess_english_slang_and_idioms():
    assert "stop doing that" in _pre_normalize_en_slang("Knock it off!").lower()
    assert "fainted unconscious" in _pre_normalize_en_slang("He passed out cold!").lower()
    assert "listen to me until the end" in _pre_normalize_en_slang("Hear me out!").lower()
    assert "just in time" in _pre_normalize_en_slang("In the nick of time!").lower()
    assert "what are you" in _pre_normalize_en_slang("Whatcha doing?").lower()
    assert "daydreaming blankly" in _pre_normalize_en_slang("Stop spacing out!").lower()
    assert "reversed the situation" in _pre_normalize_en_slang("They turned the tables!").lower()


def test_stutter_preservation():
    en = "W-What are you doing?! S-Stop!"
    clean_en, had_leading = _preprocess_stutter_en(en)
    assert had_leading is True
    assert "What" in clean_en
    assert "W-What" not in clean_en

    tr_id = "Apa yang kau lakukan?! Berhenti!"
    stuttered_id = _postprocess_stutter_id(en, tr_id)
    assert stuttered_id.startswith("A-Apa")


def test_stage2_fansub_polish_and_lexicon():
    # Calque & question tags
    s1 = _sanitize_gtxplus_id("Itu tidak membuat masuk akal, bukan?")
    assert "tidak masuk akal" in s1.lower()
    assert ", kan?" in s1
    assert "bukan tandinganmu" in _sanitize_gtxplus_id("Dia di luar ligamu.").lower()
    assert "membalikkan keadaan" in _sanitize_gtxplus_id("Mereka membalikkan meja!").lower()

    # Honorifics & Cultivation terms
    polished = _sanitize_gtxplus_id("Onii-chan telah mencapai Inti Emas di istana belakang!")
    assert "Kakak" in polished
    assert "Inti Emas" in polished
    assert "istana dalam" in polished.lower()


def test_sliding_window_scene_context():
    cues = [
        {"start": 60.0, "end": 63.0, "text": "Yang Mulia, pasukan musuh telah tiba di perbatasan."},
        {"start": 63.5, "end": 66.0, "text": "Saya tidak akan mundur dari pertempuran ini."},
        {"start": 66.5, "end": 69.0, "text": "Apakah Anda ingin mengirim bantuan sekarang?"},
    ]
    res = sanitize_cues_with_context(cues, mode="gtx+", window=2, max_gap_sec=15.0)
    # Because cue[0] has "Yang Mulia" (formal/royal anchor), cues 1 and 2 within 15s should preserve formal register ("Saya"/"Anda")
    assert "saya" in res[1]["text"].lower()
    assert "nggak" not in res[1]["text"].lower()
    assert "anda" in res[2]["text"].lower()
