import type { NextConfig } from 'next';
import { PHASE_PRODUCTION_BUILD } from 'next/constants';

const isDev = process.env.NODE_ENV === 'development';

// Origine de l'API appelée par le navigateur (voir getApiBaseUrl dans src/lib/utils.ts)
const apiOrigins = [process.env.NEXT_PUBLIC_API_BASE_URL]
  .filter((url): url is string => Boolean(url))
  .map((url) => new URL(url).origin);

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

const securityHeaders = [
  { key: 'Content-Security-Policy', value: contentSecurityPolicy },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
  ...(isDev ? [] : [{ key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' }]),
];

const nextConfig: NextConfig = {
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },
};

// allowedDevOrigins doit être au niveau racine (pas sous experimental) depuis Next 15.5,
// et ses entrées sont juste des hostnames (sans schéma, port seulement si non standard) :
// https://nextjs.org/docs/app/api-reference/config/next-config-js/allowedDevOrigins
if (isDev) {
  nextConfig.allowedDevOrigins = [
    "localhost:3000",
    "192.168.1.147:3000", // téléphone sur le même Wi-Fi que le Mac
    "*.trycloudflare.com", // tunnel temporaire (make preview-remote)
  ];
}

export default function config(phase: string): NextConfig {
  // Un build de production sans adresse d'API n'a nulle part où envoyer ses requêtes : il échoue ici
  // plutôt que de se rabattre sur une adresse codée en dur (voir getApiBaseUrl).
  if (phase === PHASE_PRODUCTION_BUILD && !process.env.NEXT_PUBLIC_API_BASE_URL) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL est obligatoire pour un build de production : c'est l'adresse de l'API.");
  }
  return nextConfig;
}
