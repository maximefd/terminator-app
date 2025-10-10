// DANS src/contexts/auth-context.tsx

"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getApiBaseUrl } from "@/lib/utils";

type AuthContextType = {
  isAuthenticated: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const queryClient = useQueryClient();

  const login = async () => {
    try {
      await fetch(`${getApiBaseUrl()}/api/login`, {
        method: "POST", // <-- L'OPTION CRUCIALE
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      setIsAuthenticated(true);
      // On invalide les requêtes pour forcer leur rafraîchissement
      await queryClient.invalidateQueries({ queryKey: ['dictionaries'] });
      await queryClient.invalidateQueries({ queryKey: ['words'] }); // Pour plus tard
    } catch (error) {
      console.error("Login failed:", error);
      setIsAuthenticated(false);
    }
  };

  const logout = async () => {
    try {
      await fetch(`${getApiBaseUrl()}/api/logout`, {
        method: "POST", // <-- L'OPTION CRUCIALE
        credentials: "include",
      });
    } catch (error) {
      console.error("Logout failed:", error);
    } finally {
      setIsAuthenticated(false);
      // On vide tout le cache pour s'assurer qu'aucune donnée personnelle ne reste
      queryClient.clear();
    }
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
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