import { getApiBaseUrl } from "@/lib/utils";

// On utilise 'unknown' qui est plus sûr que 'any'
type ApiFetchOptions = Omit<RequestInit, 'body'> & {
  body?: Record<string, unknown>;
};

type Tokens = {
  access_token: string;
  refresh_token?: string;
};

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

/** Émis quand la session ne peut pas être renouvelée : le contexte d'authentification se déconnecte. */
export const SESSION_EXPIRED_EVENT = "terminator:session-expired";

function readToken(key: string): string | null {
  return typeof window !== "undefined" ? localStorage.getItem(key) : null;
}

export function storeTokens(tokens: Tokens) {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  if (tokens.refresh_token) {
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  }
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function hasStoredSession(): boolean {
  return readToken(ACCESS_TOKEN_KEY) !== null;
}

// Plusieurs requêtes peuvent expirer en même temps : un seul renouvellement partagé
let pendingRefresh: Promise<boolean> | null = null;

function refreshAccessToken(): Promise<boolean> {
  const refreshToken = readToken(REFRESH_TOKEN_KEY);
  if (!refreshToken) return Promise.resolve(false);

  if (!pendingRefresh) {
    pendingRefresh = fetch(`${getApiBaseUrl()}/api/auth/refresh`, {
      method: "POST",
      headers: { Authorization: `Bearer ${refreshToken}` },
    })
      .then(async (response) => {
        if (!response.ok) return false;
        const data = await response.json();
        storeTokens({ access_token: data.access_token });
        return true;
      })
      .catch(() => false)
      .finally(() => {
        pendingRefresh = null;
      });
  }
  return pendingRefresh;
}

async function readErrorMessage(response: Response): Promise<string> {
  // On lit le message d'erreur de l'API s'il existe (réponse JSON { error })
  let message = `Erreur ${response.status}: ${response.statusText}`;
  try {
    const errorData = await response.json();
    if (typeof errorData?.error === "string" && errorData.error) {
      message = errorData.error;
    }
  } catch {
    // Réponse non JSON : on garde le message générique
  }
  return message;
}

export async function apiFetch(endpoint: string, options: ApiFetchOptions = {}, allowRefresh = true) {
  const token = readToken(ACCESS_TOKEN_KEY);
  const url = `${getApiBaseUrl()}${endpoint}`;

  const headers = new Headers(options.headers || {});

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const body = options.body ? JSON.stringify(options.body) : undefined;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
      body,
    });
  } catch {
    // Erreur réseau (« Failed to fetch ») : API arrêtée, en cours de redémarrage ou injoignable
    throw new Error("Impossible de joindre le serveur de Terminator. Vérifiez qu'il est lancé (make dev-api), puis réessayez.");
  }

  // Jeton expiré ou refusé : une seule tentative de renouvellement, puis déconnexion.
  // Les routes d'authentification sont exclues (un 401 y signifie « identifiants invalides »).
  if (response.status === 401 && token && allowRefresh && !endpoint.startsWith("/api/auth/")) {
    if (await refreshAccessToken()) {
      return apiFetch(endpoint, options, false);
    }
    clearTokens();
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  if (response.status === 204) {
    return { success: true };
  }

  return response.json();
}
