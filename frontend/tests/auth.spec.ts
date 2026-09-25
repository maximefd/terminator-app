import { test, expect } from "@playwright/test";

test.describe("Authentication Flow", () => {
  
  test("should allow browsing the homepage as a guest", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByTestId("logo-link")).toBeVisible();
    await expect(page.getByTestId("login-button-link")).toBeVisible();
  });

  test("l'adresse saisie suit d'un formulaire à l'autre, pas le mot de passe", async ({ page }) => {
    // On tape son adresse pour s'inscrire, puis on se rend compte qu'on a déjà un compte
    await page.goto("/register");
    await page.getByLabel("Email").fill("deja.inscrit@test.com");
    await page.getByLabel("Mot de passe").fill("UnMotDePasse123");
    await page.getByRole("link", { name: "Se connecter" }).last().click();
    await expect(page.getByTestId("login-title")).toBeVisible();
    await expect(page.getByLabel("Email")).toHaveValue("deja.inscrit@test.com");
    await expect(page.getByLabel("Mot de passe")).toHaveValue("");

    // Et l'inverse, en corrigeant au passage
    await page.getByLabel("Email").fill("nouveau@test.com");
    await page.getByRole("link", { name: "S'inscrire" }).click();
    await expect(page.getByTestId("register-title")).toBeVisible();
    await expect(page.getByLabel("Email")).toHaveValue("nouveau@test.com");

    // L'adresse ne passe jamais par l'adresse de la page
    expect(page.url()).not.toContain("nouveau");
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

  // Après l'inscription (ou la connexion), `next` ne fait jamais sortir du site : le navigateur retire
  // tabulations et retours à la ligne d'une adresse et lit « \ » comme « / », d'où `/⇥/exemple.com` → exemple.com
  for (const next of ["%2F%09%2Fexemple.com", "%2F%0A%2Fexemple.com", "%2F%2Fexemple.com", "%2F%5Cexemple.com",
    "https%3A%2F%2Fexemple.com"]) {
    test(`next=${next} ramène à l'accueil, jamais sur un autre site`, async ({ page }) => {
      await page.goto(`/register?next=${next}`);
      await page.getByLabel("Email").fill(`redirection_${Date.now()}_${Math.random().toString(36).slice(2, 8)}@test.com`);
      await page.getByLabel("Mot de passe").fill("TestPassword123");
      await page.getByRole("button", { name: "Créer un compte" }).click();
      await expect(page).toHaveURL("/");
      await expect(page.getByTestId("logout-button")).toBeVisible();
    });
  }

  test("un chemin interne dans `next` est bien suivi après l'inscription", async ({ page }) => {
    await page.goto("/register?next=%2Fsearch");
    await page.getByLabel("Email").fill(`redirection_ok_${Date.now()}@test.com`);
    await page.getByLabel("Mot de passe").fill("TestPassword123");
    await page.getByRole("button", { name: "Créer un compte" }).click();
    await expect(page).toHaveURL("/search");
  });
});

