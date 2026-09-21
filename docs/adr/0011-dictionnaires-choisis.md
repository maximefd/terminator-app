# 0011 — Les dictionnaires versés à une grille se choisissent, aucun n'est implicite

- Statut : acceptée
- Date : 2026-09-21
- Complète l'[ADR 0007](0007-contrat-de-generation.md)

## Contexte

L'[ADR 0007](0007-contrat-de-generation.md) versait au pool « souhaité » les dictionnaires demandés
(`wish_dictionary_ids`) **et**, silencieusement, le dictionnaire personnel **actif**. L'idée venait de
la recherche par motif, où le dictionnaire actif remonte en tête des résultats : le même réglage
semblait devoir servir partout.

À l'usage, non. Le dictionnaire actif est celui dans lequel l'auteur **range ses trouvailles du
moment** ; la grille qu'il compose ce jour-là peut n'avoir aucun rapport. Une grille sur la musique
héritait des mots de cuisine parce qu'ils étaient « actifs », et rien à l'écran ne le disait : le
sélecteur affichait le dictionnaire actif comme « toujours inclus », une règle que l'auteur n'avait
pas demandée et ne pouvait pas défaire.

## Décision

**Seuls les dictionnaires cochés alimentent la grille.** `wish_dictionary_ids` devient la seule
source : aucun dictionnaire n'entre de lui-même, pas même l'actif.

La notion de dictionnaire **actif** garde son rôle — mais uniquement là où elle a du sens : la
**recherche par motif**, où elle répond à « quel dictionnaire j'interroge en ce moment ».

## Conséquences

- Une grille générée sans cocher aucun dictionnaire ne contient que les mots saisis à la main et le
  lexique commun. C'est ce que l'écran annonce, et plus rien d'invisible ne s'y ajoute.
- L'écran de génération liste **tous** les dictionnaires de l'auteur, chacun à cocher. L'actif y est
  signalé comme tel, sans privilège.
- Le contrat de l'ADR 0007 n'est pas rompu : le champ ne change ni de nom ni de forme, seul l'ajout
  implicite disparaît. Un appel qui listait déjà ses dictionnaires se comporte à l'identique.
- Un test vérifiait l'ancien comportement ; il vérifie désormais l'inverse — qu'un dictionnaire non
  coché **n'entre pas** dans la grille. C'est la propriété qui compte pour l'auteur.
