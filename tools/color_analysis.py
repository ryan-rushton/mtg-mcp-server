"""Color and mana analysis tools for MTG decks."""

from fastmcp import FastMCP
import httpx
import json
from typing import List, Dict, Any
from collections import defaultdict
from .utils import get_cached_card

color_analysis_server: FastMCP = FastMCP(
    "MTG Color Analysis Server", dependencies=["httpx"]
)


@color_analysis_server.tool()
async def analyze_color_identity(card_names: List[str]) -> str:
    """
    Analyze color distribution and combinations in your deck.

    WHEN TO USE: For Commander deck building, color balance evaluation, or mana base planning.
    USE FOR: "what colors am I in?", "is my deck balanced?", color identity verification

    Args:
        card_names: List of card names to analyze

    Returns: JSON object with structured color analysis including:
        - summary: total cards, colorless count and percentage
        - color_combinations: breakdown of multicolor combinations
        - individual_colors: presence of each color across all cards
        - not_found: any cards that couldn't be looked up
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

    # Build color combinations data
    color_combinations: Dict[str, Any] = {}
    if colorless_count > 0:
        color_combinations["Colorless"] = {
            "count": colorless_count,
            "percentage": round((colorless_count / total_cards) * 100, 1)
            if total_cards > 0
            else 0,
        }

    sorted_colors = sorted(color_counts.items(), key=lambda x: (-x[1], x[0]))
    for color_combo, count in sorted_colors:
        color_names = [color_map[c] for c in color_combo]
        color_display = (
            "/".join(color_names) if len(color_names) > 1 else color_names[0]
        )
        color_combinations[color_display] = {
            "count": count,
            "percentage": round((count / total_cards) * 100, 1)
            if total_cards > 0
            else 0,
            "color_codes": list(color_combo),
        }

    # Calculate individual color presence
    individual_colors: defaultdict[str, int] = defaultdict(int)
    for color_combo, count in color_counts.items():
        for color in color_combo:
            individual_colors[color] += count

    individual_color_data: Dict[str, Any] = {}
    for color_code in ["W", "U", "B", "R", "G"]:
        if color_code in individual_colors:
            count = individual_colors[color_code]
            individual_color_data[color_map[color_code]] = {
                "count": count,
                "percentage": round((count / total_cards) * 100, 1)
                if total_cards > 0
                else 0,
                "color_code": color_code,
            }

    # Build JSON response
    analysis_result = {
        "summary": {
            "total_cards": total_cards,
            "colored_cards": total_colored_cards,
            "colorless_cards": colorless_count,
            "color_diversity": len(
                individual_colors
            ),  # Number of different colors present
            "multicolor_cards": sum(
                1 for combo in color_counts.keys() if len(combo) > 1
            ),
        },
        "color_combinations": color_combinations,
        "individual_colors": individual_color_data,
        "not_found": not_found,
    }

    return json.dumps(analysis_result, indent=2)


@color_analysis_server.tool()
async def analyze_mana_requirements(card_names: List[str]) -> str:
    """
    Compare spell requirements vs land production - critical for playable decks.

    WHEN TO USE: When analyzing mana base adequacy or fixing color screw issues.
    USE FOR: "can I cast my spells?", "do I need more lands?", mana base optimization
    PROVIDES: Warnings for insufficient sources, coverage ratios, actionable recommendations

    Args:
        card_names: Complete deck list (lands and spells)

    Returns: JSON object with structured mana analysis including:
        - summary: card counts, coverage ratio, overall status
        - color_analysis: per-color requirements vs production with status
        - recommendations: specific actions to improve mana base
        - not_found: any cards that couldn't be looked up
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
    total_color_requirements = sum(spell_color_counts.values())
    total_mana_sources = sum(land_color_production.values())

    # Calculate overall coverage and status
    coverage_ratio = (
        total_mana_sources / total_color_requirements
        if total_color_requirements > 0
        else 0
    )
    overall_status = (
        "excellent"
        if coverage_ratio >= 0.5
        else "moderate"
        if coverage_ratio >= 0.3
        else "insufficient"
    )

    # Build color analysis
    color_analysis = {}
    recommendations = []

    for color_code in ["W", "U", "B", "R", "G"]:
        color_name = color_map[color_code]
        spell_req = spell_color_counts[color_code]
        land_prod = land_color_production[color_code]

        if spell_req > 0 or land_prod > 0:
            # Calculate status
            if spell_req > 0:
                color_ratio = land_prod / spell_req if spell_req > 0 else 0
                if land_prod == 0:
                    status = "no_sources"
                    recommendations.append(
                        f"Add {color_name} mana sources - currently have none!"
                    )
                elif color_ratio < 0.3:
                    status = "insufficient"
                    recommendations.append(
                        f"Add more {color_name} sources (need {max(1, int(spell_req * 0.5 - land_prod))} more)"
                    )
                elif color_ratio >= 0.5:
                    status = "good"
                else:
                    status = "adequate"
            else:
                status = "excess"

            color_analysis[color_name] = {
                "spell_requirements": spell_req,
                "land_sources": land_prod,
                "ratio": land_prod / spell_req if spell_req > 0 else float("inf"),
                "status": status,
            }

    # Add general recommendations
    if coverage_ratio < 0.3:
        recommendations.append("Very low mana base coverage - add more colored sources")
    elif coverage_ratio < 0.5:
        recommendations.append("Consider adding more mana sources for consistency")

    if land_total < total_cards * 0.35:  # Less than 35% lands
        recommendations.append(
            f"Consider adding more lands (current: {land_total}, suggested: {int(total_cards * 0.4)})"
        )

    # Build JSON response
    analysis_result = {
        "summary": {
            "total_cards": total_cards,
            "spells": spell_total,
            "lands": land_total,
            "total_color_requirements": total_color_requirements,
            "total_mana_sources": total_mana_sources,
            "coverage_ratio": round(coverage_ratio, 3),
            "overall_status": overall_status,
        },
        "color_analysis": color_analysis,
        "recommendations": recommendations,
        "not_found": not_found,
    }

    return json.dumps(analysis_result, indent=2)
