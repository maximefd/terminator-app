# 0009 — Annoncer la difficulté d'une demande plutôt que de la subir

- Statut : acceptée
- Date : 2026-09-19

## Contexte

Les mots obligatoires sont la fonctionnalité centrale de la Phase 3. Mesurés pour la première fois ([#73](https://github.com/maximefd/terminator-app/issues/73), 4 700 générations) :

| Mots imposés | Réussite |
|--------------|----------|
| 1 | 94 % |
| 2 | 82 % |
| 3 | 46 % |

Et surtout, **c'est la longueur des mots qui décide**, pas leur nombre ni la taille de la grille : trois mots de 6 lettres au plus réussissent 67 % du temps, contre 39 % sans plafond. Une lettre rare (`Z`, `W`, `K`, `X`, `Q`, `Y`, `J`) divise encore le taux — 13 % pour trois mots longs en contenant une.

Deux tentatives pour **relever** ce taux ont échoué à la mesure : classer les layouts par charge de croisements (gain non distinguable du bruit) et changer de layout à chaque redémarrage (perte nette). Seul le changement de layout à recherche épuisée apporte un gain, borné aux formats comptant plusieurs layouts.

L'auteur, lui, ne dispose d'aucune de ces informations : il tape trois mots, attend vingt secondes, et reçoit « impossible ».

## Décision

**Dire le coût avant de chercher.** `POST /api/grids/difficulty` renvoie, sans générer :

- pour chaque mot, son niveau et **pourquoi** il est coûteux (longueur, lettres rares) ;
- pour la demande entière, un taux de réussite estimé et son niveau ;
- le mot qui pèse le plus, et une issue : **le passer en mot souhaité**, où il sera placé s'il rentre sans faire échouer la grille.

Les taux ne sont pas décrétés : ils sortent de la table mesurée (`engine/difficulty.py`), qui cite ses échantillons. Au-delà de trois mots, rien n'a été mesuré — le taux à trois sert alors de **borne haute**, signalée par `measured: false`.

L'endpoint est pur (aucune génération), plafonné comme la recherche (120/min) et non comme la génération (10/min) : il est appelé à chaque frappe.

## Conséquences

- Le critère de sortie de #73 change de nature : l'objectif n'est plus « trois mots quelconques aboutissent », mais « l'auteur sait ce qu'il demande ». Les demandes raisonnables (1 à 2 mots, ou 3 mots courts : 67 à 94 %) doivent marcher ; les autres doivent être **annoncées**.
- La Phase 4 (#23) affichera cette estimation pendant la saisie, et proposera le basculement en mot souhaité.
- La table devra être **remesurée** si le solveur ou le lexique changent notablement : elle décrit un comportement mesuré, pas une vérité.
- Limite assumée : l'estimation ignore le layout visé. Elle agrège tous les formats, faute de données suffisantes par format. La vérification préalable existante (`check_must_words`) couvre déjà le cas « ce mot n'entre nulle part ».
