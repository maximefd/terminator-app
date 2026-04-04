// DANS src/lib/utils.ts

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ON SIMPLIFIE ET SÉCURISE CETTE FONCTION
export function getApiBaseUrl() {
  // 1. Priorité à la variable d'environnement (si configurée sur Vercel/Local)
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  // 2. Fallback intelligent selon l'environnement
  // Si on est sur Vercel (production), on pointe vers Render.
  // Sinon (développement), on pointe vers le Docker local.
  return process.env.NODE_ENV === 'production'
    ? 'https://motsfleches-terminator-backend.onrender.com'
    : 'http://localhost:5001';
}