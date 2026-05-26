"""Tests for all synchronous matchers with every parameter combination."""

from elasticdash_test import (
    ai_test,
    before_all,
    after_all,
    expect,
    install_ai_interceptor,
    uninstall_ai_interceptor,
    TraceHandle,
)


@before_all
def setup():
    install_ai_interceptor()


@after_all
def teardown():
    uninstall_ai_interceptor()


# ========== to_have_llm_step ==========


@ai_test("to_have_llm_step - no args (at least one exists)")
async def test_to_have_llm_step_basic(ctx):
    ctx.trace.record_llm_step(model="gpt-4o", provider="openai", prompt="hi", completion="bye")
    expect(ctx.trace).to_have_llm_step()


@ai_test("to_have_llm_step - model filter")
async def test_to_have_llm_step_model(ctx):
    ctx.trace.record_llm_step(model="gpt-5.5", provider="openai")
    expect(ctx.trace).to_have_llm_step(model="gpt-5.5")


@ai_test("to_have_llm_step - provider filter")
async def test_to_have_llm_step_provider(ctx):
    ctx.trace.record_llm_step(model="gpt-4o", provider="openai")
    expect(ctx.trace).to_have_llm_step(provider="openai")


@ai_test("to_have_llm_step - contains (matches prompt or completion)")
async def test_to_have_llm_step_contains(ctx):
    ctx.trace.record_llm_step(model="m", prompt="hello world", completion="goodbye")
    expect(ctx.trace).to_have_llm_step(contains="hello")
    expect(ctx.trace).to_have_llm_step(contains="goodbye")


@ai_test("to_have_llm_step - prompt_contains")
async def test_to_have_llm_step_prompt_contains(ctx):
    ctx.trace.record_llm_step(model="m", prompt="search for python", completion="result")
    expect(ctx.trace).to_have_llm_step(prompt_contains="search")


@ai_test("to_have_llm_step - output_contains")
async def test_to_have_llm_step_output_contains(ctx):
    ctx.trace.record_llm_step(model="m", prompt="question", completion="the result is 42")
    expect(ctx.trace).to_have_llm_step(output_contains="result")


@ai_test("to_have_llm_step - times exact count")
async def test_to_have_llm_step_times(ctx):
    for _ in range(3):
        ctx.trace.record_llm_step(model="gpt-5.5", provider="openai")
    expect(ctx.trace).to_have_llm_step(model="gpt-5.5", times=3)


@ai_test("to_have_llm_step - min_times")
async def test_to_have_llm_step_min_times(ctx):
    for _ in range(3):
        ctx.trace.record_llm_step(model="m")
    expect(ctx.trace).to_have_llm_step(min_times=2)


@ai_test("to_have_llm_step - max_times")
async def test_to_have_llm_step_max_times(ctx):
    for _ in range(3):
        ctx.trace.record_llm_step(model="m")
    expect(ctx.trace).to_have_llm_step(max_times=5)


@ai_test("to_have_llm_step - negative case raises AssertionError")
async def test_to_have_llm_step_fails(ctx):
    ctx.trace.record_llm_step(model="gpt-4o")
    try:
        expect(ctx.trace).to_have_llm_step(model="nonexistent-model")
        assert False, "Should have raised AssertionError"
    except AssertionError:
        pass  # Expected


# ========== to_call_tool ==========


@ai_test("to_call_tool - name filter")
async def test_to_call_tool_basic(ctx):
    ctx.trace.record_tool_call(name="web_search", args={"q": "test"})
    expect(ctx.trace).to_call_tool("web_search")


@ai_test("to_call_tool - times exact count")
async def test_to_call_tool_times(ctx):
    ctx.trace.record_tool_call(name="web_search")
    ctx.trace.record_tool_call(name="web_search")
    expect(ctx.trace).to_call_tool("web_search", times=2)


@ai_test("to_call_tool - min_times and max_times")
async def test_to_call_tool_min_max(ctx):
    for _ in range(3):
        ctx.trace.record_tool_call(name="web_search")
    expect(ctx.trace).to_call_tool("web_search", min_times=1, max_times=5)


@ai_test("to_call_tool - negative case raises AssertionError")
async def test_to_call_tool_fails(ctx):
    # No tool calls recorded
    try:
        expect(ctx.trace).to_call_tool("nonexistent")
        assert False, "Should have raised AssertionError"
    except AssertionError:
        pass  # Expected


# ========== to_have_custom_step ==========


@ai_test("to_have_custom_step - kind filter")
async def test_to_have_custom_step_kind(ctx):
    ctx.trace.record_custom_step(kind="validation", name="check")
    expect(ctx.trace).to_have_custom_step(kind="validation")


