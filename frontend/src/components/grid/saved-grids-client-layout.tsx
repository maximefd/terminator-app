"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { GridDisplay, type GridData } from "@/components/grid/grid-display";

type SavedGrid = {
  id: number;
  name: string;
  layout: string;
  width: number;
  height: number;
  seed: number | null;
  word_count: number;
  must_words: string[];
  date_creation: string | null;
};

const formatDate = (value: string | null) =>
  value ? new Date(value).toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" }) : "";

export function SavedGridsClientLayout() {
  const { isAuthenticated, isLoading: isSessionLoading } = useAuth();
  const queryClient = useQueryClient();
  const [openId, setOpenId] = useState<number | null>(null);

  const { data: grids, isLoading, error } = useQuery<SavedGrid[], Error>({
    queryKey: ["saved-grids"],
    queryFn: () => apiFetch("/api/grids"),
    enabled: isAuthenticated,
  });

  // La grille complète (ses cases) n'est demandée qu'à l'ouverture : la liste n'en a pas besoin
  const { data: opened, isLoading: isOpening } = useQuery<{ grid: GridData }, Error>({
    queryKey: ["saved-grids", openId],
    queryFn: () => apiFetch(`/api/grids/${openId}`),
    enabled: openId !== null,
  });

  const remove = useMutation({
    mutationFn: (id: number) => apiFetch(`/api/grids/${id}`, { method: "DELETE" }),
    onSuccess: (_data, id) => {
      toast.success("Grille supprimée.");
      if (openId === id) setOpenId(null);
      queryClient.invalidateQueries({ queryKey: ["saved-grids"] });
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  return (
    <main className="container mx-auto max-w-3xl p-4 md:p-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Mes grilles</h1>
        <p className="mx-auto mt-2 max-w-xl text-muted-foreground">
          Les grilles que vous avez conservées, telles qu&apos;elles ont été produites.
        </p>
      </div>

      <div className="mt-8 space-y-4">
        {isSessionLoading || (isAuthenticated && isLoading) ? (
          <p className="text-center text-sm text-muted-foreground">Chargement…</p>
        ) : !isAuthenticated ? (
          <div className="rounded-lg border bg-secondary/20 p-6 text-center">
            <h2 className="font-semibold">Un compte est nécessaire ici</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              Conserver une grille demande un endroit où la ranger. Générer, en revanche, marche en invité.
            </p>
            <div className="mt-4 flex flex-col justify-center gap-2 sm:flex-row">
              <Button asChild size="sm">
                <Link href="/register">Créer un compte</Link>
              </Button>
              <Button asChild size="sm" variant="outline">
                <Link href="/grid">Générer une grille</Link>
              </Button>
            </div>
          </div>
        ) : error ? (
          <p className="text-center text-sm text-destructive">{error.message}</p>
        ) : grids?.length === 0 ? (
          <div className="rounded-lg border border-dashed p-6 text-center">
            <p className="text-sm text-muted-foreground">
              Aucune grille conservée pour l&apos;instant. Après une génération, le bouton
              «&nbsp;Conserver cette grille&nbsp;» la range ici.
            </p>
            <Button asChild size="sm" className="mt-4">
              <Link href="/grid">Générer une grille</Link>
            </Button>
          </div>
        ) : (
          grids?.map((grid) => (
            <article key={grid.id} className="rounded-lg border p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <h2 className="font-semibold">{grid.name}</h2>
                  <p className="text-sm text-muted-foreground">
                    {grid.width}×{grid.height} · mise en page {grid.layout} · {grid.word_count} mots
                    {grid.seed !== null && ` · seed ${grid.seed}`}
                    {grid.date_creation && ` · ${formatDate(grid.date_creation)}`}
                  </p>
                  {grid.must_words.length > 0 && (
                    <p className="mt-1 font-mono text-xs text-muted-foreground">
                      Imposés : {grid.must_words.join(", ")}
                    </p>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setOpenId(openId === grid.id ? null : grid.id)}
                  >
                    {openId === grid.id ? "Replier" : "Voir"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label={`Supprimer ${grid.name}`}
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(grid.id)}
                  >
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
              </div>

              {openId === grid.id && (
                <div className="mt-4 border-t pt-4">
                  {isOpening || !opened ? (
                    <p className="text-center text-sm text-muted-foreground">Chargement de la grille…</p>
                  ) : (
                    <GridDisplay gridData={opened.grid} />
                  )}
                </div>
              )}
            </article>
          ))
        )}
      </div>
    </main>
  );
}
