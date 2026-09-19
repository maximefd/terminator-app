# Benchmarks du générateur

Résultats produits par `backend/test_harness.py` (seeds fixes `0..N-1`, un Trie par format).

| Fichier | Rôle |
|---------|------|
| `baseline.json` | Référence versionnée. Toute modification du moteur doit être comparée à ce fichier. |
| `latest.json` | Dernière exécution locale (sortie par défaut du harness, non destinée à être commitée). |

## Lancer

Depuis `backend/` (Python 3.11) :

```bash
python test_harness.py --seeds 20 --time-budget 20 --output benchmarks/latest.json --html report.html
```

Le budget de 20 s correspond au budget par défaut de l'API (`GENERATION_TIME_BUDGET_S`) : le taux de succès mesuré est celui qu'on obtient réellement depuis l'interface.

`--restart-unit N` fixe l'unité des redémarrages en appels récursifs (`0` : un seul essai, comme avant la Phase 3). Sans l'option, le réglage du générateur s'applique (`DEFAULT_RESTART_UNIT_CALLS`). Le nombre d'essais de chaque seed est dans le champ `attempts`.

Autres réglages, tous facultatifs (sans l'option, le solveur applique son défaut) : `--min-safe-candidates` (seuil du forward checking), `--max-candidates` (candidats essayés par emplacement), `--frequency-mode` (place de la fréquence dans le tri : `none`, `exact`, `band`, `known`, `tiebreak`) et `--frequency-band`. Mesurer la fréquence exige `--dictionary` avec un lexique qui en porte une : `dela_clean.csv` n'a pas cette colonne.

## Lire les résultats

Pour chaque layout : taux de succès dans le budget, temps p50 / p95 / max, nombre de timeouts, backtracks moyens, puis le détail de chaque seed.

- Les **temps dépendent de la machine** : ne comparer que des exécutions faites sur la même machine (voir `environment` dans le JSON).
- Le **taux de succès sur beaucoup de seeds** est l'indicateur principal. Pour un layout difficile, le résultat d'une seed isolée ne veut presque rien dire (voir ci-dessous) : utiliser au moins 20 seeds.
- L'exécution est **reproductible** : même code + même dictionnaire + même seed ⇒ même grille.

## Baseline actuelle (septembre 2026 : redémarrages, index des candidats et validation croisée corrigée)

Machine : Docker (Python 3.11, 8 CPU, 4 Go), dictionnaire `dela_clean.csv` complet, 20 seeds, budget 20 s, exécution seule.

**Les 21 layouts du catalogue réussissent 20 fois sur 20** : 420 générations, 420 réussites (plafond de candidats à 300).

| Layout | Mots | Succès | p50 | p95 |
|--------|------|--------|-----|-----|
| 6x7-001 à 005 | 12-13 | 20/20 | 0,05 à 0,06 s | 0,10 à 0,19 s |
| 7x9-001 | 20 | 20/20 | 0,16 s | 0,44 s |
| 11x6-001 | 21 | 20/20 | 0,33 s | 1,09 s |
| 11x9-001 | 33 | 20/20 | 0,78 s | 3,32 s |
| 14x9-001 | 38 | 20/20 | 1,29 s | 3,41 s |
| 10x13-001 à 006 | 41-43 | 20/20 | 0,47 à 0,84 s | 1,49 à 5,53 s |
| 11x17-001 et 002 | 61-62 | 20/20 | 0,89 à 1,24 s | 3,44 à 3,67 s |
| 13x16-001 à 003 | 61-64 | 20/20 | 0,79 à 2,51 s | 2,87 à 10,08 s |
| 13x18-001 | 81 | 20/20 | 2,19 s | 8,72 s |

Historique sur les deux layouts d'origine :

| Étape | 6x7-001 | 11x6-001 |
|-------|---------|----------|
| Première baseline | 20/20, p95 5,4 s | 3/20 |
| Redémarrages (#19) | 20/20, p95 1,1 s | 11/20, p50 17,4 s |
| Index des candidats (#20) | 20/20, p95 0,29 s | 20/20, p50 3,1 s |

## Le mur des grandes grilles et sa cause (#57)

Ces grilles comptent 42 à 43 mots, contre 21 pour le 11×6. Diagnostic sur 10x13-002, 3 seeds, budget 30 s :

| Unité de redémarrage | Résultat |
|----------------------|----------|
| sans redémarrage | 3 échecs (1 essai, ~105 000 appels) |
| 300 | 3 échecs (~87 essais) |
| 1 500 | 3 échecs (~26 essais) |
| 5 000 | 3 échecs (~12 essais) |

Avec un **budget de 120 s** (six fois le budget de l'API), les trois grilles difficiles échouent encore : 10x13-001 après 333 essais et 373 000 appels, 10x13-002 après 255 essais, 10x13-003 après 319 essais. Ce n'est donc pas non plus une question de temps.

Ni le réglage des redémarrages, ni le budget, ni le vocabulaire (67 000 mots de 13 lettres, 92 000 de 10), ni la vitesse (~3 700 appels par seconde) n'expliquaient l'échec.

### La cause : les mots en cours d'écriture

Un balayage du catalogue a montré un mur net **entre 21 et 33 mots** : 100 % de réussite en dessous, 0 % au-dessus. Trop tôt et trop brutal pour une limite naturelle. En cause, `_is_placement_valid` : il reconstruisait la suite de lettres perpendiculaire et exigeait qu'elle existe au dictionnaire dès deux lettres, sans distinguer un mot **terminé** d'un mot **en cours d'écriture**. Deux rangées voisines traversant un emplacement de 5 cases y laissent « AB » : le solveur refusait, alors que le mot final pouvait être « TABLE ».

Les petites grilles referment leurs croisements tout de suite, ce qui masquait le défaut. Depuis la correction (seuls les mots terminés sont vérifiés), les 16 layouts passent à 20/20, 13×16 compris. Les optimisations envisagées avant d'avoir trouvé la cause — propagation des lettres possibles, tri anticipatif des candidats, retour arrière dirigé par le conflit — restent des pistes valables mais ne sont plus nécessaires.

## La fin de partie des grandes grilles (#61, septembre 2026)

Après l'ajout de cinq grands layouts au catalogue, trois n'atteignaient pas le budget : 13x16-002 15/20, 13x18-001 17/20, 13x16-003 19/20. L'issue accusait l'unité de redémarrage, calibrée sur le 11×6. **C'était faux**, et les données déjà mesurées suffisaient à le montrer.

| Question | Mesure | Réponse |
|----------|--------|---------|
| Les essais sont-ils coupés trop tôt ? | seeds en échec : 61 à 69 essais, 46 000 appels en 20 s | Non : ni les essais ni le temps ne manquent |
| Un état fuit-il entre les redémarrages ? | mots disponibles au début de chaque essai | Non : 651 990, invariablement |
| Les redémarrages diversifient-ils ? | débuts d'essai distincts | Oui, imparfaitement : 21 et 24 sur ~62 |
| Où la recherche bute-t-elle ? | profondeur maximale atteinte | **62 emplacements sur 64**, encore et encore |

La recherche n'échouait donc pas au début : elle arrivait à deux mots de la fin. Les emplacements restants avaient encore 4 à 13 candidats — pas d'impasse combinatoire. En cause, `MIN_SAFE_CANDIDATES = 3` : le forward checking refusait tout placement laissant un emplacement croisé avec moins de trois candidats, alors qu'en fin de grille presque tous les emplacements restants sont dans ce cas. La clôture était interdite par construction, et chaque redémarrage jetait 62 placements corrects pour repartir de zéro.

Le seuil est passé à **2**, le minimum imposé par l'invariant du solveur (un emplacement entièrement déterminé par ses croisements n'a qu'un candidat ; avec un seuil ≥ 2 il est rejeté, ce qui garantit que chaque emplacement est rempli explicitement).

| Seuil | Succès (21 layouts, 20 seeds) | 13x18-001 p50 | Petits formats, p50 moyen |
|-------|-------------------------------|---------------|---------------------------|
| 3 | 411/420 | 12,70 s | 0,167 s |
| **2 (retenu)** | **420/420** | **1,99 s** | **0,127 s** |

Aucun layout n'est dégradé, et **tout accélère**, y compris les petits formats qui n'avaient aucun problème : un seuil élevé ne protégeait pas la recherche, il l'envoyait explorer des branches plus longues.

## Fréquence des mots et plafond de candidats (Phase 3, septembre 2026)

Le lexique curé porte une quatrième colonne, la fréquence zipf, que `DictionnaireTrie` jetait. La roadmap demandait de trier les candidats par fréquence pour obtenir des mots plus naturels. Deux pièges ont failli fausser la mesure :

- **le benchmark était aveugle** : il tourne sur `dela_clean.csv`, qui n'a pas de colonne de fréquence. Le tri par fréquence y est rigoureusement sans effet. Les mesures ci-dessous utilisent donc `--dictionary` avec le lexique curé ;
- **le taux de succès ne dit rien de la qualité**, qui est justement le sujet. Le harness rapporte désormais `mean_zipf` (fréquence moyenne des mots placés) et `unknown_share` (part de mots absents des corpus). Une première tentative comparait un lexique amputé de sa colonne de fréquence à un lexique complet : les deux conditions différaient par l'ordre **et** par l'instrument de mesure, le résultat ne voulait rien dire. D'où `--frequency-mode`, qui change l'ordre sans toucher aux données.

Mesures sur 7 layouts (6×7, 11×9, 13×18), 20 seeds, budget 20 s, lexique curé :

| Mode | Succès | Zipf moyen | Inconnus | p50 11×9 | p50 13×18 |
|------|--------|-----------|----------|----------|-----------|
| `none` | 140/140 | 2,58 | 33,4 % | 0,49 s | 2,77 s |
| `exact` | 139/140 | 3,73 | 15,4 % | 1,23 s | 10,73 s |
| `band` 1,0 | 138/140 | 3,64 | 16,1 % | 0,85 s | 6,93 s |
| `band` 0,5 | 135/140 | 3,69 | 16,1 % | 0,75 s | 5,32 s |
| `known` | 137/140 | 3,10 | 14,1 % | 0,73 s | 9,10 s |
| `tiebreak` | 140/140 | 2,66 | 32,3 % | 0,47 s | 3,02 s |

Deux hypothèses réfutées : **les paliers** ne restaurent pas la solvabilité (0,5 descend même à 15/20), et **le classement binaire connu/inconnu** non plus — `known` est dominé par `exact` en succès comme en zipf. `tiebreak` (score de lettres d'abord) ne coûte rien mais n'apporte rien. Le constat qui reste : dès que la fréquence passe devant le score de lettres, quelle qu'en soit la finesse, la recherche se ferme. Le score de lettres n'est pas décoratif, il garde les croisements ouverts.

### Le plafond de candidats, lui, était bien en cause — à moitié

Trié par fréquence, le « top 100 » d'un emplacement devient « les 100 mots les plus courants », qui ne sont pas forcément ceux qui s'emboîtent. Élargir le plafond ramène le 13×18 de 10,73 s à 5,97 s sans perte de qualité (500 n'apporte rien de plus). **Et c'est un gain sec même sans fréquence** : sur les 21 layouts avec le DELA brut, 420/420 dans les deux cas, mais médiane 0,91 s → 0,71 s et p95 du 13×18 de 14,57 s à 8,72 s. `MAX_CANDIDATES_PER_SLOT` passe donc de 100 à **300**.

### Pourquoi le tri par fréquence n'est pas activé par défaut

Sur les **21 layouts** (et non les 7 du sondage), `exact` avec le plafond à 300 donne 409/420 : sept layouts sous 20/20, dont 13x16-002 à 17/20 (85 %) et les deux 11×17 à 18/20 (90 %). Le critère de sortie de la Phase 3 — ≥ 95 % par layout — n'est pas tenu. Le sondage à sept layouts ne le montrait pas : il annonçait 19/20 sur le seul layout en difficulté.

Le tri reste disponible (`frequency_mode` dans la requête, `--frequency-mode` au benchmark) pour qui accepte l'échange : deux fois moins de mots absents des corpus contre des grandes grilles qui échouent une fois sur six.

## Mots obligatoires : la mesure qui manquait (Phase 3, septembre 2026)

L'ADR 0007 demandait que la baseline comporte des cas avec mots obligatoires. Elle n'en avait aucun : le moteur des mots imposés, raison d'être de la Phase 3, n'avait jamais été mesuré au budget.

**Protocole.** `--must-words N` impose N mots par grille, tirés selon la seed parmi les mots **courants** (zipf ≥ 3) du lexique, à des longueurs **distinctes** présentes dans le layout. Trois choix délibérés :

- des mots *courants*, parce que c'est ce qu'un auteur impose — tirer au hasard dans 700 000 formes mesurerait des demandes que personne n'écrirait ;
- des longueurs *distinctes*, sinon la vérification préalable refuserait la demande et on mesurerait cette validation au lieu du solveur ;
- des mots tirés *par seed*, pour mesurer une distribution et non un coup de chance. Le tirage dérive d'une chaîne (`layout:seed`), donc reproductible d'une machine à l'autre.

**Résultats** (21 layouts, 20 seeds, budget 20 s, lexique curé, exécutions seules) :

| Mots imposés | Succès | Échecs par mot non placé | Layouts sous 20/20 |
|--------------|--------|--------------------------|--------------------|
| 0 (témoin) | 418/420 — 99,5 % | 0 | 2 |
| 1 | 402/420 — 96 % | 11 | 12 |
| **3** | **169/420 — 40 %** | **139** | **21** |

**Un seul mot imposé coûte déjà 4 points ; trois font s'effondrer la génération à 40 %**, et aucun layout ne tient le critère. Le 11×6 descend à 2/20, le 10x13-003 à 1/20.

Les mots en cause sont ordinaires : `NEZ` refusé sur un 6×7, `TAQUINER`, `EXPLICITE`, `BIBLIOTHEQUES` sur des 10×13. Ce ne sont pas des demandes absurdes, c'est l'usage normal de la fonctionnalité.

La majorité des échecs sont des **mots non placés**, pas des dépassements de budget : le solveur ne trouve pas de grille contenant le mot, il ne manque pas de temps. Allonger le budget n'y changerait donc rien.

### Le témoin n'est pas à 420/420

Sur le lexique curé, la génération libre donne **418/420** : `13x16-002` (seed 4) et `13x18-001` (seed 17) dépassent le budget. La baseline versionnée, mesurée sur `dela_clean.csv`, donne 420/420. Les deux sont exacts — le lexique curé est plus petit, donc plus contraint. C'est le curé que charge l'API.

## Index des candidats (#20, septembre 2026)

Le profil d'une génération 11×6 montrait 94 % du temps dans `get_candidates` : parcours du Trie par motif (5,9 millions de nœuds visités pour 1 295 recherches), puis filtrage des mots disponibles, avec un cache vidé à chaque placement. L'index par (position, lettre) en ensembles de bits (`engine/pattern_index.py`) calcule les mêmes candidats, **dans le même ordre**, par ET binaire ; le solveur ne fait que les compter pour choisir le slot et pour le forward checking.

- **Mêmes grilles** : chaque seed réussie de la baseline précédente suit exactement la même trajectoire (mêmes appels récursifs, mêmes essais), 2 à 6 fois plus vite (ex. 11x6-001 seed 0 : 8,0 s → 3,1 s).
- **Plus de réussites** : les essais plus rapides tiennent dans le budget ; le 11×6 passe de 11/20 à 20/20.
- Coût : construction de l'index au premier usage d'un lexique (1,4 s sur le DELA complet), puis 0,3 s par génération pour marquer les mots disponibles.
- Prochains points chauds du profil : `_get_slot_pattern`, `words_in` et les appels `logging.debug` formatés même quand ils ne s'affichent pas.

## Ce qu'on a appris en établissant la première baseline

`amelioration-generate.md` indiquait « 11×6 : 100 % de succès en ~9 s ». Ce chiffre venait de **4 seeds (0 à 3) chanceuses**, pas d'une propriété du moteur :

- Le moteur a été vérifié à l'identique : le nouveau code, lancé avec l'ancien harness et les mêmes conditions, reproduit exactement les temps de l'ancien code (9,2 s / 9,5 s / 28,4 s).
- La réussite dépend avant tout de la **trajectoire aléatoire** de la seed (mélange du top 20 % des candidats). Décaler le flux aléatoire d'un seul tirage (l'ancien code tirait le layout au sort avant de résoudre) suffit à transformer 3 succès en 3 timeouts sur les mêmes seeds. L'ordre des mots dans le Trie a un effet secondaire.
- Sur 20 seeds, le taux réel est de **15 % en 20 s**. Les grilles réussies le sont vite (3,6 à 15,7 s) : le solveur trouve rapidement ou s'enlise.

Conséquence pour la [roadmap](../../docs/ROADMAP.md) (Phase 3) : ce profil « vite ou jamais » est exactement le cas où les **redémarrages aléatoires** (plusieurs trajectoires courtes dans le budget plutôt qu'une longue) améliorent fortement le taux de succès. À combiner avec le lexique curé (moins de mots rares) et un index des candidats par (position, lettre).

## Redémarrages : choix de l'unité (#19, septembre 2026)

L'essai n°i s'arrête après `unité × luby(i)` appels récursifs. Le seuil est compté en appels et non en secondes : même seed ⇒ même grille, quelle que soit la machine. Mesures sur 20 seeds, budget 20 s, dictionnaire complet (deux exécutions à la fois, sur 8 CPU) :

| Unité (appels) | 6x7-001 : succès, p95 | 11x6-001 : succès | Essais par seed sur 11x6 |
|----------------|-----------------------|-------------------|--------------------------|
| sans redémarrage | 20/20, 5,4 s | 3/20 | 1 |
| 1 000 | 20/20, 2,1 s | 3/20 | 3 à 8 |
| **300 (retenu)** | **20/20, 1,3 s** | **7/20** | 2 à 15 |
| 100 | 20/20, 2,5 s | 2/20 | 6 à 26 |
| 50 | 20/20, 2,8 s | 2/20 | 4 à 31 |

⚠️ Ces mesures ne portent que sur **deux layouts**. Rien ne dit que 300 appels conviendra à un 15×8 ou à un 7×4 : la valeur sera réexaminée quand le catalogue s'étoffera (#57), en comparant plusieurs unités avec `--restart-unit` sur les nouveaux formats.

- Trop long (1 000) : trop peu d'essais tiennent dans le budget.
- Trop court (100, 50) : les essais s'arrêtent avant d'aboutir ; le 6×7, qui réussit souvent en quelques centaines d'appels, ralentit.
- Lancé seul (baseline ci-dessus), le réglage de 300 appels atteint 11/20 sur le 11×6 : le budget est en secondes, deux exécutions simultanées font donc moins d'essais. Ne comparer que des exécutions faites dans les mêmes conditions.
- Sur le 11×6, un appel récursif coûte environ 40 ms : 94 % du temps passe dans la recherche de candidats par le Trie (profil `cProfile`). C'est la limite suivante (#20) : plus d'appels par seconde, donc plus d'essais dans le budget.
