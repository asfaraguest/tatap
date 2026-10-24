import sys
import os
import lzma
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from api.animetosho import (
    _clean_anime_title,
    _is_indonesian_subtitle_label,
    search_animetosho_indonesian,
    download_animetosho_sub_text,
)
from api.translate import (
    parse_vtt,
    build_vtt,
    apply_universal_lexicon_id,
    automate_opensubtitles_pronouns,
    merge_opensubtitles_with_builtin,
)


def test_clean_anime_title():
    t1 = _clean_anime_title("Sousou no Frieren (Season 2) [1080p]", "sousou-no-frieren-s2-episode-1")
    assert "Sousou no Frieren" in t1[0]

    t2 = _clean_anime_title("Solo Leveling Season 2", "solo-leveling-season-2")
    assert "Solo Leveling" in t2[0]


def test_is_indonesian_subtitle_label():
    assert _is_indonesian_subtitle_label("CR [ind, ASS]") is True
    assert _is_indonesian_subtitle_label("[ind, SRT]") is True
    assert _is_indonesian_subtitle_label("Indonesian Subtitle") is True
    assert _is_indonesian_subtitle_label("Bahasa Indonesia Fansub") is True
    assert _is_indonesian_subtitle_label("CR [may, ASS]") is True
    assert _is_indonesian_subtitle_label("English [eng, ASS]") is False
    assert _is_indonesian_subtitle_label("Spanish [spa, ASS]") is False
    assert _is_indonesian_subtitle_label("Japanese [jpn, ASS]") is False


def test_animetosho_lzma_decompress(monkeypatch):
    dummy_ass = b"[Events]\nDialogue: 0,0:00:01.00,0:00:04.00,Default,,0,0,0,,Halo dunia Satisfy!\n"
    compressed_xz = lzma.compress(dummy_ass)

    # Mock _http_get_raw to return compressed XZ
    from api import animetosho
    monkeypatch.setattr(animetosho, "_http_get_raw", lambda url, **kwargs: compressed_xz)

    sub_txt = download_animetosho_sub_text("https://animetosho.net/download/123/subs/file/456")
    assert "Halo dunia Satisfy!" in sub_txt

    cues = parse_vtt(sub_txt)
    assert len(cues) == 1
    assert cues[0]["start"] == 1.0
    assert cues[0]["end"] == 4.0
    assert "Satisfy" in cues[0]["text"]


def test_smart_pipeline_animetosho_with_lexicon_and_scene_detector():
    raw_sub = """WEBVTT

00:00:01.000 --> 00:00:03.000
Saya harus naik level di game Satisfy ini.

00:00:03.500 --> 00:00:06.000
Kau pikir kamu bisa mengalahkanku dengan armor itu?
"""
    cues = parse_vtt(raw_sub)

    # 1. Scene detector
    cues_pronouns = automate_opensubtitles_pronouns(cues, target_lang="id")
    # Kasus dialog kasual dengan 'kau' / 'kamu' -> 'saya' otomatis berubah menjadi 'aku'
    assert "Aku harus naik level" in cues_pronouns[0]["text"]

    # 2. Universal Lexicon
    for c in cues_pronouns:
        c["text"] = apply_universal_lexicon_id(c["text"])

    assert "Satisfy" in cues_pronouns[0]["text"]
    assert "puaskan" not in cues_pronouns[0]["text"].lower()

    # 3. Merge with builtin
    builtin_cues = [
        {"start": 1.0, "end": 3.0, "text": "I must level up in the game Satisfy."},
        {"start": 7.0, "end": 9.0, "text": "Sign: Kingdom of Eternal"},
    ]
    translated_gaps = {1: "Tanda: Kerajaan Eternal"}

    merged, stats = merge_opensubtitles_with_builtin(
        builtin_cues=builtin_cues,
        os_cues=cues_pronouns,
        merge_mode="hybrid",
        translated_gaps=translated_gaps,
        target_lang="id",
    )

    assert stats["gap_filled"] == 1
    assert stats["snapped"] >= 1
    vtt_out = build_vtt(merged)
    assert "Kerajaan Eternal" in vtt_out
    assert "Satisfy" in vtt_out


def test_search_animetosho_season_extraction(monkeypatch):
    captured_queries = []

    def mock_http_get_raw(url, **kwargs):
        captured_queries.append(url)
        return b"[]"

    from api import animetosho
    monkeypatch.setattr(animetosho, "_http_get_raw", mock_http_get_raw)

    search_animetosho_indonesian("Solo Leveling Season 2", "solo-leveling-season-2", ep=3, season=1)
    assert any("S02E03" in q for q in captured_queries)
