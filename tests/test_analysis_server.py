"""Tests for analysis server functionality."""

from unittest.mock import patch


async def test_calculate_mana_curve(client, mock_scryfall_collection_response):
    """Test mana curve calculation."""
    with patch("tools.basic_analysis.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (mock_scryfall_collection_response["data"], [])

        result = await client.call_tool(
            "analysis_calculate_mana_curve",
            {"card_names": ["Lightning Bolt", "Counterspell"]},
        )

        response = result[0].text
        assert "**Mana Curve:**" in response
        assert "CMC 1.0: 1" in response  # Lightning Bolt
        assert "CMC 2.0: 1" in response  # Counterspell


async def test_calculate_mana_curve_with_not_found(client):
    """Test mana curve calculation with some cards not found."""
    with patch("tools.basic_analysis.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (
            [{"name": "Lightning Bolt", "cmc": 1.0}],
            ["Fake Card"],
        )

        result = await client.call_tool(
            "analysis_calculate_mana_curve",
            {"card_names": ["Lightning Bolt", "Fake Card"]},
        )

        response = result[0].text
        assert "**Mana Curve:**" in response
        assert "CMC 1.0: 1" in response
        assert "**Cards Not Found:** Fake Card" in response


async def test_analyze_lands(client, mock_scryfall_land_response):
    """Test land analysis functionality."""
    with patch("tools.basic_analysis.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (mock_scryfall_land_response["data"], [])

        result = await client.call_tool(
            "analysis_analyze_lands",
            {"card_names": ["Command Tower", "Sacred Foundry"]},
        )

        response = result[0].text
        assert "**Land Analysis:**" in response
        assert "Total Lands: 2" in response
        assert "White mana sources:" in response
        assert "Red mana sources:" in response


async def test_analyze_color_identity(client, mock_scryfall_collection_response):
    """Test color identity analysis."""
    with patch("tools.color_analysis.get_cached_card") as mock_get_card:
        # Mock individual card lookups used by color_analysis
        def mock_card_lookup(client, card_name):
            for card in mock_scryfall_collection_response["data"]:
                if card["name"].lower() == card_name.lower():
                    return card
            return None
        mock_get_card.side_effect = mock_card_lookup

        result = await client.call_tool(
            "analysis_analyze_color_identity",
            {"card_names": ["Lightning Bolt", "Counterspell"]},
        )

        response = result[0].text
        import json

        analysis = json.loads(response)

        assert analysis["summary"]["total_cards"] == 2
        assert "individual_colors" in analysis
        assert "Red" in analysis["individual_colors"]
        assert "Blue" in analysis["individual_colors"]
        assert analysis["individual_colors"]["Red"]["count"] == 1
        assert analysis["individual_colors"]["Blue"]["count"] == 1


async def test_analyze_mana_requirements(client):
    """Test mana requirements analysis."""
    mock_cards = [
        {
            "name": "Lightning Bolt",
            "type_line": "Instant",
            "color_identity": ["R"],
            "oracle_text": "Lightning Bolt deals 3 damage to any target.",
        },
        {
            "name": "Mountain",
            "type_line": "Basic Land — Mountain",
            "color_identity": [],
            "oracle_text": "{T}: Add {R}.",
        },
    ]

    with patch("tools.color_analysis.get_cached_card") as mock_get_card:
        # Mock individual card lookups used by color_analysis
        def mock_card_lookup(client, card_name):
            for card in mock_cards:
                if card["name"].lower() == card_name.lower():
                    return card
            return None
        mock_get_card.side_effect = mock_card_lookup

        result = await client.call_tool(
            "analysis_analyze_mana_requirements",
            {"card_names": ["Lightning Bolt", "Mountain"]},
        )

        response = result[0].text
        import json

        analysis = json.loads(response)

        assert analysis["summary"]["total_cards"] == 2
        assert analysis["summary"]["spells"] == 1
        assert analysis["summary"]["lands"] == 1
        assert "Red" in analysis["color_analysis"]
        assert analysis["color_analysis"]["Red"]["spell_requirements"] == 1
        assert analysis["color_analysis"]["Red"]["land_sources"] == 1


async def test_analyze_card_types(client, mock_scryfall_collection_response):
    """Test card type analysis."""
    with patch("tools.basic_analysis.batch_lookup_cards") as mock_batch:
        mock_batch.return_value = (mock_scryfall_collection_response["data"], [])

        result = await client.call_tool(
            "analysis_analyze_card_types",
            {"card_names": ["Lightning Bolt", "Counterspell"]},
        )

        response = result[0].text
        assert "**Card Type Distribution:**" in response
        assert "Total Cards Analyzed: 2 of 2" in response
        assert "Instant: 2 (100.0%)" in response
        assert "**All Card Types Found:**" in response


async def test_analyze_card_types_comprehensive(client):
    """Test enhanced card type analysis with diverse card types."""
    # Mix of different card types including multi-type cards
    result = await client.call_tool(
        "analysis_analyze_card_types",
        {"card_names": [
            "Sol Ring",              # Artifact
            "Forest",               # Basic Land  
            "Command Tower",        # Land
            "Lightning Bolt",       # Instant
            "Cultivate",           # Sorcery
            "Serra Angel",         # Creature — Angel
            "Llanowar Elves",      # Creature — Elf Druid  
            "Rhystic Study",       # Enchantment
            "Jace, the Mind Sculptor", # Legendary Planeswalker — Jace
        ]},
    )

    response = result[0].text
    
    # Should find all major card types
    assert "Artifact:" in response
    assert "Land:" in response or "Basic:" in response  # Basic lands have "Basic Land" type
    assert "Instant:" in response
    assert "Sorcery:" in response
    assert "Creature:" in response
    assert "Enchantment:" in response
    assert "Planeswalker:" in response
    
    # Should show comprehensive analysis
    assert "**All Card Types Found:**" in response
    assert "**Commander Deck Guidelines:**" in response
    assert "**Most Common Type Lines:**" in response
    
    # Should handle multi-type cards (like "Legendary Planeswalker")
    assert "Legendary:" in response

async def test_empty_card_names_analysis_tools(client):
    """Test all analysis tools handle empty input correctly."""
    tools = [
        "analysis_calculate_mana_curve",
        "analysis_analyze_lands",
        "analysis_analyze_color_identity",
        "analysis_analyze_mana_requirements",
        "analysis_analyze_card_types",
    ]

    for tool_name in tools:
        result = await client.call_tool(tool_name, {"card_names": []})
        response = result[0].text
        assert response == "No card names provided.", (
            f"Tool {tool_name} failed empty input test"
        )


async def test_commander_deck_analysis_balanced(client):
    """Test commander deck analysis with well-balanced categories."""
    # Create a small balanced deck list with real cards
    decklist = [
        # Ramp
        "Sol Ring",
        "Cultivate",
        "Rampant Growth",
        # Card advantage
        "Rhystic Study",
        "Phyrexian Arena",
        # Targeted disruption
        "Swords to Plowshares",
        "Lightning Bolt",
        "Counterspell",
        # Mass disruption
        "Wrath of God",
        "Cyclonic Rift",
        # Lands - using real basic lands
        "Command Tower",
        "Island",
        "Forest",
        "Plains",
        "Mountain",
        "Swamp",
    ]

    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {"commander": "Atraxa, Praetors' Voice", "decklist": decklist},
    )

    response = result[0].text
    import json

    analysis = json.loads(response)

    assert analysis["commander"]["name"] == "Atraxa, Praetors' Voice"
    assert analysis["deck"]["total_cards"] > 0
    assert "cards" in analysis
    assert "command_zone_targets" in analysis
    assert "instructions" in analysis
    assert len(analysis["cards"]) == len(set(decklist))  # Number of unique cards


async def test_commander_deck_analysis_error_cases(client):
    """Test commander deck analysis error handling."""
    # Test missing commander
    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {"commander": "", "decklist": ["Sol Ring", "Island"]},
    )
    response = result[0].text
    assert "Error: Both commander and decklist are required." in response

    # Test missing decklist
    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {"commander": "Atraxa, Praetors' Voice", "decklist": []},
    )
    response = result[0].text
    assert "Error: Both commander and decklist are required." in response


