// DANS src/app/page.tsx

import { type Metadata } from 'next';
import { HomeClientLayout } from '@/components/home/home-client-layout'; // On importe notre nouveau composant

// Ce fichier est maintenant un Composant Serveur, il peut donc exporter les métadonnées.
export const metadata: Metadata = {
  title: 'Recherche de mots | Terminator',
  description: 'Trouvez instantanément des mots pour vos grilles de mots fléchés. Recherchez par motif (ex: P??LE) et utilisez vos dictionnaires personnels.',
};

export default function HomePage() {
  // Son seul travail est de rendre le composant client qui contient toute la logique.
  return <HomeClientLayout />;
}