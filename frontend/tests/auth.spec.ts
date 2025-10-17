import { test, expect } from "@playwright/test";

test.describe("Authentication Flow", () => {
  
  test("should allow browsing the homepage as a guest", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("logo-link")).toBeVisible();
    await expect(page.getByTestId("login-button-link")).toBeVisible();
  });

  test("user can register, log out, and log back in", async ({ page }) => {
    const email = `user_${Date.now()}@test.com`;
    const password = "TestPassword123";

    // --- Étape 1 : Inscription ---
    await page.goto("/register");
    
    // CORRECTION ICI : On cherche le titre par son "data-testid"
    await expect(page.getByTestId('register-title')).toBeVisible();

    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Mot de passe').fill(password);
    await page.getByRole('button', { name: 'Créer un compte' }).click();

    // --- Étape 2 : Vérification post-inscription ---
    await expect(page).toHaveURL("/");
    await expect(page.getByTestId("logout-button")).toBeVisible();

    // --- Étape 3 : Déconnexion ---
    await page.getByTestId("logout-button").click();
    await expect(page.getByTestId("login-button-link")).toBeVisible();

    // --- Étape 4 : Reconnexion ---
    await page.getByTestId("login-button-link").click();
    
    // CORRECTION ICI : Même logique pour la page de connexion.
    await expect(page.getByTestId('login-title')).toBeVisible();

    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Mot de passe').fill(password);
    await page.getByRole('button', { name: 'Se connecter' }).click();

    // --- Étape 5 : Vérification finale ---
    await expect(page).toHaveURL("/");
    await expect(page.getByTestId("logout-button")).toBeVisible();
  });
});

