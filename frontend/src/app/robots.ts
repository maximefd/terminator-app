import type { MetadataRoute } from "next";
import { site } from "@/config/site";

// Écrit au build : l'export statique n'a pas de serveur pour le produire à la demande
export const dynamic = "force-static";

/** Tout est ouvert, y compris aux moteurs de réponse IA (#111, #113). Les pages privées ne sont pas
 *  interdites ici : elles portent `noindex`, qu'un robot doit pouvoir lire. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${site.url}/sitemap.xml`,
  };
}
