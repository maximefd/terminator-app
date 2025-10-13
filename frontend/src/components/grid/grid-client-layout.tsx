"use client";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { useState } from "react";
import { getApiBaseUrl } from "@/lib/utils";
import { apiFetch } from "@/lib/api-client"; // On importe notre client API
import { GridDisplay } from "@/components/grid/grid-display";

// On définit des types précis pour nos données
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
  words: {
    text: string;
    x: number;
    y: number;
    direction: "across" | "down";
  }[];
};

export function GridClientLayout() {
  const [gridData, setGridData] = useState<GridData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [width, setWidth] = useState(10);
  const [height, setHeight] = useState(10);

  const handleGenerateGrid = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setGridData(null);

    try {
      // On utilise maintenant apiFetch
      const data = await apiFetch(`${getApiBaseUrl()}/api/grids/generate`, {
        method: "POST",
        body: JSON.stringify({
          size: { width, height },
          use_global: true,
          seed: Math.random(),
        }),
      });
      setGridData(data.grid);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Une erreur inattendue est survenue.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="container mx-auto p-4 md:p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">Générer une Grille</h1>
        <p className="text-muted-foreground mt-2">
          Configurez les options et générez une grille de mots fléchés remplie.
        </p>
      </div>

      <form onSubmit={handleGenerateGrid} className="mt-8 mx-auto max-w-sm space-y-4 rounded-lg border p-6">
        <div className="flex items-center gap-4">
          <div className="flex-1 space-y-2">
            <Label htmlFor="width">Largeur</Label>
            <Input id="width" type="number" value={width} onChange={(e) => setWidth(parseInt(e.target.value, 10) || 4)} min="4" max="20" required />
          </div>
          <div className="flex-1 space-y-2">
            <Label htmlFor="height">Hauteur</Label>
            <Input id="height" type="number" value={height} onChange={(e) => setHeight(parseInt(e.target.value, 10) || 4)} min="4" max="20" required />
          </div>
        </div>
        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? "Génération en cours..." : "Générer la grille"}
        </Button>
      </form>

      <div className="mt-8 w-full">
        {error && <p className="text-destructive text-center">{error}</p>}
        {gridData && <GridDisplay gridData={gridData} />}
      </div>
    </main>
  );
}