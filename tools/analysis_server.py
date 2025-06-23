from fastmcp import FastMCP
import httpx
from typing import List
from collections import Counter, defaultdict
from .utils import search_card
from .scryfall_server import batch_lookup_cards

analysis_server: FastMCP = FastMCP("MTG Analysis Server", dependencies=["httpx"])


@analysis_server.tool()
async def calculate_mana_curve(card_names: List[str]) -> str:
    """
    Calculate and display the mana curve distribution for a list of Magic: The Gathering cards.
    
    The mana curve shows how many cards exist at each converted mana cost (CMC), which is
    crucial for understanding a deck's speed and mana requirements. This helps with deck
    building decisions and mana base construction.
    
    Args:
        card_names (List[str]): List of card names to analyze for their mana costs.
                               Cards that cannot be found will be listed separately.
                               Examples: ["Lightning Bolt", "Shivan Dragon", "Sol Ring"]
    
    Returns:
        str: Formatted markdown string showing the count of cards at each CMC value,
             sorted by mana cost from lowest to highest. Also lists any cards that
             could not be found.
             
             Example output format:
             **Mana Curve:**
             CMC 0: 2
             CMC 1: 4
             CMC 3: 6
             CMC 6: 1
             
             **Cards Not Found:** Misspelled Card
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


@analysis_server.tool()
async def analyze_lands(card_names: List[str]) -> str:
    """
    Analyze the land base of a Magic: The Gathering deck, counting total lands and mana production.
    
    This tool identifies all lands in the provided card list and analyzes what colors of mana
    they can produce by examining their oracle text for mana symbols. Essential for evaluating
    deck mana bases and color fixing.
    
    Args:
        card_names (List[str]): List of card names to analyze for land content and mana production.
                               Only cards with "Land" in their type line will be counted.
                               Examples: ["Island", "Sacred Foundry", "Command Tower"]
    
    Returns:
        str: Formatted markdown string showing total land count and the number of lands
             that can produce each color of mana. Lists any cards that could not be found.
             
             Example output format:
             **Land Analysis:**
             Total Lands: 8
             White mana sources: 3
             Blue mana sources: 2
             Black mana sources: 0
             Red mana sources: 4
             Green mana sources: 1
             
             **Cards Not Found:** Unknown Land
    """
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        land_count = 0
        color_production: defaultdict[str, int] = defaultdict(int)
        not_found = []
        for card_name in card_names:
            card_data = await search_card(client, card_name.strip())
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


@analysis_server.tool()
async def analyze_color_identity(card_names: List[str]) -> str:
    """
    Analyze the color identity distribution of Magic: The Gathering cards in a deck.
    
    Color identity determines which colors a card belongs to based on mana symbols in its
    mana cost and rules text. This analysis shows both individual color presence and
    color combination patterns, essential for Commander deck building and mana base design.
    
    Args:
        card_names (List[str]): List of card names to analyze for color identity.
                               Each card's color identity will be determined from its mana symbols.
                               Examples: ["Lightning Bolt", "Terminate", "Sol Ring"]
    
    Returns:
        str: Formatted markdown string with comprehensive color analysis including:
             - Total cards analyzed and colorless count
             - Color combination breakdown with percentages  
             - Individual color presence statistics
             - List of any cards that could not be found
             
             Example output format:
             **Color Identity Analysis:**
             Total Cards Analyzed: 10
             Colorless: 2 (20.0%)
             Red: 3 (30.0%)
             Black/Red: 2 (20.0%)
             
             **Individual Color Presence:**
             Red: 5 cards (50.0%)
             Black: 2 cards (20.0%)
    """
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        color_counts: defaultdict[str, int] = defaultdict(int)
        total_colored_cards = 0
        colorless_count = 0
        not_found = []
        color_map = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
        for card_name in card_names:
            card_data = await search_card(client, card_name.strip())
            if card_data:
                color_identity = card_data.get("color_identity", [])
                if color_identity:
                    colors_key = "".join(sorted(color_identity))
                    color_counts[colors_key] += 1
                    total_colored_cards += 1
                else:
                    colorless_count += 1
            else:
                not_found.append(card_name)
    total_cards = total_colored_cards + colorless_count
    result = ["**Color Identity Analysis:**"]
    result.append(f"Total Cards Analyzed: {total_cards}")
    if colorless_count > 0:
        percentage = (colorless_count / total_cards) * 100
        result.append(f"Colorless: {colorless_count} ({percentage:.1f}%)")
    sorted_colors = sorted(color_counts.items(), key=lambda x: (-x[1], x[0]))
    for color_combo, count in sorted_colors:
        color_names = [color_map[c] for c in color_combo]
        color_display = (
            "/".join(color_names) if len(color_names) > 1 else color_names[0]
        )
        percentage = (count / total_cards) * 100
        result.append(f"{color_display}: {count} ({percentage:.1f}%)")
    individual_colors: defaultdict[str, int] = defaultdict(int)
    for color_combo, count in color_counts.items():
        for color in color_combo:
            individual_colors[color] += count
    result.append("\n**Individual Color Presence:**")
    for color_code in ["W", "U", "B", "R", "G"]:
        if color_code in individual_colors:
            count = individual_colors[color_code]
            percentage = (count / total_cards) * 100
            result.append(f"{color_map[color_code]}: {count} cards ({percentage:.1f}%)")
    if not_found:
        result.append(f"\n**Cards Not Found:** {', '.join(not_found)}")
    return "\n".join(result)


@analysis_server.tool()
async def analyze_mana_requirements(card_names: List[str]) -> str:
    """
    Compare mana requirements of spells versus mana production capability of lands in a deck.
    
    This analysis separates lands from spells, examines what colors the lands can produce,
    and compares that to the color requirements of the spells. Provides warnings for
    insufficient mana sources and recommendations for deck building.
    
    Args:
        card_names (List[str]): List of card names to analyze, including both lands and spells.
                               Lands will be identified by "Land" in their type line.
                               Examples: ["Lightning Bolt", "Island", "Sacred Foundry", "Counterspell"]
    
    Returns:
        str: Formatted markdown string with detailed mana analysis including:
             - Total card breakdown (spells vs lands)
             - Color-by-color source ratio analysis with status indicators
             - Overall mana coverage ratio and recommendations
             - Warning symbols: ⚠️ for problems, ⚡ for moderate, ✓ for good coverage
             
             Example output format:
             **Mana Requirements vs Production Analysis:**
             Total Cards: 15 (Spells: 10, Lands: 5)
             
             **Color Requirements vs Land Production:**
             Red: 3/4 sources ✓ Good coverage
             Blue: 0/2 sources ⚠️ NO SOURCES!
             
             **Summary:**
             Overall coverage ratio: 0.45
             ⚡ Moderate mana base - consider adding more sources
    """
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        spell_color_counts: defaultdict[str, int] = defaultdict(int)
        land_color_production: defaultdict[str, int] = defaultdict(int)
        spell_total = 0
        land_total = 0
        not_found = []
        color_map = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
        for card_name in card_names:
            card_data = await search_card(client, card_name.strip())
            if card_data:
                type_line = card_data.get("type_line", "").lower()
                color_identity = card_data.get("color_identity", [])
                if "land" in type_line:
                    land_total += 1
                    oracle_text = card_data.get("oracle_text", "")
                    for color_code, color_name in color_map.items():
                        if f"{{{color_code}}}" in oracle_text:
                            land_color_production[color_code] += 1
                else:
                    if color_identity:
                        spell_total += 1
                        for color in color_identity:
                            spell_color_counts[color] += 1
            else:
                not_found.append(card_name)
    total_cards = spell_total + land_total
    result = ["**Mana Requirements vs Production Analysis:**"]
    result.append(
        f"Total Cards: {total_cards} (Spells: {spell_total}, Lands: {land_total})"
    )
    result.append("\n**Color Requirements vs Land Production:**")
    for color_code in ["W", "U", "B", "R", "G"]:
        color_name = color_map[color_code]
        spell_req = spell_color_counts[color_code]
        land_prod = land_color_production[color_code]
        if spell_req > 0 or land_prod > 0:
            ratio = f"{land_prod}/{spell_req}" if spell_req > 0 else f"{land_prod}/0"
            status = ""
            if spell_req > 0:
                if land_prod == 0:
                    status = " ⚠️ NO SOURCES!"
                elif land_prod < spell_req * 0.3:
                    status = " ⚠️ Low sources"
                elif land_prod >= spell_req * 0.5:
                    status = " ✓ Good coverage"
                else:
                    status = " ⚡ Moderate coverage"
            result.append(f"{color_name}: {ratio} sources{status}")
    total_color_requirements = sum(spell_color_counts.values())
    result.append("\n**Summary:**")
    result.append(f"Total color requirements: {total_color_requirements}")
    result.append(f"Colored mana sources: {sum(land_color_production.values())}")
    if total_color_requirements > 0:
        coverage_ratio = sum(land_color_production.values()) / total_color_requirements
        result.append(f"Overall coverage ratio: {coverage_ratio:.2f}")
        if coverage_ratio < 0.3:
            result.append("⚠️ Very low mana base coverage - add more colored sources")
        elif coverage_ratio < 0.5:
            result.append("⚡ Moderate mana base - consider adding more sources")
        else:
            result.append("✓ Good mana base coverage")
    if not_found:
        result.append(f"\n**Cards Not Found:** {', '.join(not_found)}")
    return "\n".join(result)


@analysis_server.tool()
async def analyze_card_types(card_names: List[str]) -> str:
    """
    Analyze the distribution of card types in a Magic: The Gathering deck.
    
    This tool categorizes cards by their primary types (Creature, Instant, Sorcery, etc.)
    and provides deck composition analysis. Includes Commander format guidelines to help
    evaluate deck balance and suggests improvements based on typical deck construction.
    
    Args:
        card_names (List[str]): List of card names to analyze for type distribution.
                               Cards will be categorized by their primary type line.
                               Examples: ["Lightning Bolt", "Llanowar Elves", "Island", "Sol Ring"]
    
    Returns:
        str: Formatted markdown string with comprehensive type analysis including:
             - Total cards analyzed and percentage breakdown by type
             - Commander deck guidelines comparison with status indicators
             - Most common detailed type lines for reference
             - Recommendations using ✓ for good ranges, ⚠ for outside typical ranges
             
             Example output format:
             **Card Type Distribution:**
             Total Cards Analyzed: 15
             Creature: 6 (40.0%)
             Instant: 4 (26.7%)
             Land: 3 (20.0%)
             Artifact: 2 (13.3%)
             
             **Commander Deck Guidelines:**
             ✓ Creatures (6): Good range (30-40 typical)
             ⚠ Lands (3): Below typical range (36-40)
             
             **Most Common Type Lines:**
             Creature — Human Wizard: 2
             Instant: 4
    """
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        type_counts: defaultdict[str, int] = defaultdict(int)
        detailed_types: defaultdict[str, int] = defaultdict(int)
        not_found = []
        for card_name in card_names:
            card_data = await search_card(client, card_name.strip())
            if card_data:
                type_line = card_data.get("type_line", "")
                primary_types = type_line.split(" — ")[0].strip()
                for card_type in [
                    "Creature",
                    "Instant",
                    "Sorcery",
                    "Enchantment",
                    "Artifact",
                    "Planeswalker",
                    "Land",
                    "Battle",
                ]:
                    if card_type.lower() in primary_types.lower():
                        type_counts[card_type] += 1
                detailed_types[primary_types] += 1
            else:
                not_found.append(card_name)
    total_cards = sum(type_counts.values())
    result = ["**Card Type Distribution:**"]
    result.append(f"Total Cards Analyzed: {total_cards}")
    sorted_types = sorted(type_counts.items(), key=lambda x: -x[1])
    for card_type, count in sorted_types:
        if count > 0:
            percentage = (count / total_cards) * 100 if total_cards > 0 else 0
            result.append(f"{card_type}: {count} ({percentage:.1f}%)")
    result.append("\n**Commander Deck Guidelines:**")
    creature_count = type_counts.get("Creature", 0)
    land_count = type_counts.get("Land", 0)
    if creature_count > 0:
        if 30 <= creature_count <= 40:
            result.append(f"✓ Creatures ({creature_count}): Good range (30-40 typical)")
        elif creature_count < 30:
            result.append(
                f"⚠ Creatures ({creature_count}): Below typical range (30-40)"
            )
        else:
            result.append(
                f"⚠ Creatures ({creature_count}): Above typical range (30-40)"
            )
    if land_count > 0:
        if 36 <= land_count <= 40:
            result.append(f"✓ Lands ({land_count}): Good range (36-40 typical)")
        elif land_count < 36:
            result.append(f"⚠ Lands ({land_count}): Below typical range (36-40)")
        else:
            result.append(f"⚠ Lands ({land_count}): Above typical range (36-40)")
    result.append("\n**Most Common Type Lines:**")
    sorted_detailed = sorted(detailed_types.items(), key=lambda x: -x[1])[:8]
    for type_line, count in sorted_detailed:
        if count > 1:
            result.append(f"{type_line}: {count}")
    if not_found:
        result.append(f"\n**Cards Not Found:** {', '.join(not_found)}")
    return "\n".join(result)
