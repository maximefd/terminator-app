# 🚀 Production — Le Fléchoir

> Comment l'API tourne sur le VPS ([ADR 0013](adr/0013-cible-hebergement-production.md)). Le site lui-même est un export statique servi par Cloudflare Pages. Document vivant : le déploiement (#119) et les sauvegardes (#120) le compléteront pour en faire le runbook.

## Ce qui tourne

`docker-compose.prod.yml` lance trois conteneurs, sans aucun port publié sur le serveur :

| Service | Rôle |
|---------|------|
| `db` | PostgreSQL 15, données dans le volume `pgdata`, joignable seulement par l'API |
| `api` | L'image de `backend/` sous gunicorn (3 workers, 2 générations à la fois), en utilisateur sans droits ; les migrations se jouent au démarrage |
| `cloudflared` | Le tunnel : une connexion **sortante** vers Cloudflare, par laquelle arrivent les requêtes de `api.leflechoir.fr` |

Le pare-feu du VPS peut donc tout refuser en entrée, sauf SSH. C'est aussi ce qui rend `CF-Connecting-IP` digne de confiance : personne d'autre que Cloudflare ne peut joindre l'API.

## Première mise en route

1. **Le tunnel** : Cloudflare → Zero Trust → Networks → Tunnels → *Create a tunnel* (type *Cloudflared*). Nom d'hôte public `api.leflechoir.fr` → service `http://api:5000`. Garder le jeton.
2. **La rétention des journaux** : les journaux des conteneurs partent dans journald. Le journal d'accès contient l'adresse IP des visiteurs, et la page de confidentialité annonce 14 jours :

   ```bash
   sudo mkdir -p /etc/systemd/journald.conf.d
   printf '[Journal]\nMaxRetentionSec=14day\nSystemMaxUse=1G\n' | sudo tee /etc/systemd/journald.conf.d/retention.conf
   sudo systemctl restart systemd-journald
   ```
3. **La configuration** :

   ```bash
   cp .env.production.example .env.production
   chmod 600 .env.production
   # remplir : secrets (python3 -c "import secrets; print(secrets.token_hex(32))"), Brevo, jeton du tunnel, Sentry
   ```
4. **Le démarrage** :

   ```bash
   docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
   docker compose -f docker-compose.prod.yml --env-file .env.production ps   # api « healthy »
   curl https://api.leflechoir.fr/api/status
   ```

## Au quotidien

Avec `C="docker compose -f docker-compose.prod.yml --env-file .env.production"` :

| Besoin | Commande |
|--------|----------|
| Mesure d'usage ([ADR 0016](adr/0016-mesure-d-usage-sans-cookie.md)) | `$C exec -e LEXICON_LOAD=0 api flask stats` |
| Journaux de l'API | `$C logs -f api` (JSON, une ligne par requête) |
| État | `$C ps` |
| Redémarrer l'API | `$C restart api` |

## Vérifié le 25/09/2026

Sur une machine de test, avec une configuration factice et `LOG_DRIVER=local` :
- les trois conteneurs démarrent, et l'API passe « healthy » ;
- aucun port n'est publié sur l'hôte ;
- l'API tourne en uid 10001 et ne peut pas écrire dans son code ;
- migrations jouées jusqu'à `0007_mesure_d_usage` ;
- recherche et génération répondent ; l'événement d'usage porte le pays et l'empreinte, jamais l'adresse ;
- le journal d'accès est en JSON, avec l'adresse de `CF-Connecting-IP` ;
- `flask stats` répond sans charger le lexique.

## Reste à faire

- **Lexique curé livré avec l'application (#118).** Sans lui, l'API se rabat sur le DELA complet de l'image (`/api/status` : `curated: false`).
- **Déploiement (#119)** : `make deploy`, test de fumée, retour arrière ; serveur (SSH par clé, mises à jour automatiques, pare-feu).
- **Sauvegardes vers R2 (#120)**, restauration vérifiée chaque mois.
