import type { OrgMemberResponse } from "@/lib/types";

function formatDate(iso: string) {
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/** Admin-only — the page rendering this already checked the role (see
 * dashboard/page.tsx). The "manages workspace" capability from the PDD,
 * kept as its own distinct thing from InviteTeammate ("invites users").
 */
export function TeamList({ members }: { members: OrgMemberResponse[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-900/[0.03] dark:border-white/10 dark:bg-white/[0.03]">
      <h3 className="text-sm font-semibold text-slate-900 dark:text-white">Team</h3>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Everyone in your organization.
      </p>

      <ul className="mt-3 divide-y divide-slate-100 dark:divide-white/10">
        {members.map((member) => (
          <li key={member.id} className="flex items-center justify-between gap-3 py-2 text-sm">
            <span className="truncate text-slate-700 dark:text-slate-200">{member.email}</span>
            <span className="flex flex-none items-center gap-3">
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                  member.role === "admin"
                    ? "bg-brand-50 text-brand-700 dark:bg-brand-400/10 dark:text-brand-300"
                    : "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-300"
                }`}
              >
                {member.role}
              </span>
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {formatDate(member.created_at)}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
