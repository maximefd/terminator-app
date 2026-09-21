"use client";

import type { GridData } from "@/components/grid/grid-display";

/**
 * La grille en SVG : cases définitions, flèches, lettres.
 *
 * Vectoriel et non composé de `<div>` : les flèches coudées se dessinent en traits, le rendu ne
 * dépend pas du navigateur, et c'est ce même dessin qui part au PDF.
 *
 * Les flèches viennent du moteur (`clues`), qui les déduit de la géométrie du layout : un mot
 * horizontal se définit depuis la case à sa gauche, un mot vertical depuis celle du dessus, et le
 * long des bords la flèche se coude. Voir `backend/engine/arrows.py`.
 */
export type Clue = {
  text: string;
  x: number;
  y: number;
  direction: "across" | "down";
  length: number | null;
  cell_x: number | null;
  cell_y: number | null;
  arrow: string | null;
  exit: "right" | "bottom" | null;
};

/**
 * Ce que la grille montre :
 * - `edition` : lettres, flèches et définitions, cases cliquables — on définit un mot qu'on voit ;
 * - `vierge` : la grille telle qu'on la résout, définitions et flèches, sans les lettres ;
 * - `solution` : les lettres seules. Ni flèche ni définition : une page de solutions sert à
 *   vérifier des lettres, le reste l'encombre.
 */
export type GridVariant = "edition" | "vierge" | "solution";

const CELL = 100;
/** Trait fin à l'intérieur, trait fort autour : c'est ce qui donne l'allure imprimée. */
const LINE = 2.2;
const BORDER = 5;

/**
 * Couleurs fixes, et non des variables CSS : une grille de mots fléchés est un objet imprimé.
 * Elle doit avoir l'air du papier dans les deux thèmes, et le convertisseur PDF ne saurait de
 * toute façon pas résoudre un `var()`.
 */
const PAPER = {
  cell: "#ffffff",
  definition: "#e9e7e2",
  line: "#1b1b1b",
  letter: "#111111",
  arrow: "#1b1b1b",
  selected: "#ffd98a",
  highlight: "#fff4dc",
  must: "#dce7ff",
  wish: "#dcf0e2",
};

/** Police des grilles : une étroite de labeur, embarquée avec l'application et dans le PDF. */
// Nom d'un seul tenant : le convertisseur PDF ne retrouvait pas une famille en deux mots,
// et retombait sur une serif large — visible seulement sur le papier.
export const GRID_FONT = "ArchivoNarrow";

const SOURCE_TINT: Record<string, string> = { must: PAPER.must, wish: PAPER.wish };

/** Profondeur de la flèche dans la case voisine, longueur et demi-largeur de sa pointe. */
const IN = 13;
const TIP = 11;
const HALF_TIP = 6;
/** Les flèches coudées longent le bord de la case suivante pour ne pas barrer sa lettre. */
const CORNER = 16;

/** Trait et pointe d'une flèche, en coordonnées locales à la case définition. */
function arrowShape(arrow: string, halfOffset: number) {
  const edge = CELL;
  switch (arrow) {
    // La définition est à gauche du mot : on sort par la droite, tout droit
    case "droite":
      return {
        d: `M ${edge - 22} ${halfOffset} H ${edge + IN}`,
        head: `${edge + IN + TIP},${halfOffset} ${edge + IN},${halfOffset - HALF_TIP} ${edge + IN},${halfOffset + HALF_TIP}`,
      };
    // La définition est au-dessus du mot : on sort par le bas, tout droit
    case "bas":
      return {
        d: `M ${halfOffset} ${edge - 22} V ${edge + IN}`,
        head: `${halfOffset},${edge + IN + TIP} ${halfOffset - HALF_TIP},${edge + IN} ${halfOffset + HALF_TIP},${edge + IN}`,
      };
    // Mot collé au bord gauche : on descend le long de sa première lettre, puis on part à droite
    case "coudee_bas_droite":
      return {
        d: `M ${CORNER} ${edge - 20} V ${edge + CORNER} H ${CORNER + 10}`,
        head: `${CORNER + 10 + TIP},${edge + CORNER} ${CORNER + 10},${edge + CORNER - HALF_TIP} ${CORNER + 10},${edge + CORNER + HALF_TIP}`,
      };
    // Mot collé au bord haut : on entre dans sa première lettre par la gauche, puis on descend
    case "coudee_droite_bas":
      return {
        d: `M ${edge - 20} ${halfOffset} H ${edge + CORNER} V ${halfOffset + 10}`,
        head: `${edge + CORNER},${halfOffset + 10 + TIP} ${edge + CORNER - HALF_TIP},${halfOffset + 10} ${edge + CORNER + HALF_TIP},${halfOffset + 10}`,
      };
    default:
      return null;
  }
}

