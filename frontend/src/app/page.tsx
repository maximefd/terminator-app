import { type Metadata } from "next";
import { Landing } from "@/components/home/landing";

export const metadata: Metadata = {
  title: "Terminator — composez vos mots fléchés",
  description:
    "Outil de création de mots fléchés français : recherche par motif (P??LE) et remplissage automatique d'une grille autour de vos mots obligatoires et souhaités.",
};

export default function HomePage() {
  return <Landing />;
}
