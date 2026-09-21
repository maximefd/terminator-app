# Audit UX — septembre 2026

Passage en revue de chaque écran existant avec les trois questions du standard de la
[roadmap](ROADMAP.md) : *qu'est-ce que c'est ? que puis-je faire ici ? que se passe-t-il ensuite ?*
([#21](https://github.com/maximefd/terminator-app/issues/21))

Les frictions corrigées le sont dans la même série de commits que ce document. Celles qui ne le sont pas
disent pourquoi, et portent un numéro d'issue.

## Accueil

L'adresse racine ouvrait directement sur le champ de recherche : un arrivant voyait une case de saisie sans
savoir ce que le logiciel fait ni qu'il sait aussi remplir une grille entière. Corrigé par la page d'accueil
([#22](https://github.com/maximefd/terminator-app/issues/22)) ; la recherche a pris l'adresse `/search`.

## Recherche par motif

| Friction | Correction |
|---|---|
| Aucun titre ni explication : le champ seul n'apprend pas la syntaxe | Titre et une phrase : les lettres connues, un `?` par case vide |
| Le champ n'avait pas d'intitulé, seulement un texte d'exemple — un lecteur d'écran n'annonçait rien d'autre | `<label>` (visuellement masqué) « Motif à rechercher » |
| Écran vide muet tant qu'on n'a rien tapé | Trois motifs cliquables (`P??LE`, `?A?SON`, `MER??`), vérifiés : ils renvoient 10, 6 et 7 mots |
| Une lettre saisie : rien ne se passe, sans dire pourquoi | « Encore une lettre : la recherche démarre à deux caractères » |
| « Aucun résultat » sans issue | Dit quoi faire : élargir avec un `?`, ou ajouter le mot à un dictionnaire |
| La saisie s'affichait en minuscules alors que la recherche travaille en majuscules | Champ en capitales espacées, comme les cases d'une grille |

## Dictionnaires personnels

| Friction | Correction |
|---|---|
| Aucune adresse à eux : une colonne de la page de recherche, visible seulement une fois connecté | Page `/dictionaries` et entrée de menu ; déconnecté, elle explique à quoi sert un compte |
| « Aucun mot ne correspond à vos critères » s'affichait aussi bien pour un dictionnaire vide que pour un filtre trop étroit | Deux messages distincts, dont « Ce dictionnaire est vide : ajoutez un premier mot ci-dessus » |
| Supprimer un dictionnaire était **impossible depuis l'interface**, alors que l'API le permet (`DELETE /api/dictionaries/<id>`) | Bouton de suppression, avec une confirmation qui nomme le dictionnaire et son nombre de mots |
| Le bouton « + » qui crée un dictionnaire n'était qu'une icône : sans nom pour un lecteur d'écran | `aria-label` « Créer un dictionnaire » |
| Le bouton de suppression d'un mot n'apparaissait qu'au survol : invisible au clavier, et sans intitulé | Visible aussi au focus, et intitulé « Supprimer *mot* » |
| Le rôle du dictionnaire « actif » n'était écrit nulle part | Une phrase sous le sélecteur : ses mots remontent dans la recherche et alimentent les grilles |
| Le filtre de longueur n'avait pour intitulé que « Lg. » dans le champ | `aria-label` « Filtrer par longueur » |
| Les définitions saisies n'apparaissaient jamais dans la liste | Définition affichée sous chaque mot |
| Le panneau imposait sa largeur (`max-w-sm`), inutilisable en pleine page | La largeur revient à la page qui l'affiche |
| Supprimer le dictionnaire **actif** n'en laissait aucun d'actif côté serveur : le sélecteur en montrait un, mais la recherche et les grilles perdaient silencieusement les mots personnels | Un dictionnaire restant est réactivé aussitôt |
| L'API recrée un « Dictionnaire par défaut » dès que la liste est vide : supprimer le dernier en fait apparaître un autre, sans prévenir | La confirmation le dit avant le geste, quand c'est le dernier |

## Connexion et inscription

| Friction | Correction |
|---|---|
| Aucun titre de document : l'onglet affichait l'URL, et un lecteur d'écran n'annonçait pas la page (trouvé par axe, #25) | Une page serveur porte les métadonnées, le formulaire reste un composant client |
| Aucun état d'attente : le bouton restait cliquable pendant l'appel réseau | Bouton désactivé et libellé « Connexion en cours… » / « Création du compte… » |

Le reste tient : intitulés associés, `autocomplete` correct, minimum de mot de passe annoncé, erreurs en
français, lien croisé entre les deux pages.

## Génération

Écran refait en [#23](https://github.com/maximefd/terminator-app/issues/23) : liste de mots ordonnée,
obligatoires contre souhaités, difficulté annoncée pendant la saisie, refus expliqués cause par cause,
provenance des mots colorée dans la grille produite.

Restent deux manques, qui ne sont pas des oublis d'interface mais des champs d'API non implémentés
([ADR 0007](adr/0007-contrat-de-generation.md)) : on ne peut ni **choisir la mise en page** dans un format,
ni **rejouer une seed** — donc pas non plus retrouver une grille obtenue la veille. La sauvegarde des
grilles est l'objet de [#24](https://github.com/maximefd/terminator-app/issues/24).

## Non corrigé, et pourquoi

- **Mentions légales et confidentialité décrivent un produit qui n'existe pas**
  ([#78](https://github.com/maximefd/terminator-app/issues/78)) : elles parlent de cookies, d'adresse IP
  collectée et de transferts de données, alors que rien n'est déployé ([ADR 0004](adr/0004-pas-de-deploiement-en-ligne.md))
  et que la session tient dans le `localStorage` du navigateur. Un texte faux est pire que pas de texte, mais
  le réécrire n'est pas un geste d'interface : il attend sa propre issue.
- **Suppression du compte** ([#79](https://github.com/maximefd/terminator-app/issues/79)) : l'API expose
  `DELETE /api/users/me` et efface tout en cascade ; l'interface ne l'atteint pas. Il manque un écran de
  compte, que la page de confidentialité devra citer.
- **Le parcours connecté est couvert par un test** (`frontend/tests/dictionaries.spec.ts`) : créer un dictionnaire, ajouter un mot avec sa définition, supprimer l'un puis l'autre. Il a servi à vérifier ces corrections, que je ne peux pas éprouver à la main — je ne saisis pas d'identifiants.
- **Supprimer un mot ne demande pas confirmation** : c'est délibéré. C'est le geste que l'on répète le plus
  dans un dictionnaire, et une confirmation par mot le rendrait pénible. À revoir si une liste se met à
  servir de brouillon.
