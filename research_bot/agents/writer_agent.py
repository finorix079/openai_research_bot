from pydantic import BaseModel

from agents import Agent

from . import STRONG_MODEL


PROMPT = (
    "You are a senior researcher tasked with writing a cohesive report for a research query. "
    "You will be provided with the original query, and some initial research done by a research "
    "assistant.\n"
    "You should first come up with an outline for the report that describes the structure and "
    "flow of the report. Then, generate the report and return that as your final output.\n"
    "The final output should be in markdown format, and it should be lengthy and detailed. Aim "
    "for 5-10 pages of content, at least 1000 words."
)


class ReportData(BaseModel):
    short_summary: str
    markdown_report: str
    follow_up_questions: list[str]


writer_agent = Agent(
    name="WriterAgent",
    instructions=PROMPT,
    model=STRONG_MODEL,
    output_type=ReportData,
)
