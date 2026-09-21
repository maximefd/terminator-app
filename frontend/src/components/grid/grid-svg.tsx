"use client";

import type { GridData } from "@/components/grid/grid-display";

/**
 * La grille en SVG : cases définitions, flèches et lettres.
 *
 * Vectoriel et non composé de `<div>`, pour trois raisons : les flèches coudées se dessinent en
 * traits, le rendu ne bouge pas d'un écran à l'autre, et c'est ce même dessin qui partira à
 * l'impression et au PDF.
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

const CELL = 100;
const STROKE = 3;

/**
 * Couleurs fixes, et non des variables CSS : une grille de mots fléchés est un objet imprimé.
 * Elle doit avoir l'air du papier dans les deux thèmes, et le convertisseur PDF ne saurait de
 * toute façon pas résoudre un `var()`.
 */
const PAPER = {
  cell: "#ffffff",
  definition: "#e8e8e6",
  line: "#1b1b1b",
  letter: "#111111",
  arrow: "#1b1b1b",
  selected: "#c9defc",
  must: "#dbe7ff",
  wish: "#dcf3e4",
};

/** Profondeur de la flèche dans la case voisine, et longueur de sa pointe. */
const IN = 15;
const TIP = 15;
/** Les flèches coudées longent le bord de la case suivante pour ne pas barrer sa lettre. */
const CORNER = 17;

/** Trait et pointe d'une flèche, en coordonnées locales à la case définition. */
function arrowShape(arrow: string, halfOffset: number) {
  const edge = CELL;
  switch (arrow) {
    // La définition est à gauche du mot : on sort par la droite, tout droit
    case "droite":
      return {
        d: `M ${edge - 28} ${halfOffset} H ${edge + IN}`,
        head: `${edge + IN + TIP},${halfOffset} ${edge + IN},${halfOffset - 9} ${edge + IN},${halfOffset + 9}`,
      };
    // La définition est au-dessus du mot : on sort par le bas, tout droit
    case "bas":
      return {
        d: `M ${halfOffset} ${edge - 28} V ${edge + IN}`,
        head: `${halfOffset},${edge + IN + TIP} ${halfOffset - 9},${edge + IN} ${halfOffset + 9},${edge + IN}`,
      };
    // Mot collé au bord gauche : on descend le long du bord de sa première lettre, puis on part à droite
    case "coudee_bas_droite":
      return {
        d: `M ${CORNER} ${edge - 26} V ${edge + CORNER} H ${CORNER + 13}`,
        head: `${CORNER + 13 + TIP},${edge + CORNER} ${CORNER + 13},${edge + CORNER - 9} ${CORNER + 13},${edge + CORNER + 9}`,
      };
    // Mot collé au bord haut : on entre dans sa première lettre par la gauche, puis on descend
    case "coudee_droite_bas":
      return {
        d: `M ${edge - 26} ${halfOffset} H ${edge + CORNER} V ${halfOffset + 13}`,
        head: `${edge + CORNER},${halfOffset + 13 + TIP} ${edge + CORNER - 9},${halfOffset + 13} ${edge + CORNER + 9},${halfOffset + 13}`,
      };
    default:
      return null;
  }
}

type GridSvgProps = {
  grid: GridData & { clues?: Clue[] };
  /** « vierge » : la grille telle qu'on la résout. « remplie » : la solution. */
  mode?: "vierge" | "remplie";
  /** Texte des définitions, par mot placé (clé « MOT-x-y-direction »). */
  definitions?: Record<string, string>;
  /** Sélection d'une définition dans l'éditeur. */
  selectedKey?: string | null;
  onSelect?: (key: string) => void;
  /** Provenance de chaque case lettre (« must », « wish »), pour teinter la solution. */
  cellSources?: Record<string, string>;
};

const SOURCE_TINT: Record<string, string> = {
  must: PAPER.must,
  wish: PAPER.wish,
};

export const clueKey = (clue: Pick<Clue, "text" | "x" | "y" | "direction">) =>
  `${clue.text}-${clue.x}-${clue.y}-${clue.direction}`;

