import pytest
from api.opensubtitles import (
    clean_anime_title_variations,
    clean_title_And_season,
    _extract_file_season_num,
    _extract_file_episode_num,
    _title_similarity,
    is_accurate_sub_title_match,
    _score_subtitle_candidate,
)


def test_clean_anime_title_variations():
    variations = clean_anime_title_variations("Solo Leveling Season 2: Arise from the Shadow", "solo-leveling-season-2-arise-from-the-shadow")
    assert "Solo Leveling Season 2: Arise from the Shadow" in variations
    assert "Solo Leveling" in variations

    variations_sub = clean_anime_title_variations("Sousou no Frieren (Frieren: Beyond Journey's End)")
    assert any("Sousou no Frieren" in v for v in variations_sub)


def test_extract_file_season_and_episode():
    # Season extraction
    assert _extract_file_season_num("[SubsPlease] Solo Leveling S2 - 05.mkv") == 2
    assert _extract_file_season_num("Boku no Hero Academia 2nd Season - 14.srt") == 2
    assert _extract_file_season_num("[Judas] Shingeki no Kyojin Season 3 - 01.mkv") == 3
    assert _extract_file_season_num("DanMachi III - 04.srt") == 3
    assert _extract_file_season_num("Frieren - 08.srt") == 0

    # Episode extraction
    assert _extract_file_episode_num("[Erai-raws] One Piece - 108.srt") == 108
    assert _extract_file_episode_num("[SubsPlease] Solo Leveling - 08.mkv") == 8
    assert _extract_file_episode_num("Naruto S01E08.srt") == 8
    assert _extract_file_episode_num("Boruto - Naruto Next Generations - 108.srt") == 108


def test_spinoff_rejection_naruto_vs_boruto():
    # Naruto vs Boruto offshoot check
    assert not is_accurate_sub_title_match(
        anime_title="Naruto",
        candidate_title="Boruto - Naruto Next Generations - 08.srt",
        target_season=1,
        target_ep=8,
    )

    # When query is Boruto, Boruto should match
    assert is_accurate_sub_title_match(
        anime_title="Boruto: Naruto Next Generations",
        candidate_title="Boruto - Naruto Next Generations - 08.srt",
        target_season=1,
        target_ep=8,
    )


def test_season_mismatch_rejection():
    # User is on Season 2 Ep 5, subtitle candidate is for Season 1 Ep 5
    assert not is_accurate_sub_title_match(
        anime_title="Solo Leveling Season 2",
        candidate_title="[Judas] Solo Leveling - S01E05.mkv",
        target_season=2,
        target_ep=5,
    )

    # User is on Season 1 Ep 5, subtitle candidate is for Season 2 Ep 5
    assert not is_accurate_sub_title_match(
        anime_title="Solo Leveling",
        candidate_title="[SubsPlease] Solo Leveling S2 - 05.mkv",
        target_season=1,
        target_ep=5,
    )

    # Correct season match
    assert is_accurate_sub_title_match(
        anime_title="Solo Leveling Season 2: Arise from the Shadow",
        candidate_title="[SubsPlease] Solo Leveling S2 - 05.mkv",
        target_season=2,
        target_ep=5,
    )


def test_episode_mismatch_rejection_no_partial_regex_leak():
    # Episode 108 should NEVER match Episode 8
    assert not is_accurate_sub_title_match(
        anime_title="One Piece",
        candidate_title="[Erai-raws] One Piece - 108.srt",
        target_season=1,
        target_ep=8,
    )

    # Episode 8 should match Episode 8
    assert is_accurate_sub_title_match(
        anime_title="One Piece",
        candidate_title="[Erai-raws] One Piece - 08.srt",
        target_season=1,
        target_ep=8,
    )


def test_score_subtitle_candidate():
    # Mismatched season should return -999
    sc_season_mismatch = _score_subtitle_candidate(
        filename="[Judas] Solo Leveling - S01E05.mkv",
        ep=5,
        season=2,
        target_lang="id",
        cand_lang="id",
    )
    assert sc_season_mismatch < 0

    # Mismatched episode (e.g. 108 instead of 8) should return -999
    sc_ep_mismatch = _score_subtitle_candidate(
        filename="[Erai-raws] One Piece - 108.srt",
        ep=8,
        season=1,
        target_lang="id",
        cand_lang="id",
    )
    assert sc_ep_mismatch < 0

    # Matching season and episode should receive positive high score
    sc_match = _score_subtitle_candidate(
        filename="[SubsPlease] Solo Leveling S2 - 05 (1080p).mkv",
        ep=5,
        season=2,
        target_lang="id",
        cand_lang="id",
        downloads=500,
    )
    assert sc_match >= 200


