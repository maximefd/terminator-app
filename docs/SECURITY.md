# 🔐 Sécurité — Terminator

> Document vivant. Dernière mise à jour : septembre 2026 (Phase 0b de la [roadmap](ROADMAP.md)).

## Signaler une vulnérabilité

Merci de **ne pas ouvrir d'issue publique**. Utilisez le signalement privé de GitHub (onglet *Security* → *Report a vulnerability*) sur le dépôt. Décrivez l'impact, les étapes de reproduction et, si possible, une piste de correction.

---

## Modèle de menace (léger)

### Ce qu'on protège

| Actif | Pourquoi c'est sensible |
|-------|-------------------------|
| Comptes (e-mail, hash du mot de passe) | Données personnelles, réutilisation de mots de passe |
| Dictionnaires et mots personnels | Travail de l'auteur, potentiellement inédit |
| Secrets (`SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`) | Permettent de forger des jetons ou d'accéder à la base |
| Disponibilité de l'API | La génération de grilles consomme beaucoup de CPU ; le dictionnaire occupe beaucoup de mémoire |

### Qui peut attaquer

- **Visiteur anonyme** : force brute sur la connexion, recherches ou générations massives (déni de service).
- **Utilisateur authentifié malveillant** : tentative d'accès aux dictionnaires des autres (IDOR), contenu hostile dans les champs.
- **Robot** : création de comptes en masse, scraping.

### Points d'entrée

| Endpoint | Auth | Risques principaux |
|----------|------|--------------------|
| `POST /api/auth/register`, `/login` | Non | Force brute, énumération de comptes, entrées malformées |
| `POST /api/auth/refresh`, `/logout` | Cookie de refresh + CSRF | Rejeu de jeton ; requête forgée depuis un autre site |
| `GET/POST/PATCH/DELETE /api/dictionaries...` | Oui | IDOR, injection, contenu hostile, remplissage de la base |
| `POST /api/search` | Optionnelle | Injection SQL (`LIKE`), masques coûteux |
| `POST /api/grids/generate` | Optionnelle | Déni de service CPU |
| `DELETE /api/users/me` | Oui + mot de passe | Effacement incomplet des données ; suppression par un jeton volé |

---

## Mesures en place

