import { jsPDF } from "jspdf";
import { svg2pdf } from "svg2pdf.js";

import { GRID_FONT } from "@/components/grid/grid-svg";

/**
 * Export d'une grille : PDF vectoriel et fichier de travail.
 *
 * Le PDF part du **même SVG que l'écran** — pas de second rendu à maintenir, et un trait net à
 * n'importe quelle taille d'impression. La police du dessin y est **embarquée** : sans elle, le
 * convertisseur retombait sur une serif large, et un texte calé à l'écran débordait sur le papier.
 */
const A4 = { width: 595.28, height: 841.89 }; // points, portrait
const MARGIN = 46;
const TITLE_SIZE = 13;

const FONTS = [
  { file: "archivo-narrow-500.ttf", style: "normal" as const },
  { file: "archivo-narrow-700.ttf", style: "bold" as const },
];

/** Base64 par tranches : `String.fromCharCode(...)` sur 57 Ko d'un coup fait déborder la pile. */
function toBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 8192) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
  }
  return btoa(binary);
}

async function embedFont(pdf: jsPDF) {
  for (const { file, style } of FONTS) {
    const response = await fetch(`/fonts/${file}`);
    if (!response.ok) throw new Error("La police de la grille n'a pas pu être chargée.");
    pdf.addFileToVFS(file, toBase64(await response.arrayBuffer()));
    pdf.addFont(file, GRID_FONT, style);
  }
}

function download(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/** Un nom de fichier sûr, tiré du nom que l'auteur a donné à sa grille. */
export function safeFilename(name: string, extension: string) {
  const base = name
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-zA-Z0-9 _-]/g, "")
    .trim()
    .replace(/\s+/g, "-")
    .toLowerCase();
  return `${base || "grille"}.${extension}`;
}

async function drawPage(pdf: jsPDF, svg: SVGSVGElement, title: string) {
  const viewBox = svg.viewBox.baseVal;
  const ratio = viewBox.height / viewBox.width;
  // La grille prend la largeur utile, sans jamais dépasser la hauteur de la page
  const width = Math.min(A4.width - MARGIN * 2, (A4.height - MARGIN * 2 - TITLE_SIZE * 2) / ratio);
  const height = width * ratio;

  pdf.setFont(GRID_FONT, "bold");
  pdf.setFontSize(TITLE_SIZE);
  pdf.text(title, MARGIN, MARGIN);
  await svg2pdf(svg, pdf, { x: MARGIN, y: MARGIN + TITLE_SIZE, width, height });
}

/**
 * Écrit le PDF. `blank` et `solution` sont les SVG déjà rendus par la page ; la solution est
 * facultative — une grille qu'on envoie à quelqu'un ne part pas toujours avec sa réponse.
 */
export async function exportPdf(name: string, blank: SVGSVGElement, solution: SVGSVGElement | null) {
  const pdf = new jsPDF({ unit: "pt", format: "a4", orientation: "portrait" });
  await embedFont(pdf);

  await drawPage(pdf, blank, name);
  if (solution) {
    pdf.addPage();
    await drawPage(pdf, solution, `${name} — solution`);
  }
  pdf.save(safeFilename(name, "pdf"));
}

/** Le fichier de travail : la grille, ses définitions, et de quoi savoir d'où elle vient. */
export function exportJson(name: string, grid: unknown, definitions: Record<string, string>) {
  const content = {
    format: "terminator/grille",
    version: 1,
    name,
    exported_at: new Date().toISOString(),
    grid,
    definitions,
  };
  download(
    new Blob([JSON.stringify(content, null, 2)], { type: "application/json" }),
    safeFilename(name, "json"),
  );
}
