# Notice — `dela_clean.csv`

`dela_clean.csv` est une **version modifiée** du dictionnaire électronique des formes fléchies du français (DELAF), conçu au Laboratoire d'Automatique Documentaire et Linguistique (LADL, équipe de Maurice Gross) et diffusé avec Unitex/GramLab (https://unitexgramlab.org/fr/language-resources).

Cette ressource est distribuée sous la **Lesser General Public License For Linguistic Resources (LGPLLR)**, dont le texte est joint : [`LGPLLR.txt`](LGPLLR.txt). Conformément à sa section 2, sa version modifiée l'est aussi.

## Modifications

Apportées au fichier d'origine pour Terminator (versionné dans ce dépôt depuis le 09/10/2025) :

- une ligne par forme, en trois colonnes séparées par `;` : forme normalisée (majuscules, sans accents ni caractères autres que lettres et chiffres), forme affichée, indication de lemme (« Forme fléchie de '…' ») ;
- les codes grammaticaux et flexionnels du DELAF ne sont pas repris.

Le lexique curé que l'API charge en priorité (`data/lexicon/build/lexique_cure.csv`, non versionné) en dérive à son tour : des mots en sont retirés par l'auteur, et des colonnes de définition et de fréquence y sont ajoutées. Voir [docs/LEXICON.md](../docs/LEXICON.md) et [docs/LICENCES.md](../docs/LICENCES.md).
