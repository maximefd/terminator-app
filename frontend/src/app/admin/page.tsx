import { type Metadata } from "next";
import { AdminDashboard } from "@/components/admin/admin-dashboard";

// Liée nulle part, absente du sitemap et de robots.txt ; `noindex` aussi par X-Robots-Tag (scripts/write-headers.mjs).
// Le titre est celui de la page 404, que voit tout autre visiteur : le vrai n'apparaît qu'à l'administrateur.
export const metadata: Metadata = { title: "Page introuvable", robots: { index: false, follow: false } };

export default function AdminPage() {
  return <AdminDashboard />;
}
