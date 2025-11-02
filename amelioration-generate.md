Mini-Projet : Le Générateur "Artiste" (V2)

Objectif : Transformer le générateur V1 "fonctionnel" en un générateur V2 "artiste" qui produit des grilles de qualité professionnelle, esthétiques, et qui offre un contrôle avancé à l'utilisateur.

1. Le Backlog V2 (Priorisé)

### ✅ Complétées

| ID | Tâche / Story | Priorité | Statut |
|----|---------------|----------|--------|
| C1 | (Fondation) Créer l'outil de test (test_harness.py) qui génère un rapport HTML visuel de plusieurs grilles. | CRITIQUE | ✅ FAIT |
| P1 | **Optimisations Performance** : Caching get_candidates, pré-calcul intersections, sets pour mots disponibles | CRITIQUE | ✅ FAIT |
| P2 | **Forward Checking** : Détection précoce des branches mortes | HAUTE | ✅ FAIT |
| P3 | **Heuristique MRV améliorée** : Score = nb_candidats / (1 + nb_intersections) | HAUTE | ✅ FAIT |
| P4 | **Métriques de performance** : Tracking appels récursifs, backtracks, FC, cache | HAUTE | ✅ FAIT |
| P5 | **Historique de construction** : Affichage de l'ordre des mots placés dans le rapport HTML | MOYENNE | ✅ FAIT |

**Résultats mesurés :**
- Grilles 6×7 : 100% succès (vs 80% avant), temps médian <1s (vs 1-5s avant)
- Grilles 11×6 : 100% succès (vs 0% timeout avant), temps ~9s
- Gains : 10-100× moins d'appels récursifs sur grilles faciles
- Cache hit rate : 80-89%
- FC efficacité : 21-54% (vs 12-37% avec FC basique)

### 🚧 Prochaines étapes prioritaires

| ID | Tâche / Story | Priorité | Statut |
|----|---------------|----------|--------|
| T1 | **Templates multiples par taille** : Fournir plusieurs templates pour chaque taille de grille (ex: 3-5 templates pour 10x10) et piocher aléatoirement selon la taille demandée. Améliore la variété visuelle des grilles. | HAUTE | À FAIRE |

### 📋 Backlog à venir

ID

Tâche / Story

Priorité

Statut

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

### ✅ Phase 1 – La Fondation : Construire le Laboratoire (COMPLÉTÉE)

**Action 1.1** : Créer le script test_harness.py qui génère N grilles et calcule les statistiques en console. ✅

**Action 1.2** : Ajouter la génération du rapport report.html qui affiche les grilles visuellement. ✅

**Action 1.3** : Ajouter les métriques de performance (appels récursifs, backtracks, FC, cache). ✅

**Action 1.4** : Ajouter l'historique de construction dans le rapport HTML. ✅

**Validation** : ✅ Rapport HTML complet avec grilles visuelles, métriques et historique.

---

### ✅ Phase 1.5 – Optimisations Performance (COMPLÉTÉE)

**Objectif** : Améliorer drastiquement les performances du solver pour générer des grilles moyennes (11×6).

**Action 1.5.1** : Implémenter le cache pour get_candidates. ✅
- Résultat : 80-85% cache hit rate

**Action 1.5.2** : Pré-calculer les intersections entre slots. ✅
- Résultat : Lookup O(1) au lieu de O(n)

**Action 1.5.3** : Utiliser des sets au lieu de listes pour les mots disponibles. ✅
- Résultat : Add/remove O(1) au lieu de O(n)

**Action 1.5.4** : Implémenter Forward Checking basique. ✅
- Résultat : 30-40% des branches mortes détectées précocement

**Action 1.5.5** : Améliorer l'heuristique MRV (Minimum Remaining Values). ✅
- Nouvelle formule : `Score = nb_candidats / (1 + nb_intersections)`
- Résultat : 10-100× moins d'exploration, grilles 11×6 maintenant possibles

**Validation** : ✅ 
- Grilles 6×7 : 100% succès en <300ms médian
- Grilles 11×6 : 100% succès en ~9s
- Passage de 0% à 100% de réussite sur grilles moyennes

---

### ✅ Phase 1.6 – Forward Checking Strict (COMPLÉTÉE)

**Objectif** : Éliminer les grilles lentes (>10s) en détectant mieux les dead-ends.

**Action 1.6.1** : Améliorer le FC pour vérifier qu'il reste au moins 3 candidats (au lieu de 1). ✅
- Paramètre : `MIN_SAFE_CANDIDATES = 3` (testé avec 5, ajusté à 3 pour équilibre)
- Logique : Si un slot intersecté aurait <3 candidats après placement, rejeter le mot

**Validation** : ✅
- Grilles 6×7 : 100% succès, 62.5% en <1s, max 18s
- FC efficacité : 21-54% (vs 12-37% avant)
- Aucun timeout, toutes les grilles réussissent

---

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

