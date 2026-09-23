# ⚖️ Licences — Terminator

> Revue du 23/09/2026, préalable à la mise en ligne (Phase 6, [ADR 0013](adr/0013-cible-hebergement-production.md)). Ce document recense ce que Terminator emprunte, sous quelle licence, et ce que chaque licence demande. Ce n'est pas un avis juridique. Les décisions de l'auteur (24/09/2026) sont notées en fin de document ; reste un point marqué ⚠️, à traiter dans #83.

## Ce qui compte : distribuer ou servir

Les obligations de ces licences naissent surtout quand on **distribue** une ressource : un fichier publié dans le dépôt public, une police envoyée au navigateur. Faire tourner un programme sur un serveur ne déclenche en général rien. Le LGPLLR le dit en toutes lettres (section 0 : les activités autres que la copie, la distribution et la modification sont hors de son champ). Les licences Creative Commons, en revanche, comptent aussi l'affichage public comme un partage.

Aujourd'hui, le dépôt GitHub est **public** : tout fichier versionné est distribué.

## Données linguistiques

| Ressource | Licence | Usage dans Terminator | Distribuée ? | Obligations | État |
|-----------|---------|-----------------------|--------------|-------------|------|
| **DELA** (`backend/dela_clean.csv`), formes fléchies du français, issu du DELAF du LADL diffusé avec [Unitex/GramLab](https://unitexgramlab.org/fr/language-resources) | [LGPLLR](https://spdx.org/licenses/LGPLLR.html) | Liste de mots de la recherche et de la génération ; base du lexique curé | **Oui** : versionné dans le dépôt public | Joindre la licence et une notice de copyright ; signaler et dater les modifications ; une version modifiée reste sous LGPLLR. Rien pour un usage serveur | ✅ [`backend/DELA-NOTICE.md`](../backend/DELA-NOTICE.md) et [`backend/LGPLLR.txt`](../backend/LGPLLR.txt). Provenance exacte non retracée : le fichier a été retouché trop souvent pour qu'elle ait un sens (décision de l'auteur) |
| **Lexique 3.83** ([lexique.org](http://www.lexique.org)), B. New, C. Pallier et coll. | CC BY-SA 4.0 | Fréquence (zipf) : tri et filtres du curateur, colonne du lexique curé, critère facultatif du solveur | Non : `data/lexicon/raw/` et `data/lexicon/build/` ne sont pas versionnés ; aucune fréquence n'est affichée dans l'application | Si le lexique curé (qui porte la fréquence) est un jour publié : attribution et même licence pour lui | ✅ Rien à faire tant qu'il n'est pas publié ; citer Lexique dans les crédits (voir plus bas) |
| **Wiktionnaire**, via [kaikki.org](https://kaikki.org/frwiktionary/) (wiktextract, T. Ylonen) | CC BY-SA 4.0 et GFDL | Définitions affichées **dans le curateur**, outil local ; colonne du lexique curé | Non : ni versionnées, ni servies par l'API (la recherche renvoie `definition: null` pour les mots du lexique) | Si des définitions du Wiktionnaire s'affichent un jour dans l'application (piste de #83) : attribution visible (« Wiktionnaire, CC BY-SA ») et même licence pour ces définitions | ⚠️ À prévoir **dans #83** avant d'afficher la moindre définition |
| **Décisions de curation** (`data/lexicon/decisions.csv`) | Travail de l'auteur | Tri du lexique | Oui (dépôt public) | Aucune : ce sont les choix de l'auteur | ✅ Dépôt privé à la mise en ligne (voir « Dépôt public ») |

## Mises en page (layouts)

`backend/layouts/` contient des géométries de grilles, dont certaines sont **recopiées de livres** de mots fléchés (#15). Une géométrie seule (où sont les cases définitions) est probablement trop pauvre pour être protégée par le droit d'auteur. Recopier méthodiquement les grilles d'un même éditeur peut en revanche toucher son droit de producteur de base de données, qui protège la collection.

Décision de l'auteur : la provenance des layouts n'est pas suivie. Ce sont des géométries, sans les mots ni les définitions de leurs grilles d'origine.

## Polices

| Police | Licence | Usage | Obligations | État |
|--------|---------|-------|-------------|------|
| Archivo Narrow (Omnibus-Type), `frontend/public/fonts/` | [SIL OFL 1.1](https://openfontlicense.org/) | Rendu des grilles à l'écran et dans le PDF exporté | La licence et la notice de copyright accompagnent les fichiers distribués ; l'intégration dans un PDF est permise | ✅ [`frontend/public/fonts/OFL.txt`](../frontend/public/fonts/OFL.txt) |

## Dépendances logicielles

Relevé du 23/09/2026 (`pnpm licenses list --prod`, `pip-licenses`) :

- **Frontend** : 83 paquets en production, MIT pour l'essentiel, puis Apache-2.0, ISC, BSD, 0BSD. `caniuse-lite` est en CC BY 4.0 : ce sont des données utilisées au build, sans obligation pour l'application servie.
- **Backend** : MIT, BSD, Apache-2.0, PSF, et `email-validator` sous Unlicense. `psycopg2-binary` est en **LGPL** : utilisée comme bibliothèque, sans modification, elle n'impose rien au code de Terminator.

Aucune licence contaminante (GPL, AGPL) : le code de Terminator peut rester fermé s'il le faut.

## Dépôt public et code de Terminator

Le dépôt n'a **aucun fichier de licence**. Par défaut, tout y est « tous droits réservés » : on peut le lire sur GitHub, pas le réutiliser. C'est protecteur, mais `decisions.csv` et les layouts (le vrai travail de curation) sont lisibles par tous.

Décision de l'auteur : le dépôt **reste public pendant le développement, et passe en privé à la mise en ligne**. Sur GitHub Free, un dépôt privé perd la protection de branche qui impose la CI verte ; la règle continuera d'être suivie à la main.

## Crédits à afficher dans l'application

Rien n'y oblige tant que l'application n'affiche que des mots (le LGPLLR ne régit pas l'usage serveur). C'est pourtant l'usage, et c'est honnête. La page des mentions légales (#78) citera donc :

- le **DELA** (LADL, Unitex/GramLab, LGPLLR) pour la liste des mots ;
- **Lexique 3.83** (New, Pallier et coll., CC BY-SA 4.0) pour les fréquences ;
- **Archivo Narrow** (Omnibus-Type, SIL OFL 1.1) pour la police des grilles ;
- le **Wiktionnaire** (CC BY-SA), le jour où une de ses définitions s'affichera.
