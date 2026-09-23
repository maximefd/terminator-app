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
| `POST /api/auth/refresh` | Refresh token | Rejeu de jeton |
| `GET/POST/PATCH/DELETE /api/dictionaries...` | Oui | IDOR, injection, contenu hostile, remplissage de la base |
| `POST /api/search` | Optionnelle | Injection SQL (`LIKE`), masques coûteux |
| `POST /api/grids/generate` | Optionnelle | Déni de service CPU |
| `DELETE /api/users/me` | Oui | Effacement incomplet des données |

---

## Mesures en place

| Domaine | Mesure | Où |
|---------|--------|----|
| Validation | Schéma pydantic sur chaque corps JSON (longueurs, jeux de caractères, types stricts) ; erreurs 400 en français sans écho de la valeur reçue | `backend/schemas.py` |
| Injection SQL | ORM paramétré ; jokers `%`, `_`, `\` échappés dans la recherche `LIKE` (et refusés par la validation) | `backend/routes.py` |
| Autorisation | Chaque dictionnaire/mot est filtré par propriétaire ; accès à la ressource d'un autre ⇒ 404 (existence non révélée) | `get_owned_dictionary` ; `tests/test_authorization.py` |
| Mots de passe | bcrypt ; 8 à 128 caractères à l'inscription | `backend/auth.py` |
| Énumération | Même message et même coût (hash factice) pour e-mail inconnu ou mauvais mot de passe | `backend/auth.py` |
| Jetons | Access token 15 min, refresh token 7 jours, endpoint `/api/auth/refresh` ; jeton d'un compte supprimé ⇒ 401 ; refresh token refusé sur l'API et inversement | `backend/security.py` |
| Force brute / DoS | Rate limiting par IP : login 10/min, inscription 5/h, refresh 30/min, recherche 120/min, génération 10/min. Derrière Cloudflare, l'IP vient de `CF-Connecting-IP`, lu seulement si `CLIENT_IP_HEADER` le désigne (sinon l'en-tête s'inventerait) | `backend/security.py` (`client_ip`) |
| Saturation CPU | Au plus 2 générations simultanées (une par cœur), une seule par visiteur (compte, sinon IP) : 429 au-delà. Verrous de fichiers partagés entre les workers gunicorn ([ADR 0013](adr/0013-cible-hebergement-production.md)) | `backend/generation_slots.py` |
| Coût des requêtes | Corps ≤ 64 Ko ; recherche arrêtée à la limite pendant le parcours du Trie ; génération bornée par un budget temps ; 20 dictionnaires et 5 000 mots max | `backend/app.py` |
| Erreurs | Réponses JSON génériques, détails uniquement dans les logs serveur ; débogueur Werkzeug désactivé hors `FLASK_DEBUG=1` | `backend/security.py`, `backend/run.py` |
| En-têtes API | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP `default-src 'none'`, `Cache-Control: no-store`, HSTS en production | `backend/security.py` |
| En-têtes frontend | CSP (scripts, connexions et frames restreints), `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, HSTS en production | `frontend/next.config.ts` |
| CORS | Liste exacte d'origines, sans credentials ; `*` refusé en production | `backend/app.py` |
| Configuration | Refus de démarrer en production avec des secrets par défaut, sans base de données ou avec CORS `*` | `backend/app.py` |
| RGPD | Suppression réelle du compte, des dictionnaires et des mots | `DELETE /api/users/me` |

---

## Limites connues (à traiter)

