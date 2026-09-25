import { type Metadata } from "next";
import { Landing } from "@/components/home/landing";
import { site } from "@/config/site";
import { publicPage } from "@/lib/seo";

export const metadata: Metadata = publicPage({
  path: "/",
  description:
    "Outil de création de mots fléchés français : recherche par motif (P??LE) et remplissage automatique d'une grille autour de vos mots obligatoires et souhaités.",
});

// Données structurées : ce qu'est le site, pour les moteurs de recherche et de réponse IA (#113)
const structuredData = {
  "@context": "https://schema.org",
  "@type": "WebApplication",
  name: site.name,
  url: site.url,
  description: site.description,
  inLanguage: site.lang,
  applicationCategory: "DesignApplication",
  operatingSystem: "Navigateur web",
  offers: { "@type": "Offer", price: "0", priceCurrency: "EUR" },
};

export default function HomePage() {
  return (
    <>
      <script
        type="application/ld+json"
        // Échapper « < » : une chaîne de la configuration ne peut pas fermer la balise
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData).replace(/</g, "\\u003c") }}
      />
      <Landing />
    </>
  );
}
