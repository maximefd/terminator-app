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
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});

