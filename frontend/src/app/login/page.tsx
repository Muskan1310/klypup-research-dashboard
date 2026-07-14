import { Suspense } from "react";

import { AuthShell } from "@/components/auth/AuthShell";
import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <AuthShell>
      {/* useSearchParams (for the post-login "?next=" redirect target)
          requires a Suspense boundary during static prerendering — the
          fallback never actually shows in practice since this page has
          no server data to wait on. */}
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
