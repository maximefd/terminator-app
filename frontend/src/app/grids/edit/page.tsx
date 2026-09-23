import { type Metadata } from "next";
import { Suspense } from "react";
import { GridEditorFromAddress } from "@/components/grid/grid-editor-page";

export const metadata: Metadata = {
  title: "Définitions | Terminator",
  description: "Écrivez les définitions de votre grille, puis exportez-la en PDF.",
};

/**
 * L'éditeur d'une grille conservée : /grids/edit?id=12.
 *
 * L'identifiant passe dans l'adresse et non dans le chemin (/grids/12) : le site est un export statique
 * (ADR 0013), qui ne peut pas générer d'avance une page par grille. <Suspense> : Next l'exige autour de
 * useSearchParams.
 */
export default function GridEditorPage() {
  return (
    <Suspense>
      <GridEditorFromAddress />
    </Suspense>
  );
}
