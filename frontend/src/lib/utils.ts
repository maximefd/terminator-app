import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getApiBaseUrl() {
  // Si le code s'exécute côté serveur (pendant le build ou SSR),
  // on utilise localhost car le frontend et le backend sont "voisins" dans Docker.
  if (typeof window === 'undefined') {
    return 'http://localhost:5001';
  }
  
  // Si le code s'exécute dans le navigateur, on utilise le même nom d'hôte
  // que celui de la page actuelle, mais avec le port de l'API.
  return `${window.location.protocol}//${window.location.hostname}:5001`;
}