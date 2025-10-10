// DANS src/components/search/search-form.tsx

"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/use-debounce";
import { getApiBaseUrl } from "@/lib/utils";

type SearchResult = {
  mot: string;
  source: string;
};

export function SearchForm() {
  const [pattern, setPattern] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const debouncedPattern = useDebounce(pattern, 300);

  useEffect(() => {
    // On met en place un minuteur pour le loader
    let loadingTimer: NodeJS.Timeout;

    const search = async () => {
      // On ne lance la recherche que si le motif a au moins 2 caractères
      if (debouncedPattern.length < 2) {
        setResults([]);
        return;
      }

      // NOUVEAUTÉ : On retarde l'affichage du loader de 200ms
      loadingTimer = setTimeout(() => {
        setIsLoading(true);
      }, 200);

      try {
        const response = await fetch(`${getApiBaseUrl()}/api/search`, { // Utiliser la fonction
            method: "POST",
            credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mask: debouncedPattern.toUpperCase() }),
        });
        const data = await response.json();
        setResults(data.results || []);
      } catch (error) {
        console.error("Search failed:", error);
      } finally {
        // NOUVEAUTÉ : On nettoie le minuteur et on cache le loader
        clearTimeout(loadingTimer);
        setIsLoading(false);
      }
    };

    search();
    
    // Au cas où le composant est "démonté" pendant une recherche
    return () => {
      clearTimeout(loadingTimer);
    }
  }, [debouncedPattern]);

  return (
    <div className="w-full max-w-xl">
      <div className="relative">
        <Input
          type="search"
          placeholder="Ex: P??LE, MA??-??É, etc."
          className="text-lg"
          value={pattern}
          onChange={(e) => setPattern(e.target.value)}
        />
        {isLoading && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <svg className="animate-spin h-5 w-5 text-muted-foreground" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        )}
      </div>

      <div className="mt-8">
        {results.length > 0 && (
          <ul className="space-y-2">
            {results.map((word, index) => (
              <li key={`${word.mot}-${index}`} className="rounded-md border bg-card p-3">
                <p className="font-mono text-lg font-semibold">{word.mot}</p>
                <p className="text-sm text-muted-foreground">Source: {word.source}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}