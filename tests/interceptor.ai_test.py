"""Tests for install_ai_interceptor / uninstall_ai_interceptor with real API calls."""

from dotenv import load_dotenv
load_dotenv()

import os
import httpx

from elasticdash_test import (
    ai_test,
    install_ai_interceptor,
    uninstall_ai_interceptor,
    TraceHandle,
    set_current_trace,
    get_current_trace,
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def _make_cheap_openai_call():
    """Make a minimal OpenAI API call (gpt-4o-mini, max_tokens=5)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Say hi"}],
                "max_tokens": 5,
            },
        )
        resp.raise_for_status()
        return resp.json()


@ai_test("interceptor captures OpenAI calls")
async def test_interceptor_captures_openai_calls(ctx):
    install_ai_interceptor()
    try:
        await _make_cheap_openai_call()
        steps = ctx.trace.get_llm_steps()
        assert len(steps) >= 1, f"Expected at least 1 LLM step, got {len(steps)}"
        assert steps[0].provider == "openai"
    finally:
        uninstall_ai_interceptor()


@ai_test("interceptor captures model name")
async def test_interceptor_captures_model_name(ctx):
    install_ai_interceptor()
    try:
        await _make_cheap_openai_call()
        steps = ctx.trace.get_llm_steps()
        assert len(steps) >= 1
        assert steps[0].model == "gpt-4o-mini", f"Expected 'gpt-4o-mini', got {steps[0].model!r}"
    finally:
        uninstall_ai_interceptor()


@ai_test("interceptor captures prompt content")
async def test_interceptor_captures_prompt(ctx):
    install_ai_interceptor()
    try:
        await _make_cheap_openai_call()
        steps = ctx.trace.get_llm_steps()
        assert len(steps) >= 1
        assert steps[0].prompt is not None
        assert "Say hi" in steps[0].prompt, f"Expected prompt to contain 'Say hi', got {steps[0].prompt!r}"
    finally:
        uninstall_ai_interceptor()


@ai_test("interceptor does not crash when no trace is set")
async def test_interceptor_no_trace_no_crash(ctx):
    install_ai_interceptor()
    saved_trace = get_current_trace()
    try:
        set_current_trace(None)
        # Should not crash even without a current trace
        await _make_cheap_openai_call()
    finally:
        set_current_trace(saved_trace)
        uninstall_ai_interceptor()


@ai_test("uninstall stops capturing")
async def test_uninstall_stops_capture(ctx):
    install_ai_interceptor()
    uninstall_ai_interceptor()
    await _make_cheap_openai_call()
    steps = ctx.trace.get_llm_steps()
    assert len(steps) == 0, f"Expected 0 LLM steps after uninstall, got {len(steps)}"


@ai_test("double install is idempotent")
async def test_double_install_idempotent(ctx):
    install_ai_interceptor()
    install_ai_interceptor()  # Second install should not cause issues
    try:
        await _make_cheap_openai_call()
        steps = ctx.trace.get_llm_steps()
        # Should capture exactly 1 step, not 2
        assert len(steps) == 1, f"Expected exactly 1 LLM step, got {len(steps)}"
    finally:
        uninstall_ai_interceptor()
