import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from api import hianime as hi


def test_label_to_lang_european_and_asian_languages():
    """Memastikan _label_to_lang memetakan seluruh varian bahasa Eropa & Asia ke kode ISO-639-1 yang tepat."""
    test_cases = {
        "Czech": "cs",
        "czech": "cs",
        "cze": "cs",
        "ces": "cs",
        "Danish": "da",
        "Dutch": "nl",
        "Finnish": "fi",
        "Greek": "el",
        "Hungarian": "hu",
        "Norwegian": "no",
        "Polish": "pl",
        "Romanian": "ro",
        "Slovak": "sk",
        "Swedish": "sv",
        "Malay": "ms",
        "Tagalog": "tl",
        "Filipino": "tl",
        "English": "en",
        "English [Full]": "en",
        "Indonesian": "id",
        "Bahasa": "id",
        "Japanese": "ja",
        "Arabic": "ar",
    }
    for label, expected in test_cases.items():
        assert hi._label_to_lang(label) == expected, f"Gagal memetakan label '{label}' -> '{expected}'"


def test_zokoanime_heavenly_delusion_ep8_subtitle_selection():
    """Simulasi persis payload raw tracks ZokoAnime Episode 8-13 Heavenly Delusion.
    Upstream CDN secara keliru memberikan dummy 'lang: en' pada hampir semua track.
    Tatap wajib menetapkan 'English' asli sebagai default track dan memetakan Czech ke 'cs'.
    """
    raw_tracks = [
        {"kind": "captions", "file": "https://cdn.example.com/sub/zh.vtt", "label": "Chinese", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/cs.vtt", "label": "Czech", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/da.vtt", "label": "Danish", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/nl.vtt", "label": "Dutch", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/en.vtt", "label": "English", "lang": "en", "default": True},
        {"kind": "captions", "file": "https://cdn.example.com/sub/en2.vtt", "label": "English 2", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/fi.vtt", "label": "Finnish", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/fr.vtt", "label": "French", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/de.vtt", "label": "German", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/el.vtt", "label": "Greek", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/hu.vtt", "label": "Hungarian", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/it.vtt", "label": "Italian", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/ja.vtt", "label": "Japanese", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/ko.vtt", "label": "Korean", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/no.vtt", "label": "Norwegian", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/pl.vtt", "label": "Polish", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/pt.vtt", "label": "Portuguese", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/ro.vtt", "label": "Romanian", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/ru.vtt", "label": "Russian", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/sk.vtt", "label": "Slovak", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/es.vtt", "label": "Spanish", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/sv.vtt", "label": "Swedish", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/th.vtt", "label": "Thai", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/tr.vtt", "label": "Turkish", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/vi.vtt", "label": "Vietnamese", "lang": "en", "default": False},
    ]

    normalized = hi._normalize_subtitles(raw_tracks)
    assert len(normalized) == 25

    # 1. Cari default track: WAJIB English (bukan Czech!)
    default_tracks = [t for t in normalized if t.get("default")]
    assert len(default_tracks) == 1
    def_track = default_tracks[0]

    assert def_track["label"] == "English"
    assert def_track["lang"] == "en"
    assert def_track["url"] == "https://cdn.example.com/sub/en.vtt"

    # 2. Pastikan Czech dinormalisasi dengan lang 'cs', BUKAN 'en'
    czech_track = next(t for t in normalized if t["label"] == "Czech")
    assert czech_track["lang"] == "cs"
    assert not czech_track.get("default")

    # 3. Pastikan Danish dinormalisasi dengan lang 'da', BUKAN 'en'
    danish_track = next(t for t in normalized if t["label"] == "Danish")
    assert danish_track["lang"] == "da"
    assert not danish_track.get("default")


def test_normalize_subtitles_native_indonesian_priority():
    """Jika track Indonesian tersedia, prioritaskan Indonesian di atas English."""
    raw_tracks = [
        {"kind": "captions", "file": "https://cdn.example.com/sub/en.vtt", "label": "English", "lang": "en", "default": True},
        {"kind": "captions", "file": "https://cdn.example.com/sub/id.vtt", "label": "Indonesian", "lang": "id", "default": False},
    ]
    normalized = hi._normalize_subtitles(raw_tracks)
    def_track = next(t for t in normalized if t.get("default"))
    assert def_track["label"] == "Indonesian"
    assert def_track["lang"] == "id"


def test_normalize_subtitles_exact_english_priority_over_variant():
    """Pastikan 'English' exact diprioritaskan di atas 'English 2' bahkan jika English 2 berada di urutan atas."""
    raw_tracks = [
        {"kind": "captions", "file": "https://cdn.example.com/sub/en2.vtt", "label": "English 2", "lang": "en", "default": False},
        {"kind": "captions", "file": "https://cdn.example.com/sub/en.vtt", "label": "English", "lang": "en", "default": False},
    ]
    normalized = hi._normalize_subtitles(raw_tracks)
    def_track = next(t for t in normalized if t.get("default"))
    assert def_track["label"] == "English"
    assert def_track["url"] == "https://cdn.example.com/sub/en.vtt"


def test_normalize_subtitles_avoid_arabic_as_default():
    """Pastikan track Arabic tidak pernah dipilih sebagai default jika ada track lain."""
    raw_tracks = [
        {"kind": "captions", "file": "https://cdn.example.com/sub/ar.vtt", "label": "Arabic", "lang": "ar", "default": True},
        {"kind": "captions", "file": "https://cdn.example.com/sub/fr.vtt", "label": "French", "lang": "fr", "default": False},
    ]
    normalized = hi._normalize_subtitles(raw_tracks)
    def_track = next(t for t in normalized if t.get("default"))
    assert def_track["label"] == "French"
    assert def_track["lang"] == "fr"


def test_has_valid_subtitles_validator():
    """Memastikan _has_valid_subtitles mendeteksi subtitle cacat/angka (seperti bookmark '28') dan mengenali URL valid."""
    from main import _has_valid_subtitles

    # Kasus invalid / poisoned:
    assert _has_valid_subtitles({}) is False
    assert _has_valid_subtitles({"subtitles": []}) is False
    assert _has_valid_subtitles({"subtitles": [], "sub": ""}) is False
    assert _has_valid_subtitles({"subtitles": [], "sub": "28"}) is False # Bentrokan jumlah episode bookmark
    assert _has_valid_subtitles({"subtitles": [{"url": ""}], "sub": None}) is False
    assert _has_valid_subtitles({"subtitles": None, "sub": "12/24"}) is False

    # Kasus valid:
    assert _has_valid_subtitles({"subtitles": [{"url": "https://cdn.example.com/sub.vtt", "lang": "en"}]}) is True
    assert _has_valid_subtitles({"subtitles": [{"url": "http://127.0.0.1:8767/api/player/sub"}]}) is True
    assert _has_valid_subtitles({"subtitles": [{"url": "/api/player/sub?url=abc"}]}) is True
    assert _has_valid_subtitles({"sub": "https://cdn.example.com/ep1.vtt"}) is True
    assert _has_valid_subtitles({"sub": "/api/player/sub?url=xyz"}) is True
