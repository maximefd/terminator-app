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
- Format de layout v1 (Phase 2, #12, ADR 0006) :
  - `x` = case définition, `-` = case lettre ; l'ancien format `#` / `.` reste lu ;
  - caractère inconnu, lignes de longueurs différentes ou taille différente du dossier : erreur qui indique la ligne et la colonne ;
  - `convert_layouts.py` convertit les anciens fichiers ;
  - identifiant déduit du chemin (`11x6-001`).
- Validateur de layouts (Phase 2, #13) :
  - `make layouts-check` et étape de CI ;
  - erreurs : case lettre isolée, taille ou nom de fichier non conformes, grille sans mot ;
  - avertissements : grilles en double, proportion inhabituelle de cases définitions ;
  - statistiques : nombre de mots et mots par longueur.
- `GET /api/layouts` : catalogue des layouts valides avec leurs grilles et statistiques.
- Index des candidats par (position, lettre) en ensembles de bits (Phase 3, #20) : remplace le parcours du Trie et le cache par motif du solveur ; mêmes candidats dans le même ordre, donc mêmes grilles pour un même seed, calculées 2 à 6 fois plus vite. Benchmark : 11x6-001 de 11/20 à 20/20 (p50 3,1 s), 6x7-001 p95 0,29 s.
- Redémarrages du solveur (Phase 3, #19) : essais successifs de `300 × luby(i)` appels récursifs dans le budget temps, trajectoires dérivées du seed (même seed ⇒ même grille) ; benchmark `--restart-unit` et nombre d'essais par seed ([mesures](backend/benchmarks/README.md)).
- Pools de mots dans le moteur (Phase 3, #17, [ADR 0007](docs/adr/0007-contrat-de-generation.md)) : mots obligatoires, souhaités (dictionnaire personnel actif) et communs (lexique curé) ; chaque mot placé indique sa provenance (`source`) et la grille renvoie la part de mots de l'auteur (`wish_ratio`).
- Mots obligatoires et souhaités (Phase 3, #18, [ADR 0007](docs/adr/0007-contrat-de-generation.md)) : champs `must_words` et `wish_words` de `POST /api/grids/generate` ; les mots imposés sont placés avant tous les autres, en commençant par le plus contraint, avec retour arrière. Un mot qui n'entre pas dans le layout est refusé **avant toute résolution** (`reason: "must_words"`, problème mot par mot et layouts de repli) ; un mot que la recherche n'a pas su placer donne `reason: "must_words_unplaced"` et la liste des mots restants.
- Éditeur de layouts dans le curateur (Phase 2, #14, onglet « Layouts ») :
  - dessin au toucher ou au clavier (`x`, `-`, flèches, Entrée, Retour arrière) ;
  - remise à blanc de toute la grille, ou de son seul intérieur (première ligne et première colonne conservées) ;
  - vérification en direct par le serveur, cases fautives en rouge, statistiques ;
  - enregistrement dans `backend/layouts/` sous le prochain numéro, sans écrasement ni doublon ;
  - catalogue avec aperçus, copie d'un layout existant, brouillon conservé sur l'appareil ;
  - le curateur démarre sans la base du lexique (éditeur seul).
- Captures d'écran dans le README (#8) : recherche par motif et grille générée, régénérables par `frontend/tests/screenshots.spec.ts` (Playwright utilise le Chrome installé).
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
- Règles automatiques, filtre positif et révision des décisions ([ADR 0008](docs/adr/0008-regles-automatiques-et-revision.md)) :
  - `python -m tools.lexicon autorules` : aperçu (sans rien écrire), activation et désactivation des règles décrivant les classes de mots jamais gardées au tri — `formes-composees` (119 triées, 119 supprimées), `inconnues-sans-definition` (94,6 % de suppressions) et `flexions-rares-longues` (sur demande) ; activées dans `data/lexicon/auto_rules.json`, jamais écrites dans `decisions.csv`, et toujours battues par une décision « garder » ;
  - `python -m tools.lexicon export --filtre moyen` : ne garde que les mots connus de Lexique, définis pour eux-mêmes ou formés sur un lemme de fréquence zipf ≥ 2 (191 709 mots de 11 lettres ou moins, contre 393 720) ;
  - `python -m tools.lexicon revision` : décisions douteuses (famille jugée à l'opposé, mot courant supprimé, rafale de décisions dans la même seconde) ; confirmer ou corriger écrit un lot marqué `revision`, et le mot ne revient plus ;
  - `stats` compte à part les mots traités par les règles (`handled_by_rules`).
- Curateur : deux nouveaux onglets ([ADR 0008](docs/adr/0008-regles-automatiques-et-revision.md)) :
  - **Familles** (`/familles`) : une carte par lemme (définition, fréquence, toutes ses formes), une décision pour toute la famille (`←` supprimer, `→` garder, `↑` passer, `↓` annuler) ; les formes déjà décidées et les mots très courants ne sont jamais touchés ; une famille doit compter au moins trois formes à trier, et toucher une forme montre sa définition pour la trier seule (les familles qui mélangent deux mots, comme l'adverbe « hier » et le verbe « hier ») ;
  - **Révision** (`/revision`) : les décisions douteuses reproposées une par une, avec les touches du tri (`←` supprimer, `→` garder, `↑` passer, `↓` annuler) ; redonner la même réponse suffit à sortir le mot de la liste ;
  - les mots visés par une règle automatique disparaissent de la file de tri et du reste à trier.

### Modifié
- Règle `formes-composees` : toutes les graphies d'un mot sont examinées, plus seulement la première. 774 mots comme `cava` (« ça va »), `aras` (« à ras ») ou `etal` (« et al. ») passaient au travers et pouvaient former des familles.
- Anciens documents de cadrage (`READMESDD.md`, `amelioration-generate.md`) archivés dans `docs/archive/`.
- Layouts déplacés de `backend/templates/<L>x<H>/template_01.txt` vers `backend/layouts/<L>x<H>/001.txt` ; le champ `layout` de la grille générée et les clés du benchmark deviennent `6x7-001`. Variable de configuration `TEMPLATES_DIR` renommée `LAYOUTS_DIR`.
- Modèle d'issue « Nouveau layout » : grille au format v1, sans champ source.
- Dépendances Python figées (`backend/requirements.txt`, `tools/curator/requirements.txt`), suivies par Dependabot et auditées par `pip-audit` en CI (#6).
- Lint Python avec ruff (`make lint-backend`, `ruff.toml`, règles tolérantes pour commencer) et couverture des tests en CI : 80 % minimum sur le moteur, 70 % sur les outils (#5).

### Corrigé
- Les mots des dictionnaires personnels n'étaient **jamais placés** : l'index des candidats ne contenait que les mots du lexique, et les mots personnels transmis au générateur étaient silencieusement ignorés, à l'indexation comme aux croisements. Ils forment désormais le pool « souhaité » : ajoutés à l'index de leur longueur, essayés avant le lexique commun et acceptés comme mots croisés (#17).
- Le solveur exigeait qu'un mot perpendiculaire **en cours d'écriture** existe déjà au dictionnaire : deux rangées voisines traversant un emplacement de 5 cases y laissent « AB », que le solveur refusait faute d'être un mot. Sur les grilles de plus d'une trentaine de mots, il rejetait ainsi des placements valides en continu et n'aboutissait jamais. Seuls les mots **terminés** sont désormais vérifiés (#57). Les **16 layouts du catalogue réussissent maintenant 20/20**, du 6×7 (0,05 s) au 13×16 de 61 mots (1,9 s) ; les formats de plus de 30 mots n'aboutissaient jamais auparavant.

### Sécurité
- Frontend : versions corrigées de postcss, nanoid et sharp imposées par des overrides pnpm (9 vulnérabilités transitives de next 15.5.25, #7).

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
