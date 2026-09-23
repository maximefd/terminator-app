// @ts-check
/**
 * Après `next build` (export statique), sécurise `out/` pour Cloudflare Pages :
 *
 * 1. `out/_headers` : les en-têtes de sécurité, au format de Pages
 *    (https://developers.cloudflare.com/pages/configuration/headers/). Sans ce fichier, l'export partirait sans
 *    CSP ni HSTS : c'est `next dev` seul qui les envoie.
 * 2. Une CSP par page, en `<meta>`, qui n'autorise que les scripts inline de cette page, par leur empreinte
 *    (#99). Next place dans chaque page ses données de rendu en scripts inline ; sans cela, il faudrait
 *    'unsafe-inline', et un script injecté par une faille XSS s'exécuterait.
 */
import { createHash } from 'node:crypto';
import { existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pageScriptPolicy, securityHeaders } from '../security-headers.mjs';

const OUT = fileURLToPath(new URL('../out/', import.meta.url));
if (!existsSync(OUT)) {
  throw new Error("out/ introuvable : lancer d'abord next build (export statique).");
}

// 1. En-têtes
const headers = securityHeaders({
  isDev: false,
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
  sentryDsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
});
const lines = ['/*', ...headers.map(({ key, value }) => `  ${key}: ${value}`)];
writeFileSync(join(OUT, '_headers'), `${lines.join('\n')}\n`);
console.log(`out/_headers : ${headers.length} en-têtes de sécurité`);

// 2. CSP de chaque page
/** @param {string} dir @returns {string[]} */
function htmlFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === '_next' ? [] : htmlFiles(path);
    return entry.name.endsWith('.html') ? [path] : [];
  });
}

// Un script inline : une balise <script> sans attribut src. Son empreinte porte sur son texte exact.
const INLINE_SCRIPT = /<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g;

let pages = 0;
for (const file of htmlFiles(OUT)) {
  const html = readFileSync(file, 'utf8');
  if (!html.includes('<head>')) {
    throw new Error(`${file} : pas de <head> où poser la CSP`);
  }
  const hashes = [...new Set([...html.matchAll(INLINE_SCRIPT)].map(([, body]) =>
    `sha256-${createHash('sha256').update(body, 'utf8').digest('base64')}`))];
  // Tout en tête de <head> : la CSP ne s'applique qu'aux éléments qui la suivent
  const meta = `<meta http-equiv="Content-Security-Policy" content="${pageScriptPolicy(hashes)}"/>`;
  writeFileSync(file, html.replace('<head>', `<head>${meta}`));
  pages += 1;
}
console.log(`CSP par page : ${pages} pages, scripts inline autorisés par empreinte`);
