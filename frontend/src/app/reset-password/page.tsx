import { type Metadata } from "next";
import { Suspense } from "react";
import { ResetPasswordForm } from "@/components/auth/email-link-forms";
import { privatePage } from "@/lib/seo";

export const metadata: Metadata = privatePage({
  title: "Nouveau mot de passe",
  description: "Choisir un nouveau mot de passe à partir du lien reçu par e-mail.",
});

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
