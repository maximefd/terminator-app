# Architecture Decision Records (ADR)

Chaque décision structurante du projet est consignée dans un court document : contexte, décision, conséquences. On ne modifie pas une ADR acceptée : on en écrit une nouvelle qui la remplace.

| # | Décision | Statut |
|---|----------|--------|
| [0001](0001-consigner-les-decisions.md) | Consigner les décisions d'architecture dans des ADR | Acceptée |
| [0002](0002-moteur-pur-et-deterministe.md) | Moteur de génération pur, déterministe et borné dans le temps | Acceptée |
| [0003](0003-jwt-en-en-tete.md) | Authentification par JWT dans l'en-tête `Authorization` | Acceptée (à revoir en Phase 6) |
| [0004](0004-pas-de-deploiement-en-ligne.md) | Pas de déploiement en ligne avant un serveur de production | Acceptée |

## Modèle

```markdown
# NNNN — Titre

- Statut : proposée | acceptée | remplacée par NNNN
- Date : AAAA-MM-JJ

## Contexte
## Décision
## Conséquences
```
