"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { ExampleDictionary, ExampleGrid, ExamplePattern } from "@/components/home/example-grid";

type Block = {
  href: string;
  title: string;
  description: string;
  action: string;
  illustration: React.ReactNode;
};

const BLOCKS: Block[] = [
  {
    href: "/search",
    title: "Trouver le mot manquant",
    description:
      "Vous connaissez la longueur et quelques lettres : tapez-les avec des « ? » pour les cases vides. Les mots de votre dictionnaire actif apparaissent avec leur définition.",
    action: "Chercher un motif",
    illustration: <ExamplePattern />,
  },
  {
    href: "/grid",
    title: "Remplir une grille automatiquement",
    description:
      "Choisissez un format, donnez les mots que vous voulez y voir — obligatoires ou simplement souhaités — et le moteur remplit le reste. Il annonce la difficulté avant de commencer.",
    action: "Générer une grille",
    illustration: <ExampleGrid />,
  },
  {
    href: "/dictionaries",
    title: "Vos propres dictionnaires",
    description:
      "Rassemblez vos mots par thème, avec leurs définitions. Ils passent en tête de la recherche et alimentent les grilles que vous générez.",
    action: "Gérer mes dictionnaires",
    illustration: <ExampleDictionary />,
  },
];

export function Landing() {
  const { isAuthenticated } = useAuth();

  return (
    <main className="container mx-auto px-4 py-12 md:py-16">
      <section className="mx-auto max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">Composez vos mots fléchés</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Deux outils pour les grilles françaises : chercher le mot qui rentre dans les cases, ou laisser le
          moteur remplir une grille entière autour de vos mots.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/grid">Remplir une grille</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/search">Chercher un mot</Link>
          </Button>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">
          Sans compte et sans installation : les deux fonctionnent tout de suite.
        </p>
      </section>

      <section className="mt-16 grid gap-6 md:grid-cols-3">
        {BLOCKS.map((block) => (
          <Link
            key={block.href}
            href={block.href}
            className="group flex flex-col gap-4 rounded-lg border p-6 transition-colors hover:border-primary/60 hover:bg-secondary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {/* Hauteur commune : sans elle, la grille (haute) décale le titre du bloc du milieu. */}
            <div className="flex h-44 items-center justify-center">{block.illustration}</div>
            <div className="space-y-2">
              <h2 className="text-lg font-semibold">{block.title}</h2>
              <p className="text-sm text-muted-foreground">{block.description}</p>
            </div>
            <span className="mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary">
              {block.action}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
        ))}
      </section>

      {/* « Que se passe-t-il ensuite ? » : ce que le compte change, et ce qu'il ne change pas. */}
      <section className="mx-auto mt-16 max-w-2xl rounded-lg border bg-secondary/20 p-6 text-center">
        {isAuthenticated ? (
          <>
            <h2 className="font-semibold">Vous êtes connecté</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Vos dictionnaires sont pris en compte dans la recherche et dans les grilles que vous générez.
            </p>
            <Button asChild variant="outline" size="sm" className="mt-4">
              <Link href="/dictionaries">Voir mes dictionnaires</Link>
            </Button>
          </>
        ) : (
          <>
            <h2 className="font-semibold">Un compte sert à garder vos mots</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              La recherche et la génération marchent en invité. Le compte n&apos;ajoute qu&apos;une chose : vos
              dictionnaires thématiques, conservés d&apos;une session à l&apos;autre.
            </p>
            <div className="mt-4 flex flex-col justify-center gap-2 sm:flex-row">
              <Button asChild size="sm">
                <Link href="/register">Créer un compte</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/login">Se connecter</Link>
              </Button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
