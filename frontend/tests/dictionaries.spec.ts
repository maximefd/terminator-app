import { expect, test } from "@playwright/test";

/**
 * Parcours complet d'un dictionnaire personnel : créer, ajouter un mot, supprimer le dictionnaire.
 *
 * Ce chemin ne s'atteint qu'une fois connecté ; le test crée donc un compte jetable, comme
 * `auth.spec.ts`. L'API et sa base de développement doivent tourner (`make dev-api`).
 *
 * Attention en local : `RATELIMIT_REGISTER` vaut « 5 par heure ». Enchaîner les exécutions finit par
 * faire échouer l'inscription — ce n'est pas le test qui casse, c'est le quota.
 */
const signUp = async (page: import("@playwright/test").Page) => {
  const email = `dico_${Date.now()}@test.com`;
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mot de passe").fill("TestPassword123");
  await page.getByRole("button", { name: "Créer un compte" }).click();
  await expect(page.getByTestId("logout-button")).toBeVisible();
};

test("un compte neuf, un dictionnaire, un mot, puis plus rien", async ({ page }) => {
  await signUp(page);
  await page.goto("/dictionaries");

  // L'API donne un « Dictionnaire par défaut » à tout compte neuf, et en recrée un dès que la liste est vide
  await expect(page.getByRole("combobox", { name: "Dictionnaire actif" })).toContainText("Dictionnaire par défaut");

  await page.getByRole("button", { name: "Créer un dictionnaire" }).click();
  await page.getByLabel("Nom").fill("Musique");
  await page.getByRole("button", { name: "Créer le dictionnaire" }).click();

  await expect(page.getByRole("combobox", { name: "Dictionnaire actif" })).toContainText("Musique");

  // Un mot et sa définition : la définition doit se voir dans la liste, pas seulement à la saisie
  await page.getByLabel("Nouveau mot").fill("TEMPO");
  await page.getByLabel("Définition (optionnel)").fill("Il donne la cadence");
  await page.getByRole("button", { name: "Ajouter le mot" }).click();

  // exact : la notification « Le mot "TEMPO" a été ajouté » contient aussi le mot
  await expect(page.getByText("TEMPO", { exact: true })).toBeVisible();
  await expect(page.getByText("Il donne la cadence")).toBeVisible();

  // Suppression du mot : le bouton n'apparaît qu'au survol ou au focus, et porte un nom
  await page.getByRole("button", { name: "Supprimer TEMPO" }).click();
  await expect(page.getByText(/Ce dictionnaire est vide/)).toBeVisible();

  // Suppression du dictionnaire : confirmation nommée, puis retour au dictionnaire restant
  await page.getByRole("button", { name: "Supprimer ce dictionnaire" }).click();
  await expect(page.getByText(/Supprimer « Musique » \?/)).toBeVisible();
  await page.getByRole("button", { name: "Supprimer définitivement" }).click();

  // L'actif supprimé, un autre doit prendre le relais : sinon la recherche perd les mots personnels
  await expect(page.getByRole("combobox", { name: "Dictionnaire actif" })).toContainText("Dictionnaire par défaut");
});

test("les dictionnaires demandent un compte, sans faire croire qu'ils sont vides", async ({ page }) => {
  await page.goto("/dictionaries");

  await expect(page.getByText("Un compte est nécessaire ici")).toBeVisible();
  await expect(page.getByRole("link", { name: "Créer un compte" })).toBeVisible();
});
