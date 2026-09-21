"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, ArrowLeft, Check, Download, FileText, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Toggle } from "@/components/ui/toggle";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { useDebounce } from "@/hooks/use-debounce";
import { GridSvg, clueKey, wrapDefinition, type Clue } from "@/components/grid/grid-svg";
import { LetterPanel, type PlacedWord } from "@/components/grid/letter-panel";
import type { GridData } from "@/components/grid/grid-display";
import { exportJson, exportPdf } from "@/lib/grid-export";

type GridContent = GridData & { clues?: Clue[]; words: PlacedWord[]; unknown_words?: string[] };

type SavedGrid = {
  id: number;
  name: string;
  grid: GridContent;
  definitions: Record<string, string>;
  notes: string;
  archived: boolean;
};

type Mode = "definitions" | "lettres" | "apercu";

/**
 * L'éditeur d'une grille conservée : définitions, lettres, notes, export.
 *
 * Les définitions s'écrivent **sur la grille remplie** — définir un mot qu'on ne voit pas n'a pas de
 * sens. La grille vierge et la solution sont rendues en même temps, hors cadre : ce sont elles qui
 * partent au PDF, et un SVG absent au moment de l'export ne se dessine pas.
 */
export function GridEditor({ gridId }: { gridId: number }) {
  const { isAuthenticated, isLoading: isSessionLoading } = useAuth();
  const queryClient = useQueryClient();

  const [mode, setMode] = useState<Mode>("definitions");
  const [selected, setSelected] = useState<string | null>(null);
  const [definitions, setDefinitions] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState("");
  const [content, setContent] = useState<GridContent | null>(null);
  const [cursor, setCursor] = useState<{ x: number; y: number } | null>(null);
  const [direction, setDirection] = useState<"across" | "down">("across");
  const [draftName, setDraftName] = useState<string | null>(null);
  const [isExporting, setExporting] = useState(false);
  const [bold, setBold] = useState(true);

  const inputRef = useRef<HTMLInputElement>(null);
  const blankRef = useRef<HTMLDivElement>(null);
  const solutionRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, error } = useQuery<SavedGrid, Error>({
    queryKey: ["saved-grids", gridId],
    queryFn: () => apiFetch(`/api/grids/${gridId}`),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (!data) return;
    setDefinitions(data.definitions ?? {});
    setNotes(data.notes ?? "");
    setContent(data.grid);
  }, [data]);

  useEffect(() => {
    try {
      setBold(localStorage.getItem("terminator:definitions-grasses") !== "non");
    } catch {
      // Stockage refusé (navigation privée) : on garde la valeur par défaut
    }
  }, []);

  const changeBold = (next: boolean) => {
    setBold(next);
    try {
      localStorage.setItem("terminator:definitions-grasses", next ? "oui" : "non");
    } catch {
      // Sans stockage, le réglage ne survit pas au rechargement : pas une raison d'échouer
    }
  };

  const patch = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiFetch(`/api/grids/${gridId}`, { method: "PATCH", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-grids"] }),
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });
  const patchRef = useRef(patch);
  patchRef.current = patch;

  // Enregistrement au fil de la frappe, définitions et notes : rien à cliquer, rien à perdre
  const pending = JSON.stringify({ definitions, notes });
  const settled = useDebounce(pending, 600);
  useEffect(() => {
    if (!data) return;
    if (settled === JSON.stringify({ definitions: data.definitions ?? {}, notes: data.notes ?? "" })) return;
    patchRef.current.mutate(JSON.parse(settled));
    // `data` change à chaque enregistrement réussi : le mettre en dépendance relancerait la boucle
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settled]);

  /** Ordre de travail : celui de la lecture d'une grille, et la moitié haute avant la basse. */
  const clues = useMemo(() => {
    const list = [...(content?.clues ?? [])];
    list.sort((a, b) =>
      (a.cell_y ?? 0) - (b.cell_y ?? 0) ||
      (a.cell_x ?? 0) - (b.cell_x ?? 0) ||
      (a.exit === "right" ? 0 : 1) - (b.exit === "right" ? 0 : 1),
    );
    return list;
  }, [content]);

  useEffect(() => {
    if (!selected && clues.length > 0) setSelected(clueKey(clues[0]));
  }, [clues, selected]);

  // Sur une grande grille, le mot suivant tombe souvent hors écran : on le ramène sans sautiller
  useEffect(() => {
    if (!selected) return;
    document.querySelector(`[data-clue="${CSS.escape(selected)}"]`)?.scrollIntoView({ block: "nearest" });
    document.querySelector(`[data-clue-row="${CSS.escape(selected)}"]`)?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  const move = useCallback(
    (step: number) => {
      if (clues.length === 0) return;
      const index = clues.findIndex((clue) => clueKey(clue) === selected);
      setSelected(clueKey(clues[(index + step + clues.length) % clues.length]));
      inputRef.current?.focus();
    },
    [clues, selected],
  );

  /** Le mot qui passe par une case dans un sens donné, tel que le serveur l'a recalculé. */
  const wordAt = useCallback(
    (cell: { x: number; y: number } | null, wanted: "across" | "down"): PlacedWord | null => {
      if (!cell || !content) return null;
      return (
        content.words.find((word) => {
          if (word.direction !== wanted) return false;
          const length = word.text.length;
          return wanted === "across"
            ? word.y === cell.y && cell.x >= word.x && cell.x < word.x + length
            : word.x === cell.x && cell.y >= word.y && cell.y < word.y + length;
        }) ?? null
      );
    },
    [content],
  );

  const currentWord = wordAt(cursor, direction);
  const crossingWord = wordAt(cursor, direction === "across" ? "down" : "across");
  const litCells = currentWord
    ? Array.from({ length: currentWord.text.length }, (_, i) =>
        currentWord.direction === "across"
          ? `${currentWord.x + i}-${currentWord.y}`
          : `${currentWord.x}-${currentWord.y + i}`,
      )
    : [];

  /** Les cases des mots hors lexique : elles se soulignent dans la grille. */
  const unknownCells = useMemo(() => {
    if (!content) return [];
    return content.words
      .filter((word) => word.in_lexicon === false)
      .flatMap((word) =>
        Array.from({ length: word.text.length }, (_, i) =>
          word.direction === "across" ? `${word.x + i}-${word.y}` : `${word.x}-${word.y + i}`,
        ),
      );
  }, [content]);

  const writeLetters = async (cells: { x: number; y: number; char: string }[]) => {
    try {
      const updated = await apiFetch(`/api/grids/${gridId}`, { method: "PATCH", body: { cells } });
      setContent(updated.grid);
      queryClient.invalidateQueries({ queryKey: ["saved-grids"] });
    } catch (writeError) {
      toast.error(writeError instanceof Error ? writeError.message : "La lettre n'a pas pu être posée.");
    }
  };

  const selectCell = (cell: { x: number; y: number }) => {
    // Un second clic sur la même case change de sens : c'est le geste des grilles croisées
    if (cursor && cursor.x === cell.x && cursor.y === cell.y) {
      setDirection((previous) => (previous === "across" ? "down" : "across"));
    } else {
      setCursor(cell);
    }
  };

  const onLetterKey = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (!cursor || !content) return;
    const isLetter = /^[a-zA-ZàâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ]$/.test(event.key);
    const inGrid = (cell: { x: number; y: number }) =>
      content.cells.some((candidate) => candidate.x === cell.x && candidate.y === cell.y && !candidate.is_black);

    if (isLetter) {
      event.preventDefault();
      // Le moteur travaille en majuscules sans accent : on y ramène la frappe
      const char = event.key.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase();
      void writeLetters([{ x: cursor.x, y: cursor.y, char }]);
      const next =
        direction === "across" ? { x: cursor.x + 1, y: cursor.y } : { x: cursor.x, y: cursor.y + 1 };
      if (inGrid(next)) setCursor(next);
      return;
    }

    const moves: Record<string, { x: number; y: number }> = {
      ArrowRight: { x: 1, y: 0 },
      ArrowLeft: { x: -1, y: 0 },
      ArrowDown: { x: 0, y: 1 },
      ArrowUp: { x: 0, y: -1 },
    };
    if (moves[event.key]) {
      event.preventDefault();
      const next = { x: cursor.x + moves[event.key].x, y: cursor.y + moves[event.key].y };
      if (inGrid(next)) setCursor(next);
      return;
    }
    if (event.key === "Tab") {
      event.preventDefault();
      setDirection((previous) => (previous === "across" ? "down" : "across"));
    }
  };

  const replaceWord = (word: string) => {
    if (!currentWord) return;
    void writeLetters(
      [...word].map((char, index) => ({
        x: currentWord.direction === "across" ? currentWord.x + index : currentWord.x,
        y: currentWord.direction === "down" ? currentWord.y + index : currentWord.y,
        char,
      })),
    );
  };

  if (isSessionLoading || (isAuthenticated && isLoading)) {
    return <p className="p-8 text-center text-sm text-muted-foreground">Chargement…</p>;
  }
  if (!isAuthenticated) {
    return (
      <main className="container mx-auto max-w-xl p-8 text-center">
        <h1 className="text-2xl font-bold">Cette grille demande un compte</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Les grilles conservées appartiennent à celui qui les a gardées.
        </p>
        <Button asChild className="mt-4" size="sm">
          <Link href="/login">Se connecter</Link>
        </Button>
      </main>
    );
  }
  if (error || !data || !content) {
    return (
      <main className="container mx-auto max-w-xl p-8 text-center">
        <p className="text-sm text-destructive">{error?.message ?? "Grille introuvable."}</p>
        <Button asChild variant="outline" className="mt-4" size="sm">
          <Link href="/grids">Retour à mes grilles</Link>
        </Button>
      </main>
    );
  }

  const selectedClue = clues.find((clue) => clueKey(clue) === selected) ?? null;
  const defined = clues.filter((clue) => definitions[clueKey(clue)]).length;
  const current = selectedClue ? definitions[clueKey(selectedClue)] ?? "" : "";
  const sharesItsCell = (clue: Clue) =>
    clues.some((other) => other !== clue && other.cell_x === clue.cell_x && other.cell_y === clue.cell_y);
  const overflows = (clue: Clue, text: string) =>
    Boolean(text) && wrapDefinition(text, clue.arrow, sharesItsCell(clue), bold).overflow;
  const tooLong = clues.filter((clue) => overflows(clue, definitions[clueKey(clue)] ?? ""));

  const svgOf = (container: HTMLDivElement | null) => container?.querySelector("svg") ?? null;
  const downloadPdf = async (withSolution: boolean) => {
    const blank = svgOf(blankRef.current);
    if (!blank) return;
    setExporting(true);
    try {
      await exportPdf(data.name, blank, withSolution ? svgOf(solutionRef.current) : null);
    } catch (exportError) {
      toast.error(exportError instanceof Error ? exportError.message : "L'export a échoué.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <main className="container mx-auto p-4 md:p-8">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <Button asChild variant="ghost" size="sm" className="-ml-2">
            <Link href="/grids">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Mes grilles
            </Link>
          </Button>
          {draftName === null ? (
            <h1 className="mt-1 flex items-center gap-2 text-2xl font-bold tracking-tight">
              {data.name}
              <button
                type="button"
                aria-label="Renommer la grille"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => setDraftName(data.name)}
              >
                <Pencil className="h-4 w-4" />
              </button>
            </h1>
          ) : (
            <Input
              autoFocus
              className="mt-1 max-w-sm text-xl font-semibold"
              aria-label="Nom de la grille"
              maxLength={100}
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
              onBlur={() => {
                const name = draftName.trim();
                if (name && name !== data.name) patch.mutate({ name });
                setDraftName(null);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") event.currentTarget.blur();
                if (event.key === "Escape") setDraftName(null);
              }}
            />
          )}
          <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span>
              {defined} définition{defined > 1 ? "s" : ""} sur {clues.length}
            </span>
            {content.unknown_words && content.unknown_words.length > 0 && (
              <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-500">
                <AlertTriangle className="h-3.5 w-3.5" />
                {content.unknown_words.length} hors lexique
              </span>
            )}
            {tooLong.length > 0 && (
              <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-500">
                <AlertTriangle className="h-3.5 w-3.5" />
                {tooLong.length} trop longue{tooLong.length > 1 ? "s" : ""}
              </span>
            )}
            {patch.isPending ? (
              <span>· enregistrement…</span>
            ) : (
              <span className="inline-flex items-center gap-1">
                <Check className="h-3.5 w-3.5" />
                enregistré
              </span>
            )}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" disabled={isExporting} onClick={() => downloadPdf(false)}>
            <FileText className="mr-1 h-4 w-4" />
            PDF
          </Button>
          <Button variant="outline" size="sm" disabled={isExporting} onClick={() => downloadPdf(true)}>
            <FileText className="mr-1 h-4 w-4" />
            PDF + solution
          </Button>
          <Button variant="outline" size="sm" onClick={() => exportJson(data.name, content, definitions)}>
            <Download className="mr-1 h-4 w-4" />
            Fichier de travail
          </Button>
        </div>
      </div>

      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div>
          <div className="mb-3 flex w-fit flex-wrap gap-1 rounded-md border p-1">
            <Toggle size="sm" pressed={mode === "definitions"} onPressedChange={() => setMode("definitions")}>
              Définitions
            </Toggle>
            <Toggle size="sm" pressed={mode === "lettres"} onPressedChange={() => setMode("lettres")}>
              Lettres
            </Toggle>
            <Toggle size="sm" pressed={mode === "apercu"} onPressedChange={() => setMode("apercu")}>
              Aperçu imprimé
            </Toggle>
            <span className="mx-1 w-px bg-border" aria-hidden />
            <Toggle size="sm" pressed={bold} onPressedChange={changeBold} aria-label="Définitions en gras">
              Gras
            </Toggle>
          </div>

          {/* Le mode lettres écoute le clavier : c'est la grille elle-même qui prend le focus */}
          <div
            tabIndex={mode === "lettres" ? 0 : -1}
            onKeyDown={mode === "lettres" ? onLetterKey : undefined}
            className="rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={mode === "lettres" ? "Grille, correction des lettres" : undefined}
          >
            {mode === "apercu" ? (
              <GridSvg grid={content} variant="vierge" definitions={definitions} boldDefinitions={bold} />
            ) : mode === "lettres" ? (
              <GridSvg
                grid={content}
                variant="lettres"
                definitions={definitions}
                boldDefinitions={bold}
                selectedCell={cursor}
                onSelectCell={selectCell}
                litCells={litCells}
                unknownCells={unknownCells}
              />
            ) : (
              <GridSvg
                grid={content}
                variant="edition"
                definitions={definitions}
                boldDefinitions={bold}
                selectedKey={selected}
                unknownCells={unknownCells}
                onSelect={(key) => {
                  setSelected(key);
                  inputRef.current?.focus();
                }}
              />
            )}
          </div>

          {mode === "lettres" && (
            <p className="mt-3 text-sm text-muted-foreground">
              Cliquez une case et tapez. <kbd className="rounded border px-1">Tab</kbd> change de sens,
              les flèches déplacent le curseur. Chaque lettre est enregistrée aussitôt.
            </p>
          )}

          {/* Les rendus de l'export : hors cadre mais mis en page, sinon le PDF ne mesure rien */}
          <div ref={blankRef} aria-hidden className="pointer-events-none absolute -left-[9999px] top-0 w-[640px]">
            <GridSvg grid={content} variant="vierge" definitions={definitions} boldDefinitions={bold} />
          </div>
          <div ref={solutionRef} aria-hidden className="pointer-events-none absolute -left-[9999px] top-0 w-[640px]">
            <GridSvg grid={content} variant="solution" />
          </div>
        </div>

        <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          {mode === "lettres" ? (
            <LetterPanel
              gridId={gridId}
              word={currentWord}
              crossing={crossingWord}
              onReplace={replaceWord}
              unknownWords={content.unknown_words ?? []}
            />
          ) : (
            <>
              <div className="rounded-lg border p-4">
                {selectedClue ? (
                  <>
                    <div className="flex items-baseline justify-between gap-2">
                      <p className="font-mono text-xl font-semibold tracking-wide">{selectedClue.text}</p>
                      <p className="text-xs text-muted-foreground">
                        {selectedClue.direction === "across" ? "horizontal" : "vertical"} ·{" "}
                        {selectedClue.text.length} lettres
                      </p>
                    </div>
                    <Input
                      ref={inputRef}
                      aria-label={`Définition de ${selectedClue.text}`}
                      autoFocus
                      maxLength={120}
                      className="mt-2"
                      placeholder="Sa définition, telle qu'elle sera imprimée"
                      value={current}
                      onChange={(event) =>
                        setDefinitions((state) => ({ ...state, [clueKey(selectedClue)]: event.target.value }))
                      }
                      onKeyDown={(event) => {
                        if (event.key === "Tab" || event.key === "Enter") {
                          event.preventDefault();
                          move(event.key === "Tab" && event.shiftKey ? -1 : 1);
                        }
                      }}
                    />
                    <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                      <span>
                        <kbd className="rounded border px-1">Tab</kbd> ou{" "}
                        <kbd className="rounded border px-1">Entrée</kbd> : mot suivant
                      </span>
                      <span>{current.length}/120</span>
                    </div>
                    {overflows(selectedClue, current) && (
                      <p className="mt-2 flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-500">
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                        Trop longue pour la case : la fin sera coupée à l&apos;impression.
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Aucun mot sélectionné. Choisissez-en un dans la grille ou dans la liste.
                  </p>
                )}
              </div>

              <ul className="max-h-[22rem] space-y-0.5 overflow-y-auto rounded-lg border p-2">
                {clues.map((clue) => {
                  const key = clueKey(clue);
                  const text = definitions[key];
                  return (
                    <li key={key} data-clue-row={key}>
                      <button
                        type="button"
                        onClick={() => {
                          setSelected(key);
                          inputRef.current?.focus();
                        }}
                        className={`flex w-full items-baseline gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-secondary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                          selected === key ? "bg-secondary" : ""
                        }`}
                      >
                        <span className="w-24 shrink-0 font-mono font-semibold">{clue.text}</span>
                        <span className={`truncate ${text ? "text-muted-foreground" : "text-destructive/70"}`}>
                          {text || "à définir"}
                        </span>
                        {overflows(clue, text ?? "") && (
                          <AlertTriangle className="ml-auto h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </>
          )}

          {/* Le bloc-notes : les idées viennent avant les définitions, et rarement en une fois */}
          <div className="rounded-lg border p-4">
            <label htmlFor="notes" className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Notes
            </label>
            <textarea
              id="notes"
              rows={5}
              maxLength={5000}
              placeholder="Idées, mots à caser, thème, où vous en êtes…"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              className="mt-2 w-full resize-y rounded-md border bg-transparent p-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Enregistrées avec la grille, comme les définitions.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
