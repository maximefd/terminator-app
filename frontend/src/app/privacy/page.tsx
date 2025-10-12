// DANS src/app/privacy/page.tsx

import { type Metadata } from "next";

export const metadata: Metadata = {
  title: "Politique de Confidentialité | Terminator",
  description: "Découvrez comment nous collectons, utilisons et protégeons vos données sur Terminator.",
};

export default function PrivacyPage() {
  return (
    <main className="container mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-bold mb-8">Politique de Confidentialité</h1>
      
      <div className="space-y-6 text-muted-foreground">
        <p><strong>Dernière mise à jour :</strong> 12 Octobre 2025</p>

        <section className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">1. Introduction</h2>
          <p>
            Bienvenue sur Terminator. Nous respectons votre vie privée et nous nous engageons à la protéger. Cette politique de confidentialité vous expliquera comment nous traitons vos données personnelles lorsque vous visitez notre site web (quel que soit l&apos;endroit d&apos;où vous le visitez) et vous informera de vos droits en matière de protection de la vie privée.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">2. Les données que nous collectons</h2>
          <p>Nous pouvons collecter, utiliser, stocker et transférer différents types de données personnelles vous concernant :</p>
          <ul className="list-disc list-inside space-y-1 pl-4">
            <li><strong>Données d&apos;identité :</strong> Pour les utilisateurs authentifiés, nous stockons votre adresse e-mail.</li>
            <li><strong>Données de contenu :</strong> Nous stockons les mots et les dictionnaires que vous créez et sauvegardez sur votre compte.</li>
            <li><strong>Données techniques :</strong> Adresse IP, type et version du navigateur, fuseau horaire et localisation, types et versions de plug-in de navigateur, système d&apos;exploitation et plate-forme.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">3. Comment vos données sont-elles collectées ?</h2>
          <p>
            Nous utilisons différentes méthodes pour collecter des données, y compris par le biais de :
          </p>
          <ul className="list-disc list-inside space-y-1 pl-4">
            <li><strong>Interactions directes :</strong> Vous pouvez nous donner votre identité et vos données de contenu en créant un compte, en ajoutant des mots à vos dictionnaires ou en nous contactant.</li>
            <li><strong>Technologies automatisées :</strong> Lorsque vous interagissez avec notre site web, nous pouvons collecter automatiquement des données techniques. Nous collectons ces données personnelles en utilisant des cookies et d&apos;autres technologies similaires.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">4. Utilisation de vos données personnelles</h2>
          <p>
            Nous n&apos;utiliserons vos données personnelles que lorsque la loi nous y autorise. Le plus souvent, nous utiliserons vos données personnelles dans les circonstances suivantes :
          </p>
          <ul className="list-disc list-inside space-y-1 pl-4">
            <li>Pour fournir et maintenir notre service, y compris pour vous permettre de créer et gérer vos dictionnaires personnels.</li>
            <li>Pour gérer votre compte et vous fournir un support client.</li>
            <li>Pour améliorer notre site web afin de garantir que le contenu est présenté de la manière la plus efficace pour vous.</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">5. Sécurité des données</h2>
          <p>
            Nous avons mis en place des mesures de sécurité appropriées pour empêcher que vos données personnelles ne soient accidentellement perdues, utilisées ou consultées de manière non autorisée, modifiées ou divulguées.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">6. Vos droits</h2>
          <p>
            Conformément à la réglementation sur la protection des données, vous disposez de droits sur vos données personnelles, notamment le droit de demander l&apos;accès, la correction, l&apos;effacement, ou la portabilité de vos données.
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-xl font-semibold text-foreground">7. Nous contacter</h2>
          <p>
            Si vous avez des questions concernant cette politique de confidentialité, veuillez nous contacter à [votre adresse e-mail de contact].
          </p>
        </section>
      </div>
    </main>
  );
}