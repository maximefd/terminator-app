# 0007 — Contrat de génération : mots obligatoires, souhaités et thématiques

- Statut : proposée
- Date : 2026-09-15

## Contexte

- La génération ne sait aujourd'hui que remplir un format (`size`) avec le dictionnaire commun. L'auteur veut fournir des **mots obligatoires**, des **mots souhaités** et des **dictionnaires thématiques**, qui représentent environ 30 % des mots de la grille, le reste venant du lexique curé.
- Les mots des dictionnaires personnels ne sont jamais placés : les candidats ne viennent que du Trie commun (#17).
- Ce contrat servira aussi au futur moteur côté client (Phase 7, [ADR 0002](0002-moteur-pur-et-deterministe.md)) : il doit être en JSON, sans dépendance à Flask, et reproductible.

## Décision

### Requête : `POST /api/grids/generate`

| Champ | Type | Défaut | Règle |
|-------|------|--------|-------|
| `layout_id` | texte | — | ex. `11x6-001` ; 404 si inconnu |
| `size` | `{width, height}` | — | tirage d'un layout du format ; **exactement un** de `layout_id` et `size` |
| `seed` | entier ≥ 0 | tiré par le serveur | toujours renvoyé, pour rejouer une grille |
| `must_words` | liste de mots | `[]` | 10 au plus ; chaque mot doit être placé |
| `wish_words` | liste de mots | `[]` | 200 au plus |
| `wish_dictionary_ids` | liste d'identifiants | `[]` | 10 au plus ; dictionnaires de l'utilisateur connecté uniquement (`get_owned_dictionary`, 404 sinon) |
| `target_wish_ratio` | nombre de 0 à 1 | `0.3` | part visée de mots souhaités parmi les mots de la grille ; objectif souple |
| `use_global` | booléen | `true` | lexique commun pour compléter la grille |
| `time_budget_ms` | entier | budget du serveur | de 1 000 au budget du serveur (`GENERATION_TIME_BUDGET_S`) |

Les mots sont normalisés comme dans la recherche (majuscules, sans accents ni espaces). Un mot obligatoire est aussi souhaité : inutile de le répéter. Le corps est validé par un schéma pydantic (`parse_body`) ; les erreurs sont en français.

La requête actuelle (`size`, `seed`, `use_global`) reste valide : le frontend continue de fonctionner sans changement.

### Réponse `200`

```json
{
  "grid": {
    "layout": "11x6-001",
    "seed": 421337,
    "width": 11, "height": 6,
    "cells": [{"x": 0, "y": 0, "char": "", "is_black": true}],
    "words": [{"text": "PORTE", "x": 1, "y": 1, "direction": "across", "source": "must"}],
    "wish_ratio": 0.33,
    "target_wish_ratio": 0.3,
    "must_words": ["PORTE"],
    "statistics": {"attempts": 4, "metrics": {}}
  }
}
```

- `source` vaut `must`, `wish` ou `common` pour chaque mot placé.
- `wish_ratio` est la part atteinte de mots `must` et `wish` parmi les mots placés.

### Échecs `422` : une explication, jamais une erreur 500

| `reason` | Quand | Contenu en plus de `error` |
|----------|-------|----------------------------|
| `must_words` | Vérification **avant** la résolution : mot plus long que tous les emplacements du layout, plus de mots d'une longueur que d'emplacements de cette longueur | `details` : `[{word, problem}]`, et `suggested_layouts` : layouts où ces mots entrent |
| `must_words_unplaced` | La résolution n'a pas réussi à placer tous les mots obligatoires dans le budget | `unplaced` : mots non placés |
| `timeout` | Budget temps dépassé | — |
| `no_solution` | Recherche épuisée sans grille | — |

Une grille est renvoyée **uniquement si tous les mots obligatoires sont placés** : un mot obligatoire n'est pas une suggestion.

### Moteur

1. Trois **pools** dans le dépôt de mots : obligatoires, souhaités (saisis et dictionnaires thématiques, y compris le dictionnaire personnel actif), communs (lexique curé). Les mots des pools `must` et `wish` sont valides pour les croisements, même absents du lexique (corrige #17).
2. Les mots obligatoires sont placés en premier, du plus contraint au moins contraint, avec retour arrière.
3. Les candidats sont triés par pool (`wish` avant `common`), puis par fréquence, puis par score de lettres ; le ratio visé est un objectif souple, recherché grâce aux redémarrages dans le budget.
4. Déterminisme : même requête, même lexique et même seed ⇒ même grille.

## Conséquences

- Le frontend peut évoluer par étapes : la Phase 4 ajoutera la saisie des mots, le choix du layout et l'affichage de la source des mots.
- Les pools et le placement des mots obligatoires se développent dans le moteur pur ; l'API ne fait que valider, résoudre les dictionnaires de l'utilisateur et traduire les échecs.
- Un layout sans emplacement assez long pour un mot obligatoire est refusé avant tout calcul, avec des layouts suggérés : l'auteur sait tout de suite quoi changer.
- Tests exigés : mot obligatoire placé, impossibilité expliquée (`must_words`, `must_words_unplaced`), ratio rapporté, dictionnaire d'un autre utilisateur refusé (404), même seed ⇒ même grille.
