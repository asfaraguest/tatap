import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import main

def test_extract_season_from_title():
    assert main._extract_season_from_title("Sword Art Online") == 1
    assert main._extract_season_from_title("Sword Art Online II") == 2
    assert main._extract_season_from_title("Sword Art Online Season 3") == 3
    assert main._extract_season_from_title("Overlord IV") == 4
    assert main._extract_season_from_title("Bleach: Thousand-Year Blood War") == 1

def test_title_match_score_precision():
    # 1. Exact match
    score_exact = main._calculate_title_match_score("Sword Art Online", "Sword Art Online")
    assert score_exact == 1.0

    # 2. Season isolation: SAO II should NOT match SAO S1
    score_sao2_vs_sao1 = main._calculate_title_match_score("Sword Art Online II", "Sword Art Online")
    assert score_sao2_vs_sao1 == 0.0

    # 3. Spurious match prevention: SAO should NOT match Long Sword
    score_sao_vs_long_sword = main._calculate_title_match_score("Sword Art Online", "Long Sword")
    assert score_sao_vs_long_sword < 0.30

    # 4. Spurious match prevention: Bleach should NOT match The Dull Sword (1917)
    score_bleach_vs_dull_sword = main._calculate_title_match_score("Bleach: The Sealed Sword Frenzy", "The Dull Sword")
    assert score_bleach_vs_dull_sword < 0.30

    # 5. Distinct arc isolation: SAO Alicization vs plain SAO
    score_alicization_vs_sao = main._calculate_title_match_score("Sword Art Online: Alicization", "Sword Art Online")
    assert score_alicization_vs_sao < 0.60

    # 6. Correct arc matching: SAO Alicization vs SAO Alicization
    score_alicization_vs_alicization = main._calculate_title_match_score("Sword Art Online: Alicization", "Sword Art Online: Alicization")
    assert score_alicization_vs_alicization >= 0.90

@pytest.mark.asyncio
async def test_enrich_search_results_with_metadata_logic():
    items = [
        {"id": "sao-1", "title": "Sword Art Online"},
        {"id": "sao-2", "title": "Sword Art Online II"},
        {"id": "bleach-sword", "title": "Bleach: The Sealed Sword Frenzy"}
    ]
    # Simulate AniList returning SAO 1, SAO II, and The Dull Sword (1917)
    al_meta_list = [
        {
            "id": 11757,
            "title": {"english": "Sword Art Online", "romaji": "Sword Art Online"},
            "season": "SUMMER",
            "seasonYear": 2012
        },
        {
            "id": 20594,
            "title": {"english": "Sword Art Online II", "romaji": "Sword Art Online II"},
            "season": "SUMMER",
            "seasonYear": 2014
        },
        {
            "id": 6654,
            "title": {"english": "The Dull Sword", "romaji": "Namakura Gatana"},
            "season": None,
            "seasonYear": 1917
        }
    ]

    await main._enrich_search_results_with_metadata(items, al_meta_list)

    # SAO 1 must get 2012
    assert items[0].get("year") == 2012
    assert items[0].get("season") == "Summer 2012"

    # SAO 2 must get 2014, NOT 2012
    assert items[1].get("year") == 2014
    assert items[1].get("season") == "Summer 2014"

    # Bleach must NOT get 1917
    assert items[2].get("year") is None or items[2].get("year") == 0
    assert items[2].get("season") != "1917"
