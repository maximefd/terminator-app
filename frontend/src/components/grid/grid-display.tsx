"use client";

export type Cell = { x: number; y: number; char: string; is_black: boolean };

export type PlacedWord = {
  text: string;
  x: number;
  y: number;
  direction: "across" | "down";
  /** « must », « wish » ou « common » : d'où vient ce mot */
  source: string;
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
};

const SOURCES: Record<string, { label: string; cell: string; badge: string }> = {
  must: { label: "Obligatoire", cell: "bg-primary/20", badge: "bg-primary/15 text-primary" },
  wish: { label: "Souhaité", cell: "bg-emerald-500/20", badge: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400" },
  common: { label: "Lexique", cell: "", badge: "bg-muted text-muted-foreground" },
};

export function GridDisplay({ gridData }: { gridData: GridData }) {
  // Une case peut appartenir à deux mots : la provenance la plus « voulue » l'emporte à l'affichage
  const priority = ["common", "wish", "must"];
  const origin = new Map<string, string>();
  for (const word of gridData.words) {
    for (let i = 0; i < word.text.length; i += 1) {
      const key = `${word.x + (word.direction === "across" ? i : 0)}-${word.y + (word.direction === "down" ? i : 0)}`;
      const current = origin.get(key);
      if (!current || priority.indexOf(word.source) > priority.indexOf(current)) {
        origin.set(key, word.source);
      }
    }
  }

  const bySource = (source: string) => gridData.words.filter((word) => word.source === source);

  return (
    <div className="w-full space-y-6">
      <div className="flex flex-col items-center">
        <p className="mb-2 text-sm text-muted-foreground">
          {gridData.width}×{gridData.height} · mise en page {gridData.layout} · seed {gridData.seed ?? "—"} ·
          {" "}{gridData.words.length} mots · {Math.round(gridData.wish_ratio * 100)} % de vos mots
        </p>
        <div
          className="grid border-2 border-foreground bg-background"
          style={{
            gridTemplateColumns: `repeat(${gridData.width}, minmax(0, 1fr))`,
            width: "100%",
            maxWidth: "600px",
            aspectRatio: `${gridData.width} / ${gridData.height}`,
          }}
        >
          {gridData.cells.map((cell) => {
            const source = origin.get(`${cell.x}-${cell.y}`);
            return (
              <div
                key={`${cell.x}-${cell.y}`}
                className={`flex select-none items-center justify-center border border-foreground/20 font-bold uppercase
                  ${cell.is_black ? "bg-foreground" : `bg-background text-foreground ${source ? SOURCES[source]?.cell ?? "" : ""}`}`}
                style={{ fontSize: "clamp(0.5rem, 4vw, 1.25rem)" }}
              >
                {!cell.is_black && cell.char}
              </div>
            );
          })}
        </div>
      </div>

      {/* La provenance des mots : c'est ce que l'auteur vient vérifier après avoir imposé des mots */}
      <div className="grid gap-4 sm:grid-cols-3">
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
    </div>
  );
}
