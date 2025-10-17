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
    try {
      const errorData = await response.json();
      throw new Error(errorData.error || `Erreur ${response.status}`);
    } catch {
      throw new Error(`Erreur ${response.status}: ${response.statusText}`);
    }
  }

  if (response.status === 204) {
    return { success: true };
  }
  
  return response.json();
}