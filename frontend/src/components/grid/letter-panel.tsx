"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, BookPlus, Check, Eraser, PenLine } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Toggle } from "@/components/ui/toggle";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { apiFetch } from "@/lib/api-client";
import type { PlacedWord } from "@/components/grid/grid-display";

export type { PlacedWord } from "@/components/grid/grid-display";

type Suggestions = {
  pattern: string;
  allowed: string[];
  words: string[];
  truncated: boolean;
  current: string;
  keep_letters: boolean;
};

type Dictionary = { id: number; name: string; is_active: boolean };

/**
 * Le panneau du mode lettres : le mot en cours, ceux qui pourraient le remplacer, et ce que le
 * lexique en dit.
 *
 * Les propositions viennent du serveur, qui n'offre que des mots **laissant les croisements
 * valides** — proposer PERTE si le vertical devient impossible ne rendrait service à personne.
 */
export function LetterPanel({
  gridId,
  word,
  crossing,
  onReplace,
  onClear,
  unknownWords,
}: {
  gridId: number;
  word: PlacedWord | null;
  crossing: PlacedWord | null;
  onReplace: (word: string) => void;
  onClear: () => void;
  unknownWords: string[];
}) {
  const [suggestions, setSuggestions] = useState<Suggestions | null>(null);
  const [isLoading, setLoading] = useState(false);
  // Par défaut on comble les trous : les lettres laissées en place sont des contraintes voulues
  const [keepLetters, setKeepLetters] = useState(true);

  useEffect(() => {
    if (!word) {
      setSuggestions(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    apiFetch(`/api/grids/${gridId}/suggestions`, {
      method: "POST",
      body: { x: word.x, y: word.y, direction: word.direction, keep_letters: keepLetters },
    })
      .then((data) => !cancelled && setSuggestions(data))
      .catch(() => !cancelled && setSuggestions(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [gridId, word, keepLetters]);

  if (!word) {
    return (
      <div className="space-y-2 rounded-lg border border-dashed p-4 text-sm">
        <p className="font-medium">Relisez les mots avant de les définir</p>
        <p className="text-muted-foreground">
          Un mot ne vous plaît pas ? Choisissez-le dans la liste ou cliquez une de ses cases : des
          remplaçants vous sont proposés, qui gardent les croisements valides. Vous pouvez aussi taper
          vos propres lettres directement dans la grille.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3 rounded-lg border p-4">
        <div className="flex items-baseline justify-between gap-2">
          <p className="font-mono text-xl font-semibold tracking-wide">{word.text}</p>
          <p className="text-xs text-muted-foreground">
            {word.direction === "across" ? "horizontal" : "vertical"} ·{" "}
            {word.length ?? word.text.length} lettres
          </p>
        </div>

        <WordState word={word} />
        <Button variant="ghost" size="sm" className="-ml-2" onClick={onClear}>
          <Eraser className="mr-1 h-4 w-4" />
          Effacer le mot
        </Button>
        {crossing && (
          <div className="border-t pt-2">
            <p className="text-xs text-muted-foreground">
              Croise <span className="font-mono font-semibold">{crossing.text}</span>
            </p>
            <WordState word={crossing} />
          </div>
        )}
      </div>

      <div className="rounded-lg border p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Mots qui entrent ici
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Motif <span className="font-mono">{suggestions?.pattern ?? "…"}</span> — seuls les mots qui
          laissent les croisements valides sont proposés.
        </p>

        {/* Combler les trous ou repartir de zéro : deux gestes différents, deux listes différentes */}
        <div className="mt-2 flex w-fit gap-1 rounded-md border p-1">
          <Toggle size="sm" pressed={keepLetters} onPressedChange={() => setKeepLetters(true)}>
            <PenLine className="mr-1 h-3.5 w-3.5" />
            Combler les trous
          </Toggle>
          <Toggle size="sm" pressed={!keepLetters} onPressedChange={() => setKeepLetters(false)}>
            Remplacer le mot
          </Toggle>
        </div>

        {isLoading ? (
          <p className="mt-3 text-sm text-muted-foreground">Recherche…</p>
        ) : suggestions?.words.length ? (
          <>
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {suggestions.words.map((candidate) => (
                <li key={candidate}>
                  <button
                    type="button"
                    onClick={() => onReplace(candidate)}
                    disabled={candidate === word.text}
                    className="rounded-full bg-secondary px-2.5 py-1 font-mono text-sm font-semibold hover:bg-secondary/70 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {candidate}
                  </button>
                </li>
              ))}
            </ul>
            {suggestions.truncated && (
              <p className="mt-2 text-xs text-muted-foreground">
                Les plus courants d&apos;abord ; la liste est plus longue.
              </p>
            )}
          </>
        ) : (
          <p className="mt-3 text-sm text-muted-foreground">
            {keepLetters
              ? "Aucun mot du lexique ne complète celui-ci tel quel. Effacez d'autres lettres, ou passez à « remplacer le mot »."
              : "Aucun mot du lexique n'entre ici sans casser un croisement. Vous pouvez tout de même écrire le vôtre, lettre par lettre."}
          </p>
        )}
      </div>

      {unknownWords.length > 0 && <UnknownWords words={unknownWords} />}
    </div>
  );
}

function WordState({ word }: { word: PlacedWord }) {
  // Un mot troué n'est pas un mot inconnu : c'est un mot en cours, et c'est le geste de l'auteur
  if (word.complete === false || word.text.includes("?")) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <PenLine className="h-3.5 w-3.5 shrink-0" />
        Inachevé — à combler
      </p>
    );
  }
  if (word.in_lexicon === false) {
    return (
      <p className="flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-500">
        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
        Hors lexique — le mot est posé, à vous de juger.
      </p>
    );
  }
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <Check className="h-3.5 w-3.5 shrink-0" />
      Dans le lexique
      {word.source === "manuel" && " · corrigé à la main"}
    </p>
  );
}

/** Les mots hors lexique de la grille, avec de quoi les adopter d'un geste. */
function UnknownWords({ words }: { words: string[] }) {
  const queryClient = useQueryClient();
  const [target, setTarget] = useState<string | null>(null);

  const { data: dictionaries } = useQuery<Dictionary[], Error>({
    queryKey: ["dictionaries"],
    queryFn: () => apiFetch("/api/dictionaries"),
  });

  const chosen = target ?? String(dictionaries?.find((d) => d.is_active)?.id ?? dictionaries?.[0]?.id ?? "");

  const add = useMutation({
    mutationFn: (word: string) =>
      apiFetch(`/api/dictionaries/${chosen}/words`, { method: "POST", body: { mot: word } }),
    onSuccess: (_data, word) => {
      const name = dictionaries?.find((d) => String(d.id) === chosen)?.name ?? "votre dictionnaire";
      toast.success(`« ${word} » ajouté à ${name}.`);
      queryClient.invalidateQueries({ queryKey: ["saved-grids"] });
      queryClient.invalidateQueries({ queryKey: ["dictionaries"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <div className="space-y-2 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-500">
        Hors lexique dans cette grille
      </p>
      <p className="text-xs text-muted-foreground">
        Rien ne vous empêche de les garder. S&apos;ils sont bons, rangez-les : ils serviront aux
        prochaines grilles et à la recherche.
      </p>

      {dictionaries && dictionaries.length > 1 && (
        <Select value={chosen} onValueChange={setTarget}>
          <SelectTrigger className="h-8 text-xs" aria-label="Dictionnaire où ranger le mot">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {dictionaries.map((dictionary) => (
              <SelectItem key={dictionary.id} value={String(dictionary.id)}>
                {dictionary.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      <ul className="space-y-1">
        {words.map((word) => (
          <li key={word} className="flex items-center justify-between gap-2">
            <span className="font-mono text-sm font-semibold">{word}</span>
            <Button
              variant="ghost"
              size="sm"
              disabled={add.isPending || !chosen}
              onClick={() => add.mutate(word)}
            >
              <BookPlus className="mr-1 h-3.5 w-3.5" />
              Ajouter
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}

const sameWord = (a: PlacedWord | null, b: PlacedWord) =>
  Boolean(a) && a!.x === b.x && a!.y === b.y && a!.direction === b.direction;

/**
 * La relecture, mot par mot : la grille entière en liste, avec ce que le lexique dit de chacun.
 *
 * C'est la première étape d'une grille conservée — on ne définit pas un mot qu'on va remplacer.
 * Les mots à regarder de près (hors lexique, inachevés) remontent en tête.
 */
export function WordReview({
  words,
  current,
  onPick,
}: {
  words: PlacedWord[];
  current: PlacedWord | null;
  onPick: (word: PlacedWord) => void;
}) {
  const ordered = useMemo(() => {
    const rank = (word: PlacedWord) =>
      word.complete === false || word.text.includes("?") ? 0 : word.in_lexicon === false ? 1 : 2;
    return [...words].sort(
      (a, b) =>
        rank(a) - rank(b) ||
        (a.direction === b.direction ? 0 : a.direction === "across" ? -1 : 1) ||
        a.y - b.y ||
        a.x - b.x,
    );
  }, [words]);

  const toCheck = ordered.filter(
    (word) => word.complete === false || word.text.includes("?") || word.in_lexicon === false,
  ).length;

  return (
    <div className="rounded-lg border p-2">
      <p className="px-2 pt-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Les {words.length} mots de la grille
      </p>
      <p className="px-2 pb-2 text-xs text-muted-foreground">
        {toCheck > 0
          ? `${toCheck} à regarder de près, en tête de liste.`
          : "Tous sont dans le lexique."}
      </p>
      <ul className="space-y-0.5">
        {ordered.map((word) => {
          const unfinished = word.complete === false || word.text.includes("?");
          return (
            <li key={`${word.x}-${word.y}-${word.direction}`}>
              <button
                type="button"
                onClick={() => onPick(word)}
                aria-current={sameWord(current, word) ? "true" : undefined}
                className={`flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-sm hover:bg-secondary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                  sameWord(current, word) ? "bg-secondary" : ""
                }`}
              >
                <span className="flex-1 font-mono font-semibold">{word.text}</span>
                <span className="text-xs text-muted-foreground">
                  {word.direction === "across" ? "→" : "↓"}
                </span>
                {unfinished ? (
                  <PenLine className="h-3.5 w-3.5 text-muted-foreground" aria-label="inachevé" />
                ) : word.in_lexicon === false ? (
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-500" aria-label="hors lexique" />
                ) : (
                  <Check className="h-3.5 w-3.5 text-emerald-600/70" aria-label="dans le lexique" />
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
