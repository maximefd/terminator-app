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
import type { GridData } from "@/components/grid/grid-display";
import { exportJson, exportPdf } from "@/lib/grid-export";

type SavedGrid = {
  id: number;
  name: string;
  grid: GridData & { clues?: Clue[] };
  definitions: Record<string, string>;
};

/**
 * L'éditeur de définitions.
 *
 * On écrit sur la **grille remplie** : définir un mot qu'on ne voit pas n'a pas de sens. La grille
 * vierge et la solution sont rendues en même temps, hors écran — ce sont elles qui partent au PDF,
 * et un SVG absent au moment de l'export ne se dessine pas.
 */
export function GridEditor({ gridId }: { gridId: number }) {
  const { isAuthenticated, isLoading: isSessionLoading } = useAuth();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string | null>(null);
  const [definitions, setDefinitions] = useState<Record<string, string>>({});
  const [isExporting, setExporting] = useState(false);
  const [draftName, setDraftName] = useState<string | null>(null);
  const [preview, setPreview] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const blankRef = useRef<HTMLDivElement>(null);
  const solutionRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, error } = useQuery<SavedGrid, Error>({
    queryKey: ["saved-grids", gridId],
    queryFn: () => apiFetch(`/api/grids/${gridId}`),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (data) setDefinitions(data.definitions ?? {});
  }, [data]);

  const rename = useMutation({
    mutationFn: (name: string) => apiFetch(`/api/grids/${gridId}`, { method: "PATCH", body: { name } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-grids"] }),
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const save = useMutation({
    mutationFn: (next: Record<string, string>) =>
      apiFetch(`/api/grids/${gridId}`, { method: "PATCH", body: { definitions: next } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-grids"] }),
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  // Enregistrement au fil de la frappe : on attend que la saisie se pose, sans bouton à penser
  const serialized = JSON.stringify(definitions);
  const debounced = useDebounce(serialized, 600);
  const saveRef = useRef(save);
  saveRef.current = save;
  useEffect(() => {
    if (!data) return;
    if (debounced === JSON.stringify(data.definitions ?? {})) return;
    saveRef.current.mutate(JSON.parse(debounced));
    // `data` change à chaque enregistrement réussi : le mettre en dépendance relancerait la boucle
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  /**
   * Ordre de travail : celui de la lecture d'une grille — de haut en bas, de gauche à droite, et
   * dans une case qui porte deux définitions, celle du haut avant celle du bas.
   */
  const clues = useMemo(() => {
    const list = [...(data?.grid.clues ?? [])];
    list.sort((a, b) =>
      (a.cell_y ?? 0) - (b.cell_y ?? 0) ||
      (a.cell_x ?? 0) - (b.cell_x ?? 0) ||
      (a.exit === "right" ? 0 : 1) - (b.exit === "right" ? 0 : 1),
    );
    return list;
  }, [data]);

  // Le premier mot est choisi d'office : on arrive et on écrit, sans un clic d'amorçage
  useEffect(() => {
    if (!selected && clues.length > 0) setSelected(clueKey(clues[0]));
  }, [clues, selected]);

  // Sur une grande grille, le mot suivant tombe souvent hors de l'écran : on le ramène, sans
  // bouger quand il est déjà visible (`nearest`), pour que la page ne sautille pas à chaque Tab.
  useEffect(() => {
    if (!selected) return;
    document.querySelector(`[data-clue="${CSS.escape(selected)}"]`)?.scrollIntoView({ block: "nearest" });
    document.querySelector(`[data-clue-row="${CSS.escape(selected)}"]`)?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  const move = useCallback(
    (step: number) => {
      if (clues.length === 0) return;
      const index = clues.findIndex((clue) => clueKey(clue) === selected);
      const next = clues[(index + step + clues.length) % clues.length];
      setSelected(clueKey(next));
      inputRef.current?.focus();
    },
    [clues, selected],
  );

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
  if (error || !data) {
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

  /** Deux définitions dans la même case : chacune n'en occupe que la moitié, donc moitié moins de place. */
  const sharesItsCell = (clue: Clue) =>
    clues.some((other) => other !== clue && other.cell_x === clue.cell_x && other.cell_y === clue.cell_y);
  const overflows = (clue: Clue, text: string) =>
    Boolean(text) && wrapDefinition(text, clue.arrow, sharesItsCell(clue)).overflow;
  const tooLong = clues.filter((clue) => overflows(clue, definitions[clueKey(clue)] ?? ""));

  const setDefinition = (key: string, text: string) =>
    setDefinitions((state) => ({ ...state, [key]: text }));

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    // Tab et Entrée passent au mot suivant : on écrit une grille entière sans lâcher le clavier
    if (event.key === "Tab" || event.key === "Enter") {
      event.preventDefault();
      move(event.key === "Tab" && event.shiftKey ? -1 : 1);
    }
  };

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
                if (name && name !== data.name) rename.mutate(name);
                setDraftName(null);
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") event.currentTarget.blur();
                if (event.key === "Escape") setDraftName(null);
              }}
            />
          )}
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>
              {defined} définition{defined > 1 ? "s" : ""} sur {clues.length}
            </span>
            {tooLong.length > 0 && (
              <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-500">
                <AlertTriangle className="h-3.5 w-3.5" />
                {tooLong.length} trop longue{tooLong.length > 1 ? "s" : ""}
              </span>
            )}
            {save.isPending ? (
              <span>· enregistrement…</span>
            ) : (
              defined > 0 && (
                <span className="inline-flex items-center gap-1">
                  <Check className="h-3.5 w-3.5" />
                  enregistré
                </span>
              )
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
          <Button variant="outline" size="sm" onClick={() => exportJson(data.name, data.grid, definitions)}>
            <Download className="mr-1 h-4 w-4" />
            Fichier de travail
          </Button>
        </div>
      </div>

      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div>
          {/* L'aperçu montre ce qui s'imprime ; on n'y écrit pas, faute de voir les mots à définir */}
          <div className="mb-3 flex w-fit gap-1 rounded-md border p-1">
            <Toggle size="sm" pressed={!preview} onPressedChange={() => setPreview(false)}>
              Édition
            </Toggle>
            <Toggle size="sm" pressed={preview} onPressedChange={() => setPreview(true)}>
              Aperçu imprimé
            </Toggle>
          </div>

          {/* On définit sur la grille remplie : le mot à définir est sous les yeux, en surbrillance */}
          {preview ? (
            <GridSvg grid={data.grid} variant="vierge" definitions={definitions} />
          ) : (
            <GridSvg
              grid={data.grid}
              variant="edition"
              definitions={definitions}
              selectedKey={selected}
              onSelect={(key) => {
                setSelected(key);
                inputRef.current?.focus();
              }}
            />
          )}

          {/*
            Les deux rendus de l'export : hors du champ de vision, mais **mis en page**. Un `display:
            none` suffirait à les cacher et casserait la mesure du texte dont le convertisseur PDF a
            besoin — d'où le renvoi hors cadre plutôt que le masquage.
          */}
          <div ref={blankRef} aria-hidden className="pointer-events-none absolute -left-[9999px] top-0 w-[640px]">
            <GridSvg grid={data.grid} variant="vierge" definitions={definitions} />
          </div>
          <div ref={solutionRef} aria-hidden className="pointer-events-none absolute -left-[9999px] top-0 w-[640px]">
            <GridSvg grid={data.grid} variant="solution" />
          </div>
        </div>

        {/* Le panneau suit la lecture : sur un 13x18, il sortirait de l'écran dès la deuxième rangée */}
        <div className="space-y-4 lg:sticky lg:top-20 lg:self-start">
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
                  onChange={(event) => setDefinition(clueKey(selectedClue), event.target.value)}
                  onKeyDown={onKeyDown}
                />
                <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    <kbd className="rounded border px-1">Tab</kbd> ou{" "}
                    <kbd className="rounded border px-1">Entrée</kbd> : mot suivant
                  </span>
                  <span>{current.length}/120</span>
                </div>
                {/* Une définition rognée à l'impression sans prévenir serait le pire des silences */}
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

          <ul className="max-h-[30rem] space-y-0.5 overflow-y-auto rounded-lg border p-2">
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
        </div>
      </div>
    </main>
  );
}
