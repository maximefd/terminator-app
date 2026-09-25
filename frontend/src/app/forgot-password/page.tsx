import { type Metadata } from "next";
import { ForgotPasswordForm } from "@/components/auth/email-link-forms";

export const metadata: Metadata = {
  title: "Mot de passe oublié",
  description: "Recevoir par e-mail un lien pour choisir un nouveau mot de passe.",
};

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
