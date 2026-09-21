import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';

// On lit le fichier .env qui se trouve à la racine de notre projet frontend
dotenv.config({ path: path.resolve(__dirname, '.env') });

export default defineConfig({
  testDir: './tests',
  timeout: 30 * 1000,
  expect: {
    timeout: 5000
  },
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,

  // `screenshots.spec.ts` ne teste rien : il régénère les captures du README, dans docs/images.
  // Il n'a rien à faire en CI, où il salirait l'arbre de travail.
  testIgnore: process.env.CI ? ['**/screenshots.spec.ts'] : [],

  use: {
    // On utilise la variable d'environnement, avec un fallback sécurisé sur localhost
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
  },

  webServer: {
    // On s'assure que le serveur de dev écoute bien sur toutes les adresses
    command: 'pnpm dev --hostname 0.0.0.0',
    // On utilise la même URL que le baseURL pour que Playwright sache quand le serveur est prêt
    url: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    // Démarrage à froid en CI : Next compile chaque page à la première visite
    timeout: 180 * 1000,
  },

  projects: [
    {
      name: 'chromium',
      // channel 'chrome' : on utilise le Google Chrome installé sur la machine, ce qui évite
      // `playwright install chromium` (son téléchargement se fige sur la machine de l'auteur,
      // alors que le même fichier se télécharge normalement avec curl). En CI, où le navigateur
      // est installé proprement par `playwright install`, on prend le Chromium de Playwright.
      use: { ...devices['Desktop Chrome'], channel: process.env.CI ? undefined : 'chrome' },
    },
  ],
});

