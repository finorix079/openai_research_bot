# Research bot

This is a simple example of a multi-agent research bot, instrumented with [ElasticDash](https://elasticdash.com) for trace recording, debugging, and step-level reruns.

## Setup (macOS)

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Set your API keys
cp .env.example .env  # then edit .env with your keys
# Required keys:
#   OPENAI_API_KEY=sk-...          # OpenAI Agents SDK
#   CLAUDE_API_KEY=sk-ant-...      # Anthropic web search
#   ELASTICDASH_API_KEY=ed_...     # ElasticDash observability
#   ELASTICDASH_SERVER_URL=...     # ElasticDash server endpoint
```

## Run

```bash
python -m research_bot.main
```

## Architecture

The flow is:

1. User enters their research topic
2. `planner_agent` comes up with a plan to search the web for information. The plan is a list of search queries, with a search term and a reason for each query.
3. For each search item, we run a `search_agent`, which uses Anthropic's built-in web search tool to search for that term and summarize the results. These all run in parallel.
4. Finally, the `writer_agent` receives the search summaries, and creates a written report.

## Observability & Rerun Support

This project uses the `elasticdash-test` SDK for trace recording. Understanding what gets tracked — and what doesn't — is important for debugging and rerunning steps.

### What gets tracked automatically

**LLM calls** — All LLM calls (OpenAI, Anthropic, etc.) are automatically intercepted and recorded when you call `init_observability()`. This includes the model name, full input/output, token usage, and duration. No code changes needed — the SDK patches the underlying HTTP clients.

**Traces** — Wrap your workflow entry point with `start_trace()` / `end_trace()` to group all events into a single trace:

```python
from elasticdash_test.observability import init_observability, ObservabilityOptions, start_trace, end_trace

handle = await init_observability(ObservabilityOptions(
    server_url=os.environ.get("ELASTICDASH_SERVER_URL"),
    api_key=os.environ.get("ELASTICDASH_API_KEY"),
))

start_trace("my_workflow")
# ... your agent logic ...
end_trace()

await handle.shutdown()
```

### What does NOT get tracked automatically

**Hosted/server-side tools** — Tools that run inside the API provider's infrastructure (e.g., OpenAI's `WebSearchTool()`, Anthropic's `web_search_20250305`) are invisible to the SDK. The SDK sees the LLM call that *triggers* the tool, but not the tool execution itself, because it happens server-side within the provider's API call.

This means:
- You can see that the LLM decided to call a search tool (in the LLM output)
- You **cannot** see the tool's input/output as a separate recorded step
- You **cannot** rerun the tool call independently

### How to make tools trackable and rerunnable

If you need full visibility and rerun support for a tool, **re-implement it as a local function** and wrap it with `@ed_tool`. Use the `name=` parameter to match the tool name the agent uses — this is how the ElasticDash MCP server matches trace events to rerunnable functions:

```python
from elasticdash_test import ed_tool

@ed_tool(name="web_search_tool")
async def web_search_rerun(query: str) -> str:
    """Trackable wrapper around Anthropic's web search."""
    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": query}],
    )
    # extract and return text ...
```

The `@ed_tool` decorator records the function's input and output as a tool event in the trace. This makes the step visible in the ElasticDash dashboard and enables reruns via the MCP server.

Then, create a corresponding `@function_tool` (from the OpenAI Agents SDK) that **calls the `@ed_tool`-wrapped function**, so the agent's tool calls flow through the ElasticDash recording:

```python
from agents import function_tool

@function_tool
async def web_search_tool(query: str) -> str:
    """Search the web for information about a topic."""
    return await web_search_rerun(query)
```

**Why two decorators?** They serve different purposes:
- `@function_tool` — Registers the function as a tool the agent can call (OpenAI Agents SDK)
- `@ed_tool` — Records the call in the trace for observability and rerun (ElasticDash SDK)

**Important:** The `@function_tool` must call the `@ed_tool`-wrapped function (not the underlying implementation directly). This ensures every tool invocation is recorded with full input/output in the trace. The `name=` on `@ed_tool` must match the `@function_tool` function name so that reruns can find the correct implementation.

Make sure the module containing `@ed_tool` functions is imported at startup so they get registered in-process:

```python
# research_bot/__init__.py
from . import tools  # noqa: F401 — register @ed_tool functions
```

For CLI discoverability (e.g. `elasticdash run-tool`), also create an `ed_tools.py` in the project root that imports the `@ed_tool` functions:

```python
# ed_tools.py
from research_bot.tools import web_search_rerun  # noqa: F401
```

### Defining workflows and tests

For the ElasticDash test runner, define your workflow in `ed_workflows.py` and tests in `ed_tests.py`:

```python
# ed_workflows.py
async def research_workflow(input=None):
    """Entry point for the ed-test runner."""
    start_trace("research_workflow")
    manager = ResearchManager()
    report = await manager.run(input)
    end_trace()
    return report.markdown_report
```

```python
# ed_tests.py
from elasticdash_test.ci.test_registry import define_test
from elasticdash_test.ci.types import TestBenchmarks

define_test({
    "name": "research bot e2e",
    "workflow": "research_workflow",
    "input": "What are the top 3 most popular programming languages in 2025?",
    "benchmarks": TestBenchmarks(
        max_duration_ms=120000,
        output_contains=["Python"],
    ),
})
```

## Suggested improvements

If you're building your own research bot, some ideas to add to this are:

1. Retrieval: Add support for fetching relevant information from a vector store. You could use the File Search tool for this.
2. Image and file upload: Allow users to attach PDFs or other files, as baseline context for the research.
3. More planning and thinking: Models often produce better results given more time to think. Improve the planning process to come up with a better plan, and add an evaluation step so that the model can choose to improve its results, search for more stuff, etc.
4. Code execution: Allow running code, which is useful for data analysis.
