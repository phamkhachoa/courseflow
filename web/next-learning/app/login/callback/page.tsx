"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { completeKeycloakLogin } from "@/features/auth/keycloak-auth";
import { hydrateLearnerProfile, learnerSession } from "@/shared/api/client";
import { Button, Card } from "@/shared/ui";

export default function LoginCallbackPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    completeKeycloakLogin(window.location.href)
      .then(({ session, returnTo }) => {
        learnerSession.write(session);
        return hydrateLearnerProfile()
          .catch(() => session)
          .finally(() => window.location.replace(returnTo));
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Đăng nhập Keycloak thất bại");
      });
  }, []);

  return (
    <main className="mx-auto flex min-h-[calc(100vh-72px)] max-w-7xl items-center justify-center px-5 py-12">
      <Card className="w-full max-w-md" padding="lg">
        <h1 className="text-2xl font-bold text-ink-900">CourseFlow Learn</h1>
        {error ? (
          <div className="mt-5 space-y-4">
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
            <Button asChild>
              <Link href="/login">Quay lại đăng nhập</Link>
            </Button>
          </div>
        ) : (
          <p className="mt-4 text-sm text-ink-500">Đang hoàn tất đăng nhập bằng Keycloak SSO...</p>
        )}
      </Card>
    </main>
  );
}
