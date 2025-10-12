// DANS src/app/grid/page.tsx

import { type Metadata } from 'next';
import { GridClientLayout } from '@/components/grid/grid-client-layout'; // On importe notre nouveau composant

// Ce fichier est maintenant un Composant Serveur, il peut exporter les métadonnées.
export const metadata: Metadata = {
  title: 'Générer une grille | Terminator',
  description: 'Créez automatiquement des grilles de mots fléchés remplies. Choisissez la taille et laissez notre algorithme construire une grille complète pour vous.',
};

export default function GridPage() {
  // Son seul travail est de rendre le composant client qui contient toute la logique.
  return <GridClientLayout />;
}