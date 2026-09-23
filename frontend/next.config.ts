import type { NextConfig } from 'next';
import { PHASE_PRODUCTION_BUILD } from 'next/constants';

import { securityHeaders } from './security-headers.mjs';

const isDev = process.env.NODE_ENV === 'development';

const nextConfig: NextConfig = {};

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
  if (phase === PHASE_PRODUCTION_BUILD) {
    // Un build de production sans adresse d'API n'a nulle part où envoyer ses requêtes : il échoue ici
    // plutôt que de se rabattre sur une adresse codée en dur (voir getApiBaseUrl).
    if (!process.env.NEXT_PUBLIC_API_BASE_URL) {
      throw new Error("NEXT_PUBLIC_API_BASE_URL est obligatoire pour un build de production : c'est l'adresse de l'API.");
    }
    // Site statique (out/), servi par Cloudflare Pages (ADR 0013) : pas de serveur Node en production.
    // Ses en-têtes de sécurité partent dans out/_headers (scripts/write-headers.mjs).
    return { ...nextConfig, output: 'export' };
  }
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  // Sans adresse d'API, le frontend appelle sa propre origine (getApiBaseUrl) : next dev relaie vers l'API
  const apiProxyTarget = process.env.API_PROXY_TARGET || 'http://localhost:5001';
  return {
    ...nextConfig,
    async headers() {
      const sentryDsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
      return [{ source: '/:path*', headers: securityHeaders({ isDev, apiBaseUrl, sentryDsn }) }];
    },
    async rewrites() {
      return apiBaseUrl ? [] : [{ source: '/api/:path*', destination: `${apiProxyTarget}/api/:path*` }];
    },
  };
}
