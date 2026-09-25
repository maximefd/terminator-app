import { type Metadata } from "next";
import Link from "next/link";
import { linkClass, Section } from "@/components/legal/section";
import { site } from "@/config/site";
import { publicPage } from "@/lib/seo";

export const metadata: Metadata = publicPage({
  path: "/privacy",
  title: "Confidentialité",
  description:
    `Ce que ${site.name} conserve sur vous — une adresse e-mail, un mot de passe haché, vos dictionnaires et vos grilles —, pour combien de temps, qui y touche et comment tout effacer.`,
});

/**
 * Chaque traitement ici figure au registre (docs/RGPD.md), et inversement. Tout nouveau champ mesuré y est
 * déclaré (ADR 0016, CLAUDE.md).
 */

// Les prestataires qui traitent des données pour le site (sous-traitants, RGPD art. 28)
const PROCESSORS = [
  { name: "OVH", what: "héberge le serveur de l'application et sa base de données", where: "France" },
  {
    name: "Cloudflare",
    what: "sert les pages du site, relaie les connexions au serveur, garde les sauvegardes chiffrées et fait suivre les messages envoyés à l'adresse de contact",
    where: "Union européenne et États-Unis (certifié Data Privacy Framework)",
  },
  { name: "Brevo", what: "envoie les e-mails du compte (confirmation de l'adresse, mot de passe oublié)", where: "France" },
  {
    name: "Sentry",
    what: "reçoit les rapports d'erreur, sans adresse IP, cookie ni contenu de formulaire",
    where: "Union européenne (Allemagne)",
  },
];

export default function PrivacyPage() {
  return (
    <main className="container mx-auto max-w-3xl p-4 md:p-8">
      <h1 className="text-3xl font-bold">Confidentialité</h1>
      <p className="mt-2 text-sm text-muted-foreground">Dernière mise à jour : 25 septembre 2026</p>

      <div className="mt-8 space-y-8 text-muted-foreground">
        <p className="rounded-lg border bg-secondary/20 p-4 text-foreground">
          {site.name} conserve votre adresse e-mail, votre mot de passe haché, vos dictionnaires et vos grilles, si
          vous créez un compte. Rien d&apos;autre : pas de mesure d&apos;audience, pas de publicité, aucun cookie en
          dehors de ceux de votre session, et aucune donnée vendue ni cédée.
        </p>

        <Section title="Qui est responsable">
          <p>
            L&apos;éditeur du site, un particulier (voir les{" "}
            <Link href="/legal" className={linkClass}>mentions légales</Link>), joignable à{" "}
            <a href={`mailto:${site.contactEmail}`} className={linkClass}>{site.contactEmail}</a>.
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
            Pourquoi : pour vous fournir le service que vous demandez en créant un compte (RGPD, art. 6.1.b). Vos
            recherches et les grilles que vous générez sans les conserver ne sont pas enregistrées. En invité, rien
            ne l&apos;est.
          </p>
        </Section>

        <Section title="Ce qui passe sans être conservé longtemps">
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
              journal technique du serveur la note aussi, avec la page demandée, pour diagnostiquer une panne ou une
              attaque ; il est effacé au bout de 14 jours (intérêt légitime, RGPD art. 6.1.f).
            </li>
            <li>
              <strong className="text-foreground">Les rapports d&apos;erreur</strong> : quand quelque chose casse, la
              page ou l&apos;action en cause part chez Sentry, sans adresse IP, cookie, mot de passe ni contenu de
              formulaire. Sentry les efface au bout de 90 jours au plus.
            </li>
          </ul>
        </Section>

        <Section title="Si vous écrivez à l'adresse de contact">
          <p>
            Votre message et votre adresse sont gardés le temps de vous répondre et de suivre votre demande, puis
            effacés au plus tard un an après le dernier échange.
          </p>
        </Section>

        <Section title="Durée et suppression">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              Vos données sont gardées tant que votre compte existe. Vous pouvez le supprimer à tout moment depuis{" "}
              <Link href="/account" className={linkClass}>Mon compte</Link> : l&apos;adresse e-mail, le mot de passe,
              les dictionnaires, les mots et les grilles sont effacés immédiatement et définitivement.
            </li>
            <li>
              Un compte où personne ne s&apos;est connecté depuis 3 ans est supprimé, après un e-mail de prévenance
              un mois avant.
            </li>
            <li>
              Des sauvegardes chiffrées de la base sont faites chaque nuit et gardées 30 jours : après la suppression
              d&apos;un compte, ses données y subsistent jusqu&apos;à l&apos;effacement de la dernière sauvegarde qui
              les contient.
            </li>
          </ul>
        </Section>

        <Section title="Qui y touche">
          <p>
            L&apos;éditeur, et les prestataires ci-dessous, pour le seul fonctionnement du site. Aucun ne reçoit vos
            dictionnaires ou vos grilles pour son propre usage.
          </p>
          <ul className="list-disc space-y-1 pl-5">
            {PROCESSORS.map((processor) => (
              <li key={processor.name}>
                <strong className="text-foreground">{processor.name}</strong> {processor.what}. Données traitées en :{" "}
                {processor.where}.
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Vos droits">
          <p>
            Vous pouvez consulter vos données dans l&apos;application (Mon compte, Dictionnaires, Mes grilles), les
            corriger, les effacer, vous opposer à un traitement ou en demander la limitation, et demander à les
            recevoir dans un format lisible. Écrivez à{" "}
            <a href={`mailto:${site.contactEmail}`} className={linkClass}>{site.contactEmail}</a>, depuis
            l&apos;adresse de votre compte : la réponse vient sous un mois. Si elle ne vous satisfait pas, vous pouvez
            saisir la <a href="https://www.cnil.fr/fr/plaintes" className={linkClass}>CNIL</a>.
          </p>
        </Section>
      </div>
    </main>
  );
}
