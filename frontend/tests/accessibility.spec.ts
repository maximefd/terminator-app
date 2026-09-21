import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * Contrôle d'accessibilité automatique (#25).
 *
 * axe ne juge que ce qui se vérifie par le code : contraste, intitulés, rôles, ordre des titres,
 * repères de page. Il ne dit pas si un écran est compréhensible — la [revue UX](../../docs/AUDIT-UX.md)
 * s'en charge. Un écran qui passe axe peut rester mauvais ; un écran qui échoue est inutilisable
 * pour quelqu'un qui navigue au clavier ou au lecteur d'écran.
 */
const PAGES = [
  { path: "/", name: "accueil" },
  { path: "/search", name: "recherche par motif" },
  { path: "/grid", name: "génération" },
  { path: "/grids", name: "mes grilles" },
  { path: "/dictionaries", name: "dictionnaires" },
  { path: "/login", name: "connexion" },
  { path: "/register", name: "inscription" },
];

for (const page of PAGES) {
  test(`aucune violation WCAG A/AA sur ${page.name}`, async ({ page: browserPage }) => {
    await browserPage.goto(page.path);
    // Les boutons désactivés au premier rendu (le temps de charger formats et session) redeviennent
    // actifs par une transition d'opacité. Mesurer pendant cette transition ferait voir à axe un
    // contraste à 50 % qui n'existe qu'un instant : on attend que la page se pose.
    await browserPage.waitForLoadState("networkidle");
    await browserPage.waitForTimeout(400);

    const results = await new AxeBuilder({ page: browserPage })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      // L'indicateur de développement de Next.js n'appartient pas à l'application
      .exclude("nextjs-portal")
      .analyze();

    // En cas d'échec, le message doit nommer la règle et l'élément, pas seulement « 3 violations »
    expect(
      results.violations.map((violation) => ({
        règle: violation.id,
        description: violation.help,
        éléments: violation.nodes.map((node) => node.target.join(" ")),
      })),
    ).toEqual([]);
  });
}
