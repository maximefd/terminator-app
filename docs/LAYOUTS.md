# 🧩 Layouts — Terminator

> Les layouts sont les mises en page des grilles. Pour garantir un rendu de mots fléchés professionnel, ils sont **recopiés depuis de vrais livres** de mots fléchés, puis ajoutés à l'application.

## Format actuel

Un layout est un fichier texte, une ligne par rangée de la grille :

| Caractère | Case |
|-----------|------|
| `#` | Case définition (ne reçoit pas de lettre) |
| `.` | Case lettre |

Emplacement : `backend/templates/<largeur>x<hauteur>/<nom>.txt`

Exemple, `backend/templates/6x7/template_01.txt` (6 colonnes, 7 rangées) :

```text
#.#.#.
......
#.....
......
#....#
..#...
#.....
```

Règles :

- le nom du dossier donne la taille : **largeur** × **hauteur** ;
- les caractères au-delà de la largeur et les lignes au-delà de la hauteur sont ignorés ;
- tout caractère autre que `#` compte comme une case lettre ;
- un mot doit faire au moins 2 lettres (une case lettre isolée dans un sens n'y forme pas de mot).

Formats disponibles aujourd'hui : **6×7** et **11×6** (un layout chacun). L'API les liste via `GET /api/grids/formats`, et le frontend ne propose que ceux-là.

## Ajouter un layout (aujourd'hui)

1. Créer le fichier dans `backend/templates/<L>x<H>/` (créer le dossier si le format est nouveau), par exemple `template_02.txt`.
2. Lancer les tests : `make test-backend`. Le test `test_shipped_layouts_load_regardless_of_working_directory` vérifie que chaque layout se charge et contient des slots.
3. Mesurer le layout : `make bench`. Il est ajouté automatiquement au benchmark.
4. Ouvrir une PR (modèle d'issue « Nouveau layout » disponible sur GitHub).

## Prévu (Phase 2 de la roadmap)

- **Format v1 adapté au clavier AZERTY** : `x` = case définition, `-` = case lettre (touches sans Maj). L'ancien format restera accepté, avec un script de conversion. En-tête de métadonnées : identifiant, format, source (livre), notes.
- **Validateur** (CLI, tests, CI) : chaque case lettre appartient à un mot de 2 lettres ou plus, chaque début de mot touche une case définition ou le bord, la taille correspond au dossier, statistiques des slots.
- **Éditeur de layouts** dans la mini-app : dessiner la grille au clic ou au toucher, validation en direct, enregistrement direct dans `backend/layouts/<L>x<H>/` (sans écraser un fichier existant).
- Les **flèches** ne sont pas encodées dans le fichier : elles seront déduites de la géométrie (Phase 5).

Voir [ROADMAP.md](ROADMAP.md).