export const clueKey = (clue: Pick<Clue, "text" | "x" | "y" | "direction">) =>
  `${clue.text}-${clue.x}-${clue.y}-${clue.direction}`;

/** Les cases qu'occupe un mot : de quoi éclairer, pendant l'édition, celui que l'on définit. */
function cellsOf(clue: Clue) {
  const length = clue.length ?? clue.text.length;
  return Array.from({ length }, (_, i) => ({
    x: clue.x + (clue.direction === "across" ? i : 0),
    y: clue.y + (clue.direction === "down" ? i : 0),
  }));
}

type GridSvgProps = {
  grid: GridData & { clues?: Clue[] };
  variant?: GridVariant;
  /** Texte des définitions, par mot placé (clé « MOT-x-y-direction »). */
  definitions?: Record<string, string>;
  selectedKey?: string | null;
  onSelect?: (key: string) => void;
  /** Provenance de chaque case lettre (« must », « wish »), pour teinter la grille produite. */
  cellSources?: Record<string, string>;
};

export function GridSvg({
  grid,
  variant = "solution",
  definitions,
  selectedKey,
  onSelect,
  cellSources,
}: GridSvgProps) {
  const clues = grid.clues ?? [];
  const showLetters = variant !== "vierge";
  const showClues = variant !== "solution";
  const letters = new Map(
    grid.cells.filter((cell) => !cell.is_black).map((cell) => [`${cell.x}-${cell.y}`, cell.char]),
  );

  // Une case définition porte au plus deux définitions, et jamais deux du même côté : celle qui sort
  // par la droite occupe la moitié haute, celle qui sort par le bas la moitié basse (vérifié sur tout
  // le catalogue par backend/tests/test_arrows.py). La case se coupe donc sans arbitrage.
  const byCell = new Map<string, Clue[]>();
  for (const clue of clues) {
    if (clue.cell_x === null || clue.cell_y === null) continue;
    const key = `${clue.cell_x}-${clue.cell_y}`;
    byCell.set(key, [...(byCell.get(key) ?? []), clue]);
  }

  const selectedClue = clues.find((clue) => clueKey(clue) === selectedKey) ?? null;
  const lit = new Set(
    selectedClue && variant === "edition" ? cellsOf(selectedClue).map((cell) => `${cell.x}-${cell.y}`) : [],
  );

  const fillOf = (cell: { x: number; y: number; is_black: boolean }) => {
    if (cell.is_black) return PAPER.definition;
    if (lit.has(`${cell.x}-${cell.y}`)) return PAPER.highlight;
    if (variant !== "vierge") return SOURCE_TINT[cellSources?.[`${cell.x}-${cell.y}`] ?? ""] ?? PAPER.cell;
    return PAPER.cell;
  };

  return (
    <svg
      viewBox={`${-BORDER / 2} ${-BORDER / 2} ${grid.width * CELL + BORDER} ${grid.height * CELL + BORDER}`}
      className="h-auto w-full"
      role="img"
      aria-label={`Grille ${grid.width} sur ${grid.height}, ${grid.words.length} mots`}
    >
      {/* Trois passes : en SVG, l'ordre de dessin décide de ce qui est au-dessus, et les flèches
          débordent sur la case voisine — dessinées trop tôt, la case suivante les effacerait. */}
      {grid.cells.map((cell) => (
        <rect
          key={`case-${cell.x}-${cell.y}`}
          x={cell.x * CELL}
          y={cell.y * CELL}
          width={CELL}
          height={CELL}
          fill={fillOf(cell)}
          stroke={PAPER.line}
          strokeWidth={LINE}
        />
      ))}

      {showLetters &&
        grid.cells
          .filter((cell) => !cell.is_black)
          .map((cell) => (
            <text
              key={`lettre-${cell.x}-${cell.y}`}
              x={cell.x * CELL + CELL / 2}
              y={cell.y * CELL + CELL / 2}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={CELL * 0.56}
              fontWeight="700"
              fontFamily={GRID_FONT}
              fill={PAPER.letter}
            >
              {letters.get(`${cell.x}-${cell.y}`)}
            </text>
          ))}

      {showClues &&
        grid.cells
          .filter((cell) => cell.is_black)
          .map((cell) => {
            const clueList = byCell.get(`${cell.x}-${cell.y}`) ?? [];
            const split = clueList.length > 1;
            const x = cell.x * CELL;
            const y = cell.y * CELL;

            return (
              <g key={`def-${cell.x}-${cell.y}`}>
                {clueList.map((clue) => {
                  const key = clueKey(clue);
                  // Deux définitions : celle qui sort à droite occupe la moitié haute, l'autre la basse
                  const offset = split ? (clue.exit === "right" ? CELL * 0.25 : CELL * 0.75) : CELL / 2;
                  const shape = arrowShape(clue.arrow ?? "", offset);
                  const text = definitions?.[key] ?? "";
                  const boxY = split && clue.exit === "bottom" ? y + CELL / 2 : y;
                  const boxHeight = split ? CELL / 2 : CELL;

                  return (
                    <g key={key}>
                      {selectedKey === key && (
                        <rect x={x} y={boxY} width={CELL} height={boxHeight} fill={PAPER.selected} />
                      )}
                      {shape && (
                        <g fill={PAPER.arrow} stroke={PAPER.arrow} transform={`translate(${x} ${y})`}>
                          <path
                            d={shape.d}
                            fill="none"
                            strokeWidth={LINE * 1.3}
                            strokeLinecap="butt"
                            strokeLinejoin="miter"
                          />
                          <polygon points={shape.head} stroke="none" />
                        </g>
                      )}
                      {text && <ClueText text={text} x={x} y={boxY} height={boxHeight} arrow={clue.arrow} />}
                      {onSelect && (
                        <rect
                          x={x}
                          y={boxY}
                          width={CELL}
                          height={boxHeight}
                          fill="transparent"
                          className="cursor-pointer"
                          data-clue={key}
                          onClick={() => onSelect(key)}
                        >
                          <title>{`Définir ${clue.text}`}</title>
                        </rect>
                      )}
                    </g>
                  );
                })}

                {/* La séparation des deux moitiés se trace par-dessus le fond de sélection */}
                {split && (
                  <line
                    x1={x}
                    y1={y + CELL / 2}
                    x2={x + CELL}
                    y2={y + CELL / 2}
                    stroke={PAPER.line}
                    strokeWidth={LINE * 0.7}
                  />
                )}
              </g>
            );
          })}

      {/* Le cadre extérieur par-dessus tout : c'est lui qui ferme la grille */}
      <rect
        x={0}
        y={0}
        width={grid.width * CELL}
        height={grid.height * CELL}
        fill="none"
        stroke={PAPER.line}
        strokeWidth={BORDER}
      />
    </svg>
  );
}

