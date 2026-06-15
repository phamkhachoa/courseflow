"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { LogIn, UserPlus } from "lucide-react";
import { learnerSession } from "@/shared/api/client";
import { Button, Card } from "@/shared/ui";
import { useEffect } from "react";

export function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const targetHref =
    next?.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") && !next.startsWith("/register")
      ? next
      : "/";
  const loginHref = targetHref === "/" ? "/login" : `/login?next=${encodeURIComponent(targetHref)}`;

  useEffect(() => {
    if (learnerSession.read()) {
      router.replace(targetHref);
      router.refresh();
    }
  }, [router, targetHref]);

  return (
    <Card className="mx-auto w-full max-w-md" padding="lg">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">Tài khoản Keycloak SSO</h1>
          <p className="mt-2 text-sm leading-6 text-ink-500">
            Tài khoản học viên được cấp qua Keycloak SSO hoặc quy trình mời của tổ chức.
          </p>
        </div>
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
          <UserPlus className="size-5" />
        </span>
      </div>
      <Button asChild className="mt-6 w-full">
        <Link href={loginHref}>
          <LogIn className="size-4" />
          Đến trang đăng nhập
        </Link>
      </Button>
    </Card>
  );
}
