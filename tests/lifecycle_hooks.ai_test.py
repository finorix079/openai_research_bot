"""Tests for lifecycle hooks: before_all, after_all, before_each, after_each."""

from elasticdash_test import (
    ai_test,
    before_all,
    after_all,
    before_each,
    after_each,
    expect,
    install_ai_interceptor,
    uninstall_ai_interceptor,
)

# Module-level execution log to track hook ordering
_execution_log = []


@before_all
def setup_suite():
    _execution_log.append("before_all")
    install_ai_interceptor()


@after_all
def teardown_suite():
    _execution_log.append("after_all")
    uninstall_ai_interceptor()


@before_each
def before_test(ctx):
    _execution_log.append("before_each")
    # Prove before_each has access to ctx.trace by recording a marker
    ctx.trace.record_custom_step(kind="hook", name="before_each_marker")


@after_each
def after_test(ctx):
    _execution_log.append("after_each")
    # Prove after_each has access to ctx.trace
    ctx.trace.record_custom_step(kind="hook", name="after_each_marker")


@ai_test("hooks - first test verifies before_all and before_each ran")
async def test_hooks_first(ctx):
    # At this point: before_all ran once, then before_each ran for this test
    assert _execution_log == ["before_all", "before_each"], (
        f"Expected ['before_all', 'before_each'], got {_execution_log}"
    )

    # Verify before_each recorded a custom step on this test's trace
    expect(ctx.trace).to_have_custom_step(kind="hook", name="before_each_marker")

    _execution_log.append("test_1")


@ai_test("hooks - second test verifies after_each ran between tests")
async def test_hooks_second(ctx):
    # Expected: before_all, before_each, test_1, after_each, before_each
    expected = ["before_all", "before_each", "test_1", "after_each", "before_each"]
    assert _execution_log == expected, (
        f"Expected {expected}, got {_execution_log}"
    )

    # This test's trace should have its OWN before_each_marker (not from first test)
    expect(ctx.trace).to_have_custom_step(kind="hook", name="before_each_marker")

    _execution_log.append("test_2")
