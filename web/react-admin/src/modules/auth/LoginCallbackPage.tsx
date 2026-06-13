import { useEffect, useState } from "react";
import { hydrateSessionProfile } from "@/shared/api/client";
import { completeKeycloakLogin } from "@/shared/auth/keycloak-auth";
import { sessionStore } from "@/shared/auth/session-store";
import { Spinner } from "@/shared/ui";

export function LoginCallbackPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    completeKeycloakLogin(window.location.href)
      .then(({ session, returnTo }) => {
        sessionStore.write(session);
        return hydrateSessionProfile()
          .catch(() => session)
          .finally(() => window.location.replace(returnTo));
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Đăng nhập Keycloak thất bại");
      });
  }, []);

  return (
    <main className="flex min-h-screen items-center justify-center bg-brand-900 p-4 text-white">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 text-slate-800 shadow-xl">
        <h1 className="text-xl font-bold">CourseFlow Admin</h1>
        {error ? (
          <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
        ) : (
          <div className="mt-5 flex items-center gap-3 text-sm text-slate-500">
            <Spinner />
            Đang hoàn tất đăng nhập...
          </div>
        )}
      </div>
    </main>
  );
}
