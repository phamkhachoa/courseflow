export type AuthUser = {
  id: number;
  email: string;
  fullName: string;
  avatarUrl?: string;
  role: string;
  status: string;
};

export type StoredSession = {
  accessToken: string;
  refreshToken: string;
  idToken?: string;
  user: AuthUser;
};

const STORAGE_KEY = "courseflow.admin.session";

/**
 * Token persistence. We use localStorage so a page refresh keeps the operator
 * signed in. Note: localStorage is readable by any script on the origin, so an
 * XSS bug would expose the token — acceptable for an internal backoffice, but
 * worth revisiting with httpOnly cookies if this goes public.
 */
export const sessionStore = {
  read(): StoredSession | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as StoredSession) : null;
    } catch {
      return null;
    }
  },
  write(session: StoredSession): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  },
  clear(): void {
    localStorage.removeItem(STORAGE_KEY);
  }
};
