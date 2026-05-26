"""Rerunnable tool implementations for the research bot."""
import os

import anthropic
from agents import function_tool
from elasticdash_test import ed_tool


async def _anthropic_web_search(query: str) -> str:
    """Call Anthropic's Messages API with the built-in web_search tool."""
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": query}],
    )

    # Extract text from the response content blocks
    parts = []
    for block in response.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts) if parts else ""


@ed_tool(name="web_search_tool")
async def web_search_rerun(query: str) -> str:
    """Search the web using Anthropic's built-in web_search tool.

    This is the local re-implementation of the hosted WebSearchTool,
    allowing reruns to validate behavior with the same input.
    """
    return await _anthropic_web_search(query)


@function_tool
async def web_search_tool(query: str) -> str:
    """Search the web for information about a topic. Use this to find
    up-to-date information, facts, and details relevant to the research query.

    Args:
        query: The search query to execute
    """
    return await web_search_rerun(query)
