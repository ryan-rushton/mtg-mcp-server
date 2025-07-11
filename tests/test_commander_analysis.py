"""Tests for commander analysis functionality."""

import json
import pytest
from unittest.mock import patch
from tools.commander_analysis import parse_decklist_with_quantities, _analyze_commander_deck_core


class TestParsedecklistWithQuantities:
    """Test the quantity parsing function in isolation."""
    
    def test_parse_basic_formats(self):
        """Given-When-Then: Test basic quantity format parsing."""
        # Given: Various quantity formats
        decklist = ["4 Forest", "2x Sol Ring", "Lightning Bolt", "1 Command Tower"]
        
        # When: Parsing quantities
        result = parse_decklist_with_quantities(decklist)
        
        # Then: Should parse all formats correctly
        assert result["Forest"] == 4
        assert result["Sol Ring"] == 2
        assert result["Lightning Bolt"] == 1  # Default quantity
        assert result["Command Tower"] == 1
        assert len(result) == 4
    
    def test_parse_duplicates_combine(self):
        """Given-When-Then: Test duplicate card quantity combination."""
        # Given: Duplicate card entries
        decklist = ["4 Forest", "Forest", "2 Forest"]
        
        # When: Parsing quantities
        result = parse_decklist_with_quantities(decklist)
        
        # Then: Should combine quantities
        assert result["Forest"] == 7  # 4 + 1 + 2
        assert len(result) == 1
    
    def test_parse_edge_cases(self):
        """Given-When-Then: Test edge cases in parsing."""
        # Given: Edge case entries
        decklist = [
            "",  # Empty entry
            "   ",  # Whitespace only
            "0 Lightning Bolt",  # Zero quantity
            "100x Command Tower",  # Very high quantity
            "2x   Padded   Spaces   ",  # Extra spaces
        ]
        
        # When: Parsing quantities
        result = parse_decklist_with_quantities(decklist)
        
        # Then: Should handle edge cases gracefully
        assert result["Lightning Bolt"] == 0  # Zero quantity preserved
        assert result["Command Tower"] == 100  # High quantity preserved
        assert result["Padded   Spaces"] == 2  # Spaces in name preserved
        assert len(result) == 3  # Empty entries skipped
    
    def test_parse_case_sensitivity(self):
        """Given-When-Then: Test case sensitivity in parsing."""
        # Given: Mixed case quantity indicators
        decklist = ["4 Forest", "2X Sol Ring", "3x Lightning Bolt"]
        
        # When: Parsing quantities
        result = parse_decklist_with_quantities(decklist)
        
        # Then: Should handle case insensitive 'x' indicator
        assert result["Forest"] == 4
        assert result["Sol Ring"] == 2
        assert result["Lightning Bolt"] == 3
    
    def test_parse_complex_card_names(self):
        """Given-When-Then: Test parsing with complex card names."""
        # Given: Complex card names with numbers and symbols
        decklist = [
            "1 Jace, the Mind Sculptor",
            "2x Sol Ring",
            "4 Force of Will",
            "1 Karn, Scion of Urza",
        ]
        
        # When: Parsing quantities
        result = parse_decklist_with_quantities(decklist)
        
        # Then: Should handle complex names correctly
        assert result["Jace, the Mind Sculptor"] == 1
        assert result["Sol Ring"] == 2
        assert result["Force of Will"] == 4
        assert result["Karn, Scion of Urza"] == 1


