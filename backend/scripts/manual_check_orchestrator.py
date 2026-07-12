"""Manual, one-off script — NOT a pytest test (not named test_*, lives
outside tests/, costs real LLM API tokens on every run). Runs real queries
through run_research_query() and prints the full result for each, so you
can see actual tool-selection behavior — not mocked structure.

Run from backend/:
    poetry run python scripts/manual_check_orchestrator.py

Requires a real API key for the configured provider (LLM_PROVIDER /
LLM_MODEL in backend/.env) — this script does not fall back to a mock or
demo mode.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import run_research_query  # noqa: E402

QUERIES = [
    "What's Tesla's current stock price?",
    "What's the capital of France?",
    "Compare NVIDIA and AMD stock performance",
    "What's the latest news on Tesla and what's their stock doing?",
]


def _print_concurrency_check(tools_called: list[dict]) -> None:
    """For queries with 2+ tool calls, print each call's timing and
    whether any pair overlaps — direct evidence of asyncio.gather running
    them concurrently rather than one after another.
    """
    if len(tools_called) < 2:
        return

    print("--- tool call timing ---")
    for call in tools_called:
        print(f"  {call['name']}({call['input']}): {call['started_at']} -> {call['finished_at']}")

    intervals = [
        (call["name"], datetime.fromisoformat(call["started_at"]), datetime.fromisoformat(call["finished_at"]))
        for call in tools_called
    ]
    overlapped = False
    for i in range(len(intervals)):
        for j in range(i + 1, len(intervals)):
            name_i, start_i, end_i = intervals[i]
            name_j, start_j, end_j = intervals[j]
            if start_i < end_j and start_j < end_i:
                print(f"  OVERLAP: {name_i} and {name_j} ran concurrently")
                overlapped = True
    if not overlapped:
        print("  NO OVERLAP DETECTED — calls ran sequentially, not concurrently")
    print()


async def _main() -> None:
    for i, query in enumerate(QUERIES, start=1):
        print(f"{'=' * 70}\nQuery {i}: {query}\n{'=' * 70}")
        result = await run_research_query(query)
        print(json.dumps(result, indent=2))
        _print_concurrency_check(result["tools_called"])
        print()


if __name__ == "__main__":
    asyncio.run(_main())
