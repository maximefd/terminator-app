import type { GridData } from "@/components/grid/grid-display";
import type { Clue } from "@/components/grid/grid-svg";

/**
 * La grille de la page d'accueil : une **vraie** sortie du moteur, pas une maquette.
 *
 * Produite par `POST /api/grids/generate` (6×7, seed 99, PIANO imposé), avec ses flèches déduites
 * par `engine/arrows.py`. Elle est rendue par le même composant que l'application : ce que le
 * visiteur voit ici est exactement ce que le logiciel fabrique.
 *
 * Les définitions, elles, sont écrites à la main — c'est le travail de l'auteur, et l'accueil doit
 * montrer une grille finie, pas une grille à moitié faite.
 */
export const DEMO_GRID: GridData & { clues: Clue[] } = {
  width: 6,
  height: 7,
  layout: "6x7-002",
  seed: 99,
  fill_ratio: 1.0,
  wish_ratio: 0.083,
  must_words: ["PIANO"],
  cells: [
    { x: 0, y: 0, char: "", is_black: true },
    { x: 1, y: 0, char: "C", is_black: false },
    { x: 2, y: 0, char: "", is_black: true },
    { x: 3, y: 0, char: "E", is_black: false },
    { x: 4, y: 0, char: "", is_black: true },
    { x: 5, y: 0, char: "P", is_black: false },
    { x: 0, y: 1, char: "R", is_black: false },
    { x: 1, y: 1, char: "A", is_black: false },
    { x: 2, y: 1, char: "M", is_black: false },
    { x: 3, y: 1, char: "P", is_black: false },
    { x: 4, y: 1, char: "E", is_black: false },
    { x: 5, y: 1, char: "R", is_black: false },
    { x: 0, y: 2, char: "", is_black: true },
    { x: 1, y: 2, char: "P", is_black: false },
    { x: 2, y: 2, char: "I", is_black: false },
    { x: 3, y: 2, char: "A", is_black: false },
    { x: 4, y: 2, char: "N", is_black: false },
    { x: 5, y: 2, char: "O", is_black: false },
    { x: 0, y: 3, char: "P", is_black: false },
    { x: 1, y: 3, char: "I", is_black: false },
    { x: 2, y: 3, char: "E", is_black: false },
    { x: 3, y: 3, char: "T", is_black: false },
    { x: 4, y: 3, char: "I", is_black: false },
    { x: 5, y: 3, char: "N", is_black: false },
    { x: 0, y: 4, char: "", is_black: true },
    { x: 1, y: 4, char: "T", is_black: false },
    { x: 2, y: 4, char: "", is_black: true },
    { x: 3, y: 4, char: "E", is_black: false },
    { x: 4, y: 4, char: "V", is_black: false },
    { x: 5, y: 4, char: "E", is_black: false },
    { x: 0, y: 5, char: "P", is_black: false },
    { x: 1, y: 5, char: "A", is_black: false },
    { x: 2, y: 5, char: "T", is_black: false },
    { x: 3, y: 5, char: "E", is_black: false },
    { x: 4, y: 5, char: "R", is_black: false },
    { x: 5, y: 5, char: "E", is_black: false },
    { x: 0, y: 6, char: "", is_black: true },
    { x: 1, y: 6, char: "L", is_black: false },
    { x: 2, y: 6, char: "E", is_black: false },
    { x: 3, y: 6, char: "S", is_black: false },
    { x: 4, y: 6, char: "E", is_black: false },
    { x: 5, y: 6, char: "S", is_black: false },
  ],
  words: [
    { text: "CAPITAL", x: 1, y: 0, direction: "down", source: "common" },
    { text: "EPATEES", x: 3, y: 0, direction: "down", source: "common" },
    { text: "PRONEES", x: 5, y: 0, direction: "down", source: "common" },
    { text: "RAMPER", x: 0, y: 1, direction: "across", source: "common" },
    { text: "MIE", x: 2, y: 1, direction: "down", source: "common" },
    { text: "ENIVRE", x: 4, y: 1, direction: "down", source: "common" },
    { text: "PIANO", x: 1, y: 2, direction: "across", source: "must" },
    { text: "PIETIN", x: 0, y: 3, direction: "across", source: "common" },
    { text: "EVE", x: 3, y: 4, direction: "across", source: "common" },
    { text: "PATERE", x: 0, y: 5, direction: "across", source: "common" },
    { text: "TE", x: 2, y: 5, direction: "down", source: "common" },
    { text: "LESES", x: 1, y: 6, direction: "across", source: "common" },
  ],
  clues: [
    { text: "CAPITAL", x: 1, y: 0, direction: "down", length: 7, cell_x: 0, cell_y: 0, arrow: "coudee_droite_bas", exit: "right" },
    { text: "EPATEES", x: 3, y: 0, direction: "down", length: 7, cell_x: 2, cell_y: 0, arrow: "coudee_droite_bas", exit: "right" },
    { text: "PRONEES", x: 5, y: 0, direction: "down", length: 7, cell_x: 4, cell_y: 0, arrow: "coudee_droite_bas", exit: "right" },
    { text: "RAMPER", x: 0, y: 1, direction: "across", length: 6, cell_x: 0, cell_y: 0, arrow: "coudee_bas_droite", exit: "bottom" },
    { text: "MIE", x: 2, y: 1, direction: "down", length: 3, cell_x: 2, cell_y: 0, arrow: "bas", exit: "bottom" },
    { text: "ENIVRE", x: 4, y: 1, direction: "down", length: 6, cell_x: 4, cell_y: 0, arrow: "bas", exit: "bottom" },
    { text: "PIANO", x: 1, y: 2, direction: "across", length: 5, cell_x: 0, cell_y: 2, arrow: "droite", exit: "right" },
    { text: "PIETIN", x: 0, y: 3, direction: "across", length: 6, cell_x: 0, cell_y: 2, arrow: "coudee_bas_droite", exit: "bottom" },
    { text: "EVE", x: 3, y: 4, direction: "across", length: 3, cell_x: 2, cell_y: 4, arrow: "droite", exit: "right" },
    { text: "PATERE", x: 0, y: 5, direction: "across", length: 6, cell_x: 0, cell_y: 4, arrow: "coudee_bas_droite", exit: "bottom" },
    { text: "TE", x: 2, y: 5, direction: "down", length: 2, cell_x: 2, cell_y: 4, arrow: "bas", exit: "bottom" },
    { text: "LESES", x: 1, y: 6, direction: "across", length: 5, cell_x: 0, cell_y: 6, arrow: "droite", exit: "right" },
  ],
};

export const DEMO_DEFINITIONS: Record<string, string> = {
  "1-0-down": "Essentiel",
  "3-0-down": "Aplaties",
  "5-0-down": "Recommandées",
  "0-1-across": "Avancer au sol",
  "2-1-down": "Cœur du pain",
  "4-1-down": "Monte à la tête",
  "1-2-across": "Instrument à touches",
  "0-3-across": "Maladie du blé",
  "3-4-across": "La première",
  "0-5-across": "Pour le manteau",
  "2-5-down": "Règle en T",
  "1-6-across": "Désavantagés",
};
