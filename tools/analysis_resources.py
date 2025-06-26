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
    Comprehensive prompt for analyzing Commander decks using the Command Zone framework.

    This prompt provides thorough guidance for LLM-based Commander deck analysis,
    including mana curve evaluation, card validity assessment, bracket system integration,
    and mandatory card recommendation validation via Scryfall API.
    """
    return f"""You are conducting a comprehensive Commander deck analysis for {commander}.

Deck list provided:
{decklist}

## CRITICAL ANALYSIS REQUIREMENTS

### 0. MANDATORY CARD COUNTING AND DECK PARSING

**BEFORE ANY ANALYSIS**, you must correctly parse and count the deck list to ensure accurate analysis:

**Card Counting Rules:**
Commander decks must have exactly 100 cards total (99 + commander). You must account for ALL duplicate formats:

**Quantity Prefix Formats:**
- `4 Forest` = 4 copies of Forest
- `3x Swamp` = 3 copies of Swamp  
- `2 Lightning Bolt` = 2 copies of Lightning Bolt
- `1x Sol Ring` = 1 copy of Sol Ring
- `Forest` (no quantity) = 1 copy of Forest

**Platform-Specific Formats:**

**MTG Arena Format:**
- `1 Lightning Bolt (M21) 162` = 1 Lightning Bolt (ignore set/collector number)
- `4 Forest (M21) 274` = 4 Forest
- `1 Jace, the Mind Sculptor (A25) 62` = 1 Jace, the Mind Sculptor

**Moxfield/Archidekt Format:**
- `1x Command Tower` = 1 Command Tower
- `4x Forest` = 4 Forest
- `1x Atraxa, Praetors' Voice` = 1 Atraxa, Praetors' Voice

**Set Code Variations:**
- `1 Sol Ring (C21) 263` = 1 Sol Ring
- `1x Lightning Bolt [M21] 162` = 1 Lightning Bolt
- `4 Forest (Basic Land)` = 4 Forest
- `1 Command Tower {{C16}} 284` = 1 Command Tower

**Treatment/Foil Indicators (ignore these):**
- `1 Sol Ring *F*` = 1 Sol Ring (ignore foil indicator)
- `1x Lightning Bolt (FOIL)` = 1 Lightning Bolt
- `1 Command Tower [Etched]` = 1 Command Tower
- `1x Jace, the Mind Sculptor (Showcase)` = 1 Jace, the Mind Sculptor

**Category Headers (skip these lines entirely):**
- `// Lands` → Skip this line
- `Creature (15)` → Skip this line
- `## Commander (1)` → Skip this line
- `Land (38)` → Skip this line
- `Instant/Sorcery (12)` → Skip this line

**Commander Identification:**
- `Commander:` → Skip the header, parse the card on next line
- `SB: 1 Atraxa, Praetors' Voice` → Parse as commander (Cockatrice format)
- Lines under `## Commander` or `// Commander` sections

**Multiple Line Duplicates:**
- `3 Swamp` + `2 Swamp` = 5 total copies of Swamp
- `Forest` + `Forest` + `Forest` = 3 total copies of Forest
- `Lightning Bolt` + `2 Lightning Bolt` = 3 total copies of Lightning Bolt

**Complex Parsing Examples:**
- `4 Forest (M21) 274` → Parse as: Forest, Forest, Forest, Forest
- `3x Swamp *F*` + `2 Swamp (Basic)` → Parse as: Swamp, Swamp, Swamp, Swamp, Swamp  
- `1 Jace, the Mind Sculptor (A25) 62` + `Jace, the Mind Sculptor` → Parse as: Jace, the Mind Sculptor, Jace, the Mind Sculptor

**Special Cases for Legal Duplicates:**
- **Basic Lands**: Forest, Island, Mountain, Plains, Swamp, Wastes can appear multiple times
- **Snow-Covered Basics**: Snow-Covered Forest, Snow-Covered Island, etc. can appear multiple times
- **Nazgûl**: The card "Nazgûl" specifically can appear multiple times (up to 9 copies)
- **Relentless Rats**: Can appear multiple times
- **Shadowborn Apostle**: Can appear multiple times
- **Rat Colony**: Can appear multiple times
- **Persistent Petitioners**: Can appear multiple times

