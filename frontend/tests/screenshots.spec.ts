import path from "node:path";

import { expect, test, type Page } from "@playwright/test";

/**
 * Captures d'écran du README (#8). L'API et le frontend doivent tourner :
 *   make dev-api    # http://localhost:5001
 *   make dev-front  # http://localhost:3000
 *   cd frontend && pnpm exec playwright test tests/screenshots.spec.ts
 * Les images sont écrites dans docs/images/ et versionnées.
 */
const IMAGES_DIR = path.join(__dirname, "..", "..", "docs", "images");

test.use({ viewport: { width: 1280, height: 860 }, deviceScaleFactor: 2, colorScheme: "light" });
// La configuration limite un test à 30 s : une génération peut dépasser ce délai
test.setTimeout(90_000);

// L'indicateur de développement de Next.js n'a rien à faire sur une capture du README
const hideDevIndicator = (page: Page) =>
  page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });

test("recherche par motif", async ({ page }) => {
  await page.goto("/");
  await hideDevIndicator(page);
  await page.getByPlaceholder(/Ex:/).fill("P??LE");

  await expect(page.getByText(/\d+ résultats?/)).toBeVisible({ timeout: 20_000 });

  await page.screenshot({ path: path.join(IMAGES_DIR, "recherche.png") });
});

test("génération d'une grille", async ({ page }) => {
  await page.goto("/grid");
  await hideDevIndicator(page);
  await page.getByRole("button", { name: "Générer la grille" }).click();

  // La génération peut prendre plusieurs secondes (budget serveur : 20 s)
  await expect(page.getByText(/Taux de remplissage/)).toBeVisible({ timeout: 45_000 });

  await page.screenshot({ path: path.join(IMAGES_DIR, "generation.png"), fullPage: true });
});
