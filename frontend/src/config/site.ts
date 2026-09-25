/**
 * Le site servi par ce build : son nom public, son adresse, sa langue et ses contacts (ADR 0017).
 *
 * Terminator est le nom du moteur ; les visiteurs ne voient que le nom du site. Un export statique par site :
 * `NEXT_PUBLIC_SITE` choisit l'entrée au build (défaut : le site français) ; une entrée inconnue fait échouer
 * le build. `NEXT_PUBLIC_SITE_URL` remplace l'adresse, pour une préversion ou le développement.
 */
export type SiteConfig = {
  /** Nom public, dans les titres, l'en-tête, le pied de page et les pages légales */
  name: string;
  /** Accroche du titre de l'accueil et des partages */
  tagline: string;
  description: string;
  /** Hôte canonique, sans barre finale */
  url: string;
  lang: string;
  contactEmail: string;
  securityEmail: string;
};

export const SITES = {
  fr: {
    name: "Le Fléchoir",
    tagline: "l'atelier des mots fléchés",
    description:
      "Créez vos mots fléchés : trouvez le mot qui manque par motif (P??LE), ou laissez le moteur remplir une grille entière, puis écrivez les définitions et exportez en PDF.",
    url: "https://leflechoir.fr",
    lang: "fr",
    contactEmail: "contact@leflechoir.fr",
    securityEmail: "securite@leflechoir.fr",
  },
} satisfies Record<string, SiteConfig>;

export type SiteKey = keyof typeof SITES;

export function isSiteKey(key: string): key is SiteKey {
  return Object.prototype.hasOwnProperty.call(SITES, key);
}

function resolveSite(): SiteConfig {
  const key = process.env.NEXT_PUBLIC_SITE || "fr";
  if (!isSiteKey(key)) {
    throw new Error(`NEXT_PUBLIC_SITE inconnu : « ${key} ». Sites connus : ${Object.keys(SITES).join(", ")}.`);
  }
  const url = (process.env.NEXT_PUBLIC_SITE_URL || SITES[key].url).replace(/\/+$/, "");
  return { ...SITES[key], url };
}

export const site: SiteConfig = resolveSite();
