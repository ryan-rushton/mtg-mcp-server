# MTG MCP Server

A comprehensive Model Context Protocol (MCP) server for Magic: The Gathering deck analysis and card lookup. This server helps LLMs understand deck compositions, provide strategic recommendations, and analyze Magic cards using the Scryfall API.

## What This Server Does

This MCP server gives Claude (and other LLMs) the ability to:

- **Look up Magic cards** by name with fuzzy matching
- **Search for cards** by color, type, mana cost, and other criteria
- **Analyze deck compositions** including mana curves, color balance, and card types
- **Evaluate Commander decks** using the proven Command Zone deckbuilding template
- **Provide strategic recommendations** for deck improvements and optimization

## Using with Claude Desktop

### Installation for Claude Desktop

1. **Download or clone this repository** to your computer
2. **Install Python 3.13+** if you don't have it already
3. **Install uv package manager**: Visit [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)
4. **Set up the server**:
   ```bash
   cd mtg-mcp-server
   uv sync
   ```
5. **Add to Claude Desktop config**:
   - Open Claude Desktop settings
   - Navigate to the MCP servers configuration
   - Add this server with the path to your installation

### Claude Desktop Configuration

Add this to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "mtg-analysis": {
      "command": "uv",
      "args": ["run", "python", "/path/to/mtg-mcp-server/server.py"],
      "cwd": "/path/to/mtg-mcp-server"
    }
  }
}
```

Replace `/path/to/mtg-mcp-server` with the actual path where you installed the server.

## What You Can Ask Claude

Once installed, you can ask Claude things like:

- "Analyze my Commander deck" (provide your deck list)
- "Look up information about Lightning Bolt and Counterspell"
- "What's the mana curve of my deck?"
- "Search for red dragons under 4 mana"
- "How good is my mana base?"
- "Give me suggestions to improve my deck"

### Example Conversation

**You:** "Can you analyze this Commander deck? My commander is Atraxa, Praetors' Voice, and here's my deck list: Sol Ring, Command Tower, Cultivate, Rhystic Study, Swords to Plowshares, Wrath of God..."

**Claude:** *Uses the MTG server tools to look up all cards, categorize them into the Command Zone framework, and provides detailed analysis with specific improvement recommendations*

## Features

### 🔍 Card Lookup & Search
- **Batch card lookup** with fuzzy name matching (up to 75 cards per request)
- **Advanced search** by name, color, type, mana cost with comprehensive filtering
- **Intelligent caching** to minimize API calls and improve performance

### 📊 Deck Analysis
- **Mana curve analysis** for deck speed optimization
- **Color identity analysis** with detailed breakdowns and percentages
- **Mana base evaluation** comparing spell requirements vs land production
- **Card type distribution** analysis with format guidelines

### 🏰 Commander Deck Analysis
- **Command Zone template integration** - automated deck analysis using the official Command Zone deckbuilding framework
- **Automatic card categorization** into 6 core categories:
  - **Ramp** (10-12+ cards): Mana acceleration and fixing
  - **Card Advantage** (12+ cards): Draw engines and card selection  
  - **Targeted Disruption** (12 cards): Single-target removal and interaction
  - **Mass Disruption** (6 cards): Board wipes and protection
  - **Lands** (38 cards): Mana base with utility lands
  - **Plan Cards** (~30 cards): Win conditions and synergy pieces
- **Balance assessment** with actionable improvement recommendations

### 🎯 Smart Prompts & Resources
- **Workflow guidance** prompts to help LLMs use tools effectively
- **Commander staples** database organized by category
- **Improvement suggestions** based on Command Zone principles

---

## Development & Contributing

This section is for developers who want to fork, modify, or contribute to the MTG MCP Server.

### Development Setup

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd mtg-mcp-server
   uv sync
   ```

2. **Run the server locally**:
   ```bash
   # Basic run
   uv run python server.py
   
   # Development mode with auto-reload
   uv run fastmcp dev server.py
   ```

3. **Test the server**:
   ```bash
   # Run interactive demo
   uv run python test_client.py
   
   # Run full test suite
   uv run pytest
   ```

### Available Tools (for developers)

The server provides 8 tools organized into two categories:

