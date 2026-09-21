# 🗺️ Roadmap — Terminator

> Plan de complétion du projet. Document vivant : chaque phase correspond à un **Milestone GitHub**, chaque point à une ou plusieurs **issues**.
> Dernière mise à jour : septembre 2026.

## État d'avancement

| Phase | État |
|-------|------|
| 0a — Stabilisation | ✅ PR #2 (génération réparée, tests, benchmark) |
| 0b — Sécurité | ✅ PR #3 |
| 0c — Documentation et GitHub | ✅ PR #31 (restent #5 à #8 : ruff et couverture en CI, dépendances figées, vulnérabilités transitives de Next.js, captures d'écran) |
| 1a — Pipeline du lexique | ✅ PR #42 |
| 1b — Curateur (+ motivation, usage hors du Wi-Fi) | ✅ PR #43 et #44 ; tri en cours (`data/lexicon/decisions.csv`) |
| 1c — Lexique curé chargé par l'API | 🚧 en cours (#11) : export et rechargement automatiques tous les 500 mots triés |
| 2 — Catalogue de layouts | ✅ format v1 (#12, [ADR 0006](adr/0006-format-des-layouts.md)), validateur et `GET /api/layouts` (#13), éditeur dans le curateur (#14) ; reste à recopier des layouts (#15) |
| 3 — Moteur avec mots imposés | ✅ critère atteint : **les 21 layouts du catalogue réussissent 20/20**. Pools de mots (#17), mots obligatoires (#18), redémarrages (#19), index des candidats (#20), validation croisée (#57), seuil du forward checking (#61), plafond de candidats à 300, dictionnaires thématiques ; contrat accepté ([ADR 0007](adr/0007-contrat-de-generation.md), #16). Tri par fréquence mesuré et **désactivé par défaut** : il ramène les mots absents des corpus de 33 % à 17 % mais fait tomber sept layouts sous le critère ([mesures](../backend/benchmarks/README.md)) — activable par requête. **Réserve levée, et elle révèle un problème** : la baseline comporte désormais des cas avec mots obligatoires (`--must-words`). Un mot imposé fait tomber le succès à 96 %, **trois le font tomber à 40 %**, tous layouts sous le critère ([mesures](../backend/benchmarks/README.md)). Le changement de layout (#73) améliore le cas où un format compte plusieurs layouts — 6×7 de 6/20 à 11/20 — sans rien résoudre sur le fond. **Traité non par le taux mais par l'aveu** : l'écran annonce la difficulté avant de générer ([ADR 0009](adr/0009-annoncer-la-difficulte.md)), et la mesure a désigné le vrai facteur — la **longueur** des mots imposés, pas leur nombre (#73 reste ouverte). Reportés en Phase 4 : `target_wish_ratio` et `layout_id`, qui n'ont de sens qu'avec la saisie |
| 4 — UX : génération et clarté | 🚧 en cours : écran de génération (#23) — liste de mots ordonnée, obligatoires/souhaités, dictionnaires thématiques, difficulté annoncée pendant la saisie, refus expliqués, provenance colorée. Reportés faute de `layout_id` : choix du layout et rejeu d'un seed. page d'accueil (#22), audit UX (#21), sauvegarde des grilles (#24). Reste #25 |
| 5 à 7 | ⏳ voir les [milestones](https://github.com/maximefd/terminator-app/milestones) |

Décision du 14/09/2026 : **pas de déploiement en ligne** avant un serveur de production ([ADR 0004](adr/0004-pas-de-deploiement-en-ligne.md)).

## Contexte

Terminator est un outil personnel de création de **mots fléchés d'aspect professionnel français**. Cible future : créateurs expérimentés et professionnels. La mise en production n'est pas immédiate, mais les pratiques d'ingénierie doivent déjà être au niveau production.

- **Création manuelle** (recherche par motif) : ~90 % terminée.
- **Création automatique** : choisir une mise en page (layout), fournir des mots **obligatoires**, des mots **souhaités** et des **dictionnaires thématiques** (~30 % des mots de la grille), le reste provenant du dictionnaire commun. C'est le gros du travail restant.
- **Layouts** : recopiés à la main depuis de vrais livres de mots fléchés (6×7 et 11×6 pour l'instant).
- **Dictionnaire** : beaucoup trop large. `dela_clean.csv` contient 714 k mots distincts (~393 k de 11 lettres ou moins), sans définitions, avec énormément de formes fléchies rares. Cela dégrade la qualité des grilles **et** la vitesse du solveur.
- **Exigences** : UX irréprochable et auto-explicative ; sécurité (la base accepte des écritures utilisateur) ; projet relu prochainement par un pair → documentation et GitHub clairs et à jour.
- **Futur** : la mise en file d'attente des générations côté API risque de ne pas tenir la charge. Un moteur côté client est une piste → garder le moteur portable dès maintenant.

### Problèmes identifiés dans le code (septembre 2026)

- `backend/routes.py` appelle `GridGenerator` sans le `prebuilt_trie` requis → la génération depuis l'UI est cassée.
- Le frontend propose des tailles pour lesquelles aucun layout n'existe.
- Aucun timeout du solveur, aucun test du moteur.
- Le secret JWT est lu depuis la mauvaise variable d'environnement ; `logging` non importé dans `routes.py`.
- La recherche dans les mots personnels injecte la saisie brute dans un `LIKE` SQL (`%` / `_` agissent comme jokers).
- Pas de validation d'entrées par schéma, pas de rate limiting.
- Identifiants de dev en dur dans `docker-compose.yml`.
- Fichiers `__pycache__`, `.DS_Store` et `report.html` versionnés.

---

## Standards transverses (dès le premier jour)

**Ingénierie**
- **Git** : branches de fonctionnalité + PR même en solo, commits conventionnels, `main` toujours vert.
- **CI** : backend `ruff` (lint + format), `mypy` (moteur, curateur), `pytest` + couverture (≥ 70 % sur `engine/` et le pipeline lexique) ; frontend `eslint`, `tsc --noEmit`, `next build`, tests Playwright.
- **Sécurité en CI** : `pip-audit`, `pnpm audit`, CodeQL, Dependabot, gitleaks.
- **Outillage local** : pre-commit identique à la CI ; `Makefile` (`setup`, `test`, `lint`, `harness`, `lexicon-build`, `curator`) ; `.env.example`.
- **Décisions** : ADR dans `docs/adr/` pour chaque choix structurant.
- **Données** : jeux de données externes téléchargés par script (versions et checksums figés), jamais versionnés. Les *décisions* de l'auteur sont versionnées. Les artefacts générés sont reconstruits.
- **Portabilité du moteur** : `backend/engine/` reste pur — aucun import Flask/BDD, déterministe pour un seed donné, contrat JSON en entrée/sortie, aucune I/O fichier dans le solveur. Condition pour un futur moteur Web Worker / WASM (Phase 7).

**Clavier (AZERTY français)**
- Raccourcis : flèches, Espace, Entrée, Retour arrière. Jamais de touches nécessitant Maj ou AltGr.

**UX**
- Chaque écran répond à : *qu'est-ce que c'est ? que puis-je faire ici ? que se passe-t-il ensuite ?*
- Textes en français cohérent, états vides utiles, messages d'erreur qui disent quoi faire.
- Indicateur de chargement pour toute action > 300 ms.
- Responsive et accessible (WCAG AA : contraste, focus, navigation clavier).

**Sécurité**
- Chaque endpoint valide ses entrées par schéma. Chaque ressource est limitée à son propriétaire. Rien ne fait confiance au client.

---

## Phase 0 — Stabiliser, sécuriser, être prêt pour la relecture

### 0a. Stabilisation
1. Hygiène : `.gitignore` (pycache, .DS_Store, report.html, test-results, venv) et retrait de ces fichiers de l'index.
2. Réparer `/api/grids/generate` (réutiliser `current_app.dela_trie` comme Trie pré-construit) ; chemins des templates relatifs au module.
3. Budget temps/nœuds dans le solveur, avec réponse d'erreur claire.
4. Config : `JWT_SECRET_KEY` lu correctement ; refus de démarrer en production avec des secrets par défaut ou sans `DATABASE_URL` ; import de `logging` ; identifiants docker-compose dans `.env`.
5. **Tests du moteur** sur mini-dictionnaires et mini-layouts : `SlotFinder`, `DictionnaireTrie.search_pattern`, `WordRepository`, solveur sur 4×4, chargement de template, smoke test de l'API `/generate`.
6. **Benchmark reproductible** : `test_harness.py` avec seeds fixes par layout, sortie JSON (taux de succès, temps p50/p95, backtracks) et baseline versionnée.

### 0b. Sécurité de base
1. **Validation des entrées** par schéma sur chaque endpoint : email en minuscules, longueur minimale du mot de passe, noms de dictionnaire (1–100 caractères sûrs), mots (lettres, accents, tiret, apostrophe, 2–30 caractères), définitions ≤ 255, masques (lettres et `?`, ≤ 30), tailles de grille et de listes plafonnées. Erreurs 400 explicites.
2. **Corriger l'injection `LIKE`** : échapper `%`, `_` et `\` avant de convertir `?` en `_`.
3. **Tests d'autorisation** : l'utilisateur B reçoit 404 sur tous les dictionnaires et mots de l'utilisateur A.
4. **Limites anti-abus** : Flask-Limiter sur login/register, recherche, génération ; plafonds de dictionnaires et de mots ; plafond de résultats *pendant* le parcours du Trie.
5. **Erreurs et en-têtes** : gestionnaire d'erreurs global sans stack trace ; debug désactivé hors dev ; en-têtes CSP, HSTS, X-Content-Type-Options, frame-ancestors ; CORS strict.
6. **Authentification** : endpoint de refresh token ; le frontend rafraîchit puis déconnecte sur 401 ; suppression réelle des données dans `delete_self`.
7. `docs/SECURITY.md` : modèle de menace léger, procédure de signalement, checklist OWASP ASVS allégée.

### 0c. Documentation et GitHub
- **README** réécrit : ce qu'est Terminator et pour qui, captures d'écran, fonctionnalités et état, démarrage en 5 minutes, carte du dépôt, badges CI.
- **`docs/`** : `ARCHITECTURE.md` (diagramme mermaid), `ENGINE.md` (slots, MRV, forward checking, nogoods, benchmark), `LEXICON.md`, `LAYOUTS.md`, `SECURITY.md`, `ROADMAP.md`, `adr/`. Mise à jour du `PRD.md` ; `READMESDD.md` et `amelioration-generate.md` fusionnés ou archivés.
- **`CONTRIBUTING.md`** et **`CLAUDE.md`** : workflow, tests, conventions.
- **GitHub** : un Milestone par phase, issues issues de ce plan, Project board, templates de PR et d'issues (bug, fonctionnalité, soumission de layout), labels, description et topics, protection de `main`, CHANGELOG, tag `v0.1.0`.

**Terminé quand** : la génération fonctionne depuis l'UI ; CI verte sur tous les contrôles ; tests d'autorisation et de validation au vert ; un nouveau venu comprend et lance le projet en moins de 15 minutes.

---

## Phase 1 — Curation du lexique

### 1a. Pipeline de données — `tools/lexicon/`
- **Sources** : DELA brut, **Lexique 3.83** (fréquence, lemme, catégorie grammaticale), extrait du **Wiktionnaire** (kaikki.org / wiktextract) pour les définitions, `wordfreq` en secours.
- **Build** → `lexicon.sqlite` local (reconstructible, non versionné) : forme normalisée, formes affichées, longueur, fréquence (zipf), lemme, catégorie, définition, suggestion (garder / supprimer).
- **Unité de décision** = la forme normalisée (celle utilisée dans les grilles), avec toutes ses formes affichées.
- **Source de vérité** = `data/lexicon/decisions.csv` (`mot;decision;date`), versionné, en ajout seul avec annulation. Un mot supprimé le reste.
- **Conservation automatique** au-dessus d'un seuil de fréquence choisi.
- `make lexicon-build` produit le dictionnaire curé utilisé par le backend. Tests unitaires.

### 1b. Mini-app de curation — `tools/curator/` (séparée du produit)
- Petit backend Flask + **page mobile-first** installable (PWA), lancée sur l'ordinateur, accessible depuis le téléphone via le Wi-Fi.
- **Sécurité** : écoute sur le réseau local uniquement, PIN/token dans `.env`, écriture limitée à `decisions.csv` et au dossier des layouts, validation des chemins côté serveur.
- **Carte de tri** : mot, formes, définition, barre de fréquence, catégorie/lemme, badge de suggestion.
- **Touches (AZERTY)** : `←` supprimer, `→` garder, `↓` / `Retour arrière` annuler, `↑` passer, `Maj+←` supprimer le mot et toutes ses formes. Sur téléphone : glisser gauche/droite + gros boutons. Carte suivante instantanée, pas de confirmation, légende des touches visible.
- **File** : mots courts d'abord (2–8 lettres, ~131 k), les moins fréquents en premier ; filtres longueur / fréquence / motif.
- **Motivation** : compteur du jour, restant par longueur, série de jours.

### 1c. Bascule du produit sur le lexique curé
- Chargement du fichier curé derrière un flag de configuration ; définitions affichées dans la recherche ; fréquence utilisée par le générateur.

**Terminé quand** : 500+ mots triés en ~10 min sur téléphone, build reproductible, recherche et génération sur le lexique curé.

---

## Phase 2 — Catalogue de layouts
Objectif : recopier vite et sans erreur les grilles trouvées dans des magazines et des cahiers, dans de nombreux formats.

1. **Format v1** adapté à l'AZERTY : `x` = case définition, `-` = case lettre (l'ancien `#`/`.` reste accepté ; script de conversion). Aucune métadonnée : le format se déduit de la grille, l'identifiant du chemin. `backend/layouts/<L>x<H>/<NNN>.txt`, numéro attribué automatiquement. Flèches non encodées (déduites de la géométrie en Phase 5). [ADR 0006](adr/0006-format-des-layouts.md).
2. **Validateur** (CLI + tests + CI) : taille conforme au dossier ; chaque case lettre appartient à un mot de ≥ 2 lettres ; grilles en double signalées ; statistiques des slots. Un mot peut commencer au bord.
3. **Éditeur de layouts** dans la mini-app : choisir L×H (n'importe quel format), cliquer/toucher les cases, validation en direct ; « Enregistrer » **écrit directement dans `backend/layouts/<L>x<H>/`** après validation serveur, sans jamais écraser. Duplication/édition d'un layout existant.
4. `GET /api/layouts` (formats + aperçus) ; les nouveaux layouts rejoignent automatiquement le benchmark.
5. **Plus tard (non planifié)** : prendre en photo une grille ; le logiciel reconnaît les cases et propose la grille dans l'éditeur, où l'auteur corrige et valide ([#47](https://github.com/maximefd/terminator-app/issues/47)).

---

## Phase 3 — Moteur de génération avec mots imposés
**Contrat d'API** (ADR d'abord ; c'est aussi le futur contrat côté client) :
- Entrée : `layout_id` ou `format`, `must_words[]`, `wish_words[]`, `wish_dictionary_ids[]`, `target_wish_ratio` (0.3 par défaut), `seed`, `time_budget_ms`.
- Sortie : grille, mots placés avec leur source (`must` / `wish` / `common`), ratio atteint, mots obligatoires non placés avec la raison, statistiques.

**Moteur** :
1. Pools de mots dans `WordRepository` : commun (curé), souhaités (saisis + dictionnaires thématiques), obligatoires.
2. **Mots obligatoires** : vérification préalable des longueurs ; placement en premier (le plus contraint d'abord, avec backtracking) ; en cas d'échec, explication plutôt qu'une erreur 500.
3. **Mots souhaités** : tri des candidats par pool, puis fréquence, puis score de lettres ; ratio visé en objectif souple via **redémarrages aléatoires** dans le budget temps.
4. **Mots communs** : tri par fréquence des candidats (l'échantillon aléatoire de 30 k mots a déjà été supprimé en Phase 0a : il rendait presque toute génération impossible).
5. **Redémarrages aléatoires** : la baseline montre un profil « vite ou jamais » (11×6 : 3/20 en 20 s, grilles réussies en 3,6 à 15,7 s) ; plusieurs trajectoires courtes dans le budget plutôt qu'une longue. Voir `backend/benchmarks/README.md`.
5. **Performance** guidée par le benchmark : index des candidats par (position, lettre), invalidation ciblée du cache.
6. Tests : mot obligatoire placé, impossibilité expliquée, ratio rapporté, même seed ⇒ même grille.

**Terminé quand** : ≥ 95 % de succès dans le budget pour chaque layout du catalogue.

---

## Phase 4 — UX : génération et clarté globale

**État de départ (septembre 2026)** : l'écran de génération se limite à un menu de format et un bouton. Tout ce que
la Phase 3 a construit — mots obligatoires, dictionnaires thématiques, tri par fréquence, provenance des mots,
ratio atteint — existe côté API mais **n'est visible nulle part dans l'interface**. C'est l'objet de cette phase.

**Prérequis backend** : « choix du layout avec aperçus » demande `layout_id` dans la requête de génération
(`GET /api/layouts` fournit déjà les aperçus). Avec `target_wish_ratio`, ce sont les deux derniers champs du
contrat de l'[ADR 0007](adr/0007-contrat-de-generation.md) restant à implémenter.

- **Audit UX** ✅ (#21) des pages existantes et corrections : [docs/AUDIT-UX.md](AUDIT-UX.md) liste friction par friction ce qui a été corrigé, et ce qui ne l'est pas avec son issue (#78, #79).
- **Page d'accueil** ✅ (#22) : trois blocs avec un exemple **vrai** chacun (le motif `P??LE` et ses résultats réels, une grille produite par le moteur), appel à l'action, mode invité explicité. La recherche par motif a déménagé de `/` à `/search`, et les dictionnaires personnels ont leur page `/dictionaries` au lieu d'une colonne visible seulement une fois connecté.
- **Aide intégrée** ✅ : motifs d'exemple cliquables (`P??LE`), obligatoire contre souhaité expliqué sous la liste de mots, états vides qui disent quoi faire (#21, #22).
- **Écran de génération** ✅ (#23) : liste de mots ordonnée par glisser-déposer, bascule obligatoire / souhaité, sélection des dictionnaires thématiques, difficulté annoncée pendant la saisie, refus expliqués cause par cause, grille avec source des mots colorée et ratio atteint. **Reportés** : choix du layout avec aperçus et rejeu d'un seed — ils demandent `layout_id`, et l'auteur a écarté le choix du layout pour l'instant.
- **Sauvegarde des grilles** ✅ (#24) : modèle `SavedGrid`, migrations Alembic ([ADR 0010](adr/0010-migrations-de-schema.md)) et page « Mes grilles ». La grille est conservée telle que produite, pas rejouée : le lexique bouge, la seed ne suffit pas à la retrouver.
- **Recherche (derniers 10 %)** : lettres incluses/exclues, filtre de longueur, définitions.
- Tests Playwright et contrôle d'accessibilité axe en CI ; session d'utilisabilité avec un pair.

## Phase 5 — Rendu professionnel (priorité basse)
- Flèches déduites des débuts de mots (droite, bas, coudées) ; rendu des cases définitions ; saisie des définitions ; export impression/PDF.

## Phase 6 — Durcissement production
- Cookies httpOnly + CSRF au lieu de localStorage ; Postgres uniquement en production avec migrations au déploiement ; sauvegardes, Sentry, logs structurés ; environnement de staging ; test d'intrusion selon la checklist ASVS ; revue des licences (Lexique / Wiktionnaire, CC BY-SA).

## Phase 7 — Décision de passage à l'échelle : file serveur ou moteur client
- **Déclencheur** : charge ou latence de génération problématique, ou avant ouverture à d'autres utilisateurs.
- **Spike + ADR** comparant : (a) file de jobs serveur (RQ/Celery + Redis) ; (b) **moteur côté client** (portage TypeScript ou Rust→WASM dans un Web Worker, lexique compressé DAWG/FST) ; (c) hybride.
- **Prérequis déjà prévus** : moteur pur et déterministe, contrat JSON, benchmark pour vérifier l'équivalence, lexique curé compact.

---

## Ordre et calendrier
1. **Avant la relecture** : Phase 0 complète + démarrage des Phases 1a/1b (démo du curateur).
2. **Ensuite, en parallèle** : Phase 1 (curation quotidienne), Phase 2 (layouts), Phase 3 (moteur).
3. Puis Phase 4, puis 5, 6 et 7 selon les besoins.
