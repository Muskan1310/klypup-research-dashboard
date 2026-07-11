"""Manual, one-off script — NOT a pytest test (not named test_*, lives
outside tests/, costs real Claude API tokens on every run). Runs three real
queries through run_research_query() and prints the full result for each,
so you can see actual tool-selection behavior — not mocked structure.

Run from backend/:
    poetry run python scripts/manual_check_orchestrator.py

Requires a real ANTHROPIC_API_KEY in your environment or backend/.env —
this script does not fall back to a mock or demo mode.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.orchestrator import run_research_query  # noqa: E402

QUERIES = [
    "What's Tesla's current stock price?",
    "What's the capital of France?",
    "Compare NVIDIA and AMD stock performance",
]

if __name__ == "__main__":
    for i, query in enumerate(QUERIES, start=1):
        print(f"{'=' * 70}\nQuery {i}: {query}\n{'=' * 70}")
        result = run_research_query(query)
        print(json.dumps(result, indent=2))
        print()
