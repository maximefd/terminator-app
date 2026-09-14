const isDev = process.env.NODE_ENV === 'development';

// Origines de l'API appelées par le navigateur (voir getApiBaseUrl dans src/lib/utils.ts)
const apiOrigins = [
  process.env.NEXT_PUBLIC_API_BASE_URL,
  'https://motsfleches-terminator-backend.onrender.com',
]
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

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // On garde cette option pour les tests locaux, mais elle peut causer des avertissements.
    // La configuration ci-dessous est une version plus robuste.
  },
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }];
  },
};

// LA CORRECTION DÉFINITIVE EST ICI :
// On applique la configuration expérimentale uniquement en mode développement.
if (isDev) {
  nextConfig.experimental = {
    ...nextConfig.experimental,
    allowedDevOrigins: [
      "http://localhost:3000",
      "http://192.168.1.56:3000",
      "http://192.0.0.2:3000", // On garde les adresses possibles
    ],
  };
}

export default nextConfig;
