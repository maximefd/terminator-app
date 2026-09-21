# 🤝 Contribuer à Terminator

Merci de votre intérêt ! Ce guide décrit comment travailler sur le projet : installation, tests, conventions et processus de PR.

## 1. Installer l'environnement

**Prérequis** : Git, Docker Desktop, Node.js 22, pnpm (`brew install pnpm`), `make`.

```bash
git clone https://github.com/maximefd/terminator-app.git
cd terminator-app
make setup        # crée .env depuis .env.example et installe le frontend
make dev-api      # API (http://localhost:5001) + PostgreSQL
make dev-front    # dans un autre terminal : frontend (http://localhost:3000)
```

Le premier démarrage de l'API charge tout le dictionnaire en mémoire : comptez une à deux minutes avant que `/api/status` réponde.

> Le backend requiert **Python 3.11**. Si votre machine a une version plus ancienne, les commandes `make` lancent Python dans Docker.

## 2. Vérifier son travail

| Commande | Ce qu'elle fait |
|----------|-----------------|
| `make test` | Tous les contrôles rapides (backend + frontend) |
| `make test-backend` | Tests pytest (Python 3.11 dans Docker) |
| `make test-tools` | Tests des outils (pipeline du lexique) |
| `make lint-backend` | Lint Python du backend et des outils (ruff, règles dans `ruff.toml`) |
| `make lint-frontend` | ESLint + vérification TypeScript |
| `make bench` | Benchmark du générateur (quelques minutes) |
| `make lexicon-build`, `lexicon-stats`, `lexicon-export` | Pipeline du lexique (voir [LEXICON.md](docs/LEXICON.md)) |
| `make curator` | Mini-app de curation du lexique (PIN dans `.env`) |
| `make test-e2e` | Parcours end-to-end et contrôle d'accessibilité axe (API et frontend démarrés) |

Les parcours end-to-end créent un compte jetable par exécution, et `RATELIMIT_REGISTER` vaut « 5 par heure » :
en enchaîner plus de cinq fait échouer l'inscription — ce n'est pas le test qui casse, c'est le quota. Le
compteur vit en mémoire, `docker compose restart api` le remet à zéro ; la CI, elle, desserre le quota par
variable d'environnement.

Le contrôle d'accessibilité (`tests/accessibility.spec.ts`) passe **axe** sur chaque écran (WCAG A et AA).
Il ne juge que ce qui se vérifie par le code — contraste, intitulés, rôles, ordre des titres. Un écran qui
y passe peut rester incompréhensible : c'est le rôle de la [revue UX](docs/AUDIT-UX.md).

Captures d'écran du README (API et frontend démarrés) : `cd frontend && pnpm exec playwright test tests/screenshots.spec.ts`. Playwright utilise le **Google Chrome installé** sur la machine (`channel: 'chrome'` dans `playwright.config.ts`) : inutile de lancer `playwright install chromium`, dont le téléchargement se fige sur la machine de l'auteur.

**Règle du moteur** : toute modification de `backend/engine/`, `grid_generator.py` ou `trie_engine.py` doit être accompagnée d'un benchmark comparé à `backend/benchmarks/baseline.json`. Voir [ENGINE.md](docs/ENGINE.md).

## 3. Processus Git

1. Partir de `main` à jour et créer une branche :
   - `feat/…` nouvelle fonctionnalité
   - `fix/…` correction
   - `docs/…` documentation
   - `test/…` tests
   - `chore/…` outillage, dépendances
2. Commits au format [Conventional Commits](https://www.conventionalcommits.org/fr/) :
   ```text
   fix(backend): generate from the whole dictionary instead of a 30k sample
   ```
   Types : `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`. Portées courantes : `backend`, `frontend`, `engine`, `config`, `bench`.
3. Ouvrir une **PR vers `main`** en remplissant le modèle (quoi, pourquoi, comment tester).
4. La **CI doit être verte** avant la fusion.
5. Fusion par **merge commit**, pour garder l'historique détaillé et permettre les PR empilées.

Chaque PR est rattachée à un milestone (une phase de la [roadmap](docs/ROADMAP.md)) quand c'est pertinent.

## 4. Conventions de code

- **Langue** :
  - interface, messages d'erreur de l'API et documentation en **français** ;
  - identifiants de code : suivre le style du fichier modifié ;
  - messages de commit en anglais.
- **Imiter le code voisin** : nommage, densité des commentaires, idiomes.
- **Backend** :
  - chaque endpoint qui lit un corps JSON passe par `parse_body(Schema)` (`backend/schemas.py`) ;
  - chaque accès à un dictionnaire passe par `get_owned_dictionary()`, chaque accès à une grille conservée par `get_owned_grid()` ;
  - les erreurs renvoient `{"error": "message en français"}` ;
  - **toute modification d'un modèle demande une migration** ([ADR 0010](docs/adr/0010-migrations-de-schema.md)) :
    `docker compose exec api sh -c "cd /app && FLASK_APP=run.py flask db migrate -m 'ce qui change'"`, puis
    **relire la révision produite** — l'auto-détection voit un renommage comme une colonne supprimée et une
    autre créée, ce qui perdrait les données. Les tests, eux, tournent sur `db.create_all()` : un modèle ajouté
    sans migration y passerait inaperçu.
- **Moteur** : pas d'import Flask ni base de données dans `backend/engine/`, aléatoire uniquement via le générateur seedé, budget temps respecté ([ADR 0002](docs/adr/0002-moteur-pur-et-deterministe.md)).
- **Frontend** :
  - appels API uniquement via `apiFetch` (`src/lib/api-client.ts`) ;
  - composants shadcn/ui dans `src/components/ui/` ;
  - les écrans répondent à « qu'est-ce que c'est ? que puis-je faire ? que se passe-t-il ensuite ? ».
- **Raccourcis clavier** : compatibles AZERTY (flèches, Espace, Entrée, Retour arrière). Jamais de touche nécessitant Maj ou AltGr.
- **Tests** : toute correction de bug vient avec un test qui aurait détecté le bug.

## 5. Sécurité

- Aucun secret dans le code ni dans les commits : tout passe par `.env` (jamais versionné) et [`.env.example`](.env.example).
- Toute nouvelle entrée utilisateur est validée côté serveur.
- Toute nouvelle ressource est limitée à son propriétaire, avec un test d'autorisation.
- Vulnérabilité découverte : ne pas ouvrir d'issue publique, voir [SECURITY.md](docs/SECURITY.md).

## 6. Documentation

- Un choix structurant ⇒ une ADR dans [`docs/adr/`](docs/adr/).
- Mettre à jour la doc concernée ([ARCHITECTURE](docs/ARCHITECTURE.md), [ENGINE](docs/ENGINE.md), [LAYOUTS](docs/LAYOUTS.md), [LEXICON](docs/LEXICON.md)) dans la même PR que le code.
- Ajouter une ligne au [CHANGELOG](CHANGELOG.md) dans la section « Non publié ».
