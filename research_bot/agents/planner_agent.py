from pydantic import BaseModel

from agents import Agent

from . import STRONG_MODEL


PROMPT = (
    "You are a helpful research assistant. Given a query, come up with a set of web "
    "searches to perform to best answer the query. Output between 5 and 20 terms to query for."
)


class WebSearchItem(BaseModel):
    reason: str
    query: str


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem]


planner_agent = Agent(
    name="PlannerAgent",
    instructions=PROMPT,
    model=STRONG_MODEL,
    output_type=WebSearchPlan,
)
