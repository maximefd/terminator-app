// DANS src/components/grid/grid-display.tsx

"use client";

type Cell = {
  x: number;
  y: number;
  char: string;
  is_black: boolean;
};

type GridData = {
  width: number;
  height: number;
  cells: Cell[];
  fill_ratio: number;
};

type GridDisplayProps = {
  gridData: GridData;
};

export function GridDisplay({ gridData }: GridDisplayProps) {
  if (!gridData) return null;

  return (
    <div className="w-full flex flex-col items-center">
      <p className="mb-2 text-sm text-muted-foreground">
        Grille de {gridData.width}x{gridData.height} générée (Taux de remplissage: {Math.round(gridData.fill_ratio * 100)}%)
      </p>
      
      {/* NOUVELLE MÉTHODE : On revient à CSS Grid, c'est le bon outil. */}
      <div
        className="grid bg-background" // On retire les bordures et gaps du conteneur
        style={{
          gridTemplateColumns: `repeat(${gridData.width}, minmax(0, 1fr))`,
          width: "100%",
          maxWidth: "600px",
          aspectRatio: `${gridData.width} / ${gridData.height}`,
          // On ajoute une bordure extérieure pour un look fini
          border: "2px solid hsl(var(--foreground))",
        }}
      >
        {gridData.cells.map((cell) => (
          <div
            key={`${cell.x}-${cell.y}`}
            // NOUVELLE STRATÉGIE DE BORDURE : Simple et robuste
            className={`flex items-center justify-center font-bold uppercase select-none border border-foreground/20
              ${cell.is_black ? "bg-foreground" : "bg-background text-foreground"}
            `}
            style={{
              fontSize: 'clamp(0.5rem, 4vw, 1.25rem)', // Taille de police responsive
            }}
          >
            {!cell.is_black && cell.char}
          </div>
        ))}
      </div>
    </div>
  );
}