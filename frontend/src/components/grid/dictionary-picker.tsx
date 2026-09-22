"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Toggle } from "@/components/ui/toggle";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/contexts/auth-context";

type Dictionary = { id: number; name: string; is_active: boolean };

/** L'API en accepte dix au plus (ADR 0007) : autant le dire avant qu'elle refuse. */
const MAX_DICTIONARIES = 10;

type DictionaryPickerProps = {
  selected: number[];
  onChange: (ids: number[]) => void;
  disabled?: boolean;
};

export function DictionaryPicker({ selected, onChange, disabled }: DictionaryPickerProps) {
  const { isAuthenticated } = useAuth();
  const { data: dictionaries, isLoading, error } = useQuery<Dictionary[], Error>({
    queryKey: ["dictionaries"],
    queryFn: () => apiFetch("/api/dictionaries"),
    enabled: isAuthenticated,
  });

  if (!isAuthenticated) {
    return (
      <p className="text-sm text-muted-foreground">
        <Link href="/login" className="underline underline-offset-2">Connectez-vous</Link> pour puiser dans vos
        dictionnaires personnels, les mêmes que dans la recherche par motif.
      </p>
    );
  }

  if (isLoading) return <p className="text-sm text-muted-foreground">Chargement de vos dictionnaires…</p>;
  if (error) return <p className="text-sm text-destructive">{error.message}</p>;
  if (!dictionaries?.length) {
    return <p className="text-sm text-muted-foreground">Vous n&apos;avez pas encore de dictionnaire personnel.</p>;
  }

  const toggle = (id: number) =>
    onChange(selected.includes(id) ? selected.filter((item) => item !== id) : [...selected, id]);

  return (
    <div className="space-y-2">
      {/*
        Tous les dictionnaires se cochent, aucun n'entre de lui-même — pas même l'actif
        ([ADR 0011](docs/adr/0011-dictionnaires-choisis.md)). L'actif sert à la recherche par motif ;
        rien ne dit que la grille du jour doit hériter de ce qu'on y range.
      */}
      <div className="flex flex-wrap gap-2">
        {dictionaries.map((dictionary) => (
          <Toggle
            key={dictionary.id}
            variant="outline"
            pressed={selected.includes(dictionary.id)}
            onPressedChange={() => toggle(dictionary.id)}
            disabled={disabled || (!selected.includes(dictionary.id) && selected.length >= MAX_DICTIONARIES)}
            aria-label={`Utiliser le dictionnaire ${dictionary.name}`}
            // Coché = vert : le gris du réglage par défaut ne se distingue pas d'un bouton inactif
            className="data-[state=on]:border-emerald-500/60 data-[state=on]:bg-emerald-500/15 data-[state=on]:text-emerald-800 dark:data-[state=on]:text-emerald-300"
          >
            {dictionary.name}
            {dictionary.is_active && (
              <span className="ml-1.5 text-xs text-muted-foreground">actif dans la recherche</span>
            )}
          </Toggle>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        {selected.length === 0
          ? "Aucun dictionnaire coché : la grille n'utilisera que vos mots saisis et le lexique commun."
          : "Leurs mots rejoignent les souhaités : placés s'ils rentrent, sans jamais faire échouer la grille."}{" "}
        {selected.length >= MAX_DICTIONARIES && `Maximum de ${MAX_DICTIONARIES} atteint.`}
      </p>
    </div>
  );
}
