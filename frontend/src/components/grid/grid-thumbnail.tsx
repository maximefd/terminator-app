"use client";

/**
 * La silhouette d'une grille, en miniature.
 *
 * Dessinée depuis la **forme** envoyée avec le résumé (`x` case définition, `-` case lettre) : avec
 * cent grilles conservées, c'est le dessin qu'on reconnaît, pas la ligne de texte. Ni lettres ni
 * mots ne transitent pour l'afficher.
 *
 * À cette taille, on ne trace pas le quadrillage : à 44 pixels de large, les traits d'un 13×18
 * tomberaient sous le pixel et ne feraient qu'un gris sale. Ce qui se lit, c'est la disposition des
 * cases définitions dans un cadre net.
 */

/**
 * Marge du viewBox : sans elle, la moitié extérieure du cadre sort du dessin et se fait rogner —
 * c'est ce qui faisait disparaître le trait du bas sur certaines grilles.
 */
const PADDING = 0.5;
/** Épaisseur du cadre, en **pixels** : un trait exprimé en unités de grille maigrit à mesure que la
 * grille compte de cases, et un 13×18 finissait avec un filet deux fois plus fin qu'un 6×7. */
const FRAME_PX = 2;

export function GridThumbnail({ shape, className = "" }: { shape: string[]; className?: string }) {
  const height = shape.length;
  const width = shape[0]?.length ?? 0;
  if (!height || !width) return null;

  return (
    <svg
      viewBox={`${-PADDING} ${-PADDING} ${width + PADDING * 2} ${height + PADDING * 2}`}
      className={`h-auto w-full ${className}`}
      role="img"
      aria-label={`Silhouette d'une grille ${width} sur ${height}`}
    >
      <rect x={0} y={0} width={width} height={height} fill="#ffffff" />
      {shape.flatMap((row, y) =>
        [...row].map((cell, x) =>
          cell === "x" ? (
            <rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill="#b9b5ac" />
          ) : null,
        ),
      )}
      <rect
        x={0}
        y={0}
        width={width}
        height={height}
        fill="none"
        stroke="#3f3f46"
        strokeWidth={FRAME_PX}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
