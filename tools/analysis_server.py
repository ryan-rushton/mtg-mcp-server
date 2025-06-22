from fastmcp import FastMCP
import httpx
from typing import List
from collections import Counter, defaultdict
from utils import search_card

analysis_server = FastMCP("MTG Analysis Server", dependencies=["httpx"])


@analysis_server.tool()
async def calculate_mana_curve(card_names: List[str]) -> str:
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        cmc_counter = Counter()
        not_found = []
        for card_name in card_names:
            card_data = await search_card(client, card_name.strip())
            if card_data and "cmc" in card_data:
                cmc = card_data["cmc"]
                cmc_counter[cmc] += 1
            else:
                not_found.append(card_name)
    result = ["**Mana Curve:**"]
    for cmc in sorted(cmc_counter):
        result.append(f"CMC {cmc}: {cmc_counter[cmc]}")
    if not_found:
        result.append(f"\n**Cards Not Found:** {', '.join(not_found)}")
    return "\n".join(result)


@analysis_server.tool()
async def analyze_lands(card_names: List[str]) -> str:
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        land_count = 0
        color_production = defaultdict(int)
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
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        color_counts = defaultdict(int)
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
    individual_colors = defaultdict(int)
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
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        spell_color_counts = defaultdict(int)
        land_color_production = defaultdict(int)
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
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        type_counts = defaultdict(int)
        detailed_types = defaultdict(int)
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
