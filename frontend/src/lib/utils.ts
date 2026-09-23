// DANS src/lib/utils.ts

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Adresse de l'API : `NEXT_PUBLIC_API_BASE_URL`, obligatoire pour un build de production (next.config.ts).
 *
 * Sans elle, en développement, la **même origine** : `next dev` relaie `/api/*` vers l'API locale
 * (next.config.ts). La session vit dans des cookies (ADR 0015) ; même origine, ils suivent partout — depuis
 * le téléphone sur le Wi-Fi comme à travers le tunnel de `make preview-remote`.
 *
 * Aucun repli vers un serveur distant : l'ancien, sur Render, a été supprimé, et son sous-domaine peut être
 * réservé par n'importe qui — un build qui s'y rabattrait lui enverrait e-mails et mots de passe.
 */
export function getApiBaseUrl() {
  return process.env.NEXT_PUBLIC_API_BASE_URL || '';
}
