"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, CheckCircle2, LogIn, MailCheck } from "lucide-react";
import { Button, Card } from "@/shared/ui";
import { verifyEmail } from "./auth-api";

type VerifyState =
  | { status: "checking" }
  | { status: "success"; email: string }
  | { status: "error"; message: string };

export function VerifyEmailPanel() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [state, setState] = useState<VerifyState>({ status: "checking" });

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setState({ status: "error", message: "Liên kết xác minh không có token." });
      return;
    }
    setState({ status: "checking" });
    verifyEmail(token)
      .then((user) => {
        if (!cancelled) setState({ status: "success", email: user.email });
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: err instanceof Error ? err.message : "Xác minh email thất bại."
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <Card className="mx-auto w-full max-w-md" padding="lg">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">Xác minh email</h1>
          <p className="mt-2 text-sm leading-6 text-ink-500">
            Hoàn tất xác minh để kích hoạt tài khoản học viên.
          </p>
        </div>
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
          <MailCheck className="size-5" />
        </span>
      </div>

      {state.status === "checking" ? (
        <div className="mt-6 rounded-md border border-brand-100 bg-brand-50 px-3 py-3 text-sm font-semibold text-brand-800">
          Đang kiểm tra liên kết xác minh...
        </div>
      ) : null}

      {state.status === "success" ? (
        <div className="mt-6 space-y-5">
          <div className="rounded-md border border-brand-100 bg-brand-50 px-3 py-3 text-sm leading-6 text-brand-800">
            <CheckCircle2 className="mr-2 inline size-4 align-[-2px]" />
            Email {state.email} đã được xác minh.
          </div>
          <Button asChild className="w-full">
            <Link href="/login">
              <LogIn className="size-4" />
              Đăng nhập
            </Link>
          </Button>
        </div>
      ) : null}

      {state.status === "error" ? (
        <div className="mt-6 space-y-5">
          <div className="rounded-md border border-coral-100 bg-coral-50 px-3 py-3 text-sm leading-6 text-coral-700">
            <AlertTriangle className="mr-2 inline size-4 align-[-2px]" />
            {state.message}
          </div>
          <Button asChild variant="secondary" className="w-full">
            <Link href="/register">Tạo lại hoặc gửi lại liên kết</Link>
          </Button>
        </div>
      ) : null}
    </Card>
  );
}
