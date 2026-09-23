import { expect, test } from "@playwright/test";

/**
 * Supprimer son compte depuis l'interface (#79).
 *
 * Crée un compte jetable, comme `saved-grids.spec.ts` : `RATELIMIT_REGISTER` vaut « 5 par heure »
 * hors de la CI, donc enchaîner les exécutions en local finit par buter sur le quota.
 */
test("un compte se supprime depuis Mon compte, mot de passe à l'appui", async ({ page }) => {
  const email = `compte_${Date.now()}@test.com`;
  const password = "TestPassword123";

  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mot de passe").fill(password);
  await page.getByRole("button", { name: "Créer un compte" }).click();
  await expect(page.getByTestId("logout-button")).toBeVisible();

  await page.goto("/account");
  await expect(page.getByText(email)).toBeVisible();
  await expect(page.getByText(/Votre compte contient \d+ dictionnaires?, 0 mot et 0 grille conservée/)).toBeVisible();

  // Un mauvais mot de passe ne supprime rien, et ne déconnecte pas
  await page.getByLabel("Votre mot de passe, pour confirmer").fill("pas-le-bon");
  await page.getByRole("button", { name: "Supprimer mon compte…" }).click();
  await page.getByRole("button", { name: "Supprimer définitivement" }).click();
  await expect(page.getByText("Mot de passe incorrect.")).toBeVisible();
  await expect(page.getByTestId("logout-button")).toBeVisible();

  await page.getByLabel("Votre mot de passe, pour confirmer").fill(password);
  await page.getByRole("button", { name: "Supprimer mon compte…" }).click();
  await expect(page.getByRole("dialog")).toContainText(email);
  await page.getByRole("button", { name: "Supprimer définitivement" }).click();

  await expect(page).toHaveURL("/");
  await expect(page.getByTestId("login-button-link")).toBeVisible();

  // Le compte n'existe plus
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mot de passe").fill(password);
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByTestId("logout-button")).toBeHidden();
});
