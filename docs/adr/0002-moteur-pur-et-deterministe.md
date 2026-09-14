# 0002 — Moteur de génération pur, déterministe et borné dans le temps

- Statut : acceptée
- Date : 2026-09-14

## Contexte

- La génération est exécutée de façon synchrone dans une requête HTTP. Sur les layouts difficiles, le solveur pouvait tourner indéfiniment.
- Le générateur utilisait l'état aléatoire global de Python : deux générations dans le même processus se perturbaient, et un même seed ne redonnait pas la même grille. Le benchmark n'était donc pas reproductible (voir `backend/benchmarks/README.md`).
- À terme, la mise en file d'attente côté serveur risque de ne pas tenir la charge. Faire tourner le moteur dans le navigateur (Web Worker, WASM) est une option sérieuse (Phase 7).

## Décision

1. `backend/engine/` reste **pur** : aucun import Flask ni base de données, pas d'I/O dans le solveur. Layouts et mots lui sont fournis.
2. Chaque génération utilise son **propre générateur aléatoire seedé** (`random.Random(seed)`) : même code + même dictionnaire + même seed ⇒ même grille.
3. Le solveur accepte un **budget** (temps et/ou nombre d'appels) et signale son dépassement (`budget_exceeded`) au lieu de bloquer.
4. Toute modification du moteur est mesurée avec le **benchmark reproductible** et comparée à la baseline versionnée.

## Conséquences

- Les résultats du benchmark sont comparables d'une version à l'autre (sur une même machine).
- L'API renvoie une erreur `422` explicite (`timeout` / `no_solution`) au lieu d'une requête qui ne répond pas.
- Un portage futur (TypeScript, Rust→WASM) pourra être validé en comparant ses grilles à celles du moteur Python pour les mêmes seeds.
- Les nouvelles fonctionnalités du moteur (mots imposés, redémarrages) doivent respecter ces trois propriétés.
