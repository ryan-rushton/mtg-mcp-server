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


# Add Command Zone deck building prompts
@analysis_resources_server.prompt("mtg-analysis-workflow")
def mtg_workflow() -> str:
    """
    Primary workflow prompt for MTG analysis - guides LLMs to use tools effectively.
    """
    return """For MTG requests, follow this essential pattern:

1. ALWAYS start with scryfall_lookup_cards for validation
2. Use specific analysis tools based on user questions:
   - "analyze deck" → analysis_analyze_commander_deck
   - "mana curve" → analysis_calculate_mana_curve  
   - "color fixing" → analysis_analyze_lands + analysis_analyze_mana_requirements
   - "what types" → analysis_analyze_card_types
3. Provide actionable recommendations, not just data
4. Focus on the most impactful improvements first

Remember: Users want help improving their decks, not just statistics."""


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

## Your Task:
Use the analysis_analyze_commander_deck tool with these parameters:
- commander: "{commander}"
- decklist: [Parse the deck list above into individual card names - clean format with one card name per list item]

## What the Tool Does Automatically:
1. Looks up all cards using Scryfall for validation
2. Automatically categorizes cards into Command Zone framework:
   - **Lands (38)**: All lands including utility lands
   - **Card Advantage (12+)**: True card draw and advantage
   - **Ramp (10-12+)**: Mana acceleration beyond land drops
   - **Targeted Disruption (12)**: One-for-one answers
   - **Mass Disruption (6)**: Board wipes and protection
   - **Plan/Synergy Cards (~30)**: Win conditions and synergy pieces
3. Provides balance assessment and improvement recommendations

## Your Role:
1. Parse the deck list into a clean list of card names
2. Call the tool with commander and decklist
3. Parse the JSON response to access specific analysis data
4. Present findings in a user-friendly format with actionable suggestions

## JSON Response Structure:
The tool returns structured JSON with these key sections:
- `commander`: name, colors, color_identity
- `categories`: Command Zone analysis with counts and status for each category
- `balance_assessment`: overall_score and categories_meeting_targets
- `recommendations`: priority_improvements, efficiency_notes, card_overlap_status
- `categorization`: automatically sorted cards by category

Use this structured data to provide specific, actionable deck improvement advice!"""


@analysis_resources_server.prompt("suggest-deck-improvements")
def suggest_deck_improvements_prompt() -> str:
    """
    Prompt for suggesting specific improvements to a Commander deck.

    This prompt helps the LLM provide actionable upgrade suggestions
    based on Command Zone principles and deck analysis results.
    """
    return """You are suggesting improvements to a Commander deck based on Command Zone principles.

## Analysis Process:
1. First analyze the deck with the Command Zone template
2. Identify the most critical gaps or imbalances
3. Suggest specific cards to add/remove with clear reasoning
4. Consider budget, power level, and deck theme

## Improvement Priorities:
1. **Fix Critical Gaps**: Missing ramp, draw, or interaction
2. **Increase Efficiency**: Cards that serve multiple roles
3. **Enhance Consistency**: More reliable card advantage and ramp
4. **Optimize Mana Base**: Better fixing and utility lands
5. **Strengthen Game Plan**: More focused synergy pieces

## Suggestion Format:
**Priority 1 - Critical:**
- Add: [Specific cards] - Reason
- Remove: [Specific cards] - Reason

**Priority 2 - Optimization:**
- Consider: [Alternative cards] - Benefits

**Priority 3 - Long-term:**
- Upgrade path: [Expensive improvements] - Impact

Focus on the most impactful changes first."""


@analysis_resources_server.resource("mcp://magic-analysis/when-to-analyze")
def analysis_guide() -> str:
    """
    Guide for when to use MTG analysis tools - helps LLMs choose the right tools.
    """
    return """
    ALWAYS use MTG analysis tools when users mention:
    - Deck lists, card lists, or "my deck"
    - "Analyze", "review", "how good", "suggestions"
    - Commander, EDH, or 100-card decks
    - Mana curve, mana base, or color fixing
    - Card advantage, ramp, or removal
    
    ESSENTIAL WORKFLOW:
    1. Start with scryfall_lookup_cards for card validation
    2. Then use appropriate analysis tools based on user questions
    3. Always provide actionable recommendations, not just data
    """


@analysis_resources_server.resource("mcp://examples/common-workflows")
def common_workflows() -> str:
    """
    Example workflows for common MTG analysis requests.
    """
    return """
    Example 1: "Analyze my Commander deck"
    → Use scryfall_lookup_cards first to validate names
    → Categorize cards into Command Zone framework
    → Use analysis_analyze_commander_deck
    → Provide specific improvement suggestions
    
    Example 2: "Is my mana base good?"
    → Use analysis_analyze_lands for land count/colors
    → Use analysis_analyze_mana_requirements for spell coverage
    → Focus on actionable mana base improvements
    
    Example 3: "My deck is too slow"
    → Use analysis_calculate_mana_curve
    → Focus on CMC 0-3 cards and ramp recommendations
    → Suggest specific low-cost alternatives
    
    Example 4: "What colors should I add?"
    → Use analysis_analyze_color_identity
    → Use analysis_analyze_mana_requirements for gaps
    → Recommend specific lands and fixing
    """


@analysis_resources_server.resource("file://commander-staples")
def get_commander_staples() -> str:
    """
    List of commonly played Commander staples by category.

    This resource provides examples of popular cards in each Command Zone category
    to help with deck building and card recommendations.
    """
    return """# Commander Staples by Category

## Ramp (10-12+ cards)
**Artifacts:** Sol Ring, Arcane Signet, Fellwar Stone, Talisman cycle, Signet cycle
**Green Spells:** Cultivate, Kodama's Reach, Rampant Growth, Nature's Lore, Three Visits
**Creatures:** Llanowar Elves, Birds of Paradise, Farhaven Elf, Wood Elves

## Card Advantage (12+ cards)  
**Enchantments:** Rhystic Study, Phyrexian Arena, Sylvan Library, Mystic Remora
**Creatures:** Beast Whisperer, Guardian Project, Mentor of the Meek
**Spells:** Harmonize, Sign in Blood, Read the Bones, Brainstorm

## Targeted Disruption (12 cards)
**Removal:** Swords to Plowshares, Path to Exile, Beast Within, Chaos Warp
**Counters:** Counterspell, Swan Song, Negate, Dispel  
**Versatile:** Assassin's Trophy, Generous Gift, Rapid Hybridization

## Mass Disruption (6 cards)
**Board Wipes:** Wrath of God, Day of Judgment, Blasphemous Act, Toxic Deluge
**Protection:** Teferi's Protection, Boros Charm, Heroic Intervention
**Utility:** Cyclonic Rift, Austere Command

## Essential Lands
**Fixing:** Command Tower, Exotic Orchard, Reflecting Pool
**Utility:** Reliquary Tower, Ghost Quarter, Strip Mine
**Budget:** Evolving Wilds, Terramorphic Expanse, basics

## Utility/Staples
**Protection:** Lightning Greaves, Swiftfoot Boots, Mother of Runes
**Recursion:** Eternal Witness, Regrowth, Sun Titan
**Card Selection:** Sensei's Divining Top, Scroll Rack
"""
