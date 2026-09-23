# 0013 — Cible d'hébergement de production

- Statut : acceptée
- Date : 2026-09-22

## Contexte

- L'[ADR 0004](0004-pas-de-deploiement-en-ligne.md) a suspendu toute mise en ligne jusqu'à un vrai serveur. La mise en production n'est pas immédiate, mais il faut savoir **où** elle se fera pour préparer le code dès maintenant.
- Contraintes : un budget d'environ **60 € par an**, aucun risque pour un tiers, et des comptes utilisateurs (e-mails, hashs de mots de passe, dictionnaires personnels) à protéger.
- Une place a été proposée sur un hébergement mutualisé o2switch qui sert déjà un site en activité. Sur ce type d'hébergement, les quotas de CPU, de RAM et de processus sont ceux du compte. Terminator y aurait consommé les ressources de ce site, et une faille dans Terminator aurait donné accès à ses fichiers. Pas de Docker non plus, et des processus arrêtés quand ils sont inactifs, ce qui imposerait de recharger le lexique à chaque réveil.

**Mesures** du 22/09/2026 : lexique curé de 701 403 mots, chemin exact de `POST /api/grids/generate`, conteneur limité à 2 CPU, 10 seeds par format.

| Mesure | Valeur |
|--------|--------|
| RAM après chargement du lexique | 601 Mo (14 Mo au démarrage) |
| RAM d'un processus après quelques générations | ~700 Mo |
| Durée médiane | 0,10 s (6×7) à 3,7 s (13×18) |
| p95 | jusqu'à 11,9 s (13×16) |
| Pire cas | 16,7 s en génération libre ; 20 s (le budget) avec deux mots imposés |
| CPU par génération | 0,14 s (6×7) à 4,6 s (13×18) ; ~1,9 s en moyenne |
| Préparation refaite à chaque requête | jusqu'à 0,8 s (tri du lexique et construction du dépôt de mots) |
| 2 générations en threads | aucun gain sur la série : le GIL les sérialise |
| 4 générations sur 2 cœurs | médiane doublée (1,9 → 4,2 s), pire cas 19,6 s, à la limite du budget |
| PyPy | environ 2 fois plus rapide, mais +250 Mo par processus ; deux processus dépassent 2 Go |

Ces mesures ont été prises sur un Mac. Un cœur de VPS d'entrée de gamme est estimé 1,5 à 2 fois plus lent.

**Après les prérequis de cette ADR**, même protocole (voir Conséquences) :

| Mesure | Avant | Après |
|--------|-------|-------|
| Préparation par requête | 0,09 à 0,76 s | ~0,001 s |
| CPU moyen d'une génération libre | 1,78 s | 1,25 s |
| Médiane 6×7 / 11×17 / 13×16 | 0,10 / 1,17 / 2,06 s | 0,01 / 0,42 / 1,33 s |
| 4 générations sur 2 cœurs : médiane | 3,6 s | 1,6 s |
| RAM totale de 4 processus forkés | 2 037 Mo | 782 Mo |
| gunicorn : maître et 3 workers, après des générations | — | 830 Mo |

L'avant-dernière ligne vient de ce que chaque requête ne recopie plus le lexique : les workers partagent celui du processus maître au lieu d'en porter chacun une copie. Ce partage peut s'éroder avec le temps, à mesure que les compteurs de références touchent les pages mémoire. C'est à surveiller sur le VPS.

**Options écartées :**

