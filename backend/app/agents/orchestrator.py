"""Agent orchestrator (TDD Section 6, Section 7): the two-pass Claude
tool-calling loop, using only the market data tool for now.

Hand-rolled per CLAUDE.md hard constraint #1 — no agent framework, and
deliberately not even the Anthropic SDK's beta tool-runner helper. Every
step below (the planning call, walking `response.content` for `tool_use`
blocks, calling the tool function ourselves, building `tool_result` blocks,
the second "synthesis" call) is code this project owns and can point to,
not framework internals — that's the whole point of the constraint.

Real parallel execution across multiple tool *types* (asyncio.gather) is
explicitly TDD Section 6 step 3 / Milestone 4's job, not this one's — this
loop is otherwise already correct for multiple tool_use blocks of the
*same* tool in one turn (e.g. two get_stock_data calls for two tickers,
see scripts/manual_check_orchestrator.py query 3), it just runs them
sequentially for now.
"""

import json

import anthropic

from app.agents.tools.market_data import get_stock_data
from app.core.config import settings

MODEL = "claude-opus-4-8"
MAX_TOKENS = 4096

STOCK_DATA_TOOL = {
    "name": "get_stock_data",
    "description": (
        "Get real-time stock price, percent change, trading volume, and "
        "fundamentals (P/E ratio, market cap, EPS) for ONE publicly traded "
        "company, given its stock ticker symbol. Use this only when the "
        "user is asking about a specific company's current stock price, "
        "recent price movement, trading volume, or financial fundamentals. "
        "Do NOT use this for general knowledge questions, news or sentiment "
        "analysis, or anything that isn't about a specific ticker's market "
        "data. If the user names multiple companies, call this tool once "
        "per company, not once for all of them."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol, e.g. 'AAPL', 'TSLA', 'NVDA'.",
            }
        },
        "required": ["ticker"],
    },
}

ALL_TOOL_NAMES = {STOCK_DATA_TOOL["name"]}


def run_research_query(query: str) -> dict:
    """Run one research query through the two-pass tool-calling loop.

    Returns:
        {
            "answer": str,             # Claude's final synthesized text
            "tools_called": [          # every tool actually invoked this run
                {"name": "get_stock_data", "input": {...}, "result": {...}},
                ...
            ],
            "tools_skipped": [str],    # names of tools NOT called this run
        }

    Structured this way — not just a bare string — because this becomes the
    agent's reasoning trace surfaced in the API response in a later
    milestone (TDD Section 6 step 4, PDD Section 8): which tools were
    called vs. skipped. `tools_skipped` names, not a bare count/bool,
    because it needs to scale to "which of our N tools did Claude decide
    were irrelevant" once Milestone 4 adds more tools — not just "were any
    tools skipped."
    """
    if not settings.anthropic_api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not configured. Set it in backend/.env "
            "before calling run_research_query — this function makes real "
            "calls to the Anthropic API and has no mock/demo fallback."
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    messages = [{"role": "user", "content": query}]

    # --- Pass 1: planning call. Claude decides which tool(s), if any, to
    # call, and with what arguments (TDD Section 6 step 2). ---
    planning_response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[STOCK_DATA_TOOL],
        messages=messages,
    )

    tool_use_blocks = [block for block in planning_response.content if block.type == "tool_use"]

    if not tool_use_blocks:
        # No tool_use blocks: Claude judged this query didn't need
        # real-time data, so its planning-call text is already the final
        # answer — no second pass needed.
        return {
            "answer": _extract_text(planning_response),
            "tools_called": [],
            "tools_skipped": sorted(ALL_TOOL_NAMES),
        }

    # --- Execute every requested tool call ourselves. This is TDD Section 7's
    # core point: the model only ever *requests* a call; our code is what
    # actually runs it (and Claude never sees code, only the JSON result we
    # send back). ---
    tools_called = []
    tool_result_blocks = []
    for block in tool_use_blocks:
        if block.name == "get_stock_data":
            result = get_stock_data(block.input.get("ticker", ""))
        else:
            result = {"status": "failed", "reason": f"Unknown tool '{block.name}'"}

        tools_called.append({"name": block.name, "input": dict(block.input), "result": result})
        tool_result_blocks.append(
            {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
                # A failed tool call (get_stock_data's own
                # {"status": "failed", "reason": ...} shape) is marked
                # is_error per Anthropic's documented convention for this
                # exact case — but the structured reason is still in
                # `content`, so Claude can read *why* it failed and
                # acknowledge that in its final answer rather than the
                # whole turn just erroring out. This is the graceful
                # degradation CLAUDE.md hard constraint #7 requires.
                "is_error": result.get("status") == "failed",
            }
        )

    called_tool_names = {block.name for block in tool_use_blocks}

    messages.append({"role": "assistant", "content": planning_response.content})
    messages.append({"role": "user", "content": tool_result_blocks})

    # --- Pass 2: synthesis call. Send the tool result(s) back as
    # tool_result blocks in the same conversation; Claude produces the
    # final answer with that data (or that failure) in context. ---
    synthesis_response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[STOCK_DATA_TOOL],
        messages=messages,
    )

    return {
        "answer": _extract_text(synthesis_response),
        "tools_called": tools_called,
        "tools_skipped": sorted(ALL_TOOL_NAMES - called_tool_names),
    }


def _extract_text(response: anthropic.types.Message) -> str:
    return "".join(block.text for block in response.content if block.type == "text")
