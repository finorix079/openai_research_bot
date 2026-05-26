from elasticdash_test import ai_test


@ai_test("helper fails")
async def test_helper_fails(ctx):
    raise AssertionError("intentional failure")
