from typing import Literal

from pydantic import BaseModel

from agents import Agent

from . import get_model

Source = Literal["web", "news", "arxiv", "knowledge_base"]

PROMPT = """\
You are a senior research planner. Given a query, produce a focused plan of
5-12 searches that, together, would answer it well.

For each search, choose the single best **source** based on what kind of
evidence is needed:

- "knowledge_base" — Internal/private corpus. Always include at least ONE
  knowledge_base search if the question could plausibly be answered by
  internal data (adoption stats, internal tooling, prior work). It's cheap
  and authoritative when relevant.
- "arxiv" — Academic papers. Use when primary research, methods,
  benchmarks, or scientific claims matter (e.g. ML, biology, physics).
- "news" — Recent events, announcements, releases, market moves. Use when
  the answer depends on what happened in the last few weeks/months.
- "web" — General open-web search. Default for everything else: market
  context, surveys, blog posts, documentation, vendor pages.

Rules:
- Diversify sources. Do not put every search on "web" — a plan that uses 2-3
  source types is almost always stronger.
- Each search should be specific enough to return useful results (avoid
  one-word queries).
- The "reason" field should explain what evidence the search is meant to
  surface, not just restate the query.
"""


class WebSearchItem(BaseModel):
    reason: str
    """Why this search is important to the overall query, and what evidence
    you expect it to surface."""

    query: str
    """The search term to use."""

    source: Source = "web"
    """Which channel to search. One of: web, news, arxiv, knowledge_base."""


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem]
    """A list of searches across diverse sources."""


planner_agent = Agent(
    name="PlannerAgent",
    instructions=PROMPT,
    model=get_model("gpt-5.5"),
    output_type=WebSearchPlan,
)
