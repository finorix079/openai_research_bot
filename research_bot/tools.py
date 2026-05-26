"""Rerunnable tool implementations for the research bot.

Each tool is exposed twice:
- ``@ed_tool`` registers the function with ElasticDash for trace recording
  and step-level reruns.
- ``@function_tool`` registers the same function with the OpenAI Agents SDK
  so an agent can call it. The ``@function_tool`` body delegates to the
  ``@ed_tool``-wrapped function so every invocation lands in the trace.
"""
from __future__ import annotations

import asyncio
import os
import re
import urllib.parse
from typing import Any

import anthropic
import httpx
from agents import function_tool
from elasticdash_test import ed_tool

from .kb import KB_DOCS


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _anthropic_client() -> anthropic.AsyncAnthropic:
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    return anthropic.AsyncAnthropic(api_key=api_key)


async def _anthropic_web_search(query: str) -> str:
    """Call Anthropic's Messages API with the built-in web_search tool."""
    client = _anthropic_client()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": query}],
    )
    parts = [b.text for b in response.content if b.type == "text"]
    return "\n".join(parts) if parts else ""


def _strip_html(html: str) -> str:
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"\s+", " ", html)
    return html.strip()


# ---------------------------------------------------------------------------
# 1. Web search (the original tool)
# ---------------------------------------------------------------------------

@ed_tool(name="web_search_tool")
async def web_search_rerun(query: str) -> str:
    """Search the web using Anthropic's built-in web_search tool."""
    return await _anthropic_web_search(query)


@function_tool
async def web_search_tool(query: str) -> str:
    """Search the open web for information about a topic. Returns short
    snippets and source URLs. Use this for general-purpose research.

    Args:
        query: The search query to execute.
    """
    return await web_search_rerun(query)


# ---------------------------------------------------------------------------
# 2. News search — same backend, biased toward recency
# ---------------------------------------------------------------------------

@ed_tool(name="news_search_tool")
async def news_search_rerun(query: str) -> str:
    """Search for recent news articles via Anthropic web search."""
    framed = (
        "Find recent news articles (last 60 days) about: "
        f"{query}. Prioritize reputable outlets. Include publication dates "
        "and outlet names where possible."
    )
    return await _anthropic_web_search(framed)


@function_tool
async def news_search_tool(query: str) -> str:
    """Search recent news for a topic. Prefer this over web_search when the
    user asks about current events, announcements, or anything time-sensitive.

    Args:
        query: The news topic to search for.
    """
    return await news_search_rerun(query)


# ---------------------------------------------------------------------------
# 3. arXiv search — academic papers
# ---------------------------------------------------------------------------

ARXIV_ENDPOINT = "https://export.arxiv.org/api/query"


@ed_tool(name="arxiv_search_tool")
async def arxiv_search_rerun(query: str, max_results: int = 5) -> str:
    """Search arxiv.org for academic papers matching the query."""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_ENDPOINT}?{urllib.parse.urlencode(params)}"

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "ResearchBot/1.0"})
            resp.raise_for_status()
            body = resp.text
    except httpx.HTTPError as exc:
        return f"arXiv request failed: {exc}"

    entries = re.findall(r"<entry>(.*?)</entry>", body, flags=re.S)
    if not entries:
        return "No arXiv papers found."

    out: list[str] = []
    for entry in entries[:max_results]:
        title_m = re.search(r"<title>(.*?)</title>", entry, flags=re.S)
        summary_m = re.search(r"<summary>(.*?)</summary>", entry, flags=re.S)
        link_m = re.search(r"<id>(.*?)</id>", entry, flags=re.S)
        published_m = re.search(r"<published>(.*?)</published>", entry, flags=re.S)
        authors = re.findall(r"<name>(.*?)</name>", entry, flags=re.S)

        title = title_m.group(1).strip().replace("\n", " ") if title_m else "(no title)"
        summary = summary_m.group(1).strip().replace("\n", " ") if summary_m else ""
        link = link_m.group(1).strip() if link_m else ""
        published = published_m.group(1).strip()[:10] if published_m else ""
        author_str = ", ".join(a.strip() for a in authors[:3]) or "(unknown)"

        out.append(
            f"- {title} ({published})\n"
            f"  Authors: {author_str}\n"
            f"  Link: {link}\n"
            f"  Abstract: {summary[:500]}"
        )

    return "\n\n".join(out)


@function_tool
async def arxiv_search_tool(query: str, max_results: int = 5) -> str:
    """Search arXiv for academic papers. Prefer this over web_search when
    the topic is technical/scientific and primary research matters.

    Args:
        query: The topic to search arXiv for.
        max_results: Number of papers to return (default 5, max 10).
    """
    capped = max(1, min(max_results, 10))
    return await arxiv_search_rerun(query, capped)


# ---------------------------------------------------------------------------
# 4. Internal knowledge base search
# ---------------------------------------------------------------------------

@ed_tool(name="knowledge_base_search_tool")
async def knowledge_base_search_rerun(query: str, top_k: int = 3) -> str:
    """Search the internal knowledge base for relevant documents."""
    tokens = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2}
    scored: list[tuple[int, dict[str, str]]] = []
    for doc in KB_DOCS:
        haystack = f"{doc['title']} {doc['content']}".lower()
        score = sum(1 for t in tokens if t in haystack)
        if score:
            scored.append((score, doc))

    scored.sort(key=lambda x: -x[0])
    top = scored[:top_k]
    if not top:
        return "No internal documents found for this query."

    return "\n\n".join(
        f"[{doc['id']}] {doc['title']}\n{doc['content']}" for _, doc in top
    )


