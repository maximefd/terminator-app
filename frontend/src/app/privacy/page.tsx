// DANS src/app/privacy/page.tsx

import { type Metadata } from "next";
import Link from "next/link";
import { type ReactNode } from "react";
import { site } from "@/config/site";

export const metadata: Metadata = {
  title: "Confidentialité",
  description: `Ce que ${site.name} conserve sur vous — une adresse e-mail, un mot de passe haché, vos dictionnaires et vos grilles — et rien d'autre.`,
};

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xl font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  );
}

const linkClass = "underline underline-offset-2 hover:text-foreground";

export default function PrivacyPage() {
  return (
    <main className="container mx-auto max-w-3xl p-4 md:p-8">
      <h1 className="text-3xl font-bold">Confidentialité</h1>
      <p className="mt-2 text-sm text-muted-foreground">Dernière mise à jour : 23 septembre 2026</p>

      <div className="mt-8 space-y-8 text-muted-foreground">
        <p className="rounded-lg border bg-secondary/20 p-4 text-foreground">
          {site.name} conserve votre adresse e-mail, votre mot de passe haché, vos dictionnaires et vos grilles.
          Rien d&apos;autre : pas de mesure d&apos;audience, pas de publicité, aucun cookie en dehors de ceux de
          votre session, et aucune donnée transmise à qui que ce soit.
        </p>

        <Section title={`Où tourne ${site.name}`}>
          <p>
            {site.name} est un outil personnel, en développement. Il n&apos;est pas publié en ligne : l&apos;application
            et sa base de données tournent sur l&apos;ordinateur de son auteur. Lors d&apos;un essai à distance,
            l&apos;auteur ouvre un tunnel temporaire : les échanges transitent alors par Cloudflare, qui relaie la
            connexion jusqu&apos;à son ordinateur.
          </p>
        </Section>

        <Section title="Ce qui est conservé, si vous créez un compte">
          <ul className="list-disc space-y-1 pl-5">
            <li><strong className="text-foreground">Votre adresse e-mail</strong>, qui sert d&apos;identifiant.</li>
            <li>
              <strong className="text-foreground">Votre mot de passe, haché</strong> (bcrypt) : il n&apos;est jamais
              enregistré tel quel, et personne ne peut le relire.
            </li>
            <li><strong className="text-foreground">Vos dictionnaires</strong>, leurs mots et leurs définitions.</li>
            <li>
              <strong className="text-foreground">Vos grilles conservées</strong> : leurs cases, leurs définitions et
              vos notes.
            </li>
          </ul>
          <p>
            Vos recherches et les grilles que vous générez sans les conserver ne sont pas enregistrées. En invité,
            rien ne l&apos;est.
          </p>
        </Section>

        <Section title="Ce qui passe sans être conservé">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong className="text-foreground">Votre session</strong> : des cookies strictement nécessaires à la
              connexion, illisibles par les scripts de la page, valables 7 jours au plus. La déconnexion les efface
              et les rend inutilisables. Ils ne servent à rien d&apos;autre : aucun consentement n&apos;est donc
              demandé.
            </li>
            <li>
              <strong className="text-foreground">Votre adresse IP</strong> : gardée en mémoire pour limiter le
              nombre de requêtes et protéger le service des abus, puis oubliée, au plus tard après une heure. Le
              journal technique de l&apos;application peut aussi la contenir, avec la page demandée : il reste sur
              l&apos;ordinateur de l&apos;auteur.
            </li>
          </ul>
        </Section>

        <Section title="Durée et suppression">
          <p>
            Vos données sont gardées tant que votre compte existe. Vous pouvez le supprimer à tout moment depuis{" "}
            <Link href="/account" className={linkClass}>Mon compte</Link> : l&apos;adresse e-mail, le mot de passe,
            les dictionnaires, les mots et les grilles sont effacés immédiatement et définitivement. Si
            l&apos;auteur a fait une sauvegarde de la base avant votre suppression, vos données y subsistent jusqu&apos;à
            son effacement, au plus 30 jours.
          </p>
        </Section>

        <Section title="Vos droits">
          <p>
            Vous pouvez consulter vos données dans l&apos;application (Mon compte, Dictionnaires, Mes grilles), les
            corriger, les effacer, et demander à les recevoir dans un format lisible. Pour toute demande, écrivez à
            l&apos;auteur par le{" "}
            <a href="https://github.com/maximefd/terminator-app/issues" className={linkClass}>
              dépôt du projet
            </a>
            . Vous pouvez aussi saisir la{" "}
            <a href="https://www.cnil.fr/fr/plaintes" className={linkClass}>CNIL</a>.
          </p>
        </Section>

        <Section title="Le jour d'une mise en ligne">
          <p>
            {site.name} sera un jour hébergé sur un serveur en France, derrière Cloudflare. Plusieurs choses changeront
            alors : un hébergeur et Cloudflare traiteront les connexions, un prestataire enverra les e-mails de
            réinitialisation du mot de passe, un service de suivi des erreurs (Sentry) recevra les rapports de panne,
            sans rien qui vous identifie, des sauvegardes chiffrées seront gardées 30 jours, et le serveur tiendra
            un journal des requêtes. Cette page sera réécrite avant, et dira qui fait quoi.
          </p>
        </Section>
      </div>
    </main>
  );
}
