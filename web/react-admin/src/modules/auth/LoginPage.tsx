import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { LogIn } from "lucide-react";
import { useAuth } from "@/shared/auth/auth-context";
import { beginKeycloakLogin, keycloakAuthEnabled } from "@/shared/auth/keycloak-auth";
import { Button, FormField, Input } from "@/shared/ui";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/courses";

  const [email, setEmail] = useState("admin@courseflow.local");
  const [password, setPassword] = useState("password");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (keycloakAuthEnabled) {
      await beginKeycloakLogin(from);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-brand-900 p-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 shadow-xl">
        <h1 className="text-xl font-bold text-slate-800">CourseFlow Admin</h1>
        <p className="mb-6 text-sm text-slate-500">
          {keycloakAuthEnabled ? "Đăng nhập bằng Keycloak SSO" : "Đăng nhập vào operations console"}
        </p>
        <form className="space-y-4" onSubmit={handleSubmit}>
          {!keycloakAuthEnabled && (
            <>
              <FormField label="Email" htmlFor="email">
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                />
              </FormField>
              <FormField label="Mật khẩu" htmlFor="password">
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </FormField>
            </>
          )}
          {error && (
            <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
          )}
          <Button type="submit" className="w-full" disabled={loading}>
            <LogIn size={16} />
            {keycloakAuthEnabled ? "Tiếp tục với Keycloak" : loading ? "Đang kết nối" : "Đăng nhập"}
          </Button>
        </form>
      </div>
    </main>
  );
}
