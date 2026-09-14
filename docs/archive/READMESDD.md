README — SDD & Plan d'action (v1.7)

Document technique centralisé — Spécification de développement détaillée, plan d'action court terme et long terme, exigences sécurité / RGPD / SEO, et checklists opérationnelles.
1. Contexte & objectif

L'objectif du projet est de fournir un outil web (site responsive) permettant de générer des grilles de mots fléchés automatiquement à partir d'un grand dictionnaire (DELA) et de dictionnaires personnels utilisateur. Le backend (Flask) et le moteur de génération sont considérés « feature complete » pour la V1. Nous basculons maintenant vers la phase frontend tout en documentant les exigences non-fonctionnelles et le backlog.

2. Etat actuel (résumé)

Backend : Python + Flask + SQLAlchemy (Docker). API opérationnelle (auth démo/POC, mots perso CRUD, recherche, endpoint /api/grids/generate). Dictionnaire DELA intégré (lite / clean switchable). Grid generator stable (V16/V14 selon commits).
Frontend : à démarrer (React + Vite + Tailwind recommandé).
Tests unitaires backend : partiels. Logging & metrics basiques en place.
3. Architecture technique

Backend : Flask app, modules séparés (app.py, models.py, trie_engine.py, grid_generator.py). DB SQLAlchemy (développement: SQLite in-memory; production: PostgreSQL).
Data : DELA (CSV), tables Utilisateur, Dictionary, PersonalWord.
Auth : POC avec Flask-Login ; futur : JWT/OAuth + verification email + password hashing sécurisé.
Infra : Docker, docker-compose, CI/CD (GitHub Actions), déploiement sur Render / Heroku / VPS.
4. Data Model (extrait)

Utilisateur (id, email, password_hash, ...)
Dictionary (id, name, user_id, is_active)
PersonalWord (id, dictionary_id, mot, mot_affiche, definition, date_ajout)
5. API (essentiel)

POST /api/login — connexion (POC)
POST /api/logout — logout
GET /api/status — health
GET/POST/DELETE /api/personal_words — CRUD mots perso (auth)
POST /api/search — recherche par mask + lettres
POST /api/grids/generate — génération de grille (auth requis pour l’instant)
6. Grid Generator — état & contraintes

Moteur : plusieurs versions itératives (V1 → V4 → V7 → V11 → V12 → V14/V16). 
Paramètres exposés : width, height, use_global, use_personal, seed, target_black_ratio (configurable).
Limites connues : règles esthétiques avancées (p.ex. connectivité des cases noires) en backlog V2.
7. Sécurité & RGPD (obligatoire)

7.1 Exigences de sécurité immédiates (MUST)

Stockage des secrets : toutes les clés/secret doivent être en variables d'environnement. En production, utiliser un gestionnaire de secrets (Vault, AWS Secrets Manager).
Chiffrement des mots de passe : utiliser Argon2id ou bcrypt avec salt ; jamais stocker les mots de passe en clair.
HTTPS obligatoire : HSTS, TLS (minimum TLS1.2), certificats automatiques (Let’s Encrypt).
Cookies : Secure, HttpOnly, SameSite=Lax/Strict selon besoins. Pas de sesiones persistantes non sécurisées.
Protection CSRF : pour endpoints sensibles côté session-based auth.
Validation & sanitation : toutes les entrées HTTP doivent être validées (longueurs, charset). Utiliser ORM/paramétrisation pour éviter SQL injection.
Rate limiting & brute force protection : limiter tentatives login et endpoints intensifs (ex: /api/search, /api/grids/generate).
CSP : Content Security Policy stricte par défaut, ouvrir seulement les domaines nécessaires.
Logging : ne jamais logguer de données sensibles (mot de passe, token). PII must be redacted.
Monitor & alert : Sentry / Rollbar pour erreurs, alertes sur erreurs 5xx et latences élevées.
7.2 RGPD & vie privée (MUST)

