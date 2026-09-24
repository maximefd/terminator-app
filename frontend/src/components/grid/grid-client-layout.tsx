"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { ChevronDown, Grid3x3, Loader2, RefreshCw } from "lucide-react";
import { ApiError, apiFetch } from "@/lib/api-client";
import { useDebounce } from "@/hooks/use-debounce";
import { GridDisplay, type GridData } from "@/components/grid/grid-display";
import { WordList, type WordEntry } from "@/components/grid/word-list";
import { DifficultyPanel, type Difficulty } from "@/components/grid/difficulty-panel";
import { DictionaryPicker } from "@/components/grid/dictionary-picker";
import { SaveGrid, type SavedRef } from "@/components/grid/save-grid";
import { loadLastGrid, storeLastGrid } from "@/lib/last-grid";

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
            décocher « Obligatoire » pour <span className="font-mono font-semibold">{hardest}</span> : il
            sera placé s&apos;il rentre, sans faire échouer la grille ;
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
              : "Aucune mise en page du catalogue ne les accueille : essayez un mot plus court, ou décochez « Obligatoire »."}
          </p>
        </>
      )}

      {data.reason === "must_words_unplaced" && (
        <p className="text-sm">
          Le solveur n&apos;a pas réussi à placer{" "}
          <span className="font-mono font-semibold">{(data.unplaced ?? []).join(", ")}</span>. Ces mots entrent
          dans la grille, mais aucun croisement ne fonctionne. Relancez pour tenter une autre disposition, ou
          décochez « Obligatoire ».
        </p>
      )}

      {data.reason === "timeout" && (
        <p className="text-sm">Relancez : chaque tentative suit un chemin différent.</p>
      )}

      <RepeatedFailures attempts={attempts} rate={rate} hardest={hardest} />
    </div>
  );
}

/** Trois familles de tailles : on choisit d'abord « petite ou grande », le détail ensuite. */
const SIZE_GROUPS = [
  { label: "Petites", upTo: 70 },
  { label: "Moyennes", upTo: 140 },
  { label: "Grandes", upTo: Number.POSITIVE_INFINITY },
];

/**
 * Le choix du format, en vignettes plutôt qu'en liste déroulante : la silhouette d'une grille dit
 * mieux sa taille que « 13 × 16 (4 mises en page) ». Des boutons radio natifs, masqués : les flèches
 * du clavier passent d'un format à l'autre sans rien à coder.
 */
