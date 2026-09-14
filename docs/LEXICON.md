# 📚 Lexique — Terminator

> Le dictionnaire commun utilisé par la recherche et la génération : d'où il vient, comment il est chargé, et comment il va être nettoyé.

## Aujourd'hui : le DELA

- **Fichier** : `backend/dela_clean.csv` (~55 Mo, 980 292 lignes), dérivé du DELA (dictionnaire électronique des formes fléchies du français).
- **Colonnes** (séparateur `;`) : forme en majuscules ; forme affichée (avec accents) ; description (toujours « Forme fléchie de … », donc **pas de vraie définition**).
- **Normalisation** (`DictionnaireTrie._normalize`) : majuscules, accents retirés, seuls les caractères alphanumériques gardés (espaces, tirets et apostrophes supprimés), 2 lettres minimum.
- **Résultat** : **714 092 mots distincts**, dont ~393 000 de 11 lettres ou moins.
- **Chargement** : au démarrage de l'API, tout le fichier est inséré dans un Trie en mémoire (`app.dela_trie`). Cela prend du temps et beaucoup de RAM.

| Longueur | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|----------|---|---|---|---|---|---|---|---|----|----|
| Mots | 91 | 604 | 2 580 | 8 310 | 19 827 | 37 843 | 60 214 | 80 091 | 91 780 | 92 380 |

### Le problème

Le DELA contient **toutes les formes fléchies** : conjugaisons, pluriels, mots très rares. Les grilles générées se remplissent de mots peu naturels (« ELIERA », « AUNES »…). Or la qualité des mots est la priorité pour un auteur de mots fléchés. Un dictionnaire plus petit rendrait aussi le solveur plus rapide.

Les dictionnaires **personnels**, eux, sont en base de données (voir [ARCHITECTURE.md](ARCHITECTURE.md)).

## Prévu : la curation (Phase 1 de la roadmap)

Objectif : un lexique curé, construit à partir de **décisions manuelles** de l'auteur, aidées par des données de fréquence.

1. **Pipeline de données** (`tools/lexicon/`) :
   - croiser le DELA avec **Lexique 3.83** (fréquence, lemme, catégorie grammaticale) et le **Wiktionnaire** (définitions) ;
   - produire une base locale reconstructible.
2. **Source de vérité versionnée** : `data/lexicon/decisions.csv` (`mot;decision;date`). Un mot supprimé le reste ; la décision porte sur la forme normalisée utilisée dans les grilles.
3. **Mini-app de tri** (`tools/curator/`) :
   - utilisable depuis le téléphone ou l'ordinateur sur le réseau local ;
   - une carte par mot (définition, fréquence, suggestion) ;
   - **une touche par décision** : `←` supprimer, `→` garder, `↓` annuler, `↑` passer.
4. **Bascule** : l'API charge le lexique curé (derrière un flag de configuration), la recherche affiche les définitions, le générateur utilise la fréquence.

Détails : [ROADMAP.md](ROADMAP.md), Phase 1.
