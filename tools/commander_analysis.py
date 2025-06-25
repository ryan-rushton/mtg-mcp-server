"""Commander-specific analysis tools providing card data for LLM categorization."""

from fastmcp import FastMCP
import httpx
import json
import re
from typing import List, Dict
from collections import defaultdict
from .utils import get_cached_card
from .scryfall_server import batch_lookup_cards
from config import config

commander_analysis_server: FastMCP = FastMCP(
    "MTG Commander Analysis Server", dependencies=["httpx"]
)


def parse_decklist_with_quantities(decklist: List[str]) -> Dict[str, int]:
    """
    Parse decklist entries that may include quantities.
    
    Handles formats like:
    - "4 Forest" -> {"Forest": 4}  
    - "Forest" -> {"Forest": 1}
    - "2x Lightning Bolt" -> {"Lightning Bolt": 2}
    
    Args:
        decklist: List of card entries with optional quantities
        
    Returns:
        Dictionary mapping card names to quantities
    """
    card_quantities: Dict[str, int] = defaultdict(int)
    
    for entry in decklist:
        entry = entry.strip()
        if not entry:
            continue
            
        # Pattern to match quantity formats: "4 Card Name", "4x Card Name", or just "Card Name"
        match = re.match(r'^(\d+)\s*x?\s+(.+)$', entry, re.IGNORECASE)
        
        if match:
            quantity = int(match.group(1))
            card_name = match.group(2).strip()
        else:
            quantity = 1
            card_name = entry
            
        card_quantities[card_name] += quantity
    
    return dict(card_quantities)


