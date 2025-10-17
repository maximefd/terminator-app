// DANS src/lib/utils.ts

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ON SIMPLIFIE RADICALEMENT CETTE FONCTION
export function getApiBaseUrl() {
  // En développement, le frontend (Next.js) et le backend (Docker) tournent sur la même machine.
  // Le backend est TOUJOURS accessible via localhost:5001 grâce au port mapping de Docker.
  // C'est la seule URL dont nous avons besoin.
  return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5001';
}