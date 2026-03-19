import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { createElement } from "react";
import { api } from "../shared/api/client";
import { queryClient } from "./query";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AuthUser = {
  id: number;
  username: string;
  role: "viewer" | "editor" | "admin";
};

type AuthContextType = {
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: async () => {},
  logout: async () => {},
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [initialized, setInitialized] = useState(false);

  // On mount: restore session from httpOnly cookie (transparent to JS)
  useEffect(() => {
    api<AuthUser>("/api/v1/users/me")
      .then((u) => setUser(u))
      .catch(() => {
        // No valid session — user stays null
      })
      .finally(() => setInitialized(true));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    await api("/api/v1/auth/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }).catch(() => {
      throw new Error("Ungültige Anmeldedaten");
    });
    const u = await api<AuthUser>("/api/v1/users/me");
    setUser(u);
  }, []);

  const logout = useCallback(async () => {
    await api("/api/v1/auth/session", { method: "DELETE" }).catch(() => {
      // Ignore errors on logout (e.g. already expired session)
    });
    setUser(null);
    queryClient.clear();
  }, []);

  if (!initialized) {
    return null;
  }

  return createElement(
    AuthContext.Provider,
    { value: { user, login, logout } },
    children,
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextType {
  return useContext(AuthContext);
}
