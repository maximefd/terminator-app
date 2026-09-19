"use client";

export type WordDifficulty = {
  word: string;
  length: number;
  rare_letters: string[];
  success_rate: number;
  level: string;
  reasons: string[];
};

export type Difficulty = {
  words: WordDifficulty[];
  success_rate: number;
  level: string;
  measured: boolean;
  hardest: string | null;
  advice: string | null;
  size_class: string | null;
};

const BAR_COLOURS: Record<string, string> = {
  facile: "bg-emerald-500",
  moyen: "bg-amber-500",
  difficile: "bg-orange-500",
  "très difficile": "bg-destructive",
};

type DifficultyPanelProps = {
  difficulty: Difficulty | null;
  isLoading: boolean;
  hasRequiredWords: boolean;
};

export function DifficultyPanel({ difficulty, isLoading, hasRequiredWords }: DifficultyPanelProps) {
  if (!hasRequiredWords) {
    return (
      <p className="text-sm text-muted-foreground">
        Sans mot obligatoire, la grille aboutit presque toujours.
      </p>
    );
  }
  if (!difficulty) {
    return <p className="text-sm text-muted-foreground">{isLoading ? "Estimation…" : null}</p>;
  }

  const percent = Math.round(difficulty.success_rate * 100);
  const colour = BAR_COLOURS[difficulty.level] ?? "bg-muted-foreground";

  return (
    <div className={`space-y-3 rounded-md border p-4 ${isLoading ? "opacity-60" : ""}`}>
      <div>
        <div className="flex items-baseline justify-between">
          <span className="text-sm font-medium">Chances d&apos;obtenir une grille</span>
          <span className="text-2xl font-bold tabular-nums">{percent}&nbsp;%</span>
        </div>
        <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted" aria-hidden="true">
          <div className={`h-full ${colour}`} style={{ width: `${percent}%` }} />
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {difficulty.level}
          {difficulty.size_class ? ` · grille ${difficulty.size_class}` : " · toutes tailles confondues"}
          {difficulty.measured ? "" : " · estimation, ce cas n'a pas été mesuré"}
        </p>
      </div>

      {/* Ce qui coûte, mot par mot : l'auteur doit voir d'où vient le chiffre */}
      {difficulty.words.some((word) => word.reasons.length > 0) && (
        <ul className="space-y-1 text-xs">
          {difficulty.words
            .filter((word) => word.reasons.length > 0)
            .map((word) => (
              <li key={word.word}>
                <span className="font-mono font-semibold">{word.word}</span> — {word.reasons.join(" ; ")}
              </li>
            ))}
        </ul>
      )}

      {difficulty.advice && (
        <p className="rounded bg-muted p-2 text-xs">{difficulty.advice}</p>
      )}
    </div>
  );
}
