"""Tests for analysis server functionality."""

import pytest
from unittest.mock import patch


async def test_calculate_mana_curve(client, mock_scryfall_collection_response):
    """Test mana curve calculation."""
    with patch("tools.analysis_server.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (
            mock_scryfall_collection_response["data"],
            []
        )
        
        result = await client.call_tool(
            "analysis_calculate_mana_curve",
            {"card_names": ["Lightning Bolt", "Counterspell"]}
        )
        
        response = result[0].text
        assert "**Mana Curve:**" in response
        assert "CMC 1.0: 1" in response  # Lightning Bolt
        assert "CMC 2.0: 1" in response  # Counterspell


async def test_calculate_mana_curve_with_not_found(client):
    """Test mana curve calculation with some cards not found."""
    with patch("tools.analysis_server.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (
            [{
                "name": "Lightning Bolt",
                "cmc": 1.0
            }],
            ["Fake Card"]
        )
        
        result = await client.call_tool(
            "analysis_calculate_mana_curve",
            {"card_names": ["Lightning Bolt", "Fake Card"]}
        )
        
        response = result[0].text
        assert "**Mana Curve:**" in response
        assert "CMC 1.0: 1" in response
        assert "**Cards Not Found:** Fake Card" in response


async def test_analyze_lands(client, mock_scryfall_land_response):
    """Test land analysis functionality."""
    with patch("tools.analysis_server.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (
            mock_scryfall_land_response["data"],
            []
        )
        
        result = await client.call_tool(
            "analysis_analyze_lands",
            {"card_names": ["Command Tower", "Sacred Foundry"]}
        )
        
        response = result[0].text
        assert "**Land Analysis:**" in response
        assert "Total Lands: 2" in response
        assert "White mana sources:" in response
        assert "Red mana sources:" in response


async def test_analyze_color_identity(client, mock_scryfall_collection_response):
    """Test color identity analysis."""
    with patch("tools.analysis_server.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (
            mock_scryfall_collection_response["data"],
            []
        )
        
        result = await client.call_tool(
            "analysis_analyze_color_identity",
            {"card_names": ["Lightning Bolt", "Counterspell"]}
        )
        
        response = result[0].text
        assert "**Color Identity Analysis:**" in response
        assert "Total Cards Analyzed: 2" in response
        assert "Red: 1" in response
        assert "Blue: 1" in response


async def test_analyze_mana_requirements(client):
    """Test mana requirements analysis."""
    mock_cards = [
        {
            "name": "Lightning Bolt",
            "type_line": "Instant",
            "color_identity": ["R"],
            "oracle_text": "Lightning Bolt deals 3 damage to any target."
        },
        {
            "name": "Mountain",
            "type_line": "Basic Land — Mountain", 
            "color_identity": [],
            "oracle_text": "{T}: Add {R}."
        }
    ]
    
    with patch("tools.analysis_server.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (mock_cards, [])
        
        result = await client.call_tool(
            "analysis_analyze_mana_requirements",
            {"card_names": ["Lightning Bolt", "Mountain"]}
        )
        
        response = result[0].text
        assert "**Mana Requirements vs Production Analysis:**" in response
        assert "Total Cards: 2 (Spells: 1, Lands: 1)" in response
        assert "Red:" in response


async def test_analyze_card_types(client, mock_scryfall_collection_response):
    """Test card type analysis."""
    with patch("tools.analysis_server.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (
            mock_scryfall_collection_response["data"],
            []
        )
        
        result = await client.call_tool(
            "analysis_analyze_card_types",
            {"card_names": ["Lightning Bolt", "Counterspell"]}
        )
        
        response = result[0].text
        assert "**Card Type Distribution:**" in response
        assert "Total Cards Analyzed: 2" in response
        assert "Instant: 2 (100.0%)" in response


async def test_empty_card_names_analysis_tools(client):
    """Test all analysis tools handle empty input correctly."""
    tools = [
        "analysis_calculate_mana_curve",
        "analysis_analyze_lands", 
        "analysis_analyze_color_identity",
        "analysis_analyze_mana_requirements",
        "analysis_analyze_card_types"
    ]
    
    for tool_name in tools:
        result = await client.call_tool(tool_name, {"card_names": []})
        response = result[0].text
        assert response == "No card names provided.", f"Tool {tool_name} failed empty input test"


async def test_commander_deck_analysis_balanced(client):
    """Test commander deck analysis with well-balanced categories."""
    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {
            "ramp": ["Sol Ring", "Cultivate", "Rampant Growth", "Llanowar Elves", "Birds of Paradise", 
                    "Kodama's Reach", "Farseek", "Nature's Lore", "Three Visits", "Sakura-Tribe Elder"],
            "card_advantage": ["Rhystic Study", "Phyrexian Arena", "Sylvan Library", "The Great Henge",
                              "Beast Whisperer", "Guardian Project", "Harmonize", "Divination", 
                              "Sign in Blood", "Read the Bones", "Night's Whisper", "Brainstorm"],
            "targeted_disruption": ["Swords to Plowshares", "Path to Exile", "Lightning Bolt", "Counterspell",
                                   "Assassin's Trophy", "Beast Within", "Chaos Warp", "Generous Gift",
                                   "Rapid Hybridization", "Swan Song", "Negate", "Dispel"],
            "mass_disruption": ["Wrath of God", "Day of Judgment", "Cyclonic Rift", "Austere Command",
                               "Supreme Verdict", "Toxic Deluge"],
            "lands": ["Command Tower", "Sol Ring"] + [f"Island {i}" for i in range(36)],  # 38 total
            "plan_cards": ["Lightning Greaves", "Swiftfoot Boots"] + [f"Theme Card {i}" for i in range(28)]  # 30 total
        }
    )
    
    response = result[0].text
    assert "**Command Zone Deck Analysis:**" in response
    assert "**Ramp: 10 cards** ⚡" in response  # 10 meets minimum but 12+ is optimal
    assert "**Card Advantage: 12 cards** ⚡" in response  # 12 meets minimum but 15+ is optimal
    assert "**Targeted Disruption: 12 cards** ✓" in response
    assert "**Mass Disruption: 6 cards** ✓" in response
    assert "**Lands: 38 cards** ✓" in response
    assert "**Plan Cards: 30 cards** ⚡" in response  # ~30 is target range
    assert "✓ Excellent deck balance following Command Zone framework" in response


