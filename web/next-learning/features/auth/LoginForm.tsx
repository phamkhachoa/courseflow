"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { LogIn, Sparkles, UserPlus } from "lucide-react";
import { hydrateLearnerProfile, learnerSession } from "@/shared/api/client";
import { Button, Card, TextInput } from "@/shared/ui";
import { loginLearner } from "./auth-api";
import { beginKeycloakLogin, keycloakAuthEnabled } from "./keycloak-auth";

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const next = searchParams.get("next");
  const targetHref =
    next?.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") && !next.startsWith("/register")
      ? next
      : "/";
  const registerHref = targetHref === "/" ? "/register" : `/register?next=${encodeURIComponent(targetHref)}`;

  useEffect(() => {
    setHydrated(true);
    if (learnerSession.read()) {
      router.replace(targetHref);
      router.refresh();
    }
  }, [router, targetHref]);

  function fillDemoAccount() {
    setEmail("student@courseflow.local");
    setPassword("password");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    if (keycloakAuthEnabled) {
      try {
        await beginKeycloakLogin(targetHref);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Không mở được Keycloak");
        setLoading(false);
      }
      return;
    }
    try {
      const session = await loginLearner({ email: email.trim(), password });
      learnerSession.write(session);
      await hydrateLearnerProfile().catch(() => session);
      router.push(targetHref);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại");
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
            {keycloakAuthEnabled
              ? "Tiếp tục bằng Keycloak SSO để truy cập không gian học tập."
              : "Truy cập chương học, bài thi, bảng điểm và thông báo cá nhân."}
          </p>
        </div>
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
          <LogIn className="size-5" />
        </span>
      </div>
      {!keycloakAuthEnabled && (
        <p className="mb-6 mt-2 text-sm leading-6 text-ink-500">
          Chưa có tài khoản?{" "}
          <Link href={registerHref} className="font-bold text-brand-700 hover:text-brand-800">
            Đăng ký học viên
          </Link>
        </p>
      )}
      <form className="space-y-4" onSubmit={handleSubmit}>
        {!keycloakAuthEnabled && (
          <>
            <label htmlFor="learner-login-email" className="block text-sm font-semibold text-ink-700">
              Email
              <TextInput
                id="learner-login-email"
                name="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-2"
                autoComplete="email"
                required
              />
            </label>
            <label htmlFor="learner-login-password" className="block text-sm font-semibold text-ink-700">
              Mật khẩu
              <TextInput
                id="learner-login-password"
                name="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-2"
                autoComplete="current-password"
                required
              />
            </label>
          </>
        )}
        {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={!hydrated || loading} className="w-full">
          <LogIn className="size-4" />
          {!hydrated
            ? "Đang sẵn sàng"
            : keycloakAuthEnabled
              ? "Tiếp tục với Keycloak"
              : loading
                ? "Đang đăng nhập"
                : "Đăng nhập"}
        </Button>
        {!keycloakAuthEnabled && (
          <div className="grid gap-2 sm:grid-cols-2">
            <Button type="button" variant="secondary" onClick={fillDemoAccount}>
              <Sparkles className="size-4" />
              Dùng demo
            </Button>
            <Button asChild variant="ghost">
              <Link href={registerHref}>
                <UserPlus className="size-4" />
                Tạo tài khoản
              </Link>
            </Button>
          </div>
        )}
      </form>
    </Card>
  );
}
