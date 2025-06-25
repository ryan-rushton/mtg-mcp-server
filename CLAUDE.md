# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MCP (Model Context Protocol) server for Magic: The Gathering deck analysis. It provides tools to help LLMs understand deck lists and make recommendations by interfacing with the Scryfall API.

The server uses a **modular architecture** with separated concerns across multiple specialized modules for better maintainability and development workflow.

## Commands

### Development Commands

**Setup:**

- `uv sync` - Install/sync dependencies using uv package manager

**Running the Server:**

- `uv run python server.py` - Run the main MCP server (STDIO transport, default)
- `uv run fastmcp run server.py` - Run using FastMCP CLI
- `uv run fastmcp dev server.py` - Run in development mode with isolated environment

**Quality Assurance:**

- `uv run pytest` - Run the test suite
- `uv run mypy .` - Run type checking
- `uv run ruff check .` - Run linting
- `uv run ruff format .` - Run code formatting

**Testing:**

- `uv run python test_client.py` - Run interactive demo (optional, shows server functionality)

## Architecture

### Core Components

**server.py** - Main MCP server that composes sub-servers:

- Uses FastMCP framework to create MCP server. Docs for understanding how the framework is used can be found at https://gofastmcp.com/llms.txt
- Uses the Scryfall API to search cards. Docs are found at https://scryfall.com/docs/api.
- Imports tools from scryfall_server and analysis_server using server composition
- Tools are prefixed: `scryfall_*` for card lookup tools, `analysis_*` for deck analysis tools
- All tools are async and use httpx for Scryfall API calls

**config.py** - Centralized configuration module:

- Contains all configuration classes using dataclasses
- `ScryfallConfig` - API settings, batch sizes, timeouts
- `CommandZoneConfig` - Command Zone template targets and thresholds
- `CacheConfig` - Caching behavior and limits
- `ServerConfig` - Main configuration combining all subsystems

**tools/utils.py** - Shared utilities:

- `get_cached_card()` - Card lookup with in-memory caching  
- `cache_card_data()` - Cache management for card data
- `format_card_info()` - Formats card data for display
- Maintains card cache to reduce API calls

**test_client.py** - Interactive demo client:

- Example calls for all tools
- Interactive mode for manual testing
- Demonstrates proper FastMCP client usage
- Shows quantity parsing in commander analysis

**tests/test_integration.py** - Integration tests with real network requests:

- Full end-to-end testing with live Scryfall API calls
- Tests all server tools with real card data
- Verifies error handling and edge cases
- Tests commander analysis with quantities and duplicates
- Run with: `uv run pytest tests/test_integration.py`

### Modular Tools Structure

The `tools/` directory contains specialized modules for different functionality:

**Core Servers:**
- `scryfall_server.py` - Card lookup tools with batch operations and comprehensive docstrings
- `analysis_server.py` - Main analysis server that composes all analysis sub-modules

**Analysis Modules:**
- `basic_analysis.py` - Simple analysis tools (mana curve, lands, card types)
- `color_analysis.py` - Color and mana analysis tools (JSON output)
- `commander_analysis.py` - Commander-specific analysis and Command Zone integration
- `analysis_resources.py` - Prompts, resources, and workflow guidance

**Utilities:**
- `utils.py` - Shared utilities for card lookups and formatting
- `__init__.py` - Makes tools directory a proper Python package

### Server Composition

The main server uses FastMCP's import system to compose two main sub-servers:
- **Scryfall Server**: Card lookup and search functionality
- **Analysis Server**: Deck analysis tools (itself composed from 4 specialized modules)

### Tools Structure

The server provides 8 tools organized into two categories:

**Scryfall Tools (prefix: `scryfall_`):**

1. `scryfall_lookup_cards` - Look up specific cards by name using batch operations (up to 75 cards per request)
2. `scryfall_search_cards_by_criteria` - Search by name/color/type/CMC

**Analysis Tools (prefix: `analysis_`):**

3. `analysis_calculate_mana_curve` - Analyze CMC distribution
4. `analysis_analyze_lands` - Count lands and mana production  
5. `analysis_analyze_color_identity` - Color distribution analysis (JSON output)
6. `analysis_analyze_mana_requirements` - Spell requirements vs land production (JSON output)
7. `analysis_analyze_card_types` - Card type distribution
8. `analysis_analyze_commander_deck` - Analyze Commander deck using Command Zone template (JSON output)