/**
 * Une définition tient rarement sur une ligne : on la coupe en lignes qui entrent dans sa case.
 *
 * Deux contraintes apprises sur le papier, et non à l'écran : la coupe se calcule pour la police
 * embarquée (le PDF utilise le même fichier, donc les mêmes largeurs), et la place réservée dépend
 * de la flèche — celle d'un mot collé au bord gauche descend à gauche, pas à droite.
 */
function ClueText({
  text,
  x,
  y,
  height,
  arrow,
}: {
  text: string;
  x: number;
  y: number;
  height: number;
  arrow: string | null;
}) {
  const half = height <= CELL / 2;
  const reserved = { left: 0, right: 0, bottom: 0 };
  if (arrow === "coudee_bas_droite") reserved.left = 30;
  else if (arrow === "bas") {
    if (half) reserved.right = 34;
    else reserved.bottom = 26;
  } else reserved.right = 26;

  const fontSize = half ? CELL * 0.125 : CELL * 0.135;
  const usable = CELL - reserved.left - reserved.right - 8;
  // Archivo Narrow tourne autour de 0,43 em par caractère : c'est ce qui fixe la coupe
  const perLine = Math.max(5, Math.floor(usable / (0.43 * fontSize)));
  const lineHeight = fontSize * 1.06;
  const maxLines = Math.max(2, Math.floor((height - reserved.bottom - 6) / lineHeight));

  const lines: string[] = [];
  let current = "";
  for (const word of text.split(" ")) {
    if (!current || (current + " " + word).length <= perLine) {
      current = current ? `${current} ${word}` : word;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  const shown = lines.slice(0, maxLines);

  const centerX = x + reserved.left + usable / 2 + 4;
  const centerY = y + (height - reserved.bottom) / 2;
  const startY = centerY - ((shown.length - 1) * lineHeight) / 2;

  return (
    <text
      textAnchor="middle"
      fill={PAPER.letter}
      fontSize={fontSize}
      fontFamily={GRID_FONT}
    >
      {shown.map((line, index) => (
        <tspan key={line + index} x={centerX} y={startY + index * lineHeight}>
          {line}
        </tspan>
      ))}
    </text>
  );
}
