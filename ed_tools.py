"""Ed-tool definitions for the research bot.

Importing @ed_tool-decorated functions here makes them discoverable
by the ElasticDash CLI (e.g. ``elasticdash run-tool``).
"""
from research_bot.tools import (  # noqa: F401
    arxiv_search_rerun,
    extract_key_facts_rerun,
    fetch_url_rerun,
    knowledge_base_search_rerun,
    news_search_rerun,
    save_finding_rerun,
    web_search_rerun,
)
