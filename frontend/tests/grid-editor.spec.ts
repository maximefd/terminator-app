import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

/**
 * L'éditeur de définitions et l'export (#27).
 *
 * La grille est créée par l'API plutôt que générée depuis l'écran : ce test porte sur l'édition,
 * et une génération vraie le rendrait lent et dépendant du lexique chargé.
 */
const API = process.env.PLAYWRIGHT_API_URL || "http://localhost:5001";

const GRID = {
  width: 3,
  height: 2,
  layout: "3x2-001",
  seed: 7,
  cells: [
    { x: 0, y: 0, char: "", is_black: true },
    { x: 1, y: 0, char: "A", is_black: false },
    { x: 2, y: 0, char: "S", is_black: false },
    { x: 0, y: 1, char: "I", is_black: false },
    { x: 1, y: 1, char: "L", is_black: false },
    { x: 2, y: 1, char: "E", is_black: false },
  ],
  words: [
    { text: "AS", x: 1, y: 0, direction: "across", source: "common" },
    { text: "ILE", x: 0, y: 1, direction: "across", source: "common" },
  ],
  fill_ratio: 1,
  wish_ratio: 0,
  must_words: [],
};

test("écrire les définitions d'une grille, puis l'exporter", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Email").fill(`editeur_${Date.now()}@test.com`);
  await page.getByLabel("Mot de passe").fill("TestPassword123");
  await page.getByRole("button", { name: "Créer un compte" }).click();
  await expect(page.getByTestId("logout-button")).toBeVisible();

  const gridId = await page.evaluate(
    async ([api, grid]) => {
      const response = await fetch(`${api}/api/grids`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
        body: JSON.stringify({ name: "Grille à définir", grid }),
      });
      return (await response.json()).id as number;
    },
    [API, GRID] as const,
  );

  await page.goto(`/grids/${gridId}`);
  await expect(page.getByRole("heading", { name: "Grille à définir" })).toBeVisible();
  await expect(page.getByText("0 définition sur 2")).toBeVisible();

  // Choisir un mot dans la liste, écrire sa définition
  await page.getByRole("button", { name: /^AS/ }).click();

  // Enregistrement au fil de la frappe : rien à cliquer. On attend la requête elle-même, et non
  // le compteur de l'écran — il compte l'état local, qui a déjà bougé avant que rien ne soit parti.
  const saved = page.waitForResponse(
    (response) => response.url().endsWith(`/api/grids/${gridId}`) && response.request().method() === "PATCH",
  );
  await page.getByLabel(/Horizontal/).fill("Champion");
  expect((await saved).status()).toBe(200);

  await page.reload();
  await expect(page.getByRole("button", { name: /AS\s+Champion/ })).toBeVisible();

  // La définition s'écrit dans la case, à côté de sa flèche
  await expect(page.locator("svg tspan", { hasText: "Champion" }).first()).toBeVisible();

  // L'export PDF : le fichier, et ce qu'il y a dedans. Un PDF vide porterait le même nom.
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "PDF + solution" }).click();
  const pdf = await download;
  expect(pdf.suggestedFilename()).toBe("grille-a-definir.pdf");

  const pdfPath = path.join(test.info().outputDir, "grille.pdf");
  await pdf.saveAs(pdfPath);
  const bytes = readFileSync(pdfPath);
  expect(bytes.subarray(0, 5).toString()).toBe("%PDF-");
  // Deux pages : la grille et sa solution
  expect(bytes.toString("latin1").match(/\/Type\s*\/Page[^s]/g)?.length).toBe(2);
  // Le dessin est bien parti dans le PDF, et pas seulement son titre
  expect(bytes.toString("latin1")).toContain("Champion");

  const workFile = page.waitForEvent("download");
  await page.getByRole("button", { name: "Fichier de travail" }).click();
  expect((await workFile).suggestedFilename()).toBe("grille-a-definir.json");
});
