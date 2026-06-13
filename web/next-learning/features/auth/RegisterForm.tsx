"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, LogIn, MailCheck, RefreshCw, UserPlus } from "lucide-react";
import { learnerSession } from "@/shared/api/client";
import { Button, Card, TextInput } from "@/shared/ui";
import { registerLearner, resendEmailVerification } from "./auth-api";

export function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const targetHref =
    next?.startsWith("/") && !next.startsWith("//") && !next.startsWith("/login") && !next.startsWith("/register")
      ? next
      : "/";
  const loginHref = targetHref === "/" ? "/login" : `/login?next=${encodeURIComponent(targetHref)}`;
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const [verificationExpiresAt, setVerificationExpiresAt] = useState<string | null>(null);
  const [resending, setResending] = useState(false);
  const [resendNotice, setResendNotice] = useState<string | null>(null);

  useEffect(() => {
    setHydrated(true);
    if (learnerSession.read()) {
      router.replace(targetHref);
      router.refresh();
    }
  }, [router, targetHref]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Mật khẩu nhập lại chưa khớp.");
      return;
    }
    setLoading(true);
    try {
      const registration = await registerLearner({
        fullName: fullName.trim(),
        email: email.trim(),
        password
      });
      setRegisteredEmail(registration.user.email);
      setVerificationExpiresAt(registration.verificationExpiresAt);
      setPassword("");
      setConfirmPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng ký thất bại");
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (!registeredEmail) return;
    setResendNotice(null);
    setResending(true);
    try {
      await resendEmailVerification(registeredEmail);
      setResendNotice("Đã gửi lại email xác minh.");
    } catch (err) {
      setResendNotice(err instanceof Error ? err.message : "Chưa gửi lại được email xác minh.");
    } finally {
      setResending(false);
    }
  }

  const expiryDate = verificationExpiresAt ? new Date(verificationExpiresAt) : null;
  const expiryText =
    expiryDate && !Number.isNaN(expiryDate.getTime())
      ? new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeStyle: "short" }).format(expiryDate)
      : null;

  if (registeredEmail) {
    return (
      <Card className="mx-auto w-full max-w-md" padding="lg">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-ink-900">Kiểm tra email</h1>
            <p className="mt-2 text-sm leading-6 text-ink-500">
              Liên kết xác minh đã được gửi tới {registeredEmail}.
            </p>
          </div>
          <span className="grid size-11 shrink-0 place-items-center rounded-md bg-brand-50 text-brand-700">
            <MailCheck className="size-5" />
          </span>
        </div>
        <div className="mt-5 rounded-md border border-brand-100 bg-brand-50 px-3 py-3 text-sm leading-6 text-brand-800">
          <CheckCircle2 className="mr-2 inline size-4 align-[-2px]" />
          Sau khi xác minh email, bạn có thể đăng nhập và tiếp tục học.
          {expiryText ? <span className="mt-1 block text-xs text-brand-700">Hết hạn: {expiryText}</span> : null}
        </div>
        <div className="mt-6 grid gap-3">
          <Button asChild className="w-full">
            <Link href={loginHref}>
              <LogIn className="size-4" />
              Đến trang đăng nhập
            </Link>
          </Button>
          <Button type="button" variant="secondary" disabled={resending} className="w-full" onClick={handleResend}>
            <RefreshCw className="size-4" />
            {resending ? "Đang gửi lại" : "Gửi lại email xác minh"}
          </Button>
          {resendNotice && <p className="text-center text-sm text-ink-500">{resendNotice}</p>}
        </div>
      </Card>
    );
  }

  return (
    <Card className="mx-auto w-full max-w-md" padding="lg">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink-900">Đăng ký học viên</h1>
          <p className="mt-2 text-sm leading-6 text-ink-500">
            Tạo tài khoản và xác minh email trước khi bắt đầu học.
          </p>
        </div>
        <span className="grid size-11 shrink-0 place-items-center rounded-md bg-accent-50 text-accent-600">
          <UserPlus className="size-5" />
        </span>
      </div>
      <div className="mb-6 mt-5 rounded-md border border-brand-100 bg-brand-50 px-3 py-3 text-sm leading-6 text-brand-800">
        <CheckCircle2 className="mr-2 inline size-4 align-[-2px]" />
        Hệ thống sẽ gửi liên kết xác minh đến email của bạn.
      </div>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <label htmlFor="learner-register-name" className="block text-sm font-semibold text-ink-700">
          Họ và tên
          <TextInput
            id="learner-register-name"
            name="fullName"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="mt-2"
            autoComplete="name"
            required
          />
        </label>
        <label htmlFor="learner-register-email" className="block text-sm font-semibold text-ink-700">
          Email
          <TextInput
            id="learner-register-email"
            name="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-2"
            autoComplete="email"
            required
          />
        </label>
        <label htmlFor="learner-register-password" className="block text-sm font-semibold text-ink-700">
          Mật khẩu
          <TextInput
            id="learner-register-password"
            name="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-2"
            autoComplete="new-password"
            minLength={12}
            required
          />
          <span className="mt-2 block text-xs font-medium leading-5 text-ink-500">
            Tối thiểu 12 ký tự, gồm chữ hoa, chữ thường, số và ký tự đặc biệt.
          </span>
        </label>
        <label htmlFor="learner-register-confirm-password" className="block text-sm font-semibold text-ink-700">
          Nhập lại mật khẩu
          <TextInput
            id="learner-register-confirm-password"
            name="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-2"
            autoComplete="new-password"
            minLength={12}
            required
          />
        </label>
        {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
        <Button type="submit" disabled={!hydrated || loading} className="w-full">
          <UserPlus className="size-4" />
          {!hydrated ? "Đang sẵn sàng" : loading ? "Đang tạo tài khoản" : "Tạo tài khoản"}
        </Button>
        <Button asChild variant="ghost" className="w-full">
          <Link href={loginHref}>
            <LogIn className="size-4" />
            Đã có tài khoản
          </Link>
        </Button>
      </form>
    </Card>
  );
}
