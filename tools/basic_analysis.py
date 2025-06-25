"""Basic MTG analysis tools for mana curve, lands, and card types."""

from fastmcp import FastMCP
import httpx
from typing import List
from collections import Counter, defaultdict
from .utils import get_cached_card
from .scryfall_server import batch_lookup_cards

basic_analysis_server: FastMCP = FastMCP(
    "MTG Basic Analysis Server", dependencies=["httpx"]
)


@basic_analysis_server.tool()
async def calculate_mana_curve(card_names: List[str]) -> str:
    """
    Calculate mana curve for deck building and mana base decisions.

    WHEN TO USE: When analyzing deck speed, mana requirements, or optimizing card costs.
    USE FOR: "My deck is too slow", "what's my curve like?", mana base optimization

    Args:
        card_names: List of Magic card names to analyze

    Returns: Formatted mana curve showing CMC distribution
    """
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        cmc_counter: Counter[float] = Counter()

        # Use batch lookup for better performance
        found_cards, not_found = await batch_lookup_cards(client, card_names)

        for card_data in found_cards:
            if "cmc" in card_data:
                cmc = card_data["cmc"]
                cmc_counter[cmc] += 1
    result = ["**Mana Curve:**"]
    for cmc in sorted(cmc_counter):
        result.append(f"CMC {cmc}: {cmc_counter[cmc]}")
    if not_found:
        result.append(f"\n**Cards Not Found:** {', '.join(not_found)}")
    return "\n".join(result)


@basic_analysis_server.tool()
async def analyze_lands(card_names: List[str]) -> str:
    """
    Analyze land base and mana production by color.

    WHEN TO USE: For mana base evaluation, color fixing analysis, or land count questions.
    USE FOR: "Is my mana base good?", "do I have enough lands?", "can I cast my spells?"

    Args:
        card_names: List of card names (will identify lands automatically)

    Returns: Land count and color production analysis
    """
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        land_count = 0
        color_production: defaultdict[str, int] = defaultdict(int)
        not_found = []
        for card_name in card_names:
            card_data = await get_cached_card(client, card_name.strip())
            if card_data:
                type_line = card_data.get("type_line", "").lower()
                if "land" in type_line:
                    land_count += 1
                    oracle_text = card_data.get("oracle_text", "")
                    for color, symbol in zip(
                        ["White", "Blue", "Black", "Red", "Green"],
                        ["{W}", "{U}", "{B}", "{R}", "{G}"],
                    ):
                        if symbol in oracle_text:
                            color_production[color] += 1
            else:
                not_found.append(card_name)
    result = [f"**Land Analysis:**\nTotal Lands: {land_count}"]
    for color in ["White", "Blue", "Black", "Red", "Green"]:
        result.append(f"{color} mana sources: {color_production[color]}")
    if not_found:
        result.append(f"\n**Cards Not Found:** {', '.join(not_found)}")
    return "\n".join(result)


@basic_analysis_server.tool()
async def analyze_card_types(card_names: List[str]) -> str:
    """
    Analyze card type distribution and deck composition - counts ALL card types found.

    WHEN TO USE: For deck composition analysis or format guideline compliance.
    USE FOR: "what types of cards do I have?", creature count, spell distribution, land analysis

    Args:
        card_names: List of card names to categorize

    Returns: Complete type breakdown with Commander format guidelines and ✓/⚠ indicators
    """
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        type_counts: defaultdict[str, int] = defaultdict(int)
        detailed_types: defaultdict[str, int] = defaultdict(int)
        not_found = []
        
        for card_name in card_names:
            card_data = await get_cached_card(client, card_name.strip())
            if card_data:
                type_line = card_data.get("type_line", "")
                primary_types = type_line.split(" — ")[0].strip()
                
                # Split by spaces and count each individual type
                individual_types = primary_types.split()
                for card_type in individual_types:
                    # Clean up the type (remove trailing punctuation)
                    clean_type = card_type.strip().rstrip(',')
                    if clean_type:  # Only count non-empty types
                        type_counts[clean_type] += 1
                
                # Also track the full type line for detailed analysis
                detailed_types[primary_types] += 1
            else:
                not_found.append(card_name)
    # Count actual cards analyzed (not type instances, since cards can have multiple types)
    total_cards = len([name for name in card_names if name.strip()])
    cards_found = total_cards - len(not_found)
    
    result = ["**Card Type Distribution:**"]
    result.append(f"Total Cards Analyzed: {cards_found} of {total_cards}")
    
    # Show all types found, sorted by count
    sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])
    result.append("\n**All Card Types Found:**")
    for card_type, count in sorted_types:
        if count > 0:
            percentage = (count / cards_found) * 100 if cards_found > 0 else 0
            result.append(f"{card_type}: {count} ({percentage:.1f}%)")
    
    # Commander format guidelines for key types
    result.append("\n**Commander Deck Guidelines:**")
    creature_count = type_counts.get("Creature", 0)
    land_count = type_counts.get("Land", 0)
    instant_count = type_counts.get("Instant", 0)
    sorcery_count = type_counts.get("Sorcery", 0)
    artifact_count = type_counts.get("Artifact", 0)
    enchantment_count = type_counts.get("Enchantment", 0)
    
    if creature_count > 0:
        if 25 <= creature_count <= 35:
            result.append(f"✓ Creatures ({creature_count}): Good range (25-35 typical)")
        elif creature_count < 25:
            result.append(f"⚠ Creatures ({creature_count}): Below typical range (25-35)")
        else:
            result.append(f"⚠ Creatures ({creature_count}): Above typical range (25-35)")
    
    if land_count > 0:
        if 36 <= land_count <= 40:
            result.append(f"✓ Lands ({land_count}): Good range (36-40 typical)")
        elif land_count < 36:
            result.append(f"⚠ Lands ({land_count}): Below typical range (36-40)")
        else:
            result.append(f"⚠ Lands ({land_count}): Above typical range (36-40)")
    
    # Additional guidance for other card types
    spells_total = instant_count + sorcery_count
    if spells_total > 0:
        result.append(f"• Instants + Sorceries: {spells_total} ({instant_count} instants, {sorcery_count} sorceries)")
    
    if artifact_count > 0:
        result.append(f"• Artifacts: {artifact_count}")
        
    if enchantment_count > 0:
        result.append(f"• Enchantments: {enchantment_count}")
    result.append("\n**Most Common Type Lines:**")
    sorted_detailed = sorted(detailed_types.items(), key=lambda x: -x[1])[:8]
    for type_line, count in sorted_detailed:
        if count > 1:
            result.append(f"{type_line}: {count}")
    if not_found:
        result.append(f"\n**Cards Not Found:** {', '.join(not_found)}")
    return "\n".join(result)
