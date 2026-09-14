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

## Lire les résultats

Pour chaque layout : taux de succès dans le budget, temps p50 / p95 / max, nombre de timeouts, backtracks moyens, puis le détail de chaque seed.

- Les **temps dépendent de la machine** : ne comparer que des exécutions faites sur la même machine (voir `environment` dans le JSON).
- Le **taux de succès sur beaucoup de seeds** est l'indicateur principal. Pour un layout difficile, le résultat d'une seed isolée ne veut presque rien dire (voir ci-dessous) : utiliser au moins 20 seeds.
- L'exécution est **reproductible** : même code + même dictionnaire + même seed ⇒ même grille.

## Baseline actuelle (septembre 2026)

Machine : Docker (Python 3.11, 8 CPU, 4 Go), dictionnaire `dela_clean.csv` complet, 20 seeds, budget 20 s.

| Layout | Succès | p50 | p95 | Backtracks moyens |
|--------|--------|-----|-----|-------------------|
| 6x7/template_01 | 20/20 | 0,28 s | 5,4 s | 964 |
| 11x6/template_01 | 3/20 | timeout | timeout | 23 627 |

## Ce qu'on a appris en établissant cette baseline

`amelioration-generate.md` indiquait « 11×6 : 100 % de succès en ~9 s ». Ce chiffre venait de **4 seeds (0 à 3) chanceuses**, pas d'une propriété du moteur :

- Le moteur a été vérifié à l'identique : le nouveau code, lancé avec l'ancien harness et les mêmes conditions, reproduit exactement les temps de l'ancien code (9,2 s / 9,5 s / 28,4 s).
- La réussite dépend avant tout de la **trajectoire aléatoire** de la seed (mélange du top 20 % des candidats). Décaler le flux aléatoire d'un seul tirage (l'ancien code tirait le layout au sort avant de résoudre) suffit à transformer 3 succès en 3 timeouts sur les mêmes seeds. L'ordre des mots dans le Trie a un effet secondaire.
- Sur 20 seeds, le taux réel est de **15 % en 20 s**. Les grilles réussies le sont vite (3,6 à 15,7 s) : le solveur trouve rapidement ou s'enlise.

Conséquence pour la [roadmap](../../docs/ROADMAP.md) (Phase 3) : ce profil « vite ou jamais » est exactement le cas où les **redémarrages aléatoires** (plusieurs trajectoires courtes dans le budget plutôt qu'une longue) améliorent fortement le taux de succès. À combiner avec le lexique curé (moins de mots rares) et un index des candidats par (position, lettre).
