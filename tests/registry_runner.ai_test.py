"""Tests for clear_registry, get_registry, run_file, run_files, TestResult, FileResult."""

import os

from elasticdash_test import (
    ai_test,
    before_all,
    after_all,
    install_ai_interceptor,
    uninstall_ai_interceptor,
    clear_registry,
    get_registry,
    TraceHandle,
)
from elasticdash_test.runner import run_file, run_files, TestResult, FileResult


@before_all
def setup():
    install_ai_interceptor()


@after_all
def teardown():
    uninstall_ai_interceptor()


# ========== get_registry ==========


@ai_test("get_registry returns dict containing current file")
async def test_get_registry_returns_current_file(ctx):
    registry = get_registry()
    assert isinstance(registry, dict), f"Expected dict, got {type(registry)}"
    # Find this file in the registry (keys are absolute paths)
    this_file = os.path.abspath(__file__)
    assert this_file in registry, f"Expected {this_file} in registry keys: {list(registry.keys())}"
    entry = registry[this_file]
    assert "tests" in entry
    assert "before_all_hooks" in entry
    assert "after_all_hooks" in entry
    assert "before_each_hooks" in entry
    assert "after_each_hooks" in entry


@ai_test("get_registry with file_path filters correctly")
async def test_get_registry_by_path(ctx):
    this_file = os.path.abspath(__file__)
    entry = get_registry(file_path=this_file)
    assert entry is not None, "Expected registry entry for current file"
    assert "tests" in entry


@ai_test("get_registry returns None for nonexistent path")
async def test_get_registry_nonexistent_path(ctx):
    result = get_registry(file_path="/nonexistent/path/test.py")
    assert result is None, f"Expected None for nonexistent path, got {result}"


# ========== clear_registry ==========


@ai_test("clear_registry with specific path only clears that path")
async def test_clear_registry_specific_path(ctx):
    this_file = os.path.abspath(__file__)
    dummy_path = "/tmp/dummy_test_file.py"

    # Ensure this file's entry exists before test
    assert get_registry(file_path=this_file) is not None

    # Clear a dummy path (may or may not exist)
    clear_registry(dummy_path)

    # This file's entry should still exist
    assert get_registry(file_path=this_file) is not None
    # The dummy path should be gone
    assert get_registry(file_path=dummy_path) is None


# ========== run_file ==========


@ai_test("run_file returns FileResult with passing test")
async def test_run_file_returns_file_result(ctx):
    helper_path = os.path.join(os.path.dirname(__file__), "helper_pass.ai_test.py")
    result = await run_file(helper_path)

    assert isinstance(result, FileResult), f"Expected FileResult, got {type(result)}"
    assert result.file == helper_path
    assert len(result.tests) == 1, f"Expected 1 test, got {len(result.tests)}"

    test_result = result.tests[0]
    assert isinstance(test_result, TestResult)
    assert test_result.name == "helper passes"
    assert test_result.status == "passed", f"Expected 'passed', got {test_result.status!r}"
    assert test_result.duration > 0, f"Expected positive duration, got {test_result.duration}"
    assert isinstance(test_result.trace, TraceHandle)
    assert test_result.error is None


@ai_test("run_file with failing test returns failed status")
async def test_run_file_with_failing_test(ctx):
    helper_path = os.path.join(os.path.dirname(__file__), "helper_fail.ai_test.py")
    result = await run_file(helper_path)

    assert isinstance(result, FileResult)
    assert len(result.tests) == 1

    test_result = result.tests[0]
    assert test_result.status == "failed", f"Expected 'failed', got {test_result.status!r}"
    assert test_result.error is not None
    assert "intentional failure" in str(test_result.error)


# ========== run_files ==========


@ai_test("run_files returns list of FileResults")
async def test_run_files_returns_list(ctx):
    helper_pass = os.path.join(os.path.dirname(__file__), "helper_pass.ai_test.py")
    helper_fail = os.path.join(os.path.dirname(__file__), "helper_fail.ai_test.py")
    results = await run_files([helper_pass, helper_fail])

    assert isinstance(results, list), f"Expected list, got {type(results)}"
    assert len(results) == 2, f"Expected 2 FileResults, got {len(results)}"
    assert all(isinstance(r, FileResult) for r in results)

    # First file should pass, second should fail
    assert results[0].tests[0].status == "passed"
    assert results[1].tests[0].status == "failed"
