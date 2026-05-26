"""Tests for async matchers: to_match_semantic_output and to_evaluate_output_metric."""

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


@before_all
def setup():
    install_ai_interceptor()


@after_all
def teardown():
    uninstall_ai_interceptor()


# ========== to_match_semantic_output ==========


@ai_test("semantic output match - passing case")
async def test_semantic_output_match_passes(ctx):
    ctx.trace.record_llm_step(
        model="gpt-4o",
        completion="Python is a popular programming language used for web development, data science, and AI.",
    )
    await expect(ctx.trace).to_match_semantic_output(
        expected="Python is widely used in software development and machine learning",
    )


@ai_test("semantic output match - failing case")
async def test_semantic_output_match_fails(ctx):
    ctx.trace.record_llm_step(
        model="gpt-4o",
        completion="The weather is sunny today with clear skies.",
    )
    try:
        await expect(ctx.trace).to_match_semantic_output(
            expected="Quantum physics explains particle behavior at subatomic scales",
        )
        assert False, "Should have raised AssertionError"
    except AssertionError as e:
        assert "score too low" in str(e).lower() or "semantic" in str(e).lower()


@ai_test("semantic output match - custom model param")
async def test_semantic_output_custom_model(ctx):
    ctx.trace.record_llm_step(
        model="gpt-4o",
        completion="Machine learning models learn patterns from data to make predictions.",
    )
    await expect(ctx.trace).to_match_semantic_output(
        expected="ML uses data patterns for prediction",
        model="gpt-4o-mini",
    )


# ========== to_evaluate_output_metric ==========


@ai_test("evaluate output metric - passing case")
async def test_evaluate_output_metric_passes(ctx):
    ctx.trace.record_llm_step(
        model="gpt-4o",
        completion="Python is the most popular programming language in 2025, widely used in AI, web development, and data science.",
    )
    score = await expect(ctx.trace).to_evaluate_output_metric(
        evaluation_prompt="Rate how well this output describes Python's popularity and use cases",
        condition={"at_least": 0.5},
    )
    assert isinstance(score, float)
    assert 0 <= score <= 1


@ai_test("evaluate output metric - with nth param")
async def test_evaluate_output_metric_with_nth(ctx):
    ctx.trace.record_llm_step(model="m", completion="First: Python is great for AI.")
    ctx.trace.record_llm_step(model="m", completion="Second: JavaScript is for web.")
    score = await expect(ctx.trace).to_evaluate_output_metric(
        evaluation_prompt="Rate if this mentions Python and AI",
        nth=0,
        condition={"at_least": 0.5},
    )
    assert isinstance(score, float)


@ai_test("evaluate output metric - with index param")
async def test_evaluate_output_metric_with_index(ctx):
    ctx.trace.record_llm_step(model="m", completion="First step output")
    ctx.trace.record_llm_step(model="m", completion="JavaScript powers modern web applications and frameworks.")
    score = await expect(ctx.trace).to_evaluate_output_metric(
        evaluation_prompt="Rate if this discusses JavaScript and web development",
        index=1,
        condition={"at_least": 0.5},
    )
    assert isinstance(score, float)


@ai_test("evaluate output metric - at_most condition passes")
async def test_evaluate_output_metric_condition_at_most(ctx):
    ctx.trace.record_llm_step(model="m", completion="Some text about programming.")
    score = await expect(ctx.trace).to_evaluate_output_metric(
        evaluation_prompt="Rate the quality of this text",
        condition={"at_most": 1.0},
    )
    assert score <= 1.0


@ai_test("evaluate output metric - failing condition raises")
async def test_evaluate_output_metric_condition_fails(ctx):
    ctx.trace.record_llm_step(
        model="m",
        completion="xyzzy gibberish not relevant at all",
    )
    try:
        await expect(ctx.trace).to_evaluate_output_metric(
            evaluation_prompt="Rate how well this explains quantum computing in detail",
            condition={"at_least": 0.99},
        )
        assert False, "Should have raised AssertionError"
    except AssertionError as e:
        assert "below threshold" in str(e).lower() or "score" in str(e).lower()
