import { type Metadata } from "next";
import { DictionariesClientLayout } from "@/components/dictionary/dictionaries-client-layout";
import { privatePage } from "@/lib/seo";

export const metadata: Metadata = privatePage({
  title: "Vos dictionnaires",
  description: "Rassemblez vos mots par thème, avec leurs définitions : ils passent en tête de la recherche par motif et alimentent les grilles que vous générez.",
});

export default function DictionariesPage() {
  return <DictionariesClientLayout />;
}
