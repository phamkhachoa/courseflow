"use client";

import Link from "next/link";
import { LogIn, MailCheck } from "lucide-react";
import { Button, Card } from "@/shared/ui";

export function VerifyEmailPanel() {
  return (
    <Card className="mx-auto w-full max-w-md" padding="lg">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">Xác minh email</h1>
          <p className="mt-2 text-sm leading-6 text-ink-500">
            Xác minh email học viên được xử lý trong Keycloak.
          </p>
        </div>
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
          <MailCheck className="size-5" />
        </span>
      </div>
      <Button asChild className="mt-6 w-full">
        <Link href="/login">
          <LogIn className="size-4" />
          Đăng nhập
        </Link>
      </Button>
    </Card>
  );
}
