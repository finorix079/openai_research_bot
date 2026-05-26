from typing import Literal

from pydantic import BaseModel

from agents import Agent

from . import get_model

Source = Literal["web", "news", "arxiv", "knowledge_base"]

PROMPT = """\
You are a senior research planner. Given a query, produce a focused plan of
5-12 searches that, together, would answer it well.

Each search needs a `source`. The available sources are: "web", "news",
"arxiv", "knowledge_base". Pick whichever is most appropriate — "web" is
the safe default when you're unsure.

Rules:
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
