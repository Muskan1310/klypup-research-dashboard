/**
 * Types mirroring the backend's actual Pydantic schemas field-for-field —
 * app/schemas/auth.py and app/schemas/research.py. Kept in exact sync by
 * hand (no codegen in this project); if a backend field changes, this file
 * changes with it, not the other way around.
 */

export type UserRole = "admin" | "analyst";

export interface UserResponse {
  id: number;
  email: string;
  role: UserRole;
  org_id: number;
}

export interface SignupRequest {
  email: string;
  password: string;
  org_invite_code?: string | null;
  org_name?: string | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

// --- app/schemas/research.py ---

export interface KeyMetrics {
  pe_ratio: number | null;
  market_cap: number | null;
  eps: number | null;
  volume: number | null;
}

export interface CompanyCard {
  ticker: string;
  price: number | null;
  change_percent: number | null;
  key_metrics: KeyMetrics | null;
}

/** One row of a long/tidy comparison table (ticker, metric, value) — the
 * backend stores it this way because a wide/arbitrary-columns table has no
 * fixed schema (see app/schemas/research.py's ComparisonRow docstring).
 * The UI pivots this back into a wide table — see lib/pivotComparison.ts.
 */
export interface ComparisonRow {
  ticker: string;
  metric: string;
  value: string;
}

export type Sentiment = "positive" | "negative" | "neutral";

export interface NewsItem {
  title: string;
  source: string;
  url: string;
  sentiment: Sentiment;
  published_at: string;
}

export type SourceType = "stock_api" | "news" | "filing";

export interface ReportSource {
  claim_text: string;
  source_type: SourceType;
  source_ref: string;
}

export interface StructuredResult {
  company_cards: CompanyCard[];
  comparison_table: ComparisonRow[] | null;
  news_items: NewsItem[];
  risk_summary: string;
  sources: ReportSource[];
}

export interface ToolCallTrace {
  name: string;
  input: Record<string, unknown>;
  result: unknown;
  started_at: string;
  finished_at: string;
}

export interface ResearchQueryRequest {
  query: string;
}

/** Direct mirror of ResearchQueryResponse (app/schemas/research.py), which
 * is itself a direct wrapper around run_research_query()'s real return
 * dict — not an independently invented shape.
 */
export interface ResearchQueryResponse {
  status: "ok" | "malformed_output";
  answer: string | null;
  structured_result: StructuredResult | null;
  reason: string | null;
  tools_called: ToolCallTrace[];
  tools_skipped: string[];
}

// --- app/schemas/report.py ---

export interface SaveReportRequest {
  query_text: string;
  structured_result: StructuredResult;
}

export interface ReportListItem {
  id: number;
  query_text: string;
  created_at: string;
}

export interface ReportListResponse {
  reports: ReportListItem[];
  total: number;
}

export interface ReportDetailResponse {
  id: number;
  query_text: string;
  structured_result: StructuredResult;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateReportTagsRequest {
  tags: string[];
}

// --- app/schemas/watchlist.py ---

export interface WatchlistItemCreate {
  ticker: string;
}

export interface WatchlistItemResponse {
  id: number;
  ticker: string;
  added_at: string;
}

export interface WatchlistResponse {
  items: WatchlistItemResponse[];
}

// --- app/schemas/org.py ---

export interface InviteCodeResponse {
  code: string;
  expires_at: string;
}

export interface OrgMemberResponse {
  id: number;
  email: string;
  role: UserRole;
  created_at: string;
}

export interface OrgMembersResponse {
  members: OrgMemberResponse[];
}
