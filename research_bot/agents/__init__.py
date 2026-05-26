import os


def get_model(openai_model: str) -> str:
    """Return the model name based on AI_PROVIDER env var.

    When AI_PROVIDER=claude, maps OpenAI model names to Anthropic equivalents
    via the litellm prefix. Otherwise returns the OpenAI model name as-is.
    """
    provider = os.environ.get("AI_PROVIDER", "openai").lower()
    if provider == "claude":
        # Map CLAUDE_API_KEY to ANTHROPIC_API_KEY for litellm
        claude_key = os.environ.get("CLAUDE_API_KEY")
        if claude_key and not os.environ.get("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = claude_key

        model_map = {
            "gpt-5.5": "litellm/anthropic/claude-sonnet-4-20250514",
            "gpt-5-mini": "litellm/anthropic/claude-haiku-4-5-20251001",
        }
        return model_map.get(openai_model, "litellm/anthropic/claude-sonnet-4-20250514")
    return openai_model