# 📚 Lexique — Terminator

> Le dictionnaire commun utilisé par la recherche et la génération : d'où il vient, comment il est chargé, et comment il va être nettoyé.

## Aujourd'hui : le DELA

- **Fichier** : `backend/dela_clean.csv` (~55 Mo, 980 292 lignes), dérivé du DELA (dictionnaire électronique des formes fléchies du français).
- **Colonnes** (séparateur `;`) : forme en majuscules ; forme affichée (avec accents) ; description (toujours « Forme fléchie de … », donc **pas de vraie définition**).
- **Normalisation** (`DictionnaireTrie._normalize`) : majuscules, accents retirés, seuls les caractères alphanumériques gardés (espaces, tirets et apostrophes supprimés), 2 lettres minimum.
- **Résultat** : **714 092 mots distincts**, dont ~393 000 de 11 lettres ou moins.
- **Chargement** : au démarrage de l'API, tout le fichier est inséré dans un Trie en mémoire (`app.dela_trie`). Cela prend du temps et beaucoup de RAM.

| Longueur | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|----------|---|---|---|---|---|---|---|---|----|----|
| Mots | 91 | 604 | 2 580 | 8 310 | 19 827 | 37 843 | 60 214 | 80 091 | 91 780 | 92 380 |

### Le problème

Le DELA contient **toutes les formes fléchies** : conjugaisons, pluriels, mots très rares. Les grilles générées se remplissent de mots peu naturels (« ELIERA », « AUNES »…). Or la qualité des mots est la priorité pour un auteur de mots fléchés. Un dictionnaire plus petit rendrait aussi le solveur plus rapide.

Les dictionnaires **personnels**, eux, sont en base de données (voir [ARCHITECTURE.md](ARCHITECTURE.md)).

## Le pipeline (Phase 1a)

Code : `tools/lexicon/` (Python, bibliothèque standard uniquement). Décision : [ADR 0005](adr/0005-pipeline-du-lexique-et-decisions.md).

```bash
make lexicon-download   # télécharge et vérifie les sources (~411 Mo, une seule fois)
make lexicon-build      # construit la base locale (plusieurs minutes)
make lexicon-stats      # avancement de la curation
make lexicon-export     # produit le lexique curé
```

### Sources

