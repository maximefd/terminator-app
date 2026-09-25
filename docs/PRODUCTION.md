# 🚀 Production — Le Fléchoir

> Le runbook du site en ligne : préparer le serveur, déployer, revenir en arrière, restaurer, changer un secret.
> Décisions : [ADR 0013](adr/0013-cible-hebergement-production.md) (VPS derrière Cloudflare), [ADR 0019](adr/0019-deploiement.md) (déploiement).

## Ce qui tourne

**Le site** (`leflechoir.fr`) est un export statique sur Cloudflare Pages. **L'API** (`api.leflechoir.fr`) tourne sur un VPS OVH (VPS-1, Ubuntu 24.04, Gravelines), dans `docker-compose.prod.yml`. Ce fichier lance trois conteneurs, sans aucun port publié sur le serveur :

| Service | Rôle |
|---------|------|
| `db` | PostgreSQL 15, données dans le volume `pgdata`, joignable seulement par l'API |
| `api` | L'image de `backend/` sous gunicorn (3 workers, 2 générations à la fois), en utilisateur sans droits ; les migrations se jouent au démarrage |
| `cloudflared` | Le tunnel : une connexion **sortante** vers Cloudflare, par laquelle arrivent les requêtes de `api.leflechoir.fr` |

Le pare-feu refuse donc tout en entrée, sauf SSH. C'est aussi ce qui rend `CF-Connecting-IP` digne de confiance : personne d'autre que Cloudflare ne peut joindre l'API.

Sur le serveur, tout vit dans `/opt/leflechoir` :

```text
/opt/leflechoir/
├── .env.production        la configuration (modèle : .env.production.example) — chmod 600
├── releases/<commit>/     le code de chaque version déployée ; quatre sont gardées
├── current → releases/…   la version en service
├── previous → releases/…  la précédente, pour revenir en arrière
├── backups/               les sauvegardes de la base, dont celle d'avant chaque déploiement
└── lexicon/               le lexique curé (#118)
```

## Première mise en ligne, dans l'ordre

Les sections suivantes détaillent chaque geste. 👤 marque ce qui demande l'auteur : un tableau de bord ou une autorisation dans le navigateur. Tout le reste se fait en ligne de commande, depuis le Mac.

> Faite le 25/09/2026 : voir « Mis en ligne le 25/09/2026 », plus bas.

1. **Le serveur** : « Préparer le serveur », étapes 1 à 7. La configuration se crée sur le serveur, à partir de `.env.production.example`, et les secrets internes (`POSTGRES_PASSWORD`, `SECRET_KEY`, `JWT_SECRET_KEY`) y sont **tirés au hasard sur place** : ils ne transitent nulle part.
2. 👤 **Les secrets des tableaux de bord**, recopiés dans un fichier du Mac hors du dépôt (`~/leflechoir-secrets.env`, `chmod 600`), au format `CLE=valeur` :
   - `CLOUDFLARE_TUNNEL_TOKEN` : « Préparer Cloudflare », le tunnel ;
   - `SMTP_USER` et `SMTP_PASSWORD` : Brevo → *SMTP & API* → *SMTP* → générer une clé SMTP ;
   - `SENTRY_DSN` : le DSN du projet Sentry `leflechoir-api` ;
   - `R2_ENDPOINT`, `R2_ACCESS_KEY_ID` et `R2_SECRET_ACCESS_KEY` : « Préparer les sauvegardes », étape 2.

   Ce fichier part sur le serveur par `scp` et se fond dans `.env.production`. On ne l'affiche jamais, et on ne le commite jamais.
3. **Les sauvegardes** : la paire de clés `age` sur le Mac (étape 1), et `BACKUP_AGE_RECIPIENT` dans `.env.production`.
4. 👤 **Pages** : `pnpm dlx wrangler@4.140.0 login` ouvre le navigateur une fois. Ensuite, `pages project create leflechoir --production-branch main`.
5. **Le premier déploiement, et l'essai du retour arrière sur le vrai serveur.**
   1. Depuis un `git worktree` d'un commit plus ancien de `main` qui contient déjà `tools/deploy` (par exemple `c9b2d56`), lancer `DEPLOY_HOST=… tools/deploy/deploy.sh api`.
   2. Puis `make deploy` depuis `main` : l'API et le site. La version précédente est alors l'ancienne.
   3. `make rollback` : l'ancienne revient en service. `make rollback` une seconde fois : la dernière revient.
