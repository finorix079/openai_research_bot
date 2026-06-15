import os

from dotenv import load_dotenv
load_dotenv()

from elasticdash_sdk.observability import (
    init_observability,
    ObservabilityOptions,
    start_trace,
    end_trace,
)
from research_bot.manager import ResearchManager


async def research_workflow(input=None):
    query = input or "What are the top 3 most popular programming languages in 2025?"
    handle = await init_observability(ObservabilityOptions(
        server_url=os.environ.get("ELASTICDASH_SERVER_URL"),
        api_key=os.environ.get("ELASTICDASH_API_KEY"),
    ))
    try:
        start_trace("research_workflow")
        report = await ResearchManager().run(query)
        end_trace()
        return report.markdown_report
    finally:
        await handle.shutdown()
