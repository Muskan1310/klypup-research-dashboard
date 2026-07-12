"""Structured research report schemas (TDD Section 6 steps 5-6): the
contract the synthesis call's JSON output must validate against before it
ever reaches the frontend, per CLAUDE.md hard constraint #7 and TDD
Section 11 — malformed LLM output gets one bounded retry, then a clean
failure state, never a crash and never an unvalidated blob shipped
downstream.

Deliberately built for strict structured-output mode (see
app/agents/orchestrator.py): every field is a fixed, known shape — no open
`dict[str, Any]` / free-form objects anywhere. OpenAI's and Gemini's
"strict" JSON-schema modes require `additionalProperties: false` on every
object in the schema, which an open dict can't satisfy; that's why
`comparison_table` is a list of fixed-shape rows (long/tidy format:
one row per ticker+metric+value) rather than an arbitrary-columns table,
and why `key_metrics` is its own model instead of a plain dict.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class KeyMetrics(BaseModel):
    pe_ratio: float | None = None
    market_cap: int | None = None
    eps: float | None = None
    volume: int | None = None


class CompanyCard(BaseModel):
    ticker: str
    price: float | None = None
    change_percent: float | None = None
    key_metrics: KeyMetrics | None = None


class ComparisonRow(BaseModel):
    """One row of a multi-company comparison, in long/tidy format (ticker,
    metric name, value) rather than wide/arbitrary-columns — see module
    docstring for why: a wide table has no fixed schema, which strict
    structured-output mode can't express.
    """

    ticker: str
    metric: str
    value: str


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    sentiment: Literal["positive", "negative", "neutral"]
    published_at: str


class ReportSource(BaseModel):
    """Mirrors app.models.report_source.ReportSource's columns exactly —
    this is what gets persisted into the report_sources table when a
    research report is saved (a later milestone). `source_type`'s three
    literal values must stay in sync with
    app.models.report_source.SourceType (stock_api / news / filing); it's
    a `Literal` here rather than importing that enum directly, to keep
    schemas/ decoupled from the SQLAlchemy model layer (TDD Section 2's
    stated separation) at the cost of duplicating three string constants.
    """

    claim_text: str
    source_type: Literal["stock_api", "news", "filing"]
    source_ref: str


class StructuredResult(BaseModel):
    """The synthesis call's structured output contract. One
    StructuredResult per research query — populated from whatever tool
    results actually came back (a query that only needed stock data will
    have an empty `news_items`, and so on; nothing here is mandatory
    content, only mandatory *shape*).
    """

    company_cards: list[CompanyCard] = Field(default_factory=list)
    comparison_table: list[ComparisonRow] | None = None
    news_items: list[NewsItem] = Field(default_factory=list)
    risk_summary: str = ""
    sources: list[ReportSource] = Field(default_factory=list)


class ResearchQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class ToolCallTrace(BaseModel):
    """One entry in the agent reasoning trace (CLAUDE.md hard constraint
    #9 / PDD F11): which tool ran, with what input, what it returned, and
    when. `result` is intentionally untyped (`Any`) rather than a fixed
    model — unlike `StructuredResult`, this never goes through an LLM
    strict-schema call, and each of the three tools returns a genuinely
    different shape (a dict for get_stock_data/search_documents, a list
    for search_news) that a single fixed schema can't express without
    losing information.
    """

    name: str
    input: dict[str, Any]
    result: Any
    started_at: str
    finished_at: str


class ResearchQueryResponse(BaseModel):
    """The HTTP response shape for POST /research — a direct wrapper
    around app.agents.orchestrator.run_research_query()'s return dict, not
    an independently-invented contract. See that function's docstring for
    the three cases this covers:

    - No tool needed: status="ok", answer set, structured_result None.
    - Tools called, valid output: status="ok", structured_result set,
      answer None.
    - Tools called, still invalid after the bounded retry: status=
      "malformed_output", reason set.

    `tools_called`/`tools_skipped` are always present (the reasoning
    trace), regardless of which of the above applies.
    """

    status: Literal["ok", "malformed_output"]
    answer: str | None = None
    structured_result: StructuredResult | None = None
    reason: str | None = None
    tools_called: list[ToolCallTrace] = Field(default_factory=list)
    tools_skipped: list[str] = Field(default_factory=list)
