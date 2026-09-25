import { expect, test } from "@playwright/test";

/**
 * Référencement (#113) : les pages publiques ont un titre, une description, une canonique et un aperçu de
 * partage ; les pages privées sont en `noindex` ; robots.txt et le sitemap sont servis.
 *
 * L'adresse attendue est celle du site (src/config/site.ts), sauf si NEXT_PUBLIC_SITE_URL la remplace.
 */
const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "https://leflechoir.fr").replace(/\/+$/, "");

const PUBLIC_PAGES = [
  { path: "/", title: "Le Fléchoir — l'atelier des mots fléchés", canonical: SITE_URL },
  { path: "/search", title: "Recherche de mots | Le Fléchoir", canonical: `${SITE_URL}/search` },
  { path: "/grid", title: "Générer une grille | Le Fléchoir", canonical: `${SITE_URL}/grid` },
  { path: "/contact", title: "Contact | Le Fléchoir", canonical: `${SITE_URL}/contact` },
  { path: "/legal", title: "Mentions légales | Le Fléchoir", canonical: `${SITE_URL}/legal` },
  { path: "/privacy", title: "Confidentialité | Le Fléchoir", canonical: `${SITE_URL}/privacy` },
  { path: "/terms", title: "Conditions d'utilisation | Le Fléchoir", canonical: `${SITE_URL}/terms` },
];

const PRIVATE_PAGES = ["/account", "/grids", "/grids/edit?id=1", "/dictionaries", "/login", "/register",
  "/forgot-password", "/reset-password", "/verify-email"];

for (const { path, title, canonical } of PUBLIC_PAGES) {
  test(`${path} : indexable, avec titre, description, canonique et aperçu`, async ({ page }) => {
    await page.goto(path);

    await expect(page).toHaveTitle(title);
    await expect(page.locator('meta[name="description"]')).toHaveAttribute("content", /.{50,}/);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", canonical);
    await expect(page.locator('meta[property="og:image"]')).toHaveAttribute("content", `${SITE_URL}/og.png`);
    await expect(page.locator('meta[name="robots"]')).toHaveCount(0);
    expect(await page.title()).not.toContain("Terminator");
  });
}

for (const path of PRIVATE_PAGES) {
  test(`${path} : en noindex, sans canonique`, async ({ page }) => {
    await page.goto(path);

    await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
    await expect(page.locator('link[rel="canonical"]')).toHaveCount(0);
  });
}

test("l'accueil décrit l'application en données structurées", async ({ page }) => {
  await page.goto("/");

  const json = await page.locator('script[type="application/ld+json"]').textContent();
  expect(JSON.parse(json ?? "{}")).toMatchObject({ "@type": "WebApplication", name: "Le Fléchoir", url: SITE_URL });
});

test("robots.txt ouvre tout le site et donne le sitemap", async ({ request }) => {
  const body = await (await request.get("/robots.txt")).text();

  expect(body).toContain("Allow: /");
  expect(body).not.toContain("Disallow");
  expect(body).toContain(`Sitemap: ${SITE_URL}/sitemap.xml`);
});

test("le sitemap liste les pages publiques, et elles seules", async ({ request }) => {
  const body = await (await request.get("/sitemap.xml")).text();
  const urls = [...body.matchAll(/<loc>(.*?)<\/loc>/g)].map(([, url]) => url);

  expect(urls).toEqual(PUBLIC_PAGES.map(({ canonical }) => canonical));
});

test("l'image de partage est un PNG", async ({ request }) => {
  const response = await request.get("/og.png");

  expect(response.ok()).toBe(true);
  expect(response.headers()["content-type"]).toContain("image/png");
});

test("security.txt donne l'adresse des failles et une date d'expiration de moins d'un an", async ({ request }) => {
  const response = await request.get("/.well-known/security.txt");
  const body = await response.text();

  expect(response.headers()["content-type"]).toContain("text/plain");
  expect(body).toContain("Contact: mailto:securite@leflechoir.fr");
  const expires = Date.parse(body.match(/^Expires: (.+)$/m)?.[1] ?? "");
  expect(expires - Date.now()).toBeGreaterThan(0);
  expect(expires - Date.now()).toBeLessThan(365 * 24 * 60 * 60 * 1000);
});

test("la page contact donne les deux adresses, et le pied de page y mène", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("contentinfo").getByRole("link", { name: "Contact" }).click();

  await expect(page).toHaveURL(/\/contact$/);
  await expect(page.getByRole("link", { name: "contact@leflechoir.fr" })).toHaveAttribute(
    "href", "mailto:contact@leflechoir.fr");
  await expect(page.getByRole("link", { name: "securite@leflechoir.fr" })).toHaveAttribute(
    "href", "mailto:securite@leflechoir.fr");
});

test("les pages publiques ne renvoient plus vers GitHub, qui deviendra privé", async ({ page }) => {
  for (const { path } of PUBLIC_PAGES) {
    await page.goto(path);
    await expect(page.locator('a[href*="github.com"]'), path).toHaveCount(0);
  }
});

test("une adresse inconnue répond en français", async ({ page }) => {
  await page.goto("/page-inexistante");

  await expect(page.getByRole("heading", { name: "Cette page n'existe pas" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Retour à l'accueil" })).toBeVisible();
});
