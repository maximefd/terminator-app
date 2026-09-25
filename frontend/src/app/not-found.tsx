import type { Metadata } from "next";
import { NotFoundContent } from "@/components/layout/not-found-content";

// Next ajoute lui-même `noindex` à cette page
export const metadata: Metadata = { title: "Page introuvable" };

export default function NotFound() {
  return <NotFoundContent />;
}
