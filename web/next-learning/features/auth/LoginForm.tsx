"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LogIn } from "lucide-react";
import { learnerSession } from "@/shared/api/client";
import { Button, Card } from "@/shared/ui";
import { beginKeycloakLogin } from "./keycloak-auth";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const next = searchParams.get("next");
  const targetHref =
    next?.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") && !next.startsWith("/register")
      ? next
      : "/";

  useEffect(() => {
    setHydrated(true);
    if (learnerSession.read()) {
      router.replace(targetHref);
      router.refresh();
    }
  }, [router, targetHref]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await beginKeycloakLogin(targetHref);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không mở được Keycloak");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="mx-auto w-full max-w-md" padding="lg">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">Đăng nhập học viên</h1>
          <p className="mt-2 text-sm leading-6 text-ink-500">
            Tiếp tục bằng Keycloak SSO để truy cập không gian học tập.
          </p>
        </div>
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
          <LogIn className="size-5" />
        </span>
      </div>
      <form className="space-y-4" onSubmit={handleSubmit}>
        {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={!hydrated || loading} className="w-full">
          <LogIn className="size-4" />
          {!hydrated ? "Đang sẵn sàng" : loading ? "Đang chuyển hướng" : "Tiếp tục với Keycloak"}
        </Button>
      </form>
    </Card>
  );
}
