import asyncio
from fastmcp import Client

client: Client = Client("server.py")


async def lookup_cards_example():
    """Example: Look up a list of specific cards"""
    print("=== Looking up specific cards ===")
    async with client:
        result = await client.call_tool(
            "lookup_cards",
            {
                "card_names": [
                    "Lightning Bolt",
                    "Counterspell",
                    "Black Lotus",
                    "Sol Ring",
                ]
            },
        )
        print(result[0].text)


async def search_cards_example():
    """Example: Search for cards by criteria"""
    print("\n=== Searching for red creatures with CMC 3 ===")
    async with client:
        result = await client.call_tool(
            "search_cards_by_criteria",
            {"colors": "red", "type_line": "creature", "mana_cost": 3, "limit": 5},
        )
        print(result[0].text)


async def search_by_name_example():
    """Example: Search for cards with partial name"""
    print("\n=== Searching for cards with 'dragon' in the name ===")
    async with client:
        result = await client.call_tool(
            "search_cards_by_criteria", {"name": "dragon", "limit": 3}
        )
        print(result[0].text)


async def mana_curve_example():
    """Example: Calculate mana curve for a sample deck"""
    print("\n=== Calculating mana curve for sample cards ===")
    sample_cards = [
        "Lightning Bolt",
        "Sol Ring",
        "Counterspell",
        "Wrath of God",
        "Llanowar Elves",
        "Jace, the Mind Sculptor",
        "Force of Will",
        "Birds of Paradise",
        "Swords to Plowshares",
        "Brainstorm",
    ]
    async with client:
        result = await client.call_tool(
            "calculate_mana_curve", {"card_names": sample_cards}
        )
        print(result[0].text)


async def color_identity_example():
    """Example: Analyze color identity of a sample deck"""
    print("\n=== Analyzing color identity of sample deck ===")
    sample_cards = [
        "Lightning Bolt",
        "Counterspell",
        "Swords to Plowshares",
        "Llanowar Elves",
        "Terminate",
        "Sol Ring",
        "Command Tower",
        "Lightning Helix",
        "Electrolyze",
        "Boros Signet",
        "Azorius Signet",
    ]
    async with client:
        result = await client.call_tool(
            "analyze_color_identity", {"card_names": sample_cards}
        )
        print(result[0].text)


async def card_types_example():
    """Example: Analyze card type distribution"""
    print("\n=== Analyzing card types of sample deck ===")
    sample_cards = [
        "Lightning Bolt",
        "Counterspell",
        "Llanowar Elves",
        "Sol Ring",
        "Wrath of God",
        "Birds of Paradise",
        "Island",
        "Mountain",
        "Jace, the Mind Sculptor",
        "Swords to Plowshares",
        "Forest",
        "Brainstorm",
        "Terminate",
        "Command Tower",
        "Rhystic Study",
    ]
    async with client:
        result = await client.call_tool(
            "analyze_card_types", {"card_names": sample_cards}
        )
        print(result[0].text)


async def lands_analysis_example():
    """Example: Analyze lands in a deck"""
    print("\n=== Analyzing lands in sample deck ===")
    sample_cards = [
        "Command Tower",
        "Sol Ring",
        "Island",
        "Mountain",
        "Forest",
        "Sacred Foundry",
        "Steam Vents",
        "Stomping Ground",
        "Lightning Bolt",
    ]
    async with client:
        result = await client.call_tool("analyze_lands", {"card_names": sample_cards})
        print(result[0].text)


