import { InviteTeammate } from "@/components/dashboard/InviteTeammate";
import { RecentReports } from "@/components/dashboard/RecentReports";
import { TeamList } from "@/components/dashboard/TeamList";
import { WatchlistStrip } from "@/components/dashboard/WatchlistStrip";
import { ResearchConsole } from "@/components/research/ResearchConsole";
import { BACKEND_URL } from "@/lib/backend";
import { getAuthToken, getCurrentUser } from "@/lib/server-auth";
import type { OrgMemberResponse, ReportListItem, WatchlistItemResponse } from "@/lib/types";

const RECENT_REPORTS_LIMIT = 3;

export default async function DashboardPage() {
  const token = await getAuthToken();
  const authHeader = { Authorization: `Bearer ${token}` };
  // Decoding the JWT is local (no network call), so awaiting it up front
  // costs nothing and lets us decide below whether the org-members fetch
  // is even worth making.
  const currentUser = await getCurrentUser();
  const isAdmin = currentUser?.role === "admin";

  const [reportsRes, watchlistRes, membersRes] = await Promise.all([
    fetch(`${BACKEND_URL}/reports`, { headers: authHeader, cache: "no-store" }),
    fetch(`${BACKEND_URL}/watchlist`, { headers: authHeader, cache: "no-store" }),
    isAdmin
      ? fetch(`${BACKEND_URL}/orgs/members`, { headers: authHeader, cache: "no-store" })
      : Promise.resolve(null),
  ]);

  const recentReports: ReportListItem[] = reportsRes.ok
    ? (await reportsRes.json()).reports.slice(0, RECENT_REPORTS_LIMIT)
    : [];
  const watchlistItems: WatchlistItemResponse[] = watchlistRes.ok
    ? (await watchlistRes.json()).items
    : [];
  const members: OrgMemberResponse[] = membersRes?.ok ? (await membersRes.json()).members : [];

  return (
    <div className="space-y-8">
      <ResearchConsole />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <RecentReports reports={recentReports} />
        <WatchlistStrip initialItems={watchlistItems} />
      </div>

      {isAdmin && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <TeamList members={members} />
          <InviteTeammate />
        </div>
      )}
    </div>
  );
}
