# 🛡️ Audit de sécurité — OWASP ASVS

> Audit du 23/09/2026, avant la mise en ligne (Phase 6 de la [roadmap](ROADMAP.md)). Référence : [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/) niveau 1, étendu aux points du niveau 2 qui comptent pour une application à comptes. Ce n'est pas un test d'intrusion externe : c'est une revue méthodique menée par l'équipe elle-même. Elle a été conduite sur le code, puis vérifiée par des essais sur l'image Docker en configuration de production (gunicorn, `APP_ENV=production`, PostgreSQL).

## Méthode

1. **Revue du code** par chapitre ASVS : authentification, session, contrôle d'accès, validation, erreurs et journaux, protection des données, communications, configuration.
2. **Recherche de motifs à risque** : HTML injecté (`dangerouslySetInnerHTML`, `innerHTML`), `eval` ou `new Function`, SQL brut, secrets en dur, données sensibles dans les journaux, redirections construites à partir d'une entrée. Aucune occurrence.
3. **Essais sur l'API en configuration de production**, avec `curl`, un navigateur piloté par Playwright et des jetons forgés à la main (tableau ci-dessous).

## Essais sur l'API

| Essai | Attendu | Résultat |
|-------|---------|----------|
| JWT avec `alg: none` | refusé | ✅ 401 |
| JWT signé avec une autre clé | refusé | ✅ 401 |
| Refresh token utilisé comme access token, et l'inverse | refusé | ✅ 401 (tests) |
| Jeton d'une session fermée ou d'avant un changement de mot de passe | refusé | ✅ 401 (tests) |
| Écriture par cookie sans jeton CSRF | refusée | ✅ 401 (tests) |
| Corps `text/plain` (formulaire posté depuis un autre site) | refusé | ✅ 400 |
| Méthodes `TRACE`, `PUT` | refusées | ✅ 405 |
| Corps de 70 Ko | refusé | ✅ 413 |
| 12 connexions ratées avec un `X-Forwarded-For` différent à chaque fois | pas de contournement | ✅ 429 dès la 10ᵉ |
| `CF-Connecting-IP` inventé, sans `CLIENT_IP_HEADER` | ignoré | ✅ |
| Grille, dictionnaire ou mot d'un autre compte | 404 | ✅ (tests d'autorisation) |
| **Mot de passe de 100 caractères, ou de 64 lettres accentuées** | inscription possible | ❌ **500**, corrigé |
| **Clé secrète courte en production** (`SECRET_KEY=court`) | démarrage refusé | ❌ **acceptée**, corrigé |

## Défauts trouvés et corrigés

1. **Mots de passe de plus de 72 octets : erreur 500.** L'API accepte 128 caractères, mais bcrypt ne lit que 72 octets, et depuis sa version 5 il refuse le reste. Un long mot de passe, ou un mot de passe plus court fait de lettres accentuées (2 octets chacune), empêchait l'inscription et la réinitialisation. Au-delà de 72 octets, bcrypt reçoit maintenant l'empreinte SHA-256 du mot de passe entier : chaque caractère compte. Les mots de passe plus courts sont traités comme avant, donc les comptes existants restent valables.
2. **Clés secrètes faibles acceptées en production.** L'API refusait les clés par défaut, pas les clés courtes, ni une même clé pour deux usages. `SECRET_KEY` et `JWT_SECRET_KEY` signent les sessions et les liens envoyés par e-mail : il leur faut maintenant 32 octets au moins (RFC 7518), et deux valeurs distinctes. Sinon l'API refuse de démarrer.

