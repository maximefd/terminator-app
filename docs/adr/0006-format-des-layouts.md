# 0006 — Format et emplacement des fichiers de layout

- Statut : acceptée
- Date : 2026-09-15

## Contexte

- L'auteur veut recopier **vite et sans erreur** de nombreuses grilles trouvées dans des magazines et des cahiers de mots fléchés, dans **beaucoup de formats** différents.
- L'ancien format utilisait `#` (case définition) et `.` (case lettre). Sur un clavier AZERTY, `#` demande AltGr. Surtout, tout caractère autre que `#` était lu comme une case lettre, et une ligne trop courte ou trop longue était complétée ou tronquée sans rien dire : une faute de frappe changeait la grille en silence.
- Les fichiers s'appelaient `backend/templates/<L>x<H>/template_01.txt` : le nom était choisi à la main.
- Plus tard, l'éditeur de layouts (#14) puis la reconnaissance d'une grille photographiée (#47) devront produire exactement le même fichier.

## Décision

1. **Caractères** : `x` = case définition, `-` = case lettre, une ligne par rangée. Ce sont des touches directes sur AZERTY. L'ancien format `#` / `.` reste lu ; un même fichier ne mélange pas les deux. Tout autre caractère, une ligne vide au milieu ou des lignes de longueurs différentes sont des **erreurs** qui indiquent la ligne et la colonne.
2. **Aucune métadonnée** dans le fichier : pas de source, pas d'en-tête. Le fichier ne contient que la grille.
3. **Le format se déduit de la grille** (largeur = longueur des lignes, hauteur = nombre de lignes). Il doit correspondre au dossier qui contient le fichier ; sinon le chargement échoue.
4. **Emplacement et identifiant automatiques** : `backend/layouts/<L>x<H>/<NNN>.txt`, où `NNN` est un numéro à trois chiffres attribué automatiquement (le plus grand numéro du dossier + 1). L'identifiant `<L>x<H>-<NNN>` (ex. `11x6-001`) se déduit du chemin ; il est renvoyé par l'API et utilisé par le benchmark. Un fichier existant n'est jamais écrasé.
5. **Les flèches ne sont pas encodées** : elles seront déduites de la géométrie (Phase 5). Un mot peut commencer au bord de la grille.
6. Le code de lecture est pur et vit dans le moteur (`backend/engine/layout_format.py`) : le validateur (#13), l'éditeur (#14) et le benchmark s'appuient sur lui.

## Conséquences

- Recopier une grille à la main dans un éditeur de texte ne demande que deux touches ; une erreur de recopie est signalée au lieu d'être absorbée.
- Les deux layouts existants ont été convertis (`python convert_layouts.py`) et renommés `001.txt`, sans changement des grilles générées (benchmark sur 20 seeds).
- Les clés du benchmark et le champ `layout` de la réponse de `/api/grids/generate` passent de `6x7/template_01.txt` à `6x7-001`.
- Sans métadonnées, la provenance d'une grille n'est pas tracée dans le dépôt. Si ce besoin apparaît, une nouvelle ADR ajoutera un en-tête optionnel.
