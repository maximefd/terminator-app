import { type Metadata } from "next";
import { notFound } from "next/navigation";
import { GridEditor } from "@/components/grid/grid-editor";

export const metadata: Metadata = {
  title: "Définitions | Terminator",
  description: "Écrivez les définitions de votre grille, puis exportez-la en PDF.",
};

export default async function GridEditorPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const gridId = Number(id);
  if (!Number.isInteger(gridId) || gridId < 1) notFound();

  return <GridEditor gridId={gridId} />;
}
