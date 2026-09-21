# 0010 — Le schéma de la base évolue par migrations Alembic

- Statut : acceptée
- Date : 2026-09-21

## Contexte

Depuis le début, la base est fabriquée par `db.create_all()` au démarrage de l'API. C'est commode
et c'est ce qui a permis d'avancer vite : les trois tables (`user`, `dictionary`, `personal_word`)
n'ont jamais changé de forme.

`create_all` ne sait faire qu'une chose : **créer les tables manquantes**. Il ne renomme rien,
ne change aucun type, n'ajoute aucune colonne à une table existante, et ne prévient pas quand le
modèle Python et la base ont divergé. Tant qu'aucune donnée ne compte, on efface et on recommence.
Ce n'est plus le cas : la curation du lexique et les dictionnaires personnels représentent des
heures de travail, et les grilles conservées ([#24](https://github.com/maximefd/terminator-app/issues/24))
sont précisément des données que l'auteur veut retrouver.

La Phase 6 prévoit « migrations au déploiement » ; il aurait fallu introduire l'outil à ce
moment-là, sur une base contenant déjà des données et sans historique pour la décrire.

## Décision

**Flask-Migrate (Alembic) devient la source de vérité du schéma.** Toute évolution du modèle
s'accompagne d'une révision dans `backend/migrations/versions/`.

Deux révisions existent :

- `0001_schema_initial` décrit la base **telle qu'elle était avant Alembic**. Elle n'est
  quasiment jamais exécutée : elle sert de point d'ancrage.
- `0002_grilles_conservees` ajoute `saved_grid`.

Au démarrage, `app.prepare_database()` :

1. en mode test, appelle `db.create_all()` — la base SQLite en mémoire est recréée à chaque
   session, y jouer les migrations coûterait du temps sans rien vérifier de plus ;
2. sur une base **existante sans table `alembic_version`** (celle d'un poste de développement
   créée par `create_all`), marque `0001_schema_initial` comme appliquée plutôt que de la rejouer
   sur des tables déjà là ;
3. applique les révisions en attente.

Le point 3 est piloté par `AUTO_MIGRATE`, vrai par défaut. Le jour où un déploiement existera, il
jouera `flask db upgrade` avant de lancer l'application, et ce réglage passera à faux : appliquer
des migrations depuis plusieurs processus qui démarrent en même temps est une mauvaise idée.

## Conséquences

- **Une migration doit laisser écrire le code d'avant.** Entre le moment où elle passe et celui où le
  nouveau code tourne, l'ancien continue d'insérer des lignes : une colonne `NOT NULL` sans valeur par
  défaut **côté base** lui devient impossible à écrire. C'est arrivé avec `saved_grid.definitions` —
  conserver une grille répondait 500, et le message ne disait rien du schéma. Toute colonne non nulle
  ajoutée à une table déjà utilisée porte donc un `server_default`.
- Ajouter une colonne demande désormais une révision. `flask db migrate -m "..."` la rédige, et
  **il faut la relire** : l'auto-détection ignore les renommages et les voit comme une colonne
  supprimée et une autre créée, ce qui perdrait les données.
- L'absence de `migrations/` n'empêche plus l'API de démarrer : elle prévient dans le journal et
  laisse le schéma en l'état. Un dossier oublié ne doit pas ressembler à une panne de base.
- `db.create_all()` ne subsiste que pour les tests. Un modèle ajouté sans migration passera donc
  les tests et échouera en développement — l'ordre inverse serait pire (une migration jamais
  exercée), mais c'est un piège à connaître.
- Les révisions portent des identifiants lisibles (`0001_schema_initial`) plutôt que les
  empreintes aléatoires d'Alembic : elles se citent dans le code et dans les discussions.
