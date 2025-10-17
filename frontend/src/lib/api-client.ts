import { getApiBaseUrl } from "@/lib/utils";

// On définit un type plus robuste pour nos options
type ApiFetchOptions = Omit<RequestInit, 'body'> & {
  // Le 'body' peut être n'importe quel objet JavaScript simple
  body?: Record<string, any>;
};

export async function apiFetch(endpoint: string, options: ApiFetchOptions = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem("access_token") : null;
  // LA CORRECTION EST ICI : getApiBase-url() -> getApiBaseUrl()
  const url = `${getApiBaseUrl()}${endpoint}`;

  // On utilise le constructeur `Headers` qui est plus sûr
  const headers = new Headers(options.headers || {});
  
  // On ajoute le Content-Type uniquement s'il y a un corps de requête
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // On ne stringify le corps que s'il existe, et on le garde séparé du reste des options
  const body = options.body ? JSON.stringify(options.body) : undefined;

  const response = await fetch(url, {
    ...options,
    headers,
    body, // On passe le corps stringifié
  });

  if (!response.ok) {
    try {
      const errorData = await response.json();
      throw new Error(errorData.error || `Erreur ${response.status}`);
    } catch {
      throw new Error(`Erreur ${response.status}: ${response.statusText}`);
    }
  }

  // On gère le cas des réponses sans contenu (ex: 204 No Content)
  if (response.status === 204) {
    return { success: true };
  }
  
  return response.json();
}

