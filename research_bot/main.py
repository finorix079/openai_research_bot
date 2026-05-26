import asyncio
import os

from dotenv import load_dotenv
load_dotenv()

from elasticdash_test.observability import init_observability, shutdown_observability, ObservabilityOptions, start_trace, end_trace


def input_with_fallback(prompt: str, fallback: str) -> str:
    result = input(prompt)
    return result if result.strip() else fallback


from .manager import ResearchManager


async def main() -> None:
    query = input_with_fallback(
        "What would you like to research? ",
        "Impact of electric vehicles on the grid.",
    )

    handle = await init_observability(ObservabilityOptions(
        server_url=os.environ.get("ELASTICDASH_SERVER_URL"),
        api_key=os.environ.get("ELASTICDASH_API_KEY"),
    ))

    try:
        start_trace("research_workflow")
        manager = ResearchManager()
        report = await manager.run(query)
        end_trace()

        while report and report.follow_up_questions:
            print("\n=====FOLLOW UP QUESTIONS=====\n")
            for i, q in enumerate(report.follow_up_questions, 1):
                print(f"  {i}. {q}")
            print()
            loop = asyncio.get_event_loop()
            answer = await loop.run_in_executor(
                None, lambda: input("Enter follow-up answer (or press Enter to quit): ").strip()
            )
            if not answer:
                break
            follow_up_query = f"{query}\n\nAdditional context from user: {answer}"
            start_trace("research_workflow")
            report = await manager.run(follow_up_query)
            end_trace()

    finally:
        await handle.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
