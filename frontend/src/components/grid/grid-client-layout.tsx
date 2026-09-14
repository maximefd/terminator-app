"use client";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch } from "@/lib/api-client"; // On importe notre client API
import { GridDisplay } from "@/components/grid/grid-display";

type GridFormat = {
  width: number;
  height: number;
  layouts: number;
};

const formatKey = (format: Pick<GridFormat, "width" | "height">) => `${format.width}x${format.height}`;

const fetchFormats = async (): Promise<GridFormat[]> => {
  const data = await apiFetch(`/api/grids/formats`);
  return data.formats;
};

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
  const [selectedFormat, setSelectedFormat] = useState<string | null>(null);

  const { data: formats, isLoading: isFormatsLoading, error: formatsError } = useQuery<GridFormat[], Error>({
    queryKey: ["grid-formats"],
    queryFn: fetchFormats,
  });
  // Par défaut, le premier format disponible
  const currentFormat = formats?.find((f) => formatKey(f) === selectedFormat) ?? formats?.[0];

  const handleGenerateGrid = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentFormat) return;
    setIsLoading(true);
    setError(null);
    setGridData(null);

    try {
      // On utilise maintenant apiFetch
      const data = await apiFetch(`/api/grids/generate`, {
        method: "POST",
        body: {
          size: { width: currentFormat.width, height: currentFormat.height },
          use_global: true,
          seed: Math.floor(Math.random() * 1_000_000),
        },
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
        <div className="space-y-2">
          <Label htmlFor="format">Format de grille</Label>
          <Select
            value={currentFormat ? formatKey(currentFormat) : undefined}
            onValueChange={setSelectedFormat}
            disabled={isFormatsLoading || !formats?.length}
          >
            <SelectTrigger id="format" className="w-full">
              <SelectValue placeholder={isFormatsLoading ? "Chargement des formats..." : "Aucun format disponible"} />
            </SelectTrigger>
            <SelectContent>
              {formats?.map((format) => (
                <SelectItem key={formatKey(format)} value={formatKey(format)}>
                  {format.width} × {format.height} ({format.layouts} mise{format.layouts > 1 ? "s" : ""} en page)
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Largeur × hauteur. Seuls les formats disposant d&apos;une mise en page sont proposés.
          </p>
          {formatsError && <p className="text-xs text-destructive">{formatsError.message}</p>}
        </div>
        <Button type="submit" disabled={isLoading || !currentFormat} className="w-full">
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
