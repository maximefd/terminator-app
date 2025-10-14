import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // Dossier où se trouvent nos fichiers de test
  testDir: './tests',
  
  // Temps maximum pour un test avant de l'arrêter (30 secondes)
  timeout: 30 * 1000,
  
  expect: {
    // Temps maximum pour qu'une assertion (ex: "s'attendre à ce que ce texte apparaisse") réussisse
    timeout: 5000
  },

  // Exécuter les tests en parallèle
  fullyParallel: true,

  // Nombre de tentatives si un test échoue
  retries: process.env.CI ? 2 : 0,

  // Le plus important : on dit à Playwright de lancer notre serveur de développement avant de commencer
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },

  // On peut configurer les navigateurs sur lesquels on veut tester
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
