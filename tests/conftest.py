"""Pytest configuration and fixtures for MTG MCP Server tests."""

import pytest
import pytest_asyncio
from fastmcp import FastMCP, Client
from tools.scryfall_server import scryfall_server
from tools.analysis_server import analysis_server


@pytest_asyncio.fixture
async def mcp_server():
    """Create a test MCP server with both sub-servers imported."""
    server = FastMCP("MTG Test Server", dependencies=["httpx"])
    
    # Import sub-servers like the main server does
    await server.import_server("scryfall", scryfall_server)
    await server.import_server("analysis", analysis_server)
    
    return server


@pytest_asyncio.fixture
async def client(mcp_server):
    """Create a client connected to the test server."""
    async with Client(mcp_server) as client:
        yield client


@pytest.fixture
def mock_scryfall_collection_response():
    """Mock response for Scryfall's collection endpoint."""
    return {
        "data": [
            {
                "name": "Lightning Bolt",
                "mana_cost": "{R}",
                "type_line": "Instant",
                "oracle_text": "Lightning Bolt deals 3 damage to any target.",
                "cmc": 1.0,
                "color_identity": ["R"],
                "prices": {"usd": "0.50"}
            },
            {
                "name": "Counterspell", 
                "mana_cost": "{U}{U}",
                "type_line": "Instant",
                "oracle_text": "Counter target spell.",
                "cmc": 2.0,
                "color_identity": ["U"],
                "prices": {"usd": "1.25"}
            }
        ],
        "not_found": []
    }


@pytest.fixture
def mock_scryfall_search_response():
    """Mock response for Scryfall's search endpoint."""
    return {
        "data": [
            {
                "name": "Shivan Dragon",
                "mana_cost": "{4}{R}{R}",
                "type_line": "Creature — Dragon",
                "oracle_text": "Flying (This creature can't be blocked except by creatures with flying or reach.)",
                "power": "5",
                "toughness": "5",
                "cmc": 6.0,
                "color_identity": ["R"],
                "prices": {"usd": "0.25"}
            }
        ],
        "total_cards": 1
    }


@pytest.fixture
def mock_scryfall_land_response():
    """Mock response for land cards."""
    return {
        "data": [
            {
                "name": "Command Tower",
                "mana_cost": "",
                "type_line": "Land",
                "oracle_text": "{T}: Add one mana of any color in your commander's color identity.",
                "cmc": 0.0,
                "color_identity": [],
                "prices": {"usd": "0.75"}
            },
            {
                "name": "Sacred Foundry",
                "mana_cost": "",
                "type_line": "Land — Mountain Plains",
                "oracle_text": "({T}: Add {R} or {W}.)\nAs Sacred Foundry enters the battlefield, you may pay 2 life. If you don't, it enters the battlefield tapped.",
                "cmc": 0.0,
                "color_identity": [],
                "prices": {"usd": "12.50"}
            }
        ],
        "not_found": []
    }