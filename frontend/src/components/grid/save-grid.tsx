"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import { withNext } from "@/lib/next-path";
import type { GridData } from "@/components/grid/grid-display";

export type SavedRef = { id: number; name: string };

/**
 * Conserver la grille affichée, puis passer à la suite.
 *
 * On envoie la grille telle qu'elle a été reçue, et non ses paramètres : le lexique est curé au
 * fil des semaines, la même seed ne redonnerait pas la même grille plus tard.
 *
 * Une grille conservée n'est pas une grille finie : l'écran le dit, et le bouton principal mène à
 * l'étape suivante — relire les mots, écrire les définitions — plutôt qu'à la liste des grilles.
 */
export function SaveGrid({
  grid,
  saved,
  onSaved,
}: {
  grid: GridData;
  saved: SavedRef | null;
  onSaved: (saved: SavedRef) => void;
}) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [isSaving, setSaving] = useState(false);

  if (!isAuthenticated) {
    return (
      <div className="mx-auto w-full max-w-xl rounded-lg border bg-muted/40 p-4 text-center">
        <p className="font-medium">Cette grille vous plaît ?</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Connectez-vous pour la conserver et écrire ses définitions. Elle vous attendra ici.
        </p>
        <div className="mt-3 flex flex-wrap justify-center gap-2">
          <Button asChild size="sm">
            <Link href={withNext("/login", "/grid")}>Se connecter</Link>
          </Button>
          <Button asChild size="sm" variant="outline">
            <Link href={withNext("/register", "/grid")}>Créer un compte</Link>
          </Button>
        </div>
      </div>
    );
  }

  if (saved !== null) {
    return (
      <div className="mx-auto w-full max-w-xl rounded-lg border border-emerald-500/40 bg-emerald-500/5 p-4">
        <p className="flex items-center gap-2 font-medium">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600 dark:text-emerald-500" />
          Grille conservée : « {saved.name} »
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          Étape suivante : relire ses mots, puis écrire les définitions.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button asChild>
            <Link href={`/grids/edit?id=${saved.id}`}>
              Relire et écrire les définitions
              <ArrowRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
          <Link href="/grids" className="text-sm text-muted-foreground underline underline-offset-2">
            Toutes mes grilles
          </Link>
        </div>
      </div>
    );
  }

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const created = await apiFetch("/api/grids", {
        method: "POST",
        body: { ...(name.trim() ? { name: name.trim() } : {}), grid },
      });
      onSaved({ id: created.id, name: created.name });
      queryClient.invalidateQueries({ queryKey: ["saved-grids"] });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "La grille n'a pas pu être conservée.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={save} className="mx-auto flex w-full max-w-xl flex-col gap-2 sm:flex-row sm:items-end">
      <div className="flex-1 space-y-1">
        <Label htmlFor="grid-name" className="text-xs">
          Nom (facultatif)
        </Label>
        <Input
          id="grid-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={`${grid.width}×${grid.height} du jour`}
          maxLength={100}
          disabled={isSaving}
        />
      </div>
      <Button type="submit" disabled={isSaving}>
        {isSaving ? "Enregistrement…" : "Conserver cette grille"}
      </Button>
    </form>
  );
}
