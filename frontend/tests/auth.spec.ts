import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {

  test('should allow browsing the homepage as a guest', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Recherche de mots | Terminator/);
    await expect(page.getByTestId('logo-link')).toBeVisible();
  });

  test('should allow a user to register, log out, and log back in', async ({ page }) => {
    const uniqueEmail = `user-${Date.now()}@example.com`;
    const password = 'password123';

    // --- Étape 1 : Inscription ---
    await page.goto('/register');
    await page.getByLabel('Email').fill(uniqueEmail);
    await page.getByLabel('Mot de passe').fill(password);
    await page.getByRole('button', { name: 'Créer un compte' }).click();

    // --- Étape 2 : Vérification (la nouvelle méthode) ---
    // Avant de vérifier la redirection, on s'assure qu'AUCUN message d'erreur n'est apparu.
    // S'il y en a un, le test échouera ici et nous montrera le message.
    const errorMessage = page.locator('p.text-destructive');
    await expect(errorMessage).not.toBeVisible();
    
    // Si aucune erreur n'est apparue, ALORS on vérifie la redirection.
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('button', { name: 'Déconnexion' })).toBeVisible();

    // --- Étape 3 : Déconnexion ---
    await page.getByRole('button', { name: 'Déconnexion' }).click();
    await expect(page.getByRole('button', { name: 'Connexion' })).toBeVisible();
    
    // --- Étape 4 : Reconnexion ---
    await page.getByRole('button', { name: 'Connexion' }).click();
    await expect(page).toHaveURL('/login');
    await page.getByLabel('Email').fill(uniqueEmail);
    await page.getByLabel('Mot de passe').fill(password);
    await page.getByRole('button', { name: 'Se connecter' }).click();
    
    // --- Étape 5 : Vérification Finale ---
    await expect(page).toHaveURL('/');
    await expect(page.getByRole('button', { name: 'Déconnexion' })).toBeVisible();
  });

});