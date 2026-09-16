# Benchmarks du générateur

Résultats produits par `backend/test_harness.py` (seeds fixes `0..N-1`, un Trie par format).

| Fichier | Rôle |
|---------|------|
| `baseline.json` | Référence versionnée. Toute modification du moteur doit être comparée à ce fichier. |
| `latest.json` | Dernière exécution locale (sortie par défaut du harness, non destinée à être commitée). |

## Lancer

Depuis `backend/` (Python 3.11) :

```bash
python test_harness.py --seeds 20 --time-budget 20 --output benchmarks/latest.json --html report.html
```

Le budget de 20 s correspond au budget par défaut de l'API (`GENERATION_TIME_BUDGET_S`) : le taux de succès mesuré est celui qu'on obtient réellement depuis l'interface.

`--restart-unit N` fixe l'unité des redémarrages en appels récursifs (`0` : un seul essai, comme avant la Phase 3). Sans l'option, le réglage du générateur s'applique (`DEFAULT_RESTART_UNIT_CALLS`). Le nombre d'essais de chaque seed est dans le champ `attempts`.

## Lire les résultats

Pour chaque layout : taux de succès dans le budget, temps p50 / p95 / max, nombre de timeouts, backtracks moyens, puis le détail de chaque seed.

- Les **temps dépendent de la machine** : ne comparer que des exécutions faites sur la même machine (voir `environment` dans le JSON).
- Le **taux de succès sur beaucoup de seeds** est l'indicateur principal. Pour un layout difficile, le résultat d'une seed isolée ne veut presque rien dire (voir ci-dessous) : utiliser au moins 20 seeds.
- L'exécution est **reproductible** : même code + même dictionnaire + même seed ⇒ même grille.

## Baseline actuelle (septembre 2026, redémarrages de 300 appels et index des candidats)

Machine : Docker (Python 3.11, 8 CPU, 4 Go), dictionnaire `dela_clean.csv` complet, 20 seeds, budget 20 s, exécution seule.

| Layout | Succès | p50 | p95 |
|--------|--------|-----|-----|
| 6x7-001 | 20/20 | 0,12 s | 0,29 s |
| 11x6-001 | **20/20** | 3,1 s | 15,6 s |

Historique :

| Étape | 6x7-001 | 11x6-001 |
|-------|---------|----------|
| Première baseline | 20/20, p95 5,4 s | 3/20 |
| Redémarrages (#19) | 20/20, p95 1,1 s | 11/20, p50 17,4 s |
| Index des candidats (#20) | 20/20, p95 0,29 s | 20/20, p50 3,1 s |

## Index des candidats (#20, septembre 2026)

Le profil d'une génération 11×6 montrait 94 % du temps dans `get_candidates` : parcours du Trie par motif (5,9 millions de nœuds visités pour 1 295 recherches), puis filtrage des mots disponibles, avec un cache vidé à chaque placement. L'index par (position, lettre) en ensembles de bits (`engine/pattern_index.py`) calcule les mêmes candidats, **dans le même ordre**, par ET binaire ; le solveur ne fait que les compter pour choisir le slot et pour le forward checking.

- **Mêmes grilles** : chaque seed réussie de la baseline précédente suit exactement la même trajectoire (mêmes appels récursifs, mêmes essais), 2 à 6 fois plus vite (ex. 11x6-001 seed 0 : 8,0 s → 3,1 s).
- **Plus de réussites** : les essais plus rapides tiennent dans le budget ; le 11×6 passe de 11/20 à 20/20.
- Coût : construction de l'index au premier usage d'un lexique (1,4 s sur le DELA complet), puis 0,3 s par génération pour marquer les mots disponibles.
- Prochains points chauds du profil : `_get_slot_pattern`, `words_in` et les appels `logging.debug` formatés même quand ils ne s'affichent pas.

## Ce qu'on a appris en établissant la première baseline

`amelioration-generate.md` indiquait « 11×6 : 100 % de succès en ~9 s ». Ce chiffre venait de **4 seeds (0 à 3) chanceuses**, pas d'une propriété du moteur :

- Le moteur a été vérifié à l'identique : le nouveau code, lancé avec l'ancien harness et les mêmes conditions, reproduit exactement les temps de l'ancien code (9,2 s / 9,5 s / 28,4 s).
- La réussite dépend avant tout de la **trajectoire aléatoire** de la seed (mélange du top 20 % des candidats). Décaler le flux aléatoire d'un seul tirage (l'ancien code tirait le layout au sort avant de résoudre) suffit à transformer 3 succès en 3 timeouts sur les mêmes seeds. L'ordre des mots dans le Trie a un effet secondaire.
- Sur 20 seeds, le taux réel est de **15 % en 20 s**. Les grilles réussies le sont vite (3,6 à 15,7 s) : le solveur trouve rapidement ou s'enlise.

Conséquence pour la [roadmap](../../docs/ROADMAP.md) (Phase 3) : ce profil « vite ou jamais » est exactement le cas où les **redémarrages aléatoires** (plusieurs trajectoires courtes dans le budget plutôt qu'une longue) améliorent fortement le taux de succès. À combiner avec le lexique curé (moins de mots rares) et un index des candidats par (position, lettre).

## Redémarrages : choix de l'unité (#19, septembre 2026)

L'essai n°i s'arrête après `unité × luby(i)` appels récursifs. Le seuil est compté en appels et non en secondes : même seed ⇒ même grille, quelle que soit la machine. Mesures sur 20 seeds, budget 20 s, dictionnaire complet (deux exécutions à la fois, sur 8 CPU) :

| Unité (appels) | 6x7-001 : succès, p95 | 11x6-001 : succès | Essais par seed sur 11x6 |
|----------------|-----------------------|-------------------|--------------------------|
| sans redémarrage | 20/20, 5,4 s | 3/20 | 1 |
| 1 000 | 20/20, 2,1 s | 3/20 | 3 à 8 |
| **300 (retenu)** | **20/20, 1,3 s** | **7/20** | 2 à 15 |
| 100 | 20/20, 2,5 s | 2/20 | 6 à 26 |
| 50 | 20/20, 2,8 s | 2/20 | 4 à 31 |

⚠️ Ces mesures ne portent que sur **deux layouts**. Rien ne dit que 300 appels conviendra à un 15×8 ou à un 7×4 : la valeur sera réexaminée quand le catalogue s'étoffera (#57), en comparant plusieurs unités avec `--restart-unit` sur les nouveaux formats.

- Trop long (1 000) : trop peu d'essais tiennent dans le budget.
- Trop court (100, 50) : les essais s'arrêtent avant d'aboutir ; le 6×7, qui réussit souvent en quelques centaines d'appels, ralentit.
- Lancé seul (baseline ci-dessus), le réglage de 300 appels atteint 11/20 sur le 11×6 : le budget est en secondes, deux exécutions simultanées font donc moins d'essais. Ne comparer que des exécutions faites dans les mêmes conditions.
- Sur le 11×6, un appel récursif coûte environ 40 ms : 94 % du temps passe dans la recherche de candidats par le Trie (profil `cProfile`). C'est la limite suivante (#20) : plus d'appels par seconde, donc plus d'essais dans le budget.