class TestCommanderAnalysis:
    """Test the full commander deck analysis workflow."""
    
    @pytest.fixture
    def mock_commander_card(self):
        """Mock commander card data."""
        return {
            "name": "Atraxa, Praetors' Voice",
            "type_line": "Legendary Creature — Phyrexian Angel Horror",
            "oracle_text": "Flying, vigilance, deathtouch, lifelink\nAt the beginning of your end step, proliferate.",
            "mana_cost": "{G}{W}{U}{B}",
            "cmc": 4.0,
            "color_identity": ["B", "G", "U", "W"],
            "colors": ["B", "G", "U", "W"]
        }
    
    @pytest.fixture
    def mock_deck_cards(self):
        """Mock deck card data."""
        return [
            {
                "name": "Sol Ring",
                "type_line": "Artifact",
                "oracle_text": "{T}: Add {C}{C}.",
                "mana_cost": "{1}",
                "cmc": 1.0,
                "color_identity": [],
                "colors": []
            },
            {
                "name": "Lightning Bolt",
                "type_line": "Instant",
                "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                "mana_cost": "{R}",
                "cmc": 1.0,
                "color_identity": ["R"],
                "colors": ["R"]
            },
            {
                "name": "Forest",
                "type_line": "Basic Land — Forest",
                "oracle_text": "({T}: Add {G}.)",
                "mana_cost": "",
                "cmc": 0.0,
                "color_identity": [],
                "colors": []
            }
        ]
    
    @patch('tools.commander_analysis.get_cached_card')
    @patch('tools.commander_analysis.batch_lookup_cards')
    async def test_analyze_valid_commander_deck(self, mock_batch_lookup, mock_get_cached, 
                                               mock_commander_card, mock_deck_cards):
        """Given-When-Then: Test analyzing a valid commander deck."""
        # Given: Valid commander and deck data
        mock_get_cached.return_value = mock_commander_card
        mock_batch_lookup.return_value = (mock_deck_cards, [])
        
        commander = "Atraxa, Praetors' Voice"
        decklist = ["1 Sol Ring", "1 Lightning Bolt", "1 Forest"]
        
        # When: Analyzing the deck
        result = await _analyze_commander_deck_core(commander, decklist)
        
        # Then: Should return valid JSON analysis
        analysis = json.loads(result)
        
        # Verify structure
        assert "commander" in analysis
        assert "deck" in analysis
        assert "cards" in analysis
        assert "command_zone_targets" in analysis
        assert "instructions" in analysis
        
        # Verify commander data
        assert analysis["commander"]["name"] == "Atraxa, Praetors' Voice"
        assert len(analysis["commander"]["colors"]) == 4
        assert "White" in analysis["commander"]["colors"]
        assert "Blue" in analysis["commander"]["colors"]
        assert "Black" in analysis["commander"]["colors"]
        assert "Green" in analysis["commander"]["colors"]
        
        # Verify deck data
        assert analysis["deck"]["deck_cards"] == 3
        assert analysis["deck"]["unique_cards"] == 3
        assert analysis["deck"]["total_cards"] == 4  # Including commander
        assert not analysis["deck"]["format_valid"]  # Only 3 cards, need 99
        
        # Verify validation integration
        assert "validation" in analysis
        assert "is_valid" in analysis["validation"]
        assert "errors" in analysis["validation"]
        assert "warnings" in analysis["validation"]
        assert "summary" in analysis["validation"]
        
        # Verify cards data
        assert len(analysis["cards"]) == 3
        for card in analysis["cards"]:
            assert "name" in card
            assert "quantity" in card
            assert "type_line" in card
            assert "oracle_text" in card
    
    @patch('tools.commander_analysis.get_cached_card')
    @patch('tools.commander_analysis.batch_lookup_cards')
    async def test_analyze_deck_with_quantities(self, mock_batch_lookup, mock_get_cached,
                                               mock_commander_card, mock_deck_cards):
        """Given-When-Then: Test analyzing deck with various quantities."""
        # Given: Deck with different quantities
        mock_get_cached.return_value = mock_commander_card
        mock_batch_lookup.return_value = (mock_deck_cards, [])
        
        commander = "Atraxa, Praetors' Voice"
        decklist = ["2x Sol Ring", "4 Lightning Bolt", "Forest"]
        
        # When: Analyzing the deck
        result = await _analyze_commander_deck_core(commander, decklist)
        
        # Then: Should handle quantities correctly
        analysis = json.loads(result)
        
        # Find cards by name to check quantities
        sol_ring = next(card for card in analysis["cards"] if card["name"] == "Sol Ring")
        lightning_bolt = next(card for card in analysis["cards"] if card["name"] == "Lightning Bolt")
        forest = next(card for card in analysis["cards"] if card["name"] == "Forest")
        
        assert sol_ring["quantity"] == 2
        assert lightning_bolt["quantity"] == 4
        assert forest["quantity"] == 1
        
        # Total should be 2 + 4 + 1 = 7
        assert analysis["deck"]["deck_cards"] == 7
    
    @patch('tools.commander_analysis.get_cached_card')
    @patch('tools.commander_analysis.batch_lookup_cards')
    async def test_analyze_deck_with_commander_in_list(self, mock_batch_lookup, mock_get_cached,
                                                      mock_commander_card):
        """Given-When-Then: Test deck with commander included in deck list."""
        # Given: Commander appears in the deck list (should be removed)
        mock_get_cached.return_value = mock_commander_card
        
        # Include commander in deck cards
        deck_with_commander = [
            mock_commander_card,  # Commander should be removed
            {
                "name": "Sol Ring",
                "type_line": "Artifact",
                "mana_cost": "{1}",
                "cmc": 1.0,
                "color_identity": [],
                "colors": []
            }
        ]
        mock_batch_lookup.return_value = (deck_with_commander, [])
        
        commander = "Atraxa, Praetors' Voice"
        decklist = ["2 Atraxa, Praetors' Voice", "1 Sol Ring"]  # Commander in deck list
        
        # When: Analyzing the deck
        result = await _analyze_commander_deck_core(commander, decklist)
        
        # Then: Should remove commander from deck and track removal
        analysis = json.loads(result)
        
        # Commander should not appear in cards list
        card_names = [card["name"] for card in analysis["cards"]]
        assert "Atraxa, Praetors' Voice" not in card_names
        
        # Should have only Sol Ring
        assert len(analysis["cards"]) == 1
        assert analysis["cards"][0]["name"] == "Sol Ring"
        
        # Should track commander removal
        assert analysis["deck"]["commander_in_original_list"]
        assert analysis["deck"]["commander_quantity_removed"] == 2
        assert analysis["deck"]["deck_cards"] == 1  # Only Sol Ring
    
    async def test_analyze_empty_inputs(self):
        """Given-When-Then: Test error handling for empty inputs."""
        # Given: Empty inputs
        # When: Analyzing with empty commander
        result1 = await _analyze_commander_deck_core("", ["Sol Ring"])
        # Then: Should return error
        assert "Error: Both commander and decklist are required" in result1
        
        # When: Analyzing with empty decklist
        result2 = await _analyze_commander_deck_core("Atraxa, Praetors' Voice", [])
        # Then: Should return error
        assert "Error: Both commander and decklist are required" in result2
        
        # When: Analyzing with both empty
        result3 = await _analyze_commander_deck_core("", [])
        # Then: Should return error
        assert "Error: Both commander and decklist are required" in result3
    
    @patch('tools.commander_analysis.get_cached_card')
    async def test_analyze_commander_not_found(self, mock_get_cached):
        """Given-When-Then: Test error handling when commander not found."""
        # Given: Commander that doesn't exist
        mock_get_cached.return_value = None
        
        commander = "Nonexistent Commander"
        decklist = ["Sol Ring", "Lightning Bolt"]
        
        # When: Analyzing the deck
        result = await _analyze_commander_deck_core(commander, decklist)
        
        # Then: Should return commander not found error
        assert "Error: Could not find commander" in result
        assert "Nonexistent Commander" in result
    
    @patch('tools.commander_analysis.get_cached_card')
    @patch('tools.commander_analysis.batch_lookup_cards')
    async def test_analyze_cards_not_found(self, mock_batch_lookup, mock_get_cached,
                                          mock_commander_card):
        """Given-When-Then: Test error handling when deck cards not found."""
        # Given: Some cards not found
        mock_get_cached.return_value = mock_commander_card
        mock_batch_lookup.return_value = ([], ["Fake Card 1", "Fake Card 2"])
        
        commander = "Atraxa, Praetors' Voice"
        decklist = ["Fake Card 1", "Fake Card 2"]
        
        # When: Analyzing the deck
        result = await _analyze_commander_deck_core(commander, decklist)
        
        # Then: Should return cards not found error
        assert "Error: Could not find the following cards" in result
        assert "Fake Card 1" in result
        assert "Fake Card 2" in result
    
    @patch('tools.commander_analysis.get_cached_card')
    @patch('tools.commander_analysis.batch_lookup_cards')
    async def test_command_zone_targets_included(self, mock_batch_lookup, mock_get_cached,
                                                mock_commander_card, mock_deck_cards):
        """Given-When-Then: Test that Command Zone targets are included in output."""
        # Given: Valid analysis setup
        mock_get_cached.return_value = mock_commander_card
        mock_batch_lookup.return_value = (mock_deck_cards, [])
        
        commander = "Atraxa, Praetors' Voice"
        decklist = ["Sol Ring", "Lightning Bolt", "Forest"]
        
        # When: Analyzing the deck
        result = await _analyze_commander_deck_core(commander, decklist)
        
        # Then: Should include Command Zone targets
        analysis = json.loads(result)
        targets = analysis["command_zone_targets"]
        
        # Verify all categories are present
        expected_categories = ["Ramp", "Card Advantage", "Targeted Disruption", 
                              "Mass Disruption", "Lands", "Plan Cards"]
        for category in expected_categories:
            assert category in targets
            assert "target" in targets[category]
            assert "optimal" in targets[category]
            assert "description" in targets[category]
        
        # Verify specific target values match config
        assert targets["Ramp"]["target"] == 10
        assert targets["Ramp"]["optimal"] == 12
        assert targets["Lands"]["target"] == 38
    
    @patch('tools.commander_analysis.get_cached_card')
    @patch('tools.commander_analysis.batch_lookup_cards')
    async def test_instructions_included(self, mock_batch_lookup, mock_get_cached,
                                        mock_commander_card, mock_deck_cards):
        """Given-When-Then: Test that detailed instructions are included."""
        # Given: Valid analysis setup
        mock_get_cached.return_value = mock_commander_card
        mock_batch_lookup.return_value = (mock_deck_cards, [])
        
        commander = "Atraxa, Praetors' Voice"
        decklist = ["Sol Ring"]
        
        # When: Analyzing the deck
        result = await _analyze_commander_deck_core(commander, decklist)
        
        # Then: Should include comprehensive instructions
        analysis = json.loads(result)
        instructions = analysis["instructions"]
        
        # Verify instruction structure
        assert "task" in instructions
        assert "categories" in instructions
        assert "requirements" in instructions
        assert "example_format" in instructions
        assert "multi_category_reminder" in instructions
        
        # Verify specific instruction content
        assert "Categorize the provided cards" in instructions["task"]
        assert "MUST list the specific cards" in str(instructions["requirements"])
        assert "CRITICAL: Cards can and should belong to multiple categories" in str(instructions["requirements"])
        assert "Ramp (" in instructions["example_format"]
    
    def test_parse_decklist_empty_handling(self):
        """Given-When-Then: Test empty decklist handling in parsing."""
        # Given: Empty decklist
        decklist = []
        
        # When: Parsing quantities
        result = parse_decklist_with_quantities(decklist)
        
        # Then: Should return empty dict
        assert len(result) == 0
        assert isinstance(result, dict)
    
    def test_parse_decklist_whitespace_handling(self):
        """Given-When-Then: Test whitespace handling in card names."""
        # Given: Cards with extra whitespace
        decklist = ["  4   Forest  ", "2x   Sol Ring   "]
        
        # When: Parsing quantities
        result = parse_decklist_with_quantities(decklist)
        
        # Then: Should trim whitespace from card names
        assert result["Forest"] == 4
        assert result["Sol Ring"] == 2
        assert "  Forest  " not in result
        assert "   Sol Ring   " not in result

    @patch('tools.commander_analysis.get_cached_card')
    @patch('tools.commander_analysis.batch_lookup_cards')
    async def test_analyze_deck_with_validation_errors(self, mock_batch_lookup, mock_get_cached,
                                                      mock_commander_card):
        """Given-When-Then: Test deck analysis with validation errors."""
        # Given: Deck with validation issues
        mock_get_cached.return_value = mock_commander_card
        deck_with_issues = [
            {
                "name": "Sol Ring",
                "type_line": "Artifact",
                "mana_cost": "{1}",
                "cmc": 1.0,
                "color_identity": [],
                "colors": []
            },
            {
                "name": "Lightning Bolt", 
                "type_line": "Instant",
                "mana_cost": "{R}",
                "cmc": 1.0,
                "color_identity": ["R"],
                "colors": ["R"]
            }
        ]
        mock_batch_lookup.return_value = (deck_with_issues, [])
        
        commander = "Atraxa, Praetors' Voice"
        # Problematic decklist: too few cards, invalid quantity, singleton violation
        decklist = ["0 Lightning Bolt", "4 Sol Ring", "Forest"]  # Only 3 unique cards, invalid quantity
        
        # When: Analyzing the deck
        result = await _analyze_commander_deck_core(commander, decklist)
        
        # Then: Should include validation errors
        analysis = json.loads(result)
        
        # Should have validation section with errors
        assert "validation" in analysis
        validation = analysis["validation"]
        assert not validation["is_valid"]  # Should be invalid
        assert len(validation["errors"]) > 0  # Should have errors
        assert "validation errors found" in validation["summary"]
        
        # Should still provide analysis but with validation context
        assert "instructions" in analysis
        assert "MUST review the validation section first" in str(analysis["instructions"]["requirements"])