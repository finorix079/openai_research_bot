import os

if os.environ.get("CLAUDE_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = os.environ["CLAUDE_API_KEY"]

STRONG_MODEL = "litellm/anthropic/claude-sonnet-4-20250514"
FAST_MODEL = "litellm/anthropic/claude-haiku-4-5-20251001"