@function_tool
async def knowledge_base_search_tool(query: str, top_k: int = 3) -> str:
    """Search the internal knowledge base (private corpus). Use this for
    anything the user is likely asking about internally — adoption numbers,
    company practices, prior research — before falling back to the web.

    Args:
        query: The search query.
        top_k: Number of documents to return (default 3, max 5).
    """
    capped = max(1, min(top_k, 5))
    return await knowledge_base_search_rerun(query, capped)


# ---------------------------------------------------------------------------
# 5. fetch_url — pull and clean a single URL
# ---------------------------------------------------------------------------

MAX_FETCH_BYTES = 200_000
MAX_RETURN_CHARS = 8_000


@ed_tool(name="fetch_url_tool")
async def fetch_url_rerun(url: str) -> str:
    """Fetch a URL and return cleaned plain-text content (truncated)."""
    if not re.match(r"^https?://", url):
        return f"Refusing to fetch: URL must start with http:// or https:// (got {url!r})."

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                headers={"User-Agent": "ResearchBot/1.0 (+https://example.com)"},
            )
            resp.raise_for_status()
            body = resp.text[:MAX_FETCH_BYTES * 4]  # chars not bytes; rough bound
    except httpx.HTTPError as exc:
        return f"Failed to fetch {url}: {exc}"

    cleaned = _strip_html(body)
    truncated = cleaned[:MAX_RETURN_CHARS]
    suffix = "" if len(cleaned) <= MAX_RETURN_CHARS else f"\n\n[truncated, {len(cleaned)} chars total]"
    return truncated + suffix


@function_tool
async def fetch_url_tool(url: str) -> str:
    """Fetch a single URL and return its cleaned text. Use this after a
    search tool surfaces a promising link you want to read in full.

    Args:
        url: The full http(s) URL to fetch.
    """
    return await fetch_url_rerun(url)


# ---------------------------------------------------------------------------
# 6. extract_key_facts — distill long text into bullets
# ---------------------------------------------------------------------------

@ed_tool(name="extract_key_facts_tool")
async def extract_key_facts_rerun(text: str, focus: str = "") -> str:
    """Extract a numbered list of factual claims from a body of text."""
    if not text.strip():
        return "No text supplied."

    instructions = (
        "Extract the most important factual claims from the text below as a "
        "numbered list. Each item should be one sentence, concrete and "
        "verifiable. Skip opinions and marketing fluff. Aim for 5-10 items."
    )
    if focus:
        instructions += f"\n\nFocus on facts relevant to: {focus}."

    prompt = f"{instructions}\n\n---\nText:\n{text[:12_000]}"

    client = _anthropic_client()
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    parts = [b.text for b in response.content if b.type == "text"]
    return "\n".join(parts).strip() or "(no facts extracted)"


@function_tool
async def extract_key_facts_tool(text: str, focus: str = "") -> str:
    """Distill a long body of text into a numbered list of factual claims.
    Use this after fetch_url, or on a long search result, before
    summarizing.

    Args:
        text: The text to extract facts from.
        focus: Optional aspect to bias extraction toward.
    """
    return await extract_key_facts_rerun(text, focus)


# ---------------------------------------------------------------------------
# 7. save_finding — scratchpad shared across the run
# ---------------------------------------------------------------------------

_FINDINGS: list[str] = []
_FINDINGS_LOCK = asyncio.Lock()


async def _append_finding(entry: str) -> int:
    async with _FINDINGS_LOCK:
        _FINDINGS.append(entry)
        return len(_FINDINGS)


def get_findings() -> list[str]:
    return list(_FINDINGS)


def reset_findings() -> None:
    _FINDINGS.clear()


@ed_tool(name="save_finding_tool")
async def save_finding_rerun(finding: str, source: str = "") -> str:
    """Persist an important finding to the shared research scratchpad."""
    finding = finding.strip()
    if not finding:
        return "No finding provided."
    entry = f"- {finding}" + (f" (source: {source})" if source.strip() else "")
    total = await _append_finding(entry)
    return f"Saved finding #{total}."


@function_tool
async def save_finding_tool(finding: str, source: str = "") -> str:
    """Record a single important finding to the run's shared scratchpad.
    Use this for facts the final report should anchor on (1-3 per search).
    Always pass a short source label (URL, paper id, KB id, or outlet).

    Args:
        finding: One-sentence factual finding to record.
        source: Where it came from (URL, kb-id, paper id, outlet name).
    """
    return await save_finding_rerun(finding, source)


__all__ = [
    "web_search_tool",
    "web_search_rerun",
    "news_search_tool",
    "news_search_rerun",
    "arxiv_search_tool",
    "arxiv_search_rerun",
    "knowledge_base_search_tool",
    "knowledge_base_search_rerun",
    "fetch_url_tool",
    "fetch_url_rerun",
    "extract_key_facts_tool",
    "extract_key_facts_rerun",
    "save_finding_tool",
    "save_finding_rerun",
    "get_findings",
    "reset_findings",
]
