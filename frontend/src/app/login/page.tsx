import { type Metadata } from "next";
import { LoginForm } from "@/components/auth/login-form";

// Un composant client ne peut pas exporter de métadonnées : sans cette page serveur, l'onglet
// n'avait pas de titre — axe le signale comme une violation WCAG (#25).
export const metadata: Metadata = {
  title: "Connexion | Terminator",
  description: "Connectez-vous pour retrouver vos dictionnaires personnels et vos grilles conservées.",
};

export default function LoginPage() {
  return <LoginForm />;
}
