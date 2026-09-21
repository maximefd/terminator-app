"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
    // Les premiers mots de la liste sont ceux qui comptent : ils arrivent obligatoires par défaut,
    // les suivants en souhaités. L'auteur bascule ensuite comme il veut.
    const required = entries.filter((entry) => entry.required).length < 3;
    onChange([...entries, { id: `${text}-${Date.now()}`, text, required }]);
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
          placeholder="Ajouter un mot (ex : PORTE)"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
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
        <p className="text-sm text-muted-foreground">
          Aucun mot imposé : la grille sera remplie librement. Ajoutez les mots que vous voulez y voir.
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
              className={`flex items-center gap-2 rounded-md border p-2 ${dragged === index ? "opacity-50" : ""}`}
            >
              <span className="cursor-grab select-none px-1 text-muted-foreground" aria-hidden="true">
                ⠿
              </span>
              <span className="flex-1 font-mono font-semibold">{entry.text}</span>

              <Button
                type="button"
                variant={entry.required ? "default" : "secondary"}
                size="sm"
                disabled={disabled}
                onClick={() => toggle(entry.id)}
                aria-pressed={entry.required}
              >
                {entry.required ? "Obligatoire" : "Souhaité"}
              </Button>

              {/* Le glisser-déposer ne suffit pas au clavier : deux boutons font le même travail */}
              <Button type="button" variant="ghost" size="sm" disabled={disabled || index === 0}
                      onClick={() => move(index, index - 1)} aria-label={`Monter ${entry.text}`}>
                ↑
              </Button>
              <Button type="button" variant="ghost" size="sm" disabled={disabled || index === entries.length - 1}
                      onClick={() => move(index, index + 1)} aria-label={`Descendre ${entry.text}`}>
                ↓
              </Button>
              <Button type="button" variant="ghost" size="sm" disabled={disabled}
                      onClick={() => remove(entry.id)} aria-label={`Retirer ${entry.text}`}>
                ✕
              </Button>
            </li>
          ))}
        </ul>
      )}

      <p className="text-xs text-muted-foreground">
        <strong>Obligatoire</strong> : la grille est refusée si le mot n&apos;y entre pas.{" "}
        <strong>Souhaité</strong> : il est placé s&apos;il rentre, sans jamais faire échouer la grille.
      </p>
    </div>
  );
}
