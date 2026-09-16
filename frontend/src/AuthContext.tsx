import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, setToken } from "./api/client";
import type { Me, TokenResponse } from "./api/types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      const m = await api.get<Me>("/auth/me");
      setMe(m);
    } catch {
      setMe(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(email: string, password: string) {
    const res = await api.post<TokenResponse>("/auth/login", { email, password });
    setToken(res.access_token);
    await refresh();
  }

  function logout() {
    api.post("/auth/logout").catch(() => {});
    setToken(null);
    setMe(null);
  }

  return <AuthContext.Provider value={{ me, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
