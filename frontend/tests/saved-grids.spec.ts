import { expect, test } from "@playwright/test";

/**
 * Générer une grille sans compte, s'inscrire, la conserver, la retrouver, la supprimer (#24).
 *
 * Le parcours commence en invité : c'est le cas où l'on perdait sa grille — générée, appréciée,
 * puis envolée pendant l'inscription.
 *
 * Comme `dictionaries.spec.ts`, ce parcours crée un compte jetable ; `RATELIMIT_REGISTER` vaut
 * « 5 par heure », donc enchaîner les exécutions en local finit par buter sur le quota.
 */
test("une grille générée se conserve et se retrouve", async ({ page }) => {
  test.setTimeout(120_000);

  await page.goto("/grid");
  // Les mots imposés sont une option, et l'écran le dit
  await expect(page.getByRole("heading", { name: /Imposer des mots\s*\(facultatif\)/ })).toBeVisible();
  // Le bouton radio est masqué sous sa vignette : c'est elle qu'on clique, comme un visiteur
  await page.locator("label").filter({ hasText: /^6\s*×\s*7$/ }).click();
  await expect(page.getByRole("radio", { name: /6\s*×\s*7/ })).toBeChecked();

  // Un mot facile arrive obligatoire ; un mot qui ferait tomber les chances sous 70 %, souhaité
  const mot = page.getByLabel("Mot à placer dans la grille");
  await mot.fill("PORTE");
  await mot.press("Enter");
  await expect(page.getByRole("button", { name: "PORTE obligatoire" })).toHaveAttribute("aria-pressed", "true");
  // On attend la décision elle-même : avant elle, le mot est déjà affiché non coché
  const decision = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/grids/difficulty") &&
      (response.request().postData() ?? "").includes("ANTICONSTITUTIONNEL"),
  );
  await mot.fill("ANTICONSTITUTIONNEL");
  await mot.press("Enter");
  await decision;
  await expect(page.getByRole("button", { name: "ANTICONSTITUTIONNEL obligatoire" })).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  // La grille du parcours se génère sans mot imposé : on les retire
  await page.getByRole("button", { name: "Retirer PORTE" }).click();
  await page.getByRole("button", { name: "Retirer ANTICONSTITUTIONNEL" }).click();

  await page.getByRole("button", { name: "Générer la grille" }).click();
  // Budget serveur : 20 s, et la première génération charge le lexique
  await expect(page.getByText("Cette grille vous plaît ?")).toBeVisible({ timeout: 60_000 });
  const firstWord = (await page.locator("details ul li").first().textContent())?.trim();

  // L'inscription ramène à la grille, qui a attendu
  await page.getByRole("link", { name: "Créer un compte" }).click();
  await expect(page).toHaveURL(/\/register\?next=%2Fgrid/);
  await page.getByLabel("Email").fill(`grilles_${Date.now()}@test.com`);
  await page.getByLabel("Mot de passe").fill("TestPassword123");
  await page.getByRole("button", { name: "Créer un compte" }).click();
  await expect(page).toHaveURL(/\/grid$/);
  await expect(page.getByTestId("logout-button")).toBeVisible();
  await expect(page.locator("details ul li").first()).toHaveText(firstWord ?? "");
  await expect(page.getByRole("radio", { name: /6\s*×\s*7/ })).toBeChecked();

  await page.getByLabel("Nom (facultatif)").fill("Essai du parcours");
  await page.getByRole("button", { name: "Conserver cette grille" }).click();
  await expect(page.getByText("Grille conservée : « Essai du parcours »")).toBeVisible();

  // L'étape suivante est proposée franchement, et elle commence par la relecture des mots
  await page.getByRole("link", { name: "Relire et écrire les définitions" }).click();
  await expect(page.getByRole("heading", { name: "Essai du parcours" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Relire les mots/ })).toHaveAttribute("aria-current", "step");

  await page.goto("/grids");
  const saved = page.getByRole("listitem").filter({ hasText: "Essai du parcours" });
  await expect(saved).toBeVisible();
  // La liste ne transporte que des résumés : l'avancement des définitions est ce qu'on y cherche
  await expect(saved.getByText(/définition|Définitions complètes/)).toBeVisible();
  // Et sa silhouette, dessinée depuis la forme envoyée avec le résumé — c'est ce qu'on reconnaît
  await expect(saved.getByRole("img", { name: /Silhouette d'une grille 6 sur 7/ })).toBeVisible();

  // Archiver range la grille sans rien perdre : elle sort de la liste de travail, pas de la base
  await saved.getByRole("button", { name: "Archiver" }).click();
  await expect(page.getByText(/Aucune grille ne correspond/)).toBeVisible();
  await page.getByRole("button", { name: "Voir les grilles archivées" }).click();
  await expect(saved).toBeVisible();

  await saved.getByRole("button", { name: "Supprimer Essai du parcours" }).click();
  await expect(page.getByText(/Aucune grille conservée|Aucune grille ne correspond/)).toBeVisible();
});
