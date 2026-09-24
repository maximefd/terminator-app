/**
 * Où revenir après la connexion ou l'inscription (`/login?next=/grid`).
 *
 * Seul un chemin **interne** est suivi : `//exemple.com` ou `https://…` feraient de la page de
 * connexion un tremplin vers un autre site. Sans paramètre valable, on retourne à l'accueil.
 */
export function nextPath(fallback = "/"): string {
  if (typeof window === "undefined") return fallback;
  const next = new URLSearchParams(window.location.search).get("next");
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return fallback;
  return next;
}

/** Le lien vers une page d'authentification qui ramène ici ensuite. */
export function withNext(page: "/login" | "/register", next: string) {
  return `${page}?next=${encodeURIComponent(next)}`;
}
