# CLAUDE.md — consignes pour les sessions IA

Terminator : outil personnel de création de mots fléchés (recherche par motif + génération automatique de grilles). Monorepo `backend/` (Flask, Python 3.11) + `frontend/` (Next.js 15, pnpm). Lire d'abord [README.md](README.md), [docs/ROADMAP.md](docs/ROADMAP.md) et [CONTRIBUTING.md](CONTRIBUTING.md).

## Commandes

- Tests backend : `make test-backend` (Python 3.11 dans Docker : la machine hôte n'a que Python 3.9)
- Lint + types frontend : `make lint-frontend`
- Benchmark moteur : `make bench` (à comparer à `backend/benchmarks/baseline.json`) ; profil de charge (RAM, CPU, concurrence) : `make bench-load`
- Outils / lexique : `make test-tools`, `make lexicon-build`, `make lexicon-stats`, `make lexicon-export` ([docs/LEXICON.md](docs/LEXICON.md)) ; ne jamais réécrire `data/lexicon/decisions.csv` (ajout seul)
- Dev : `make dev-api` (API :5001 + Postgres) et `make dev-front` (:3000)
- Déploiement ([ADR 0019](docs/adr/0019-deploiement.md), [docs/PRODUCTION.md](docs/PRODUCTION.md)) : `make deploy` (API puis site), `make rollback` ; migrations additives seulement
- Mesure d'usage : `make stats` (`flask stats` dans le conteneur de l'API, sans charger le lexique)
- Base : `make db-backup` (dans `backups/`, ignoré par git) et `make db-restore-check FILE=…` (restaure dans une base jetable, jamais dans la base en service)

## Règles

- **Le site est en ligne** depuis le 25/09/2026 ([ADR 0013](docs/adr/0013-cible-hebergement-production.md) : VPS derrière Cloudflare). On déploie un commit de `main` par `make deploy` ([ADR 0019](docs/adr/0019-deploiement.md)), jamais à la main sur le serveur ; le lexique par `make deploy-lexicon` ; runbook : [docs/PRODUCTION.md](docs/PRODUCTION.md). Render et Vercel sont supprimés : ne plus les proposer.
- **Nom et langues** ([ADR 0017](docs/adr/0017-un-site-par-langue.md)) :
  - Terminator est le nom du moteur ; le nom public du site vient de sa configuration, jamais en dur ;
  - toute nouvelle donnée liée au lexique ou à l'usage porte sa langue (`lang`) ;
  - toute nouvelle erreur de l'API porte un code `reason` stable.
- **Mesure** ([ADR 0016](docs/adr/0016-mesure-d-usage-sans-cookie.md)) :
  - côté serveur, sans cookie ni script tiers ;
  - jamais d'adresse IP en base ;
  - tout nouveau champ mesuré est déclaré dans la page confidentialité.
- **Moteur** (`backend/engine/`) : pur (pas de Flask ni de BDD), aléatoire seedé par génération, budget temps. Toute modification ⇒ benchmark sur 20 seeds.
- **API** : `parse_body(Schema)` pour tout corps JSON, `get_owned_dictionary()` pour tout accès à un dictionnaire, erreurs `{"error": "..."}` en français, test d'autorisation pour toute nouvelle ressource.
- **Frontend** : appels via `apiFetch`, textes en français, raccourcis compatibles AZERTY (flèches, Espace, Entrée, Retour arrière).
- **Ne jamais lancer `next build` dans `frontend/`** pendant que le serveur de dev tourne (il écrase `.next`) : construire dans une copie. Le build est un **export statique** (`out/`, avec `out/_headers`) : pas de route dynamique ni de code serveur Next (identifiants en paramètre, `?id=`).
- **Ne pas utiliser `npx`** pour les outils du projet : utiliser `frontend/node_modules/.bin/…` ou `pnpm exec`.
- Git : branche par sujet, Conventional Commits, PR vers `main`, CI verte, merge commit.
- Docs en français ; une ADR pour chaque décision structurante ; mettre à jour le CHANGELOG.
