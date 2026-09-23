// @ts-check
/**
 * Écrit `out/_headers` après `next build` : les en-têtes de sécurité du site statique, au format de
 * Cloudflare Pages (https://developers.cloudflare.com/pages/configuration/headers/). Sans ce fichier, l'export
 * partirait sans CSP ni HSTS : c'est `next dev` seul qui les envoyait.
 */
import { existsSync, writeFileSync } from 'node:fs';
import { securityHeaders } from '../security-headers.mjs';

const OUT = new URL('../out/', import.meta.url);
if (!existsSync(OUT)) {
  throw new Error("out/ introuvable : lancer d'abord next build (export statique).");
}

const headers = securityHeaders({ isDev: false, apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL });
const lines = ['/*', ...headers.map(({ key, value }) => `  ${key}: ${value}`)];
writeFileSync(new URL('_headers', OUT), `${lines.join('\n')}\n`);
console.log(`out/_headers : ${headers.length} en-têtes de sécurité`);
