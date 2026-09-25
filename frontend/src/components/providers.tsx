"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/auth-context";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Toaster } from "@/components/ui/sonner";
import { MonitoringInit } from "@/components/monitoring/monitoring-init";

/** Tout ce qui vit dans le navigateur : cache des requêtes, session, notifications. La mise en page racine reste
 *  un composant serveur, pour porter les métadonnées communes (titres, adresse canonique). */
export function Providers({ children }: { children: React.ReactNode }) {
  // Un client par navigateur, créé une fois
  const [queryClient] = useState(() => new QueryClient());
  return (
    <>
      <MonitoringInit />
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <div className="relative flex min-h-screen flex-col">
            <Header />
            <div className="flex-1">{children}</div>
            <Footer />
          </div>
          <Toaster richColors position="bottom-right" />
        </AuthProvider>
      </QueryClientProvider>
    </>
  );
}
