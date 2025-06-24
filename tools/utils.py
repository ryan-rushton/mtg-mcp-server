# Utility functions and shared cache for MTG MCP server
import httpx
from typing import Dict, Any, Optional
from config import config

# Scryfall API base URL
SCRYFALL_API_BASE = config.scryfall.api_base

# In-memory cache for card data
card_cache: Dict[str, Dict[str, Any]] = {}

# Cache for search results to avoid repeated API calls
search_cache: Dict[str, Dict[str, Any]] = {}


def cache_card_data(card_data: Dict[str, Any]) -> None:
    """Cache card data for future lookups."""
    if "name" in card_data:
        cache_key = card_data["name"].strip().lower()
        card_cache[cache_key] = card_data


async def get_cached_card(client: httpx.AsyncClient, card_name: str) -> Optional[Dict[str, Any]]:
    """Get card from cache or fetch and cache it."""
    cache_key = card_name.strip().lower()
    
    # Check cache first
    if cache_key in card_cache:
        return card_cache[cache_key]
    
    # Fetch and cache
    try:
        response = await client.get(
            f"{SCRYFALL_API_BASE}/cards/named", 
            params={"fuzzy": card_name}
        )
        if response.status_code == 200:
            card_data = response.json()
            cache_card_data(card_data)
            return card_data
        elif response.status_code == 404:
            # Don't cache negative results to avoid type issues
            return None
        else:
            response.raise_for_status()
    except httpx.HTTPError as e:
        print(f"Error fetching card '{card_name}': {e}")
    
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
