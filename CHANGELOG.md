# Changelog

Toutes les évolutions notables du projet. Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- Pipeline du lexique (`tools/lexicon/`, Phase 1a) :
  - téléchargement de Lexique 3.83 et du Wiktionnaire avec empreintes consignées ;
  - base locale (fréquence, lemme, définition, suggestion) ;
  - décisions de curation versionnées avec annulation par lot ;
  - export du lexique curé ; statistiques d'avancement ;
  - ADR 0005.
- Mini-app de curation du lexique (`tools/curator/`, `make curator`, Phase 1b) :
  - une carte par mot : définition, fréquence, lemme, suggestion ;
  - une touche par décision (← supprimer, → garder, ↓ annuler, ↑ passer, Maj + ← toute la famille) ;
  - glisser sur téléphone ;
  - accès par code PIN ; statistiques du jour et série.
- Curateur :
  - motivation : objectif du jour, série, niveaux, 14 badges, combos, fenêtre de progression avec les 7 derniers jours ;
  - `make curator-bg`, `curator-stop` et `curator-logs` pour le lancer en arrière-plan ;
  - accès hors du Wi-Fi documenté avec Tailscale.
- Lexique curé dans Terminator (Phase 1c) :
  - l'API charge le lexique curé s'il existe et le recharge à chaud quand il change ;
  - le curateur l'exporte tous les 500 mots triés et propose de tester les grilles ;
  - `GET /api/status` indique le lexique chargé.
- Curateur : bulle « Chercher ce mot » avec les résultats Google (Serper) ou, sans clé, Wikipédia et Wiktionnaire.
- Documentation de relecture :
  - README réécrit ;
  - `docs/ARCHITECTURE.md`, `docs/ENGINE.md`, `docs/LAYOUTS.md`, `docs/LEXICON.md` ;
  - ADR 0001 à 0004 ;
  - PRD mis à jour ;
  - `CONTRIBUTING.md`, `CLAUDE.md`.
- `Makefile` (setup, dev, tests, benchmark).
- Modèles de PR et d'issues GitHub.
- Dependabot.
- CI frontend : ESLint et vérification TypeScript.

### Modifié
- Anciens documents de cadrage (`READMESDD.md`, `amelioration-generate.md`) archivés dans `docs/archive/`.
- Dépendances Python figées (`backend/requirements.txt`, `tools/curator/requirements.txt`), suivies par Dependabot et auditées par `pip-audit` en CI (#6).
- Lint Python avec ruff (`make lint-backend`, `ruff.toml`, règles tolérantes pour commencer) et couverture des tests en CI : 80 % minimum sur le moteur, 70 % sur les outils (#5).

## [0.1.0] — 2026-09-14

Première version stabilisée (Phase 0a et 0b de la [roadmap](docs/ROADMAP.md)).

### Ajouté
- Roadmap du projet (`docs/ROADMAP.md`).
- `GET /api/grids/formats` ; le frontend ne propose que les formats disposant d'un layout.
- Budget temps du solveur : erreurs `422` explicites (`timeout`, `no_solution`).
- Benchmark reproductible du générateur et baseline (`backend/benchmarks/`).
- Tests : moteur, endpoints de grille, configuration, validation, autorisation, sécurité (123 tests).
- Validation de toutes les entrées de l'API (pydantic), messages d'erreur en français.
- Rate limiting (connexion, inscription, refresh, recherche, génération).
- Plafonds de taille : corps de requête, nombre de dictionnaires et de mots.
- Endpoint `POST /api/auth/refresh` et renouvellement automatique de session côté frontend.
- En-têtes de sécurité (API et frontend), CORS strict.
- `docs/SECURITY.md`.
- `.env.example` ; identifiants docker compose sortis du code.

### Corrigé
- La génération de grille plantait à chaque appel (Trie pré-construit non transmis).
- La génération échouait presque toujours : les mots étaient tirés d'un échantillon de 30 000 mots (~4 % du dictionnaire).
- Un même seed ne donnait pas la même grille (état aléatoire global partagé).
- Les messages d'erreur de l'API n'étaient jamais affichés dans l'interface.
- La suppression de compte laissait les mots personnels en base.
- La connexion d'un ancien compte anonymisé provoquait une erreur 500.
- Le secret JWT était lu depuis la mauvaise variable d'environnement.

### Sécurité
- Next.js 15.5.4 → 15.5.25 (advisories critiques d'exécution de code à distance).
- Débogueur Werkzeug activé uniquement avec `FLASK_DEBUG=1`.
- Refus de démarrer en production avec des secrets par défaut, sans base de données ou avec CORS `*`.
- Jokers SQL échappés dans la recherche de mots personnels.

[Non publié]: https://github.com/maximefd/terminator-app/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/maximefd/terminator-app/releases/tag/v0.1.0
