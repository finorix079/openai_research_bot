from __future__ import annotations

import os

import anthropic
from agents import function_tool
from elasticdash_sdk import ed_tool


def _anthropic_client() -> anthropic.AsyncAnthropic:
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    return anthropic.AsyncAnthropic(api_key=api_key)


@ed_tool(name="web_search_tool")
async def web_search_rerun(query: str) -> str:
    client = _anthropic_client()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": query}],
    )
    parts = [b.text for b in response.content if b.type == "text"]
    return "\n".join(parts) if parts else ""


@function_tool
async def web_search_tool(query: str) -> str:
    """Search the web for information about a topic.

    Args:
        query: The search query.
    """
    return await web_search_rerun(query)


__all__ = ["web_search_tool", "web_search_rerun"]
