// DANS src/lib/api-client.ts

export async function apiFetch(url: string, options: RequestInit = {}) {
  const token = localStorage.getItem("access_token");

  // On prépare les en-têtes par défaut
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  } as HeadersInit;

  // Si un token existe, on l'ajoute à l'en-tête Authorization
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // On construit la requête finale
  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Si la réponse n'est pas OK, on essaie de lire l'erreur JSON et on la lance
  if (!response.ok) {
    try {
      const errorData = await response.json();
      throw new Error(errorData.error || `Erreur ${response.status}`);
    } catch (e) {
      throw new Error(`Erreur ${response.status}: ${response.statusText}`);
    }
  }

  // Si la réponse n'a pas de contenu (ex: DELETE), on renvoie un succès simple
  if (response.status === 204) {
    return { success: true };
  }
  
  return response.json();
}