from fastmcp import FastMCP
import httpx
from typing import List, Optional, Dict, Any
from .utils import format_card_info, SCRYFALL_API_BASE, cache_card_data, search_cache
from config import config

scryfall_server: FastMCP = FastMCP("MTG Scryfall Server", dependencies=["httpx"])


async def batch_lookup_cards(
    client: httpx.AsyncClient, card_names: List[str]
) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    Batch lookup cards using Scryfall's collection endpoint.

    Args:
        client: HTTP client for making requests
        card_names: List of card names to look up

    Returns:
        Tuple of (found_cards, not_found_names)
    """
    if not card_names:
        return [], []

    # Scryfall batch endpoint accepts max cards per request
    BATCH_SIZE = config.scryfall.batch_size
    all_found_cards = []
    all_not_found = []

    # Process cards in batches
    for i in range(0, len(card_names), BATCH_SIZE):
        batch = card_names[i : i + BATCH_SIZE]

        # Prepare batch request payload
        identifiers = [{"name": name.strip()} for name in batch]

        try:
            response = await client.post(
                f"{SCRYFALL_API_BASE}/cards/collection",
                json={"identifiers": identifiers},
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                data = response.json()
                found_cards = data.get("data", [])
                not_found = data.get("not_found", [])

                # Cache each found card for future single lookups
                for card_data in found_cards:
                    cache_card_data(card_data)

                all_found_cards.extend(found_cards)

                # Extract card names from not_found identifiers
                not_found_names = [
                    item.get("name", "") for item in not_found if "name" in item
                ]
                all_not_found.extend(not_found_names)

            else:
                # If batch fails, fall back to individual lookups for this batch
                print(
                    f"Batch lookup failed with status {response.status_code}, falling back to individual lookups"
                )
                (
                    individual_found,
                    individual_not_found,
                ) = await individual_lookup_fallback(client, batch)
                all_found_cards.extend(individual_found)
                all_not_found.extend(individual_not_found)

        except Exception as e:
            print(f"Batch lookup error: {e}, falling back to individual lookups")
            individual_found, individual_not_found = await individual_lookup_fallback(
                client, batch
            )
            all_found_cards.extend(individual_found)
            all_not_found.extend(individual_not_found)

    return all_found_cards, all_not_found


async def individual_lookup_fallback(
    client: httpx.AsyncClient, card_names: List[str]
) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    Fallback to individual card lookups when batch fails.

    Args:
        client: HTTP client for making requests
        card_names: List of card names to look up individually

    Returns:
        Tuple of (found_cards, not_found_names)
    """
    found_cards = []
    not_found_names = []

    for card_name in card_names:
        try:
            response = await client.get(
                f"{SCRYFALL_API_BASE}/cards/named", params={"fuzzy": card_name.strip()}
            )

            if response.status_code == 200:
                card_data = response.json()
                cache_card_data(card_data)  # Cache individual fallback lookups too
                found_cards.append(card_data)
            elif response.status_code == 404:
                not_found_names.append(card_name)
            else:
                response.raise_for_status()

        except httpx.HTTPError:
            not_found_names.append(card_name)

    return found_cards, not_found_names


@scryfall_server.tool()
async def lookup_cards(card_names: List[str]) -> str:
    """
    Look up MTG cards by name with fuzzy matching - ESSENTIAL FIRST STEP for deck analysis.

    WHEN TO USE: Always use this before other analysis tools to validate card names.
    FOLLOWS WELL WITH: analysis_calculate_mana_curve, analysis_analyze_commander_deck

    Uses batch operations (up to 75 cards) for efficient API usage.

    Args:
        card_names: List of card names (supports fuzzy matching)

    Returns: Detailed card info with prices and oracle text
    """
    if not card_names:
        return "No card names provided."

    async with httpx.AsyncClient() as client:
        found_cards, not_found_names = await batch_lookup_cards(client, card_names)

        # Format found cards
        results = []
        for card_data in found_cards:
            formatted_card = format_card_info(card_data)
            results.append(formatted_card)

        # Build response
        response_parts = []
        if results:
            response_parts.append("**Cards Found:**\n")
            response_parts.extend([f"{result}\n---\n" for result in results])

        if not_found_names:
            response_parts.append(f"**Cards Not Found:** {', '.join(not_found_names)}")

        return "\n".join(response_parts)


@scryfall_server.tool()
async def search_cards_by_criteria(
    name: Optional[str] = None,
    colors: Optional[str] = None,
    type_line: Optional[str] = None,
    mana_cost: Optional[int] = None,
    limit: int = 10,
) -> str:
    """
    Search MTG database by name, color, type, or mana cost.

    WHEN TO USE: When users want to find cards matching specific criteria or need recommendations.
    EXAMPLES: "find red dragons", "show me 3-mana artifacts", "search for counterspells"

    Args:
        name: Partial card name (e.g. "dragon", "bolt")
        colors: Color filter (e.g. "red", "blue white")
        type_line: Card type (e.g. "creature", "instant")
        mana_cost: Exact CMC value
        limit: Max results (1-25, default 10)

    Returns: Search results with card details and total count
    """
    query_parts = []
    if name:
        query_parts.append(f'name:"{name}"')
    if colors:
        query_parts.append(f"color:{colors}")
    if type_line:
        query_parts.append(f"type:{type_line}")
    if mana_cost is not None:
        query_parts.append(f"cmc:{mana_cost}")
    if not query_parts:
        return "No search criteria provided."
    search_query = " ".join(query_parts)
    limit = min(max(1, limit), 25)

    # Create cache key for search results
    cache_key = f"{search_query}:{limit}"

    # Check search cache first
    if cache_key in search_cache:
        cached_result = search_cache[cache_key]
        if "error" in cached_result:
            return cached_result["error"]

        cards = cached_result.get("cards", [])
        total_cards = cached_result.get("total_cards", len(cards))

        # Build result from cache
        results = []
        for card in cards:
            formatted_card = format_card_info(card)
            results.append(formatted_card)
        result_text = f"**Search Results for:** {search_query}\\n\\n"
        result_text += "\\n---\\n".join(results)
        if total_cards > limit:
            result_text += (
                f"\\n\\n*Showing {len(cards)} of {total_cards} total results*"
            )
        return result_text

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{SCRYFALL_API_BASE}/cards/search",
                params={"q": search_query, "page": 1, "order": "name"},
            )
            if response.status_code == 404:
                error_msg = f"No cards found matching criteria: {search_query}"
                search_cache[cache_key] = {"error": error_msg}
                return error_msg
            response.raise_for_status()
            data = response.json()
            cards = data.get("data", [])[:limit]
            if not cards:
                error_msg = f"No cards found matching criteria: {search_query}"
                search_cache[cache_key] = {"error": error_msg}
                return error_msg

            # Cache individual cards and search results
            for card in cards:
                cache_card_data(card)

            total_cards = data.get("total_cards", len(cards))
            search_cache[cache_key] = {"cards": cards, "total_cards": total_cards}

            results = []
            for card in cards:
                formatted_card = format_card_info(card)
                results.append(formatted_card)
            result_text = f"**Search Results for:** {search_query}\n\n"
            result_text += "\n---\n".join(results)
            if total_cards > limit:
                result_text += (
                    f"\n\n*Showing {len(cards)} of {total_cards} total results*"
                )
            return result_text
        except httpx.HTTPError as e:
            return f"Error searching cards: {e}"
