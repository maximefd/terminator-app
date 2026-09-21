import { jsPDF } from "jspdf";
import { svg2pdf } from "svg2pdf.js";

/**
 * Export d'une grille : PDF vectoriel et fichier de travail.
 *
 * Le PDF part du **même SVG que l'écran** : pas de second rendu à maintenir, et le trait reste net
 * à n'importe quelle taille d'impression. La page solution est une seconde page du même document,
 * pour qu'elle ne se perde pas en route.
 */
const A4 = { width: 595.28, height: 841.89 }; // points, portrait
const MARGIN = 48;

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
  const width = A4.width - MARGIN * 2;
  const height = width * ratio;

  pdf.setFontSize(14);
  pdf.text(title, MARGIN, MARGIN);
  await svg2pdf(svg, pdf, { x: MARGIN, y: MARGIN + 18, width, height });
}

/**
 * Écrit le PDF. `blank` et `solution` sont les deux SVG déjà rendus par la page ; la solution est
 * facultative — une grille qu'on envoie à quelqu'un ne part pas toujours avec sa réponse.
 */
export async function exportPdf(
  name: string,
  blank: SVGSVGElement,
  solution: SVGSVGElement | null,
) {
  const pdf = new jsPDF({ unit: "pt", format: "a4", orientation: "portrait" });
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
  download(new Blob([JSON.stringify(content, null, 2)], { type: "application/json" }), safeFilename(name, "json"));
}
