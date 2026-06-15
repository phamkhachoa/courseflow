import { FormEvent, useState } from "react";
import { useLocation } from "react-router-dom";
import { LogIn } from "lucide-react";
import { beginKeycloakLogin } from "@/shared/auth/keycloak-auth";
import { Button } from "@/shared/ui";

export function LoginPage() {
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/courses";

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await beginKeycloakLogin(from);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không bắt đầu được đăng nhập Keycloak");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-brand-900 p-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 shadow-xl">
        <h1 className="text-xl font-bold text-slate-800">CourseFlow Admin</h1>
        <p className="mb-6 text-sm text-slate-500">
          Đăng nhập bằng Keycloak SSO
        </p>
        <form className="space-y-4" onSubmit={handleSubmit}>
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            <LogIn size={16} />
            {loading ? "Đang chuyển hướng" : "Tiếp tục với Keycloak"}
          </Button>
        </form>
      </div>
    </main>
  );
}
