/**
 * Où revenir après la connexion ou l'inscription (`/login?next=/grid`).
 *
 * Seul un chemin **interne** est suivi : `//exemple.com` ou `https://…` feraient de la page de
 * connexion un tremplin vers un autre site. Sans paramètre valable, on retourne à l'accueil.
 *
 * On juge l'adresse telle que le navigateur la lira, pas son texte : l'analyseur d'URL retire
 * tabulations et retours à la ligne, et lit « \ » comme « / ». Ainsi `/⇥/exemple.com` devient
 * `//exemple.com`, qu'un simple test sur le texte laissait passer.
 */
export function nextPath(fallback = "/"): string {
  if (typeof window === "undefined") return fallback;
  const next = new URLSearchParams(window.location.search).get("next");
  if (!next || !next.startsWith("/")) return fallback;
  let target: URL;
  try {
    target = new URL(next, window.location.origin);
  } catch {
    return fallback;
  }
  if (target.origin !== window.location.origin) return fallback;
  return target.pathname + target.search + target.hash;
}

/** Le lien vers une page d'authentification qui ramène ici ensuite. */
export function withNext(page: "/login" | "/register", next: string) {
  return `${page}?next=${encodeURIComponent(next)}`;
}