async def test_commander_deck_analysis_imbalanced(client):
    """Test commander deck analysis with imbalanced categories."""
    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {
            "ramp": ["Sol Ring", "Cultivate"],  # Only 2 instead of 10
            "card_advantage": ["Rhystic Study"],  # Only 1 instead of 12
            "targeted_disruption": ["Swords to Plowshares", "Path to Exile", "Lightning Bolt", "Counterspell"],  # 4 vs 12
            "mass_disruption": ["Wrath of God", "Day of Judgment", "Cyclonic Rift", "Austere Command",
                               "Supreme Verdict", "Toxic Deluge", "Damnation", "Cleansing Nova"],  # 8 vs 6
            "lands": [f"Island {i}" for i in range(30)],  # 30 vs 38
            "plan_cards": [f"Theme Card {i}" for i in range(50)]  # 50 vs 30
        }
    )
    
    response = result[0].text
    assert "**Ramp: 2 cards** ⚠️" in response
    assert "**Card Advantage: 1 cards** ⚠️" in response
    assert "**Lands: 30 cards** ⚠️" in response  
    assert "⚠️ Major structural issues" in response
    assert "Priority Improvements:" in response


async def test_commander_deck_analysis_empty_categories(client):
    """Test commander deck analysis with some empty categories."""
    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {
            "ramp": ["Sol Ring", "Cultivate", "Rampant Growth"],
            "lands": [f"Island {i}" for i in range(38)],
            # Other categories left empty
        }
    )
    
    response = result[0].text
    assert "**Ramp: 3 cards**" in response
    assert "**Card Advantage: 0 cards**" in response
    assert "**Lands: 38 cards** ✓" in response
    assert "No cards provided in this category" in response


async def test_commander_deck_analysis_overlapping_cards(client):
    """Test commander deck analysis with cards in multiple categories."""
    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {
            "ramp": ["Sol Ring", "Cultivate"],
            "card_advantage": ["Sol Ring", "Sylvan Library"],  # Sol Ring appears in both
            "lands": ["Command Tower", "Island"]
        }
    )
    
    response = result[0].text
    assert "Total Unique Cards: 5" in response  # Sol Ring, Cultivate, Sylvan Library, Command Tower, Island
    assert "**Ramp: 2 cards**" in response
    assert "**Card Advantage: 2 cards**" in response
    assert "Sol Ring" in response


async def test_commander_deck_analysis_wrong_total(client):
    """Test commander deck analysis with wrong total card count."""
    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {
            "ramp": ["Sol Ring"],
            "lands": ["Island"]
        }
    )
    
    response = result[0].text
    assert "Total Unique Cards: 2" in response
    assert "⚠️ Total cards (2) should equal 100 for Commander format" in response