from __future__ import annotations

import asyncio
import os
import time

from rich.console import Console

from agents import Runner, custom_span, gen_trace_id, trace

from .agents.planner_agent import WebSearchItem, WebSearchPlan, planner_agent
from .agents.search_agent import search_agent
from .agents.writer_agent import ReportData, writer_agent
from .printer import Printer
from .tools import get_findings, reset_findings


# Tune to your Anthropic concurrent-requests budget. Defaults to a
# generous ceiling; override in deployments with tighter quotas.
_MAX_PARALLEL_SEARCHES = int(os.environ.get("ANTHROPIC_CONCURRENT_REQUESTS", "100"))


class ResearchManager:
    def __init__(self):
        self.console = Console()
        self.printer = Printer(self.console)

    async def run(self, query: str) -> ReportData:
        reset_findings()
        trace_id = gen_trace_id()
        with trace("Research trace", trace_id=trace_id):
            self.printer.update_item(
                "trace_id",
                f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}",
                is_done=True,
                hide_checkmark=True,
            )

            self.printer.update_item(
                "starting",
                "Starting research...",
                is_done=True,
                hide_checkmark=True,
            )
            search_plan = await self._plan_searches(query)
            search_results = await self._perform_searches(search_plan)
            report = await self._write_report(query, search_results)

            final_report = f"Report summary\n\n{report.short_summary}"
            self.printer.update_item("final_report", final_report, is_done=True)

            self.printer.end()

        print("\n\n=====REPORT=====\n\n")
        print(f"Report: {report.markdown_report}")

        return report

    async def _plan_searches(self, query: str) -> WebSearchPlan:
        self.printer.update_item("planning", "Planning searches...")
        result = await Runner.run(
            planner_agent,
            f"Query: {query}",
        )
        plan = result.final_output_as(WebSearchPlan)
        lines = [f"Will perform {len(plan.searches)} searches:"]
        for i, s in enumerate(plan.searches, 1):
            # Parens (not square brackets) — Rich's Live renderer treats
            # [...] as style markup and would eat the source tag.
            lines.append(f"   {i:>2}. ({s.source:<14}) {s.query}")
        self.printer.update_item(
            "planning",
            "\n".join(lines),
            is_done=True,
        )
        return plan

    @staticmethod
    def _format_tool_chain(tools: list[str]) -> str:
        """Render a tool-call sequence, collapsing consecutive duplicates."""
        if not tools:
            return "(no tools)"
        parts: list[str] = []
        prev, count = tools[0], 1
        for t in tools[1:]:
            if t == prev:
                count += 1
            else:
                parts.append(f"{prev}×{count}" if count > 1 else prev)
                prev, count = t, 1
        parts.append(f"{prev}×{count}" if count > 1 else prev)
        return " → ".join(parts)

    async def _perform_searches(self, search_plan: WebSearchPlan) -> list[str]:
        with custom_span("Search the web"):
            self.printer.update_item("searching", "Searching...")
            num_completed = 0
            num_succeeded = 0
            num_failed = 0

            async def wrapped(idx: int, item: WebSearchItem):
                res = await self._search(item)
                return idx, item, res

            # Cap parallel search agents (see _MAX_PARALLEL_SEARCHES).
            items = search_plan.searches[:_MAX_PARALLEL_SEARCHES]
            tasks = [
                asyncio.create_task(wrapped(i, it))
                for i, it in enumerate(items)
            ]
            results: list[str] = []
            for task in asyncio.as_completed(tasks):
                idx, item, result = await task
                if result is not None:
                    summary, tool_calls = result
                    results.append(summary)
                    num_succeeded += 1
                    self.printer.update_item(
                        f"search_done_{idx}",
                        f"Search {idx+1} ({item.source}): "
                        f"{self._format_tool_chain(tool_calls)}",
                        is_done=True,
                    )
                else:
                    num_failed += 1
                    self.printer.update_item(
                        f"search_done_{idx}",
                        f"Search {idx+1} ({item.source}): FAILED",
                        is_done=True,
                    )
                num_completed += 1
                status = f"Searching... {num_completed}/{len(tasks)} finished"
                if num_failed:
                    status += f" ({num_succeeded} succeeded, {num_failed} failed)"
                self.printer.update_item("searching", status)
            summary = f"Searches finished: {num_succeeded}/{len(tasks)} succeeded"
            if num_failed:
                summary += f", {num_failed} failed"
            self.printer.update_item("searching", summary, is_done=True)
            return results

    async def _search(self, item: WebSearchItem) -> tuple[str, list[str]] | None:
        input = (
            f"Search term: {item.query}\n"
            f"Reason for searching: {item.reason}\n"
            f"Preferred source: {item.source}"
        )
        try:
            result = await Runner.run(
                search_agent,
                input,
            )
            tool_calls = [
                it.tool_name
                for it in result.new_items
                if getattr(it, "type", None) == "tool_call_item"
            ]
            return str(result.final_output), tool_calls
        except Exception:
            return None

    async def _write_report(self, query: str, search_results: list[str]) -> ReportData:
        self.printer.update_item("writing", "Thinking about report...")
        findings = get_findings()
        findings_block = (
            "\n".join(findings) if findings else "(no findings recorded)"
        )
        input = (
            f"Original query: {query}\n"
            f"Summarized search results: {search_results}\n"
            f"Key findings recorded by the search agents:\n{findings_block}"
        )
        result = Runner.run_streamed(
            writer_agent,
            input,
        )
        update_messages = [
            "Thinking about report...",
            "Planning report structure...",
            "Writing outline...",
            "Creating sections...",
            "Cleaning up formatting...",
            "Finalizing report...",
            "Finishing report...",
        ]

        last_update = time.time()
        next_message = 0
        async for _ in result.stream_events():
            if time.time() - last_update > 5 and next_message < len(update_messages):
                self.printer.update_item("writing", update_messages[next_message])
                next_message += 1
                last_update = time.time()

        self.printer.mark_item_done("writing")
        return result.final_output_as(ReportData)
