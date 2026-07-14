"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AuthShell } from "@/components/auth/AuthShell";
import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { extractErrorMessage } from "@/lib/api-error";
import type { SignupRequest } from "@/lib/types";
import { TextField } from "@/components/ui/TextField";

type OrgMode = "create" | "join";

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgMode, setOrgMode] = useState<OrgMode>("create");
  const [orgName, setOrgName] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      // Mirrors SignupRequest's own validator (app/schemas/auth.py):
      // org_name only when founding a new org, org_invite_code only when
      // joining one — never both.
      const payload: SignupRequest =
        orgMode === "create"
          ? { email, password, org_name: orgName }
          : { email, password, org_invite_code: inviteCode };

      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok) {
        // Matches app/api/auth.py exactly: 409 duplicate email, 400 for
        // invite-code not-found/expired/already-used.
        const fallback =
          res.status === 409
            ? "An account with that email already exists."
            : res.status === 400
              ? "That invite code isn't valid."
              : "Signup failed. Please try again.";
        setError(extractErrorMessage(data, fallback));
        return;
      }

      router.push("/dashboard");
      router.refresh();
    } catch {
      setError("Couldn't reach the server. Check your connection and try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div className="w-full max-w-sm">
        <div className="mb-8">
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Create your account</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Start a new workspace or join one with an invite
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-900/[0.03] dark:border-white/10 dark:bg-white/[0.03]"
        >
          {error && <ErrorBanner message={error} />}

          <TextField
            id="email"
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            id="password"
            label="Password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={72}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="-mt-2 text-xs text-slate-500 dark:text-slate-400">At least 8 characters.</p>

          <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1 text-sm dark:bg-white/5">
            <button
              type="button"
              onClick={() => setOrgMode("create")}
              className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
                orgMode === "create"
                  ? "bg-white text-brand-700 shadow-sm dark:bg-white/10 dark:text-brand-300"
                  : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              New organization
            </button>
            <button
              type="button"
              onClick={() => setOrgMode("join")}
              className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
                orgMode === "join"
                  ? "bg-white text-brand-700 shadow-sm dark:bg-white/10 dark:text-brand-300"
                  : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              Join with invite
            </button>
          </div>

          {orgMode === "create" ? (
            <TextField
              id="org_name"
              label="Organization name"
              required
              value={orgName}
              onChange={(e) => setOrgName(e.target.value)}
            />
          ) : (
            <TextField
              id="org_invite_code"
              label="Invite code"
              required
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
            />
          )}

          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Creating account…" : "Create account"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-brand-600 hover:text-brand-500">
            Sign in
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
