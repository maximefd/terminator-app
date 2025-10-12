// DANS src/components/search/search-form.tsx

"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/use-debounce";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getApiBaseUrl } from "@/lib/utils"; // Assurez-vous que cet import est présent

type SearchResult = {
  mot: string;
  source: string;
  definition?: string;
};

export function SearchForm() {
  const [pattern, setPattern] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const debouncedPattern = useDebounce(pattern, 300);

  useEffect(() => {
    let loadingTimer: NodeJS.Timeout;

    const search = async () => {
      if (debouncedPattern.length < 2) {
        setResults([]);
        return;
      }

      loadingTimer = setTimeout(() => {
        setIsLoading(true);
      }, 200);

      try {
        // VÉRIFIEZ BIEN CETTE LIGNE
        const response = await fetch(`${getApiBaseUrl()}/api/search`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mask: debouncedPattern.toUpperCase() }),
        });
        
        // Si la réponse est 404, on lance une erreur
        if (!response.ok) {
            throw new Error(`Erreur ${response.status}: La route n'a pas été trouvée.`);
        }

        const data = await response.json();
        setResults(data.results || []);
      } catch (error) {
        console.error("Search failed:", error);
      } finally {
        clearTimeout(loadingTimer);
        setIsLoading(false);
      }
    };

    search();
    
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
        {isLoading && results.length === 0 && (
          <p className="text-center text-muted-foreground italic">Recherche en cours...</p>
        )}
        {!isLoading && debouncedPattern.length >= 2 && results.length === 0 && (
          <p className="text-center text-muted-foreground">Aucun résultat trouvé pour "{debouncedPattern}".</p>
        )}
        {results.length > 0 && (
          <div className="rounded-md border">
            <ScrollArea className="h-[60vh]">
              <div className="p-4">
                <p className="mb-4 text-sm font-medium text-muted-foreground">
                  {results.length} résultat{results.length > 1 ? 's' : ''}
                </p>
                <div className="space-y-4">
                  {results.map((word, index) => (
                    <div key={`${word.mot}-${index}`}>
                      <div className="flex items-center justify-between">
                        <p className="font-mono text-base font-semibold">{word.mot}</p>
                        {word.source === 'PERSONNEL' && (
                          <span className="text-xs font-semibold text-primary px-2 py-1 bg-primary/10 rounded-full">
                            Personnel
                          </span>
                        )}
                      </div>
                      {word.definition && (
                        <p className="text-sm text-muted-foreground mt-1 italic">
                          {word.definition}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </ScrollArea>
          </div>
        )}
      </div>
    </div>
  );
}