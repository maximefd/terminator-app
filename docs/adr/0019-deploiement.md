# 0019 — Déploiement : un commit envoyé par SSH et construit sur le serveur, le site envoyé à Pages

- Statut : acceptée
- Date : 2026-09-25

## Contexte

- L'API tourne sur un VPS, dans `docker-compose.prod.yml` ([ADR 0013](0013-cible-hebergement-production.md), #117). Le site est un export statique, servi par Cloudflare Pages.
- **Un seul auteur déploie**, rarement, depuis son Mac. Le Mac est en arm64, le VPS en amd64.
- **Le dépôt deviendra privé** à l'ouverture.
- **Aucun budget supplémentaire** : pas de registre d'images payant, et les minutes d'Actions d'un dépôt privé sont comptées.
- **Deux exigences** : ne jamais laisser une version cassée en service, et pouvoir revenir en arrière en une commande.

## Décision

1. **On déploie un commit de `main`, jamais un dossier de travail.** `make deploy` refuse :
   - des modifications non commitées ;
   - un commit absent de `origin/main`, sauf essai explicite (`DEPLOY_ANY_COMMIT=1`).
2. **L'API : le code du commit part par SSH et le serveur construit l'image sur place.**
   - Concrètement : `git archive | ssh … tar -x` dans `releases/<commit>/`.
   - Ni registre d'images, ni accès du serveur à GitHub, donc aucune clé de déploiement pour le dépôt privé.
   - Pas de construction croisée arm64 → amd64 sur le Mac.
3. **Le serveur vérifie avant de basculer** (`tools/deploy/server.sh`). Les étapes, dans l'ordre :
   1. sauvegarde de la base ;
   2. construction de l'image ;
   3. démarrage, en attendant l'état « healthy » ;
   4. test de fumée sur `/api/status` : l'API, sa base, le lexique.

   Si l'une échoue, **retour automatique à la version précédente**. `current` et `previous` désignent les deux dernières versions, et `make rollback` passe de l'une à l'autre. Quatre versions sont gardées, avec leurs images.
4. **Les migrations sont additives.** Une version doit fonctionner avec le schéma de la suivante :
   - on ajoute des tables et des colonnes ;
   - on n'en retire ni n'en renomme dans le même déploiement ;
   - une suppression se fait en deux déploiements : le code cesse de s'en servir, puis la migration la retire.

   Un retour arrière n'a donc jamais à redescendre le schéma. Sinon, la sauvegarde faite juste avant le déploiement répare.
5. **Le site est construit sur le Mac, à partir du même commit, puis envoyé à Cloudflare Pages.**
   - La construction se fait dans un dossier temporaire, jamais dans `frontend/`.
   - L'envoi passe par « Direct Upload » (`wrangler pages deploy`).
   - Le site part toujours **après** l'API : il ne part jamais avant l'API qu'il appelle.
   - Chaque déploiement de Pages reste disponible : le retour arrière du site se fait depuis le tableau de bord.
6. **Une coupure brève est acceptée.** Au redémarrage, l'API est indisponible le temps de charger le lexique, de l'ordre d'une minute : on déploie aux heures creuses. Une bascule sans coupure (deux API côte à côte, puis un changement d'aiguillage) attendra la [Phase 7](../ROADMAP.md).

## Conséquences

- ✅ Un seul geste, `make deploy`, et le code en service se retrouve dans l'historique : la version est le commit, reprise dans `RELEASE`, Sentry et le nom de l'image.
- ✅ Une version qui ne démarre pas ne reste jamais en service.
- ✅ Le serveur n'a ni accès à GitHub, ni la clé privée des sauvegardes.
- `/api/status` vérifie aussi la base : il répond 503 si elle est injoignable, pour le test de fumée et la surveillance.
- `wrangler` n'est pas une dépendance du projet : il pèserait sur chaque installation de la CI. Il est lancé par `pnpm dlx`, à une version figée dans `tools/deploy/deploy.sh`.
- **Essayé le 25/09/2026** sur un serveur simulé, avec Docker :
  - premier déploiement : 53 s ;
  - deuxième déploiement, précédé d'une sauvegarde : 25 s ;
  - version cassée : retour automatique en 39 s ;
  - retour arrière manuel ;
  - ménage des anciennes versions.
- **Options écartées :**
  - **une image construite par GitHub Actions et publiée sur GHCR**, puis tirée par le serveur : un registre et des jetons de plus, et des minutes d'Actions comptées une fois le dépôt privé ;
  - **une image construite sur le Mac puis envoyée** (`docker save | ssh docker load`) : construction croisée arm64 → amd64, lente et source d'écarts ;
  - **un `git pull` sur le serveur** : une clé de déploiement sur le serveur, et le code en service dépendrait de l'état de GitHub à cet instant ;
  - **l'intégration Git de Cloudflare Pages** : chaque fusion sur `main` publierait le site aussitôt, avant que l'API qu'il appelle soit déployée, et Cloudflare lirait le dépôt privé.