async def test_commander_deck_analysis_basic_functionality(client):
    """Test basic commander deck analysis functionality."""
    decklist = [
        "Sol Ring",
        "Command Tower",
        "Island",
        "Forest",
        "Plains",
        "Mountain",
        "Swamp",
        "Lightning Bolt",
        "Counterspell",
        "Wrath of God",
    ]

    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {"commander": "Atraxa, Praetors' Voice", "decklist": decklist},
    )

    response = result[0].text
    import json

    analysis = json.loads(response)

    assert analysis["commander"]["name"] == "Atraxa, Praetors' Voice"
    assert "cards" in analysis
    assert "command_zone_targets" in analysis
    assert "instructions" in analysis
    assert "unique_cards" in analysis["deck"]


async def test_commander_deck_analysis_with_quantities(client):
    """Test commander deck analysis with card quantities."""
    # Test decklist with quantities and duplicates
    decklist = [
        "4 Forest",
        "3 Swamp", 
        "2x Sol Ring",  # Different quantity format
        "Lightning Bolt",  # No quantity (should be 1)
        "Forest",  # Duplicate (should combine with "4 Forest" for total 5)
        "2 Island",
    ]

    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {"commander": "Atraxa, Praetors' Voice", "decklist": decklist},
    )

    response = result[0].text
    import json

    analysis = json.loads(response)

    # Should have unique cards (Forest, Swamp, Sol Ring, Lightning Bolt, Island)
    assert len(analysis["cards"]) == 5
    
    # Total deck cards should sum the quantities: 5+3+2+1+2 = 13
    assert analysis["deck"]["deck_cards"] == 13
    
    # Check specific card quantities
    forest_card = next(card for card in analysis["cards"] if card["name"] == "Forest")
    assert forest_card["quantity"] == 5  # 4 + 1 from duplicates
    
    sol_ring_card = next(card for card in analysis["cards"] if card["name"] == "Sol Ring")
    assert sol_ring_card["quantity"] == 2
    
    lightning_bolt_card = next(card for card in analysis["cards"] if card["name"] == "Lightning Bolt")
    assert lightning_bolt_card["quantity"] == 1


