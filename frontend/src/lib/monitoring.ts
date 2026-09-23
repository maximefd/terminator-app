/**
 * Suivi des erreurs du navigateur avec Sentry (ADR 0013), inactif sans `NEXT_PUBLIC_SENTRY_DSN`.
 *
 * Seules les erreurs partent, et rien qui identifie l'utilisateur ou ouvre son compte : ni cookies, ni
 * adresse IP, ni le jeton des liens reçus par e-mail (`/reset-password?token=…`), que l'adresse de la page
 * porte et que Sentry joindrait sinon au rapport et à son fil d'événements.
 */
import type { Breadcrumb, ErrorEvent } from "@sentry/browser";

/** Adresse sans ses paramètres sensibles : `?token=abc` devient `?token=[retiré]`. */
export function withoutSecrets(url: string | undefined): string | undefined {
  if (!url) return url;
  return url.replace(/([?&](?:token|password)=)[^&#\s]*/gi, "$1[retiré]");
}

export function scrubEvent(event: ErrorEvent): ErrorEvent {
  if (event.request) {
    event.request.url = withoutSecrets(event.request.url);
    delete event.request.cookies;
    delete event.request.query_string;
    const userAgent = event.request.headers?.["User-Agent"];
    event.request.headers = userAgent ? { "User-Agent": userAgent } : {};
  }
  delete event.user;
  event.breadcrumbs = event.breadcrumbs?.map(scrubBreadcrumb);
  return event;
}

export function scrubBreadcrumb(breadcrumb: Breadcrumb): Breadcrumb {
  const data = breadcrumb.data;
  if (data) {
    for (const key of ["url", "from", "to"]) {
      if (typeof data[key] === "string") data[key] = withoutSecrets(data[key]);
    }
  }
  return breadcrumb;
}

export async function initMonitoring(dsn: string | undefined) {
  if (!dsn) return;
  // Chargé seulement s'il sert : sans DSN, le module ne quitte jamais le serveur
  const Sentry = await import("@sentry/browser");
  Sentry.init({
    dsn,
    environment: process.env.NODE_ENV === "production" ? "production" : "development",
    // Rien sur l'utilisateur, ni cookies, ni en-têtes, ni corps, ni paramètres d'adresse : scrubEvent le
    // vérifie encore avant l'envoi, au cas où une intégration en ajouterait
    dataCollection: { userInfo: false, cookies: false, httpHeaders: false, httpBodies: [], urlQueryParams: false },
    tracesSampleRate: 0,
    beforeSend: scrubEvent,
    beforeBreadcrumb: scrubBreadcrumb,
  });
}
