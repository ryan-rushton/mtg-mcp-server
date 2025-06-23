# Utility functions and shared cache for MTG MCP server
import httpx
from typing import Dict, Any, Optional

# Scryfall API base URL
SCRYFALL_API_BASE = "https://api.scryfall.com"

# In-memory cache for card data
card_cache: Dict[str, Dict[str, Any]] = {}


async def search_card(
    client: httpx.AsyncClient, card_name: str
) -> Optional[Dict[str, Any]]:
    """Search for a single card by name using Scryfall's fuzzy search, with cache."""
    cache_key = card_name.strip().lower()
    if cache_key in card_cache:
        return card_cache[cache_key]
    try:
        response = await client.get(
            f"{SCRYFALL_API_BASE}/cards/named", params={"fuzzy": card_name}
        )
        if response.status_code == 200:
            card_data = response.json()
            card_cache[cache_key] = card_data
            return card_data
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()
        return None
    except httpx.HTTPError as e:
        print(f"Error searching for card '{card_name}': {e}")
        return None


def format_card_info(card_data: Dict[str, Any]) -> str:
    """Format card data into a readable string."""
    name = card_data.get("name", "Unknown")
    mana_cost = card_data.get("mana_cost", "")
    type_line = card_data.get("type_line", "")
    oracle_text = card_data.get("oracle_text", "")
    power = card_data.get("power")
    toughness = card_data.get("toughness")

    result = f"**{name}**"
    if mana_cost:
        result += f" {mana_cost}"
    result += f"\n{type_line}"
    if power and toughness:
        result += f" {power}/{toughness}"
    if oracle_text:
        result += f"\n\n{oracle_text}"
    prices = card_data.get("prices", {})
    if prices.get("usd"):
        result += f"\n\nPrice (USD): ${prices['usd']}"
    return result