async def test_commander_analysis_with_commander_in_decklist(client):
    """Test commander analysis when commander is included in the decklist."""
    # Include the commander in the decklist - it should be automatically removed
    decklist = [
        "Atraxa, Praetors' Voice",  # This should be removed from the 99
        "2 Atraxa, Praetors' Voice",  # Additional copies should also be removed
        "Sol Ring",
        "Lightning Bolt", 
        "Forest",
        "Island",
    ]

    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {"commander": "Atraxa, Praetors' Voice", "decklist": decklist},
    )

    response = result[0].text
    import json

    analysis = json.loads(response)

    # Commander should not appear in the card list
    commander_in_cards = any(card["name"] == "Atraxa, Praetors' Voice" for card in analysis["cards"])
    assert not commander_in_cards, "Commander should not appear in the cards list"
    
    # Should have 4 unique cards (Sol Ring, Lightning Bolt, Forest, Island)
    assert len(analysis["cards"]) == 4
    
    # Total deck cards should be 4 (excluding all commander copies)
    assert analysis["deck"]["deck_cards"] == 4
    
    # Should indicate commander was in original list
    assert analysis["deck"]["commander_in_original_list"]
    assert analysis["deck"]["commander_quantity_removed"] == 3  # 1 + 2 copies removed


async def test_commander_analysis_strategy_awareness(client):
    """Test that commander analysis instructions encourage strategy awareness."""
    decklist = [
        "Sol Ring", "Lightning Bolt", "Forest", "Command Tower"
    ]

    result = await client.call_tool(
        "analysis_analyze_commander_deck",
        {
            "commander": "Atraxa, Praetors' Voice", 
            "decklist": decklist
        },
    )

    response = result[0].text
    import json

    analysis = json.loads(response)
    
    # Should include strategy-aware instructions
    requirements = analysis["instructions"]["requirements"]
    strategy_mentioned = any("strategy" in req or "theme" in req for req in requirements)
    assert strategy_mentioned
    
    # Should encourage looking for strategy clues
    clues_mentioned = any("clues" in req for req in requirements)
    assert clues_mentioned
