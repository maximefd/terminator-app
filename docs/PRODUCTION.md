# 🚀 Production — Le Fléchoir

> Le runbook du site en ligne : préparer le serveur, déployer, revenir en arrière, restaurer, changer un secret.
> Décisions : [ADR 0013](adr/0013-cible-hebergement-production.md) (VPS derrière Cloudflare), [ADR 0019](adr/0019-deploiement.md) (déploiement). Les sauvegardes planifiées vers R2 (#120) compléteront ce document.

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
  2. nom d'hôte public `api.leflechoir.fr` → service `http://api:5000` ;
  3. le jeton va dans `CLOUDFLARE_TUNNEL_TOKEN`.
- **Le projet Pages**, créé depuis le Mac. La première commande ouvre le navigateur pour autoriser l'accès, une seule fois :

  ```bash
  pnpm dlx wrangler@4.140.0 login
  pnpm dlx wrangler@4.140.0 pages project create leflechoir --production-branch main
  ```
  Puis, dans Pages → `leflechoir` → *Custom domains* :
  - ajouter `leflechoir.fr` et `www.leflechoir.fr` ;
  - faire rediriger `www` vers `leflechoir.fr`, avec une règle de redirection (*Rules → Redirect Rules*).
- **Les réglages de la zone** (#111) :
  - robots des moteurs de recherche et de réponse IA autorisés (*AI Crawl Control*) ;
  - Bot Fight Mode coupé pour `api.` : ses défis cassent les appels du site ;
  - Web Analytics de Pages coupé : la CSP bloquerait son script.

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

## Vérifié le 25/09/2026

Sur une machine de test, avec Docker et une configuration factice :
- **Le compose de production** (#117) :
  - les trois conteneurs démarrent, sans port publié ;
  - l'API tourne en uid 10001 et ne peut pas écrire dans son code ;
  - migrations jouées ;
  - événements d'usage sans adresse IP ;
  - journal d'accès en JSON.
- **Le déploiement**, sur un serveur simulé (`LEFLECHOIR_BASE`) :
  - premier déploiement : 53 s ;
  - deuxième, précédé d'une sauvegarde : 25 s ;
  - version cassée : détectée, puis retour automatique à la précédente en 39 s ;
  - `rollback` manuel ;
  - ménage des anciennes versions et de leurs images.

## Reste à faire

- **Le lexique curé livré** (#118) : sans lui, l'API se rabat sur le DELA complet de l'image (`/api/status` : `curated: false`).
- **Les sauvegardes nocturnes vers R2** (#120), et la restauration vérifiée chaque mois.
- **Le premier vrai déploiement** et un retour arrière, joués de bout en bout sur le VPS (#119).