6. 👤 **Le domaine du site** : Pages → `leflechoir` → *Custom domains* → `leflechoir.fr` et `www.leflechoir.fr`, puis la redirection de `www` et les réglages de la zone (« Préparer Cloudflare »).
7. **Le lexique** : `make deploy-lexicon`, puis `make deploy-status`, qui doit indiquer un lexique curé.
8. **La sauvegarde de la nuit** : un premier `backup-offsite.sh` à la main, puis la tâche cron. Récupérer ensuite la sauvegarde depuis R2 et la vérifier avec `make db-restore-check`.
9. **Les vérifications finales :**
   - `https://api.leflechoir.fr/api/status` répond `"database":"ok"` ;
   - `https://leflechoir.fr` affiche le site, et une recherche y fonctionne ;
   - une inscription de test avec une adresse de l'auteur reçoit l'e-mail de confirmation (Brevo). Les liens y pointent-ils vers `leflechoir.fr` ou vers `mail.leflechoir.fr` (suivi des clics, #111) ? Puis on supprime ce compte de test ;
   - `make deploy-status` affiche les versions, le lexique et la dernière sauvegarde.

## Préparer le serveur (une fois)

Le VPS est livré avec l'utilisateur `ubuntu` et ta clé SSH. Depuis le Mac : `ssh ubuntu@ADRESSE`.

1. **Mises à jour et paquets.** Les paquets d'Ubuntu, et non ceux de docker.com, reçoivent les mises à jour de sécurité automatiques :

   ```bash
   sudo apt update && sudo apt full-upgrade -y
   sudo apt install -y docker.io docker-compose-v2 age rclone ufw unattended-upgrades
   sudo usermod -aG docker ubuntu     # puis se déconnecter et se reconnecter
   ```
2. **Un fichier d'échange de 2 Go.** Il évite qu'une construction d'image ou un pic de mémoire ne tue l'API sur 4 Go :

   ```bash
   sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```
3. **SSH par clé seulement.** Le fichier s'appelle `00-…` parce que la **première** valeur lue l'emporte : l'image d'OVH en pose une autre dans `50-cloud-init.conf`.

   ```bash
   printf 'PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin no\n' \
     | sudo tee /etc/ssh/sshd_config.d/00-leflechoir.conf
   sudo sshd -t && sudo systemctl restart ssh
   sudo sshd -T | grep -E '^(passwordauthentication|permitrootlogin)'   # « no » et « no »
   ```
   **Garde cette session ouverte** et vérifie dans un autre terminal que `ssh ubuntu@ADRESSE` fonctionne encore avant de la fermer.
4. **Pare-feu : tout refuser en entrée, sauf SSH.** Docker ne publie aucun port, il ne contourne donc pas le pare-feu :

   ```bash
   sudo ufw default deny incoming && sudo ufw default allow outgoing && sudo ufw allow OpenSSH && sudo ufw --force enable
   ```
5. **Mises à jour de sécurité automatiques**, avec redémarrage la nuit si un correctif l'exige. Les conteneurs repartent seuls (`restart: unless-stopped`) :

   ```bash
   printf 'Unattended-Upgrade::Automatic-Reboot "true";\nUnattended-Upgrade::Automatic-Reboot-Time "04:30";\n' \
     | sudo tee /etc/apt/apt.conf.d/52leflechoir
   ```
6. **Journaux effacés au bout de 14 jours.** Le journal d'accès contient l'adresse IP des visiteurs, et la page de confidentialité annonce 14 jours :

   ```bash
   sudo mkdir -p /etc/systemd/journald.conf.d
   printf '[Journal]\nMaxRetentionSec=14day\nSystemMaxUse=1G\n' | sudo tee /etc/systemd/journald.conf.d/retention.conf
   sudo systemctl restart systemd-journald
   ```
7. **Le dossier et la configuration**, en recopiant le modèle `.env.production.example` du dépôt :

   ```bash
   sudo mkdir -p /opt/leflechoir/lexicon && sudo chown -R ubuntu:ubuntu /opt/leflechoir
   nano /opt/leflechoir/.env.production    # coller le modèle, puis remplir
   chmod 600 /opt/leflechoir/.env.production
   ```
   Pour générer un secret : `python3 -c "import secrets; print(secrets.token_hex(32))"`.

## Préparer Cloudflare (une fois)

- **Le tunnel** :
  1. Zero Trust → Networks → Tunnels → *Create a tunnel* (type *Cloudflared*) ;
  2. le jeton va dans `CLOUDFLARE_TUNNEL_TOKEN` : c'est la longue suite `eyJ…` de la commande d'installation affichée, sans rien installer ;
  3. le tunnel → onglet *Published application routes* (anciennement *Public hostname*) → *Add a published application route* : sous-domaine `api`, domaine `leflechoir.fr`, type `HTTP`, URL `api:5000`. Cloudflare crée lui-même l'enregistrement DNS.
- **Le projet Pages**, créé depuis le Mac. La première commande ouvre le navigateur pour autoriser l'accès, une seule fois :

  ```bash
  pnpm dlx wrangler@4.140.0 login
  pnpm dlx wrangler@4.140.0 pages project create leflechoir --production-branch main
  ```
  Puis, dans Pages → `leflechoir` → *Custom domains* :
  - ajouter `leflechoir.fr` et `www.leflechoir.fr` ;
  - faire rediriger `www` vers `leflechoir.fr`, avec une règle de redirection (*Rules → Redirect Rules*, modèle *Redirect from WWW to root*) ;
  - si `leflechoir.fr` affiche encore « Site en construction », la page d'attente d'OVH : supprimer d'abord, dans Cloudflare → *DNS* → *Records*, les `A` et `AAAA` de `leflechoir.fr` et de `www` repris d'OVH. Garder les `MX` (Email Routing), les `TXT`, les `CNAME` de Brevo (`brevo1._domainkey`, `brevo2._domainkey`, `mail`) et `api`.
- **Les réglages de la zone** (#111) :
  - robots des moteurs de recherche et de réponse IA autorisés (*AI Crawl Control*) ;
  - Bot Fight Mode coupé pour `api.` : ses défis cassent les appels du site ;
  - Web Analytics de Pages coupé : la CSP bloquerait son script ;
  - *Always Use HTTPS* (*SSL/TLS → Edge Certificates*) : Pages redirige seul, mais sans ce réglage `api.` répond aussi en HTTP simple.

## Préparer les sauvegardes (une fois)

Chaque nuit, `tools/db/backup-offsite.sh` fait un dump de la base, **chiffré** pour une clé publique `age`, puis le copie sur Cloudflare R2, vérifie la copie et note la réussite. Le serveur n'a que la clé publique : il chiffre ses sauvegardes sans pouvoir les relire.

1. **La paire de clés, sur le Mac** (`brew install age`). La clé privée ne va **jamais** sur le serveur ; garde-la aussi dans ton gestionnaire de mots de passe, car sans elle aucune sauvegarde ne se relit :

   ```bash
   age-keygen -o ~/leflechoir-sauvegardes.key     # affiche la clé publique : age1…
   ```
   Dans le `.env` du Mac, avec le chemin complet (le `~` n'y est pas compris) : `BACKUP_AGE_IDENTITY=/Users/TON_NOM/leflechoir-sauvegardes.key`, pour `make db-restore-check`.
2. **Le seau R2**, dans Cloudflare → R2 (à activer une fois : une carte est demandée, l'offre gratuite suffit) :
   - créer le seau `leflechoir-sauvegardes`, avec la **juridiction « European Union »**. Le registre annonce des sauvegardes dans l'UE, et ce choix ne se change plus ;
   - dans le seau → *Settings* → *Object lifecycle rules* : supprimer les objets **après 30 jours** ;
   - ces deux gestes se font aussi depuis le Mac, wrangler autorisé : `pnpm dlx --allow-build=esbuild --allow-build=workerd wrangler@4.140.0 r2 bucket create leflechoir-sauvegardes --jurisdiction eu`, puis `… r2 bucket lifecycle add leflechoir-sauvegardes expire-30j --expire-days 30 --jurisdiction eu` ;
   - R2 → *Manage API tokens* → créer un jeton *Object Read & Write* limité à ce seau. Noter l'identifiant et le secret, et l'adresse S3 du compte, en `https://<compte>.eu.r2.cloudflarestorage.com` pour un seau européen.
3. **Dans `.env.production`** : `BACKUP_AGE_RECIPIENT` (la clé publique), `R2_ENDPOINT`, `R2_BUCKET`, `R2_ACCESS_KEY_ID` et `R2_SECRET_ACCESS_KEY`.
4. **Un premier essai**, puis la tâche de la nuit, à 3 h 30 UTC, avant les mises à jour de 4 h 30 :

   ```bash
   sh /opt/leflechoir/current/tools/db/backup-offsite.sh      # « Sauvegarde copiée sur R2 : … »
   ( crontab -l 2>/dev/null; echo '30 3 * * * sh /opt/leflechoir/current/tools/db/backup-offsite.sh 2>&1 | systemd-cat -t leflechoir-sauvegarde' ) | crontab -
   ```
   Le journal se lit avec `journalctl -t leflechoir-sauvegarde`, et `make deploy-status` affiche la dernière réussite.
5. **Être prévenu si une nuit échoue** (facultatif) : un contrôle gratuit sur [Healthchecks.io](https://healthchecks.io), ou un moniteur de tâche de Sentry, dont l'adresse va dans `BACKUP_PING_URL`. Le script l'appelle après chaque réussite, et le service envoie un e-mail si l'appel ne vient plus.

## Préparer le Mac (une fois)

Dans le `.env` du dépôt (jamais versionné) :

```bash
DEPLOY_HOST=ubuntu@ADRESSE_DU_VPS
# Suivi des erreurs du site (projet Sentry « leflechoir-web ») : facultatif
NEXT_PUBLIC_SENTRY_DSN=
```

## Déployer

```bash
git checkout main && git pull
make deploy            # l'API, puis le site ; make deploy-api ou make deploy-front pour l'un des deux
```

`make deploy` refuse des modifications non commitées et un commit absent de `origin/main`. Ensuite :

1. **L'API.** Le code du commit part sur le serveur (`releases/<commit>/`). Le serveur fait alors, dans l'ordre :
   - une sauvegarde de la base ;
   - la construction de l'image ;
   - le démarrage, en attendant que l'API soit « healthy » ;
   - la vérification de `/api/status` (l'API, sa base, le lexique).

   Au moindre échec, il **revient seul à la version précédente** et le montre dans le journal. Le Mac vérifie enfin l'API par le tunnel, avec `https://api.leflechoir.fr/api/status`.
2. **Le site.** Il est construit à partir du même commit, dans un dossier temporaire, puis envoyé à Pages.

Compter quelques minutes. L'API est coupée environ une minute, le temps de charger le lexique : déployer aux heures creuses.

**Les migrations sont additives** ([ADR 0019](adr/0019-deploiement.md)) : on ne retire ni ne renomme une colonne dans le même déploiement que le code qui cesse de s'en servir.

## Publier le lexique

L'API lit le lexique curé que le curateur exporte sur le Mac (`data/lexicon/build/lexique_cure.csv`, réécrit tous les 500 mots triés). C'est le lexique de lancement : le même que celui du site local, filtre « aucun » (#118). Sans lui, le serveur se rabat sur le DELA complet, avec ses formes rares.

```bash
make deploy-lexicon
```

La commande :
- envoie le fichier **sans la colonne des définitions** : elles viennent du Wiktionnaire (CC BY-SA), le site ne les sert pas, elles restent donc sur le Mac ;
- fait vérifier son empreinte par le serveur, puis redémarre l'API (environ une minute de coupure) ;
- s'assure que l'API a bien chargé le lexique curé, avec plus de 50 000 mots ;
- remet le lexique précédent en service si ce n'est pas le cas.

À relancer après une séance de curation pour publier ses progrès, de préférence aux heures creuses. `make deploy-status` affiche la date du lexique en service.

## En cas de problème

| Situation | Geste |
|-----------|-------|
| La nouvelle version se comporte mal | `make rollback` : l'API revient à la version précédente, et `make rollback` à nouveau y retourne |
| Le site se comporte mal | Pages → `leflechoir` → *Deployments* → le déploiement d'avant → *Rollback* |
| Voir les versions en service | `make deploy-status` |
| Voir ce qui se passe | `ssh` sur le serveur, puis `$C logs -f api` (voir « Au quotidien ») |

### Restaurer une sauvegarde

Les sauvegardes sont chiffrées pour la clé publique `age`, et **la clé privée n'est pas sur le serveur**. Le déchiffrement se fait donc sur le Mac, et le contenu repart directement dans la base :

```bash
# Sur le Mac : récupérer la sauvegarde, et d'abord vérifier qu'elle se restaure (base jetable, en local)
scp ubuntu@ADRESSE:/opt/leflechoir/backups/terminator-AAAAMMJJ-HHMMSS.dump.age .
make db-restore-check FILE=terminator-AAAAMMJJ-HHMMSS.dump.age

# Puis la restaurer en production : l'API est arrêtée pendant l'opération
ssh ubuntu@ADRESSE 'docker stop leflechoir-api-1'
age -d -i ~/CHEMIN/leflechoir-sauvegardes.key terminator-AAAAMMJJ-HHMMSS.dump.age \
  | ssh ubuntu@ADRESSE 'docker exec -i leflechoir-db-1 sh -c "pg_restore -U \$POSTGRES_USER -d \$POSTGRES_DB --clean --if-exists --no-owner"'
ssh ubuntu@ADRESSE 'docker start leflechoir-api-1'
```

À répéter une fois pour de vrai avant l'ouverture (6g) : une sauvegarde jamais restaurée n'est pas une sauvegarde.

### Vérifier une sauvegarde, chaque mois

1. Télécharger la sauvegarde de la nuit depuis le seau R2 (tableau de bord Cloudflare → R2 → `leflechoir-sauvegardes`). Ou depuis le Mac, avec le nom que donne `make deploy-status` :

   ```bash
   pnpm dlx --allow-build=esbuild --allow-build=workerd wrangler@4.140.0 r2 object get leflechoir-sauvegardes/terminator-AAAAMMJJ-HHMMSS.dump.age \
     --file ~/Downloads/terminator-AAAAMMJJ-HHMMSS.dump.age --jurisdiction eu --remote
   ```
2. Sur le Mac, avec l'API de développement démarrée (`make dev-api`) :

   ```bash
   make db-restore-check FILE=~/Downloads/terminator-AAAAMMJJ-HHMMSS.dump.age
   ```
   La sauvegarde est restaurée dans une base jetable, qui est comptée puis supprimée. La base de développement n'est pas touchée.

### Changer un secret

1. Modifier `/opt/leflechoir/.env.production` sur le serveur.
2. `make deploy-api` : même sans nouveau code, l'API redémarre avec la nouvelle valeur.

Selon le secret changé :
- **`SECRET_KEY` ou `JWT_SECRET_KEY`** : tout le monde est déconnecté, et les liens déjà envoyés par e-mail (confirmation, mot de passe) ne marchent plus. C'est le but si une clé a fuité.
- **`POSTGRES_PASSWORD`** : il faut d'abord changer le mot de passe dans la base, avec `docker exec -it leflechoir-db-1 psql -U leflechoir -c "ALTER USER leflechoir PASSWORD '…'"`, puis dans le fichier.
- **Le jeton du tunnel** : Cloudflare → le tunnel → *Refresh token*, puis `make deploy-api`.

## Au quotidien

Sur le serveur, avec :

```bash
C="docker compose -p leflechoir -f /opt/leflechoir/current/docker-compose.prod.yml --env-file /opt/leflechoir/.env.production"
```

| Besoin | Commande |
|--------|----------|
| Mesure d'usage ([ADR 0016](adr/0016-mesure-d-usage-sans-cookie.md)) | `$C exec -e LEXICON_LOAD=0 api flask stats` |
| Journaux de l'API | `$C logs -f api` (JSON, une ligne par requête) |
| État | `$C ps` |

## Surveillance

- **Sentry**, dans l'Union européenne :
  - projet `leflechoir-api` → `SENTRY_DSN` dans `.env.production` ;
  - projet `leflechoir-web` → `NEXT_PUBLIC_SENTRY_DSN` dans le `.env` du Mac.

  Dans l'organisation, activer *Prevent Storing of IP Addresses*.
- **UptimeRobot**, en offre gratuite :
  - un moniteur « Keyword » sur `https://api.leflechoir.fr/api/status`, qui attend `"database":"ok"` ;
  - un moniteur HTTP sur `https://leflechoir.fr`.

  Alertes par e-mail.

## Mis en ligne le 25/09/2026

Sur le vrai serveur (OVH VPS-1), en suivant « Première mise en ligne, dans l'ordre » :
- **Le serveur** : mots de passe SSH refusés (essayé depuis une seconde connexion), seul le port 22 ouvert de l'extérieur, mises à jour automatiques, journald à 14 jours.
- **Le déploiement** : une première version depuis `c9b2d56`, puis `8750a5b` par `make deploy-api`, avec une sauvegarde chiffrée juste avant. `make rollback`, deux fois : 38 s à chaque fois, et l'API répondait par le tunnel après chacun.
- **Le lexique curé** (`make deploy-lexicon`) : 692 516 mots, en 42 s, sans la colonne des définitions sur le serveur. L'API occupe alors 770 Mo, sur 4 Go.
- **Les sauvegardes** :
  - copiées sur R2 (seau en juridiction UE, règle de 30 jours) ;
  - la tâche de la nuit essayée dans l'environnement de cron ;
  - une sauvegarde contenant un compte, récupérée depuis R2, déchiffrée sur le Mac et restaurée par `make db-restore-check` : le compte y était.
- **Le site**, sur `leflechoir.fr` :
  - `www` et `http` redirigent en 301 ;
  - les en-têtes de sécurité sont servis, et la console du navigateur est vide ;
  - recherche et génération (une grille 6×7 en 0,4 s, aller-retour compris) ;
  - CORS limité à `https://leflechoir.fr`.
- **Un compte de test** : inscription, e-mail de confirmation reçu par Brevo, lien suivi, puis compte supprimé. Les événements d'usage portent le pays, jamais l'adresse IP.
- **Écarts trouvés en route** :
  - `pnpm dlx wrangler` refusé par pnpm 12, et projet Pages créé sur Workers sans `--force` (#160) ;
  - la copie sur R2 qui ne réussissait qu'au second essai de rclone (#161) ;
  - les requêtes préliminaires CORS comptées comme des recherches et des générations (#162).
- **À savoir** : juste après la création de `api.leflechoir.fr`, le Mac garde en cache la réponse « domaine inconnu », jusqu'à 30 minutes. `make deploy` échoue alors à sa dernière vérification, alors que le serveur est à jour. Vérifier avec `dig +short @1.1.1.1 api.leflechoir.fr`, puis `curl --resolve api.leflechoir.fr:443:ADRESSE https://api.leflechoir.fr/api/status`.

## Vérifié sur une machine de test, le 25/09/2026

Sur une machine de test, avec Docker et une configuration factice :
- **Le compose de production** (#117) :
  - les trois conteneurs démarrent, sans port publié ;
  - l'API tourne en uid 10001 et ne peut pas écrire dans son code ;
  - migrations jouées ;
  - événements d'usage sans adresse IP ;
  - journal d'accès en JSON.
- **Les sauvegardes** : sur un PostgreSQL nommé comme en production, avec un stockage compatible S3 à la place de R2 et une vraie paire de clés `age`, les étapes suivantes ont été vérifiées :
  - dump chiffré ;
  - copie et vérification de sa taille ;
  - trace de réussite ;
  - rattrapage d'une nuit ratée ;
  - restauration depuis la copie distante, avec les 1 000 lignes retrouvées ;
  - refus d'envoyer quoi que ce soit sans clé publique.
- **Le lexique** (`make deploy-lexicon`), du Mac jusqu'à un serveur simulé :
  - lexique valide : en service, sans la colonne des définitions ;
  - lexique tronqué (10 lignes) : refusé, le précédent reprend sa place, code de sortie 1 ;
  - second lexique valide : en service, avec le précédent gardé.
- **Le déploiement**, sur un serveur simulé (`LEFLECHOIR_BASE`) :
  - premier déploiement : 53 s ;
  - deuxième, précédé d'une sauvegarde : 25 s ;
  - version cassée : détectée, puis retour automatique à la précédente en 39 s ;
  - `rollback` manuel ;
  - ménage des anciennes versions et de leurs images.

## Reste à faire

- ***Always Use HTTPS*** dans la zone : le dernier point de la checklist de [SECURITY.md](SECURITY.md).
- **UptimeRobot** : les deux moniteurs (« Surveillance »).
- **Sentry** : *Prevent Storing of IP Addresses* dans l'organisation, que la page de confidentialité promet.
- **Les liens des e-mails du compte** : s'ils passent par `mail.leflechoir.fr` (suivi des clics de Brevo), couper ce suivi, car les jetons de confirmation et de mot de passe transiteraient par Brevo.
- **Search Console et Bing Webmaster**, sitemap soumis (Phase 6g).
- **La première semaine** : `backend/benchmarks/load_profile.py` sur le VPS, puis les seuils de l'[ADR 0013](adr/0013-cible-hebergement-production.md).
- **#111** : un message de test à `contact@` ; le double facteur sur Cloudflare, OVH, GitHub, Brevo et Sentry.
- **Le dépôt privé** ([ADR 0013](adr/0013-cible-hebergement-production.md)) : à décider maintenant que le site est en ligne.
