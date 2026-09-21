"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";
import type { GridData } from "@/components/grid/grid-display";

/**
 * Conserver la grille affichée.
 *
 * On envoie la grille telle qu'elle a été reçue, et non ses paramètres : le lexique est curé au
 * fil des semaines, la même seed ne redonnerait pas la même grille plus tard.
 */
export function SaveGrid({ grid }: { grid: GridData }) {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [isSaving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<number | null>(null);

  if (!isAuthenticated) {
    return (
      <p className="text-center text-sm text-muted-foreground">
        <Link href="/login" className="underline">
          Connectez-vous
        </Link>{" "}
        pour conserver cette grille et la retrouver plus tard.
      </p>
    );
  }

  if (savedId !== null) {
    return (
      <p className="text-center text-sm text-muted-foreground">
        Grille conservée.{" "}
        <Link href="/grids" className="font-medium underline">
          Voir mes grilles
        </Link>
      </p>
    );
  }

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const saved = await apiFetch("/api/grids", {
        method: "POST",
        body: { ...(name.trim() ? { name: name.trim() } : {}), grid },
      });
      setSavedId(saved.id);
      queryClient.invalidateQueries({ queryKey: ["saved-grids"] });
      toast.success(`« ${saved.name} » est conservée.`);
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
