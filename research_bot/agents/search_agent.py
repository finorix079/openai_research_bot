from agents import Agent

from . import FAST_MODEL
from ..tools import web_search_tool


INSTRUCTIONS = (
    "You are a research assistant. Given a search term, you search the web for that term and "
    "produce a single paragraph of under 60 words, keep only the core finding, write succinctly "
    "with no need for complete sentences or good grammar, and cut any fluff. The output is "
    "consumed by a downstream writer, so keep only the essential result. Do not include any "
    "commentary other than the summary itself."
)


search_agent = Agent(
    name="Search agent",
    instructions=INSTRUCTIONS,
    model=FAST_MODEL,
    tools=[web_search_tool],
)
