# 0012 — Une grille conservée est un document que l'auteur modifie

- Statut : acceptée
- Date : 2026-09-21
- Complète l'[ADR 0007](0007-contrat-de-generation.md)

## Contexte

Jusqu'ici, une grille conservée était le **procès-verbal d'une génération** : le contenu stocké tel
quel, parce que le lexique est curé de semaine en semaine et que la même seed ne redonnerait pas la
même grille six mois plus tard.

C'est vrai, et insuffisant. L'auteur revient sur sa grille : le moteur a placé `PORTE`, il préfère
`PERTE`. Il ne veut pas régénérer — le reste lui convient — il veut changer une lettre. Un logiciel
de mots fléchés professionnel qui l'oblige à tout refaire pour un `O` passe à côté de son métier.

Deux difficultés rendent cette modification moins anodine qu'elle en a l'air :

1. **Une lettre appartient à deux mots.** Changer le `O` de `PORTE` change aussi le mot vertical qui
   traverse cette case. Une correction n'en est jamais une : c'est toujours deux.
2. **La définition était accrochée au texte du mot.** Sa clé était `PORTE-1-2-across` : renommer le
   mot aurait rendu sa définition orpheline, silencieusement.

## Décision

**Les lettres font foi ; les mots s'en déduisent.**

- `PATCH /api/grids/<id>` accepte des `cells` — les lettres changées, et elles seules. Le serveur les
  pose, puis **recalcule tous les mots** à partir de la grille. Tenir deux vérités (les lettres et la
  liste des mots) les aurait laissées diverger.
- Les **emplacements ne bougent jamais** : ils sont dictés par les cases définitions, que l'édition
  manuelle ne touche pas. C'est ce qui rend l'opération sûre.
- La clé d'une définition devient sa **position** : `1-2-across`. Elle survit à tout changement de
  lettre (migration `0004`).
- Un mot que l'auteur a corrigé prend la provenance **`manuel`** : il ne vient plus du moteur, et la
  grille ne doit pas prétendre le contraire.
- Le résultat est **vérifié, pas censuré** : chaque mot est confronté au lexique et aux dictionnaires
  de l'auteur. Un mot inconnu est signalé — souligné dans la grille, listé dans le panneau — et
  **posé quand même**, avec un bouton pour le ranger dans un dictionnaire. Un nom propre ou un
  régionalisme est parfois exactement ce qu'il faut ; c'est l'auteur qui juge, pas le lexique.
- Les propositions de remplacement respectent les croisements : `POST /api/grids/<id>/suggestions`
  calcule, case par case, les lettres qui laissent le mot perpendiculaire valide — la cohérence d'arc
  du solveur ramenée à un emplacement — et n'offre que des mots qui les respectent toutes. Proposer
  un mot qui casse un croisement ne rendrait service à personne.

## Conséquences

- Une grille conservée n'est plus « ce que le moteur a produit » mais **ce que l'auteur a voulu**.
  Le champ `seed` garde la trace de l'origine ; il ne promet plus de reproduire le contenu.
- `must_words` reste la **demande d'origine**, pas une description de la grille : un mot imposé peut
  avoir été réécrit à la main depuis.
- La provenance colorée des cases (obligatoire, souhaité, lexique) gagne une quatrième valeur, et
  l'écran la montre.
- Le moteur reste pur : `engine/grid_edit.py` ne sait rien du lexique, il reçoit une fonction qui dit
  si une chaîne est un mot. Ce que contient le dictionnaire se décide dans l'API, qui seule connaît
  l'utilisateur et ses dictionnaires.
- Corollaire à ne pas perdre de vue : rien ne garantit plus qu'une grille conservée soit remplie de
  mots existants. Les écrans doivent le dire plutôt que le supposer.
