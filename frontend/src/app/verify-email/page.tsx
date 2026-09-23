import { type Metadata } from "next";
import { Suspense } from "react";
import { VerifyEmail } from "@/components/auth/email-link-forms";

export const metadata: Metadata = {
  title: "Confirmation de l'adresse | Terminator",
  description: "Confirmer l'adresse e-mail de votre compte Terminator.",
};

export default function VerifyEmailPage() {
  return (
    <Suspense>
      <VerifyEmail />
    </Suspense>
  );
}