export function GridSvg({ grid, mode = "remplie", definitions, selectedKey, onSelect, cellSources }: GridSvgProps) {
  const clues = grid.clues ?? [];
  const letters = new Map(grid.cells.filter((cell) => !cell.is_black).map((cell) => [`${cell.x}-${cell.y}`, cell.char]));

  // Une case définition porte au plus deux définitions, et jamais deux du même côté : celle qui sort
  // par la droite occupe la moitié haute, celle qui sort par le bas la moitié basse (vérifié sur tout
  // le catalogue par backend/tests/test_arrows.py). La case se coupe donc sans arbitrage.
  const byCell = new Map<string, Clue[]>();
  for (const clue of clues) {
    if (clue.cell_x === null || clue.cell_y === null) continue;
    const key = `${clue.cell_x}-${clue.cell_y}`;
    byCell.set(key, [...(byCell.get(key) ?? []), clue]);
  }

  // Trois passes, parce qu'en SVG c'est l'ordre de dessin qui décide de ce qui est au-dessus :
  // les flèches débordent sur la case voisine, et la case suivante les effacerait.
  const definitionCells = grid.cells.filter((cell) => cell.is_black);

  return (
    <svg
      viewBox={`-${STROKE} -${STROKE} ${grid.width * CELL + STROKE * 2} ${grid.height * CELL + STROKE * 2}`}
      className="h-auto w-full max-w-3xl"
      role="img"
      aria-label={`Grille ${grid.width} sur ${grid.height}, ${grid.words.length} mots`}
    >
      {/* 1. Les cases */}
      {grid.cells.map((cell) => (
        <rect
          key={`case-${cell.x}-${cell.y}`}
          x={cell.x * CELL}
          y={cell.y * CELL}
          width={CELL}
          height={CELL}
          fill={
            cell.is_black
              ? PAPER.definition
              : (mode === "remplie" && SOURCE_TINT[cellSources?.[`${cell.x}-${cell.y}`] ?? ""]) ||
                PAPER.cell
          }
          stroke={PAPER.line}
          strokeWidth={STROKE}
        />
      ))}

      {/* 2. Les lettres */}
      {mode === "remplie" &&
        grid.cells
          .filter((cell) => !cell.is_black)
          .map((cell) => (
            <text
              key={`lettre-${cell.x}-${cell.y}`}
              x={cell.x * CELL + CELL / 2}
              y={cell.y * CELL + CELL / 2}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={CELL * 0.6}
              fontWeight="600"
              fontFamily="Helvetica, Arial, sans-serif"
              fill={PAPER.letter}
            >
              {letters.get(`${cell.x}-${cell.y}`)}
            </text>
          ))}

      {/* 3. Les définitions et leurs flèches, par-dessus tout le reste */}
      {definitionCells.map((cell) => {
        const clueList = byCell.get(`${cell.x}-${cell.y}`) ?? [];
        const split = clueList.length > 1;
        const x = cell.x * CELL;
        const y = cell.y * CELL;

        return (
          <g key={`def-${cell.x}-${cell.y}`}>
            {split && (
              <line x1={x} y1={y + CELL / 2} x2={x + CELL} y2={y + CELL / 2}
                    stroke={PAPER.line} strokeWidth={STROKE / 2} />
            )}

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
                  {onSelect && (
                    <rect
                      x={x} y={boxY} width={CELL} height={boxHeight}
                      fill={selectedKey === key ? PAPER.selected : "transparent"}
                      className="cursor-pointer"
                      onClick={() => onSelect(key)}
                    />
                  )}
                  {shape && (
                    <g transform={`translate(${x} ${y})`} fill={PAPER.arrow}
                       stroke={PAPER.arrow} strokeWidth={STROKE + 1}>
                      <path d={shape.d} fill="none" strokeLinecap="round" strokeLinejoin="round" />
                      <polygon points={shape.head} stroke="none" />
                    </g>
                  )}
                  {text && (
                    <ClueText text={text} x={x} y={boxY} height={boxHeight} arrow={clue.arrow} />
                  )}
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}

/**
 * Une définition tient rarement sur une ligne : on la coupe en lignes qui entrent dans sa moitié de case.
 *
 * La coupe est calculée pour la police la plus large des deux rendus : le convertisseur PDF ne dispose
 * pas de la police du navigateur, et un texte juste à la bonne largeur à l'écran débordait sur le papier.
 */
function ClueText({
  text, x, y, height, arrow,
}: { text: string; x: number; y: number; height: number; arrow: string | null }) {
  // La flèche traverse la case : le texte se serre dans ce qu'elle laisse, et le côté dépend de la
  // flèche — la coudée d'un mot collé au bord gauche descend le long de la gauche, pas de la droite.
  const half = height <= CELL / 2;
  const reserved = { left: 0, right: 0, bottom: 0 };
  if (arrow === "coudee_bas_droite") reserved.left = 34;
  else if (arrow === "bas") { if (half) reserved.right = 40; else reserved.bottom = 30; }
  else reserved.right = 30;

  const fontSize = half ? CELL * 0.13 : CELL * 0.14;
  const usable = CELL - reserved.left - reserved.right;
  // Largeur d'un caractère estimée au plus large des deux rendus (le PDF n'a pas la police de l'écran)
  const perLine = Math.max(6, Math.floor((usable * 0.92) / (0.55 * fontSize)));
  const maxLines = Math.max(2, Math.floor((height - reserved.bottom) / (fontSize * 1.2)));
  const words = text.split(" ");
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    if ((current + " " + word).trim().length <= perLine || !current) {
      current = (current + " " + word).trim();
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  const shown = lines.slice(0, maxLines);
  const centerX = x + reserved.left + usable / 2;
  const centerY = y + (height - reserved.bottom) / 2;
  const startY = centerY - ((shown.length - 1) * fontSize * 1.15) / 2;

  return (
    // La police est nommée explicitement : sans elle, le PDF retombe sur une serif bien plus large
    <text textAnchor="middle" fill={PAPER.letter} fontSize={fontSize} fontFamily="Helvetica, Arial, sans-serif">
      {shown.map((line, index) => (
        <tspan key={line + index} x={centerX} y={startY + index * fontSize * 1.15}>
          {line}
        </tspan>
      ))}
    </text>
  );
}
