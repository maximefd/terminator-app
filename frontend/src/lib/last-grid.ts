import type { GridData } from "@/components/grid/grid-display";
import type { WordEntry } from "@/components/grid/word-list";

/**
 * La dernière génération, gardée dans le navigateur.
 *
 * On génère souvent **avant** de se connecter : la grille plaît, on veut la garder, on passe par
 * l'inscription… et on revenait sur un écran vide. La demande et la grille survivent donc au
 * changement de page, jusqu'à la génération suivante ou la déconnexion.
 *
 * Commodité, pas stockage : un navigateur en navigation privée peut tout refuser, et l'écran doit
 * alors fonctionner comme avant — d'où les `try` qui avalent l'erreur.
 */
const KEY = "terminator:derniere-grille";

export type LastGrid = {
  format: string | null;
  entries: WordEntry[];
  dictionaryIds: number[];
  grid: GridData | null;
  /** La grille a déjà été conservée : on propose la suite plutôt qu'un second enregistrement. */
  saved: { id: number; name: string } | null;
};

export function loadLastGrid(): LastGrid | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<LastGrid>;
    return {
      format: typeof parsed.format === "string" ? parsed.format : null,
      entries: Array.isArray(parsed.entries) ? parsed.entries : [],
      dictionaryIds: Array.isArray(parsed.dictionaryIds) ? parsed.dictionaryIds : [],
      grid: parsed.grid && Array.isArray(parsed.grid.cells) ? parsed.grid : null,
      saved: parsed.saved && typeof parsed.saved.id === "number" ? parsed.saved : null,
    };
  } catch {
    return null;
  }
}

export function storeLastGrid(state: LastGrid) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Stockage refusé ou plein : la grille ne survivra pas au changement de page, rien de plus
  }
}

/** À la déconnexion : la grille « déjà conservée » d'un compte ne doit pas s'afficher dans un autre. */
export function forgetLastGrid() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // Rien à effacer si le stockage est refusé
  }
}
