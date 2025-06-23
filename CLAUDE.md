# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server for Magic: The Gathering card analysis. It provides tools to help LLMs understand deck lists and make recommendations by interfacing with the Scryfall API.

## Commands

### Development Commands

**Setup:**
- `uv sync` - Install/sync dependencies using uv package manager

**Running the Server:**
- `python server.py` - Run the main MCP server (STDIO transport, default)
- `fastmcp run server.py` - Run using FastMCP CLI
- `fastmcp dev server.py` - Run in development mode with isolated environment

**Quality Assurance:**
- `uv run pytest` - Run the test suite
- `uv run mypy .` - Run type checking
- `uv run ruff check .` - Run linting
- `uv run ruff format .` - Run code formatting

**Testing:**
- `python test_client.py` - Run interactive demo (optional, shows server functionality)

## Architecture

### Core Components

**server.py** - Main MCP server that composes sub-servers:

- Uses FastMCP framework to create MCP server. Docs for understanding how the framework is used can be found at https://gofastmcp.com/llms.txt
- Imports tools from scryfall_server and analysis_server using server composition
- Tools are prefixed: scryfall_* for card lookup tools, analysis_* for deck analysis tools
- All tools are async and use httpx for Scryfall API calls

**tools/utils.py** - Shared utilities:

- `search_card()` - Card lookup with in-memory caching
- `format_card_info()` - Formats card data for display
- Maintains card cache to reduce API calls

**test_client.py** - Comprehensive test client:

- Example calls for all tools
- Interactive mode for manual testing
- Demonstrates proper FastMCP client usage

### Tools Structure

The server provides these analysis tools (with prefixes):

**Scryfall Tools (prefix: scryfall_):**
1. `scryfall_lookup_cards` - Look up specific cards by name using batch operations (up to 75 cards per request)
2. `scryfall_search_cards_by_criteria` - Search by name/color/type/CMC

**Analysis Tools (prefix: analysis_):**
3. `analysis_calculate_mana_curve` - Analyze CMC distribution
4. `analysis_analyze_lands` - Count lands and mana production
5. `analysis_analyze_color_identity` - Color distribution analysis
6. `analysis_analyze_mana_requirements` - Spell requirements vs land production
7. `analysis_analyze_card_types` - Card type distribution

All tools handle card lookup failures gracefully and have comprehensive docstrings.

### Separated Tool Files

The `tools/` directory contains the sub-servers:

- `scryfall_server.py` - Card lookup tools with batch operations and comprehensive docstrings
- `analysis_server.py` - Deck analysis tools with comprehensive docstrings  
- `utils.py` - Shared utilities for card lookups and formatting
- `__init__.py` - Makes tools directory a proper Python package
- These are imported by the main server using FastMCP server composition

## Key Patterns

- **Batch Operations**: Card lookups use Scryfall's collection endpoint (up to 75 cards per request) for efficient bulk operations
- **Fallback Strategy**: Automatically falls back to individual lookups if batch operations fail
- **Caching**: Card data is cached in `tools/utils.py` to minimize Scryfall API calls
- **Error Handling**: All tools handle missing cards and API errors gracefully
- **Async Design**: All operations are async using httpx for API calls
- **Consistent Output**: All tools return formatted strings with markdown headers
- **Fuzzy Search**: Uses Scryfall's fuzzy matching for card name lookup

## Dependencies

- `fastmcp>=2.8.1` - MCP server framework
- `httpx` - Async HTTP client for Scryfall API
- `mypy>=1.16.1` - Type checking (dev)
- `ruff>=0.12.0` - Linting and formatting (dev)
