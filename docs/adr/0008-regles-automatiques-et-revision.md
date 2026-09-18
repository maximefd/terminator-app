# 0008 — Règles automatiques, filtre positif et révision des décisions

- Statut : acceptée
- Date : 2026-09-18

## Contexte

Après 4 958 décisions prises à la main (environ 2 h de tri effectif), l'analyse de
`data/lexicon/decisions.csv` donne des chiffres nets :

- **Le reste est hors d'atteinte à la main** : 376 286 mots de 11 lettres ou moins ne sont pas
  triés, soit environ 157 h au rythme observé (~2 400 mots/h).
- **La longueur décide presque tout** : les 21 layouts du catalogue demandent 94 % de mots de 2 à
  8 lettres ; 9 emplacements seulement, sur 821, dépassent 11 lettres. Or 580 000 mots de la file
  font 9 lettres ou plus.
- **Le bon niveau de décision est la famille, pas la forme** : la fréquence du lemme prédit la
  décision (19 % de mots gardés quand le lemme est absent de Lexique, 66 % entre 2 et 3, 73 %
  au-dessus de 3), alors que la fréquence propre de la forme n'apprend rien.
- **La fatigue laisse des traces** : 11,6 % des familles jugées forme par forme se contredisent
  (`BITA` supprimé, `BITAI` gardé, à quelques secondes d'écart).
- **Des classes entières n'ont jamais été gardées** : 119 formes en plusieurs mots triées, 119
  supprimées (« lot de », « aux WC ») ; 94,6 % de suppressions pour les mots absents de Lexique,
  sans définition ni lemme.
- **Un lexique plus petit remplit aussi bien les grilles** : sur 5 layouts × 5 seeds, le lexique
  complet (647 764 mots) réussit 24/25, un lexique filtré à 251 639 mots 25/25, et à 164 870 mots
  25/25 également ; 25 grilles ne consomment que ~700 mots distincts.

## Décision

1. **Règles automatiques déclaratives** (`tools/lexicon/autorules.py`). Une règle est une condition
   SQL sur la base du lexique, activée dans `data/lexicon/auto_rules.json` (versionné). Elle
   **n'écrit rien** dans `decisions.csv` : elle est appliquée à l'export et à la file de tri.
   - Conseillées par défaut, car mesurées : `formes-composees` et `inconnues-sans-definition`.
   - Sur demande seulement : `flexions-rares-longues` (415 065 mots : trop large pour être activée
     sans regarder l'aperçu).
   - `python -m tools.lexicon autorules` montre, pour chaque règle, le nombre de mots, des exemples
     et ce qui est déjà décidé, **sans rien écrire**.
2. **Une décision explicite « garder » l'emporte toujours** sur une règle et sur un filtre.
3. **Filtre positif optionnel à l'export** : `--filtre moyen` ne garde que les mots connus de
   Lexique, définis pour eux-mêmes, ou formés sur un lemme de fréquence zipf ≥ 2. Le défaut reste
   `aucun` : changer le lexique de Terminator reste un geste volontaire.
4. **Révision des décisions** (`tools/lexicon/review.py`) : les décisions prises mot à mot sont
   relues quand elles sont douteuses — famille jugée à l'opposé, mot courant supprimé, rafale de
   décisions dans la même seconde. Confirmer ou corriger écrit une ligne dans un lot marqué
   `revision` (`20260918120000-revision.3f9a1c`), donc un mot revu ne revient jamais.
5. **`decisions.csv` reste la seule source de vérité des choix humains** ([ADR 0001](0001-consigner-les-decisions.md),
   [ADR 0005](0005-pipeline-du-lexique-et-decisions.md)) : ni les règles ni les filtres n'y écrivent.

## Conséquences

- Le lexique exporté est reproductible à partir de trois éléments versionnés : les décisions, le
  fichier de règles et le filtre choisi. Désactiver une règle (`--aucune`) rend ses mots d'un coup,
  sans réécrire l'historique.
- Le tri à la main se concentre là où il compte : les mots courts, et une décision par famille.
- **Risque assumé** : `formes-composees` retire aussi des locutions qui pourraient servir en grille
  (`APRIORI`, `EXNIHILO`). Les 119 cas triés à la main ont tous été supprimés, et un mot voulu se
  récupère par une décision « garder », qui l'emporte sur la règle.
- Activer une règle ou un filtre change le dictionnaire du générateur : à mesurer au benchmark
  (`make bench`) avant d'en faire le défaut de l'API.
- Les lots `revision` distinguent le deuxième regard du premier tri : les statistiques de curation
  et l'historique restent lisibles.