| Domaine | Mesure | Où |
|---------|--------|----|
| Validation | Schéma pydantic sur chaque corps JSON (longueurs, jeux de caractères, types stricts) ; erreurs 400 en français sans écho de la valeur reçue | `backend/schemas.py` |
| Injection SQL | ORM paramétré ; jokers `%`, `_`, `\` échappés dans la recherche `LIKE` (et refusés par la validation) | `backend/routes.py` |
| Autorisation | Chaque dictionnaire/mot est filtré par propriétaire ; accès à la ressource d'un autre ⇒ 404 (existence non révélée) | `get_owned_dictionary` ; `tests/test_authorization.py` |
| Mots de passe | bcrypt ; 8 à 128 caractères à l'inscription | `backend/auth.py` |
| Énumération | Même message et même coût (hash factice) pour e-mail inconnu ou mauvais mot de passe | `backend/auth.py` |
| Liens par e-mail | Signés (itsdangerous, `SECRET_KEY`), un sel par usage ; mot de passe : une heure, une seule fois (empreinte du hash actuel) ; confirmation : 7 jours ; « mot de passe oublié » répond pareil que le compte existe ou non ; 5 envois par heure et par IP | `backend/account_links.py`, `backend/auth.py` |
| Session | Jetons en **cookies `httpOnly`** (`SameSite=Lax`, `Secure` en production), jamais dans le corps des réponses ; access token 15 min sur `/api/`, refresh token 7 jours sur `/api/auth/` seulement ; jeton d'un compte supprimé ⇒ 401 ; refresh token refusé sur l'API et inversement ([ADR 0015](adr/0015-session-en-cookies.md)) | `backend/auth.py`, `backend/app.py` |
| CSRF | Double soumission : cookie `csrf_*` lisible, recopié dans `X-CSRF-TOKEN` pour toute écriture ; CORS avec credentials limité aux origines exactes | Flask-JWT-Extended, `frontend/src/lib/api-client.ts` |
| Révocation | La déconnexion révoque l'access et le refresh token (table `revoked_token`) ; un changement de mot de passe ferme toutes les sessions (`user.sessions_revoked_at`) | `backend/security.py`, `backend/auth.py` |
| Force brute / DoS | Rate limiting par IP : login 10/min, inscription 5/h, refresh 30/min, recherche 120/min, génération 10/min. Derrière Cloudflare, l'IP vient de `CF-Connecting-IP`, lu seulement si `CLIENT_IP_HEADER` le désigne (sinon l'en-tête s'inventerait) | `backend/security.py` (`client_ip`) |
| Saturation CPU | Au plus 2 générations simultanées (une par cœur), une seule par visiteur (compte, sinon IP) : 429 au-delà. Verrous de fichiers partagés entre les workers gunicorn ([ADR 0013](adr/0013-cible-hebergement-production.md)) | `backend/generation_slots.py` |
| Coût des requêtes | Corps ≤ 64 Ko ; recherche arrêtée à la limite pendant le parcours du Trie ; génération bornée par un budget temps ; 20 dictionnaires et 5 000 mots max | `backend/app.py` |
| Erreurs | Réponses JSON génériques, détails uniquement dans les logs serveur ; débogueur Werkzeug désactivé hors `FLASK_DEBUG=1` | `backend/security.py`, `backend/run.py` |
| En-têtes API | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP `default-src 'none'`, `Cache-Control: no-store`, HSTS en production | `backend/security.py` |
| En-têtes frontend | CSP (scripts, connexions et frames restreints), `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, HSTS en production ; sur le site statique, une CSP par page n'autorise que ses scripts inline, par empreinte `sha256` (#99) | `frontend/security-headers.mjs`, `frontend/scripts/write-headers.mjs` |
| CORS | Liste exacte d'origines, sans credentials ; `*` refusé en production | `backend/app.py` |
| Configuration | Refus de démarrer en production avec des secrets par défaut, sans base de données ou avec CORS `*` | `backend/app.py` |
| Suivi des erreurs | Sentry, inactif sans DSN. Seules les erreurs partent : ni cookies, ni en-têtes d'authentification, ni corps de requête, ni variables locales, ni adresse IP ; le jeton des liens reçus par e-mail est retiré des adresses. Vérifié par un aller-retour réel dans les tests | `backend/monitoring.py`, `frontend/src/lib/monitoring.ts` |
| Journaux | En production, JSON ; chemins **sans query string**, jamais de mot de passe, de jeton ni de corps de requête ; l'adresse IP du visiteur figure dans le journal d'accès | `backend/logging_setup.py`, `backend/gunicorn.conf.py` |
| RGPD | Suppression réelle du compte, des dictionnaires, des mots et des grilles, depuis la page « Mon compte » ; le mot de passe est redemandé (un jeton volé ne suffit pas) et les tentatives suivent la limite de la connexion | `DELETE /api/users/me`, `frontend/src/app/account` |

---

## Limites connues (à traiter)

