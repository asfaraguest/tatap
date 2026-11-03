"""Unit test custom prompt AI translate / fansub."""
import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from api import translate as T  # noqa: E402
import database as db_mod  # noqa: E402


def test_fansub_system_prompt_default():
    prompt = T._fansub_system_prompt("English", "id", "Indonesian")
    assert "You are an experienced anime fansub translator" in prompt or "TLC" in prompt or "FORMAT KELUARAN (WAJIB)" in prompt
    assert "INSTRUKSI KHUSUS & GAYA DARI PENGGUNA" not in prompt


def test_fansub_system_prompt_with_custom_prompt():
    custom = "Gunakan bahasa gaul Jakarta (lo/gue) dan pertahankan istilah 'nakama' serta nama jurus."
    prompt = T._fansub_system_prompt("English", "id", "Indonesian", custom_prompt=custom)
    assert "INSTRUKSI KHUSUS & GAYA DARI PENGGUNA (PRIORITAS TINGGI):" in prompt
    assert custom in prompt
    assert "FORMAT KELUARAN (WAJIB)" in prompt


def test_fansub_system_prompt_generic_with_custom_prompt():
    custom = "Always keep medieval knight honorifics."
    prompt = T._fansub_system_prompt("Japanese", "es", "Spanish", custom_prompt=custom)
    assert "INSTRUKSI KHUSUS & GAYA DARI PENGGUNA (PRIORITAS TINGGI):" in prompt
    assert custom in prompt
    assert "Output format (MANDATORY)" in prompt


@pytest.mark.asyncio
async def test_custom_prompt_settings_persistence(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_anime.db")
    monkeypatch.setattr(db_mod, "DB_PATH", test_db)
    await db_mod.init_db()

    # Default harus string kosong
    val = await db_mod.get_setting("translate_custom_prompt", "")
    assert val == ""

    # Simpan custom prompt
    custom_text = "Gunakan persona santai dan jangan terjemahkan kata 'Senpai'."
    await db_mod.set_setting("translate_custom_prompt", custom_text)

    # Verifikasi tersimpan
    val_after = await db_mod.get_setting("translate_custom_prompt", "")
    assert val_after == custom_text
