# CLAUDE.md — consignes pour les sessions IA

Terminator : outil personnel de création de mots fléchés (recherche par motif + génération automatique de grilles). Monorepo `backend/` (Flask, Python 3.11) + `frontend/` (Next.js 15, pnpm). Lire d'abord [README.md](README.md), [docs/ROADMAP.md](docs/ROADMAP.md) et [CONTRIBUTING.md](CONTRIBUTING.md).

## Commandes

- Tests backend : `make test-backend` (Python 3.11 dans Docker : la machine hôte n'a que Python 3.9)
- Lint + types frontend : `make lint-frontend`
- Benchmark moteur : `make bench` (à comparer à `backend/benchmarks/baseline.json`) ; profil de charge (RAM, CPU, concurrence) : `make bench-load`
- Outils / lexique : `make test-tools`, `make lexicon-build`, `make lexicon-stats`, `make lexicon-export` ([docs/LEXICON.md](docs/LEXICON.md)) ; ne jamais réécrire `data/lexicon/decisions.csv` (ajout seul)
- Dev : `make dev-api` (API :5001 + Postgres) et `make dev-front` (:3000)

## Règles

- **Pas de déploiement en ligne** pour l'instant ([ADR 0004](docs/adr/0004-pas-de-deploiement-en-ligne.md)) ; la cible est choisie ([ADR 0013](docs/adr/0013-cible-hebergement-production.md) : VPS derrière Cloudflare). Render et Vercel sont supprimés : ne plus les proposer.
- **Moteur** (`backend/engine/`) : pur (pas de Flask ni de BDD), aléatoire seedé par génération, budget temps. Toute modification ⇒ benchmark sur 20 seeds.
- **API** : `parse_body(Schema)` pour tout corps JSON, `get_owned_dictionary()` pour tout accès à un dictionnaire, erreurs `{"error": "..."}` en français, test d'autorisation pour toute nouvelle ressource.
- **Frontend** : appels via `apiFetch`, textes en français, raccourcis compatibles AZERTY (flèches, Espace, Entrée, Retour arrière).
- **Ne jamais lancer `next build` dans `frontend/`** pendant que le serveur de dev tourne (il écrase `.next`) : construire dans une copie.
- **Ne pas utiliser `npx`** pour les outils du projet : utiliser `frontend/node_modules/.bin/…` ou `pnpm exec`.
- Git : branche par sujet, Conventional Commits, PR vers `main`, CI verte, merge commit.
- Docs en français ; une ADR pour chaque décision structurante ; mettre à jour le CHANGELOG.
