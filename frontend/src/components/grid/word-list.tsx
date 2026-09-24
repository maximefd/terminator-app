"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Toggle } from "@/components/ui/toggle";
import { Lock } from "lucide-react";

export type WordEntry = {
  id: string;
  text: string;
  /** Obligatoire : la grille est refusée sans lui. Sinon souhaité : placé s'il rentre. */
  required: boolean;
};

type WordListProps = {
  entries: WordEntry[];
  onChange: (entries: WordEntry[]) => void;
  disabled?: boolean;
};

const MAX_WORDS = 20;

export function WordList({ entries, onChange, disabled }: WordListProps) {
  const [draft, setDraft] = useState("");
  const [dragged, setDragged] = useState<number | null>(null);

  const addWord = () => {
    const text = draft.trim().toUpperCase();
    if (!text) return;
    if (entries.some((entry) => entry.text === text)) {
      setDraft("");
      return;
    }
    // Un mot arrive souhaité : il ne fait jamais échouer la grille. Le rendre obligatoire est un
    // choix explicite, parce qu'il a un prix — la génération peut alors échouer.
    onChange([...entries, { id: `${text}-${Date.now()}`, text, required: false }]);
    setDraft("");
  };

  const move = (from: number, to: number) => {
    if (from === to || to < 0 || to >= entries.length) return;
    const next = [...entries];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onChange(next);
  };

  const toggle = (id: string) =>
    onChange(entries.map((entry) => (entry.id === id ? { ...entry, required: !entry.required } : entry)));

  const remove = (id: string) => onChange(entries.filter((entry) => entry.id !== id));

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          value={draft}
          disabled={disabled || entries.length >= MAX_WORDS}
          placeholder="Un mot à placer (ex : PORTE)"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            // Entrée et Tab ajoutent le mot et laissent le curseur en place : on tape sa liste
            // d'une traite. Tab sur un champ vide reprend son rôle habituel et quitte le champ.
            if (event.key === "Enter" || (event.key === "Tab" && !event.shiftKey && draft.trim())) {
              event.preventDefault();
              addWord();
            }
          }}
          aria-label="Mot à placer dans la grille"
        />
        <Button type="button" onClick={addWord} disabled={disabled || !draft.trim()}>
          Ajouter
        </Button>
      </div>

      {entries.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          Le moteur essaiera de les placer. <kbd className="rounded border px-1">Entrée</kbd> pour
          enchaîner les mots.
        </p>
      ) : (
        <ul className="space-y-2">
          {entries.map((entry, index) => (
            <li
              key={entry.id}
              draggable={!disabled}
              onDragStart={() => setDragged(index)}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => {
                if (dragged !== null) move(dragged, index);
                setDragged(null);
              }}
              onDragEnd={() => setDragged(null)}
              className={`flex items-center gap-1 rounded-md border p-1.5 ${dragged === index ? "opacity-50" : ""}`}
            >
              <span className="cursor-grab select-none px-1 text-muted-foreground" aria-hidden="true">
                ⠿
              </span>
              <span className="min-w-0 flex-1 truncate font-mono font-semibold" title={entry.text}>{entry.text}</span>

              <Toggle
                size="sm"
                variant="outline"
                disabled={disabled}
                pressed={entry.required}
                onPressedChange={() => toggle(entry.id)}
                aria-label={`${entry.text} obligatoire`}
                title="Obligatoire : la grille est refusée si le mot n'y entre pas"
                className="h-7 px-2 text-xs data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
              >
                <Lock className="mr-1 h-3 w-3" />
                Obligatoire
              </Toggle>

              {/* Le glisser-déposer ne suffit pas au clavier : deux boutons font le même travail */}
              <Button type="button" variant="ghost" size="icon" className="h-7 w-7" disabled={disabled || index === 0}
                      onClick={() => move(index, index - 1)} aria-label={`Monter ${entry.text}`}>
                ↑
              </Button>
              <Button type="button" variant="ghost" size="icon" className="h-7 w-7" disabled={disabled || index === entries.length - 1}
                      onClick={() => move(index, index + 1)} aria-label={`Descendre ${entry.text}`}>
                ↓
              </Button>
              <Button type="button" variant="ghost" size="icon" className="h-7 w-7" disabled={disabled}
                      onClick={() => remove(entry.id)} aria-label={`Retirer ${entry.text}`}>
                ✕
              </Button>
            </li>
          ))}
        </ul>
      )}

      {entries.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Chaque mot est placé s&apos;il trouve sa place, sans jamais faire échouer la grille. Cochez{" "}
          <strong>Obligatoire</strong> pour l&apos;exiger : la génération peut alors échouer, et
          d&apos;autant plus que le mot est long.
        </p>
      )}
    </div>
  );
}
