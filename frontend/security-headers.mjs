// @ts-check
/**
 * En-têtes de sécurité du frontend, en un seul endroit.
 *
 * - En développement, `next dev` les envoie (next.config.ts, `headers()`).
 * - En production, le site est un export statique servi par Cloudflare Pages (ADR 0013) : aucun serveur Next
 *   pour les envoyer. `scripts/write-headers.mjs` les écrit dans `out/_headers`, que Pages applique.
 */

/**
 * @param {{ isDev: boolean, apiBaseUrl: string | undefined }} options
 * @returns {{ key: string, value: string }[]}
 */
export function securityHeaders({ isDev, apiBaseUrl }) {
  // Origine de l'API appelée par le navigateur (voir getApiBaseUrl dans src/lib/utils.ts)
  const apiOrigins = apiBaseUrl ? [new URL(apiBaseUrl).origin] : [];

  const contentSecurityPolicy = [
    "default-src 'self'",
    // Next.js injecte des scripts inline ; 'unsafe-eval' uniquement en dev (rechargement à chaud)
    `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ''}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    // En dev : API locale (localhost ou réseau local) et websocket du rechargement à chaud
    `connect-src 'self' ${apiOrigins.join(' ')}${isDev ? ' http: ws:' : ''}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join('; ');

  return [
    { key: 'Content-Security-Policy', value: contentSecurityPolicy },
    { key: 'X-Content-Type-Options', value: 'nosniff' },
    { key: 'X-Frame-Options', value: 'DENY' },
    { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
    { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
    ...(isDev ? [] : [{ key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' }]),
  ];
}

/**
 * CSP propre à une page du site statique, pour ses scripts : seuls ceux dont l'empreinte est listée
 * s'exécutent (#99). Posée en <meta> dans la page par scripts/write-headers.mjs : chaque page a ses propres
 * scripts inline (les données de rendu de Next), et leur réunion dépasserait la taille d'un en-tête.
 *
 * Elle s'ajoute à la CSP de l'en-tête, qui garde 'unsafe-inline' : le navigateur applique les deux, un script
 * doit donc satisfaire les deux, et c'est celle-ci qui tranche. `frame-ancestors` et les autres directives
 * restent dans l'en-tête, qu'une <meta> ne peut pas porter.
 *
 * @param {string[]} hashes empreintes au format 'sha256-…'
 */
export function pageScriptPolicy(hashes) {
  return ["script-src 'self'", ...hashes.map((hash) => `'${hash}'`)].join(' ');
}
