"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { apiFetch, clearTokens, hasStoredSession, SESSION_EXPIRED_EVENT, storeTokens } from "@/lib/api-client";

type AuthContextType = {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    setIsAuthenticated(hasStoredSession());
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
    const data = await apiFetch(`/api/auth/login`, {
      method: "POST",
      body: { email, password },
    });

    storeTokens(data);
    setIsAuthenticated(true);
    // On invalide les requêtes pour forcer un rafraîchissement des données protégées
    await queryClient.invalidateQueries();
  };

  const register = async (email: string, password: string) => {
    const data = await apiFetch(`/api/auth/register`, {
      method: "POST",
      body: { email, password },
    });
    // La route /register renvoie les tokens, on les stocke directement
    storeTokens(data);
    setIsAuthenticated(true);
    await queryClient.invalidateQueries();
  };

  const logout = () => {
    clearTokens();
    setIsAuthenticated(false);
    queryClient.clear();
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
