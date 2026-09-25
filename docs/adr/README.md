# Architecture Decision Records (ADR)

Chaque décision structurante du projet est consignée dans un court document : contexte, décision, conséquences. On ne modifie pas une ADR acceptée : on en écrit une nouvelle qui la remplace.

| # | Décision | Statut |
|---|----------|--------|
| [0001](0001-consigner-les-decisions.md) | Consigner les décisions d'architecture dans des ADR | Acceptée |
| [0002](0002-moteur-pur-et-deterministe.md) | Moteur de génération pur, déterministe et borné dans le temps | Acceptée |
| [0003](0003-jwt-en-en-tete.md) | Authentification par JWT dans l'en-tête `Authorization` | Remplacée par 0015 |
| [0004](0004-pas-de-deploiement-en-ligne.md) | Pas de déploiement en ligne avant un serveur de production | Remplacée par 0013 |
| [0005](0005-pipeline-du-lexique-et-decisions.md) | Pipeline du lexique et fichier de décisions versionné | Acceptée |
| [0006](0006-format-des-layouts.md) | Format (`x` / `-`) et emplacement des fichiers de layout | Acceptée |
| [0007](0007-contrat-de-generation.md) | Contrat de génération : mots obligatoires, souhaités et thématiques | Acceptée |
| [0008](0008-regles-automatiques-et-revision.md) | Règles automatiques, filtre positif et révision des décisions | Acceptée |
| [0009](0009-annoncer-la-difficulte.md) | Annoncer la difficulté d'une demande plutôt que de la subir | Acceptée |
| [0010](0010-migrations-de-schema.md) | Le schéma de la base évolue par migrations Alembic | Acceptée |
| [0011](0011-dictionnaires-choisis.md) | Les dictionnaires versés à une grille se choisissent, aucun n'est implicite | Acceptée |
| [0012](0012-grille-modifiable.md) | Une grille conservée est un document que l'auteur modifie | Acceptée |
| [0013](0013-cible-hebergement-production.md) | Cible d'hébergement de production : un VPS derrière Cloudflare | Acceptée |
| [0014](0014-emails-du-compte.md) | E-mails du compte : liens signés, SMTP, confirmation non bloquante | Acceptée |
| [0015](0015-session-en-cookies.md) | Session en cookies httpOnly, protection CSRF et révocation | Acceptée |
| [0016](0016-mesure-d-usage-sans-cookie.md) | Mesure d'usage côté serveur, sans cookie ni script tiers | Acceptée |
| [0017](0017-un-site-par-langue.md) | Un site par langue, un seul moteur | Acceptée |
| [0018](0018-nom-du-site-francais.md) | Nom et domaine du site français : Le Fléchoir | Acceptée |
| [0019](0019-deploiement.md) | Déploiement : un commit envoyé par SSH et construit sur le serveur, le site envoyé à Pages | Acceptée |

## Modèle

```markdown
# NNNN — Titre

- Statut : proposée | acceptée | remplacée par NNNN
- Date : AAAA-MM-JJ

## Contexte
## Décision
## Conséquences
```
