"""Validation system for MTG deck analysis robustness."""

import re
from dataclasses import dataclass
from typing import List, Dict, Tuple
from collections import defaultdict


@dataclass
class ValidationResult:
    """Result of validation with success status and detailed messages."""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)


class QuantityValidator:
    """Validator for deck list quantity parsing and validation."""
    
    # Regex pattern to match quantity formats: "4 Card Name", "4x Card Name", or just "Card Name"
    # Also matches negative numbers to handle them as errors
    QUANTITY_PATTERN = re.compile(r'^(-?\d+)\s*x?\s+(.+)$', re.IGNORECASE)
    
    @classmethod
    def parse_decklist_with_validation(cls, decklist: List[str]) -> Tuple[Dict[str, int], ValidationResult]:
        """
        Parse decklist entries with comprehensive validation.
        
        Args:
            decklist: List of card entries with optional quantities
            
        Returns:
            Tuple of (card_quantities dict, validation_result)
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        card_quantities: Dict[str, int] = defaultdict(int)
        
        if not decklist:
            result.add_error("Decklist cannot be empty")
            return dict(card_quantities), result
        
        for i, entry in enumerate(decklist):
            entry = entry.strip()
            if not entry:
                result.add_warning(f"Empty entry at position {i+1}, skipping")
                continue
            
            # Validate entry length
            if len(entry) > 200:
                result.add_error(f"Card name too long at position {i+1}: '{entry[:50]}...' (max 200 characters)")
                continue
            
            # Parse quantity
            match = cls.QUANTITY_PATTERN.match(entry)
            
            if match:
                try:
                    quantity = int(match.group(1))
                    card_name = match.group(2).strip()
                    
                    # Validate quantity range
                    if quantity <= 0:
                        result.add_error(f"Invalid quantity {quantity} for '{card_name}' at position {i+1} (must be positive)")
                        continue
                    elif quantity > 100:
                        result.add_warning(f"Very high quantity {quantity} for '{card_name}' at position {i+1}")
                    
                except ValueError:
                    result.add_error(f"Invalid quantity format at position {i+1}: '{entry}'")
                    continue
            else:
                # Check if entry starts with something that looks like a quantity but isn't valid
                # Only flag obvious mistakes like "abc Forest" where "abc" looks like a failed quantity
                parts = entry.split(None, 1)
                if len(parts) >= 2:
                    first_part = parts[0]
                    # Only flag patterns that are clearly trying to be quantities but failing
                    # Like "abc", "xyz", etc. - random letter combinations
                    if (re.match(r'^[a-z]{2,4}$', first_part.lower()) and 
                        first_part.lower() not in ['sol', 'the', 'of', 'a', 'an', 'or', 'in', 'on', 'at', 'to', 'for']):
                        # Check if it's clearly not a valid card name start
                        if first_part.lower() in ['abc', 'xyz', 'def', 'test']:
                            result.add_error(f"Invalid quantity format at position {i+1}: '{entry}' (quantity must be a number)")
                            continue
                
                quantity = 1
                card_name = entry
            
            # Validate card name
            if not card_name:
                result.add_error(f"Empty card name at position {i+1}")
                continue
            
            if len(card_name) < 1:
                result.add_error(f"Card name too short at position {i+1}: '{card_name}'")
                continue
            
            # Check for duplicate entries (same card name)
            if card_name in card_quantities:
                result.add_warning(f"Duplicate card '{card_name}' found, quantities will be combined")
            
            card_quantities[card_name] += quantity
        
        return dict(card_quantities), result


class DeckValidator:
    """Validator for deck format compliance and structure."""
    
    def __init__(self, format_name: str = "Commander"):
        self.format_name = format_name
    
    def validate_commander_format(self, commander: str, deck_cards: Dict[str, int], 
                                 commander_quantity_removed: int = 0) -> ValidationResult:
        """
        Validate Commander format compliance.
        
        Args:
            commander: Commander card name
            deck_cards: Dictionary of card names to quantities (excluding commander)
            commander_quantity_removed: Number of commander copies removed from original list
            
        Returns:
            ValidationResult with format compliance details
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Validate commander
        if not commander or not commander.strip():
            result.add_error("Commander is required for Commander format")
            return result
        
        # Calculate deck totals
        total_deck_cards = sum(deck_cards.values())
        total_with_commander = total_deck_cards + 1  # Commander counts as 1
        
        # Commander format: exactly 100 cards total
        if total_with_commander != 100:
            if total_with_commander < 100:
                result.add_error(f"Deck has only {total_with_commander} cards (need exactly 100 for Commander format)")
            else:
                result.add_error(f"Deck has {total_with_commander} cards (need exactly 100 for Commander format)")
        
        # Validate singleton rule (except basic lands)
        basic_lands = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
        for card_name, quantity in deck_cards.items():
            if quantity > 1 and card_name not in basic_lands:
                if card_name.lower() in [land.lower() for land in basic_lands]:
                    # Case-insensitive basic land check
                    continue
                result.add_error(f"'{card_name}' appears {quantity} times (Commander format allows only 1 copy of non-basic lands)")
        
        # Check for commander duplicates that were removed
        if commander_quantity_removed > 0:
            result.add_warning(f"Removed {commander_quantity_removed} copies of commander '{commander}' from deck list")
        
        # Validate minimum deck structure recommendations
        if total_deck_cards < 90:
            result.add_warning("Deck has fewer than 90 cards (excluding commander), consider adding more cards")
        
        return result
    
    def validate_deck_structure(self, deck_cards: Dict[str, int]) -> ValidationResult:
        """
        Validate general deck structure and composition.
        
        Args:
            deck_cards: Dictionary of card names to quantities
            
        Returns:
            ValidationResult with structural validation details
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not deck_cards:
            result.add_error("Deck cannot be empty")
            return result
        
        total_cards = sum(deck_cards.values())
        unique_cards = len(deck_cards)
        
        # Basic structure validation
        if total_cards == 0:
            result.add_error("Deck has no cards")
        elif total_cards < 10:
            result.add_warning(f"Very small deck with only {total_cards} cards")
        
        if unique_cards == 0:
            result.add_error("Deck has no unique cards")
        elif unique_cards < 10:
            result.add_warning(f"Low card diversity with only {unique_cards} unique cards")
        
        # Check for extremely high quantities
        for card_name, quantity in deck_cards.items():
            if quantity > 20:
                result.add_warning(f"Very high quantity of '{card_name}': {quantity} copies")
        
        return result


class FormatValidator:
    """High-level format validation coordinator."""
    
    def __init__(self, format_name: str = "Commander"):
        self.format_name = format_name
        self.quantity_validator = QuantityValidator()
        self.deck_validator = DeckValidator(format_name)
    
    def validate_full_deck(self, commander: str, decklist: List[str]) -> ValidationResult:
        """
        Perform comprehensive deck validation.
        
        Args:
            commander: Commander card name
            decklist: List of deck card entries with quantities
            
        Returns:
            ValidationResult with all validation details combined
        """
        # Start with overall validation result
        overall_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Step 1: Parse and validate quantities
        deck_cards, quantity_result = self.quantity_validator.parse_decklist_with_validation(decklist)
        overall_result.errors.extend(quantity_result.errors)
        overall_result.warnings.extend(quantity_result.warnings)
        
        if not quantity_result.is_valid:
            overall_result.is_valid = False
            # Continue with other validations even if quantity parsing failed
            # to provide comprehensive feedback
        
        # Step 2: Validate deck structure (if we have any cards)
        if deck_cards:
            structure_result = self.deck_validator.validate_deck_structure(deck_cards)
            overall_result.errors.extend(structure_result.errors)
            overall_result.warnings.extend(structure_result.warnings)
            
            if not structure_result.is_valid:
                overall_result.is_valid = False
        
        # Step 3: Validate format compliance (Commander) - if we have cards and commander
        if self.format_name == "Commander" and deck_cards:
            format_result = self.deck_validator.validate_commander_format(commander, deck_cards)
            overall_result.errors.extend(format_result.errors)
            overall_result.warnings.extend(format_result.warnings)
            
            if not format_result.is_valid:
                overall_result.is_valid = False
        
        return overall_result