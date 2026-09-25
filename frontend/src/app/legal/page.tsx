// DANS src/app/legal/page.tsx

import { type Metadata } from "next";
import Link from "next/link";
import { type ReactNode } from "react";
import { site } from "@/config/site";
import { publicPage } from "@/lib/seo";

export const metadata: Metadata = publicPage({
  path: "/legal",
  title: "Mentions légales",
  description:
    `Qui fait ${site.name}, où il tourne, et les ressources qu'il emprunte.`,
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

export default function LegalPage() {
  return (
    <main className="container mx-auto max-w-3xl p-4 md:p-8">
      <h1 className="text-3xl font-bold">Mentions légales</h1>
      <p className="mt-2 text-sm text-muted-foreground">Dernière mise à jour : 23 septembre 2026</p>

      <div className="mt-8 space-y-8 text-muted-foreground">
        <Section title="Éditeur">
          <p>
            {site.name} est un outil personnel de création de mots fléchés, développé par un particulier, à titre non
            commercial. Pour le contacter : le{" "}
            <a href="https://github.com/maximefd/terminator-app/issues" className={linkClass}>
              dépôt du projet
            </a>
            .
          </p>
        </Section>

        <Section title="Hébergement">
          <p>
            Aucun à ce jour : {site.name} n&apos;est pas publié en ligne, il tourne sur l&apos;ordinateur de son auteur.
            Le jour d&apos;une mise en ligne, cette page indiquera l&apos;hébergeur et l&apos;identité complète de
            l&apos;éditeur, comme la loi le demande.
          </p>
        </Section>

        <Section title="Données personnelles">
          <p>
            Ce que {site.name} conserve, pourquoi, et comment le supprimer :{" "}
            <Link href="/privacy" className={linkClass}>page de confidentialité</Link>.
          </p>
        </Section>

        <Section title="Crédits">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong className="text-foreground">Liste des mots</strong> : dérivée du DELA, dictionnaire des formes
              fléchies du français (LADL, diffusé avec{" "}
              <a href="https://unitexgramlab.org/fr/language-resources" className={linkClass}>Unitex/GramLab</a>),
              sous licence LGPLLR.
            </li>
            <li>
              <strong className="text-foreground">Fréquence des mots</strong> :{" "}
              <a href="http://www.lexique.org" className={linkClass}>Lexique 3.83</a> (Boris New, Christophe Pallier et
              coll.), sous licence CC BY-SA 4.0.
            </li>
            <li>
              <strong className="text-foreground">Police des grilles</strong> : Archivo Narrow (Omnibus-Type), sous
              licence SIL Open Font License 1.1.
            </li>
          </ul>
          <p>
            Le détail des licences et de ce qu&apos;elles demandent :{" "}
            <a
              href="https://github.com/maximefd/terminator-app/blob/main/docs/LICENCES.md"
              className={linkClass}
            >
              LICENCES.md
            </a>
            .
          </p>
        </Section>
      </div>
    </main>
  );
}
