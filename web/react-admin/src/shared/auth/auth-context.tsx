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
import { redirectToKeycloakLogout } from "./keycloak-auth";
import { sessionStore, type AuthUser, type StoredSession } from "./session-store";

type AuthContextValue = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(() => sessionStore.read());

  const logout = useCallback(() => {
    const current = sessionStore.read();
    sessionStore.clear();
    setSession(null);
    redirectToKeycloakLogout(current);
  }, []);

  // When the api client gives up on refreshing, drop the session.
  useEffect(() => {
    setAuthFailureHandler(() => setSession(null));
    return () => setAuthFailureHandler(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      isAuthenticated: Boolean(session?.accessToken),
      logout
    }),
    [session, logout]
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
