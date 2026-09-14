import { getApiBaseUrl } from "@/lib/utils";

// On utilise 'unknown' qui est plus sûr que 'any'
type ApiFetchOptions = Omit<RequestInit, 'body'> & {
  body?: Record<string, unknown>; 
};

export async function apiFetch(endpoint: string, options: ApiFetchOptions = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem("access_token") : null;
  const url = `${getApiBaseUrl()}${endpoint}`;

  const headers = new Headers(options.headers || {});
  
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const body = options.body ? JSON.stringify(options.body) : undefined;

  const response = await fetch(url, {
    ...options,
    headers,
    body,
  });

  if (!response.ok) {
    // On lit le message d'erreur de l'API s'il existe ; le throw reste hors du try
    // pour ne pas être avalé par le catch (qui ne gère que les réponses non JSON).
    let message = `Erreur ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (typeof errorData?.error === "string" && errorData.error) {
        message = errorData.error;
      }
    } catch {
      // Réponse non JSON : on garde le message générique
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return { success: true };
  }
  
  return response.json();
}