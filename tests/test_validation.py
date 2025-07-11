"""Tests for validation system robustness."""

from tools.validation import QuantityValidator, DeckValidator, FormatValidator, ValidationResult


class TestQuantityValidator:
    """Test quantity parsing and validation."""
    
    def test_parse_basic_quantity_formats(self):
        """Given-When-Then: Test basic quantity format parsing."""
        # Given: Various quantity formats
        decklist = ["4 Forest", "2x Sol Ring", "Lightning Bolt", "1 Rhystic Study"]
        
        # When: Parsing the decklist
        card_quantities, result = QuantityValidator.parse_decklist_with_validation(decklist)
        
        # Then: Should parse all quantities correctly
        assert result.is_valid
        assert card_quantities["Forest"] == 4
        assert card_quantities["Sol Ring"] == 2
        assert card_quantities["Lightning Bolt"] == 1  # Default quantity
        assert card_quantities["Rhystic Study"] == 1
        assert len(card_quantities) == 4
    
    def test_parse_duplicate_cards_combine_quantities(self):
        """Given-When-Then: Test duplicate card quantity combination."""
        # Given: Decklist with duplicate entries for same card
        decklist = ["4 Forest", "Forest", "2 Forest"]
        
        # When: Parsing the decklist
        card_quantities, result = QuantityValidator.parse_decklist_with_validation(decklist)
        
        # Then: Should combine quantities and warn about duplicates
        assert result.is_valid
        assert card_quantities["Forest"] == 7  # 4 + 1 + 2
        assert len(result.warnings) > 0
        assert "Duplicate card" in result.warnings[0]
    
    def test_parse_invalid_quantity_formats(self):
        """Given-When-Then: Test invalid quantity formats."""
        # Given: Invalid quantity formats
        decklist = ["0 Lightning Bolt", "-1x Sol Ring", "abc Forest", "999x Command Tower"]
        
        # When: Parsing the decklist
        card_quantities, result = QuantityValidator.parse_decklist_with_validation(decklist)
        
        # Then: Should report errors for invalid quantities
        assert not result.is_valid
        assert len(result.errors) >= 2  # Invalid 0 and -1 quantities
        assert "Invalid quantity 0" in str(result.errors)
        assert "Invalid quantity -1" in str(result.errors)
        # Very high quantity should generate warning
        assert len(result.warnings) >= 1
        assert "Very high quantity" in str(result.warnings)
    
    def test_parse_empty_and_whitespace_entries(self):
        """Given-When-Then: Test empty and whitespace handling."""
        # Given: Decklist with empty and whitespace entries
        decklist = ["", "   ", "Forest", "  Sol Ring  "]
        
        # When: Parsing the decklist
        card_quantities, result = QuantityValidator.parse_decklist_with_validation(decklist)
        
        # Then: Should skip empty entries and trim whitespace
        assert result.is_valid
        assert card_quantities["Forest"] == 1
        assert card_quantities["Sol Ring"] == 1
        assert len(card_quantities) == 2
        assert len(result.warnings) >= 2  # Empty entry warnings
    
    def test_parse_very_long_card_names(self):
        """Given-When-Then: Test very long card name validation."""
        # Given: Card name exceeding maximum length
        long_name = "A" * 250  # Exceeds 200 character limit
        decklist = [f"1 {long_name}"]
        
        # When: Parsing the decklist
        card_quantities, result = QuantityValidator.parse_decklist_with_validation(decklist)
        
        # Then: Should report error for name too long
        assert not result.is_valid
        assert "Card name too long" in str(result.errors)
    
    def test_parse_empty_decklist(self):
        """Given-When-Then: Test empty decklist handling."""
        # Given: Empty decklist
        decklist = []
        
        # When: Parsing the decklist
        card_quantities, result = QuantityValidator.parse_decklist_with_validation(decklist)
        
        # Then: Should report error for empty decklist
        assert not result.is_valid
        assert "Decklist cannot be empty" in str(result.errors)
        assert len(card_quantities) == 0


