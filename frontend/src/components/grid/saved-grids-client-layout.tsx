"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Archive, ArchiveRestore, NotebookPen, Search, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Toggle } from "@/components/ui/toggle";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { GridThumbnail } from "@/components/grid/grid-thumbnail";

type SavedGrid = {
  id: number;
  name: string;
  layout: string;
  width: number;
  height: number;
  seed: number | null;
  word_count: number;
  must_words: string[];
  defined_count: number;
  shape: string[];
  archived: boolean;
  has_notes: boolean;
  date_creation: string | null;
};

type Sort = "recent" | "ancien" | "nom";

const formatDate = (value: string | null) =>
  value ? new Date(value).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" }) : "";

/**
 * Les grilles conservées.
 *
 * Tout est chargé d'un coup et trié dans le navigateur : à l'échelle d'un auteur — quelques
 * centaines de grilles au plus — c'est instantané, et cela évite une requête à chaque frappe dans
 * le champ de recherche. Le jour où cela ne tiendra plus, la pagination se fera côté API.
 */
export function SavedGridsClientLayout() {
  const { isAuthenticated, isLoading: isSessionLoading } = useAuth();
  const queryClient = useQueryClient();

  const [search, setSearch] = useState("");
  const [format, setFormat] = useState("tous");
  const [etat, setEtat] = useState<"tous" | "a-definir" | "completes">("tous");
  const [archivees, setArchivees] = useState(false);
  const [sort, setSort] = useState<Sort>("recent");

  const { data: grids, isLoading, error } = useQuery<SavedGrid[], Error>({
    queryKey: ["saved-grids"],
    queryFn: () => apiFetch("/api/grids"),
    enabled: isAuthenticated,
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      apiFetch(`/api/grids/${id}`, { method: "PATCH", body }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-grids"] }),
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const remove = useMutation({
    mutationFn: (id: number) => apiFetch(`/api/grids/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success("Grille supprimée.");
      queryClient.invalidateQueries({ queryKey: ["saved-grids"] });
    },
    onError: (mutationError: Error) => toast.error(mutationError.message),
  });

  const formats = useMemo(() => {
    const seen = new Map<string, number>();
    for (const grid of grids ?? []) {
      const key = `${grid.width}×${grid.height}`;
      seen.set(key, (seen.get(key) ?? 0) + 1);
    }
    return [...seen.entries()].sort();
  }, [grids]);

  const shown = useMemo(() => {
    const terme = search.trim().toLocaleLowerCase("fr");
    const liste = (grids ?? []).filter((grid) => {
      if (grid.archived !== archivees) return false;
      if (terme && !grid.name.toLocaleLowerCase("fr").includes(terme)) return false;
      if (format !== "tous" && `${grid.width}×${grid.height}` !== format) return false;
      if (etat === "completes" && grid.defined_count < grid.word_count) return false;
      if (etat === "a-definir" && grid.defined_count >= grid.word_count) return false;
      return true;
    });
    return liste.sort((a, b) => {
      if (sort === "nom") return a.name.localeCompare(b.name, "fr");
      const dateA = a.date_creation ?? "";
      const dateB = b.date_creation ?? "";
      return sort === "recent" ? dateB.localeCompare(dateA) : dateA.localeCompare(dateB);
    });
  }, [grids, search, format, etat, archivees, sort]);

  const archivedCount = (grids ?? []).filter((grid) => grid.archived).length;

  return (
    <main className="container mx-auto max-w-5xl p-4 md:p-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Mes grilles</h1>
        <p className="mx-auto mt-2 max-w-xl text-muted-foreground">
          Les grilles que vous avez conservées, telles qu&apos;elles ont été produites — et telles que
          vous les avez corrigées depuis.
        </p>
      </div>

      {isSessionLoading || (isAuthenticated && isLoading) ? (
        <p className="mt-8 text-center text-sm text-muted-foreground">Chargement…</p>
      ) : !isAuthenticated ? (
        <div className="mx-auto mt-8 max-w-xl rounded-lg border bg-secondary/20 p-6 text-center">
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
        <p className="mt-8 text-center text-sm text-destructive">{error.message}</p>
      ) : (grids ?? []).length === 0 ? (
        <div className="mx-auto mt-8 max-w-xl rounded-lg border border-dashed p-6 text-center">
          <p className="text-sm text-muted-foreground">
            Aucune grille conservée pour l&apos;instant. Après une génération, le bouton
            «&nbsp;Conserver cette grille&nbsp;» la range ici.
          </p>
          <Button asChild size="sm" className="mt-4">
            <Link href="/grid">Générer une grille</Link>
          </Button>
        </div>
      ) : (
        <>
          {/* Les filtres : avec cent grilles, une liste à dérouler ne suffit plus */}
          <div className="mt-8 flex flex-wrap items-center gap-2">
            <div className="relative min-w-[14rem] flex-1">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Chercher par nom"
                aria-label="Chercher une grille par son nom"
                className="pl-8"
              />
            </div>

            <Select value={format} onValueChange={setFormat}>
              <SelectTrigger className="w-auto min-w-[9rem]" aria-label="Filtrer par format">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tous">Tous les formats</SelectItem>
                {formats.map(([nom, nombre]) => (
                  <SelectItem key={nom} value={nom}>
                    {nom} ({nombre})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={etat} onValueChange={(value: typeof etat) => setEtat(value)}>
              <SelectTrigger className="w-auto min-w-[10rem]" aria-label="Filtrer par état">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="tous">Tous les états</SelectItem>
                <SelectItem value="a-definir">À définir</SelectItem>
                <SelectItem value="completes">Définitions complètes</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sort} onValueChange={(value: Sort) => setSort(value)}>
              <SelectTrigger className="w-auto min-w-[9rem]" aria-label="Trier">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recent">Plus récentes</SelectItem>
                <SelectItem value="ancien">Plus anciennes</SelectItem>
                <SelectItem value="nom">Par nom</SelectItem>
              </SelectContent>
            </Select>

            <Toggle
              pressed={archivees}
              onPressedChange={setArchivees}
              variant="outline"
              aria-label="Voir les grilles archivées"
            >
              <Archive className="mr-1 h-4 w-4" />
              Archivées ({archivedCount})
            </Toggle>
          </div>

          <p className="mt-3 text-sm text-muted-foreground">
            {shown.length} grille{shown.length > 1 ? "s" : ""}
            {archivees ? " archivée" : ""}
            {shown.length > 1 && archivees ? "s" : ""}
          </p>

          {shown.length === 0 ? (
            <p className="mt-6 rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              Aucune grille ne correspond. Élargissez la recherche ou changez de filtre.
            </p>
          ) : (
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              {shown.map((grid) => {
                const complete = grid.word_count > 0 && grid.defined_count >= grid.word_count;
                const part = grid.word_count ? Math.round((grid.defined_count / grid.word_count) * 100) : 0;
                return (
                  <li key={grid.id} className="flex flex-col rounded-lg border p-4">
                    <div className="flex items-start gap-3">
                      {/*
                        La silhouette : c'est elle qu'on reconnaît quand on en a cent. Une image,
                        pas un lien — un second lien vers la même page, sans intitulé, n'apporterait
                        rien et encombrerait la navigation au clavier.
                      */}
                      <div className="flex h-12 w-11 shrink-0 items-center">
                        <GridThumbnail shape={grid.shape} className="max-h-12" />
                      </div>

                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <Link
                            href={`/grids/${grid.id}`}
                            className="font-semibold hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                          >
                            {grid.name}
                          </Link>
                          {grid.has_notes && (
                            <NotebookPen
                              className="h-4 w-4 shrink-0 text-muted-foreground"
                              aria-label="Contient des notes"
                            />
                          )}
                        </div>

                        <p className="mt-1 text-sm text-muted-foreground">
                          {grid.width}×{grid.height} · {grid.word_count} mots ·{" "}
                          {formatDate(grid.date_creation)}
                        </p>
                      </div>
                    </div>

                    {/* L'avancement des définitions : c'est ce qu'on cherche en revenant sur une grille */}
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>
                          {complete
                            ? "Définitions complètes"
                            : `${grid.defined_count} définition${grid.defined_count > 1 ? "s" : ""} sur ${grid.word_count}`}
                        </span>
                        <span className="tabular-nums">{part} %</span>
                      </div>
                      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
                        <div
                          className={complete ? "h-full bg-emerald-500" : "h-full bg-amber-500"}
                          style={{ width: `${part}%` }}
                        />
                      </div>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      <Button asChild size="sm">
                        <Link href={`/grids/${grid.id}`}>Ouvrir</Link>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={update.isPending}
                        onClick={() => update.mutate({ id: grid.id, body: { archived: !grid.archived } })}
                      >
                        {grid.archived ? (
                          <>
                            <ArchiveRestore className="mr-1 h-4 w-4" />
                            Sortir de l&apos;archive
                          </>
                        ) : (
                          <>
                            <Archive className="mr-1 h-4 w-4" />
                            Archiver
                          </>
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="ml-auto"
                        aria-label={`Supprimer ${grid.name}`}
                        disabled={remove.isPending}
                        onClick={() => remove.mutate(grid.id)}
                      >
                        <Trash2 className="h-4 w-4 text-muted-foreground" />
                      </Button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </main>
  );
}
