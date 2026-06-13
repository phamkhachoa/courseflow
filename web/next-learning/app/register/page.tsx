import { Suspense } from "react";
import { BookOpenCheck, GraduationCap, ShieldCheck } from "lucide-react";
import { RegisterForm } from "@/features/auth/RegisterForm";
import { FeatureTile } from "@/shared/ui";

const registerFeatures = [
  { title: "Xác minh email", icon: BookOpenCheck },
  { title: "Theo dõi tiến độ", icon: GraduationCap },
  { title: "Phiên đăng nhập an toàn", icon: ShieldCheck }
];

export default function RegisterPage() {
  return (
    <main className="mx-auto grid min-h-[calc(100vh-72px)] max-w-7xl items-center gap-8 px-5 py-12 sm:px-6 lg:grid-cols-[1fr_440px] lg:px-8">
      <section>
        <p className="text-sm font-bold text-brand-600">Tạo tài khoản học viên</p>
        <h1 className="mt-3 max-w-2xl text-5xl font-bold leading-tight text-ink-900">
          Tạo tài khoản học viên với phiên đăng nhập an toàn hơn ngay từ đầu.
        </h1>
        <div className="mt-8 grid max-w-2xl gap-4 sm:grid-cols-3">
          {registerFeatures.map(({ title, icon: Icon }) => (
            <FeatureTile key={title} title={title} icon={<Icon className="size-5" />} />
          ))}
        </div>
      </section>
      <Suspense fallback={null}>
        <RegisterForm />
      </Suspense>
    </main>
  );
}
