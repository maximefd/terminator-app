"use client";

/**
 * La silhouette d'une grille, en miniature.
 *
 * Dessinée depuis la **forme** envoyée avec le résumé (`x` case définition, `-` case lettre) : avec
 * cent grilles conservées, c'est le dessin qu'on reconnaît, pas la ligne de texte. Ni lettres ni
 * mots ne transitent pour l'afficher.
 */
export function GridThumbnail({ shape, className = "" }: { shape: string[]; className?: string }) {
  const height = shape.length;
  const width = shape[0]?.length ?? 0;
  if (!height || !width) return null;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={`h-auto w-full object-contain ${className}`}
      role="img"
      aria-label={`Silhouette d'une grille ${width} sur ${height}`}
      shapeRendering="crispEdges"
    >
      <rect x={0} y={0} width={width} height={height} fill="#ffffff" />
      {shape.flatMap((row, y) =>
        [...row].map((cell, x) =>
          cell === "x" ? (
            <rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill="#c9c6bf" />
          ) : null,
        ),
      )}
      {/* Le quadrillage, tracé d'un seul chemin : une miniature de 13×18 reste légère */}
      <path
        d={[
          ...Array.from({ length: width - 1 }, (_, i) => `M ${i + 1} 0 V ${height}`),
          ...Array.from({ length: height - 1 }, (_, i) => `M 0 ${i + 1} H ${width}`),
        ].join(" ")}
        stroke="#d8d5ce"
        strokeWidth={0.06}
        fill="none"
      />
      <rect
        x={0}
        y={0}
        width={width}
        height={height}
        fill="none"
        stroke="#1b1b1b"
        strokeWidth={0.12}
      />
    </svg>
  );
}
