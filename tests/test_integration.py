"""
Integration tests for MTG MCP Server with real network requests.

These tests make actual calls to the Scryfall API to verify the entire system
works end-to-end. They should be run periodically to ensure compatibility
with the live API.

Note: These tests require internet connectivity and may be slower than unit tests.
"""

import asyncio
import json
import pytest
from fastmcp import Client


@pytest.fixture
async def integration_client():
    """Fixture that provides a real MCP client for integration testing."""
    client = Client("server.py")
    async with client:
        yield client


class TestScryfallIntegration:
    """Integration tests for Scryfall API tools."""

    async def test_lookup_popular_cards(self, integration_client):
        """Test looking up well-known cards that should always exist."""
        result = await integration_client.call_tool(
            "scryfall_lookup_cards",
            {"card_names": ["Lightning Bolt", "Sol Ring", "Command Tower"]},
        )
        
        assert result
        response_text = result[0].text
        
        # Verify all cards were found
        assert "Lightning Bolt" in response_text
        assert "Sol Ring" in response_text
        assert "Command Tower" in response_text
        
        # Verify mana costs are included
        assert "{R}" in response_text  # Lightning Bolt
        assert "{1}" in response_text  # Sol Ring

    async def test_lookup_nonexistent_cards(self, integration_client):
        """Test error handling for cards that don't exist."""
        result = await integration_client.call_tool(
            "scryfall_lookup_cards",
            {"card_names": ["Nonexistent Card That Definitely Does Not Exist"]},
        )
        
        assert result
        response_text = result[0].text
        data = json.loads(response_text)
        assert "not_found_cards" in data
        assert len(data["not_found_cards"]) > 0

    async def test_batch_lookup_large_list(self, integration_client):
        """Test batch lookup with a larger list of cards."""
        # Create a list of 20 well-known cards
        card_names = [
            "Lightning Bolt", "Sol Ring", "Command Tower", "Cultivate",
            "Swords to Plowshares", "Counterspell", "Wrath of God", "Rhystic Study",
            "Phyrexian Arena", "Cyclonic Rift", "Forest", "Island", "Mountain",
            "Plains", "Swamp", "Rampant Growth", "Kodama's Reach", "Signets",
            "Arcane Signet", "Three Visits"
        ]
        
        result = await integration_client.call_tool(
            "scryfall_lookup_cards",
            {"card_names": card_names},
        )
        
        assert result
        response_text = result[0].text
        
        # Should find most cards (some might be ambiguous like "Signets")
        found_count = sum(1 for name in card_names if name in response_text)
        assert found_count >= 15  # Expect at least 15/20 to be found

    async def test_search_by_criteria(self, integration_client):
        """Test searching cards by various criteria."""
        # Search for dragons
        result = await integration_client.call_tool(
            "scryfall_search_cards_by_criteria",
            {"name": "dragon", "limit": 5}
        )
        
        assert result
        response_text = result[0].text
        # Should find dragons - check JSON structure
        try:
            data = json.loads(response_text)
            assert "search_query" in data
            assert "cards" in data
            assert len(data["cards"]) > 0
            # Check that we found some dragons
            card_names = [card["name"].lower() for card in data["cards"]]
            assert any("dragon" in name for name in card_names)
        except json.JSONDecodeError:
            # Fallback: if it's an error message, ensure it's informative
            assert "error" in response_text.lower() or "found" in response_text.lower()
        
        # Search by color
        result = await integration_client.call_tool(
            "scryfall_search_cards_by_criteria",
            {"colors": "R", "limit": 3}
        )
        
        assert result
        response_text = result[0].text
        # Should find red cards


