import { type Metadata } from "next";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = {
  title: "Créer un compte | Terminator",
  description: "Créez un compte pour conserver vos dictionnaires thématiques et vos grilles.",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
