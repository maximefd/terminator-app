import { expect, test } from "@playwright/test";

/**
 * Le poste de pilotage (ADR 0016, point 6) : la page est dans l'export statique, donc publique, mais tout autre
 * visiteur que l'administrateur n'y voit que la page 404. Les chiffres, eux, sont gardés par l'API (test_admin.py).
 */
test("un visiteur voit la page 404 sur /admin", async ({ page }) => {
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Cette page n'existe pas" })).toBeVisible();
  await expect(page.getByText("Poste de pilotage")).toHaveCount(0);
});

test("un compte ordinaire aussi", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Email").fill(`pilotage_${Date.now()}@test.com`);
  await page.getByLabel("Mot de passe").fill("TestPassword123");
  await page.getByRole("button", { name: "Créer un compte" }).click();
  await expect(page.getByTestId("logout-button")).toBeVisible();

  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Cette page n'existe pas" })).toBeVisible();
  await expect(page.getByText("Poste de pilotage")).toHaveCount(0);
});

test("la page n'est liée nulle part sur l'accueil", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator('a[href*="admin"]')).toHaveCount(0);
});