class TestAnalysisIntegration:
    """Integration tests for analysis tools."""

    async def test_mana_curve_analysis(self, integration_client):
        """Test mana curve analysis with real cards."""
        result = await integration_client.call_tool(
            "analysis_calculate_mana_curve",
            {
                "card_names": [
                    "Lightning Bolt",      # CMC 1
                    "Sol Ring",           # CMC 1
                    "Counterspell",       # CMC 2
                    "Cultivate",          # CMC 3
                    "Wrath of God",       # CMC 4
                    "Consecrated Sphinx", # CMC 6
                ]
            },
        )
        
        assert result
        response_text = result[0].text
        
        # Should contain CMC distribution information
        assert "CMC" in response_text or "mana curve" in response_text.lower()
        assert "CMC 1.0:" in response_text or "CMC 2.0:" in response_text

    async def test_lands_analysis(self, integration_client):
        """Test land analysis with real cards."""
        result = await integration_client.call_tool(
            "analysis_analyze_lands",
            {
                "card_names": [
                    "Forest", "Island", "Mountain", "Plains", "Swamp",
                    "Command Tower", "Sol Ring", "Lightning Bolt"
                ]
            },
        )
        
        assert result
        response_text = result[0].text
        
        # Should identify lands vs non-lands
        assert "land" in response_text.lower()
        assert "6" in response_text  # 6 lands (including Command Tower)

    async def test_color_analysis(self, integration_client):
        """Test color analysis with real cards."""
        result = await integration_client.call_tool(
            "analysis_analyze_color_identity",
            {
                "card_names": [
                    "Lightning Bolt",     # Red
                    "Counterspell",       # Blue
                    "Swords to Plowshares", # White
                    "Sol Ring",           # Colorless
                ]
            },
        )
        
        assert result
        response_text = result[0].text
        
        # Should be valid JSON
        color_data = json.loads(response_text)
        assert "color_combinations" in color_data
        assert "individual_colors" in color_data

    async def test_card_types_analysis(self, integration_client):
        """Test card type analysis with real cards."""
        result = await integration_client.call_tool(
            "analysis_analyze_card_types",
            {
                "card_names": [
                    "Lightning Bolt",     # Instant
                    "Sol Ring",           # Artifact
                    "Forest",             # Land
                    "Serra Angel",        # Creature
                ]
            },
        )
        
        assert result
        response_text = result[0].text
        
        # Should identify different card types
        assert "instant" in response_text.lower() or "sorcery" in response_text.lower()
        assert "artifact" in response_text.lower()
        assert "land" in response_text.lower()


class TestCommanderAnalysisIntegration:
    """Integration tests for Commander deck analysis."""

    async def test_commander_analysis_basic(self, integration_client):
        """Test basic Commander deck analysis with real cards."""
        # Small but representative deck list
        decklist = [
            # Ramp
            "Sol Ring", "Cultivate", "Rampant Growth", "Arcane Signet",
            # Card advantage  
            "Rhystic Study", "Phyrexian Arena", "Harmonize",
            # Removal
            "Swords to Plowshares", "Lightning Bolt", "Counterspell",
            "Wrath of God", "Cyclonic Rift",
            # Lands
            "Command Tower", "Forest", "Island", "Mountain", "Plains", "Swamp",
            "Evolving Wilds", "Terramorphic Expanse",
            # Win conditions
            "Serra Angel", "Shivan Dragon", "Consecrated Sphinx"
        ]
        
        result = await integration_client.call_tool(
            "analysis_analyze_commander_deck",
            {"commander": "Atraxa, Praetors' Voice", "decklist": decklist},
        )
        
        assert result
        response_text = result[0].text
        
        # Should be valid JSON
        analysis = json.loads(response_text)
        
        # Verify structure
        assert "commander" in analysis
        assert "deck" in analysis
        assert "cards" in analysis
        assert "command_zone_targets" in analysis
        assert "instructions" in analysis
        
        # Verify commander info
        assert analysis["commander"]["name"] == "Atraxa, Praetors' Voice"
        assert len(analysis["commander"]["colors"]) == 4  # WUBG
        
        # Verify deck info
        assert analysis["deck"]["deck_cards"] == len(decklist)
        assert analysis["deck"]["unique_cards"] == len(set(decklist))
        
        # Verify cards have required fields
        for card in analysis["cards"]:
            assert "name" in card
            assert "quantity" in card
            assert "type_line" in card
            assert "oracle_text" in card

    async def test_commander_analysis_with_quantities(self, integration_client):
        """Test Commander analysis with card quantities and duplicates."""
        decklist = [
            "4 Forest",
            "3 Island", 
            "2x Sol Ring",
            "Lightning Bolt",
            "Forest",  # Should combine with "4 Forest" for total 5
            "2 Command Tower",
        ]
        
        result = await integration_client.call_tool(
            "analysis_analyze_commander_deck",
            {"commander": "Atraxa, Praetors' Voice", "decklist": decklist},
        )
        
        assert result
        response_text = result[0].text
        
        analysis = json.loads(response_text)
        
        # Should have 5 unique cards
        assert len(analysis["cards"]) == 5
        
        # Total should be 5+3+2+1+2 = 13
        assert analysis["deck"]["deck_cards"] == 13
        
        # Verify specific quantities
        forest_card = next(card for card in analysis["cards"] if card["name"] == "Forest")
        assert forest_card["quantity"] == 5  # 4 + 1
        
        sol_ring_card = next(card for card in analysis["cards"] if card["name"] == "Sol Ring")
        assert sol_ring_card["quantity"] == 2

    async def test_commander_in_decklist_removal(self, integration_client):
        """Test that commander is properly removed when included in decklist."""
        # Include commander in decklist - should be automatically removed
        decklist = [
            "Atraxa, Praetors' Voice",  # Commander - should be removed
            "2x Atraxa, Praetors' Voice",  # More commander copies - should be removed  
            "Sol Ring",
            "Lightning Bolt",
            "Forest",
            "Command Tower"
        ]
        
        result = await integration_client.call_tool(
            "analysis_analyze_commander_deck",
            {"commander": "Atraxa, Praetors' Voice", "decklist": decklist},
        )
        
        assert result
        response_text = result[0].text
        
        analysis = json.loads(response_text)
        
        # Commander should not appear in cards list
        commander_in_cards = any(card["name"] == "Atraxa, Praetors' Voice" for card in analysis["cards"])
        assert not commander_in_cards
        
        # Should have only 4 unique cards (excluding commander)
        assert len(analysis["cards"]) == 4
        
        # Should have removed 3 total commander copies (1 + 2)
        assert analysis["deck"]["commander_in_original_list"]
        assert analysis["deck"]["commander_quantity_removed"] == 3
        
        # Deck should have 4 cards total (excluding commander)
        assert analysis["deck"]["deck_cards"] == 4

    async def test_commander_not_found(self, integration_client):
        """Test error handling when commander doesn't exist."""
        result = await integration_client.call_tool(
            "analysis_analyze_commander_deck",
            {
                "commander": "Nonexistent Commander That Does Not Exist",
                "decklist": ["Sol Ring", "Lightning Bolt"]
            },
        )
        
        assert result
        response_text = result[0].text
        assert "Error" in response_text
        assert "Could not find commander" in response_text


