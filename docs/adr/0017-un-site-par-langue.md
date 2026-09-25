# 0017 — Un site par langue, un seul moteur

- Statut : acceptée
- Date : 2026-09-24

## Contexte

- **Les langues visées.** Après le français, l'auteur vise l'anglais et l'allemand, puis l'espagnol. Le public se trouvera peut-être ailleurs qu'en France :
  - les mots fléchés sont très répandus en Allemagne (*Schwedenrätsel*), en Scandinavie et aux Pays-Bas ;
  - au Royaume-Uni, ce sont les *arrowords* ;
  - en Espagne, les *autodefinidos*.
- **Chaque pays a ses conventions :**
  - l'allemand écrit Ä, Ö et Ü en deux lettres (AE, OE, UE), et ß en SS ;
  - l'espagnol garde Ñ comme une lettre à part ;
  - l'anglais n'a que A–Z.

  Les mises en page et le style des définitions suivent les publications de chaque pays.
- **La décision de l'auteur (24/09/2026).** Chaque site portera un **nom descriptif dans sa langue**, plutôt qu'une marque internationale unique. Terminator reste le nom du moteur.
- **L'état du code :** aucune notion de langue.
  - Deux normalisations coexistent. `DictionnaireTrie._normalize` retire tirets, apostrophes et espaces ; `routes.normalize_pattern`, qui traite les mots imposés, les mots souhaités et les dictionnaires personnels, les garde. Aucune des deux ne décompose Œ ni Æ.
  - L'alphabet A–Z est écrit en dur : scores des lettres, retouche d'une grille, saisie dans l'éditeur.
  - Il n'y a qu'un lexique, qui occupe 601 Mo de RAM.
  - Les textes français sont écrits en dur dans une quarantaine de fichiers du frontend, et dans les messages de l'API.
- **Les cookies de session valent pour un domaine** ([ADR 0015](0015-session-en-cookies.md)) : le frontend et l'API d'un même site doivent partager ce domaine.

## Décision

1. **Un site par langue**, à la racine de son domaine, sans préfixe `/fr/`. Chaque site a :
   - son nom ;
   - son domaine : celui du pays quand il existe (`.fr`, `.de`, `.es`), `.com` ou `.co.uk` pour l'anglais ;
   - ses contenus ;
   - ses pages légales (en Allemagne, un Impressum) ;
   - ses e-mails ;
   - sa propriété Search Console.
2. **Un seul code frontend, un export statique par site.**
   - Une configuration de site, lue au build, remplace tout nom écrit en dur : nom, URL du site, langue, adresses de contact, URL de l'API.
   - Le build échoue sans URL de site, comme il échoue déjà sans URL d'API.
   - Chaque site a son projet Cloudflare Pages.
3. **Un seul moteur, un seul serveur, une seule base.**
   - Chaque site a son sous-domaine `api.`, du même site que son frontend pour les cookies, relié au même tunnel.
   - Deux formes sont possibles, à choisir en Phase 10 :
     - **un conteneur d'API par site** (la forme par défaut) : les sites ne diffèrent que par leurs variables d'environnement, et chaque conteneur ne charge que le lexique de sa langue. Ils partagent PostgreSQL et le dossier des verrous : la limite de deux générations simultanées reste globale ;
     - **une API pour plusieurs noms d'hôte** : le domaine des cookies, l'adresse des liens et l'expéditeur des e-mails viennent d'une liste fermée, indexée par l'hôte. Jamais de l'en-tête `Host` brut, sinon un lien de réinitialisation pourrait être détourné.
4. **La langue devient une dimension des données liées au lexique :**
   - `lang` dans les contrats de recherche et de génération, sur les grilles conservées, les dictionnaires et les événements ([ADR 0016](0016-mesure-d-usage-sans-cookie.md)) ;
   - un lexique et un fichier de décisions par langue ;
   - des layouts rattachés à une tradition : mots fléchés français, Schwedenrätsel, arrowords, autodefinidos ;
   - des tables de difficulté par langue.
5. **Une seule normalisation, paramétrée par la langue.** Voici la cible, à confirmer sur les publications de chaque pays :

   | Langue | Règle |
   |--------|-------|
   | Français | Accents retirés ; Œ → OE, Æ → AE ; tirets, apostrophes et espaces retirés |
   | Allemand | Ä → AE, Ö → OE, Ü → UE, ß → SS |
   | Espagnol | Accents retirés, **Ñ gardé** comme 27e lettre |
   | Anglais | A–Z |

6. **Avant l'ouverture du site français, deux choses seulement :**
   - le nom du site vient de la configuration : plus aucun « Terminator » visible, ni dans l'interface ni dans les e-mails ;
   - toute **nouvelle** donnée liée au lexique ou à l'usage porte sa langue.

   Tout le reste attend la [Phase 10](../ROADMAP.md) : catalogues de textes, messages de l'API par code, alphabet, lexiques par langue.
7. **Dès maintenant, chaque nouvelle erreur de l'API porte un code `reason` stable**, comme la génération le fait déjà. Le texte se traduira, le code restera.
8. **`data/lexicon/decisions.csv` reste le fichier du français**, en ajout seul. Chaque langue aura le sien.
9. **Les identifiants techniques gardent « terminator »** : dépôt, conteneurs, base, format d'export `terminator/grille`, clés `terminator:*` du navigateur.

## Conséquences

- ✅ Le site français ouvre sans refonte des routes. Ses adresses ne changeront pas quand d'autres langues arriveront.
- ✅ Chaque pays reçoit un site qui parle sa langue et suit ses conventions.
- **Référencement :** chaque domaine se construit seul. Les liens `hreflang` entre domaines se limitent aux pages vraiment équivalentes, et vont dans les deux sens.
- **Coûts par site :** un domaine (~10 € par an), des pages légales, une authentification d'envoi chez Brevo. Le quota gratuit d'e-mails est partagé entre les sites.
- **Comptes :** l'adresse e-mail est aujourd'hui unique dans toute la table. Des comptes séparés par site demanderaient une unicité sur le couple (site, e-mail). À trancher à l'arrivée du deuxième site.
- **Mémoire :** le lexique français occupe 601 Mo sur 4 Go, et chaque langue ajoute le sien. Avant la deuxième langue, il faudra la curation, une représentation plus compacte, ou le VPS-2 ([Phase 7](../ROADMAP.md)).
- **La normalisation française est déjà fautive :** `porte-monnaie` devient `PORTE-MONNAIE`, `cœur` devient `CŒUR`. L'unifier sert avant même le multilingue.
