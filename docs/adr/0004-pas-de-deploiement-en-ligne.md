# 0004 — Pas de déploiement en ligne avant un serveur de production

- Statut : acceptée
- Date : 2026-09-14

## Contexte

- Un backend Render et un projet Vercel avaient été configurés. Le projet Vercel déployait un ancien commit absent de ce dépôt.
- Maintenir ces déploiements coûtait du temps : Next.js vulnérable bloqué par Vercel, variables d'environnement incorrectes, pas de base de données persistante (les comptes étaient perdus à chaque redémarrage), mémoire limitée pour le dictionnaire.
- L'application n'a aujourd'hui qu'un utilisateur, son auteur, qui l'utilise en local.

## Décision

- **Tout tourne en local** : `docker compose up` (API + PostgreSQL) et `pnpm dev` (frontend).
- Les services Render et Vercel sont mis en pause.
- La **CI** (tests et build sur chaque PR) est conservée : elle ne déploie rien.
- La mise en production se fera plus tard sur un vrai serveur, préparée en Phase 6 de la roadmap.

## Conséquences

- Pas d'URL publique à montrer. Les démonstrations se font en local.
- La checklist de production de [SECURITY.md](../SECURITY.md) reste valable pour le futur serveur.
- Les vulnérabilités de dépendances restent suivies (Dependabot), mais sans urgence d'exposition publique.