| Source | Apporte | Licence |
|--------|---------|---------|
| `backend/dela_clean.csv` | La liste de mots et leurs formes affichées | — |
| [Lexique 3.83](http://www.lexique.org) | Fréquence (films et livres), lemme, catégorie grammaticale | CC BY-SA 4.0 |
| [Wiktionnaire](https://fr.wiktionary.org), extrait [kaikki.org](https://kaikki.org/frwiktionary/) | Définitions ; une forme fléchie est expliquée par son lemme | CC BY-SA 4.0 |

Les fichiers téléchargés vont dans `data/lexicon/raw/` (non versionné). Leurs empreintes sont consignées dans `data/lexicon/sources.lock.json` (versionné), qui dit exactement quelles données ont servi. `make lexicon-download` refuse un fichier dont l'empreinte a changé ; `python -m tools.lexicon download --refresh` met la source à jour.

### La base locale

`data/lexicon/build/lexicon.sqlite` (non versionnée, reconstructible à tout moment). Un mot par forme normalisée :

| Colonne | Contenu |
|---------|---------|
| `norm` | Forme normalisée, celle des grilles (`ETE`) |
| `display_forms` | Formes affichées (`["été", "étê"]`) |
| `zipf` | Fréquence sur l'échelle zipf : 3 = 1 occurrence par million, 6 = 1 pour 1 000 ; 0 si absent de Lexique |
| `lemma`, `pos` | Lemme et catégorie de l'emploi le plus fréquent |
| `definition` | Première définition du Wiktionnaire, dans la catégorie grammaticale donnée par Lexique ; pour une forme fléchie, « forme de X — définition de X » |
| `definition_kind` | `own` (définition du mot lui-même), `inflection` (forme fléchie expliquée par son lemme) ou vide |
| `suggestion` | Aide à la décision, voir ci-dessous |

Les noms propres, préfixes, suffixes et sigles du Wiktionnaire sont ignorés.

| Suggestion | Règle | Dans le tri ? | Mots |
|------------|-------|---------------|------|
| `keep` | zipf ≥ 3,5 (mot courant) | Non, gardé d'office | 12 963 |
| `likely_keep` | zipf ≥ 2,5 | Oui | 33 833 |
| `review` | Peu fréquent, ou absent de Lexique mais avec une définition propre | Oui | 121 054 |
| `likely_delete` | Absent de Lexique et sans définition propre (au mieux « forme fléchie de X ») | Oui, en priorité | 546 242 |

Chiffres de la construction du 15/09/2026. Le Wiktionnaire définit presque toutes les conjugaisons : seule une définition propre au mot distingue un mot rare mais réel d'une conjugaison obscure.

Mots de 8 lettres ou moins restant à trier : 65 830 `likely_delete`, 37 237 `review`, 16 907 `likely_keep`.

Les seuils se règlent à la construction (`--auto-keep-zipf`, `--likely-keep-zipf`) et sont consignés dans la base.

### Les décisions

`data/lexicon/decisions.csv`, **versionné**, en ajout seul :

```text
mot;decision;date;lot
AABAM;delete;2026-09-15T08:30:00+00:00;20260915083000-3f9a1c
OUVRAGE;keep;2026-09-15T08:30:04+00:00;20260915083004-b27e40
AABAM;undo;2026-09-15T08:30:09+00:00;20260915083000-3f9a1c
```

- `decision` : `keep`, `delete` ou `undo`. Une ligne `undo` annule tout son lot : annuler « supprimer ce mot et toutes ses formes » les restaure toutes.
- La décision porte sur la forme normalisée : supprimer `ETE` retire « été » et « étê » ensemble.
- La décision effective d'un mot est la dernière qui n'a pas été annulée.

### L'export

`make lexicon-export` écrit `data/lexicon/build/lexique_cure.csv` (`MOT;forme affichée;définition;zipf`), lisible par le Trie du backend.

- Par défaut, seuls les mots **supprimés par l'auteur** sont retirés.
- `python -m tools.lexicon export --exclude-suggested-deletes` retire aussi les mots suggérés `likely_delete` que l'auteur n'a pas gardés explicitement.

## La mini-app de curation (Phase 1b)

Code : `tools/curator/` (Flask + une page HTML/JS sans dépendance). Elle lit la base locale en **lecture seule** et n'écrit que dans `data/lexicon/decisions.csv`.

### Lancer

1. Construire la base une fois : `make lexicon-build`.
2. Choisir un code PIN (6 caractères minimum) dans `.env` : `CURATOR_PIN=...`.
3. Lancer :
   ```bash
   make curator
   ```
4. Ouvrir l'adresse affichée :
   - sur l'ordinateur : http://localhost:8765 ;
   - sur le téléphone, connecté au même Wi-Fi : http://<IP du Mac>:8765 (ajoutable à l'écran d'accueil).

### Trier

Une carte par mot : le mot et ses graphies, la définition (signalée quand ce n'est qu'une forme fléchie), la fréquence, la catégorie, le lemme et la suggestion.

| Action | Clavier | Téléphone |
|--------|---------|-----------|
| Supprimer | `←` | glisser à gauche ou bouton |
| Garder | `→` | glisser à droite ou bouton |
| Annuler la dernière action | `↓` ou `⌫` | bouton |
| Passer (revient en fin de file) | `↑` | bouton |
| Supprimer le mot et toutes ses formes | `Maj` + `←` | bouton |

- **Une touche maintenue ne décide qu'une fois.** Pas de confirmation : l'annulation est toujours possible, y compris pour une famille entière.
- **Suppression par famille** : le mot, son lemme et toutes les formes du même lemme. Les mots gardés et les mots très courants (`keep`) ne sont jamais supprimés de cette façon.
- **Ordre de la file** : mots les plus courts d'abord ; dans une longueur, `likely_delete`, puis `review`, puis `likely_keep`, du moins fréquent au plus fréquent. Filtres par longueur et par suggestion.
- **En haut de l'écran** : décisions du jour, série de jours consécutifs, mots restant à trier.

Les décisions sont écrites immédiatement. Pensez à commiter `data/lexicon/decisions.csv` de temps en temps.

### Sécurité

Le curateur est accessible depuis le réseau local : il ne démarre pas sans `CURATOR_PIN`.

- Blocage de 5 minutes après 5 codes erronés.
- Cookie de session `HttpOnly` et `SameSite=Strict`.
- En-tête obligatoire sur chaque écriture (protection CSRF).
- CSP stricte (aucun script externe ou inline).
- Base ouverte en lecture seule ; seules des décisions valides sur des mots connus sont acceptées.
- À ne lancer que sur un réseau de confiance (Wi-Fi domestique) : la connexion n'est pas chiffrée (HTTP).

## Prochaine étape (Phase 1c)

L'API chargera le lexique curé (`make lexicon-export`) derrière un flag de configuration ; la recherche affichera les définitions ; le générateur utilisera la fréquence. Voir [ROADMAP.md](ROADMAP.md) et l'issue #11.