| Limite | Risque | Plan |
|--------|--------|------|
| Jetons stockés dans `localStorage` | Vol de session en cas de faille XSS (atténué par la CSP et l'absence de HTML utilisateur rendu) | Phase 6 : cookies `httpOnly` + protection CSRF |
| Pas de révocation des jetons à la déconnexion | Un jeton volé reste valable jusqu'à expiration (refresh : 7 jours) | Phase 6 : liste de révocation ou rotation des refresh tokens |
| CSP frontend avec `'unsafe-inline'` pour les scripts | Protection XSS partielle | Phase 6 : nonces CSP |
| Rate limiting en mémoire | Compteurs non partagés entre processus : avec 3 workers gunicorn, une limite de 10/min vaut jusqu'à 30/min (les places de génération, elles, sont communes) | Redis (`RATELIMIT_STORAGE_URI`) si l'écart devient un problème, et avant tout passage multi-instance |
| L'inscription révèle si un e-mail existe (409) | Énumération de comptes | Acceptable tant que l'app est personnelle ; vérification par e-mail plus tard |
| Pas de vérification d'e-mail ni de réinitialisation de mot de passe | Comptes jetables, perte d'accès | Avant ouverture à d'autres utilisateurs |
| Dépendances Python non figées | Mise à jour non maîtrisée, vulnérabilités | Phase 0c : versions figées + `pip-audit`, Dependabot, CodeQL en CI |
| Génération synchrone dans la requête | Un worker occupé jusqu'à 20 s ; au-delà des places de génération, les visiteurs reçoivent 429 plutôt que d'attendre | Atténué par les places de génération ; Phase 7 : file de jobs ou moteur côté client |
| Écritures utilisateur nouvelles (définitions, notes, lettres d'une grille) | Contenu arbitraire en base | Validées par schéma et bornées (120 caractères par définition, 5 000 pour les notes, une lettre A-Z par case) ; chaque accès passe par `get_owned_grid()`, une grille d'autrui répond 404 |
| Sauvegardes non automatisées | Perte de données | Les outils existent : `make db-backup` (dump compressé, chiffré par `age` si `BACKUP_AGE_RECIPIENT`, rotation à 30 jours) et `make db-restore-check` (restauration dans une base jetable). Reste, sur le serveur : les lancer chaque nuit, copier hors du serveur (Cloudflare R2), vérifier chaque mois ([ADR 0013](adr/0013-cible-hebergement-production.md)) |

---

## Checklist de mise en production

- [ ] `APP_ENV=production`
- [ ] `SECRET_KEY` et `JWT_SECRET_KEY` distincts, aléatoires (≥ 32 octets), jamais commités
- [ ] `DATABASE_URL` vers PostgreSQL
- [ ] `CORS_ORIGINS` = origine exacte du frontend (ex : `https://terminator.fr`)
- [ ] `CLIENT_IP_HEADER=CF-Connecting-IP` derrière Cloudflare Tunnel, `TRUST_PROXY_HOPS=0` (sinon le rate limiting voit toutes les requêtes venir de cloudflared)
- [ ] L'API n'est joignable que par le tunnel : aucun port web ouvert sur le serveur (sinon `CF-Connecting-IP` s'invente)
- [ ] Serveur gunicorn (commande par défaut de l'image), jamais `python run.py`
- [ ] `FLASK_DEBUG` absent
- [ ] `RATELIMIT_STORAGE_URI` vers Redis si plusieurs instances
- [ ] HTTPS uniquement (fourni par Cloudflare)
- [ ] `BACKUP_AGE_RECIPIENT` renseigné, clé privée **hors** du serveur ; sauvegarde nocturne copiée hors du serveur ; une restauration vérifiée (`make db-restore-check`)

---

## Checklist OWASP ASVS (allégée)

| Exigence | Statut |
|----------|--------|
| V2 — Mots de passe hashés avec un algorithme adapté (bcrypt) | ✅ |
| V2 — Longueur minimale de mot de passe | ✅ (8) |
| V2 — Protection contre la force brute | ✅ rate limiting |
| V2 — Messages d'échec de connexion génériques | ✅ |
| V3 — Jetons à durée de vie courte + renouvellement | ✅ |
| V3 — Révocation des sessions | ❌ (Phase 6) |
| V3 — Jetons hors de portée de JavaScript | ❌ (Phase 6) |
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
| V14 — Dépendances surveillées | ❌ (Phase 0c) |
| V14 — Secrets hors du code | ✅ |
