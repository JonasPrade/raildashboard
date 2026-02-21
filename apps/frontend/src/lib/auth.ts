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
// Module-level credential store
//
// Lives outside React so that shared/api/client.ts can read credentials
// without depending on the React tree. Credentials are stored as
// base64(username:password) — the raw HTTP Basic Auth token.
// ---------------------------------------------------------------------------

const STORAGE_KEY = "auth_credentials";

let _credentials: string | null = localStorage.getItem(STORAGE_KEY);

export function getCredentials(): string | null {
  return _credentials;
}

export function setCredentials(creds: string | null): void {
  _credentials = creds;
  if (creds) {
    localStorage.setItem(STORAGE_KEY, creds);
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

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
  logout: () => void;
};

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextType>({
  user: null,
  login: async () => {},
  logout: () => {},
});

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [initialized, setInitialized] = useState(false);

  // On mount: restore session from stored credentials
  useEffect(() => {
    const creds = getCredentials();
    if (!creds) {
      setInitialized(true);
      return;
    }
    api<AuthUser>("/api/v1/users/me")
      .then((u) => setUser(u))
      .catch(() => setCredentials(null))
      .finally(() => setInitialized(true));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const creds = btoa(`${username}:${password}`);
    setCredentials(creds);
    try {
      const u = await api<AuthUser>("/api/v1/users/me");
      setUser(u);
    } catch {
      setCredentials(null);
      throw new Error("Ungültige Anmeldedaten");
    }
  }, []);

  const logout = useCallback(() => {
    setCredentials(null);
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
