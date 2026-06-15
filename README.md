# Research bot

A multi-agent research bot built on the OpenAI Agents SDK, instrumented with [ElasticDash](https://elasticdash.com).

## Flow

1. **`planner_agent`** (Claude Sonnet) takes the query and produces 5–20 search terms.
2. **`search_agent`** (Claude Haiku) runs once per search term, in parallel, calling
   `web_search_tool` and returning a single short paragraph summary.
3. **`writer_agent`** (Claude Sonnet) synthesizes the summaries into a multi-section markdown report.

### Model tier choice

| Agent          | Model                   | Why                                                                                |
|----------------|-------------------------|------------------------------------------------------------------------------------|
| Planner        | `claude-sonnet-4`       | One call per query. Plan quality drives everything downstream — pay for it.        |
| Search/summary | `claude-haiku-4-5`      | Highest call volume (one per search term × every query). Cost-sensitive hot path.  |
| Writer         | `claude-sonnet-4`       | One call per query. Report quality is user-facing — pay for it.                    |

Concrete model IDs are pinned in `research_bot/agents/__init__.py` as `STRONG_MODEL` and `FAST_MODEL`.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
# create .env with the keys below
```

Required env vars:

```bash
CLAUDE_API_KEY=sk-ant-...           # all three agents + the web search tool
ELASTICDASH_API_KEY=ed_...
ELASTICDASH_SERVER_URL=https://server.elasticdash.com
```

## Run

```bash
python -m research_bot.main
```

## Minimal instrumentation diff

Three touch points adopt ElasticDash. They are the only ElasticDash-aware lines in the project.

### 1. Wrap the entrypoint as a single trace

`research_bot/main.py`:

```python
from elasticdash_sdk.observability import (
    init_observability, ObservabilityOptions, start_trace, end_trace,
)

handle = await init_observability(ObservabilityOptions(
    server_url=os.environ.get("ELASTICDASH_SERVER_URL"),
    api_key=os.environ.get("ELASTICDASH_API_KEY"),
))
try:
    start_trace("research_workflow")
    await ResearchManager().run(query)
    end_trace()
finally:
    await handle.shutdown()
```

That's the workflow wrap. Every LLM call made between `start_trace` and `end_trace` — the
planner, every parallel search/summarizer, and the writer — is captured as its own step with
the exact input and output.

### 2. Wrap the web search tool with `@ed_tool`

`research_bot/tools.py`:

```python
from elasticdash_sdk import ed_tool
from agents import function_tool

@ed_tool(name="web_search_tool")
async def web_search_rerun(query: str) -> str:
    ...  # real web search call

@function_tool
async def web_search_tool(query: str) -> str:
    """Search the web for information about a topic."""
    return await web_search_rerun(query)
```

`@function_tool` registers the tool with the Agents SDK; `@ed_tool` records the call's
raw input and output as its own step in the trace, separate from the search agent's
summary output that flows to the writer.

### 3. Register the tool module at import time

`research_bot/__init__.py`:

```python
from . import tools  # noqa: F401
```

That's the full integration.

## What the trace contains

After a run, the trace exposes — per step, individually addressable:

| Step                       | Input                                  | Output                          |
|----------------------------|----------------------------------------|---------------------------------|
| Planner LLM call           | the user query                         | the `WebSearchPlan`             |
| Each search agent LLM call | one `WebSearchItem`                    | the short paragraph summary     |
| Each `web_search_tool` call| the search term                        | the raw web search result       |
| Writer LLM call            | the query + all summaries              | the markdown report             |

The raw web search result is stored as the `web_search_tool` step output, separately from
the summary that the search agent emits — so reruns and inspections can target either layer.