async def interactive_mode():
    """Interactive mode - let user input card names and choose analysis type"""
    print("\n=== Interactive Card Analysis ===")
    print("Choose analysis type:")
    print("  1. Lookup specific cards")
    print("  2. Calculate mana curve")
    print("  3. Analyze color identity")
    print("  4. Analyze card types")
    print("  5. Analyze lands")
    print("  6. Search by criteria")
    print("Type 'quit' to exit")

    async with client:
        while True:
            print("\n" + "=" * 50)
            choice = input("Choose analysis (1-6) or 'quit': ").strip()

            if choice.lower() in ["quit", "exit", "q"]:
                break

            if choice not in ["1", "2", "3", "4", "5", "6"]:
                print("Please enter a number 1-6!")
                continue

            if choice == "6":
                # Search by criteria
                print("\nSearch by criteria:")
                name = input("Card name (partial, optional): ").strip() or None
                colors = (
                    input("Colors (e.g., 'red', 'blue', optional): ").strip() or None
                )
                type_line = (
                    input("Type (e.g., 'creature', 'instant', optional): ").strip()
                    or None
                )
                mana_cost_input = input("Mana cost (number, optional): ").strip()
                mana_cost = int(mana_cost_input) if mana_cost_input.isdigit() else None
                limit = input("Limit (default 10): ").strip()
                limit = int(limit) if limit.isdigit() else 10

                try:
                    result = await client.call_tool(
                        "search_cards_by_criteria",
                        {
                            "name": name,
                            "colors": colors,
                            "type_line": type_line,
                            "mana_cost": mana_cost,
                            "limit": limit,
                        },
                    )
                    print("\n" + result[0].text)
                except Exception as e:
                    print(f"Error: {e}")
                continue

            # For all other choices, get card list
            print("\nEnter card names separated by semicolons (;) or pipes (|)")
            print("Examples:")
            print("  Jace, the Mind Sculptor; Lightning Bolt; Sol Ring")
            print("  Command Tower | Island | Mountain")

            user_input = input("\nCard names: ").strip()

            if not user_input:
                print("Please enter some card names!")
                continue

            # Parse card names (same logic as before)
            card_names = []
            if ";" in user_input:
                card_names = [
                    name.strip() for name in user_input.split(";") if name.strip()
                ]
            elif "|" in user_input:
                card_names = [
                    name.strip() for name in user_input.split("|") if name.strip()
                ]
            elif "," in user_input:
                potential_names = [name.strip() for name in user_input.split(",")]
                if (
                    len(potential_names) == 2
                    and len(potential_names[0]) > 1
                    and not potential_names[1]
                    .strip()
                    .lower()
                    .startswith(("the ", "a ", "an "))
                ):
                    print(f"Interpreting as single card: '{user_input}'")
                    card_names = [user_input]
                else:
                    card_names = potential_names
            else:
                card_names = [user_input]

            if not card_names:
                print("No valid card names found!")
                continue

            # Execute the chosen analysis
            try:
                if choice == "1":
                    result = await client.call_tool(
                        "lookup_cards", {"card_names": card_names}
                    )
                elif choice == "2":
                    result = await client.call_tool(
                        "calculate_mana_curve", {"card_names": card_names}
                    )
                elif choice == "3":
                    result = await client.call_tool(
                        "analyze_color_identity", {"card_names": card_names}
                    )
                elif choice == "4":
                    result = await client.call_tool(
                        "analyze_card_types", {"card_names": card_names}
                    )
                elif choice == "5":
                    result = await client.call_tool(
                        "analyze_lands", {"card_names": card_names}
                    )

                print("\n" + result[0].text)
            except Exception as e:
                print(f"Error: {e}")


async def test_calculate_mana_curve():
    async with client:
        result = await client.call_tool(
            "calculate_mana_curve",
            {
                "card_names": [
                    "Lightning Bolt",
                    "Llanowar Elves",
                    "Island",
                    "Forest",
                    "Shivan Dragon",
                ]
            },
        )
        print("Mana Curve Result:\n", result[0].text)


async def test_analyze_lands():
    async with client:
        result = await client.call_tool(
            "analyze_lands",
            {
                "card_names": [
                    "Island",
                    "Forest",
                    "Plains",
                    "Swamp",
                    "Mountain",
                    "Command Tower",
                ]
            },
        )
        print("Land Analysis Result:\n", result[0].text)


async def test_analyze_color_identity():
    async with client:
        result = await client.call_tool(
            "analyze_color_identity",
            {
                "card_names": [
                    "Lightning Bolt",
                    "Llanowar Elves",
                    "Island",
                    "Forest",
                    "Shivan Dragon",
                    "Swords to Plowshares",
                ]
            },
        )
        print("Color Identity Result:\n", result[0].text)


async def test_analyze_mana_requirements():
    async with client:
        result = await client.call_tool(
            "analyze_mana_requirements",
            {
                "card_names": [
                    "Lightning Bolt",
                    "Llanowar Elves",
                    "Island",
                    "Forest",
                    "Shivan Dragon",
                    "Command Tower",
                ]
            },
        )
        print("Mana Requirements Result:\n", result[0].text)


async def test_analyze_card_types():
    async with client:
        result = await client.call_tool(
            "analyze_card_types",
            {
                "card_names": [
                    "Lightning Bolt",
                    "Llanowar Elves",
                    "Island",
                    "Forest",
                    "Shivan Dragon",
                    "Sol Ring",
                ]
            },
        )
        print("Card Types Result:\n", result[0].text)


async def main():
    """Run all examples"""
    try:
        # Run predefined examples
        await lookup_cards_example()
        await search_cards_example()
        await search_by_name_example()
        await mana_curve_example()
        await color_identity_example()
        await card_types_example()
        await lands_analysis_example()

        # Run test functions for new tools
        await test_calculate_mana_curve()
        await test_analyze_lands()
        await test_analyze_color_identity()
        await test_analyze_mana_requirements()
        await test_analyze_card_types()

        # Optional: Run interactive mode
        run_interactive = (
            input("\nWould you like to try interactive mode? (y/n): ").strip().lower()
        )
        if run_interactive in ["y", "yes"]:
            await interactive_mode()

    except Exception as e:
        print(f"Error running client: {e}")
        print("Make sure the MCP server is running correctly!")


if __name__ == "__main__":
    asyncio.run(main())
