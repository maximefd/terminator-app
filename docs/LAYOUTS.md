# 🧩 Layouts — Terminator

> Les layouts sont les mises en page des grilles. Pour garantir un rendu de mots fléchés professionnel, ils sont **recopiés depuis de vrais magazines et cahiers** de mots fléchés, puis ajoutés à l'application.

## Format (v1)

Un layout est un fichier texte qui ne contient que la grille, une ligne par rangée :

| Caractère | Case |
|-----------|------|
| `x` | Case définition (ne reçoit pas de lettre) |
| `-` | Case lettre |

Deux touches directes sur un clavier AZERTY, sans Maj ni AltGr. Décision consignée dans l'[ADR 0006](adr/0006-format-des-layouts.md).

Exemple, `backend/layouts/6x7/001.txt` (6 colonnes, 7 rangées) :

```text
x-x-x-
------
x-----
------
x----x
--x---
x-----
```

Règles :

- **le format se déduit de la grille** : largeur = longueur des lignes, hauteur = nombre de lignes. Il doit correspondre au dossier du fichier ;
- toutes les lignes ont la même longueur ; les espaces en fin de ligne et les lignes vides en fin de fichier sont ignorés ;
- tout autre caractère est une **erreur**, avec la ligne et la colonne en cause (il n'est plus lu comme une case lettre) ;
- un mot doit faire au moins 2 lettres (une case lettre isolée dans un sens n'y forme pas de mot) ;
- un mot peut commencer au bord de la grille ;
- les flèches ne sont pas encodées : elles seront déduites de la géométrie (Phase 5).

L'ancien format (`#` = définition, `.` = lettre) reste lu, mais un fichier ne mélange pas les deux. Pour convertir des fichiers (depuis `backend/`) :

```bash
python convert_layouts.py
```

## Emplacement et identifiant

`backend/layouts/<largeur>x<hauteur>/<NNN>.txt`, par exemple `backend/layouts/11x6/001.txt`.

- `NNN` est un numéro à trois chiffres : le plus grand numéro du dossier + 1. On n'écrase jamais un fichier existant.
- L'identifiant du layout se déduit du chemin : `11x6-001`. C'est lui que renvoient l'API (champ `layout` de la grille générée) et le benchmark.
- Aucune métadonnée (source, notes) dans le fichier.

Formats disponibles aujourd'hui : **6×7** et **11×6** (un layout chacun). L'API les liste via `GET /api/grids/formats`, et le frontend ne propose que ceux-là.

## Ajouter un layout (aujourd'hui)

1. Créer le fichier `backend/layouts/<L>x<H>/<NNN>.txt` (créer le dossier si le format est nouveau).
2. Lancer les tests : `make test-backend`. Le test `test_shipped_layouts_load_regardless_of_working_directory` vérifie que chaque layout se lit, a la taille de son dossier et contient des slots.
3. Mesurer le layout : `make bench`. Il est ajouté automatiquement au benchmark.
4. Ouvrir une PR (modèle d'issue « Nouveau layout » disponible sur GitHub).

## Prévu (Phase 2 de la roadmap)

- **Validateur** (CLI, tests, CI) : taille conforme au dossier, chaque case lettre appartient à un mot de 2 lettres ou plus, identifiants uniques, grilles en double signalées, statistiques des slots.
- **Éditeur de layouts** dans la mini-app : dessiner la grille au clic ou au toucher, validation en direct, enregistrement direct dans `backend/layouts/<L>x<H>/` avec un numéro attribué automatiquement.
- **Plus tard** : prendre en photo une grille, la faire reconnaître, puis la corriger et la valider dans l'éditeur ([#47](https://github.com/maximefd/terminator-app/issues/47)).

Voir [ROADMAP.md](ROADMAP.md).
