import { type Metadata } from "next";
import { SavedGridsClientLayout } from "@/components/grid/saved-grids-client-layout";
import { privatePage } from "@/lib/seo";

export const metadata: Metadata = privatePage({
  title: "Mes grilles",
  description: "Les grilles de mots fléchés que vous avez conservées, telles qu'elles ont été produites.",
});

export default function SavedGridsPage() {
  return <SavedGridsClientLayout />;
}
