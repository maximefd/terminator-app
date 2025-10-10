// DANS src/app/page.tsx

"use client"; // On passe cette page en composant client pour utiliser le hook useAuth

import { SearchForm } from "@/components/search/search-form";
import { DictionaryPanel } from "@/components/dictionary/dictionary-panel";
import { useAuth } from "@/contexts/auth-context";

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <main className="container mx-auto flex-1 p-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Le formulaire de recherche prend les 2/3 de l'espace sur grand écran */}
        <div className="lg:col-span-2">
          <SearchForm />
        </div>

        {/* Le panneau des dictionnaires s'affiche uniquement si on est connecté */}
        {isAuthenticated && (
          <div className="lg:col-span-1">
            <DictionaryPanel />
          </div>
        )}
      </div>
    </main>
  );
}