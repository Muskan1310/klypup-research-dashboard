import { redirect } from "next/navigation";

/**
 * "/" has no content of its own — middleware.ts sends unauthenticated
 * visitors to /login and authenticated ones to /dashboard, so this route
 * just picks a default target. The Milestone 0 health-check page this
 * used to be has served its purpose (proving frontend/backend
 * connectivity end-to-end); every real request through /api/* now
 * exercises that same path.
 */
export default function RootPage() {
  redirect("/login");
}
