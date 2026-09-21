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
import { DictionaryPicker } from "@/components/grid/dictionary-picker";
import { SaveGrid } from "@/components/grid/save-grid";

type GridFormat = { width: number; height: number; layouts: number };

const formatKey = (format: Pick<GridFormat, "width" | "height">) => `${format.width}x${format.height}`;

const fetchFormats = async (): Promise<GridFormat[]> => (await apiFetch("/api/grids/formats")).formats;

/**
 * Ce que veulent dire des échecs répétés, quand l'estimation annonçait mieux.
 *
 * À 66 % par tentative, trois échecs de suite n'arrivent qu'une fois sur 26. Le dire vaut mieux que
 * de laisser l'auteur relancer indéfiniment : la vraie information, c'est que l'estimation — mesurée
 * sur des mots courants du lexique — ne colle pas à ses mots.
 */
function RepeatedFailures({ attempts, rate, hardest }: { attempts: number; rate: number | null; hardest: string | null }) {
  if (attempts < 2) return null;
  const improbable = rate !== null && rate > 0 && rate < 1 ? Math.round(1 / Math.pow(1 - rate, attempts)) : null;

  return (
    <div className="mt-3 space-y-2 border-t border-destructive/20 pt-3 text-sm">
      <p>
        <strong>
          {attempts} tentatives, {attempts} échecs.
        </strong>{" "}
        {improbable !== null && rate !== null
          ? `À ${Math.round(rate * 100)} % par tentative, cela n'arrive qu'une fois sur ${improbable} :` +
            " l'estimation ne colle pas à vos mots."
          : "Relancer encore ne changera probablement rien."}
      </p>
      <p className="text-muted-foreground">
        Ce qui change vraiment les choses, dans l&apos;ordre :
      </p>
      <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
        {hardest && (
          <li>
            passer <span className="font-mono font-semibold">{hardest}</span> en{" "}
            <strong>souhaité</strong> : il sera placé s&apos;il rentre, sans faire échouer la grille ;
          </li>
        )}
        <li>raccourcir : c&apos;est la longueur qui décide, bien plus que le nombre de mots ;</li>
        <li>changer de format : pour des mots longs, une grande grille offre plus d&apos;emplacements.</li>
      </ul>
    </div>
  );
}

/** Refus de génération : chaque cause mérite sa propre explication, pas un « impossible » commun. */
function FailureNotice({
  error,
  attempts,
  rate,
  hardest,
}: {
  error: ApiError;
  attempts: number;
  rate: number | null;
  hardest: string | null;
}) {
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

      <RepeatedFailures attempts={attempts} rate={rate} hardest={hardest} />
    </div>
  );
}

export function GridClientLayout() {
  const [entries, setEntries] = useState<WordEntry[]>([]);
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [dictionaryIds, setDictionaryIds] = useState<number[]>([]);
  const [gridData, setGridData] = useState<GridData | null>(null);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  // Échecs consécutifs pour une même demande : c'est leur répétition qui informe, pas le dernier
  const [failures, setFailures] = useState(0);
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

  // Changer un mot ou le format, c'est une autre demande : les échecs précédents ne la concernent plus
  useEffect(() => setFailures(0), [estimateKey]);

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
          wish_dictionary_ids: dictionaryIds,
        },
      });
      setGridData(data.grid);
      setFailures(0);
    } catch (error) {
      setFailures((count) => count + 1);
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

        <div className="space-y-2">
          <Label>Vos dictionnaires</Label>
          <DictionaryPicker selected={dictionaryIds} onChange={setDictionaryIds} disabled={isGenerating} />
        </div>

        <DifficultyPanel difficulty={difficulty} isLoading={isEstimating} hasRequiredWords={required.length > 0} />

        <Button type="submit" disabled={isGenerating || !currentFormat} className="w-full">
          {isGenerating ? "Génération en cours…" : "Générer la grille"}
        </Button>
      </form>

      <div className="mt-8 w-full">
        {failure && (
          <div className="mx-auto max-w-xl">
            <FailureNotice
              error={failure}
              attempts={failures}
              rate={difficulty?.success_rate ?? null}
              hardest={difficulty?.hardest ?? null}
            />
          </div>
        )}
        {gridData && (
          <div className="space-y-6">
            <GridDisplay gridData={gridData} />
            <SaveGrid grid={gridData} />
          </div>
        )}
      </div>
    </main>
  );
}