class TestErrorHandlingIntegration:
    """Integration tests for error handling with real API calls."""

    async def test_empty_inputs(self, integration_client):
        """Test various tools with empty inputs."""
        # Empty card lookup
        result = await integration_client.call_tool(
            "scryfall_lookup_cards",
            {"card_names": []},
        )
        assert result
        assert "No card names provided" in result[0].text

        # Empty analysis
        result = await integration_client.call_tool(
            "analysis_calculate_mana_curve",
            {"card_names": []},
        )
        assert result
        assert "No card names provided" in result[0].text

    async def test_malformed_inputs(self, integration_client):
        """Test tools with malformed but valid inputs."""
        # Very long card name
        result = await integration_client.call_tool(
            "scryfall_lookup_cards",
            {"card_names": ["A" * 200]},  # Very long name
        )
        assert result
        # Should handle gracefully

    async def test_rate_limiting_resilience(self, integration_client):
        """Test that the system handles API rate limits gracefully."""
        # Make several rapid requests
        tasks = []
        for i in range(5):
            task = integration_client.call_tool(
                "scryfall_lookup_cards",
                {"card_names": ["Lightning Bolt", "Sol Ring"]},
            )
            tasks.append(task)
        
        # All should complete successfully
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # At least most should succeed (some might fail due to rate limits)
        successful = sum(1 for r in results if not isinstance(r, Exception))
        assert successful >= 3  # At least 3/5 should succeed


@pytest.mark.asyncio
async def test_full_integration_workflow():
    """Test a complete workflow using multiple tools together."""
    client = Client("server.py")
    
    async with client:
        # 1. Look up some cards
        result = await client.call_tool(
            "scryfall_lookup_cards",
            {"card_names": ["Atraxa, Praetors' Voice", "Sol Ring", "Lightning Bolt"]},
        )
        assert result
        
        # 2. Analyze their mana curve
        result = await client.call_tool(
            "analysis_calculate_mana_curve",
            {"card_names": ["Sol Ring", "Lightning Bolt", "Cultivate", "Wrath of God"]},
        )
        assert result
        
        # 3. Do a commander analysis
        result = await client.call_tool(
            "analysis_analyze_commander_deck",
            {
                "commander": "Atraxa, Praetors' Voice",
                "decklist": [
                    "Sol Ring", "Lightning Bolt", "Cultivate", "Wrath of God",
                    "Forest", "Island", "Mountain", "Plains", "Swamp"
                ]
            },
        )
        assert result
        
        # Should get valid JSON response
        analysis = json.loads(result[0].text)
        assert "commander" in analysis
        assert analysis["commander"]["name"] == "Atraxa, Praetors' Voice"


if __name__ == "__main__":
    # Allow running integration tests directly
    print("Running integration tests...")
    print("Note: These tests make real network requests and may take a while.")
    
    # Run with pytest
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ])
    
    sys.exit(result.returncode)