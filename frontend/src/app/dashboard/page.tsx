import { InviteTeammate } from "@/components/dashboard/InviteTeammate";
import { RecentReports } from "@/components/dashboard/RecentReports";
import { WatchlistStrip } from "@/components/dashboard/WatchlistStrip";
import { ResearchConsole } from "@/components/research/ResearchConsole";
import { BACKEND_URL } from "@/lib/backend";
import { getAuthToken, getCurrentUser } from "@/lib/server-auth";
import type { ReportListItem, WatchlistItemResponse } from "@/lib/types";

const RECENT_REPORTS_LIMIT = 3;

export default async function DashboardPage() {
  const token = await getAuthToken();
  const authHeader = { Authorization: `Bearer ${token}` };

  const [reportsRes, watchlistRes, currentUser] = await Promise.all([
    fetch(`${BACKEND_URL}/reports`, { headers: authHeader, cache: "no-store" }),
    fetch(`${BACKEND_URL}/watchlist`, { headers: authHeader, cache: "no-store" }),
    getCurrentUser(),
  ]);

  const recentReports: ReportListItem[] = reportsRes.ok
    ? (await reportsRes.json()).reports.slice(0, RECENT_REPORTS_LIMIT)
    : [];
  const watchlistItems: WatchlistItemResponse[] = watchlistRes.ok
    ? (await watchlistRes.json()).items
    : [];

  return (
    <div className="space-y-8">
      <ResearchConsole />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <RecentReports reports={recentReports} />
        <WatchlistStrip initialItems={watchlistItems} />
      </div>

      {currentUser?.role === "admin" && <InviteTeammate />}
    </div>
  );
}
