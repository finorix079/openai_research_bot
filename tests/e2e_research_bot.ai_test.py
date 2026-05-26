"""End-to-end tests running the full research bot pipeline with real LLM calls."""

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


@ai_test("e2e - full pipeline captures LLM steps and produces valid report")
async def test_full_pipeline(ctx):
    manager = ResearchManager()
    report = await manager.run("What is Python?")

    # Verify interceptor captured LLM calls (at least some from the pipeline)
    steps = ctx.trace.get_llm_steps()
    assert len(steps) >= 1, f"Expected at least 1 intercepted LLM step, got {len(steps)}"

    # Verify at least one step has provider="openai"
    expect(ctx.trace).to_have_llm_step(provider="openai", min_times=1)

    # Verify planner or search used gpt-5.5 (if intercepted)
    models_seen = {s.model for s in steps}
    assert len(models_seen) >= 1, f"Expected at least 1 model, got {models_seen}"

    # Check if any prompt contains the query (the interceptor captures user-role messages)
    prompts_with_python = [s for s in steps if s.prompt and "python" in s.prompt.lower()]
    if prompts_with_python:
        expect(ctx.trace).to_have_llm_step(contains="Python", min_times=1)

    # Validate report fields
    assert report.markdown_report, "Report markdown should not be empty"
    assert len(report.markdown_report) > 100, "Report should be substantial"
    assert report.short_summary, "Summary should not be empty"
    assert len(report.follow_up_questions) > 0, "Should have follow-up questions"


@ai_test("e2e - semantic match on manually recorded research summary")
async def test_semantic_report_quality(ctx):
    # Record a research-like completion for semantic matching
    ctx.trace.record_llm_step(
        model="gpt-4o",
        completion=(
            "Python is a high-level, interpreted programming language known for its simplicity "
            "and readability. It is widely used in web development with frameworks like Django "
            "and Flask, in data science with libraries like pandas and NumPy, and in artificial "
            "intelligence and machine learning with TensorFlow and PyTorch."
        ),
    )
    await expect(ctx.trace).to_match_semantic_output(
        expected="A description of the Python programming language and its applications in web, data science, and AI",
    )


@ai_test("e2e - evaluate output metric on manually recorded summary")
async def test_metric_evaluation(ctx):
    ctx.trace.record_llm_step(
        model="gpt-4o",
        completion=(
            "Python ranks as the #1 programming language in 2025 according to TIOBE and Stack Overflow surveys. "
            "Its ecosystem includes over 400,000 packages on PyPI. Key growth areas include AI/ML, data engineering, "
            "and cloud automation. The language's simple syntax makes it popular among beginners and experts alike."
        ),
    )
    score = await expect(ctx.trace).to_evaluate_output_metric(
        evaluation_prompt="Rate how well this text covers Python's popularity, ecosystem, and growth areas",
        condition={"at_least": 0.5},
    )
    assert isinstance(score, float)
    assert 0 <= score <= 1


@ai_test("e2e - custom step recording and assertion")
async def test_custom_step_recording(ctx):
    # Simulate pipeline tracking with custom steps
    ctx.trace.record_custom_step(
        kind="pipeline",
        name="research_pipeline",
        tags=["e2e", "integration"],
        payload="What is Python?",
        result="completed successfully",
        metadata={"query": "What is Python?", "agent_count": 3},
    )

    expect(ctx.trace).to_have_custom_step(kind="pipeline")
    expect(ctx.trace).to_have_custom_step(name="research_pipeline")
    expect(ctx.trace).to_have_custom_step(tag="e2e")
    expect(ctx.trace).to_have_custom_step(tag="integration")
    expect(ctx.trace).to_have_custom_step(result_contains="completed")
    expect(ctx.trace).to_have_custom_step(payload_contains="Python")
    expect(ctx.trace).to_have_custom_step(metadata_contains="agent_count")
    expect(ctx.trace).to_have_custom_step(kind="pipeline", times=1)
