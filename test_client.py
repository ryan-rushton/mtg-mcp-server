"""
Simple interactive demo client for the MTG MCP Server.

This is a minimal demonstration of the server functionality.
For comprehensive testing, use the pytest suite in the tests/ directory.
For integration tests with real network requests, run: uv run pytest tests/test_integration.py
"""

import asyncio
from fastmcp import Client

client: Client = Client("server.py")


async def demo_basic_functionality():
    """Demo basic server functionality with a few example cards."""
    print("=== MTG MCP Server Demo ===")
    print("Note: This demo uses cached data. For full integration tests with")
    print("real network requests, run: uv run pytest tests/test_integration.py")

    async with client:
        # Demo card lookup
        print("\n1. Looking up some popular Magic cards...")
        result = await client.call_tool(
            "scryfall_lookup_cards",
            {"card_names": ["Lightning Bolt", "Sol Ring", "Command Tower"]},
        )
        if result and hasattr(result[0], "text"):
            print(
                result[0].text[:500] + "..."
                if len(result[0].text) > 500
                else result[0].text
            )

        # Demo mana curve analysis
        print("\n2. Analyzing mana curve...")
        result = await client.call_tool(
            "analysis_calculate_mana_curve",
            {
                "card_names": [
                    "Lightning Bolt",
                    "Counterspell",
                    "Wrath of God",
                    "Sol Ring",
                ]
            },
        )
        if result and hasattr(result[0], "text"):
            print(result[0].text)

        # Demo commander analysis with quantities
        print("\n3. Analyzing a sample Commander deck with quantities...")
        result = await client.call_tool(
            "analysis_analyze_commander_deck",
            {
                "commander": "Atraxa, Praetors' Voice",
                "decklist": [
                    "4 Forest", "3 Island", "2x Sol Ring", 
                    "Lightning Bolt", "Forest",  # This should combine to 5 Forest total
                    "Command Tower", "Cultivate"
                ]
            },
        )
        if result and hasattr(result[0], "text"):
            import json
            try:
                analysis = json.loads(result[0].text)
                print(f"Commander: {analysis['commander']['name']}")
                print(f"Total deck cards: {analysis['deck']['deck_cards']}")
                print(f"Unique cards: {analysis['deck']['unique_cards']}")
                print("Cards with quantities:")
                for card in analysis['cards'][:5]:  # Show first 5
                    print(f"  {card['quantity']}x {card['name']}")
            except json.JSONDecodeError:
                print(result[0].text[:400] + "...")

        # Demo search functionality
        print("\n4. Searching for dragons...")
        result = await client.call_tool(
            "scryfall_search_cards_by_criteria", {"name": "dragon", "limit": 3}
        )
        if result and hasattr(result[0], "text"):
            print(
                result[0].text[:400] + "..."
                if len(result[0].text) > 400
                else result[0].text
            )


async def interactive_mode():
    """Simple interactive mode for manual testing."""
    print("\n=== Interactive Mode ===")
    print("Enter card names separated by commas (or 'quit' to exit):")

    async with client:
        while True:
            user_input = input("\nCard names: ").strip()

            if user_input.lower() in ["quit", "exit", "q"]:
                break

            if not user_input:
                print("Please enter some card names!")
                continue

            card_names = [name.strip() for name in user_input.split(",")]

            try:
                result = await client.call_tool(
                    "scryfall_lookup_cards", {"card_names": card_names}
                )
                if result and hasattr(result[0], "text"):
                    print("\n" + result[0].text)
                else:
                    print("\n" + str(result[0]))
            except Exception as e:
                print(f"Error: {e}")


async def main():
    """Run the demo and optionally interactive mode."""
    try:
        await demo_basic_functionality()

        run_interactive = (
            input("\nWould you like to try interactive mode? (y/n): ").strip().lower()
        )
        if run_interactive in ["y", "yes"]:
            await interactive_mode()

        print("\nDemo complete!")
        print("For unit tests, run: uv run pytest")
        print("For integration tests with real network requests, run: uv run pytest tests/test_integration.py")

    except Exception as e:
        print(f"Error running demo: {e}")
        print("Make sure the server is properly configured!")


if __name__ == "__main__":
    asyncio.run(main())
