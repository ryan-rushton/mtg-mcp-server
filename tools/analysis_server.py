"""Main MTG Analysis Server - composes all analysis sub-servers."""

import asyncio
from fastmcp import FastMCP
from .basic_analysis import basic_analysis_server
from .color_analysis import color_analysis_server
from .commander_analysis import commander_analysis_server
from .analysis_resources import analysis_resources_server

# Create the main analysis server by composing all sub-servers
analysis_server: FastMCP = FastMCP("MTG Analysis Server", dependencies=["httpx"])


async def setup_analysis_server():
    """Set up the analysis server by importing all sub-servers."""
    # Import with empty prefix to get clean tool names
    await analysis_server.import_server(basic_analysis_server)
    await analysis_server.import_server(color_analysis_server)
    await analysis_server.import_server(commander_analysis_server)
    await analysis_server.import_server(analysis_resources_server)


# Initialize at module level for import
asyncio.run(setup_analysis_server())
