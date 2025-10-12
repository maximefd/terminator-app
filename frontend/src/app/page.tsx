// DANS src/app/page.tsx

"use client";

import { SearchForm } from "@/components/search/search-form";
import { DictionaryPanel } from "@/components/dictionary/dictionary-panel";
import { useAuth } from "@/contexts/auth-context";

export default function HomePage() {
  const { isAuthenticated } = useAuth();

  return (
    <main className="container mx-auto flex-1 p-4 md:p-8">
      {/* Cette mise en page est déjà responsive ! */}
      {/* Par défaut (mobile), c'est une seule colonne. */}
      {/* Sur les grands écrans (lg:), ça passe à 3 colonnes. */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <SearchForm />
        </div>

        {isAuthenticated && (
          <div className="lg:col-span-1">
            <DictionaryPanel />
          </div>
        )}
      </div>
    </main>
  );
}