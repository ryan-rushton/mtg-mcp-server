"""Resources and prompts for MTG analysis guidance."""

from fastmcp import FastMCP

analysis_resources_server: FastMCP = FastMCP("MTG Analysis Resources Server")


# Add Command Zone template as a resource
@analysis_resources_server.resource("file://command-zone-template")
def get_command_zone_template() -> str:
    """
    The official Command Zone podcast deckbuilding template for Commander decks.

    This resource provides the complete framework for building balanced, functional
    Commander decks with proper interaction and consistency.
    """
    try:
        with open("COMMAND_ZONE_TEMPLATE.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        return """# Command Zone Template (Fallback)
        
## Core Categories:
- **Lands**: 38 (includes MDFCs, utility lands, land cyclers)
- **Card Advantage**: 12+ (true draw, impulse, exile-to-play)
- **Ramp**: 10-12+ (mana acceleration beyond land drops)
- **Targeted Disruption**: 12 (removal, counters, bounce, graveyard hate)
- **Mass Disruption**: 6 (wraths, artifact wipes, fogs, stax)
- **Plan/Synergy Cards**: ~30 (win conditions, synergy pieces, combos)

## Key Principles:
- Cards can overlap categories (MDFCs, ETB creatures, modal spells)
- Template is a guideline - adjust after playtesting
- Don't neglect fundamentals: ramp, draw, interaction, disruption
"""


@analysis_resources_server.prompt("analyze-commander-deck")
def analyze_commander_deck_prompt(commander: str, decklist: str) -> str:
    """
    Prompt for analyzing a Commander deck using the new simplified parameters.

    This prompt guides the LLM to use the updated analysis_analyze_commander_deck tool
    which now takes just a commander and decklist and handles everything automatically.
    """
    return f"""You are analyzing a Commander deck for {commander}.

The provided deck list is:
{decklist}

## Important: Identify Deck Strategy
FIRST, look for clues about the deck's strategy in:
- The user's original request (did they mention "token deck", "sacrifice", "+1/+1 counters", etc.?)
- The commander's abilities and common archetypes
- Obvious synergies in the card list

IF the strategy isn't clear, ask them to clarify:
- "What's your deck's main strategy?" 
- "Is this a token deck, +1/+1 counters, aristocrats, combo, voltron, control, etc.?"
- "What's your win condition or main gameplan?"

This information is CRITICAL for properly categorizing Plan Cards and providing relevant recommendations.

## Your Analysis Process:
Follow this step-by-step analysis workflow:

### Step 1: Preliminary Analysis
First, run these basic analysis tools to understand the deck foundation:

1. **analyze_card_types** - Get comprehensive card type breakdown
   ```
   analysis_analyze_card_types(card_names=[parsed deck list])
   ```

2. **calculate_mana_curve** - Understand the deck's speed and curve
   ```
   analysis_calculate_mana_curve(card_names=[parsed deck list])
   ```

3. **analyze_lands** - Evaluate the mana base
   ```
   analysis_analyze_lands(card_names=[parsed deck list])
   ```

### Step 2: Commander Framework Analysis
Then use the comprehensive Commander analysis:

4. **analyze_commander_deck** - Full Command Zone framework analysis
   ```
   analysis_analyze_commander_deck(commander="{commander}", decklist=[parsed deck list])
   ```

## What Each Tool Provides:
- **Card Types**: Shows ALL card types found (Creature, Instant, Sorcery, Artifact, Enchantment, Land, etc.) with counts and percentages
- **Mana Curve**: CMC distribution to assess deck speed and mana requirements  
- **Lands**: Land count, color production, and mana base evaluation
- **Commander Analysis**: Command Zone categorization with detailed card lists and improvement recommendations

## Your Role:
1. Ask about deck strategy/gameplan if not provided
2. Parse the deck list into a clean list of card names, ensure that if names appear multiple times, they are counted correctly:
   - "2x Lightning Bolt" = 2 copies
   - "4 Forest" = 4 copies  
   - Multiple lines: "2 Forest\n2 Forest" = 4 total copies
   - Handle both quantity prefixes and duplicate entries
3. Run ALL FOUR analysis tools in the order above
4. Synthesize the results from all analyses
5. Present comprehensive findings with strategy-aware suggestions
6. Use the preliminary analyses to inform your interpretation of the Commander analysis. IMPORTANT: When categorizing the cards it is expected that cards can fall into multiple categories, so be sure to categorize them in all relevant categories. Examples:
   - "Ashnod's Altar" = Ramp + Plan/Synergy card (for sacrifice decks)
   - "Skullclamp" = Card Advantage + Targeted Disruption (kills small creatures)
   - "Beast Within" = Targeted Disruption + minor Ramp (gives opponent a token)
   - "Deadly Dispute" = Card Advantage + synergizes with sacrifice themes
7. For all cards that are being suggested use the scryfall_lookup_cards(card_names: List[str]) to fetch the card data and provide detailed information about the cards, including mana cost, type, abilities, and any relevant synergies or interactions. It is CRITICAL that the suggested cards have the correct mana types for the deck's color identity. If any suggested cards are not found, provide alternative suggestions.
8. When suggesting cards, provide options at different budget levels when possible (budget alternatives to expensive cards).
9. Validate your analysis: Ensure total deck size is reasonable for Commander format (99 + commander), and that your categorization accounts for most cards in the deck.

## Output Formats:
- **Card Types**: Text output with type counts, percentages, and Commander guidelines
- **Mana Curve**: Text output showing CMC distribution
- **Lands**: Text output with land count and color production
- **Commander Analysis**: JSON output with structured data including:
  - `commander`: name, colors, color_identity
  - `cards`: all deck cards with properties
  - `command_zone_targets`: framework targets for each category
  - `instructions`: detailed categorization requirements

## Analysis Synthesis:
Combine insights from all four tools to provide:
1. **Foundation Assessment**: Card types, curve, and mana base evaluation
2. **Strategic Analysis**: Command Zone framework with specific card categorizations
3. **Integrated Recommendations**: Suggestions that address both fundamental issues (from basic analysis) and strategic improvements (from Commander analysis)
4. **Prioritized Recommendations**: Present suggestions in order of importance:
   - Critical fixes (format violations, severe mana issues)
   - High-impact improvements (missing fundamentals like ramp/draw)
   - Strategic enhancements (cards that support the specific gameplan)
   - Optional upgrades (budget permitting)

Use this multi-layered approach to provide comprehensive, actionable deck improvement advice!"""
