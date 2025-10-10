"use client";

import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";

export function Header() {
  const { isAuthenticated, login, logout } = useAuth();

  return (
    <header className="border-b">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        <h1 className="text-xl font-bold">🧩 Terminator</h1>
        {isAuthenticated ? (
          <Button onClick={logout}>Se déconnecter</Button>
        ) : (
          <Button onClick={login}>Se connecter (Démo)</Button>
        )}
      </div>
    </header>
  );
}