- **L'hébergement mutualisé**, pour les raisons ci-dessus.
- **Render et Vercel** : déjà essayés, voir l'ADR 0004.
- **Hetzner CX23** : 5,49 € HT par mois depuis la hausse du 15 juin 2026, sauvegardes en option.
- **Contabo** : processeurs réputés surchargés, un mauvais choix pour un moteur qui calcule.
- **Oracle Free Tier** : instances suspendues sans préavis.
- **Deux serveurs** (un pour le site et l'API, un pour le moteur) : rien dans les mesures ne le justifie.
- **PyPy** : écarté pour l'instant. À reconsidérer quand la curation aura réduit le lexique.

## Décision

1. **Un seul VPS : OVH VPS-1.** 2 vCores, 4 Go, 40 Go NVMe, hébergé en France, avec sauvegarde quotidienne et protection anti-DDoS incluses. Environ 4,57 € TTC par mois (tarif relevé le 22/09/2026, probablement avec engagement).
2. **Cloudflare devant tout**, en offre gratuite :
   - DNS, HTTPS et cache ;
   - l'API joignable uniquement par **Cloudflare Tunnel**, sans aucun port web ouvert sur le serveur ;
   - le frontend en **export statique** sur Cloudflare Pages.
3. **Sur le VPS**, Docker Compose : l'API sous gunicorn, PostgreSQL et cloudflared. Le trafic entrant est refusé, sauf SSH par clé.
4. **Serveur d'application** : gunicorn avec **3 workers synchrones**, l'application chargée une fois dans le processus maître avant de les créer. Au plus **2 générations simultanées** (une par cœur) et **une seule par visiteur**. Au-delà, l'API répond 429. Le troisième worker reste libre pour les requêtes légères (connexion, recherche, grilles). Le budget reste à **20 s** : le réduire ferait échouer les grandes grilles sur un cœur plus lent. C'est la limite de concurrence qui protège le serveur.
5. **Adresse du visiteur** : derrière le tunnel, toutes les requêtes arrivent de cloudflared. Le rate limiting lit donc l'IP dans `CF-Connecting-IP` (`CLIENT_IP_HEADER`), et seulement si la configuration le demande.
6. **Lexique** : un fichier versionné, livré avec l'application. Pas de rechargement à chaud en production.
7. **Sauvegardes** : en plus de celle d'OVH, un dump PostgreSQL quotidien, chiffré, stocké hors du serveur (Cloudflare R2), conservé 30 jours. La restauration est testée chaque mois.
8. **Services annexes**, en offres gratuites : un domaine propre (~10 € par an), Brevo pour les e-mails transactionnels, Sentry pour les erreurs et UptimeRobot pour surveiller `/api/status`.

| Poste | Coût TTC par an |
|-------|-----------------|
| OVH VPS-1 | ~55 € |
| Domaine | ~10 € |
| Cloudflare, Brevo, Sentry, UptimeRobot | 0 € |
| **Total** | **~65 €** |

## Conséquences

- **Prérequis réalisés avec cette ADR** :
  - la clé du rate limiting ;
  - gunicorn et la limite de générations simultanées ;
  - le lexique préparé une fois au chargement, au lieu de l'être à chaque requête : les grilles produites sont identiques, le benchmark donne les mêmes trajectoires sur ses 420 générations ;
  - le rechargement à chaud coupé en production ;
  - les journaux de gunicorn, que les migrations jouées au démarrage éteignaient.
- **Reste à faire avant l'ouverture** :
  - l'export statique du frontend (`/grids/[id]` à passer en paramètre de requête, en-têtes de sécurité déplacés vers Cloudflare) ;
  - la Phase 6 de la [roadmap](../ROADMAP.md) : cookies httpOnly, mot de passe oublié, Sentry, revue des licences ;
  - une commande de déploiement, et la sauvegarde nocturne qui appelle `tools/db/backup.sh` puis copie hors du serveur (la sauvegarde et sa vérification existent déjà : `make db-backup`, `make db-restore-check`) ;
  - la checklist de [SECURITY.md](../SECURITY.md).
- **Première semaine en ligne** : refaire ces mesures sur le VPS (`backend/benchmarks/load_profile.py`, `make bench-load` en local). Passer au VPS-2 (4 vCores, 8 Go, environ 104 € par an) si la RAM dépasse 75 %, si les refus « générateur occupé » deviennent fréquents, ou si le p95 dépasse 15 s. Au-delà, c'est la [Phase 7](../ROADMAP.md) : file de jobs ou moteur côté client.
- **Rate limiting** : ses compteurs restent en mémoire, par worker. Une limite de 10 par minute vaut donc jusqu'à 30 avec 3 workers. Les générations simultanées, elles, sont comptées entre tous les workers.
- **Dépôt GitHub** : le passer en privé protégerait la curation (`decisions.csv`) et les layouts. Mais sur GitHub Free, un dépôt privé perd la protection de branche qui impose la CI verte. Décision à prendre avant la mise en ligne.
- **L'ADR 0004 reste en vigueur** jusqu'à la mise en ligne. Ce jour-là, elle sera remplacée par la présente.