Consentement cookies : bannière cookie, catégorisation (strictement nécessaires, analytiques, marketing). Chargement de trackers conditionnel au consentement.
Droit d’accès / suppression : endpoints ou process admin pour exporter/supprimer les données personnelles (email, mots perso). Supporter la portabilité JSON.
Minimisation : ne collecter que les données essentielles.
Durée de rétention : définir une politique (ex. données actives 2 ans, logs anonymisés 90 jours, backups 30 jours) et la documenter.
Registre d’activités : conserver logs d’accès admin et actions sensibles.
7.3 Audits & conformité (SHOULD)

Scans SCA (Dependabot / Snyk), audits réguliers des dépendances, tests de pénétration avant mise en production.
8. SEO & Accessibilité

8.1 SEO (must-have pour site public)

Pages publiques : landing, features, pricing, docs — inclure meta title/description, Open Graph, canonical.
Sitemap.xml & robots.txt : générés automatiquement (ou via build pipeline).
SSR/Prerender : pour SEO, privilégier SSR (Next.js) ou prerendering des pages publiques statiques (landing, onboarding). SPA pure aura un coût SEO supplémentaire.
Structured data : JSON-LD pour organisation et product/service.
Performance : objectifs Lighthouse (perf > 90, accessibility > 90 sur pages clés).
8.2 Accessibilité (a11y)

Respect WCAG AA : contraste, labels explicites, focus management, keyboard navigation.
Tester avec axe / lighthouse et utilisateurs réels.
9. Dev environment & CI/CD

9.1 Environnement dev (obligatoire)

.env.example : lister toutes les variables d’environnement nécessaires (DATABASE_URL, SECRET_KEY, TRIE_MODE, DELA_PATH, SMTP_*, STRIPE_* etc.)
Docker : docker-compose.yml pour dev (app, db, redis optional). Démarrage : docker-compose up --build.
Scripts utiles : make setup, make db-migrate, make test, make lint.
9.2 CI/CD (recommended)

GitHub Actions pipeline : lint → unit tests → security scan → build image → push image → deploy to staging.
Staging/Production séparés, with protected branches and PR review.
10. Testing & QA

Unit tests backend (pytest), couverture minimale 80% sur modules critiques.
Integration tests pour endpoints (auth, search, generate).
E2E : Playwright pour le flux principal (login, add personal word, generate grid, view grid).
Pre-commit hooks : black, isort, flake8, mypy.
11. Monitoring, observability & ops

Health endpoints (/api/status) exposés. Liveness/readiness pour orchestrateur.
Error tracking : Sentry.
Metrics : exporter latencies and counters (Prometheus), dashboard Grafana.
Logs : structuré JSON, centralisé (ELK/CloudWatch/LogDNA).
12. Backups & DR

DB backups : nightly snapshots, retention 30 days, test restore monthly.
DELA source : versioned copy and checksum; store original CSV in object storage (S3).
Export/Import : tools to export user's personal dictionaries when user requests data porting.

Monetisation : freemium + plans pro, Stripe integration, feature gating.
Advanced generator V2 : implement black-square connectivity, symmetry options, quality heuristics.
Scaling : Redis cache, worker queue (Celery/RQ), horizontal DB scaling.
Analytics product : user metrics, retention, A/B tests for generator parameters.
13. Definition of Done (DoD) — critères minimaux pour features

Code revu & testé (unit/integration), couverture minimale 80% sur modules critiques.
Lint pass (black, flake8), types check (mypy) si activé.
Sécurité : secrets not in repo, env example present, basic rate limits.
Déploiement validé en staging et smoke-tested.
Documentation utilisateur/README mise à jour.
12. Backlog (priorités)

Frontend MVP (next) — HIGH
Save/Load grid, PDF export — HIGH
DELA clean by default + importer scripts — HIGH
Black-square connectivity & symmetry (V2 generator) — MEDIUM
Monetization & billing flow — MEDIUM
Admin dashboards, usage metrics — LOW
16. Prochaines actions immédiates

Commit this README_SDD.md to repository (suggested message: docs: SDD v1.7 — backend gelé, roadmap frontend).
Create GH issues for the 4-week roadmap tasks and assign owners/estimates.
Initialize frontend repo with CI, linting, and a minimal landing page.
Configure staging environment and add monitoring (Sentry).