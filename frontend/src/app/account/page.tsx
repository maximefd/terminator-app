import { type Metadata } from "next";
import { AccountClientLayout } from "@/components/account/account-client-layout";
import { privatePage } from "@/lib/seo";

export const metadata: Metadata = privatePage({
  title: "Mon compte",
  description: "Votre adresse e-mail, ce que votre compte contient, et sa suppression.",
});

export default function AccountPage() {
  return <AccountClientLayout />;
}
