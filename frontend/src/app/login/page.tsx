import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <main className="flex flex-1 items-center justify-center px-4 py-12">
      {/* useSearchParams (for the post-login "?next=" redirect target)
          requires a Suspense boundary during static prerendering — the
          fallback never actually shows in practice since this page has
          no server data to wait on. */}
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
