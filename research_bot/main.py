import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from elasticdash_sdk.observability import (
    init_observability,
    ObservabilityOptions,
    start_trace,
    end_trace,
)

from .manager import ResearchManager


async def main() -> None:
    query = input("What would you like to research? ")

    handle = await init_observability(ObservabilityOptions(
        server_url=os.environ.get("ELASTICDASH_SERVER_URL"),
        api_key=os.environ.get("ELASTICDASH_API_KEY"),
    ))
    try:
        start_trace("research_workflow")
        await ResearchManager().run(query)
        end_trace()
    finally:
        await handle.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
