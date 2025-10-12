// DANS src/components/layout/footer.tsx

import Link from "next/link";

export function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t">
      <div className="container mx-auto flex flex-col items-center justify-between gap-4 p-4 md:flex-row">
        <p className="text-sm text-muted-foreground">
          &copy; {currentYear} Terminator. Tous droits réservés.
        </p>
        <nav className="flex items-center gap-4 text-sm text-muted-foreground">
          <Link href="/legal" className="hover:text-primary">
            Mentions Légales
          </Link>
          <Link href="/privacy" className="hover:text-primary">
            Confidentialité
          </Link>
        </nav>
      </div>
    </footer>
  );
}