"""Tests for TraceHandle, dataclasses, AITestContext, and trace context vars."""

from elasticdash_test import (
    ai_test,
    before_all,
    after_all,
    install_ai_interceptor,
    uninstall_ai_interceptor,
    LLMStep,
    ToolCall,
    CustomStep,
    TraceHandle,
    AITestContext,
    set_current_trace,
    get_current_trace,
)


@before_all
def setup():
    install_ai_interceptor()


@after_all
def teardown():
    uninstall_ai_interceptor()


# --- Dataclass construction ---


@ai_test("LLMStep dataclass fields")
async def test_llm_step_dataclass(ctx):
    step = LLMStep(model="gpt-5.5", provider="openai", prompt="hello", completion="world", contains="x")
    assert step.model == "gpt-5.5"
    assert step.provider == "openai"
    assert step.prompt == "hello"
    assert step.completion == "world"
    assert step.contains == "x"


@ai_test("ToolCall dataclass fields")
async def test_tool_call_dataclass(ctx):
    call = ToolCall(name="web_search", args={"q": "test"}, result="ok")
    assert call.name == "web_search"
    assert call.args == {"q": "test"}
    assert call.result == "ok"


@ai_test("CustomStep dataclass fields")
async def test_custom_step_dataclass(ctx):
    step = CustomStep(
        kind="validation",
        name="check",
        tags=["a", "b"],
        payload={"key": "val"},
        result="pass",
        metadata={"m": 1},
    )
    assert step.kind == "validation"
    assert step.name == "check"
    assert step.tags == ["a", "b"]
    assert step.payload == {"key": "val"}
    assert step.result == "pass"
    assert step.metadata == {"m": 1}


# --- TraceHandle.record_llm_step ---


@ai_test("record_llm_step with LLMStep object")
async def test_record_llm_step_with_object(ctx):
    step = LLMStep(model="gpt-4o", provider="openai", prompt="hi", completion="bye")
    ctx.trace.record_llm_step(step=step)
    steps = ctx.trace.get_llm_steps()
    assert len(steps) == 1
    assert steps[0].model == "gpt-4o"
    assert steps[0].prompt == "hi"


@ai_test("record_llm_step with kwargs")
async def test_record_llm_step_with_kwargs(ctx):
    ctx.trace.record_llm_step(model="gpt-5.5", provider="openai", prompt="question", completion="answer")
    steps = ctx.trace.get_llm_steps()
    assert len(steps) == 1
    assert steps[0].model == "gpt-5.5"
    assert steps[0].completion == "answer"


# --- TraceHandle.record_tool_call ---


@ai_test("record_tool_call with ToolCall object")
async def test_record_tool_call_with_object(ctx):
    call = ToolCall(name="calculator", args={"expr": "2+2"}, result="4")
    ctx.trace.record_tool_call(call=call)
    calls = ctx.trace.get_tool_calls()
    assert len(calls) == 1
    assert calls[0].name == "calculator"
    assert calls[0].result == "4"


@ai_test("record_tool_call with kwargs")
async def test_record_tool_call_with_kwargs(ctx):
    ctx.trace.record_tool_call(name="web_search", args={"q": "python"}, result="results")
    calls = ctx.trace.get_tool_calls()
    assert len(calls) == 1
    assert calls[0].name == "web_search"


# --- TraceHandle.record_custom_step ---


@ai_test("record_custom_step with CustomStep object")
async def test_record_custom_step_with_object(ctx):
    step = CustomStep(kind="rag", name="retrieve", tags=["search"], payload="query", result="docs")
    ctx.trace.record_custom_step(step=step)
    steps = ctx.trace.get_custom_steps()
    assert len(steps) == 1
    assert steps[0].kind == "rag"
    assert steps[0].name == "retrieve"
    assert steps[0].tags == ["search"]


@ai_test("record_custom_step with kwargs")
async def test_record_custom_step_with_kwargs(ctx):
    ctx.trace.record_custom_step(kind="code", name="exec", tags=["fast"], payload="print('hi')", result="hi")
    steps = ctx.trace.get_custom_steps()
    assert len(steps) == 1
    assert steps[0].kind == "code"
    assert steps[0].result == "hi"


# --- TraceHandle.get_steps (combined) ---


@ai_test("get_steps returns all step types combined")
async def test_get_steps_combined(ctx):
    ctx.trace.record_llm_step(model="m1", prompt="p1")
    ctx.trace.record_llm_step(model="m2", prompt="p2")
    ctx.trace.record_tool_call(name="tool1")
    ctx.trace.record_custom_step(kind="custom1")
    all_steps = ctx.trace.get_steps()
    assert len(all_steps) == 4
    # First two are LLMSteps
    assert isinstance(all_steps[0], LLMStep)
    assert isinstance(all_steps[1], LLMStep)
    # Third is ToolCall
    assert isinstance(all_steps[2], ToolCall)
    # Fourth is CustomStep
    assert isinstance(all_steps[3], CustomStep)


# --- AITestContext ---


@ai_test("AITestContext has trace attribute")
async def test_ai_test_context_has_trace(ctx):
    assert isinstance(ctx, AITestContext)
    assert isinstance(ctx.trace, TraceHandle)


# --- set_current_trace / get_current_trace ---


@ai_test("set_current_trace and get_current_trace round-trip")
async def test_set_get_current_trace(ctx):
    # The runner already sets current trace to ctx.trace
    current = get_current_trace()
    assert current is ctx.trace

    # Set a custom trace
    custom_trace = TraceHandle()
    set_current_trace(custom_trace)
    assert get_current_trace() is custom_trace

    # Set None
    set_current_trace(None)
    assert get_current_trace() is None

    # Restore ctx.trace so after_each/cleanup works
    set_current_trace(ctx.trace)
