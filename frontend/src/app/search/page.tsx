import { type Metadata } from "next";
import { SearchClientLayout } from "@/components/search/search-client-layout";

export const metadata: Metadata = {
  title: "Recherche de mots | Terminator",
  description:
    "Trouvez instantanément des mots pour vos grilles de mots fléchés. Recherchez par motif (ex : P??LE) et utilisez vos dictionnaires personnels.",
};

export default function SearchPage() {
  return <SearchClientLayout />;
}
