"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiFetch, forgetLegacyTokens, hasSession, SESSION_EXPIRED_EVENT } from "@/lib/api-client";
import { forgetLastGrid } from "@/lib/last-grid";

type AuthContextType = {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    forgetLegacyTokens();
    setIsAuthenticated(hasSession());
    setIsLoading(false);
  }, []);

  // Session impossible à renouveler (refresh token expiré, compte supprimé...) : on repasse en invité
  useEffect(() => {
    const handleSessionExpired = () => {
      setIsAuthenticated(false);
      queryClient.clear();
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
  }, [queryClient]);

  const login = async (email: string, password: string) => {
    await apiFetch(`/api/auth/login`, {
      method: "POST",
      body: { email, password },
    });

    // L'API a posé les cookies de session (ADR 0015) : rien à ranger ici
    setIsAuthenticated(true);
    // On invalide les requêtes pour forcer un rafraîchissement des données protégées
    await queryClient.invalidateQueries();
  };

  const register = async (email: string, password: string) => {
    await apiFetch(`/api/auth/register`, {
      method: "POST",
      body: { email, password },
    });
    // Comme la connexion : la session arrive en cookies
    setIsAuthenticated(true);
    await queryClient.invalidateQueries();
  };

  const logout = async () => {
    // L'API révoque les jetons et efface les cookies ; même si elle ne répond pas, on se déconnecte ici
    await apiFetch("/api/auth/logout", { method: "POST", csrf: "refresh" }).catch(() => {});
    setIsAuthenticated(false);
    queryClient.clear();
    forgetLastGrid();
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
