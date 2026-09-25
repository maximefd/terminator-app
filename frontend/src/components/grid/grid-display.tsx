"use client";

import { useState } from "react";
import { Toggle } from "@/components/ui/toggle";
import { GridSvg, type Clue, type GridVariant } from "@/components/grid/grid-svg";

export type Cell = { x: number; y: number; char: string; is_black: boolean };

export type PlacedWord = {
  text: string;
  x: number;
  y: number;
  direction: "across" | "down";
  /** « must », « wish », « common » — ou « manuel » quand l'auteur l'a corrigé lui-même */
  source: string;
  /** Longueur de l'emplacement : le texte peut être troué, elle ne bouge pas. */
  length?: number;
  /** Faux si l'auteur a effacé des lettres : « P?RTE » est un mot en cours, pas un mot inconnu. */
  complete?: boolean;
  /** Connu du lexique ou d'un dictionnaire de l'auteur ; `null` tant que le mot est inachevé. */
  in_lexicon?: boolean | null;
};

export type GridData = {
  width: number;
  height: number;
  layout: string;
  seed: number | null;
  cells: Cell[];
  words: PlacedWord[];
  fill_ratio: number;
  wish_ratio: number;
  must_words: string[];
  /** Où va la définition de chaque mot et par où part sa flèche (#26) */
  clues?: Clue[];
};

const SOURCES: Record<string, { label: string; cell: string; badge: string }> = {
  must: { label: "Obligatoire", cell: "bg-primary/20", badge: "bg-primary/15 text-primary" },
  wish: { label: "Souhaité", cell: "bg-emerald-500/20", badge: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400" },
  common: { label: "Lexique", cell: "", badge: "bg-muted text-muted-foreground" },
};

/**
 * `unplaced` : les mots souhaités restés sans place. Ils se lisent **après** ce que la grille contient,
 * discrètement, avec les mots de la grille : l'écran montre d'abord ce qui a réussi.
 */
export function GridDisplay({ gridData, unplaced = [] }: { gridData: GridData; unplaced?: string[] }) {
  const [variant, setVariant] = useState<GridVariant>("solution");

  // Une case peut appartenir à deux mots : la provenance la plus « voulue » l'emporte à l'affichage
  const priority = ["common", "wish", "must"];
  const origin: Record<string, string> = {};
  for (const word of gridData.words) {
    for (let i = 0; i < word.text.length; i += 1) {
      const key = `${word.x + (word.direction === "across" ? i : 0)}-${word.y + (word.direction === "down" ? i : 0)}`;
      const current = origin[key];
      if (!current || priority.indexOf(word.source) > priority.indexOf(current)) {
        origin[key] = word.source;
      }
    }
  }

  const bySource = (source: string) => gridData.words.filter((word) => word.source === source);
  const mine = gridData.words.filter((word) => word.source === "must" || word.source === "wish");

  return (
    <div className="w-full space-y-6">
      <div className="flex flex-col items-center">
        {/* Mise en page et seed n'intéressent que celui qui règle le moteur : au survol, pas en titre */}
        <p
          className="mb-2 text-sm text-muted-foreground"
          title={`Mise en page ${gridData.layout} · seed ${gridData.seed ?? "—"}`}
        >
          {gridData.width} × {gridData.height} · {gridData.words.length} mots
          {mine.length > 0 && ` · dont ${mine.length} des vôtres`}
        </p>

        {/* La grille vierge est celle qu'on imprime ; la solution, celle qu'on relit */}
        <div className="mb-3 flex gap-1 rounded-md border p-1">
          <Toggle size="sm" pressed={variant === "solution"} onPressedChange={() => setVariant("solution")}>
            Solution
          </Toggle>
          <Toggle size="sm" pressed={variant === "vierge"} onPressedChange={() => setVariant("vierge")}>
            Grille vierge
          </Toggle>
        </div>

        {/* La grille se voit en entier : une grande mise en page ne doit pas obliger à défiler */}
        <div className="flex w-full max-w-2xl justify-center">
          <GridSvg
            grid={gridData}
            variant={variant}
            cellSources={origin}
            className="max-h-[80vh] w-auto max-w-full"
          />
        </div>
      </div>

      {/*
        La provenance des mots : c'est ce que l'auteur vient vérifier après avoir imposé des mots.
        Repliée : sans mot imposé, ce n'est qu'une longue liste, et la relecture se fait ensuite, mot
        par mot, dans l'éditeur.
      */}
      <details className="rounded-md border p-3" open={mine.length > 0 || unplaced.length > 0}>
        <summary className="cursor-pointer text-sm font-medium">Les mots de la grille</summary>
        <div className="mt-3 grid gap-4 sm:grid-cols-3">
          {["must", "wish", "common"].map((source) => {
            const words = bySource(source);
            if (words.length === 0) return null;
            return (
              <div key={source}>
                <p className={`mb-2 inline-block rounded-full px-2 py-1 text-xs font-semibold ${SOURCES[source].badge}`}>
                  {SOURCES[source].label} · {words.length}
                </p>
                <ul className="space-y-1 font-mono text-sm">
                  {words.map((word) => (
                    <li key={`${word.text}-${word.x}-${word.y}`}>{word.text}</li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
        {unplaced.length > 0 && (
          <p className="mt-4 border-t pt-3 text-xs text-muted-foreground">
            Sans place dans cette grille :{" "}
            <span className="font-mono">{unplaced.join(", ")}</span>. Une autre génération ou un format
            plus grand leur en laissera peut-être une.
          </p>
        )}
      </details>
    </div>
  );
}
