// DANS src/app/layout.tsx
"use client"; // Ce layout devient un composant client pour fournir le contexte

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/auth-context";
import { Header } from "@/components/layout/header";
import "./globals.css";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

// On crée une seule instance du client
const queryClient = new QueryClient();

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          inter.variable
        )}
      >
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <div className="relative flex min-h-screen flex-col">
              <Header />
              <div className="flex-1">{children}</div>
            </div>
          </AuthProvider>
        </QueryClientProvider>
      </body>
    </html>
  );
}