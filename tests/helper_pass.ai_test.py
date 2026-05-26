from elasticdash_test import ai_test


@ai_test("helper passes")
async def test_helper_passes(ctx):
    ctx.trace.record_llm_step(model="test-model", provider="test", prompt="hi", completion="bye")
    assert True
