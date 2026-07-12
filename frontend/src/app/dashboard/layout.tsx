import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/dashboard/LogoutButton";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="border-b border-slate-200 bg-white dark:border-white/10 dark:bg-transparent">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-6">
            <span className="text-sm font-semibold text-slate-900 dark:text-white">
              Klypup Research
            </span>
            <nav className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
              <Link href="/dashboard" className="hover:text-slate-900 dark:hover:text-white">
                New query
              </Link>
              <Link
                href="/dashboard/history"
                className="hover:text-slate-900 dark:hover:text-white"
              >
                History
              </Link>
            </nav>
          </div>
          <LogoutButton />
        </div>
      </header>
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8">{children}</main>
    </div>
  );
}
