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
- Uses the scryfall API to search cards. Docs are found at https://scryfall.com/docs/api.
- Imports tools from scryfall_server and analysis_server using server composition
- Tools are prefixed: scryfall*\* for card lookup tools, analysis*\* for deck analysis tools
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

**Scryfall Tools (prefix: scryfall\_):**

1. `scryfall_lookup_cards` - Look up specific cards by name using batch operations (up to 75 cards per request)
2. `scryfall_search_cards_by_criteria` - Search by name/color/type/CMC

**Analysis Tools (prefix: analysis\_):**
3. `analysis_calculate_mana_curve` - Analyze CMC distribution
4. `analysis_analyze_lands` - Count lands and mana production
5. `analysis_analyze_color_identity` - Color distribution analysis
6. `analysis_analyze_mana_requirements` - Spell requirements vs land production
7. `analysis_analyze_card_types` - Card type distribution
8. `analysis_analyze_commander_deck` - Analyze Commander deck using Command Zone template

All tools handle card lookup failures gracefully and have comprehensive docstrings.

### Separated Tool Files

The `tools/` directory contains the sub-servers:

- `scryfall_server.py` - Card lookup tools with batch operations and comprehensive docstrings
- `analysis_server.py` - Deck analysis tools with comprehensive docstrings
- `utils.py` - Shared utilities for card lookups and formatting
- `__init__.py` - Makes tools directory a proper Python package
- These are imported by the main server using FastMCP server composition

## Commander Deck Analysis

The `analysis_analyze_commander_deck` tool implements the Command Zone deckbuilding template for 100-card Commander decks:

**Command Zone Categories:**
- **Ramp (10 cards)**: Mana acceleration and fixing (Sol Ring, Cultivate, etc.)
- **Card Advantage (12 cards)**: Card draw and selection (Rhystic Study, Phyrexian Arena, etc.)
- **Targeted Disruption (12 cards)**: Single-target removal/interaction (Swords to Plowshares, Counterspell, etc.)
- **Mass Disruption (6 cards)**: Board wipes and mass effects (Wrath of God, Cyclonic Rift, etc.)
- **Lands (38 cards)**: All land cards including basics and nonbasics
- **Plan Cards (30 cards)**: Theme/strategy cards that advance your deck's game plan

**Usage Pattern:**
The LLM should categorize cards into these buckets based on their functions, then call the tool with the categorized lists. Cards can appear in multiple categories. The tool validates counts against recommendations and provides balance assessment.

## Key Patterns

- **Unified Caching**: All API calls use shared caching infrastructure to minimize Scryfall requests
- **Batch Operations**: Card lookups use Scryfall's collection endpoint (up to 75 cards per request) with automatic cache population
- **Search Result Caching**: Criteria-based searches are cached to avoid repeated API calls
- **Fallback Strategy**: Automatically falls back to individual lookups if batch operations fail
- **Cross-Tool Cache Sharing**: Batch operations populate cache for future single card lookups
- **Negative Result Caching**: Failed lookups are cached to prevent repeated failures
- **Error Handling**: All tools handle missing cards and API errors gracefully
- **Async Design**: All operations are async using httpx for API calls
- **Consistent Output**: All tools return formatted strings with markdown headers
- **Fuzzy Search**: Uses Scryfall's fuzzy matching for card name lookup

## Dependencies

- `fastmcp>=2.8.1` - MCP server framework
- `httpx` - Async HTTP client for Scryfall API
- `mypy>=1.16.1` - Type checking (dev)
- `ruff>=0.12.0` - Linting and formatting (dev)
