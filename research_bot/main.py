import asyncio

from dotenv import load_dotenv
load_dotenv()


def input_with_fallback(prompt: str, fallback: str) -> str:
    result = input(prompt)
    return result if result.strip() else fallback


from .manager import ResearchManager


async def main() -> None:
    query = input_with_fallback(
        "What would you like to research? ",
        "Impact of electric vehicles on the grid.",
    )
    manager = ResearchManager()
    report = await manager.run(query)

    while report and report.follow_up_questions:
        print("\n=====FOLLOW UP QUESTIONS=====\n")
        for i, q in enumerate(report.follow_up_questions, 1):
            print(f"  {i}. {q}")
        print()
        answer = input("Enter follow-up answer (or press Enter to quit): ").strip()
        if not answer:
            break
        # Combine original context with follow-up for a deeper research pass
        follow_up_query = f"{query}\n\nAdditional context from user: {answer}"
        report = await manager.run(follow_up_query)


if __name__ == "__main__":
    asyncio.run(main())
