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
        assert "Total Cards Analyzed: 2" in response
        assert "Instant: 2 (100.0%)" in response


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
    assert "categories" in analysis
    assert "balance_assessment" in analysis
    assert "recommendations" in analysis
    assert "categorization" in analysis


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
    assert "categories" in analysis
    assert "balance_assessment" in analysis