@commander_analysis_server.tool()
async def analyze_commander_deck(commander: str, decklist: List[str]) -> str:
    """
    Fetch card data for Commander deck analysis - LLM categorizes cards and lists them by category.

    USE THIS TOOL when users ask about:
    - Commander deck analysis or review
    - Deck balance or improvement suggestions
    - Command Zone template evaluation
    - "How good is my deck?" questions

    This tool provides:
    1. Commander card data (name, colors, type, text)
    2. All deck card data with relevant properties
    3. Command Zone framework targets for reference
    4. Detailed instructions for LLM to categorize and list cards by category

    The LLM will categorize cards and MUST list specific cards in each category.
    CRITICAL: Cards should appear in MULTIPLE categories when they serve multiple functions:
    - Ramp (target: 10-12+ cards) - mana acceleration and fixing
    - Card Advantage (target: 12+ cards) - card draw and selection
    - Targeted Disruption (target: 12 cards) - single-target removal/interaction
    - Mass Disruption (target: 6 cards) - board wipes and mass effects
    - Lands (target: 38 cards) - all land cards
    - Plan Cards (target: ~30 cards) - theme/strategy cards

    Expected LLM output format: "Category (X/Y): card1, card2, card3..."
    Multi-category examples: Skullclamp (Card Advantage + Targeted Disruption), 
    Cultivate (Ramp + Card Advantage), Beast Within (Targeted Disruption + Ramp)

    Args:
        commander: The commander card name (e.g. "Atraxa, Praetors' Voice")
        decklist: List of 99 card names in the deck (excluding commander)

    Returns: JSON object with card data for analysis including:
        - commander: name, colors, color identity, type, oracle text
        - deck: card counts and format validation
        - cards: list of all cards with name, type, oracle text, mana cost, colors
        - command_zone_targets: reference targets for each category
        - instructions: detailed requirements for LLM categorization and formatting
    """
    if not commander or not decklist:
        return "Error: Both commander and decklist are required."

    # Parse decklist with quantities
    card_quantities = parse_decklist_with_quantities(decklist)
    unique_card_names = list(card_quantities.keys())
    
    # Look up commander first
    async with httpx.AsyncClient() as client:
        commander_data = await get_cached_card(client, commander.strip())
        if not commander_data:
            return f"Error: Could not find commander '{commander}'. Please check the spelling."

        # Look up all unique cards in the decklist using batch operations
        found_cards, not_found = await batch_lookup_cards(client, unique_card_names)

        if not_found:
            return f"Error: Could not find the following cards: {', '.join(not_found[:10])}{'...' if len(not_found) > 10 else ''}. Please check spellings."

    # Extract commander info
    commander_name = commander_data.get("name", commander)
    commander_colors = commander_data.get("color_identity", [])
    color_names = []
    color_map = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
    for color in commander_colors:
        if color in color_map:
            color_names.append(color_map[color])

    # Check if commander is in the decklist and remove it
    commander_in_deck = False
    commander_quantity_in_deck = 0
    
    for card_data in found_cards:
        card_name = card_data.get("name", "")
        if card_name == commander_name:
            commander_in_deck = True
            commander_quantity_in_deck = card_quantities.get(card_name, 1)
            # Remove commander from quantities
            del card_quantities[card_name]
            break
    
    # Prepare card data for LLM analysis with quantities (excluding commander)
    cards_data = []
    total_deck_cards = 0
    
    for card_data in found_cards:
        card_name = card_data.get("name", "")
        
        # Skip commander - it shouldn't be in the 99
        if card_name == commander_name:
            continue
            
        quantity = card_quantities.get(card_name, 0)
        if quantity == 0:  # Card was removed (commander) or not found
            continue
            
        total_deck_cards += quantity
        
        card_info = {
            "name": card_name,
            "quantity": quantity,
            "type_line": card_data.get("type_line", ""),
            "oracle_text": card_data.get("oracle_text", ""),
            "mana_cost": card_data.get("mana_cost", ""),
            "cmc": card_data.get("cmc", 0),
            "colors": card_data.get("colors", []),
            "color_identity": card_data.get("color_identity", [])
        }
        cards_data.append(card_info)

    # Get Command Zone targets from config
    cz = config.command_zone
    command_zone_targets = {
        "Ramp": {
            "target": cz.ramp_target,
            "optimal": cz.ramp_optimal,
            "description": "Mana acceleration and fixing (Sol Ring, Cultivate, etc.)"
        },
        "Card Advantage": {
            "target": cz.card_advantage_target,
            "optimal": cz.card_advantage_optimal,
            "description": "Card draw and selection (Rhystic Study, Phyrexian Arena, etc.)"
        },
        "Targeted Disruption": {
            "target": cz.targeted_disruption_target,
            "optimal": cz.targeted_disruption_target,
            "description": "Single-target removal/interaction (Swords to Plowshares, Counterspell, etc.)"
        },
        "Mass Disruption": {
            "target": cz.mass_disruption_target,
            "optimal": cz.mass_disruption_target,
            "description": "Board wipes and mass effects (Wrath of God, Cyclonic Rift, etc.)"
        },
        "Lands": {
            "target": cz.lands_target,
            "optimal": cz.lands_target,
            "description": "All land cards including basics and nonbasics"
        },
        "Plan Cards": {
            "target": cz.plan_cards_target,
            "optimal": cz.plan_cards_target + 5,
            "description": "Theme/strategy cards that advance your deck's game plan"
        }
    }

    # Build structured JSON response with card data for LLM analysis
    analysis_result = {
        "commander": {
            "name": commander_name,
            "type_line": commander_data.get("type_line", ""),
            "oracle_text": commander_data.get("oracle_text", ""),
            "colors": color_names,
            "color_identity": commander_colors,
            "mana_cost": commander_data.get("mana_cost", ""),
            "cmc": commander_data.get("cmc", 0)
        },
        "deck": {
            "total_cards": total_deck_cards + 1,  # Including commander
            "deck_cards": total_deck_cards,  # Excluding commander
            "unique_cards": len(cards_data),  # Only non-commander cards
            "format_valid": total_deck_cards == 99,
            "commander_in_original_list": commander_in_deck,
            "commander_quantity_removed": commander_quantity_in_deck if commander_in_deck else 0
        },
        "cards": cards_data,
        "command_zone_targets": command_zone_targets,
        "instructions": {
            "task": "Categorize the provided cards into Command Zone framework categories and provide detailed analysis",
            "categories": list(command_zone_targets.keys()),
            "requirements": [
                "MUST list the specific cards you assigned to each category",
                "MUST show card counts for each category with target comparisons", 
                "MUST use the format: 'Category (X/Y): card1, card2, card3...' where X is current count and Y is target",
                "CRITICAL: Cards can and should belong to multiple categories - count them in EVERY relevant category",
                "IMPORTANT: Look for clues about the deck's strategy in the user's original request or card choices - consider this when categorizing Plan Cards",
                "MUST provide improvement recommendations with specific card suggestions that fit the apparent deck strategy",
                "Explain your reasoning for borderline categorization decisions, especially how cards relate to the deck's apparent theme/strategy",
                "Consider card quantities when analyzing deck balance",
                "Examples of multi-category cards: Skullclamp (Card Advantage + can kill small creatures), Cultivate (Ramp + Card Advantage), Beast Within (Targeted Disruption + gives opponent Ramp), Deadly Dispute (Card Advantage + requires sacrifice), Pitiless Plunderer (Ramp when creatures die + Plan Card), Idol of Oblivion (Card Advantage + Plan Card for token decks)"
            ],
            "example_format": "Ramp (7/10-12): Sol Ring, Cultivate, Nature's Lore, Arcane Signet...",
            "multi_category_reminder": "IMPORTANT: Many cards serve multiple functions! Count them in ALL applicable categories. For example: Skullclamp should appear in BOTH Card Advantage AND potentially Targeted Disruption (if you consider equipment that kills creatures as removal).",
            "note": "Be specific about which cards you categorized where, and explain any borderline decisions. DO NOT try to put each card in only one category - versatile cards should appear in multiple categories."
        }
    }

    return json.dumps(analysis_result, indent=2)
