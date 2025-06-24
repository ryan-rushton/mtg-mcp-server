"""Commander-specific analysis tools and card categorization."""

from fastmcp import FastMCP
import httpx
import json
from typing import List, Set, Dict, Any
from .utils import get_cached_card
from .scryfall_server import batch_lookup_cards
from config import config

commander_analysis_server: FastMCP = FastMCP(
    "MTG Commander Analysis Server", dependencies=["httpx"]
)


def _categorize_cards_automatically(
    found_cards: List[Dict[str, Any]],
) -> Dict[str, List[str]]:
    """Automatically categorize cards into Command Zone framework based on their properties."""
    categories: Dict[str, List[str]] = {
        "ramp": [],
        "card_advantage": [],
        "targeted_disruption": [],
        "mass_disruption": [],
        "lands": [],
        "plan_cards": [],
    }

    for card_data in found_cards:
        name = card_data.get("name", "")
        type_line = card_data.get("type_line", "").lower()
        oracle_text = card_data.get("oracle_text", "").lower()

        # Lands category
        if "land" in type_line:
            categories["lands"].append(name)
            continue

        # Ramp category - mana acceleration
        if any(
            keyword in oracle_text
            for keyword in [
                "add",
                "mana",
                "search",
                "basic land",
                "rampant growth",
                "cultivate",
                "sol ring",
                "signet",
                "talisman",
                "arcane signet",
                "chromatic lantern",
            ]
        ) and not any(
            keyword in oracle_text for keyword in ["draw", "destroy", "counter"]
        ):
            categories["ramp"].append(name)

        # Card advantage - draw and advantage
        elif any(
            keyword in oracle_text
            for keyword in [
                "draw",
                "card",
                "hand",
                "library",
                "exile.*play",
                "impulse",
                "scry 2 or more",
            ]
        ) and not any(keyword in oracle_text for keyword in ["discard", "destroy"]):
            categories["card_advantage"].append(name)

        # Targeted disruption - single target removal/interaction
        elif any(
            keyword in oracle_text
            for keyword in [
                "destroy target",
                "exile target",
                "counter target",
                "return target",
                "bounce",
                "remove",
                "path to exile",
                "swords to plowshares",
            ]
        ):
            categories["targeted_disruption"].append(name)

        # Mass disruption - board wipes and mass effects
        elif any(
            keyword in oracle_text
            for keyword in [
                "destroy all",
                "exile all",
                "return all",
                "wrath",
                "board wipe",
                "each player",
                "each opponent",
                "all creatures",
                "all artifacts",
            ]
        ):
            categories["mass_disruption"].append(name)

        # Everything else goes to plan cards (win conditions, synergy, etc.)
        else:
            categories["plan_cards"].append(name)

    return categories


