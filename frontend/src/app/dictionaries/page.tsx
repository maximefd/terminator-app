import { type Metadata } from "next";
import { DictionariesClientLayout } from "@/components/dictionary/dictionaries-client-layout";

export const metadata: Metadata = {
  title: "Vos dictionnaires",
  description:
    "Rassemblez vos mots par thème, avec leurs définitions : ils passent en tête de la recherche par motif et alimentent les grilles que vous générez.",
};

export default function DictionariesPage() {
  return <DictionariesClientLayout />;
}
