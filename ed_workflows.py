"""Workflow functions for ElasticDash ed-test runner."""
import os
from dotenv import load_dotenv
load_dotenv()

from elasticdash_test.observability import init_observability, shutdown_observability, ObservabilityOptions, start_trace, end_trace
from research_bot.manager import ResearchManager


async def research_workflow(input=None):
    """Run the research bot with a given query."""
    query = input or "What are the top 3 most popular programming languages in 2025?"

    # Init observability to push LLM call events to backend
    handle = await init_observability(ObservabilityOptions(
        server_url=os.environ.get("ELASTICDASH_SERVER_URL"),
        api_key=os.environ.get("ELASTICDASH_API_KEY"),
    ))

    try:
        start_trace("research_workflow")
        manager = ResearchManager()
        report = await manager.run(query)
        end_trace()
        return report.markdown_report
    finally:
        await handle.shutdown()