| Limite | Risque | Plan |
|--------|--------|------|
| Pas de rotation du refresh token | Un refresh token volé sert jusqu'à la déconnexion ou au changement de mot de passe | Choix de l'[ADR 0015](adr/0015-session-en-cookies.md) : la rotation déconnecterait les onglets entre eux |
| CSP de développement avec `'unsafe-inline'` et `'unsafe-eval'` | Aucun en production : le site statique n'autorise que les scripts de chaque page, par empreinte (#99) | Limité à `next dev` ; `style-src` garde `'unsafe-inline'` (styles en ligne des composants), risque bien moindre |
| Rate limiting en mémoire | Compteurs non partagés entre processus : avec 3 workers gunicorn, une limite de 10/min vaut jusqu'à 30/min (les places de génération, elles, sont communes) | Redis (`RATELIMIT_STORAGE_URI`) si l'écart devient un problème, et avant tout passage multi-instance |
| L'inscription révèle si un e-mail existe (409) | Énumération de comptes | Acceptable tant que l'app est personnelle ; vérification par e-mail plus tard |
| Confirmation d'adresse non bloquante | Un compte peut être créé au nom d'une adresse qui n'est pas la sienne ; il reste marqué « non confirmé » | Choix de l'[ADR 0014](adr/0014-emails-du-compte.md) : à rendre bloquante si des comptes jetables apparaissent |
| Génération synchrone dans la requête | Un worker occupé jusqu'à 20 s ; au-delà des places de génération, les visiteurs reçoivent 429 plutôt que d'attendre | Atténué par les places de génération ; Phase 7 : file de jobs ou moteur côté client |
| Écritures utilisateur nouvelles (définitions, notes, lettres d'une grille) | Contenu arbitraire en base | Validées par schéma et bornées (120 caractères par définition, 5 000 pour les notes, une lettre A-Z par case) ; chaque accès passe par `get_owned_grid()`, une grille d'autrui répond 404 |
| Sauvegardes non automatisées | Perte de données | Les outils existent : `make db-backup` (dump compressé, chiffré par `age` si `BACKUP_AGE_RECIPIENT`, rotation à 30 jours) et `make db-restore-check` (restauration dans une base jetable). Reste, sur le serveur : les lancer chaque nuit, copier hors du serveur (Cloudflare R2), vérifier chaque mois ([ADR 0013](adr/0013-cible-hebergement-production.md)) |

---

## Checklist de mise en production

- [ ] `APP_ENV=production`
- [ ] `SECRET_KEY` et `JWT_SECRET_KEY` distincts, aléatoires (≥ 32 octets, l'API refuse de démarrer sinon), jamais commités
- [ ] `DATABASE_URL` vers PostgreSQL
- [ ] `CORS_ORIGINS` = origine exacte du frontend (ex : `https://leflechoir.fr`)
- [ ] `CLIENT_IP_HEADER=CF-Connecting-IP` derrière Cloudflare Tunnel, `TRUST_PROXY_HOPS=0` (sinon le rate limiting voit toutes les requêtes venir de cloudflared)
- [ ] L'API n'est joignable que par le tunnel : aucun port web ouvert sur le serveur (sinon `CF-Connecting-IP` s'invente)
- [ ] Serveur gunicorn (commande par défaut de l'image), jamais `python run.py`
- [ ] `MAIL_BACKEND=smtp` avec le relais du prestataire (sinon les liens de mot de passe finissent dans le journal) ; `MAIL_FROM` sur le domaine, SPF et DKIM configurés
- [ ] `COOKIE_DOMAIN` = domaine commun au frontend et à l'API (ex : `leflechoir.fr`), pour que le frontend lise les cookies CSRF
- [ ] `SENTRY_DSN` (API) et `NEXT_PUBLIC_SENTRY_DSN` (build du frontend) renseignés, projet Sentry hébergé dans l'UE ; la page de confidentialité le mentionne
- [ ] `FLASK_DEBUG` absent
- [ ] `RATELIMIT_STORAGE_URI` vers Redis si plusieurs instances
- [ ] HTTPS uniquement (fourni par Cloudflare)
- [ ] `BACKUP_AGE_RECIPIENT` renseigné, clé privée **hors** du serveur ; sauvegarde nocturne copiée hors du serveur ; une restauration vérifiée (`make db-restore-check`)

---

## Checklist OWASP ASVS (allégée)

Audit complet, essais compris : [AUDIT-SECURITE.md](AUDIT-SECURITE.md).

| Exigence | Statut |
|----------|--------|
| V2 — Mots de passe hashés avec un algorithme adapté (bcrypt) | ✅ |
| V2 — Longueur minimale de mot de passe | ✅ (8) ; jusqu'à 128 caractères, y compris au-delà des 72 octets de bcrypt |
| V2 — Protection contre la force brute | ✅ rate limiting |
| V2 — Messages d'échec de connexion génériques | ✅ |
| V2 — Récupération de compte sûre (lien à usage unique, limité dans le temps, sans révéler l'existence du compte) | ✅ ([ADR 0014](adr/0014-emails-du-compte.md)) |
| V3 — Jetons à durée de vie courte + renouvellement | ✅ |
| V3 — Révocation des sessions | ✅ déconnexion et changement de mot de passe ([ADR 0015](adr/0015-session-en-cookies.md)) |
| V3 — Jetons hors de portée de JavaScript | ✅ cookies `httpOnly` |
| V4 — Protection CSRF | ✅ double soumission |
| V4 — Contrôle d'accès côté serveur sur chaque ressource | ✅ testé |
| V5 — Validation des entrées par liste blanche | ✅ |
| V5 — Requêtes paramétrées / échappement SQL | ✅ |
| V7 — Pas de détail technique dans les erreurs | ✅ |
| V7 — Pas de donnée sensible dans les logs | ✅ (aucun mot de passe ni jeton loggé) |
| V8 — Effacement des données personnelles | ✅ |
| V12 — Taille des requêtes limitée | ✅ |
| V13 — Limitation de débit des API | ✅ (mémoire) |
| V14 — En-têtes de sécurité HTTP | ✅ |
| V14 — CORS restrictif | ✅ |
| V14 — Dépendances surveillées | ✅ versions figées, `pip-audit` en CI, Dependabot (pip, npm, GitHub Actions) |
| V14 — Secrets hors du code | ✅ |
