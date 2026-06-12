import { Suspense } from "react";
import { Award, BarChart3, BookOpen } from "lucide-react";
import { LoginForm } from "@/features/auth/LoginForm";
import { FeatureTile } from "@/shared/ui";

const loginFeatures = [
  { title: "Tiến độ học", icon: BookOpen },
  { title: "Bảng điểm", icon: BarChart3 },
  { title: "Chứng chỉ", icon: Award }
];

export default function LoginPage() {
  return (
    <main className="mx-auto grid min-h-[calc(100vh-72px)] max-w-7xl items-center gap-8 px-5 py-12 sm:px-6 lg:grid-cols-[1fr_440px] lg:px-8">
      <section>
        <p className="text-sm font-bold text-brand-600">Truy cập học viên</p>
        <h1 className="mt-3 max-w-2xl text-5xl font-bold leading-tight text-ink-900">
          Tiếp tục học, làm bài thi và xem điểm trong một phiên đăng nhập.
        </h1>
        <div className="mt-8 grid max-w-2xl gap-4 sm:grid-cols-3">
          {loginFeatures.map(({ title, icon: Icon }) => (
            <FeatureTile key={title} title={title} icon={<Icon className="size-5" />} />
          ))}
        </div>
      </section>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
