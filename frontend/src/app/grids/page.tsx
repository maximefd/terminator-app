import { type Metadata } from "next";
import { SavedGridsClientLayout } from "@/components/grid/saved-grids-client-layout";

export const metadata: Metadata = {
  title: "Mes grilles | Terminator",
  description: "Les grilles de mots fléchés que vous avez conservées, telles qu'elles ont été produites.",
};

export default function SavedGridsPage() {
  return <SavedGridsClientLayout />;
}
