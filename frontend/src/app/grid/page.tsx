// DANS src/app/grid/page.tsx

import { type Metadata } from 'next';
import { GridClientLayout } from '@/components/grid/grid-client-layout'; // On importe notre nouveau composant
import { publicPage } from '@/lib/seo';

// Ce fichier est maintenant un Composant Serveur, il peut exporter les métadonnées.
export const metadata: Metadata = publicPage({
  path: "/grid",
  title: "Générer une grille",
  description:
    "Choisissez un format de grille et les mots que vous voulez y voir : le moteur remplit le reste avec des mots qui se croisent, puis vous écrivez les définitions et exportez en PDF.",
});

export default function GridPage() {
  // Son seul travail est de rendre le composant client qui contient toute la logique.
  return <GridClientLayout />;
}