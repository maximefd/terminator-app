# 0005 — Pipeline du lexique et fichier de décisions versionné

- Statut : acceptée
- Date : 2026-09-15

## Contexte

- Le DELA compte 714 092 mots distincts, dont une grande majorité de formes fléchies rares. La qualité des grilles en souffre.
- L'auteur veut **décider lui-même** quels mots supprimer, définitivement, un peu chaque jour, depuis son téléphone ou son ordinateur. Trier 714 000 mots à la main est impossible sans aide : tri par fréquence, définition affichée, suggestion.
- Les sources d'aide sont externes et volumineuses : Lexique 3.83 (26 Mo) et un extrait du Wiktionnaire (385 Mo compressés). L'URL du Wiktionnaire n'est pas versionnée.

## Décision

1. **Pipeline** `tools/lexicon/` en Python sans dépendance externe, exécuté dans Docker (Python 3.11) :
   - `download` : télécharge les sources dans `data/lexicon/raw/` (non versionné), empreintes consignées dans `data/lexicon/sources.lock.json` (versionné) ;
   - `build` : construit `data/lexicon/build/lexicon.sqlite` (non versionné, reconstructible). Pour chaque mot : formes affichées, fréquence (zipf), lemme, catégorie, définition, suggestion (`keep`, `likely_keep`, `review`, `likely_delete`) ;
   - `export` : produit le lexique curé, lisible par le Trie du backend ;
   - `stats` : avancement de la curation.
2. **Source de vérité** : `data/lexicon/decisions.csv` (`mot;decision;date;lot`), versionné, en **ajout seul**. Le mot est la forme normalisée utilisée dans les grilles. Une annulation ajoute des lignes `undo` pour tout un lot (ex. un mot et toutes ses formes) : l'historique reste lisible dans `git diff`.
3. **Export conservateur par défaut** : seules les suppressions décidées par l'auteur sont retirées. Retirer aussi les mots suggérés `likely_delete` est une option explicite (`--exclude-suggested-deletes`).
4. Les mots très fréquents (`keep`, zipf ≥ 3,5) ne passent pas par le tri. Les seuils sont configurables et consignés dans la base.

## Conséquences

- La base locale peut être supprimée et reconstruite à tout moment. Seules les décisions de l'auteur ont de la valeur et sont versionnées.
- Les décisions portent sur les formes normalisées : supprimer `ETE` supprime « été » et « étê » ensemble, comme dans les grilles.
- La mini-app de curation (Phase 1b) et l'API (Phase 1c) liront la base et l'export ; aucune ne modifie la base.
- Les données dérivées de Lexique et du Wiktionnaire sont sous CC BY-SA : à respecter si le lexique curé est un jour redistribué (Phase 6).
