// DANS src/lib/utils.ts

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Adresse de l'API : `NEXT_PUBLIC_API_BASE_URL`, obligatoire pour un build de production (next.config.ts).
 * Sans elle, en développement, l'API locale. Aucun repli vers un serveur distant : l'ancien, sur Render, a
 * été supprimé, et son sous-domaine peut être réservé par n'importe qui — un build qui s'y rabattrait lui
 * enverrait e-mails et mots de passe.
 */
export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5001';
}