@ai_test("to_have_custom_step - name filter")
async def test_to_have_custom_step_name(ctx):
    ctx.trace.record_custom_step(kind="rag", name="check-output")
    expect(ctx.trace).to_have_custom_step(name="check-output")


@ai_test("to_have_custom_step - tag filter")
async def test_to_have_custom_step_tag(ctx):
    ctx.trace.record_custom_step(kind="code", tags=["critical", "fast"])
    expect(ctx.trace).to_have_custom_step(tag="critical")


@ai_test("to_have_custom_step - contains (payload or result)")
async def test_to_have_custom_step_contains(ctx):
    ctx.trace.record_custom_step(kind="log", payload="important data", result="done")
    expect(ctx.trace).to_have_custom_step(contains="important")
    expect(ctx.trace).to_have_custom_step(contains="done")


@ai_test("to_have_custom_step - result_contains")
async def test_to_have_custom_step_result_contains(ctx):
    ctx.trace.record_custom_step(kind="check", result="test passed successfully")
    expect(ctx.trace).to_have_custom_step(result_contains="passed")


@ai_test("to_have_custom_step - payload_contains")
async def test_to_have_custom_step_payload_contains(ctx):
    ctx.trace.record_custom_step(kind="io", payload="input data here")
    expect(ctx.trace).to_have_custom_step(payload_contains="input")


@ai_test("to_have_custom_step - metadata_contains")
async def test_to_have_custom_step_metadata_contains(ctx):
    ctx.trace.record_custom_step(kind="meta", metadata={"version": "1.0", "env": "test"})
    expect(ctx.trace).to_have_custom_step(metadata_contains="version")


@ai_test("to_have_custom_step - times exact count")
async def test_to_have_custom_step_times(ctx):
    ctx.trace.record_custom_step(kind="log", name="entry1")
    ctx.trace.record_custom_step(kind="log", name="entry2")
    expect(ctx.trace).to_have_custom_step(kind="log", times=2)


# ========== to_have_prompt_where ==========


@ai_test("to_have_prompt_where - require_contains")
async def test_to_have_prompt_where_require_contains(ctx):
    ctx.trace.record_llm_step(model="m", prompt="search for python tutorials")
    expect(ctx.trace).to_have_prompt_where(require_contains="search")


@ai_test("to_have_prompt_where - require_not_contains")
async def test_to_have_prompt_where_require_not_contains(ctx):
    ctx.trace.record_llm_step(model="m", prompt="search for python tutorials")
    expect(ctx.trace).to_have_prompt_where(require_not_contains="secret")


@ai_test("to_have_prompt_where - filter_contains + require_contains")
async def test_to_have_prompt_where_filter_contains(ctx):
    ctx.trace.record_llm_step(model="m", prompt="plan the query for research")
    ctx.trace.record_llm_step(model="m", prompt="unrelated prompt")
    expect(ctx.trace).to_have_prompt_where(filter_contains="plan", require_contains="query")


@ai_test("to_have_prompt_where - index")
async def test_to_have_prompt_where_index(ctx):
    ctx.trace.record_llm_step(model="m", prompt="step A content")
    ctx.trace.record_llm_step(model="m", prompt="step B content")
    expect(ctx.trace).to_have_prompt_where(index=1, require_contains="step B")


@ai_test("to_have_prompt_where - nth (alias for index)")
async def test_to_have_prompt_where_nth(ctx):
    ctx.trace.record_llm_step(model="m", prompt="first step here")
    expect(ctx.trace).to_have_prompt_where(nth=0, require_contains="first")


@ai_test("to_have_prompt_where - times count")
async def test_to_have_prompt_where_times(ctx):
    for _ in range(3):
        ctx.trace.record_llm_step(model="m", prompt="common keyword in prompt")
    expect(ctx.trace).to_have_prompt_where(require_contains="common", times=3)


@ai_test("to_have_prompt_where - index out of range raises")
async def test_to_have_prompt_where_fails_index_out_of_range(ctx):
    ctx.trace.record_llm_step(model="m", prompt="only one")
    try:
        expect(ctx.trace).to_have_prompt_where(index=99, require_contains="x")
        assert False, "Should have raised AssertionError"
    except AssertionError as e:
        assert "out of range" in str(e)


# ========== expect() on non-TraceHandle ==========


@ai_test("expect on non-TraceHandle raises AssertionError")
async def test_expect_non_trace_raises(ctx):
    try:
        expect("not a trace").to_have_llm_step()
        assert False, "Should have raised AssertionError"
    except AssertionError as e:
        assert "TraceHandle" in str(e)
