import { type Metadata } from "next";
import Link from "next/link";
import { linkClass, Section } from "@/components/legal/section";
import { site } from "@/config/site";
import { publicPage } from "@/lib/seo";

export const metadata: Metadata = publicPage({
  path: "/terms",
  title: "Conditions d'utilisation",
  description: `Les règles d'utilisation de ${site.name} : ce qui vous appartient, ce que le site vous doit, et ce qu'il ne garantit pas.`,
});

export default function TermsPage() {
  return (
    <main className="container mx-auto max-w-3xl p-4 md:p-8">
      <h1 className="text-3xl font-bold">Conditions d&apos;utilisation</h1>
      <p className="mt-2 text-sm text-muted-foreground">Dernière mise à jour : 25 septembre 2026</p>

      <div className="mt-8 space-y-8 text-muted-foreground">
        <p className="rounded-lg border bg-secondary/20 p-4 text-foreground">
          En bref : {site.name} est gratuit et fourni tel quel. Vos dictionnaires et vos grilles sont à vous. Les
          mots que vous suggérez pour le dictionnaire commun deviennent ceux du site. N&apos;utilisez pas le site
          pour nuire à d&apos;autres ou au service.
        </p>

        <Section title="Le service">
          <p>
            {site.name} aide à créer des grilles de mots fléchés : recherche de mots par motif, génération
            automatique de grilles, définitions et export. Il est gratuit, sans publicité. On peut l&apos;utiliser
            sans compte ; un compte permet de conserver ses dictionnaires et ses grilles.
          </p>
        </Section>

        <Section title="Votre compte">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              Il faut avoir au moins 15 ans pour créer un compte, ou l&apos;accord d&apos;un parent.
            </li>
            <li>
              Vous gardez votre mot de passe pour vous : ce qui est fait avec votre compte est réputé fait par vous.
            </li>
            <li>
              Vous pouvez supprimer votre compte à tout moment depuis{" "}
              <Link href="/account" className={linkClass}>Mon compte</Link>.
            </li>
          </ul>
        </Section>

        <Section title="Ce qui vous appartient">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong className="text-foreground">Vos dictionnaires et vos grilles</strong> restent les vôtres.{" "}
              {site.name} ne les conserve que pour vous les rendre, ne les montre à personne et n&apos;en fait aucun
              autre usage.
            </li>
            <li>
              <strong className="text-foreground">Les grilles que vous créez</strong>, générées ou non, vous pouvez
              les utiliser librement : les imprimer, les partager, les publier, y compris dans un cadre commercial.
              Vous êtes responsable de leur contenu, en particulier des mots et des définitions que vous y mettez.
            </li>
          </ul>
        </Section>

        <Section title="Le dictionnaire commun et vos suggestions">
          <p>
            Le tri du dictionnaire commun, les formats de grilles et le moteur de génération sont le travail du
            site ; les ressources qu&apos;il emprunte gardent leur licence (voir les crédits des{" "}
            <Link href="/legal" className={linkClass}>mentions légales</Link>). Quand vous suggérez un mot à ajouter
            ou à retirer, vous acceptez qu&apos;il soit utilisé, gratuitement et sans limite de durée, pour enrichir
            ce dictionnaire ; il n&apos;y a aucun droit à réclamer sur le résultat, y compris le jour où le site
            proposerait une offre payante.
          </p>
        </Section>

        <Section title="Ce qui n'est pas permis">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              Surcharger le service, par exemple en lançant des générations ou des recherches automatisées en masse.
            </li>
            <li>Tenter d&apos;accéder aux données d&apos;un autre, ou de contourner les protections du site.</li>
            <li>Enregistrer dans vos dictionnaires ou vos grilles un contenu illicite.</li>
          </ul>
          <p>
            En cas d&apos;abus, l&apos;accès peut être limité ou le compte supprimé. Une faille découverte de bonne
            foi est la bienvenue : signalez-la à{" "}
            <a href={`mailto:${site.securityEmail}`} className={linkClass}>{site.securityEmail}</a>.
          </p>
        </Section>

        <Section title="Sans garantie">
          <p>
            Le site est fourni tel quel, par un particulier, sans garantie de disponibilité ni de résultat : une
            grille peut ne pas pouvoir être générée, un mot peut manquer ou être rare, le service peut être
            interrompu. Gardez une copie de ce qui compte pour vous (l&apos;export PDF et le fichier de travail sont
            faits pour cela). Dans les limites permises par la loi, l&apos;éditeur n&apos;est pas responsable des
            dommages indirects liés à l&apos;utilisation du site.
          </p>
        </Section>

        <Section title="Changements et droit applicable">
          <p>
            Ces conditions peuvent changer ; la date en haut de la page l&apos;indique. Un changement important est
            annoncé sur le site. Elles sont soumises au droit français. Pour toute
            question : <Link href="/contact" className={linkClass}>contact</Link>.
          </p>
        </Section>
      </div>
    </main>
  );
}
