import { type Metadata } from "next";
import { Suspense } from "react";
import { VerifyEmail } from "@/components/auth/email-link-forms";
import { site } from "@/config/site";

export const metadata: Metadata = {
  title: "Confirmation de l'adresse",
  description: `Confirmer l'adresse e-mail de votre compte ${site.name}.`,
};

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmail />
    </Suspense>
  );
}
