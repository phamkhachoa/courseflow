import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import { setAuthFailureHandler } from "@/shared/api/client";
import { loginRequest, logoutRequest } from "./auth-api";
import { sessionStore, type AuthUser, type StoredSession } from "./session-store";

type AuthContextValue = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(() => sessionStore.read());

  const logout = useCallback(() => {
    void logoutRequest();
    sessionStore.clear();
    setSession(null);
  }, []);

  // When the api client gives up on refreshing, drop the session.
  useEffect(() => {
    setAuthFailureHandler(() => setSession(null));
    return () => setAuthFailureHandler(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const token = await loginRequest(email, password);
    const next: StoredSession = {
      accessToken: token.accessToken,
      refreshToken: token.refreshToken,
      user: token.user
    };
    sessionStore.write(next);
    setSession(next);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      isAuthenticated: Boolean(session?.accessToken),
      login,
      logout
    }),
    [session, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