Les chantiers précédents avaient déjà corrigé en cours de route : un repli vers un sous-domaine Render supprimé, qui aurait reçu e-mails et mots de passe (#92) ; des jetons lisibles par une faille XSS (ADR 0015) ; des scripts inline autorisés sans condition (#99) ; des variables locales envoyées à Sentry.

## Résultat par chapitre

| Chapitre ASVS | État | Notes |
|---------------|------|-------|
| V2 — Authentification | ✅ | bcrypt ; 8 à 128 caractères, sans règle de composition (conforme ASVS) ; limite de débit ; messages génériques ; récupération par lien à usage unique ([ADR 0014](adr/0014-emails-du-compte.md)) |
| V3 — Session | ✅ | Cookies `httpOnly`, `Secure`, `SameSite=Lax` ; révocation à la déconnexion et au changement de mot de passe ([ADR 0015](adr/0015-session-en-cookies.md)) |
| V4 — Contrôle d'accès | ✅ | Chaque ressource est filtrée par propriétaire (`get_owned_*`), celle d'un autre compte répond 404 ; testé |
| V5 — Validation et encodage | ✅ | Schémas pydantic partout ; React encode tout ce qu'il affiche ; aucun HTML injecté ; SQL paramétré |
| V7 — Erreurs et journaux | ✅ | Erreurs génériques ; journaux JSON sans mot de passe, jeton, corps ni query string ; Sentry sans données personnelles |
| V8 — Protection des données | ✅ | `Cache-Control: no-store` sur l'API ; suppression réelle du compte ; sauvegardes chiffrées |
| V9 — Communications | ✅ | HTTPS et HSTS par Cloudflare ; l'API n'est joignable que par le tunnel ([ADR 0013](adr/0013-cible-hebergement-production.md)) |
| V13 — API | ✅ | CORS limité aux origines exactes ; JSON exigé ; méthodes limitées ; corps de 64 Ko au plus |
| V14 — Configuration | ✅ | Démarrage refusé en production avec une configuration faible ; dépendances figées et auditées ; en-têtes de sécurité ; CSP par empreinte |

## Risques acceptés

| Risque | Pourquoi l'accepter |
|--------|---------------------|
| L'inscription révèle si une adresse est déjà prise (409), et « mot de passe oublié » répond un peu plus lentement quand un e-mail part | Déjà noté dans [SECURITY.md](SECURITY.md). Le cacher demanderait une vérification d'adresse **avant** la création du compte ; à reconsidérer si des comptes jetables apparaissent. |
| Pas de vérification des mots de passe contre les fuites connues (ASVS 2.1.7) | Demanderait d'appeler un service extérieur (Have I Been Pwned) à chaque inscription. À reconsidérer à l'ouverture publique. |
| Pas de changement de mot de passe une fois connecté : il passe par « mot de passe oublié » | Le lien par e-mail le permet déjà, et il ferme les autres sessions. |
| L'en-tête `Server: gunicorn` | Cloudflare le remplace devant l'API ; il ne dit ni la version ni le système. |
| `style-src 'unsafe-inline'` | Styles en ligne des composants ; une injection de style est bien moins grave qu'une injection de script, qui est bloquée. |
| Rate limiting en mémoire, par worker (jusqu'à 3 fois la limite) | Voir SECURITY.md ; Redis le jour où il y aura plusieurs serveurs. |

## Contrôle de l'adresse publique, le 25/09/2026

Le jour de la mise en ligne, contre `https://leflechoir.fr` et `https://api.leflechoir.fr` : les essais ci-dessus qui ont un sens en production, puis TLS, en-têtes, fichiers exposés et redirections. Aucun essai destructif.

| Essai | Attendu | Résultat |
|-------|---------|----------|
| JWT avec `alg: none`, puis signé d'une autre clé | refusé | ✅ 401 |
| Corps `text/plain` | refusé | ✅ 400 |
| Méthodes `TRACE`, `PUT` | refusées | ✅ 405 |
| Corps de 70 Ko | refusé | ✅ 413 |
| `CF-Connecting-IP` inventé par le client | ignoré | ✅ bloqué par Cloudflare (403), n'atteint pas l'API |
| Connexions ratées, `X-Forwarded-For` différent à chaque fois | pas de contournement | ✅ 429 à la 25ᵉ (compteurs par worker, voir « Risques acceptés ») |
| Deux visiteurs derrière le tunnel | comptés à part | ✅ l'API voit leurs vraies adresses, pas celle de cloudflared |
| Ports du serveur, de l'extérieur | seul SSH | ✅ 22 ouvert ; 80, 443, 5000, 5432 et 8080 fermés |
| Fichiers sensibles (`/.env`, `/.git/config`…) | absents | ✅ 404 sur le site et sur l'API |
| Erreurs de l'API | génériques | ✅ JSON en français, sans trace technique |
| En-têtes | présents | ✅ CSP, HSTS, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy` ; `Cache-Control: no-store` sur l'API ; `security.txt` |
| **Redirection après la connexion** (`?next=/⇥/exemple.com`) | reste sur le site | ❌ **menait sur un autre site**, corrigé (#165) |
| **HTTP en clair sur l'API** | redirigé | ⚠️ `http://api.leflechoir.fr` répond (le site, lui, redirige) : *Always Use HTTPS* à activer dans la zone |
| **TLS 1.0 et 1.1** | refusés | ⚠️ refusés par le site, **acceptés par l'API** : *Minimum TLS Version* à 1.2 dans la zone |
| DNSSEC, enregistrement CAA | recommandés | ➖ absents ; durcissements facultatifs |

## À refaire

~~À la mise en ligne, sur le vrai serveur : la checklist de production de [SECURITY.md](SECURITY.md), puis les essais du tableau ci-dessus contre l'adresse publique. Il faut notamment vérifier que l'API ne répond **que** par le tunnel.~~ Fait le 25/09/2026 (section précédente). Restent deux réglages de la zone : *Always Use HTTPS* et *Minimum TLS Version* à 1.2.