@pytest.mark.asyncio
async def test_opensubtitles_merge_job_mismatch_fallback_to_gtx(monkeypatch):
    import main

    # Mock fetch sub text returning sample english VTT cues
    sample_vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello, world!\n"
    async def mock_fetch(url, ref):
        return sample_vtt
    monkeypatch.setattr(main, "_fetch_sub_text", mock_fetch)

    # Mock animetosho returning nothing
    monkeypatch.setattr("api.animetosho.search_animetosho_indonesian", lambda **kw: [])

    # Mock opensubtitles returning an unmatched anime or wrong season
    def mock_os_search(**kw):
        return [
            {
                "id": "123",
                "file_id": "123",
                "filename": "[Judas] Boruto - Naruto Next Generations - 08.srt",
                "lang": "id",
                "url": "http://example.com/sub.srt",
                "score": 100,
            }
        ]
    monkeypatch.setattr("api.opensubtitles.search_opensubtitles", mock_os_search)

    # Mock gtx+ translation
    async def mock_translate(cues, src, tgt, requested_mode="gtx+"):
        return {"cues": [{"start": 1.0, "end": 3.0, "text": "Halo, dunia!"}], "level": "gtx+"}
    monkeypatch.setattr(main, "_translate_with_fallback", mock_translate)

    # Execute _opensubtitles_merge_sub_job for Naruto Season 1 Episode 8
    new_text, tier = await main._opensubtitles_merge_sub_job(
        url="http://example.com/stream.vtt",
        referer="http://example.com",
        src="en",
        lang="id",
        title="Naruto",
        slug="naruto",
        ep=8,
        os_file_id="",
        is_dual=False,
        cache_key="",
        fallback_key_gtxplus="",
        season=1,
    )

    # Should reject Boruto and cleanly fallback to Smart GTX+
    assert tier["level"] == "os_fallback_gtx+"
    assert "Halo, dunia!" in new_text


@pytest.mark.asyncio
async def test_subtitle_endpoint_accepts_seasonal_string_without_422(monkeypatch):
    from httpx import AsyncClient, ASGITransport
    import main

    async def mock_fetch(url, ref):
        return "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello!\n"
    monkeypatch.setattr(main, "_fetch_sub_text", mock_fetch)

    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test endpoint with non-numeric season string like "Spring 2019"
        res = await client.get("/api/subtitles/opensubtitles?title=Demon%20Slayer&ep=1&season=Spring%202019")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True

        res_sub = await client.get("/api/player/sub?url=http://example.com/sub.vtt&referer=http://example.com&lang=id&mode=os_merge&title=Demon%20Slayer&ep=1&season=Spring%202019")
        # Must not be 422 Unprocessable Entity
        assert res_sub.status_code != 422


def test_malay_subtitle_rejection_for_indonesian_target():
    # 1. Candidate tagged as Malay (ms, may, msa) or filename containing Malay keywords must be rejected
    sc_malay_cand = _score_subtitle_candidate(
        filename="Demon Slayer - 01 (MAY).srt",
        ep=1,
        season=1,
        target_lang="id",
        cand_lang="ms",
    )
    assert sc_malay_cand == -999

    sc_malay_fn = _score_subtitle_candidate(
        filename="[Bahasa Melayu] Naruto - 01.srt",
        ep=1,
        season=1,
        target_lang="id",
        cand_lang="id",
    )
    assert sc_malay_fn == -999

    # 2. AnimeTosho label check
    from api.animetosho import _is_indonesian_subtitle_label
    assert not _is_indonesian_subtitle_label("[may, ass]")
    assert not _is_indonesian_subtitle_label("Crunchyroll [may, eng]")
    assert not _is_indonesian_subtitle_label("Malay Subtitle")
    assert _is_indonesian_subtitle_label("[ind, ass]")
    assert _is_indonesian_subtitle_label("Indonesian")
    assert _is_indonesian_subtitle_label("cr [ind, ass]")


def test_malay_to_indonesian_lexicon_normalization():
    from api.translate import apply_universal_lexicon_id

    # Normal Malay sentence should become natural Indonesian
    malay_text = "Awak semua jangan risau, kerana kami takkan bercakap pasal tu!"
    normalized = apply_universal_lexicon_id(malay_text)
    assert "kalian semua" in normalized.lower()
    assert "jangan khawatir" in normalized.lower()
    assert "karena" in normalized.lower()
    assert "tidak akan" in normalized.lower()
    assert "soal itu" in normalized.lower()
    assert "awak" not in normalized.lower()
    assert "risau" not in normalized.lower()
    assert "pasal" not in normalized.lower()

    # Awak kapal (ship crew) must NOT be replaced with kamu kapal
    crew_text = "Semua awak kapal bersiap di pos masing-masing!"
    normalized_crew = apply_universal_lexicon_id(crew_text)
    assert "awak kapal" in normalized_crew.lower()

    # Time phrases
    time_text = "Tunggu sekejap, dia orang akan sampai sekejap lagi."
    normalized_time = apply_universal_lexicon_id(time_text)
    assert "tunggu sebentar" in normalized_time.lower()
    assert "mereka" in normalized_time.lower()
    assert "sebentar lagi" in normalized_time.lower()
