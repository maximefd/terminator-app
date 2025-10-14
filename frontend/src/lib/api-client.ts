import { getApiBaseUrl } from "@/lib/utils";

type ApiFetchOptions = RequestInit & {
  // On peut ajouter des options spécifiques plus tard si besoin
};

export async function apiFetch(endpoint: string, options: ApiFetchOptions = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem("access_token") : null;
  const url = `${getApiBaseUrl()}${endpoint}`;

  const headers = new Headers(options.headers || {});
  
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    try {
      const errorData = await response.json();
      throw new Error(errorData.error || `Erreur ${response.status}`);
    } catch { // CORRECTION ICI : On retire la variable 'e' qui n'est pas utilisée
      throw new Error(`Erreur ${response.status}: ${response.statusText}`);
    }
  }

  if (response.status === 204) {
    return { success: true };
  }
  
  return response.json();
}
