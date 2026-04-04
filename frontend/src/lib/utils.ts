// DANS src/lib/utils.ts

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ON SIMPLIFIE ET SÉCURISE CETTE FONCTION
export function getApiBaseUrl() {
  // 1. Priorité à la variable d'environnement (si configurée explicitememt)
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  // 2. Détection intelligente selon l'environnement (Client side)
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    const isLocal = hostname === 'localhost' || hostname.startsWith('192.168.') || hostname === '127.0.0.1';
    
    if (!isLocal) {
      // On est en production (Vercel ou autre)
      return 'https://motsfleches-terminator-backend.onrender.com';
    }
  }

  // 3. Fallback par défaut (Développement local)
  return 'http://localhost:5001';
}
