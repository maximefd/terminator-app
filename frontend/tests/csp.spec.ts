import { expect, test } from "@playwright/test";

/**
 * CSP par empreinte du site statique (#99) : chaque page n'exécute que ses propres scripts inline.
 *
 * Ne vaut que pour l'export statique (`pnpm build`, servi depuis `out/`) : `next dev` n'a pas de CSP par page
 * et garde 'unsafe-inline'. Sur le serveur de dev, ces tests sont ignorés.
 */
const PAGES = ["/", "/search", "/grid", "/grids", "/dictionaries", "/login", "/register", "/account", "/privacy",
  "/legal", "/forgot-password", "/grids/edit?id=1", "/page-inexistante"];

for (const path of PAGES) {
  test(`${path} : ses scripts passent, et rien d'autre`, async ({ page }) => {
    const violations: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error" && /Content Security Policy/i.test(message.text())) {
        violations.push(message.text());
      }
    });

    await page.goto(path);
    const csp = page.locator('meta[http-equiv="Content-Security-Policy"]');
    test.skip((await csp.count()) === 0, "pas d'export statique (serveur de dev)");

    // L'application a pris la main : l'en-tête est interactif, donc les scripts de rendu ont tourné
    await expect(page.getByTestId("logo-link")).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(violations, "scripts de la page bloqués par sa propre CSP").toEqual([]);

    // Un script injecté, lui, est refusé
    const ran = await page.evaluate(() => {
      (window as unknown as { injected?: boolean }).injected = false;
      const script = document.createElement("script");
      script.textContent = "window.injected = true";
      document.head.appendChild(script);
      return (window as unknown as { injected?: boolean }).injected;
    });
    expect(ran).toBe(false);
  });
}
