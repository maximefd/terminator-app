# Architecture Decision Records (ADR)

Chaque décision structurante du projet est consignée dans un court document : contexte, décision, conséquences. On ne modifie pas une ADR acceptée : on en écrit une nouvelle qui la remplace.

| # | Décision | Statut |
|---|----------|--------|
| [0001](0001-consigner-les-decisions.md) | Consigner les décisions d'architecture dans des ADR | Acceptée |
| [0002](0002-moteur-pur-et-deterministe.md) | Moteur de génération pur, déterministe et borné dans le temps | Acceptée |
| [0003](0003-jwt-en-en-tete.md) | Authentification par JWT dans l'en-tête `Authorization` | Acceptée (à revoir en Phase 6) |
| [0004](0004-pas-de-deploiement-en-ligne.md) | Pas de déploiement en ligne avant un serveur de production | Acceptée |
| [0005](0005-pipeline-du-lexique-et-decisions.md) | Pipeline du lexique et fichier de décisions versionné | Acceptée |
| [0006](0006-format-des-layouts.md) | Format (`x` / `-`) et emplacement des fichiers de layout | Acceptée |
| [0007](0007-contrat-de-generation.md) | Contrat de génération : mots obligatoires, souhaités et thématiques | Acceptée |
| [0008](0008-regles-automatiques-et-revision.md) | Règles automatiques, filtre positif et révision des décisions | Acceptée |
| [0009](0009-annoncer-la-difficulte.md) | Annoncer la difficulté d'une demande plutôt que de la subir | Acceptée |
| [0010](0010-migrations-de-schema.md) | Le schéma de la base évolue par migrations Alembic | Acceptée |

## Modèle

```markdown
# NNNN — Titre

- Statut : proposée | acceptée | remplacée par NNNN
- Date : AAAA-MM-JJ

## Contexte
## Décision
## Conséquences
```