#### Scryfall Tools (prefix: `scryfall_`)
- `scryfall_lookup_cards` - Look up specific cards by name
- `scryfall_search_cards_by_criteria` - Search by name/color/type/CMC

#### Analysis Tools (prefix: `analysis_`)
- `analysis_calculate_mana_curve` - Analyze CMC distribution
- `analysis_analyze_lands` - Count lands and mana production
- `analysis_analyze_color_identity` - Color distribution analysis (JSON)
- `analysis_analyze_mana_requirements` - Spell requirements vs land production (JSON)
- `analysis_analyze_card_types` - Card type distribution
- `analysis_analyze_commander_deck` - Full Commander deck analysis (JSON)

### Architecture

#### Modular Design

The server uses a clean, modular architecture with separated concerns:

```
mtg-mcp-server/
├── server.py                 # Main server composition
├── config.py                 # Centralized configuration
├── tools/
│   ├── scryfall_server.py    # Card lookup tools
│   ├── basic_analysis.py     # Simple analysis tools
│   ├── color_analysis.py     # Color and mana analysis
│   ├── commander_analysis.py # Commander-specific analysis
│   ├── analysis_resources.py # Prompts and resources
│   ├── analysis_server.py    # Analysis server composition
│   └── utils.py              # Shared utilities
└── tests/                    # Comprehensive test suite
```

#### Server Composition

The main server composes two sub-servers using FastMCP's import system:
- **Scryfall Server**: Card lookup and search functionality
- **Analysis Server**: Deck analysis tools (composed from 4 specialized modules)

#### Configuration

All configuration is centralized in `config.py` with sensible defaults:

```python
# Scryfall API settings
api_base: str = "https://api.scryfall.com"
batch_size: int = 75
request_timeout: int = 30

# Command Zone template targets
ramp_target: int = 10
card_advantage_target: int = 12
lands_target: int = 38

# Caching behavior
max_card_cache_size: int = 10000
ttl_seconds: int = 3600
```

### Key Implementation Features

#### Intelligent Caching
- **Unified caching** across all tools to minimize API calls
- **Batch operation caching** - batch lookups populate cache for future single lookups
- **Search result caching** to avoid repeated identical searches
- **Cross-tool cache sharing** for maximum efficiency

#### Command Zone Integration
The server implements the official Command Zone deckbuilding template:
- Automated card categorization using oracle text analysis
- Balance assessment against proven targets
- Priority-based improvement recommendations
- JSON output for programmatic analysis

#### Robust Error Handling
- Graceful handling of missing cards and API errors
- Automatic fallback from batch to individual lookups
- Comprehensive input validation
- Detailed error messages with actionable guidance

### Quality Assurance

```bash
# Type checking
uv run mypy .

# Linting
uv run ruff check .

# Code formatting
uv run ruff format .

# Run tests
uv run pytest
```

### Adding New Tools

1. Create your tool in the appropriate module (or create a new one)
2. Import it in the relevant server composition file
3. Add comprehensive tests
4. Update documentation

### Configuration Management

Modify `config.py` to adjust:
- Scryfall API settings
- Command Zone template targets
- Caching behavior
- Server performance parameters

### Dependencies

- **fastmcp>=2.9.0** - MCP server framework
- **httpx** - Async HTTP client for Scryfall API
- **mypy>=1.16.1** - Type checking (development)
- **ruff>=0.12.0** - Linting and formatting (development)
- **pytest>=8.0.0** - Testing framework (development)

### API Integration

#### Scryfall API
- Uses the official [Scryfall API](https://scryfall.com/docs/api) for all card data
- Implements batch operations using the `/cards/collection` endpoint
- Supports fuzzy card name matching for user-friendly lookups
- Comprehensive search using Scryfall's advanced query syntax

#### Rate Limiting & Ethics
- Implements intelligent caching to minimize API calls
- Respects Scryfall's terms of service
- Uses batch operations when possible for efficiency
- Includes configurable request timeouts and retry logic

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with tests
4. Run the quality assurance tools
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Scryfall](https://scryfall.com/) for providing the comprehensive Magic: The Gathering API
- [The Command Zone](https://www.commandzone.com/) podcast for the deckbuilding template framework
- [FastMCP](https://gofastmcp.com/) for the excellent MCP server framework
