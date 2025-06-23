"""Integration tests for the main MCP server."""

import pytest


async def test_server_has_all_tools(client):
    """Test that the server has imported all expected tools from sub-servers."""
    # Get list of available tools
    tools = await client.list_tools()
    tool_names = {tool.name for tool in tools}
    
    # Check Scryfall tools are available with correct prefix
    assert "scryfall_lookup_cards" in tool_names
    assert "scryfall_search_cards_by_criteria" in tool_names
    
    # Check analysis tools are available with correct prefix
    assert "analysis_calculate_mana_curve" in tool_names
    assert "analysis_analyze_lands" in tool_names
    assert "analysis_analyze_color_identity" in tool_names
    assert "analysis_analyze_mana_requirements" in tool_names
    assert "analysis_analyze_card_types" in tool_names


async def test_tool_descriptions_exist(client):
    """Test that all tools have proper descriptions."""
    tools = await client.list_tools()
    
    for tool in tools:
        assert tool.description is not None
        assert len(tool.description.strip()) > 0, f"Tool {tool.name} has empty description"


async def test_server_composition_works(client):
    """Test that server composition with sub-servers works correctly."""
    # This is a smoke test to ensure the server initializes properly
    # and we can make basic tool calls
    
    result = await client.call_tool(
        "scryfall_lookup_cards",
        {"card_names": []}
    )
    
    # Should get the "no cards provided" response
    assert result[0].text == "No card names provided."


async def test_server_name_and_info(client):
    """Test server information is correct."""
    # The server should have the correct name as specified in server.py
    # This test verifies that the server composition maintained the correct metadata
    
    # We can't directly test server name through client, but we can verify
    # the server responds correctly to tool calls, indicating proper setup
    tools = await client.list_tools()
    assert len(tools) == 7  # 2 scryfall + 5 analysis tools