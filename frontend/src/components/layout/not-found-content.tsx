import Link from "next/link";
import { Button } from "@/components/ui/button";

/** Le contenu de la page 404. Aussi montré par `/admin` à tout autre visiteur que l'administrateur. */
export function NotFoundContent() {
  return (
    <main className="container mx-auto max-w-xl p-4 py-16 text-center md:p-8 md:py-24">
      <p className="text-sm font-medium text-muted-foreground">Erreur 404</p>
      <h1 className="mt-2 text-3xl font-bold">Cette page n&apos;existe pas</h1>
      <p className="mt-4 text-muted-foreground">
        L&apos;adresse est peut-être mal recopiée, ou la page a changé de place. Vous pouvez chercher un mot par
        motif ou générer une grille.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Button asChild>
          <Link href="/">Retour à l&apos;accueil</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/search">Chercher un mot</Link>
        </Button>
      </div>
    </main>
  );
}
