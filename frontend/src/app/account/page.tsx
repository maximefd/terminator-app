import { type Metadata } from "next";
import { AccountClientLayout } from "@/components/account/account-client-layout";

export const metadata: Metadata = {
  title: "Mon compte | Terminator",
  description: "Votre adresse e-mail, ce que votre compte contient, et sa suppression.",
};

export default function AccountPage() {
  return <AccountClientLayout />;
}
