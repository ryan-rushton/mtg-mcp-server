from fastmcp import FastMCP
import httpx
from typing import List
from collections import Counter, defaultdict
from .utils import get_cached_card
from .scryfall_server import batch_lookup_cards

analysis_server: FastMCP = FastMCP("MTG Analysis Server", dependencies=["httpx"])

# Add Command Zone template as a resource
@analysis_server.resource("file://command-zone-template")
def get_command_zone_template() -> str:
    """
    The official Command Zone podcast deckbuilding template for Commander decks.
    
    This resource provides the complete framework for building balanced, functional
    Commander decks with proper interaction and consistency.
    """
    try:
        with open("COMMAND_ZONE_TEMPLATE.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return """# Command Zone Template (Fallback)
        
## Core Categories:
- **Lands**: 38 (includes MDFCs, utility lands, land cyclers)
- **Card Advantage**: 12+ (true draw, impulse, exile-to-play)
- **Ramp**: 10-12+ (mana acceleration beyond land drops)
- **Targeted Disruption**: 12 (removal, counters, bounce, graveyard hate)
- **Mass Disruption**: 6 (wraths, artifact wipes, fogs, stax)
- **Plan/Synergy Cards**: ~30 (win conditions, synergy pieces, combos)

## Key Principles:
- Cards can overlap categories (MDFCs, ETB creatures, modal spells)
- Template is a guideline - adjust after playtesting
- Don't neglect fundamentals: ramp, draw, interaction, disruption
"""

# Add Command Zone deck building prompts
@analysis_server.prompt("analyze-commander-deck")
def analyze_commander_deck_prompt() -> str:
    """
    Prompt for analyzing a Commander deck against the Command Zone template.
    
    This prompt guides the LLM to properly categorize cards and identify
    deck balance issues using the official Command Zone framework.
    """
    return """You are analyzing a Commander deck using the Command Zone podcast's deckbuilding template.

## Your Task:
1. Categorize each card into Command Zone categories (cards can fit multiple categories)
2. Use the analysis_analyze_commander_deck tool with your categorizations
3. Provide specific improvement suggestions based on the analysis

## Command Zone Categories:
- **Lands (38)**: All lands including MDFCs, utility lands, land cyclers
- **Card Advantage (12+)**: True card draw, impulse draw, exile-to-play (NOT card selection like Faithless Looting)
- **Ramp (10-12+)**: Mana acceleration beyond land drops (rocks, dorks, ramp spells - NOT temporary burst)
- **Targeted Disruption (12)**: One-for-one answers (removal, counters, bounce, graveyard hate)
- **Mass Disruption (6)**: Broad answers (wraths, artifact wipes, fogs, stax, Teferi's Protection)
- **Plan/Synergy Cards (~30)**: Win conditions, synergy pieces, combos, flavor picks

## Key Principles:
- Look for overlap and efficiency (MDFCs, ETB creatures, modal spells)
- Prioritize consistency - aim for higher counts in ramp/draw for reliability
- Template is a guideline - adjust based on strategy and meta
- Don't neglect fundamentals for flashy synergy pieces

Categorize thoughtfully and explain your reasoning for borderline cards."""

@analysis_server.prompt("suggest-deck-improvements")
def suggest_deck_improvements_prompt() -> str:
    """
    Prompt for suggesting specific improvements to a Commander deck.
    
    This prompt helps the LLM provide actionable upgrade suggestions
    based on Command Zone principles and deck analysis results.
    """
    return """You are suggesting improvements to a Commander deck based on Command Zone principles.

## Analysis Process:
1. First analyze the deck with the Command Zone template
2. Identify the most critical gaps or imbalances
3. Suggest specific cards to add/remove with clear reasoning
4. Consider budget, power level, and deck theme

## Improvement Priorities:
1. **Fix Critical Gaps**: Missing ramp, draw, or interaction
2. **Increase Efficiency**: Cards that serve multiple roles
3. **Enhance Consistency**: More reliable card advantage and ramp
4. **Optimize Mana Base**: Better fixing and utility lands
5. **Strengthen Game Plan**: More focused synergy pieces

## Suggestion Format:
**Priority 1 - Critical:**
- Add: [Specific cards] - Reason
- Remove: [Specific cards] - Reason

**Priority 2 - Optimization:**
- Consider: [Alternative cards] - Benefits

**Priority 3 - Long-term:**
- Upgrade path: [Expensive improvements] - Impact

Focus on the most impactful changes first."""

@analysis_server.resource("file://commander-staples")
def get_commander_staples() -> str:
    """
    List of commonly played Commander staples by category.
    
    This resource provides examples of popular cards in each Command Zone category
    to help with deck building and card recommendations.
    """
    return """# Commander Staples by Category

## Ramp (10-12+ cards)
**Artifacts:** Sol Ring, Arcane Signet, Fellwar Stone, Talisman cycle, Signet cycle
**Green Spells:** Cultivate, Kodama's Reach, Rampant Growth, Nature's Lore, Three Visits
**Creatures:** Llanowar Elves, Birds of Paradise, Farhaven Elf, Wood Elves

## Card Advantage (12+ cards)  
**Enchantments:** Rhystic Study, Phyrexian Arena, Sylvan Library, Mystic Remora
**Creatures:** Beast Whisperer, Guardian Project, Mentor of the Meek
**Spells:** Harmonize, Sign in Blood, Read the Bones, Brainstorm

## Targeted Disruption (12 cards)
**Removal:** Swords to Plowshares, Path to Exile, Beast Within, Chaos Warp
**Counters:** Counterspell, Swan Song, Negate, Dispel  
**Versatile:** Assassin's Trophy, Generous Gift, Rapid Hybridization

## Mass Disruption (6 cards)
**Board Wipes:** Wrath of God, Day of Judgment, Blasphemous Act, Toxic Deluge
**Protection:** Teferi's Protection, Boros Charm, Heroic Intervention
**Utility:** Cyclonic Rift, Austere Command

## Essential Lands
**Fixing:** Command Tower, Exotic Orchard, Reflecting Pool
**Utility:** Reliquary Tower, Ghost Quarter, Strip Mine
**Budget:** Evolving Wilds, Terramorphic Expanse, basics

## Utility/Staples
**Protection:** Lightning Greaves, Swiftfoot Boots, Mother of Runes
**Recursion:** Eternal Witness, Regrowth, Sun Titan
**Card Selection:** Sensei's Divining Top, Scroll Rack
"""


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
            card_data = await get_cached_card(client, card_name.strip())
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
            card_data = await get_cached_card(client, card_name.strip())
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
async def analyze_commander_deck(
    ramp: List[str] = None,
    card_advantage: List[str] = None, 
    targeted_disruption: List[str] = None,
    mass_disruption: List[str] = None,
    lands: List[str] = None,
    plan_cards: List[str] = None
) -> str:
    """
    Analyze a Commander deck using the official Command Zone deckbuilding template.
    
    This tool validates categorized cards against the Command Zone podcast's framework for
    building balanced, functional Commander decks with proper interaction and consistency.
    
    Based on the official template:
    - Lands (38): Includes MDFCs, utility lands, land cyclers - start at 38, adjust after testing
    - Card Advantage (12+): True card draw, impulse draw, exile-to-play (NOT just card selection)
    - Ramp (10-12+): Mana acceleration beyond land drops (rocks, dorks, ramp spells)
    - Targeted Disruption (12): One-for-one answers (removal, counters, bounce, graveyard hate)
    - Mass Disruption (6): Broad answers (wraths, artifact wipes, fogs, stax, protection)
    - Plan/Synergy Cards (~30): Win conditions, synergy pieces, combos, flavor picks
    
    Cards can and should overlap categories for efficiency (MDFCs, ETB creatures, modal spells).
    Template totals exceed 100 due to overlap - this is intentional and encouraged.
    
    Args:
        ramp (List[str], optional): Mana acceleration beyond land drops (NOT temporary burst mana)
        card_advantage (List[str], optional): True card advantage (draw, impulse, exile-to-play)
        targeted_disruption (List[str], optional): One-for-one answers and targeted interaction
        mass_disruption (List[str], optional): Broad answers affecting multiple permanents/players
        lands (List[str], optional): All lands including MDFCs, utility lands, land cyclers
        plan_cards (List[str], optional): Win conditions, synergy pieces, combo pieces, theme cards
    
    Returns:
        str: Formatted analysis with Command Zone framework recommendations:
             - Category breakdowns with official target ranges
             - Efficiency and overlap analysis
             - Specific improvement suggestions
             - Balance assessment against proven template
    """
    # Initialize categories with Command Zone template targets
    categories = {
        "Ramp": {"cards": ramp or [], "target": 10, "target_range": "10-12+", "min_target": 10, "optimal_target": 12},
        "Card Advantage": {"cards": card_advantage or [], "target": 12, "target_range": "12+", "min_target": 12, "optimal_target": 15},
        "Targeted Disruption": {"cards": targeted_disruption or [], "target": 12, "target_range": "12", "min_target": 12, "optimal_target": 12},
        "Mass Disruption": {"cards": mass_disruption or [], "target": 6, "target_range": "6", "min_target": 6, "optimal_target": 6},
        "Lands": {"cards": lands or [], "target": 38, "target_range": "38", "min_target": 36, "optimal_target": 38},
        "Plan Cards": {"cards": plan_cards or [], "target": 30, "target_range": "~30", "min_target": 25, "optimal_target": 35}
    }
    
    # Calculate total unique cards (since cards can be in multiple categories)
    all_cards = set()
    for data in categories.values():
        all_cards.update(data["cards"])
    
    total_cards = len(all_cards)
    
    # Build analysis result
    result = ["**Command Zone Deck Analysis:**"]
    result.append(f"Total Unique Cards: {total_cards}")
    result.append("")
    
    # Analyze each category with Command Zone framework
    total_variance = 0
    problem_categories = []
    efficiency_notes = []
    
    for category_name, data in categories.items():
        count = len(data["cards"])
        min_target = data["min_target"]
        optimal_target = data["optimal_target"]
        target_range = data["target_range"]
        
        # Determine status using Command Zone guidelines
        status = ""
        if count >= optimal_target:
            status = " ✓"
        elif count >= min_target:
            status = " ⚡"
        else:
            status = " ⚠️"
            problem_categories.append(f"{category_name} ({count} vs {target_range})")
        
        # Special handling for key categories
        if category_name == "Card Advantage" and count >= 15:
            status = " ✓"
            efficiency_notes.append(f"Excellent card advantage consistency ({count} cards)")
        elif category_name == "Ramp" and count >= 12:
            status = " ✓" 
            efficiency_notes.append(f"Strong ramp consistency ({count} cards)")
        
        variance = abs(count - min_target)
        total_variance += variance
        
        result.append(f"**{category_name}: {count} cards**{status} (Target: {target_range})")
        
        # Show sample cards with more context
        if data["cards"]:
            card_sample = data["cards"][:6]  # Show more cards for better context
            cards_text = ", ".join(card_sample)
            if len(data["cards"]) > 6:
                cards_text += f"... (+{len(data['cards']) - 6} more)"
            result.append(f"  {cards_text}")
        else:
            result.append("  No cards provided in this category")
        result.append("")
    
    # Overall assessment with Command Zone principles
    result.append("**Overall Assessment:**")
    
    # Calculate how many categories meet minimum requirements
    categories_meeting_min = sum(1 for data in categories.values() if len(data["cards"]) >= data["min_target"])
    total_categories = len(categories)
    
    if categories_meeting_min == total_categories:
        result.append("✓ Excellent deck balance following Command Zone framework")
        result.append("All categories meet minimum requirements for functional gameplay")
    elif categories_meeting_min >= total_categories - 1:
        result.append("⚡ Strong deck foundation with minor gaps to address")
    elif categories_meeting_min >= total_categories - 2:
        result.append("⚡ Decent foundation but needs attention in key areas")
    else:
        result.append("⚠️ Major structural issues - deck may struggle with consistency")
        result.append("Focus on fundamentals: ramp, draw, interaction, and lands")
    
    # Add efficiency highlights
    if efficiency_notes:
        result.append("\n**Efficiency Highlights:**")
        for note in efficiency_notes:
            result.append(f"✓ {note}")
    
    # Priority recommendations
    if problem_categories:
        result.append("\n**Priority Improvements:**")
        for i, category in enumerate(problem_categories[:3], 1):  # Top 3 priorities
            result.append(f"{i}. {category}")
    
    # Card overlap guidance
    total_categorized_cards = sum(len(data["cards"]) for data in categories.values())
    if total_categorized_cards > total_cards * 1.2:  # Good overlap
        result.append("\n✓ Good card overlap - many cards serve multiple roles (recommended)")
    elif total_categorized_cards < total_cards * 1.1:  # Low overlap
        result.append("\n⚡ Consider cards that serve multiple roles (MDFCs, ETB creatures, modal spells)")
    
    # Commander format validation
    if total_cards != 100:
        result.append(f"\n⚠️ Total cards ({total_cards}) should equal 100 for Commander format")
        if total_cards < 100:
            result.append("Missing cards may indicate incomplete deck list")
        else:
            result.append("Excess cards need to be cut to 100")
    
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
            card_data = await get_cached_card(client, card_name.strip())
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