class TestDeckValidator:
    """Test deck format and structure validation."""
    
    def test_valid_commander_format(self):
        """Given-When-Then: Test valid Commander format deck."""
        # Given: Valid Commander deck (99 unique cards)
        deck_cards = {f"Card {i}": 1 for i in range(99)}
        
        # When: Validating Commander format
        validator = DeckValidator("Commander")
        result = validator.validate_commander_format("Atraxa, Praetors' Voice", deck_cards)
        
        # Then: Should pass validation
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_commander_format_wrong_deck_size(self):
        """Given-When-Then: Test Commander format with wrong deck size."""
        # Given: Deck with wrong number of cards
        deck_cards_too_few = {f"Card {i}": 1 for i in range(95)}  # 96 total with commander
        deck_cards_too_many = {f"Card {i}": 1 for i in range(105)}  # 106 total with commander
        
        validator = DeckValidator("Commander")
        
        # When: Validating undersized deck
        result_few = validator.validate_commander_format("Atraxa", deck_cards_too_few)
        
        # Then: Should report error for too few cards
        assert not result_few.is_valid
        assert "only 96 cards" in str(result_few.errors)
        
        # When: Validating oversized deck
        result_many = validator.validate_commander_format("Atraxa", deck_cards_too_many)
        
        # Then: Should report error for too many cards
        assert not result_many.is_valid
        assert "106 cards" in str(result_many.errors)
    
    def test_commander_format_singleton_violations(self):
        """Given-When-Then: Test singleton rule violations."""
        # Given: Deck with non-basic land duplicates
        deck_cards = {
            "Lightning Bolt": 4,  # Violation - non-basic duplicate
            "Forest": 10,  # OK - basic land
            "Command Tower": 2,  # Violation - non-basic duplicate
            **{f"Card {i}": 1 for i in range(85)}  # Fill to 99 total
        }
        
        # When: Validating singleton compliance
        validator = DeckValidator("Commander")
        result = validator.validate_commander_format("Atraxa", deck_cards)
        
        # Then: Should report singleton violations
        assert not result.is_valid
        assert "Lightning Bolt" in str(result.errors)
        assert "Command Tower" in str(result.errors)
        assert "4 times" in str(result.errors)
        assert "2 times" in str(result.errors)
        # Forest should be OK (basic land)
        assert "Forest" not in str(result.errors)
    
    def test_commander_duplicate_removal_warning(self):
        """Given-When-Then: Test commander duplicate removal warning."""
        # Given: Valid deck with commander quantity removed
        deck_cards = {f"Card {i}": 1 for i in range(99)}
        
        # When: Validating with commander removal noted
        validator = DeckValidator("Commander")
        result = validator.validate_commander_format("Atraxa", deck_cards, commander_quantity_removed=2)
        
        # Then: Should warn about commander removal
        assert result.is_valid
        assert len(result.warnings) > 0
        assert "Removed 2 copies of commander" in str(result.warnings)
    
    def test_deck_structure_validation(self):
        """Given-When-Then: Test general deck structure validation."""
        # Given: Various deck structures
        empty_deck = {}
        tiny_deck = {"Forest": 1, "Lightning Bolt": 1}
        normal_deck = {f"Card {i}": 1 for i in range(60)}
        
        validator = DeckValidator()
        
        # When: Validating empty deck
        result_empty = validator.validate_deck_structure(empty_deck)
        
        # Then: Should report error for empty deck
        assert not result_empty.is_valid
        assert "Deck cannot be empty" in str(result_empty.errors)
        
        # When: Validating tiny deck
        result_tiny = validator.validate_deck_structure(tiny_deck)
        
        # Then: Should warn about small deck
        assert result_tiny.is_valid  # Valid but warnings
        assert "Very small deck" in str(result_tiny.warnings)
        assert "Low card diversity" in str(result_tiny.warnings)
        
        # When: Validating normal deck
        result_normal = validator.validate_deck_structure(normal_deck)
        
        # Then: Should pass without issues
        assert result_normal.is_valid
        assert len(result_normal.errors) == 0
    
    def test_high_quantity_warnings(self):
        """Given-When-Then: Test high quantity warnings."""
        # Given: Deck with very high quantities
        deck_cards = {
            "Forest": 25,  # Very high quantity
            "Lightning Bolt": 1,
        }
        
        # When: Validating deck structure
        validator = DeckValidator()
        result = validator.validate_deck_structure(deck_cards)
        
        # Then: Should warn about high quantities
        assert result.is_valid
        assert "Very high quantity" in str(result.warnings)
        assert "Forest" in str(result.warnings)
        assert "25 copies" in str(result.warnings)


class TestFormatValidator:
    """Test comprehensive format validation."""
    
    def test_full_valid_commander_deck(self):
        """Given-When-Then: Test complete valid Commander deck validation."""
        # Given: Valid Commander deck list
        commander = "Atraxa, Praetors' Voice"
        decklist = [f"1 Card {i}" for i in range(99)]
        
        # When: Performing full validation
        validator = FormatValidator("Commander")
        result = validator.validate_full_deck(commander, decklist)
        
        # Then: Should pass all validation
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_full_invalid_commander_deck(self):
        """Given-When-Then: Test comprehensive validation with multiple issues."""
        # Given: Problematic Commander deck
        commander = "Atraxa, Praetors' Voice"
        decklist = [
            "",  # Empty entry
            "0 Lightning Bolt",  # Invalid quantity
            "4 Sol Ring",  # Singleton violation
            "Forest",  # Valid entry
            "2x Command Tower",  # Valid entry
            # Missing cards to reach 99
        ]
        
        # When: Performing full validation
        validator = FormatValidator("Commander")
        result = validator.validate_full_deck(commander, decklist)
        
        # Then: Should catch multiple issues
        assert not result.is_valid
        assert len(result.errors) > 0
        assert len(result.warnings) > 0
        
        # Should catch quantity issues
        assert any("Invalid quantity 0" in error for error in result.errors)
        # Should catch empty entry
        assert any("Empty entry" in warning for warning in result.warnings)
        # Should catch deck size issues
        assert any("cards" in error for error in result.errors)
    
    def test_validation_with_empty_commander(self):
        """Given-When-Then: Test validation with missing commander."""
        # Given: Empty commander
        commander = ""
        decklist = ["1 Forest", "1 Lightning Bolt"]
        
        # When: Performing full validation
        validator = FormatValidator("Commander")
        result = validator.validate_full_deck(commander, decklist)
        
        # Then: Should report commander error
        assert not result.is_valid
        assert "Commander is required" in str(result.errors)


class TestValidationResult:
    """Test ValidationResult helper class."""
    
    def test_validation_result_initialization(self):
        """Given-When-Then: Test ValidationResult initialization."""
        # Given: New ValidationResult
        # When: Creating ValidationResult
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Then: Should initialize correctly
        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_add_error_changes_validity(self):
        """Given-When-Then: Test that adding error changes validity."""
        # Given: Valid ValidationResult
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # When: Adding an error
        result.add_error("Test error")
        
        # Then: Should become invalid
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "Test error" in result.errors
    
    def test_add_warning_preserves_validity(self):
        """Given-When-Then: Test that adding warning preserves validity."""
        # Given: Valid ValidationResult
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # When: Adding a warning
        result.add_warning("Test warning")
        
        # Then: Should remain valid
        assert result.is_valid
        assert len(result.warnings) == 1
        assert "Test warning" in result.warnings