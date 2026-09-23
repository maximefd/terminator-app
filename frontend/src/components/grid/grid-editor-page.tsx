"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { GridEditor } from "@/components/grid/grid-editor";

/** Lit l'identifiant de la grille dans l'adresse (`?id=12`) et ouvre l'éditeur. */
export function GridEditorFromAddress() {
  const gridId = Number(useSearchParams().get("id"));

  if (!Number.isInteger(gridId) || gridId < 1) {
    return (
      <main className="container mx-auto max-w-2xl p-4 text-center md:p-8">
        <h1 className="text-2xl font-semibold">Grille introuvable</h1>
        <p className="mt-2 text-muted-foreground">Cette adresse ne désigne aucune grille.</p>
        <Button asChild size="sm" className="mt-4">
          <Link href="/grids">Retour à mes grilles</Link>
        </Button>
      </main>
    );
  }
  return <GridEditor gridId={gridId} />;
}