**Comprehensive Deck Parsing Process:**
1. **Clean and normalize lines**:
   - Skip empty lines and category headers
   - Remove comments (lines starting with //, #, or similar)
   - Strip treatment indicators (*F*, (FOIL), [Etched], etc.)
   - Remove set codes and collector numbers
   
2. **Parse quantity indicators**:
   - Extract numbers at start of line (1, 2, 3, 4, etc.)
   - Handle "x" format (1x, 2x, 3x, 4x, etc.)
   - Default to 1 if no quantity specified
   
3. **Extract clean card names**:
   - Remove quantity prefixes
   - Remove set codes in (), [], {{}} formats
   - Remove collector numbers
   - Handle special characters (apostrophes, commas, hyphens)
   
4. **Identify commanders**:
   - Cards in Commander/SB sections
   - Cards following "Commander:" headers
   - Single copies of legendary creatures (contextual)
   
5. **Combine duplicates** across multiple lines and formats
6. **Create final card list** with total quantities
7. **Validate total count** equals 99 cards (+ commander = 100 total)
8. **Flag any issues** with deck size or illegal duplicates

**Comprehensive Parsing Examples:**

**Example 1 - Mixed Platform Formats:**
```
Input deck list:
// Lands
4 Forest (M21) 274
1x Command Tower
1 Sol Ring (C21) 263 *F*
Swamp
2x Swamp (Basic Land)

## Commander (1)
1 Atraxa, Praetors' Voice (C16) 28

Parsed result:
- Forest: 4 copies
- Command Tower: 1 copy
- Sol Ring: 1 copy (foil indicator removed)
- Swamp: 3 copies (1 + 2)
- Commander: Atraxa, Praetors' Voice
Total: 9 cards + commander = 10 total

No issues detected.
```

**Example 2 - MTG Arena Export:**
```
Input deck list:
1 Lightning Bolt (M21) 162
1 Counterspell (M21) 267
4 Forest (M21) 274
1 Jace, the Mind Sculptor (A25) 62

Commander
1 Atraxa, Praetors' Voice (C16) 28

Parsed result:
- Lightning Bolt: 1 copy
- Counterspell: 1 copy
- Forest: 4 copies
- Jace, the Mind Sculptor: 1 copy
- Commander: Atraxa, Praetors' Voice
Total: 7 cards + commander = 8 total
```

**Example 3 - Complex Multi-Format:**
```
Input deck list:
Creature (15)
1x Llanowar Elves
1 Birds of Paradise (M12) 165
Elvish Mystic
2x Fyndhorn Elves *F*

Land (38)  
4 Forest (Basic)
Command Tower
1x Reflecting Pool [Shadowmoor] 162

// Commander
1 Ezuri, Renegade Leader (SOM) 119

Parsed result:
- Llanowar Elves: 1 copy
- Birds of Paradise: 1 copy
- Elvish Mystic: 1 copy
- Fyndhorn Elves: 2 copies
- Forest: 4 copies
- Command Tower: 1 copy
- Reflecting Pool: 1 copy
- Commander: Ezuri, Renegade Leader
Total: 11 cards + commander = 12 total
```

**Additional Format Considerations:**

**Edge Cases to Handle:**
- **Double-sided cards**: `Jace, Vryn's Prodigy // Jace, Telepath Unbound` → Parse as "Jace, Vryn's Prodigy"
- **Split cards**: `Fire // Ice` → Parse as "Fire // Ice" (keep full name)
- **Adventure cards**: `Brazen Borrower // Petty Theft` → Parse as "Brazen Borrower"
- **Alternative names**: Handle both `Gideon Blackblade` and `Gideon, Blackblade`
- **Unicode characters**: Handle cards with special symbols (âēîōû, etc.)

**Maybeboard/Sideboard Indicators:**
- Lines starting with `SB:` (Cockatrice sideboard)
- Lines under `Maybeboard` or `Sideboard` sections
- Lines starting with `//` followed by card names (some formats)

**Quantity Zero Handling:**
- `0 Lightning Bolt` → Should be ignored/skipped
- Cards with quantity 0 in various formats

**Whitespace and Formatting:**
- Handle inconsistent spacing and tabs
- Trim leading/trailing whitespace from card names
- Handle mixed case variations

**Error Handling:**
- **Deck size errors**: Flag if total ≠ 99 cards
- **Illegal duplicates**: Flag non-basic lands with multiple copies (except legal exceptions)
- **Parsing errors**: Flag cards that can't be parsed or identified
- **Format ambiguity**: Flag unclear lines that need manual review
- **Missing commander**: Flag if no commander is identified
- **Multiple commanders**: Flag if more than one commander is found

**Required Pre-Analysis Output:**
Before proceeding with ANY analysis tools, you MUST provide:

1. **Parsing Summary**:
   - Total lines processed
   - Lines skipped (headers, comments, empty)
   - Successfully parsed card entries
   - Failed/ambiguous parsing attempts

2. **Deck Composition**:
   - Commander identified: [Name]
   - Total deck cards: [Number] (should be 99)
   - Total deck size: [Number] (should be 100 including commander)

3. **Duplicate Analysis**:
   - Cards with multiple copies and their counts
   - Legal duplicates (basic lands, special exceptions)
   - Potentially illegal duplicates flagged for review

4. **Format Violations**:
   - Deck size issues (not 99 + commander)
   - Illegal duplicate non-basic lands
   - Cards that couldn't be parsed
   - Missing or multiple commanders

5. **Final Card List**:
   - Clean, parsed list ready for analysis tools
   - Format: ["Card Name", "Card Name", "Card Name", ...] with all duplicates expanded

### 1. MANDATORY DECK STRATEGY IDENTIFICATION
BEFORE any analysis, identify the deck's primary strategy:
- Examine the user's original request for strategy keywords (tokens, sacrifice, counters, combo, voltron, control, etc.)
- Analyze the commander's abilities and typical archetypes
- Look for obvious synergies and themes in the card list
- If strategy is unclear, ask specific questions:
  - "What is your deck's primary win condition?"
  - "What archetype does this deck represent?" (aggro, midrange, control, combo)
  - "What are the key synergies you're trying to exploit?"

### 2. COMPREHENSIVE ANALYSIS WORKFLOW

**CRITICAL**: Use the correctly parsed and counted card list for ALL analysis tools.

#### Phase 1: Foundation Analysis
Execute these tools in order to establish deck fundamentals:

1. **Card Type Analysis** - Essential for understanding deck composition
   ```
   analysis_analyze_card_types(card_names=[correctly_parsed_card_list_with_quantities])
   ```

2. **Mana Curve Analysis** - Critical for speed and consistency assessment
   ```
   analysis_calculate_mana_curve(card_names=[correctly_parsed_card_list_with_quantities])
   ```

3. **Mana Base Analysis** - Evaluate land count and color production
   ```
   analysis_analyze_lands(card_names=[correctly_parsed_card_list_with_quantities])
   ```

4. **Color Identity & Requirements Analysis** - Assess color balance and requirements
   ```
   analysis_analyze_color_identity(card_names=[correctly_parsed_card_list_with_quantities])
   analysis_analyze_mana_requirements(card_names=[correctly_parsed_card_list_with_quantities])
   ```

#### Phase 2: Strategic Framework Analysis
5. **Command Zone Framework Analysis** - Comprehensive categorization
   ```
   analysis_analyze_commander_deck(commander="{commander}", decklist=[correctly_parsed_card_list_with_quantities])
   ```

**Important Notes:**
- **Always use the expanded card list** where "4 Forest" becomes ["Forest", "Forest", "Forest", "Forest"]
- **Include all duplicates** in the analysis to get accurate mana curve and type distribution
- **Verify card counts** match your parsing before running tools

### 3. THOROUGH MANA CURVE EVALUATION

Provide detailed mana curve analysis including:

**Curve Distribution Assessment:**
- 0-2 CMC: Early game presence and efficiency
- 3-4 CMC: Mid-game power and consistency
- 5-6 CMC: Late game threats and haymakers
- 7+ CMC: High-impact finishers and bombs

**Curve Quality Metrics:**
- **Curve Smoothness**: Gaps in the curve that could cause awkward hands
- **Early Game Density**: Sufficient 1-2 mana plays for tempo
- **Mid-Game Power**: 3-4 mana value engines and threats
- **Top-End Payoffs**: High-impact expensive spells worth ramping into
- **Average CMC**: Should typically be 3.0-4.5 for most strategies

**Strategic Curve Alignment:**
- **Aggro/Tempo**: Heavy concentration 1-3 CMC (avg 2.5-3.5)
- **Midrange**: Balanced curve 2-5 CMC (avg 3.5-4.5)
- **Control**: Higher curve 3-6+ CMC (avg 4.0-5.0)
- **Combo**: Depends on combo pieces, but needs early setup (avg 3.0-4.0)

### 4. CARD VALIDITY AND OPTIMIZATION

For each card in the deck, evaluate:

**Format Legality:**
- Commander format legality
- Color identity compliance
- Singleton restriction adherence

**Strategic Relevance:**
- Alignment with deck strategy
- Synergy with commander abilities
- Power level appropriateness

**Efficiency Assessment:**
- Mana cost to effect ratio
- Board impact and versatility
- Replacement options if suboptimal

### 5. COMMAND ZONE FRAMEWORK CATEGORIZATION

**CRITICAL**: Cards MUST be categorized in ALL relevant categories. Examples:

**Multi-Category Cards:**
- **Skullclamp**: Card Advantage + Targeted Disruption (kills small creatures) + Plan/Synergy (aristocrats)
- **Ashnod's Altar**: Ramp + Plan/Synergy (sacrifice decks) + Targeted Disruption (sacrifice response)
- **Beast Within**: Targeted Disruption + minor Ramp (gives opponent token) + Mass Disruption (hits any permanent)
- **Deadly Dispute**: Card Advantage + Plan/Synergy (sacrifice themes) + Instant speed value
- **Modal Double-Faced Cards**: Lands + Spells (count as both categories)
- **Creatures with ETB effects**: Plan/Synergy + Targeted/Mass Disruption
- **Ramp spells that fix mana**: Ramp + deck consistency

**Category Definitions (Command Zone Framework):**

**Lands (Target: 38):**
- Basic and non-basic lands
- MDFCs (Modal Double-Faced Cards) that can be played as lands
- Utility lands with activated abilities
- Land-cycling cards that can find lands

**Card Advantage (Target: 12+, Optimal: 15+):**
- Draw engines and repeated card draw
- Impulse draw and exile-to-play effects
- Self-mill when graveyard is a resource
- Tutors that generate virtual card advantage
- NOT card selection without advantage (e.g., Faithless Looting)

**Ramp (Target: 10+, Optimal: 12+):**
- Mana rocks (Sol Ring, Signets, Talismans)
- Mana dorks (Elvish Mystic, Birds of Paradise)
- Ramp spells (Cultivate, Kodama's Reach)
- Permanent mana acceleration
- NOT temporary mana (Dark Ritual, Jeska's Will) unless part of combo

**Targeted Disruption (Target: 12):**
- Single-target removal (Swords to Plowshares, Path to Exile)
- Counterspells (Counterspell, Negate)
- Artifact/enchantment removal (Naturalize, Disenchant)
- Bounce spells (Cyclonic Rift in single-target mode)
- Graveyard hate (Tormod's Crypt, Relic of Progenitus)

**Mass Disruption (Target: 6):**
- Board wipes (Wrath of God, Blasphemous Act)
- Mass artifact/enchantment removal (Bane of Progress)
- Graveyard resets (Bojuka Bog, Rest in Peace)
- Stax effects (Thalia, Guardian of Thraben)
- Fogs and damage prevention (Teferi's Protection)

**Plan/Synergy Cards (Target: ~30):**
- Win conditions and finishers
- Synergy pieces that support the strategy
- Combo pieces and enablers
- Value engines specific to the strategy
- Flavor cards that enhance the theme

### 6. COMMANDER BRACKET SYSTEM INTEGRATION

Assess the deck's bracket level using both official criteria and practical tournament experience:

**Practical Bracket Characteristics (Based on Tournament Data):**

**Bracket 2 - Battlecruiser (4-5 turns setup, games end turn 10+):**
- **Setup Phase**: 4-5 turns of ramping and board development
- **Game Length**: Typically ends turn 10 or later
- **Strategy**: Resilience over speed, big splashy plays
- **Win Conditions**: Primarily damage-based, combat-focused
- **Interaction Level**: Limited, focuses on threats over answers
- **Power Floor**: Average preconstructed deck (NOT the ceiling!)
- **Tempo**: Not a major factor, players have time to recover
- **Example Cards**: Big creatures, expensive spells, minimal fast mana

**Bracket 3 - Upgraded (2-3 turns setup, games end turn 7+):**
- **Setup Phase**: 2-3 turns of efficient development
- **Game Length**: Win attempts with protection starting turn 7
- **Strategy**: Tempo becomes significant, smooth curves matter
- **Win Conditions**: Still mostly damage-based, but faster
- **Interaction Level**: Meaningful interaction expected
- **Power Level**: More powerful than most players realize
- **Tempo**: Curving out and early pressure matter
- **Example Cards**: Efficient threats, some fast mana, protection

**Bracket 4 - Optimized (1-2 turns setup, games end turn 4+):**
- **Setup Phase**: 1-2 turns before major plays
- **Game Length**: Serious win attempts starting turn 4-5
- **Strategy**: "Diet cEDH" - maximum efficiency
- **Win Conditions**: Combos, stax, degenerate strategies
- **Interaction Level**: Free interaction expected and necessary
- **Fast Mana**: Expected and required to compete
- **Tempo**: Every turn and mana matters critically
- **Example Cards**: Fast mana package, free counterspells, tutors

**Fast Mana Assessment (Critical for Higher Brackets):**

**Bracket 2 Fast Mana:**
- Sol Ring (universal)
- Signets, Talismans (color fixing)
- Cultivate, Kodama's Reach (ramp spells)

**Bracket 3 Fast Mana:**
- Sol Ring + 2-3 additional mana rocks
- Command Tower, Arcane Signet
- Some 0-1 CMC acceleration
- Efficient land ramp

**Bracket 4 Fast Mana Package:**
- **Mana Crypt** (Game Changer)
- **Mana Vault** (Game Changer) 
- **Chrome Mox, Mox Diamond** (Game Changers)
- **Ancient Tomb, City of Traitors**
- Full suite of 0-2 CMC mana acceleration
- Multiple ways to accelerate on turn 1

**Game Changers Assessment:**
Identify cards that significantly impact game speed and power:

**Fast Mana Game Changers:**
- Mana Crypt, Mana Vault, Chrome Mox, Mox Diamond
- Grim Monolith, Basalt Monolith
- Ancient Tomb, City of Traitors

**Powerful Tutors:**
- Demonic Tutor, Vampiric Tutor, Enlightened Tutor
- Mystical Tutor, Worldly Tutor, Survival of the Fittest

**High-Impact Permanents:**
- Necropotence, Teferi's Protection, Humility
- Rhystic Study, Mystic Remora, Smothering Tithe

**Stax and Control:**
- Winter Orb, Static Orb, Trinisphere (removed from Game Changers)
- Rule of Law, Sphere of Resistance
- Mass land destruction (Armageddon, Ravages of War)

**Free Interaction (Bracket 4 Expected):**
- Force of Will, Force of Negation, Fierce Guardianship
- Deflecting Swat, Deadly Rollick
- Mental Misstep, Pact of Negation

**Bracket Assessment Methodology:**
1. **Count Game Changers cards** (official criteria)
2. **Evaluate fast mana density** (practical speed assessment)
3. **Assess setup time requirements** (turns needed before major plays)
4. **Identify win turn potential** (earliest realistic win)
5. **Check interaction suite** (ability to stop opponents)
6. **Consider overall optimization** (card quality and synergy)

**Bracket Recommendation Framework:**
- **Bracket 2**: 0-1 Game Changers, minimal fast mana, setup-heavy
- **Bracket 3**: 1-3 Game Changers, moderate fast mana, tempo-aware
- **Bracket 4**: 3+ Game Changers, extensive fast mana, free interaction
- **Bracket 5 (cEDH)**: Maximum optimization, consistent turn 2-4 wins

### 7. MANDATORY CARD RECOMMENDATION VALIDATION

**CRITICAL REQUIREMENT**: ALL recommended cards MUST be validated using scryfall_lookup_cards.

**Validation Process:**
1. **Before making ANY recommendations**, compile a list of all suggested cards
2. **Execute scryfall_lookup_cards** with the complete list:
   ```
   scryfall_lookup_cards(card_names=[list_of_all_recommended_cards])
   ```
3. **Analyze returned data** for each card:
   - **Color Identity**: Verify compatibility with commander's color identity
   - **Mana Cost**: Confirm fit with deck's curve and strategy
   - **Type Line**: Ensure card type aligns with stated purpose
   - **Oracle Text**: Validate synergies and interactions claimed
   - **Power Level**: Assess appropriateness for deck's bracket

**Recommendation Criteria:**
- **Color Identity Compliance**: Cards MUST match commander's color identity
- **Mana Curve Fit**: Consider impact on curve distribution
- **Strategic Synergy**: Clear connection to deck's primary strategy
- **Power Level**: Appropriate for intended bracket level
- **Budget Considerations**: Provide alternatives at different price points

**If Cards Are Not Found:**
- Acknowledge the invalid suggestion
- Provide alternative cards with similar effects
- Re-validate alternatives using scryfall_lookup_cards

### 8. COMPREHENSIVE ANALYSIS SYNTHESIS

**Foundation Assessment:**
- Card type distribution and gaps
- Mana curve analysis with specific recommendations
- Mana base evaluation and fixing needs
- Color balance and requirements

**Strategic Framework Evaluation:**
- Command Zone category compliance
- Multi-category card identification
- Synergy analysis and theme coherence
- Win condition assessment

**Power Level and Bracket Analysis:**
- **Game Changers identification** with count and impact assessment
- **Fast mana density evaluation** (critical for higher brackets)
- **Setup time analysis** (turns needed before major plays)
- **Win turn potential** (earliest realistic win attempts)
- **Interaction suite assessment** (especially free interaction for Bracket 4)
- **Bracket recommendation** with detailed justification using both official criteria and practical tournament data
- **Optimization suggestions** for target bracket with specific focus on:
  - Fast mana improvements for higher brackets
  - Interaction density for competitive play  
  - Win condition efficiency for faster games

**Prioritized Recommendations (in order):**
1. **Critical Fixes**: Format violations, severe mana issues, missing win conditions
2. **Framework Compliance**: Command Zone category deficiencies
3. **Strategic Improvements**: Cards that enhance primary strategy
4. **Curve Optimization**: Filling gaps in mana curve
5. **Power Level Adjustments**: Bracket-appropriate upgrades
6. **Budget Alternatives**: Lower-cost options for expensive cards

### 9. FINAL VALIDATION CHECKLIST

Before presenting analysis, verify:
- ✅ All recommended cards validated via scryfall_lookup_cards
- ✅ Color identity compliance confirmed for all suggestions
- ✅ Mana curve implications addressed
- ✅ Multi-category card memberships identified
- ✅ Command Zone targets evaluated
- ✅ **Comprehensive bracket assessment** performed using both official criteria and practical tournament data
- ✅ **Fast mana density** evaluated for bracket appropriateness
- ✅ **Setup time and win turn potential** analyzed
- ✅ Strategic coherence maintained
- ✅ Budget alternatives provided where applicable

**Output Structure:**
1. **Executive Summary**: Deck strategy, bracket level (with tournament-based justification), key strengths/weaknesses
2. **Foundation Analysis**: Types, curve, mana base, colors
3. **Command Zone Framework**: Category breakdown with multi-category cards
4. **Strategic Assessment**: Synergy analysis and win condition evaluation
5. **Enhanced Bracket Analysis**: 
   - Game Changers count and assessment
   - Fast mana density and bracket appropriateness
   - Setup time analysis (turns to major plays)
   - Win turn potential (earliest realistic wins)
   - Interaction suite evaluation
   - Final bracket recommendation with both official and practical justification
6. **Prioritized Recommendations**: Validated suggestions with alternatives and bracket-specific improvements
7. **Implementation Guidance**: Specific next steps for deck improvement, including bracket optimization paths

This comprehensive analysis ensures thorough evaluation of every aspect of the Commander deck while providing actionable, validated recommendations for improvement."""
