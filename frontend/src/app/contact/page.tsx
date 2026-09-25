import { type Metadata } from "next";
import Link from "next/link";
import { type ReactNode } from "react";
import { site } from "@/config/site";
import { publicPage } from "@/lib/seo";

export const metadata: Metadata = publicPage({
  path: "/contact",
  title: "Contact",
  description: `Écrire à ${site.name} : une suggestion, un problème, une question sur vos données, ou une faille de sécurité.`,
});

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xl font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  );
}

const linkClass = "underline underline-offset-2 hover:text-foreground";

export default function ContactPage() {
  return (
    <main className="container mx-auto max-w-3xl p-4 md:p-8">
      <h1 className="text-3xl font-bold">Contact</h1>

      <div className="mt-8 space-y-8 text-muted-foreground">
        <p className="rounded-lg border bg-secondary/20 p-4 text-foreground">
          Écrivez à{" "}
          <a href={`mailto:${site.contactEmail}`} className="font-semibold underline underline-offset-2">
            {site.contactEmail}
          </a>
          . Chaque message est lu par l&apos;auteur du site, qui répond en général sous quelques jours.
        </p>

        <Section title="Ce que vous pouvez y envoyer">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong className="text-foreground">Une suggestion</strong> : un format de grille qui manque, un mot
              absent du dictionnaire, ou un mot qui n&apos;a rien à faire dans une grille.
            </li>
            <li>
              <strong className="text-foreground">Un problème</strong> : ce que vous faisiez, ce que vous attendiez
              et ce qui s&apos;est passé. Si un message d&apos;erreur s&apos;est affiché, recopiez-le.
            </li>
            <li>
              <strong className="text-foreground">Une demande sur vos données</strong> : les consulter, les corriger,
              les recevoir ou les effacer (voir la{" "}
              <Link href="/privacy" className={linkClass}>page de confidentialité</Link>). Écrivez depuis
              l&apos;adresse de votre compte : c&apos;est ainsi que l&apos;auteur sait que la demande vient de vous.
            </li>
          </ul>
        </Section>

        <Section title="Une faille de sécurité">
          <p>
            Écrivez plutôt à{" "}
            <a href={`mailto:${site.securityEmail}`} className={linkClass}>{site.securityEmail}</a>, en décrivant
            l&apos;impact et les étapes pour la reproduire. Merci de ne pas la rendre publique avant sa correction.
          </p>
        </Section>
      </div>
    </main>
  );
}
