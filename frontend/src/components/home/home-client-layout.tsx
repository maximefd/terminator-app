// DANS src/components/home/home-client-layout.tsx

"use client";

import { SearchForm } from "@/components/search/search-form";
import { DictionaryPanel } from "@/components/dictionary/dictionary-panel";
import { useAuth } from "@/contexts/auth-context";

export function HomeClientLayout() {
  const { isAuthenticated } = useAuth();

  return (
    <main className="container mx-auto flex-1 p-4 md:p-8">
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