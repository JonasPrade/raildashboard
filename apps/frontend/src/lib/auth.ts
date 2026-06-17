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
  // Role name — a system role (viewer/editor/admin) or a custom role.
  role: string;
  // Effective capability keys (admin receives the full catalog from the API).
  permissions: string[];
};

type AuthContextType = {
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Whether the current user holds a capability. */
  can: (permission: string) => boolean;
};

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: async () => {},
  logout: async () => {},
  can: () => false,
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

  const can = useCallback(
    (permission: string) => user?.permissions?.includes(permission) ?? false,
    [user],
  );

  if (!initialized) {
    return null;
  }

  return createElement(
    AuthContext.Provider,
    { value: { user, login, logout, can } },
    children,
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextType {
  return useContext(AuthContext);
}
