"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { DictionaryPanel } from "@/components/dictionary/dictionary-panel";
import { useAuth } from "@/contexts/auth-context";
import { site } from "@/config/site";

export function DictionariesClientLayout() {
  const { isAuthenticated, isLoading } = useAuth();

  return (
    <main className="container mx-auto max-w-3xl p-4 md:p-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Vos dictionnaires</h1>
        <p className="mx-auto mt-2 max-w-xl text-muted-foreground">
          Vos mots par thème, avec leurs définitions. Ils passent en tête de la recherche par motif et
          alimentent les mots souhaités des grilles que vous générez.
        </p>
      </div>

      <div className="mt-8">
        {/* Tant que la session n'est pas relue, ni panneau ni invitation : les deux seraient faux. */}
        {isLoading ? (
          <p className="text-center text-sm text-muted-foreground">Chargement…</p>
        ) : isAuthenticated ? (
          <DictionaryPanel />
        ) : (
          <div className="rounded-lg border bg-secondary/20 p-6 text-center">
            <h2 className="font-semibold">Un compte est nécessaire ici</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              Les dictionnaires sont les seules données que {site.name} conserve. La recherche et la génération,
              elles, fonctionnent en invité.
            </p>
            <div className="mt-4 flex flex-col justify-center gap-2 sm:flex-row">
              <Button asChild size="sm">
                <Link href="/register">Créer un compte</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/login">Se connecter</Link>
              </Button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
