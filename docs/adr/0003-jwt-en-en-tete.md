# 0003 — Authentification par JWT dans l'en-tête `Authorization`

- Statut : remplacée par l'[ADR 0015](0015-session-en-cookies.md)
- Date : 2026-09-14

## Contexte

Le frontend (Next.js) et l'API (Flask) sont deux applications distinctes, sur des origines différentes. L'authentification existante reposait déjà sur des JWT (Flask-JWT-Extended) stockés côté navigateur. Le jeton d'accès durait 15 minutes, sans moyen de le renouveler.

## Décision

- **Access token** de 15 minutes et **refresh token** de 7 jours, émis à l'inscription et à la connexion.
- Envoi par l'en-tête `Authorization: Bearer`, **sans cookie** : CORS sans credentials, pas de protection CSRF nécessaire.
- Endpoint `POST /api/auth/refresh`. Le client renouvelle automatiquement le jeton sur un 401, une seule fois, puis déconnecte.
- Les jetons d'un compte supprimé sont refusés : l'utilisateur est rechargé depuis la base à chaque requête.

## Conséquences

- ✅ Simple, adapté à deux origines, pas de CSRF.
- ⚠️ Les jetons sont dans `localStorage` : une faille XSS permettrait de les voler. Atténué par la CSP et l'absence de HTML utilisateur rendu.
- ⚠️ Pas de révocation à la déconnexion : un refresh token volé reste valable 7 jours.
- Avant toute ouverture publique (Phase 6) : passage à des cookies `httpOnly` avec protection CSRF, et révocation / rotation des refresh tokens. Voir [SECURITY.md](../SECURITY.md).