All tools handle card lookup failures gracefully and have comprehensive docstrings.

## Commander Deck Analysis

The `analysis_analyze_commander_deck` tool provides card data for LLM-based Command Zone deckbuilding template analysis for 100-card Commander decks:

**Command Zone Categories:**
- **Ramp (10-12+ cards)**: Mana acceleration and fixing (Sol Ring, Cultivate, etc.)
- **Card Advantage (12+ cards)**: Card draw and selection (Rhystic Study, Phyrexian Arena, etc.)
- **Targeted Disruption (12 cards)**: Single-target removal/interaction (Swords to Plowshares, Counterspell, etc.)
- **Mass Disruption (6 cards)**: Board wipes and mass effects (Wrath of God, Cyclonic Rift, etc.)
- **Lands (38 cards)**: All land cards including basics and nonbasics
- **Plan Cards (~30 cards)**: Theme/strategy cards that advance your deck's game plan

**Usage Pattern:**
The tool takes two parameters: `commander` and `decklist`. It provides:
1. Commander card data (name, colors, type, oracle text)
2. All deck card data with relevant properties for analysis
3. Command Zone framework targets for reference
4. Raw card data for the LLM to categorize and analyze

The LLM should analyze the card data and categorize cards based on their properties, then provide deck balance assessment and improvement recommendations.

## Key Patterns

- **Unified Caching**: All API calls use shared caching infrastructure to minimize Scryfall requests
- **Batch Operations**: Card lookups use Scryfall's collection endpoint (up to 75 cards per request) with automatic cache population
- **Search Result Caching**: Criteria-based searches are cached to avoid repeated API calls
- **Fallback Strategy**: Automatically falls back to individual lookups if batch operations fail
- **Cross-Tool Cache Sharing**: Batch operations populate cache for future single card lookups
- **Negative Result Caching**: Failed lookups are cached to prevent repeated failures
- **Error Handling**: All tools handle missing cards and API errors gracefully
- **Async Design**: All operations are async using httpx for API calls
- **Structured Output**: Key analysis tools return JSON for programmatic access
- **Fuzzy Search**: Uses Scryfall's fuzzy matching for card name lookup
- **Modular Architecture**: Clean separation of concerns across multiple focused modules

## Configuration Management

All configuration is centralized in `config.py` with these key settings:

**Scryfall API Configuration:**
- `api_base: str = "https://api.scryfall.com"`
- `batch_size: int = 75` - Max cards per batch request
- `request_timeout: int = 30` - API request timeout
- `max_retries: int = 3` - Retry attempts for failed requests

**Command Zone Template Targets:**
- `ramp_target: int = 10` / `ramp_optimal: int = 12`
- `card_advantage_target: int = 12` / `card_advantage_optimal: int = 15`
- `targeted_disruption_target: int = 12`
- `mass_disruption_target: int = 6`
- `lands_target: int = 38`
- `plan_cards_target: int = 30`

**Caching Configuration:**
- `max_card_cache_size: int = 10000` - Maximum cached cards
- `max_search_cache_size: int = 1000` - Maximum cached searches
- `ttl_seconds: int = 3600` - Cache time-to-live
- `enable_persistence: bool = False` - Persistent cache (future feature)

## JSON vs Text Outputs

**Tools with JSON Output** (for structured data analysis):
- `analysis_analyze_color_identity` - Color combinations and individual color presence
- `analysis_analyze_mana_requirements` - Mana coverage analysis with recommendations  
- `analysis_analyze_commander_deck` - Complete Command Zone analysis

**Tools with Text Output** (for readable summaries):
- `analysis_calculate_mana_curve` - Simple CMC distribution
- `analysis_analyze_lands` - Basic land count and color production
- `analysis_analyze_card_types` - Card type breakdown with guidelines

## Dependencies

- `fastmcp>=2.9.0` - MCP server framework (updated from 2.8.1)
- `httpx` - Async HTTP client for Scryfall API
- `mypy>=1.16.1` - Type checking (dev)
- `ruff>=0.12.0` - Linting and formatting (dev)
- `pytest>=8.0.0` - Testing framework (dev)
- `pytest-asyncio>=0.24.0` - Async testing support (dev)