import { type Metadata } from "next";
import { ForgotPasswordForm } from "@/components/auth/email-link-forms";
import { privatePage } from "@/lib/seo";

export const metadata: Metadata = privatePage({
  title: "Mot de passe oublié",
  description: "Recevoir par e-mail un lien pour choisir un nouveau mot de passe.",
});

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
