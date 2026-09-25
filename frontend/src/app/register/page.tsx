import { type Metadata } from "next";
import { RegisterForm } from "@/components/auth/register-form";
import { privatePage } from "@/lib/seo";

export const metadata: Metadata = privatePage({
  title: "Créer un compte",
  description: "Créez un compte pour conserver vos dictionnaires thématiques et vos grilles.",
});

export default function RegisterPage() {
  return <RegisterForm />;
}
