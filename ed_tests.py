from elasticdash_sdk.ci.test_registry import define_test
from elasticdash_sdk.ci.types import TestBenchmarks

define_test({
    "name": "research bot e2e",
    "workflow": "research_workflow",
    "input": "What are the top 3 most popular programming languages in 2025?",
    "benchmarks": TestBenchmarks(
        max_duration_ms=120000,
        output_contains=["Python"],
    ),
})
