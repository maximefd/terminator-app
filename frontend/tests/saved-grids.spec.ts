import { expect, test } from "@playwright/test";

/**
 * Générer une grille, la conserver, la retrouver, la supprimer (#24).
 *
 * Comme `dictionaries.spec.ts`, ce parcours crée un compte jetable ; `RATELIMIT_REGISTER` vaut
 * « 5 par heure », donc enchaîner les exécutions en local finit par buter sur le quota.
 */
test("une grille générée se conserve et se retrouve", async ({ page }) => {
  test.setTimeout(120_000);

  await page.goto("/register");
  await page.getByLabel("Email").fill(`grilles_${Date.now()}@test.com`);
  await page.getByLabel("Mot de passe").fill("TestPassword123");
  await page.getByRole("button", { name: "Créer un compte" }).click();
  await expect(page.getByTestId("logout-button")).toBeVisible();

  await page.goto("/grid");
  await page.getByRole("button", { name: "Générer la grille" }).click();
  // Budget serveur : 20 s, et la première génération charge le lexique
  await expect(page.getByText(/% de vos mots/)).toBeVisible({ timeout: 60_000 });

  await page.getByLabel("Nom (facultatif)").fill("Essai du parcours");
  await page.getByRole("button", { name: "Conserver cette grille" }).click();
  await expect(page.getByText("Grille conservée.")).toBeVisible();

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
