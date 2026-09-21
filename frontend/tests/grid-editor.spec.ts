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

  // Le premier mot est choisi d'office : on arrive et on écrit, sans clic d'amorçage
  await expect(page.getByLabel("Définition de AS")).toBeFocused();

  // Enregistrement au fil de la frappe : rien à cliquer. On attend la requête elle-même, et non
  // le compteur de l'écran — il compte l'état local, qui a déjà bougé avant que rien ne soit parti.
  const saved = page.waitForResponse(
    (response) => response.url().endsWith(`/api/grids/${gridId}`) && response.request().method() === "PATCH",
  );
  await page.getByLabel("Définition de AS").fill("Champion");
  expect((await saved).status()).toBe(200);

  // Tab passe au mot suivant sans lâcher le clavier : c'est ainsi qu'on définit une grille entière
  await page.getByLabel("Définition de AS").press("Tab");
  await expect(page.getByLabel("Définition de ILE")).toBeFocused();
  await page.getByLabel("Définition de ILE").press("Shift+Tab");
  await expect(page.getByLabel("Définition de AS")).toBeFocused();

  await page.reload();
  await expect(page.getByRole("button", { name: /AS\s+Champion/ })).toBeVisible();

  // La définition s'écrit dans la case en capitales accentuées, comme dans les magazines, alors que
  // la saisie reste telle que l'auteur l'a tapée
  await expect(page.locator("svg tspan").filter({ hasText: /^CHAMPION$/ }).first()).toBeVisible();
  await expect(page.getByLabel("Définition de AS")).toHaveValue("Champion");

  // Le gras se coupe, et le réglage survit au rechargement
  await page.getByRole("button", { name: "Définitions en gras" }).click();
  await expect(page.locator("svg tspan").filter({ hasText: /^CHAMPION$/ }).first()).toHaveAttribute(
    "x", /\d/,
  );
  await page.reload();
  await expect(page.getByRole("button", { name: "Définitions en gras" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await page.getByRole("button", { name: "Définitions en gras" }).click();

  // L'aperçu montre la grille telle qu'elle s'imprime : définitions et flèches, sans les lettres
  await page.getByRole("button", { name: "Aperçu imprimé" }).click();
  await expect(page.locator("svg[role='img']").first().locator("tspan", { hasText: "Champion" })).toBeVisible();
  await page.getByRole("button", { name: "Définitions", exact: true }).click();

  // La page de solution ne porte ni flèche ni définition : elle sert à vérifier des lettres.
  // Les pointes de flèches sont les seuls polygones du dessin.
  const grids = page.locator("svg[role='img']");
  expect(await grids.nth(1).locator("polygon").count()).toBeGreaterThan(0);
  expect(await grids.nth(2).locator("polygon").count()).toBe(0);
  expect(await grids.nth(2).locator("tspan").count()).toBe(0);

  // L'export PDF : le fichier, et ce qu'il y a dedans. Un PDF vide porterait le même nom.
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "PDF + solution" }).click();
  const pdf = await download;
  expect(pdf.suggestedFilename()).toBe("grille-a-definir.pdf");

  const pdfPath = path.join(test.info().outputDir, "grille.pdf");
  await pdf.saveAs(pdfPath);
  const bytes = readFileSync(pdfPath);
  const raw = bytes.toString("latin1");

  expect(bytes.subarray(0, 5).toString()).toBe("%PDF-");
  // Deux pages : la grille et sa solution
  expect(raw.match(/\/Type\s*\/Page[^s]/g)?.length).toBe(2);
  // La police du dessin est embarquée — sans elle, le convertisseur retombe sur une serif large.
  // C'est aussi pourquoi on ne cherche plus le texte en clair : il est encodé par cette police.
  expect(raw).toContain("ArchivoNarrow");
  // Le dessin est là : les traits de la grille (opérateur « l ») et du texte (opérateur « Tj »).
  // Le texte s'écrit en hexadécimal, encodé par la police embarquée — d'où ce contrôle indirect.
  expect((raw.match(/\sl\s/g) ?? []).length).toBeGreaterThanOrEqual(20);
  expect((raw.match(/Tj/g) ?? []).length).toBeGreaterThanOrEqual(2);

  // Une définition trop longue est annoncée pendant qu'on l'écrit, et non découverte à l'impression
  await page.getByRole("button", { name: /^ILE/ }).click();
  await page.getByLabel("Définition de ILE").fill(
    "Une définition beaucoup trop longue pour tenir dans une demi-case de grille",
  );
  await expect(page.getByText(/Trop longue pour la case/)).toBeVisible();
  await page.getByLabel("Définition de ILE").fill("Terre entourée d'eau");
  await expect(page.getByText(/Trop longue pour la case/)).toHaveCount(0);

  // Renommer : l'API le permettait déjà, l'écran ne l'atteignait pas
  await page.getByRole("button", { name: "Renommer la grille" }).click();
  await page.getByLabel("Nom de la grille").fill("Grille renommée");
  await page.getByLabel("Nom de la grille").press("Enter");
  await expect(page.getByRole("heading", { name: "Grille renommée" })).toBeVisible();

  // --- Mode lettres : corriger la grille à la main (ADR 0012) ---
  await page.getByRole("button", { name: "Lettres" }).click();
  // La case (1,1) porte le L de ILE : on en fait un Z, mot que le lexique ne connaît pas
  await page.locator("svg rect.cursor-text").nth(3).click();
  await page.keyboard.press("z");
  await expect(page.getByText(/hors lexique/)).toBeVisible();
  await expect(page.getByRole("button", { name: /^Ajouter$/ }).first()).toBeVisible();

  // Les propositions ne cassent aucun croisement : en cliquer une réécrit le mot entier.
  // « Remplacer le mot » plutôt que « combler les trous » : ici on veut un autre mot, pas le même.
  await page.locator("svg rect.cursor-text").nth(2).click();
  await page.getByRole("button", { name: "Remplacer le mot" }).click();
  const suggestion = page.locator("li > button.font-mono").first();
  await expect(suggestion).toBeVisible({ timeout: 15_000 });
  const mot = (await suggestion.textContent())?.trim() ?? "";
  await suggestion.click();
  await expect(page.locator("svg text").filter({ hasText: new RegExp(`^${mot[0]}$`) }).first()).toBeVisible();

  // --- Effacer : le trou est un état de travail, pas une anomalie ---
  await page.locator("svg rect.cursor-text").nth(4).click();
  await page.keyboard.press("Backspace");
  await expect(page.getByText(/Inachevé/)).toBeVisible();
  // Le mot garde sa longueur : le trou ne raccourcit rien
  await expect(page.getByText(/3 lettres/)).toBeVisible();

  // Les propositions comblent le trou en gardant ce qui reste en place
  await page.getByRole("button", { name: "Combler les trous" }).click();
  const comble = page.locator("li > button.font-mono").first();
  await expect(comble).toBeVisible({ timeout: 15_000 });

  // Annuler rend la lettre effacée ; rétablir la retire de nouveau
  await page.getByRole("button", { name: "Annuler" }).click();
  await expect(page.getByText(/Inachevé/)).toHaveCount(0);
  await page.getByRole("button", { name: "Rétablir" }).click();
  await expect(page.getByText(/Inachevé/)).toBeVisible();
  await page.getByRole("button", { name: "Annuler" }).click();

  // --- Le bloc-notes suit la grille ---
  await page.getByLabel("Notes").fill("Idée : thème musique");
  // On attend l'enregistrement **des notes**, et non n'importe quel PATCH : les lettres en écrivent
  // aussi, et attendre le mauvais rechargerait la page avant que le texte ne soit parti.
  await page.waitForResponse(
    (response) =>
      response.url().endsWith(`/api/grids/${gridId}`) &&
      response.request().method() === "PATCH" &&
      (response.request().postData() ?? "").includes("notes"),
  );
  await page.reload();
  await expect(page.getByLabel("Notes")).toHaveValue("Idée : thème musique");

  const workFile = page.waitForEvent("download");
  await page.getByRole("button", { name: "Fichier de travail" }).click();
  expect((await workFile).suggestedFilename()).toBe("grille-renommee.json");
});
