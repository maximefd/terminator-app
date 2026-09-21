"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Toggle } from "@/components/ui/toggle";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { useDebounce } from "@/hooks/use-debounce";
import { GridSvg, clueKey, type Clue } from "@/components/grid/grid-svg";
import type { GridData } from "@/components/grid/grid-display";
import { exportJson, exportPdf } from "@/lib/grid-export";

type SavedGrid = {
  id: number;
  name: string;
  grid: GridData & { clues?: Clue[] };
  definitions: Record<string, string>;
};

/**
 * L'éditeur : une grille conservée, ses définitions, et l'export.
 *
 * La grille vierge est rendue en permanence, même quand l'écran montre la solution : c'est elle que
 * le PDF embarque, et un SVG qui n'existe pas au moment de l'export ne se dessine pas.
 */
export function GridEditor({ gridId }: { gridId: number }) {
  const { isAuthenticated, isLoading: isSessionLoading } = useAuth();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"vierge" | "remplie">("vierge");
  const [selected, setSelected] = useState<string | null>(null);
  const [definitions, setDefinitions] = useState<Record<string, string>>({});
  const [isExporting, setExporting] = useState(false);
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
    // `data` change à chaque enregistrement réussi : ne pas le mettre en dépendance, sinon boucle
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

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

  const clues = data.grid.clues ?? [];
  const selectedClue = clues.find((clue) => clueKey(clue) === selected) ?? null;
  const defined = clues.filter((clue) => definitions[clueKey(clue)]).length;

  const setDefinition = (key: string, text: string) =>
    setDefinitions((current) => ({ ...current, [key]: text }));

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
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Button asChild variant="ghost" size="sm" className="-ml-2">
            <Link href="/grids">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Mes grilles
            </Link>
          </Button>
          <h1 className="mt-1 text-2xl font-bold tracking-tight">{data.name}</h1>
          <p className="text-sm text-muted-foreground">
            {defined} définition{defined > 1 ? "s" : ""} sur {clues.length}
            {save.isPending && " · enregistrement…"}
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

      <div className="grid gap-8 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div>
          <div className="mb-3 flex w-fit gap-1 rounded-md border p-1">
            <Toggle size="sm" pressed={mode === "vierge"} onPressedChange={() => setMode("vierge")}>
              Grille vierge
            </Toggle>
            <Toggle size="sm" pressed={mode === "remplie"} onPressedChange={() => setMode("remplie")}>
              Solution
            </Toggle>
          </div>

          {/* La grille vierge reste montée en permanence : c'est elle que le PDF embarque */}
          <div ref={blankRef} className={mode === "vierge" ? "" : "hidden"}>
            <GridSvg
              grid={data.grid}
              mode="vierge"
              definitions={definitions}
              selectedKey={selected}
              onSelect={setSelected}
            />
          </div>
          <div ref={solutionRef} className={mode === "remplie" ? "" : "hidden"} aria-hidden={mode !== "remplie"}>
            <GridSvg grid={data.grid} mode="remplie" definitions={definitions} />
          </div>

          <p className="mt-3 text-sm text-muted-foreground">
            Cliquez une case définition — ou un mot de la liste — puis écrivez sa définition.
          </p>
        </div>

        <div className="space-y-3">
          {selectedClue ? (
            <div className="space-y-2 rounded-lg border p-4">
              <Label htmlFor="definition" className="text-xs uppercase tracking-wide text-muted-foreground">
                {selectedClue.direction === "across" ? "Horizontal" : "Vertical"} · {selectedClue.text.length} lettres
              </Label>
              <p className="font-mono text-lg font-semibold">{selectedClue.text}</p>
              <Input
                id="definition"
                autoFocus
                maxLength={120}
                placeholder="La définition telle qu'elle sera imprimée"
                value={definitions[clueKey(selectedClue)] ?? ""}
                onChange={(event) => setDefinition(clueKey(selectedClue), event.target.value)}
              />
            </div>
          ) : (
            <p className="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
              Aucun mot sélectionné. Choisissez-en un dans la grille ou dans la liste.
            </p>
          )}

          <ul className="max-h-[32rem] space-y-1 overflow-y-auto rounded-lg border p-2">
            {clues.map((clue) => {
              const key = clueKey(clue);
              const text = definitions[key];
              return (
                <li key={key}>
                  <button
                    type="button"
                    onClick={() => setSelected(key)}
                    className={`w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-secondary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      selected === key ? "bg-secondary" : ""
                    }`}
                  >
                    <span className="font-mono font-semibold">{clue.text}</span>{" "}
                    <span className={text ? "text-muted-foreground" : "text-destructive/70"}>
                      {text || "à définir"}
                    </span>
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
