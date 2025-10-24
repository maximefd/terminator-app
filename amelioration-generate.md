Mini-Projet : Le Générateur "Artiste" (V2)

Objectif : Transformer le générateur V1 "fonctionnel" en un générateur V2 "artiste" qui produit des grilles de qualité professionnelle, esthétiques, et qui offre un contrôle avancé à l'utilisateur.

1. Le Backlog V2 (Priorisé)

ID

Tâche / Story

Priorité

Statut

C1

(Fondation) Créer l'outil de test (test_harness.py) qui génère un rapport HTML visuel de plusieurs grilles.

CRITIQUE

À FAIRE

A1

Appliquer la règle stricte : jamais plus de deux cases noires adjacentes (horizontalement ou verticalement).

Haute

À FAIRE

B1

Permettre à l'utilisateur d'imposer 1 à 3 mots de son choix que l'algorithme doit placer en priorité.

Haute

À FAIRE

A3

Assurer une distribution équilibrée des longueurs de mots pour garantir la variété (mots courts et longs).

Moyenne

À FAIRE

B3

Permettre à l'utilisateur de choisir quels dictionnaires personnels utiliser et de leur donner un poids de priorité.

Moyenne

À FAIRE

B2

Permettre à l'utilisateur de dessiner des cases noires avant la génération.

Basse

En attente

A4

(Futur) Explorer des options de symétrie pour les cases noires.

Très Basse

En attente

2. L'Outil de Test ("Harness") - Spécifications

Notre priorité absolue. L'outil sera un script Python (test_harness.py) qui :

Importe notre GridGenerator.

Charge une liste de mots depuis dela_clean.csv une seule fois.

Génère un petit nombre de grilles (ex: 5 à 10) avec des paramètres différents (taille, seed).

Calcule les statistiques pour chaque grille (temps, fill_ratio).

Génère un fichier HTML unique (report.html) qui affiche :

Les statistiques globales (temps moyen, fill_ratio moyen).

Le rendu visuel de chaque grille générée, côte à côte, pour une comparaison facile.

Cet outil sera notre "laboratoire". Chaque modification de l'algorithme sera validée par un nouveau rapport.

[Image d'un rapport de test avec plusieurs grilles affichées côte à côte]

3. La Méthodologie Proposée (Plan Chronologique)

Nous allons procéder par phases, en nous concentrant sur une seule amélioration à la fois et en la validant avec notre outil de test.

Phase 1 – La Fondation : Construire le Laboratoire (Priorité Absolue)

Action 1.1 : Créer le script test_harness.py qui génère N grilles et calcule les statistiques en console.

Action 1.2 : Ajouter la génération du rapport report.html qui affiche les grilles visuellement.

Validation : Nous devons être capables de lancer une commande et d'obtenir un rapport visuel de l'état actuel de notre algorithme.

Phase 2 – L'Artiste : La Règle des Cases Noires (Story A1)

Action 2.1 : Modifier l'algorithme (_can_place_word ou le système de score) pour qu'il interdise de placer un mot si cela crée un bloc de plus de X cases noires adjacentes.

Action 2.2 : Lancer notre "harness" de test.

Validation :

Le rapport visuel montre des grilles sans amas de cases noires.

Les statistiques montrent que le fill_ratio et le temps de génération restent acceptables.

Phase 3 – Le Directeur : Le Forçage de Mots (Story B1)

Action 3.1 : Modifier l'algorithme pour qu'il accepte une liste de "mots à forcer". Il tentera de placer ces mots en tout premier, avant même le "premier mot" habituel.

Action 3.2 : Mettre à jour le "harness" pour qu'il puisse tester ce nouveau paramètre.

Action 3.3 : Mettre à jour la route de l'API (/api/grids/generate) pour qu'elle accepte ce nouveau paramètre.

Validation :

Le rapport visuel montre des grilles qui contiennent bien les mots imposés.

Les statistiques restent bonnes.

4. Proposition : Mise à Jour de l'API

Pour supporter les futures fonctionnalités (B1, B3), je propose d'anticiper et de mettre à jour la "signature" de notre endpoint de génération.

Actuellement :
POST /api/grids/generate avec {"size": ..., "use_global": ...}

Proposition V2 :
POST /api/grids/generate avec :

{
  "size": { "width": 10, "height": 10 },
  "seed": 123,
  "dictionaries": {
    "use_global": true,
    "personal_ids": [1, 5],
    "prioritize_id": 5 
  },
  "constraints": {
    "forced_words": ["TERMINATOR", "GRILLE"],
    "forced_black_squares": [{"x": 0, "y": 0}]
  }
}


Nous n'implémenterons pas tout tout de suite, mais cela nous donne une structure claire et évolutive.

Ce plan est notre nouvelle feuille de route. Il est centré sur la qualité, la mesure, et l'itération.

Êtes-vous prêt à commencer avec la Phase 1 : la construction de notre outil de test test_harness.py ?