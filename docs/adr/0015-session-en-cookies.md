# 0015 — Session en cookies httpOnly, protection CSRF et révocation

- Statut : acceptée (remplace l'[ADR 0003](0003-jwt-en-en-tete.md))
- Date : 2026-09-23

## Contexte

- L'[ADR 0003](0003-jwt-en-en-tete.md) rangeait les jetons dans le `localStorage` du navigateur : une faille XSS pouvait les lire et les emporter. Le refresh token, valable 7 jours, n'était pas révocable : se déconnecter ne l'invalidait pas.
- L'ADR 0003 prévoyait de passer aux cookies `httpOnly` avant toute ouverture publique (Phase 6, #28).
- Le frontend et l'API seront sur deux sous-domaines d'un même domaine en production ([ADR 0013](0013-cible-hebergement-production.md)) : même site, donc des cookies `SameSite=Lax` suffisent.

## Décision

1. **Les jetons voyagent en cookies `httpOnly`**, que le JavaScript de la page ne peut pas lire. L'API ne les met **jamais dans le corps** d'une réponse : un jeton dans le corps redeviendrait lisible par une faille XSS.
   - L'access token (15 minutes) est envoyé sur `/api/` ; le refresh token (7 jours) seulement sur `/api/auth/` (renouvellement, déconnexion).
   - `SameSite=Lax`, `Secure` en production, et en production `COOKIE_DOMAIN`, le domaine commun au frontend et à l'API.
   - Les cookies durent autant que leur jeton, pas le temps d'un onglet.
2. **Protection CSRF par double soumission** (Flask-JWT-Extended) : à chaque session, l'API pose aussi deux cookies **lisibles** (`csrf_access_token`, `csrf_refresh_token`). Le frontend en recopie la valeur dans l'en-tête `X-CSRF-TOKEN` de chaque écriture. Un autre site peut faire envoyer les cookies, mais il ne peut pas les lire pour les recopier.
3. **Révocation.**
   - La déconnexion (`POST /api/auth/logout`) révoque l'access token et le refresh token en cours : table `revoked_token`, gardée jusqu'à leur expiration seulement.
   - Changer de mot de passe par e-mail ([ADR 0014](0014-emails-du-compte.md)) ferme **toutes** les sessions ouvertes avant : `user.sessions_revoked_at`.
4. **Pas de rotation du refresh token.** Avec des cookies partagés, deux onglets qui renouvellent en même temps se déconnecteraient l'un l'autre. La révocation à la déconnexion et au changement de mot de passe couvre le vol.
5. **L'en-tête `Authorization: Bearer` reste accepté, et prioritaire.** Les tests et un éventuel client autre que le navigateur s'en servent. Un jeton passé par en-tête n'est pas soumis au CSRF, puisqu'aucun autre site ne peut le poser.
6. **En développement, le frontend passe par un proxy** : `next dev` relaie `/api/*` vers l'API locale quand `NEXT_PUBLIC_API_BASE_URL` n'est pas défini. Tout est sur la même origine, depuis le Mac, depuis le téléphone sur le Wi-Fi, et à travers le tunnel de `make preview-remote`, qui n'en ouvre plus qu'un. Deux sous-domaines de `trycloudflare.com` ne sont pas forcément le même site pour les cookies.

## Conséquences

- ✅ Une faille XSS ne peut plus emporter les jetons. Elle peut encore agir dans la page le temps de la visite : la CSP reste la défense principale.
- ✅ Se déconnecter ferme vraiment la session, et un mot de passe changé ferme toutes les autres.
- Le frontend sait qu'une session existe à la présence du cookie `csrf_refresh_token`, sans appeler l'API. Une session révoquée entre-temps se découvre au premier 401 : l'API efface alors les cookies et l'interface se déconnecte.
- CORS passe en `credentials`, et reste limité aux origines exactes de `CORS_ORIGINS` (`*` refusé en production).
- Les sessions ouvertes avant ce changement (jetons dans `localStorage`) sont effacées au premier chargement : il faut se reconnecter une fois.
- Une requête de plus par appel authentifié (le jeton est-il révoqué ?), sur une clé primaire.
- **Reste, de #28** : les nonces CSP. Ils sont impossibles sur un site statique, faute de serveur pour les tirer à chaque requête. La voie est une CSP à empreintes (`sha256-…`) calculées au build (#99).
