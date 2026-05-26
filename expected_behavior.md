# Expected behavior — `research_workflow`

This document defines the intended flow of the research bot. If a recorded
trace deviates from this spec, treat it as a bug and locate the root cause.

It is meant to be read by a human reviewer **and** by an automated
debug agent comparing a trace against a contract.

---

## Architecture

```
user query
   │
   ▼
PlannerAgent ──► WebSearchPlan (N items, each with query + source + reason)
   │
   ▼  (one parallel search agent run per plan item)
SearchAgent × N ──► per-item summary + findings appended to scratchpad
   │
   ▼
WriterAgent ──► final report (markdown, short summary, follow-up questions)
```

---

## Planner contract

| Field | Expectation |
|---|---|
| Plan size | 5–12 `WebSearchItem`s |
| Each item | unique, specific query (avoid one-word queries) |
| `source` | exactly one of `web`, `news`, `arxiv`, `knowledge_base` |
| `reason` | explains what evidence the search will surface (not a restatement of the query) |

### Source-selection rules (must hold across the plan)

| Source | Use when… |
|---|---|
| `knowledge_base` | Question could plausibly be answered by internal data (adoption stats, internal tooling, prior work). Always include ≥1 KB item if the query hints at internal scope. |
| `arxiv` | Question concerns primary research, methods, benchmarks, or scientific claims (ML, biology, physics, etc.). |
| `news` | Question depends on recent events, announcements, releases, or market moves (last weeks/months). |
| `web` | General fallback: market context, surveys, blog posts, documentation, vendor pages. |

### Diversity rule (HARD)

A healthy plan uses **2 or more source types**. A plan that's 100% one
source (typically `web`) is the canonical symptom of a planner-prompt
regression.

### Query-keyword heuristics for source expectations

If the user query contains one of the listed keywords/phrases, the plan
**must include at least one item with the corresponding source**:

| If query contains… | Plan must include source… |
|---|---|
| "paper", "papers", "research", "literature", "arxiv", "study" | `arxiv` |
| "recent", "latest", "news", "this week", "announced", "release", "Q[1-4] 20\d\d" | `news` |
| "internally", "internal", "our company", "our team", "our org", "in-house" | `knowledge_base` |

---

## Search-agent contract (per plan item)

The search agent runs once per planned item with its `Preferred source`.
A healthy run looks like:

```
primary search tool (matching the assigned source)
   → (optional) fetch_url_tool          [at most once, only for a clearly informative URL]
   → (optional) extract_key_facts_tool  [only after a fetch_url]
   → save_finding_tool × 1–3            [anchored on verifiable facts with source labels]
   → final LLM message (the summary)
```

Tool-call expectations per item:

| Metric | Healthy range | Red flag |
|---|---|---|
| Total tool calls per item | 3–7 | 0, or > 12 |
| `save_finding_tool` per item | 1–3 | 0 (no findings recorded) |
| Primary search tool fired | exactly 1 | 0 (search skipped) or > 2 (thrashing) |
| `fetch_url_tool` per item | 0 or 1 | ≥ 2 (unbounded fetching) |

If the preferred source returns nothing useful, the agent **may** fall
back to `web_search_tool`. That's the only legitimate cross-source
behavior at the per-item level.

---

## Writer-agent contract

Input includes: original query, list of per-item summaries, and the
findings scratchpad.

Output:

| Field | Expectation |
|---|---|
| `short_summary` | 2–3 sentences |
| `markdown_report` | ≥ 1000 words, structured with headings |
| `follow_up_questions` | non-empty list of suggested next searches |

The final report **must reference findings recorded via
`save_finding_tool`**. If the writer ignores them, suspect that
findings aren't being passed in (check `manager._write_report`).

---

## Workflow-level invariants

| Invariant | How to check |
|---|---|
| At least one tool of each kind fires for a multi-faceted query | Tool-name distribution in trace |
| Source diversity ≥ 2 in the planner output | Plan's `source` field histogram |
| Total trace duration < 30 min for plans ≤ 10 items | `duration_ms` |
| Zero `hasError: true` events | Walk all events |

---

## Debugging playbook (for a tracing agent)

Given a freshly fetched trace and a user-reported issue, run these
checks **in order**. Stop at the first violation; that's almost
certainly the root cause.

1. **Source histogram across plan items.** Reconstruct it from the
   search-agent inputs (`Preferred source: X` line). If one source
   accounts for > 80% of items, the planner prompt has likely lost its
   diversification rule. Open `research_bot/agents/planner_agent.py` and
   compare the `PROMPT` constant against the source-selection rules
   above.
2. **Keyword-heuristic checks.** Run the table in "Query-keyword
   heuristics" against the user's input query. If a required source is
   missing, that's the bug surface.
3. **Per-item tool-chain shape.** For each search item, compare the
   tool-call sequence against "Search-agent contract." Items with 0
   `save_finding_tool` calls usually mean the search agent's
   instructions have drifted.
4. **Writer findings linkage.** If the report's `markdown_report`
   doesn't mention facts that show up in `save_finding_tool` outputs,
   findings aren't reaching the writer — check `manager._write_report`.
5. **Rerun the suspicious step.** Use `rerun_step` on the planner's AI
   event (or the search-agent's first AI event for a problem item)
   to confirm the bug is deterministic.

When you find the violation, the suggested fix is **always**: restore
the prompt or wiring described in this document, then re-run the
workflow with the same query to confirm the trace now matches the spec.
