import type { Metadata } from "next";
import { site } from "@/config/site";

/**
 * Référencement (#113). Deux sortes de pages :
 * - publiques : indexées, dans le sitemap, avec une adresse canonique et un aperçu de partage ;
 * - privées (compte, grilles, dictionnaires, liens reçus par e-mail) : `noindex`. Jamais de `Disallow` sur
 *   elles dans robots.txt : un robot qui ne peut pas lire la page ne voit pas son `noindex`.
 */

/** Pages publiques, dans l'ordre du sitemap */
export const PUBLIC_PATHS = ["/", "/search", "/grid", "/legal", "/privacy"] as const;
export type PublicPath = (typeof PUBLIC_PATHS)[number];

/** Image de partage, écrite au build par app/og.png/route.tsx */
export const OG_IMAGE = { url: "/og.png", width: 1200, height: 630, alt: `${site.name} — ${site.tagline}` };

/** Aperçu de partage commun. Une page qui donne son propre `openGraph` remplace tout l'objet : elle repart d'ici. */
export const baseOpenGraph = {
  type: "website",
  siteName: site.name,
  locale: site.locale,
  images: [OG_IMAGE],
} satisfies Metadata["openGraph"];

export function publicPage({ path, title, description }: {
  path: PublicPath;
  /** Absent : le titre par défaut du site (accueil) */
  title?: string;
  description: string;
}): Metadata {
  const shareTitle = title ? `${title} | ${site.name}` : `${site.name} — ${site.tagline}`;
  return {
    ...(title ? { title } : {}),
    description,
    alternates: { canonical: path },
    openGraph: { ...baseOpenGraph, url: path, title: shareTitle, description },
    twitter: { card: "summary_large_image", title: shareTitle, description, images: [OG_IMAGE.url] },
  };
}

export function privatePage({ title, description }: { title: string; description: string }): Metadata {
  return { title, description, robots: { index: false, follow: false } };
}
