# 0001 — Consigner les décisions d'architecture dans des ADR

- Statut : acceptée
- Date : 2026-09-14

## Contexte

Le projet est développé en solo, avec l'aide d'assistants IA, et va être relu par un pair. Les choix structurants (format des layouts, pipeline du lexique, contrat de l'API de génération…) doivent rester compréhensibles plus tard, sans reconstituer l'historique des conversations ou des commits.

## Décision

Toute décision structurante fait l'objet d'une ADR courte dans `docs/adr/`, numérotée, en français : contexte, décision, conséquences. Une ADR acceptée n'est pas réécrite ; elle est remplacée par une nouvelle.

## Conséquences

- Une PR qui introduit un choix structurant inclut son ADR.
- L'index `docs/adr/README.md` est tenu à jour.
