"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getApiBaseUrl } from "@/lib/utils";
import { apiFetch } from "@/lib/api-client"; // On importe notre nouveau client API

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
    const token = localStorage.getItem("access_token");
    if (token) {
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    // On utilise notre client API, qui gère les erreurs
    const data = await apiFetch(`${getApiBaseUrl()}/api/auth/login`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setIsAuthenticated(true);
    // On invalide les requêtes pour forcer leur rafraîchissement avec le nouveau token
    await queryClient.invalidateQueries();
  };

  const register = async (email: string, password: string) => {
    await apiFetch(`${getApiBaseUrl()}/api/auth/register`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    // Après une inscription réussie, on connecte l'utilisateur
    await login(email, password);
  };

  const logout = () => {
    // La déconnexion JWT est une opération purement client : on supprime les tokens
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setIsAuthenticated(false);
    // On vide le cache pour s'assurer qu'aucune donnée personnelle ne reste
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