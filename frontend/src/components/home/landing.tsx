"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Toggle } from "@/components/ui/toggle";
import { useAuth } from "@/contexts/auth-context";
import { GridSvg } from "@/components/grid/grid-svg";
import { DEMO_DEFINITIONS, DEMO_GRID } from "@/components/home/demo-grid";
import { ExampleDictionary, ExamplePattern } from "@/components/home/example-grid";

/**
 * L'accueil : ce que Terminator fait, dans l'ordre où on s'en sert.
 *
 * La grille montrée est une vraie sortie du moteur, rendue par le composant de l'application — un
 * visiteur voit donc exactement ce que le logiciel fabrique, définitions et flèches comprises.
 */
const STEPS = [
  {
    title: "Générer",
    text: "Un format, vos mots imposés, et le moteur remplit le reste. Il annonce la difficulté avant de chercher.",
    href: "/grid",
    action: "Remplir une grille",
  },
  {
    title: "Conserver",
    text: "La grille qui vous convient se garde, avec un bloc-notes pour vos idées.",
    href: "/grids",
    action: "Voir mes grilles",
  },
  {
    title: "Retoucher",
    text: "Changez les lettres qui ne vous plaisent pas : le logiciel propose les mots qui entrent sans casser un croisement.",
  },
  {
    title: "Définir, puis imprimer",
    text: "Les définitions s'écrivent à même la grille. Export en PDF, solution en seconde page.",
  },
];

export function Landing() {
  const { isAuthenticated } = useAuth();
  const [solution, setSolution] = useState(false);

  return (
    <main className="container mx-auto px-4 py-12 md:py-16">
      <section className="mx-auto max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight md:text-5xl">Composez vos mots fléchés</h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Remplir, retoucher, définir, imprimer. L&apos;atelier complet.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button asChild size="lg">
            <Link href="/grid">Remplir une grille</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link href="/search">Chercher un mot</Link>
          </Button>
        </div>
        <p className="mt-4 text-sm text-muted-foreground">Sans compte, tout de suite.</p>
      </section>

      {/* Une grille finie, produite par le moteur : c'est l'argument, autant le montrer */}
      <section className="mt-16 grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div>
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-semibold">Une grille, du début à la fin</h2>
            <div className="flex gap-1 rounded-md border p-1">
              <Toggle size="sm" pressed={!solution} onPressedChange={() => setSolution(false)}>
                Grille
              </Toggle>
              <Toggle size="sm" pressed={solution} onPressedChange={() => setSolution(true)}>
                Solution
              </Toggle>
            </div>
          </div>
          <div className="max-w-xl">
            <GridSvg
              grid={DEMO_GRID}
              variant={solution ? "solution" : "vierge"}
              definitions={DEMO_DEFINITIONS}
              className="h-auto w-full"
            />
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Une vraie sortie du moteur, autour du mot imposé <strong>PIANO</strong>.
          </p>
        </div>

        {/* Numérotée parce que c'en est une : chaque étape suppose la précédente */}
        <ol className="space-y-6">
          {STEPS.map((step, index) => (
            <li key={step.title} className="flex gap-4">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold tabular-nums">
                {index + 1}
              </span>
              <div>
                <h3 className="font-semibold">{step.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{step.text}</p>
                {step.href && (
                  <Link
                    href={step.href}
                    className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {step.action}
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                )}
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Les deux outils qui ne sont pas dans la séquence : on s'en sert quand on veut */}
      <section className="mt-16">
        <h2 className="text-xl font-semibold">Deux outils à part</h2>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <Link
            href="/search"
            className="group flex flex-col gap-4 rounded-lg border p-6 transition-colors hover:border-primary/60 hover:bg-secondary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="flex h-28 items-center">
              <ExamplePattern />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">Trouver le mot manquant</h3>
              <p className="text-sm text-muted-foreground">
                Les lettres que vous connaissez, un <span className="font-mono font-semibold">?</span>{" "}
                par case vide.
              </p>
            </div>
            <span className="mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary">
              Chercher un motif
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>

          <Link
            href="/dictionaries"
            className="group flex flex-col gap-4 rounded-lg border p-6 transition-colors hover:border-primary/60 hover:bg-secondary/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className="flex h-28 items-center">
              <ExampleDictionary />
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold">Vos propres dictionnaires</h3>
              <p className="text-sm text-muted-foreground">
                Vos mots par thème. Ils remontent dans la recherche, et alimentent les grilles que vous
                cochez.
              </p>
            </div>
            <span className="mt-auto inline-flex items-center gap-1 text-sm font-medium text-primary">
              Gérer mes dictionnaires
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
        </div>
      </section>

      {/* « Que se passe-t-il ensuite ? » : ce que le compte change, et ce qu'il ne change pas */}
      <section className="mx-auto mt-16 max-w-2xl rounded-lg border bg-secondary/20 p-6 text-center">
        {isAuthenticated ? (
          <>
            <h2 className="font-semibold">Vous êtes connecté</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Vos grilles et vos dictionnaires vous attendent.
            </p>
            <div className="mt-4 flex flex-col justify-center gap-2 sm:flex-row">
              <Button asChild variant="outline" size="sm">
                <Link href="/grids">Mes grilles</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link href="/dictionaries">Mes dictionnaires</Link>
              </Button>
            </div>
          </>
        ) : (
          <>
            <h2 className="font-semibold">Un compte sert à garder votre travail</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Chercher et générer marchent en invité. Le compte garde vos grilles et vos dictionnaires.
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
