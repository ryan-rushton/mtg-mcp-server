import asyncio
from fastmcp import FastMCP
from tools.scryfall_server import scryfall_server
from tools.analysis_server import analysis_server

# Initialize the main FastMCP server
mcp: FastMCP = FastMCP("MTG Card Analysis Server", dependencies=["httpx"])


# Set up the server by importing sub-servers at module level
async def setup_server():
    """Set up the main server by importing sub-servers."""
    # Import Scryfall server tools (will be prefixed with "scryfall_")
    await mcp.import_server("scryfall", scryfall_server)

    # Import analysis server tools (will be prefixed with "analysis_")
    await mcp.import_server("analysis", analysis_server)


# Initialize server setup at module level for testing
asyncio.run(setup_server())

if __name__ == "__main__":
    # Run the server following FastMCP best practices
    mcp.run()
