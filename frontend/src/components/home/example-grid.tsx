/**
 * Illustration de la page d'accueil : une grille que le moteur a réellement produite.
 *
 * Sortie de `POST /api/grids/generate` avec la seed 99, le layout 6x7-002, PIANO en mot
 * obligatoire et le tri par fréquence. On ne montre donc pas une grille idéalisée que le
 * logiciel ne saurait pas remplir.
 */
const ROWS = ["#C#E#P", "RAMPER", "#PIANO", "PIETIN", "#T#EVE", "PATERE", "#LESES"];

/** PIANO : le mot imposé, mis en évidence comme dans l'écran de génération. */
const MUST_ROW = 2;
const MUST_COLUMNS = [1, 2, 3, 4, 5];

export function ExampleGrid() {
  return (
    <div
      aria-label="Grille 6 × 7 remplie par le moteur, avec le mot imposé PIANO en évidence"
      role="img"
      className="grid h-full w-auto border-2 border-foreground/80 bg-background"
      style={{ gridTemplateColumns: "repeat(6, minmax(0, 1fr))", aspectRatio: "6 / 7" }}
    >
      {ROWS.flatMap((row, y) =>
        [...row].map((char, x) => {
          const isBlack = char === "#";
          const isMust = y === MUST_ROW && MUST_COLUMNS.includes(x);
          return (
            <div
              key={`${x}-${y}`}
              className={`flex select-none items-center justify-center border border-foreground/20 text-[0.6rem] font-bold uppercase
                ${isBlack ? "bg-foreground" : isMust ? "bg-primary/25 text-foreground" : "text-muted-foreground"}`}
            >
              {isBlack ? "" : char}
            </div>
          );
        }),
      )}
    </div>
  );
}

/** Illustration de la recherche : les cinq premiers des dix mots que `P??LE` renvoie vraiment. */
export function ExamplePattern() {
  return (
    <div className="w-full space-y-2">
      <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 font-mono text-lg tracking-[0.3em]">
        P??LE
      </div>
      <ul className="flex flex-wrap gap-1.5">
        {["PARLE", "PELLE", "PERLE", "POELE", "POULE"].map((word) => (
          <li key={word} className="rounded-full bg-secondary px-2 py-0.5 font-mono text-xs font-semibold">
            {word}
          </li>
        ))}
        <li className="px-1 py-0.5 text-xs text-muted-foreground">+ 5 autres</li>
      </ul>
    </div>
  );
}

/** Illustration des dictionnaires : un thème et ses mots, comme on en saisit un. */
export function ExampleDictionary() {
  return (
    <div className="w-full space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Musique · 18 mots</p>
      <ul className="space-y-1 font-mono text-xs">
        {[
          { word: "SOLFEGE", definition: "L'alphabet du musicien" },
          { word: "TEMPO", definition: "Il donne la cadence" },
          { word: "VALSE", definition: "Elle tourne à trois temps" },
        ].map(({ word, definition }) => (
          <li key={word} className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-semibold">{word}</span>
            <span className="font-sans text-muted-foreground">{definition}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
