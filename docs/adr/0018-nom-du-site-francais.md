# 0018 — Nom et domaine du site français

- Statut : proposée (acceptée quand le domaine sera acheté)
- Date : 2026-09-24

## Contexte

- « Terminator » devient le nom du moteur ([ADR 0017](0017-un-site-par-langue.md)). Comme nom public, il pose deux problèmes :
  - c'est une marque de cinéma connue ;
  - il ne dit pas ce que fait le site.
- L'auteur veut un **nom descriptif français** pour le site français.
- **Le nom conditionne la mise en ligne**, parce qu'il fixe :
  - le domaine des cookies (`COOKIE_DOMAIN`) et les origines CORS ;
  - l'expéditeur et l'authentification des e-mails (Brevo) ;
  - la zone Cloudflare et le projet Pages ;
  - les mentions légales et la propriété Search Console.

  Le changer après l'ouverture coûterait une migration de référencement.
- La plupart des recherches « mots fléchés » viennent de joueurs qui cherchent une grille ou une solution. Le site, lui, sert à **créer** ; la recherche par motif attirera les autres.

## Décision (proposée)

1. **Critères** :
   - descriptif et français, professionnel, facile à dire et à écrire ;
   - dit *créer* plutôt que *jouer* ou *résoudre* ;
   - `.fr` disponible, sans accent dans le nom de domaine ;
   - **pas de conflit avec une marque existante**, en particulier celle d'un éditeur de jeux (bases INPI, EUIPO et WIPO ; classes 9, 16, 41 et 42). Un nom purement descriptif se protège mal : le vrai risque est d'empiéter sur le nom d'un autre.
2. **Pistes à vérifier** (disponibilité non vérifiée) :

   | Nom | Domaine envisagé | Pour | Contre |
   |-----|------------------|------|--------|
   | L'Atelier des mots fléchés | `atelier-mots-fleches.fr` | Reprend le positionnement du README : « l'atelier d'un auteur » | Long |
   | La Fabrique à mots fléchés | `fabrique-mots-fleches.fr` | Chaleureux, dit la fabrication | Long |
   | Mots fléchés sur mesure | `mots-fleches-sur-mesure.fr` | Annonce les grilles personnalisées (Phase 11) | Moins « outil d'auteur » |
   | Créateur de mots fléchés | `createur-mots-fleches.fr` | Colle à la recherche « créer des mots fléchés » | Générique |
   | Verbicruciste | `verbicruciste.fr` | Le nom du métier : court, distinctif | Inconnu du grand public |

3. **Achat du domaine** :
   - chez OVH (déjà prestataire) ou Gandi, avec renouvellement automatique ;
   - géré ensuite par les serveurs de noms de Cloudflare, qui ne vend pas forcément le `.fr` ;
   - les variantes avec et sans tiret aussi, si elles sont libres.
4. **Hôtes et adresses** :
   - `<nom>.fr` : le site (Cloudflare Pages), et hôte canonique. `www` redirige vers lui, ou l'inverse : à fixer une fois pour toutes ;
   - `api.<nom>.fr` : l'API, par le tunnel ; `COOKIE_DOMAIN=<nom>.fr` ;
   - `no-reply@<nom>.fr` : les envois (Brevo ; SPF, DKIM, DMARC) ;
   - `contact@<nom>.fr` et `securite@<nom>.fr` : la réception, par Cloudflare Email Routing (gratuit), vers la boîte de l'auteur.

## Conséquences

- Tant que le nom n'est pas choisi, la mise en ligne attend : c'est la première étape de la Phase 6 (6b dans la [roadmap](../ROADMAP.md)).
- Une fois le nom choisi, trois suites :
  - cette ADR passe en « acceptée » ;
  - le nom entre dans la configuration du site (6c) ;
  - les exemples `terminator.fr` de la documentation sont remplacés.
- Les mots-clés vont dans les titres et les textes des pages, pas seulement dans le nom.
