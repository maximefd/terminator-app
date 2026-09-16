# 🧩 Product Requirements Document (PRD) — Terminator

> Vision produit. Pour le « comment » et le « quand », voir [ROADMAP.md](ROADMAP.md) et [ARCHITECTURE.md](ARCHITECTURE.md).
> Dernière mise à jour : septembre 2026.

## 1. Problème et proposition de valeur

### Le problème
Créer une grille de mots fléchés prend du temps. À la main, on bute sur la case qui manque : il faut un mot d'une longueur donnée, avec certaines lettres imposées par les croisements. Remplir automatiquement une grille est encore plus dur : les mots doivent tous exister et tous se croiser. Et pour qu'une grille paraisse professionnelle, il faut respecter les mises en page des publications françaises et utiliser des mots naturels.

### La proposition
Un atelier pour l'auteur de mots fléchés :
1. **Création manuelle assistée** : trouver instantanément les mots correspondant à un motif (`P??LE`), dans un grand dictionnaire et dans ses propres listes.
2. **Création automatique** : choisir un format, donner quelques mots qu'on veut absolument voir ou aimerait voir (environ 30 % de la grille), et laisser le moteur compléter avec le dictionnaire commun.
3. **Rendu professionnel** : des layouts recopiés de vrais livres, un vocabulaire courant, puis des flèches, des définitions et un export.

Ce n'est **pas un jeu**, c'est un **outil de création**.

## 2. Personas

| Persona | Besoin | Aujourd'hui |
|---------|--------|-------------|
| **L'auteur** (créateur du projet, seul utilisateur actuel) | Gagner du temps sur ses grilles, avec un résultat de qualité professionnelle | Cible principale |
| **Créateur expérimenté / professionnel** | Grilles denses, esthétiques, vocabulaire maîtrisé, export | Cible future (après la mise en production) |
| **Visiteur** | Découvrir l'outil via la recherche par motif, sans compte | Supporté |

## 3. Fonctionnalités

| # | Fonctionnalité | Détail | État |
|---|----------------|--------|------|
| F1 | Recherche par motif | `?` = lettre inconnue ; accents ignorés ; résultats personnels en tête | ✅ (~90 %) |
| F2 | Dictionnaires personnels | Plusieurs par utilisateur, un actif, mots avec définition | ✅ |
| F3 | Comptes | Inscription, connexion, session renouvelée, suppression des données | ✅ |
| F4 | Génération automatique | À partir d'un layout ; déterministe par seed ; budget temps | ✅ fragile sur les grands formats |
| F5 | Lexique curé | Tri manuel rapide des mots rares, aidé par la fréquence et les définitions | Phase 1 |
| F6 | Catalogue de layouts | Nombreux formats et mises en page issus de livres ; éditeur | Phase 2 |
| F7 | Mots imposés | Obligatoires, souhaités, dictionnaires thématiques | Phase 3 |
| F8 | Écran de génération complet et sauvegarde des grilles | Choix visuel du layout, sources des mots, historique | Phase 4 |
| F9 | Rendu mots fléchés | Flèches, cases définitions, saisie des définitions, export PDF | Phase 5 |

## 4. Contraintes

- **Aspect professionnel français** : les layouts viennent de publications réelles ; les mots doivent être courants.
- **Clavier AZERTY** : raccourcis sans Maj ni AltGr.
- **UX irréprochable** : chaque écran explique ce qu'il fait et ce qui se passe ensuite, même pour un public expert.
- **Sécurité** dès maintenant (données utilisateur en base), même sans mise en production.
- **Pratiques d'ingénierie de niveau production** (tests, CI, revue, ADR) malgré l'usage personnel.

## 5. Hors périmètre (pour l'instant)

- Déploiement en ligne et URL publique ([ADR 0004](adr/0004-pas-de-deploiement-en-ligne.md)).
- Offre payante, collaboration multi-utilisateurs.
- Mots croisés « à l'américaine », autres langues.

## 6. Critères de succès

| Critère | Mesure | Aujourd'hui |
|---------|--------|-------------|
| Recherche rapide | Réponse `/api/search` < 200 ms (P95) | ✅ (arrêt du parcours à la limite) |
| Génération fiable | ≥ 95 % de succès en 20 s pour chaque layout du catalogue (benchmark, 20 seeds) | 🚧 6×7, 7×9 et 11×6 : 100 % (15 % avant les redémarrages et l'index) · 10×13 : 0 à 15 %, sauf 10x13-004 à 85 % |
| Qualité des mots | Grilles sans formes fléchies rares, jugées publiables par l'auteur | ❌ avant la Phase 1 |
| Mots imposés | Mots obligatoires toujours placés, ou échec expliqué | Phase 3 |
| Qualité technique | CI verte ; couverture ≥ 70 % sur le moteur et le pipeline du lexique | Tests en place, couverture non mesurée |

## 7. Architecture (résumé)

Frontend Next.js ↔ API Flask ↔ PostgreSQL ; dictionnaire DELA chargé en mémoire dans un Trie ; moteur de génération par backtracking guidé. Détails : [ARCHITECTURE.md](ARCHITECTURE.md) et [ENGINE.md](ENGINE.md).
