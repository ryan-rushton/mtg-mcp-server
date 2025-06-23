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