function FormatPicker({
  formats,
  value,
  onChange,
  disabled,
}: {
  formats: GridFormat[];
  value: string | null;
  onChange: (key: string) => void;
  disabled?: boolean;
}) {
  const sorted = [...formats].sort((a, b) => a.width * a.height - b.width * b.height);
  let lower = 0;
  const groups = SIZE_GROUPS.map((group) => {
    const members = sorted.filter((format) => format.width * format.height > lower && format.width * format.height <= group.upTo);
    lower = group.upTo;
    return { ...group, members };
  }).filter((group) => group.members.length > 0);
  const largest = Math.max(...formats.map((format) => Math.max(format.width, format.height)));

  return (
    <div role="radiogroup" aria-label="Taille de la grille" className="space-y-3">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="mb-1.5 text-xs font-medium text-muted-foreground">{group.label}</p>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 lg:grid-cols-3">
            {group.members.map((format) => {
              const key = formatKey(format);
              const scale = 22 / largest;
              return (
                <label key={key} className="relative" title={`${format.layouts} mise${format.layouts > 1 ? "s" : ""} en page`}>
                  <input
                    type="radio"
                    name="format"
                    value={key}
                    checked={value === key}
                    onChange={() => onChange(key)}
                    disabled={disabled}
                    className="peer sr-only"
                  />
                  <span className="flex h-11 cursor-pointer items-center justify-center gap-2 rounded-md border px-2 text-sm tabular-nums transition-colors hover:bg-secondary/60 peer-checked:border-primary peer-checked:bg-primary/10 peer-checked:font-semibold peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-disabled:cursor-not-allowed peer-disabled:opacity-50">
                    <span
                      aria-hidden
                      className="inline-block rounded-[2px] border border-current opacity-60"
                      style={{ width: format.width * scale + 4, height: format.height * scale + 4 }}
                    />
                    {format.width}&nbsp;×&nbsp;{format.height}
                  </span>
                </label>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * L'écran de génération.
 *
 * Pensé pour quelqu'un qui arrive sans rien savoir : une taille, un bouton, une grille. Imposer des
 * mots reste possible, mais c'est une **option**, repliée par défaut — l'ancien écran ouvrait sur la
 * liste de mots et laissait croire qu'il fallait la remplir.
 *
 * La demande et la dernière grille sont gardées dans le navigateur (`last-grid`) : on peut aller se
 * connecter et revenir la conserver.
 */
export function GridClientLayout() {
  const [entries, setEntries] = useState<WordEntry[]>([]);
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);
  const [dictionaryIds, setDictionaryIds] = useState<number[]>([]);
  const [gridData, setGridData] = useState<GridData | null>(null);
  const [saved, setSaved] = useState<SavedRef | null>(null);
  // Les mots demandés que le moteur n'a pas pu placer : un souhaité absent doit se voir
  const [unplaced, setUnplaced] = useState<string[]>([]);
  const [showWords, setShowWords] = useState(false);
  const [restored, setRestored] = useState(false);
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  // Échecs consécutifs pour une même demande : c'est leur répétition qui informe, pas le dernier
  const [failures, setFailures] = useState(0);
  const [difficulty, setDifficulty] = useState<Difficulty | null>(null);
  const [isEstimating, setIsEstimating] = useState(false);
  const resultRef = useRef<HTMLElement>(null);

  // Lu après le montage : le stockage n'existe pas au rendu statique, et l'y lire casserait l'hydratation
  useEffect(() => {
    const last = loadLastGrid();
    if (last) {
      setSelectedFormat(last.format);
      setEntries(last.entries);
      setDictionaryIds(last.dictionaryIds);
      setGridData(last.grid);
      setSaved(last.saved);
      setShowWords(last.entries.length > 0 || last.dictionaryIds.length > 0);
    }
    setRestored(true);
  }, []);

  useEffect(() => {
    // Avant la lecture, ce serait écraser la grille gardée par un écran encore vide
    if (!restored) return;
    storeLastGrid({ format: selectedFormat, entries, dictionaryIds, grid: gridData, saved });
  }, [restored, selectedFormat, entries, dictionaryIds, gridData, saved]);

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
    setSaved(null);
    setUnplaced([]);
    // Sur téléphone, le résultat tombe sous le formulaire : on l'amène à l'écran. Sur grand écran il
    // est déjà à côté, et faire défiler cacherait le titre.
    if (window.matchMedia("(max-width: 1023px)").matches) {
      resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
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
      // Le moteur écrit sans accent ni tiret : ARC-EN-CIEL est placé sous la forme ARCENCIEL
      const plain = (word: string) => word.normalize("NFD").replace(/[^A-Za-z]/g, "").toUpperCase();
      setUnplaced(
        wished.filter((word) => !(data.grid as GridData).words.some((placed) => plain(placed.text) === plain(word))),
      );
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

  const imposed = entries.length + dictionaryIds.length;

  return (
    <main className="container mx-auto p-4 md:p-8">
      <div className="max-w-2xl">
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Générer une grille</h1>
        <p className="mt-2 text-muted-foreground">
          Choisissez une taille : le moteur remplit la grille en quelques secondes. Vous relirez ensuite
          ses mots et écrirez les définitions.
        </p>
      </div>

      <div className="mt-8 grid items-start gap-8 lg:grid-cols-[minmax(0,400px)_minmax(0,1fr)]">
        <form onSubmit={generate} className="space-y-6 rounded-lg border p-5">
          <section className="space-y-3">
            <h2 className="text-sm font-semibold">Taille de la grille</h2>
            {formats?.length ? (
              <FormatPicker
                formats={formats}
                value={currentFormat ? formatKey(currentFormat) : null}
                onChange={setSelectedFormat}
                disabled={isGenerating}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                {isFormatsLoading ? "Chargement des formats…" : "Aucun format disponible."}
              </p>
            )}
            {formatsError && <p className="text-xs text-destructive">{formatsError.message}</p>}
          </section>

          {/* L'option repliée : sans elle, la grille se remplit seule, et c'est le cas courant */}
          <section className="border-t pt-4">
            <button
              type="button"
              aria-expanded={showWords}
              aria-controls="imposed-words"
              onClick={() => setShowWords((open) => !open)}
              className="flex w-full items-center justify-between gap-2 rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span>
                <span className="block text-sm font-semibold">
                  Imposer des mots
                  <span className="ml-1.5 font-normal text-muted-foreground">(facultatif)</span>
                </span>
                <span className="block text-xs text-muted-foreground">
                  {imposed > 0
                    ? `${entries.length} mot${entries.length > 1 ? "s" : ""}${
                        dictionaryIds.length ? ` · ${dictionaryIds.length} dictionnaire${dictionaryIds.length > 1 ? "s" : ""}` : ""
                      }`
                    : "Un thème, des prénoms… Sinon, le moteur choisit tout seul."}
                </span>
              </span>
              <ChevronDown className={`h-4 w-4 shrink-0 transition-transform ${showWords ? "rotate-180" : ""}`} />
            </button>

            {showWords && (
              <div id="imposed-words" className="mt-4 space-y-5">
                <WordList entries={entries} onChange={setEntries} disabled={isGenerating} />
                <div className="space-y-2">
                  <p className="text-sm font-medium">Puiser dans vos dictionnaires</p>
                  <DictionaryPicker selected={dictionaryIds} onChange={setDictionaryIds} disabled={isGenerating} />
                </div>
                {required.length > 0 && (
                  <DifficultyPanel difficulty={difficulty} isLoading={isEstimating} hasRequiredWords />
                )}
              </div>
            )}
          </section>

          <Button type="submit" size="lg" disabled={isGenerating || !currentFormat} className="w-full">
            {isGenerating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Génération en cours…
              </>
            ) : gridData ? (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                Générer une autre grille
              </>
            ) : (
              "Générer la grille"
            )}
          </Button>
        </form>

        <section ref={resultRef} aria-label="Grille générée" aria-live="polite" className="scroll-mt-20">
          {failure && (
            <FailureNotice
              error={failure}
              attempts={failures}
              rate={difficulty?.success_rate ?? null}
              hardest={difficulty?.hardest ?? null}
            />
          )}
          {gridData ? (
            <div className="space-y-6">
              <SaveGrid grid={gridData} saved={saved} onSaved={setSaved} />
              {unplaced.length > 0 && (
                <p className="text-center text-sm text-muted-foreground">
                  Pas de place pour{" "}
                  <span className="font-mono font-semibold">{unplaced.join(", ")}</span> dans cette
                  grille : relancez, ou essayez un format plus grand.
                </p>
              )}
              <GridDisplay gridData={gridData} />
            </div>
          ) : (
            !failure && (
              <div className="flex min-h-[320px] flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center text-muted-foreground">
                {isGenerating ? (
                  <>
                    <Loader2 className="h-6 w-6 animate-spin" />
                    <p className="mt-3 text-sm">Le moteur cherche des mots qui se croisent…</p>
                  </>
                ) : (
                  <>
                    <Grid3x3 className="h-8 w-8 opacity-40" />
                    <p className="mt-3 text-sm">Votre grille apparaîtra ici.</p>
                  </>
                )}
              </div>
            )
          )}
        </section>
      </div>
    </main>
  );
}
