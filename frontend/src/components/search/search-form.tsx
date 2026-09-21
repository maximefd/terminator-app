"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDebounce } from "@/hooks/use-debounce";
import { ScrollArea } from "@/components/ui/scroll-area";
import { apiFetch } from "@/lib/api-client";

type SearchResult = {
  mot: string;
  source: string;
  definition?: string;
};

/** Motifs proposés à l'écran vide : ils se chargent d'un clic plutôt que d'être à recopier. */
const EXAMPLES = ["P??LE", "?A?SON", "MER??"];

export function SearchForm() {
  const [pattern, setPattern] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const debouncedPattern = useDebounce(pattern, 300);

  useEffect(() => {
    let loadingTimer: NodeJS.Timeout;

    const search = async () => {
      if (debouncedPattern.length < 2) {
        setResults([]);
        setError(null);
        return;
      }

      loadingTimer = setTimeout(() => {
        setIsLoading(true);
      }, 200);

      try {
        setError(null);
        // On utilise maintenant apiFetch, qui gère le token et les erreurs
        const data = await apiFetch(`/api/search`, {
          method: "POST",
          body: { mask: debouncedPattern.toUpperCase() },
        });
        setResults(data.results || []);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("La recherche a échoué.");
        }
        setResults([]);
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
      <div className="mb-4 space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Trouver le mot manquant</h1>
        <p className="text-sm text-muted-foreground">
          Tapez les lettres que vous connaissez et un <span className="font-mono font-semibold">?</span> par
          case vide. La recherche part dès la deuxième lettre.
        </p>
      </div>

      <Label htmlFor="pattern" className="sr-only">
        Motif à rechercher
      </Label>
      <div className="relative">
        <Input
          id="pattern"
          type="search"
          placeholder="Ex : P??LE"
          className="font-mono text-lg uppercase tracking-widest"
          autoComplete="off"
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
        {/* Écran vide : il explique la syntaxe au lieu de ne rien montrer. */}
        {debouncedPattern.length === 0 && !isLoading && (
          <div className="rounded-md border border-dashed p-6 text-center">
            <p className="text-sm text-muted-foreground">Essayez un de ces motifs :</p>
            <div className="mt-3 flex flex-wrap justify-center gap-2">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setPattern(example)}
                  className="rounded-full bg-secondary px-3 py-1 font-mono text-sm font-semibold hover:bg-secondary/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        {debouncedPattern.length === 1 && !isLoading && (
          <p className="text-center text-sm text-muted-foreground">
            Encore une lettre : la recherche démarre à deux caractères.
          </p>
        )}

        {isLoading && results.length === 0 && (
          <p className="text-center text-muted-foreground italic">Recherche en cours...</p>
        )}
        
        {error && (
            <p className="text-center text-destructive">{error}</p>
        )}

        {!isLoading && !error && debouncedPattern.length >= 2 && results.length === 0 && (
          <div className="rounded-md border border-dashed p-6 text-center">
            <p className="text-muted-foreground">
              Aucun mot ne correspond à{" "}
              <span className="font-mono font-semibold uppercase">{debouncedPattern}</span>.
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Remplacez une lettre par un <span className="font-mono font-semibold">?</span>, ou ajoutez le mot
              à l&apos;un de vos dictionnaires s&apos;il vous manque.
            </p>
          </div>
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

