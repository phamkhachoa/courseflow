import { Suspense } from "react";
import { MailCheck, ShieldCheck, UserCheck } from "lucide-react";
import { VerifyEmailPanel } from "@/features/auth/VerifyEmailPanel";
import { FeatureTile } from "@/shared/ui";

const verifyFeatures = [
  { title: "Kích hoạt tài khoản", icon: UserCheck },
  { title: "Bảo vệ danh tính", icon: ShieldCheck },
  { title: "Sẵn sàng vào học", icon: MailCheck }
];

export default function VerifyEmailPage() {
  return (
    <main className="mx-auto grid min-h-[calc(100vh-72px)] max-w-7xl items-center gap-8 px-5 py-12 sm:px-6 lg:grid-cols-[1fr_440px] lg:px-8">
      <section>
        <p className="text-sm font-bold text-brand-600">Xác minh tài khoản</p>
        <h1 className="mt-3 max-w-2xl text-5xl font-bold leading-tight text-ink-900">
          Hoàn tất xác minh email để bắt đầu học an toàn.
        </h1>
        <div className="mt-8 grid max-w-2xl gap-4 sm:grid-cols-3">
          {verifyFeatures.map(({ title, icon: Icon }) => (
            <FeatureTile key={title} title={title} icon={<Icon className="size-5" />} />
          ))}
        </div>
      </section>
      <Suspense fallback={null}>
        <VerifyEmailPanel />
      </Suspense>
    </main>
  );
}
