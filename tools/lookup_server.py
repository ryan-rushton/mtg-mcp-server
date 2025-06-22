from fastmcp import FastMCP
import httpx
from typing import List, Optional
from utils import search_card, format_card_info

lookup_server = FastMCP("MTG Card Lookup Server", dependencies=["httpx"])


@lookup_server.tool()
async def lookup_cards(card_names: List[str]) -> str:
    if not card_names:
        return "No card names provided."
    async with httpx.AsyncClient() as client:
        results = []
        not_found = []
        for card_name in card_names:
            card_data = await search_card(client, card_name.strip())
            if card_data:
                formatted_card = format_card_info(card_data)
                results.append(formatted_card)
            else:
                not_found.append(card_name)
    response_parts = []
    if results:
        response_parts.append("**Cards Found:**\n")
        response_parts.extend([f"{result}\n---\n" for result in results])
    if not_found:
        response_parts.append(f"**Cards Not Found:** {', '.join(not_found)}")
    return "\n".join(response_parts)


@lookup_server.tool()
async def search_cards_by_criteria(
    name: Optional[str] = None,
    colors: Optional[str] = None,
    type_line: Optional[str] = None,
    mana_cost: Optional[int] = None,
    limit: int = 10,
) -> str:
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
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.scryfall.com/cards/search",
                params={"q": search_query, "page": 1, "order": "name"},
            )
            if response.status_code == 404:
                return f"No cards found matching criteria: {search_query}"
            response.raise_for_status()
            data = response.json()
            cards = data.get("data", [])[:limit]
            if not cards:
                return f"No cards found matching criteria: {search_query}"
            results = []
            for card in cards:
                formatted_card = format_card_info(card)
                results.append(formatted_card)
            result_text = f"**Search Results for:** {search_query}\n\n"
            result_text += "\n---\n".join(results)
            total_cards = data.get("total_cards", len(cards))
            if total_cards > limit:
                result_text += (
                    f"\n\n*Showing {len(cards)} of {total_cards} total results*"
                )
            return result_text
        except httpx.HTTPError as e:
            return f"Error searching cards: {e}"
