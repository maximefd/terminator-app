"use client";

export type WordDifficulty = {
  word: string;
  length: number;
  rare_letters: string[];
  success_rate: number;
  level: string;
  reasons: string[];
  in_lexicon: boolean;
};

export type Difficulty = {
  words: WordDifficulty[];
  success_rate: number;
  level: string;
  measured: boolean;
  hardest: string | null;
  advice: string | null;
  size_class: string | null;
  unknown_words: string[];
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
          <span className="text-sm font-medium">Chances par tentative</span>
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

      {/* Un mot hors lexique se place, mais aucun autre mot hors lexique ne peut le croiser */}
      {difficulty.unknown_words?.length > 0 && (
        <p className="text-xs text-muted-foreground">
          <span className="font-mono font-semibold">{difficulty.unknown_words.join(", ")}</span>{" "}
          {difficulty.unknown_words.length > 1 ? "ne sont pas" : "n'est pas"} dans le lexique. Le moteur
          {difficulty.unknown_words.length > 1 ? " les placera" : " le placera"} quand même, mais chacun de
          {difficulty.unknown_words.length > 1 ? " leurs" : " ses"} croisements devra tomber sur un mot du
          lexique : c&apos;est plus contraint que l&apos;estimation ci-dessus ne le suppose.
        </p>
      )}

      {difficulty.advice && <p className="rounded bg-muted p-2 text-xs">{difficulty.advice}</p>}

      {/* D'où sort le chiffre : sans quoi 66 % se lit comme une promesse */}
      <p className="border-t pt-2 text-xs text-muted-foreground">
        Chiffre mesuré sur 4 700 générations, avec des mots courants tirés du lexique. Chaque tentative
        est indépendante : relancer change de tirage, mais deux échecs de suite sur une demande annoncée
        facile veulent dire que vos mots sont plus durs que ceux de la mesure.
      </p>
    </div>
  );
}
