"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ApiError, apiFetch } from "@/lib/api-client";
import { useDebounce } from "@/hooks/use-debounce";
import { GridDisplay, type GridData } from "@/components/grid/grid-display";
import { WordList, type WordEntry } from "@/components/grid/word-list";
import { DifficultyPanel, type Difficulty } from "@/components/grid/difficulty-panel";

type GridFormat = { width: number; height: number; layouts: number };

const formatKey = (format: Pick<GridFormat, "width" | "height">) => `${format.width}x${format.height}`;

const fetchFormats = async (): Promise<GridFormat[]> => (await apiFetch("/api/grids/formats")).formats;

/** Refus de génération : chaque cause mérite sa propre explication, pas un « impossible » commun. */
function FailureNotice({ error }: { error: ApiError }) {
  const data = error.data as {
    reason?: string;
    details?: { word: string; problem: string }[];
    suggested_layouts?: string[];
    unplaced?: string[];
  };

  return (
    <div className="space-y-2 rounded-md border border-destructive/40 bg-destructive/5 p-4">
      <p className="font-medium text-destructive">{error.message}</p>

      {data.reason === "must_words" && (
        <>
          <ul className="space-y-1 text-sm">
            {(data.details ?? []).map((detail) => (
              <li key={detail.word}>
                <span className="font-mono font-semibold">{detail.word}</span> — {detail.problem}
              </li>
            ))}
          </ul>
          <p className="text-sm text-muted-foreground">
            {data.suggested_layouts?.length
              ? `Ces mises en page les accueilleraient : ${data.suggested_layouts.join(", ")}.`
              : "Aucune mise en page du catalogue ne les accueille : essayez un mot plus court, ou passez-le en souhaité."}
          </p>
        </>
      )}

      {data.reason === "must_words_unplaced" && (
        <p className="text-sm">
          Le solveur n&apos;a pas réussi à placer{" "}
          <span className="font-mono font-semibold">{(data.unplaced ?? []).join(", ")}</span>. Ces mots entrent
          dans la grille, mais aucun croisement ne fonctionne. Relancez pour tenter une autre disposition, ou
          passez-les en souhaités.
        </p>
      )}

      {data.reason === "timeout" && (
        <p className="text-sm">Relancez : chaque tentative suit un chemin différent.</p>
      )}
    </div>
  );
}

export function GridClientLayout() {
  const [entries, setEntries] = useState<WordEntry[]>([]);
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [gridData, setGridData] = useState<GridData | null>(null);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [difficulty, setDifficulty] = useState<Difficulty | null>(null);
  const [isEstimating, setIsEstimating] = useState(false);

  const { data: formats, isLoading: isFormatsLoading, error: formatsError } = useQuery<GridFormat[], Error>({
    queryKey: ["grid-formats"],
    queryFn: fetchFormats,
  });
  const currentFormat = formats?.find((format) => formatKey(format) === selectedFormat) ?? formats?.[0];

  const required = entries.filter((entry) => entry.required).map((entry) => entry.text);
  const wished = entries.filter((entry) => !entry.required).map((entry) => entry.text);
  // Le chiffre ne doit pas sauter à chaque frappe : on attend que la saisie se pose
  const estimateKey = useDebounce(`${required.join(",")}|${currentFormat ? formatKey(currentFormat) : ""}`, 300);

  useEffect(() => {
    const [words, size] = estimateKey.split("|");
    if (!words) {
      setDifficulty(null);
      return;
    }
    let cancelled = false;
    setIsEstimating(true);
    const [width, height] = size ? size.split("x").map(Number) : [];
    apiFetch("/api/grids/difficulty", {
      method: "POST",
      body: { must_words: words.split(","), ...(width ? { size: { width, height } } : {}) },
    })
      .then((data) => { if (!cancelled) setDifficulty(data); })
      .catch(() => { if (!cancelled) setDifficulty(null); })
      .finally(() => { if (!cancelled) setIsEstimating(false); });
    return () => { cancelled = true; };
  }, [estimateKey]);

  const generate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!currentFormat) return;
    setIsGenerating(true);
    setFailure(null);
    setGridData(null);
    try {
      const data = await apiFetch("/api/grids/generate", {
        method: "POST",
        body: {
          size: { width: currentFormat.width, height: currentFormat.height },
          seed: Math.floor(Math.random() * 1_000_000),
          must_words: required,
          wish_words: wished,
        },
      });
      setGridData(data.grid);
    } catch (error) {
      setFailure(error instanceof ApiError
        ? error
        : new ApiError(error instanceof Error ? error.message : "Une erreur inattendue est survenue.", 0, {}));
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="container mx-auto p-4 md:p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">Générer une grille</h1>
        <p className="mt-2 text-muted-foreground">
          Choisissez un format, ajoutez les mots que vous voulez y voir, et lancez la génération.
        </p>
      </div>

      <form onSubmit={generate} className="mx-auto mt-8 max-w-xl space-y-6 rounded-lg border p-6">
        <div className="space-y-2">
          <Label htmlFor="format">Format de grille</Label>
          <Select
            value={currentFormat ? formatKey(currentFormat) : undefined}
            onValueChange={setSelectedFormat}
            disabled={isFormatsLoading || !formats?.length}
          >
            <SelectTrigger id="format" className="w-full">
              <SelectValue placeholder={isFormatsLoading ? "Chargement des formats…" : "Aucun format disponible"} />
            </SelectTrigger>
            <SelectContent>
              {formats?.map((format) => (
                <SelectItem key={formatKey(format)} value={formatKey(format)}>
                  {format.width} × {format.height} ({format.layouts} mise{format.layouts > 1 ? "s" : ""} en page)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {formatsError && <p className="text-xs text-destructive">{formatsError.message}</p>}
        </div>

        <div className="space-y-2">
          <Label>Mots à placer</Label>
          <WordList entries={entries} onChange={setEntries} disabled={isGenerating} />
        </div>

        <DifficultyPanel difficulty={difficulty} isLoading={isEstimating} hasRequiredWords={required.length > 0} />

        <Button type="submit" disabled={isGenerating || !currentFormat} className="w-full">
          {isGenerating ? "Génération en cours…" : "Générer la grille"}
        </Button>
      </form>

      <div className="mt-8 w-full">
        {failure && <div className="mx-auto max-w-xl"><FailureNotice error={failure} /></div>}
        {gridData && <GridDisplay gridData={gridData} />}
      </div>
    </main>
  );
}
