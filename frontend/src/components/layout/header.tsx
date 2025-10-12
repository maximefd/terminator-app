// DANS src/components/layout/header.tsx

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { Menu } from "lucide-react";
import { useState } from "react";

export function Header() {
  const { isAuthenticated, login, logout } = useAuth();
  const pathname = usePathname();
  const [isMobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { href: "/", label: "Recherche" },
    { href: "/grid", label: "Générer" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4">
        {/* LOGO (visible partout) */}
        <Link href="/" className="flex items-center gap-2 text-xl font-bold">
          <span role="img" aria-label="Pièce de puzzle">🧩</span>
          <span className="hidden sm:inline-block">Terminator</span>
        </Link>

        {/* NAVIGATION BUREAU (cachée sur mobile) */}
        <nav className="hidden lg:flex items-center gap-2">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "px-3 py-2 rounded-md text-sm font-medium transition-colors",
                pathname === item.href
                  ? "bg-secondary text-secondary-foreground"
                  : "text-muted-foreground hover:bg-secondary/80 hover:text-secondary-foreground"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* SECTION DROITE : AUTH + MENU MOBILE */}
        <div className="flex items-center gap-2">
          {/* Bouton de connexion */}
          <div>
            {isAuthenticated ? (
              <Button onClick={logout} size="sm">Déconnexion</Button>
            ) : (
              <Button onClick={login} size="sm">Connexion</Button>
            )}
          </div>

          {/* Menu Hamburger (caché sur bureau) */}
          <div className="lg:hidden">
            <Sheet open={isMobileMenuOpen} onOpenChange={setMobileMenuOpen}>
              <SheetTrigger asChild>
                <Button variant="outline" size="icon">
                  <Menu className="h-6 w-6" />
                  <span className="sr-only">Ouvrir le menu</span>
                </Button>
              </SheetTrigger>
              <SheetContent side="left">
                {/* ... Contenu du menu mobile (inchangé) ... */}
                <nav className="grid gap-6 text-lg font-medium mt-8">
                  <Link href="/" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2 text-lg font-semibold">
                     <span role="img" aria-label="Pièce de puzzle">🧩</span> Terminator
                  </Link>
                  {navItems.map((item) => (
                    <Link key={item.href} href={item.href} onClick={() => setMobileMenuOpen(false)} className={cn("text-muted-foreground hover:text-foreground", pathname === item.href && "text-foreground font-semibold")}>
                      {item.label}
                    </Link>
                  ))}
                </nav>
              </SheetContent>
            </Sheet>
          </div>
        </div>
      </div>
    </header>
  );
}