@commander_analysis_server.tool()
async def analyze_commander_deck(commander: str, decklist: List[str]) -> str:
    """
    Analyze Commander decks against the Command Zone template - automatically categorizes cards.

    USE THIS TOOL when users ask about:
    - Commander deck analysis or review
    - Deck balance or improvement suggestions
    - Command Zone template evaluation
    - "How good is my deck?" questions

    This tool automatically:
    1. Looks up all cards using Scryfall
    2. Categorizes them into Command Zone framework
    3. Provides balance assessment and recommendations

    Args:
        commander: The commander card name (e.g. "Atraxa, Praetors' Voice")
        decklist: List of 99 card names in the deck (excluding commander)

    Returns: JSON object with structured analysis including:
        - commander: name, colors, color identity
        - deck: card counts and format validation
        - categories: Command Zone analysis with counts and status
        - balance_assessment: overall deck balance score
        - recommendations: priority improvements and efficiency notes
        - categorization: automatically sorted cards by category
    """
    if not commander or not decklist:
        return "Error: Both commander and decklist are required."

    # Look up commander first
    async with httpx.AsyncClient() as client:
        commander_data = await get_cached_card(client, commander.strip())
        if not commander_data:
            return f"Error: Could not find commander '{commander}'. Please check the spelling."

        # Look up all cards in the decklist using batch operations
        found_cards, not_found = await batch_lookup_cards(client, decklist)

        if not_found:
            return f"Error: Could not find the following cards: {', '.join(not_found[:10])}{'...' if len(not_found) > 10 else ''}. Please check spellings."

        # Automatically categorize cards based on their properties
        categorized_cards = _categorize_cards_automatically(found_cards)
    # Initialize categories with Command Zone template targets
    cz = config.command_zone
    categories: Dict[str, Dict[str, Any]] = {
        "Ramp": {
            "cards": categorized_cards["ramp"],
            "target": cz.ramp_target,
            "target_range": f"{cz.ramp_target}-{cz.ramp_optimal}+",
            "min_target": cz.ramp_target,
            "optimal_target": cz.ramp_optimal,
        },
        "Card Advantage": {
            "cards": categorized_cards["card_advantage"],
            "target": cz.card_advantage_target,
            "target_range": f"{cz.card_advantage_target}+",
            "min_target": cz.card_advantage_target,
            "optimal_target": cz.card_advantage_optimal,
        },
        "Targeted Disruption": {
            "cards": categorized_cards["targeted_disruption"],
            "target": cz.targeted_disruption_target,
            "target_range": str(cz.targeted_disruption_target),
            "min_target": cz.targeted_disruption_target,
            "optimal_target": cz.targeted_disruption_target,
        },
        "Mass Disruption": {
            "cards": categorized_cards["mass_disruption"],
            "target": cz.mass_disruption_target,
            "target_range": str(cz.mass_disruption_target),
            "min_target": cz.mass_disruption_target,
            "optimal_target": cz.mass_disruption_target,
        },
        "Lands": {
            "cards": categorized_cards["lands"],
            "target": cz.lands_target,
            "target_range": str(cz.lands_target),
            "min_target": cz.lands_target - 2,
            "optimal_target": cz.lands_target,
        },
        "Plan Cards": {
            "cards": categorized_cards["plan_cards"],
            "target": cz.plan_cards_target,
            "target_range": f"~{cz.plan_cards_target}",
            "min_target": cz.plan_cards_target - 5,
            "optimal_target": cz.plan_cards_target + 5,
        },
    }

    # Calculate total unique cards (since cards can be in multiple categories)
    all_cards: Set[str] = set()
    for data in categories.values():
        all_cards.update(data["cards"])

    total_cards = len(all_cards)

    # Add commander info to results
    commander_name = commander_data.get("name", commander)
    commander_colors = commander_data.get("color_identity", [])
    color_names = []
    color_map = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}
    for color in commander_colors:
        if color in color_map:
            color_names.append(color_map[color])

    # Build analysis result
    result = ["**Command Zone Deck Analysis:**"]
    result.append(f"**Commander:** {commander_name}")
    if color_names:
        result.append(f"**Colors:** {'/'.join(color_names)}")
    result.append(f"**Deck Size:** {total_cards + 1} cards (including commander)")
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
            efficiency_notes.append(
                f"Excellent card advantage consistency ({count} cards)"
            )
        elif category_name == "Ramp" and count >= 12:
            status = " ✓"
            efficiency_notes.append(f"Strong ramp consistency ({count} cards)")

        variance = abs(count - min_target)
        total_variance += variance

        result.append(
            f"**{category_name}: {count} cards**{status} (Target: {target_range})"
        )

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
    categories_meeting_min = sum(
        1 for data in categories.values() if len(data["cards"]) >= data["min_target"]
    )
    total_categories = len(categories)

    if categories_meeting_min == total_categories:
        result.append("✓ Excellent deck balance following Command Zone framework")
        result.append(
            "All categories meet minimum requirements for functional gameplay"
        )
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
        result.append(
            "\n✓ Good card overlap - many cards serve multiple roles (recommended)"
        )
    elif total_categorized_cards < total_cards * 1.1:  # Low overlap
        result.append(
            "\n⚡ Consider cards that serve multiple roles (Modal Double-Faced Cards, ETB creatures, modal spells)"
        )

    # Commander format validation
    if total_cards != 99:
        result.append(
            f"\n⚠️ Deck should have 99 cards (excluding commander), found {total_cards}"
        )
        if total_cards < 99:
            result.append("Missing cards may indicate incomplete deck list")
        else:
            result.append("Excess cards need to be cut to 99")

    # Build structured JSON response
    analysis_result = {
        "commander": {
            "name": commander_name,
            "colors": color_names,
            "color_identity": commander_colors,
        },
        "deck": {
            "total_cards": total_cards + 1,  # Including commander
            "deck_cards": total_cards,  # Excluding commander
            "format_valid": total_cards == 99,
        },
        "categories": {},
        "balance_assessment": {
            "overall_score": "excellent"
            if categories_meeting_min == total_categories
            else "good"
            if categories_meeting_min >= total_categories - 1
            else "needs_improvement",
            "categories_meeting_targets": categories_meeting_min,
            "total_categories": total_categories,
        },
        "recommendations": {
            "priority_improvements": problem_categories[:3],
            "efficiency_notes": efficiency_notes,
            "card_overlap_status": "good"
            if total_categorized_cards > total_cards * 1.2
            else "low"
            if total_categorized_cards < total_cards * 1.1
            else "moderate",
        },
        "categorization": categorized_cards,
    }

    # Add category analysis
    for category_name, data in categories.items():
        count = len(data["cards"])
        min_target = data["min_target"]
        optimal_target = data["optimal_target"]
        target_range = data["target_range"]

        status = (
            "optimal"
            if count >= optimal_target
            else "adequate"
            if count >= min_target
            else "insufficient"
        )

        analysis_result["categories"][category_name] = {
            "count": count,
            "target_range": target_range,
            "min_target": min_target,
            "optimal_target": optimal_target,
            "status": status,
            "cards": data["cards"][:10],  # Show first 10 cards as examples
        }

    return json.dumps(analysis_result, indent=2)
