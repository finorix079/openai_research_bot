from dotenv import load_dotenv
load_dotenv()

from elasticdash_test import (
    ai_test,
    before_all,
    after_all,
    expect,
    install_ai_interceptor,
    uninstall_ai_interceptor,
)

from research_bot.manager import ResearchManager


@before_all
def setup():
    install_ai_interceptor()


@after_all
def teardown():
    uninstall_ai_interceptor()


@ai_test("research bot end-to-end")
async def test_research_flow(ctx):
    manager = ResearchManager()
    report = await manager.run("What are the top 3 most popular programming languages in 2025?")

    # Verify the planner agent made an LLM call
    expect(ctx.trace).to_have_llm_step(provider="openai")

    # Verify the writer produced a report with content
    assert report.markdown_report, "Report should not be empty"
    assert report.short_summary, "Summary should not be empty"
    assert len(report.follow_up_questions) > 0, "Should have follow-up questions"
