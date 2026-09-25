import type { MetadataRoute } from "next";
import { site } from "@/config/site";
import { PUBLIC_PATHS } from "@/lib/seo";

export const dynamic = "force-static";

/** Les pages publiques seulement (lib/seo.ts) ; les privées sont en `noindex`. */
export default function sitemap(): MetadataRoute.Sitemap {
  return PUBLIC_PATHS.map((path) => ({
    // Comme la canonique de l'accueil : l'adresse du site, sans barre finale
    url: path === "/" ? site.url : `${site.url}${path}`,
    changeFrequency: "monthly",
    priority: path === "/" ? 1 : path === "/search" || path === "/grid" ? 0.8 : path === "/contact" ? 0.5 : 0.3,
  }));
}
