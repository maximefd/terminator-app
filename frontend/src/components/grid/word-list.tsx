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
  /** Ajouté à l'instant : obligatoire ou souhaité reste à décider, selon les chances de la grille. */
  pending?: boolean;
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
    // Souhaité le temps d'estimer : l'écran décide ensuite s'il peut le rendre obligatoire sans trop
    // faire baisser les chances de la grille (voir GridClientLayout)
    onChange([...entries, { id: `${text}-${Date.now()}`, text, required: false, pending: true }]);
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
    onChange(
      entries.map((entry) => (entry.id === id ? { ...entry, required: !entry.required, pending: false } : entry)),
    );

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
          Les premiers mots sont <strong>obligatoires</strong> tant que la grille garde plus de 70 % de
          chances d&apos;aboutir ; les autres sont <strong>souhaités</strong> : placés s&apos;ils trouvent
          leur place, sans jamais faire échouer la grille. Un clic sur « Obligatoire » bascule.
        </p>
      )}
    </div>
  );
}
