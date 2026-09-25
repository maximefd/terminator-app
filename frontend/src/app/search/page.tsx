import { type Metadata } from "next";
import { SearchClientLayout } from "@/components/search/search-client-layout";
import { publicPage } from "@/lib/seo";

export const metadata: Metadata = publicPage({
  path: "/search",
  title: "Recherche de mots",
  description:
    "Trouvez instantanément des mots pour vos grilles de mots fléchés. Recherchez par motif (ex : P??LE) et utilisez vos dictionnaires personnels.",
});

export default function SearchPage() {
  return <SearchClientLayout />;
}
