# Changelog

Toutes les évolutions notables du projet. Format inspiré de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/), versions selon [SemVer](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté
- **Suivi des erreurs avec Sentry**, API et navigateur, **inactif sans DSN** (`SENTRY_DSN`,
  `NEXT_PUBLIC_SENTRY_DSN`) : rien ne part en développement. Seules les erreurs sont envoyées, sans cookies,
  en-têtes d'authentification, corps de requête, variables locales ni adresse IP, et le jeton des liens reçus
  par e-mail est retiré des adresses. Le gestionnaire d'erreurs de l'API interceptant tout, il transmet
  lui-même l'exception à Sentry. Vérifié par un vrai rapport dans les tests (backend) et dans un navigateur.
- **Journaux structurés** : JSON en production (`LOG_FORMAT`, texte en développement), une ligne par
  événement avec la méthode, le chemin et l'identifiant de la requête. Cet identifiant reprend `CF-Ray`
  (Cloudflare) et revient dans l'en-tête `X-Request-ID`. gunicorn suit le même format, journal d'accès compris
  (adresse du visiteur, chemin **sans query string** : un jeton n'y figure jamais). Vérifié sur l'image en
  configuration de production : toutes les lignes sont du JSON, aucune n'est en double.
- **Mot de passe oublié et confirmation de l'adresse** ([ADR 0014](docs/adr/0014-emails-du-compte.md)) : un
  lien par e-mail pour choisir un nouveau mot de passe (une heure, une seule fois, sans révéler si le compte
  existe), et un lien de confirmation envoyé à l'inscription, redemandable depuis « Mon compte ». Liens signés,
  sans table ; migration `0005` (`email_verified_at`). En développement, les e-mails arrivent dans **Mailpit**
  (http://localhost:8025) et ne partent jamais ; en production, par le relais SMTP du prestataire.
- **Revue des licences** ([docs/LICENCES.md](docs/LICENCES.md)) : sources linguistiques, polices, dépendances
  et dépôt public, avec ce que chaque licence demande. Le DELA versionné est sous LGPLLR, qui impose de
  joindre sa licence : c'est fait (`backend/DELA-NOTICE.md`, `backend/LGPLLR.txt`), comme la licence OFL de
  la police des grilles (`frontend/public/fonts/OFL.txt`). Aucune dépendance sous GPL ou AGPL. Restent à
  trancher : la provenance des layouts recopiés de livres, et le dépôt public ou privé.
- **Page « Mon compte »** (#79) : l'adresse e-mail, ce que le compte contient, et sa suppression — mot
  de passe redemandé, confirmation qui dit ce qui disparaît, déconnexion et retour à l'accueil. Nouvel
  endpoint `GET /api/users/me`.
- `make bench-load` (`backend/benchmarks/load_profile.py`) : profil de charge de l'API — RAM après
  chargement, CPU et durées par génération, générations simultanées en threads et en processus — dans un
  conteneur de 2 CPU et 2 Go. Ce sont les mesures de l'[ADR 0013](docs/adr/0013-cible-hebergement-production.md),
  à refaire sur le VPS la première semaine.
- **Sauvegardes de la base** : `make db-backup` (dump PostgreSQL compressé dans `backups/`, chiffré par
  `age` si `BACKUP_AGE_RECIPIENT` est défini, rotation à 30 jours) et `make db-restore-check FILE=…`,
  qui restaure la sauvegarde dans une base jetable, compte les lignes des tables puis la supprime — la
  base en service n'est jamais touchée. Le serveur n'aura que la clé publique : il chiffrera ses
  sauvegardes sans pouvoir les relire ([ADR 0013](docs/adr/0013-cible-hebergement-production.md)).
- [ADR 0013](docs/adr/0013-cible-hebergement-production.md) — **cible d'hébergement de production** : un VPS
  OVH derrière Cloudflare (tunnel, frontend statique sur Pages), environ 65 € par an, choisi sur mesures
  (RAM, CPU par génération, concurrence, PyPy). L'hébergement mutualisé est écarté : il aurait partagé ses
  ressources et son utilisateur système avec un site en activité.
- **gunicorn** pour la production (`backend/gunicorn.conf.py`, commande par défaut de l'image) : 3 workers
  synchrones, application chargée une fois avant de les créer. Le développement reste sur `python run.py`,
  qui recharge le lexique du curateur.
- **Places de génération** : au plus 2 générations à la fois (une par cœur) et une seule par visiteur,
  429 au-delà (« Le générateur est occupé »). Les verrous sont des fichiers, communs à tous les workers et
  rendus si l'un d'eux meurt. Le rate limiting comptait les requêtes par minute, pas leur recouvrement :
  quatre générations sur deux cœurs doublaient la durée médiane.
- `make preview-remote` : tunnel Cloudflare **temporaire** pour faire tester l'app à quelqu'un à
  distance sans qu'il clone le repo, sans rien déployer (cohérent avec
  [ADR 0004](docs/adr/0004-pas-de-deploiement-en-ligne.md)) — l'URL n'existe que tant que la commande
  tourne. Corrige au passage `allowedDevOrigins` (mal placé sous `experimental`, ignoré depuis
  Next 15.5) pour que l'accès distant au serveur de dev fonctionne à nouveau.
- Effacer des lettres dans l'éditeur ([ADR 0012](docs/adr/0012-grille-modifiable.md)) :
  `Retour arrière` efface en remontant — maintenu, il vide le mot — et `Suppr` efface sur place. Les
  trous sont un **état de travail** : le mot garde sa longueur (`P?RTE`, jamais `PRTE`), il est dit
  **inachevé** plutôt qu'inconnu, et les propositions **comblent les trous** en gardant les lettres
  laissées en place. Un bouton bascule vers « remplacer le mot » quand on veut repartir de zéro, un
  autre efface le mot entier.
- **Annuler et rétablir** dans l'éditeur de lettres (boutons et `Ctrl+Z` / `Ctrl+Y`), sur les
  cinquante dernières modifications de la session.
- Retouche d'une grille conservée ([ADR 0012](docs/adr/0012-grille-modifiable.md)) : l'auteur change une
  lettre à la main — le `O` de PORTE devient un `E` — et **les mots se recalculent** à partir de la grille.
  Une lettre appartenant toujours à deux mots, la correction en touche deux ; les emplacements, eux, ne
  bougent jamais. Le résultat est **vérifié sans être censuré** : un mot absent du lexique est souligné
  dans la grille, listé dans le panneau, et posé quand même — avec un bouton pour le ranger dans le
  dictionnaire de son choix. `POST /api/grids/<id>/suggestions` propose les mots qui entrent à un
  emplacement **sans casser ses croisements** : c'est la cohérence d'arc du solveur ramenée à une case.
- Bloc-notes par grille : les idées viennent avant les définitions, et rarement en une fois. Enregistré au
  fil de la frappe, comme les définitions.
- Grilles conservées à l'échelle : recherche par nom, filtres (format, définitions complètes ou non,
  archivées), tri, et **archivage** — une grille rangée sort de la liste de travail sans quitter la base.
  L'affichage passe en cartes, chacune montrant l'avancement de ses définitions.
- Définitions composées comme dans les magazines (#27) : **capitales accentuées**, centrées, en gras —
  le gras se coupe d'un bouton, et le réglage vaut pour l'écran comme pour le PDF. La coupe des lignes
  suit la mesure : une capitale d'Archivo Narrow fait **0,64 em** contre 0,42 en bas de casse, et une
  définition trop longue fait **rétrécir sa police** plutôt que gagner une ligne — c'est ce qui évite
  « IL DONNE / LA / CADENCE » au profit de « IL DONNE / LA CADENCE ». La saisie, elle, reste telle que
  l'auteur l'a tapée.
- Échecs répétés expliqués (#73) : après deux tentatives infructueuses, l'écran calcule ce que cela veut
  dire — « à 66 % par tentative, trois échecs de suite n'arrivent qu'une fois sur 26 : l'estimation ne
  colle pas à vos mots » — et propose les trois sorties qui changent vraiment quelque chose. L'estimation
  dit désormais qu'elle vaut **par tentative**, sur quoi elle a été mesurée, et **quels mots imposés sont
  absents du lexique** : ceux-là se placent, mais tous leurs croisements devront venir du lexique.
- Les mots s'ajoutent à la chaîne : **Tab** valide le mot saisi et laisse le curseur en place, comme Entrée.
- Saisie des définitions et export (Phase 5, #27) : sur une grille conservée, un écran **Définitions**.
  On écrit **sur la grille remplie** — définir un mot qu'on ne voit pas n'a pas de sens — en cliquant une
  case ou un mot de la liste ; **Tab** et **Entrée** passent au suivant, dans l'ordre de lecture de la
  grille, si bien qu'une grille entière se définit sans lâcher le clavier. Enregistrement au fil de la
  frappe (`PATCH /api/grids/<id>`, 200 définitions au plus, 120 caractères chacune ; une grille d'autrui
  répond 404). Trois sorties : **PDF vectoriel**, **PDF + solution** (seconde page du même document) et
  **fichier de travail JSON**. La page de solution ne porte ni flèche ni définition : elle sert à vérifier
  des lettres. Le PDF est dessiné à partir du SVG de l'écran, avec la **police du dessin embarquée** —
  une étroite de labeur versionnée dans le dépôt, la même à l'écran et sur le papier. Deux garde-fous :
  une définition **trop longue pour sa case** est signalée pendant qu'on l'écrit (elle serait rognée à
  l'impression, et le découvrir sur le papier serait pire), et la grille se **renomme** depuis son titre. Une bascule **Édition / Aperçu imprimé** montre à tout moment ce qui sortira sur le papier, sans passer par l'export.
- Flèches et cases définitions (Phase 5, #26) : la grille se dessine désormais en **SVG**, avec les cases
  définitions, leurs flèches, et une bascule **Solution / Grille vierge**. Les flèches ne sont pas encodées
  dans les layouts ([ADR 0006](docs/adr/0006-format-des-layouts.md)) : le moteur les déduit de la géométrie
  (`backend/engine/arrows.py`) — définition à gauche pour un mot horizontal, au-dessus pour un mot vertical,
  et flèche coudée le long des bords. Mesuré sur les 21 layouts et 821 mots du catalogue : **aucun mot sans
  case où se définir**, **jamais plus de deux définitions par case**, et dans une case qui en porte deux,
  l'une sort toujours par la droite et l'autre par le bas — c'est ce qui permet de la couper en deux moitiés
  sans arbitrage. Les tests le vérifient layout par layout, pour que l'ajout d'une mise en page bancale se
  voie tout de suite. Une grille conservée avant cette version reçoit ses flèches à la relecture : elles se
  recalculent au lieu d'être stockées.
- Parcours end-to-end et accessibilité en CI (Phase 4, #25) : un travail `e2e-ci` démarre PostgreSQL et
  l'API, puis joue les parcours Playwright (inscription, dictionnaires, génération et conservation d'une
  grille) et **axe** sur chaque écran (WCAG A et AA). Premier verdict d'axe : les pages de connexion et
  d'inscription n'avaient **aucun titre de document** — composants clients, elles ne pouvaient pas en
  déclarer ; elles sont désormais une page serveur qui porte ses métadonnées.
- Grilles conservées (Phase 4, #24) : une grille générée se garde, se retrouve et se supprime —
  `POST /api/grids`, `GET /api/grids`, `GET /api/grids/<id>`, `DELETE /api/grids/<id>`, page **Mes grilles**.
  La grille est stockée **telle qu'elle a été produite**, et non rejouée à partir de sa seed : le lexique est
  curé au fil des semaines et le catalogue de layouts s'enrichit, si bien que la même seed ne redonnerait pas
  la même grille plus tard. 200 grilles par compte au plus ; une grille d'autrui répond 404.
- Migrations de schéma Alembic ([ADR 0010](docs/adr/0010-migrations-de-schema.md), #24) : `db.create_all()`
  ne savait que créer les tables manquantes — ni ajouter une colonne, ni signaler que le modèle et la base
  avaient divergé. Deux révisions : le schéma d'avant Alembic, puis les grilles conservées. Une base de
  développement existante est **marquée** à la première révision au lieu d'être recréée, puis mise à niveau.
- Audit UX des écrans existants ([docs/AUDIT-UX.md](docs/AUDIT-UX.md), #21) et ses corrections : la
  recherche explique sa syntaxe et propose trois motifs cliquables au lieu d'un champ muet ; les états vides
  disent quoi faire ; les dictionnaires personnels gagnent une page, un bouton de suppression (l'API le
  permettait, l'interface non), des définitions visibles dans la liste, et des intitulés là où il n'y avait
  que des icônes ; connexion et inscription montrent leur attente. Deux frictions restent, avec leur issue :
  les pages légales décrivent un produit qui n'existe pas (#78) et on ne peut pas supprimer son compte (#79).
- Parcours Playwright des dictionnaires (`frontend/tests/dictionaries.spec.ts`) : créer, ajouter un mot avec
  sa définition, supprimer le mot puis le dictionnaire, et vérifier qu'un dictionnaire reste actif.
- Page d'accueil (Phase 4, #22) : `/` explique ce qu'est Terminator au lieu d'ouvrir directement sur la
  recherche. Trois blocs — trouver le mot manquant, remplir une grille, vos dictionnaires — chacun avec un
  exemple **vrai** : le motif `P??LE` avec cinq des dix mots qu'il renvoie réellement, et une grille 6×7
  réellement produite par le moteur (seed 99, PIANO imposé). Le mode invité est dit explicitement : recherche
  et génération marchent sans compte, le compte ne sert qu'à garder les dictionnaires.
- Page `/dictionaries` (Phase 4, #22) : les dictionnaires personnels ont enfin une adresse à eux. Ils
  n'existaient que dans la colonne de droite de la recherche, et seulement une fois connecté.
- Écran de génération (Phase 4, #23) : tout ce que la Phase 3 avait construit devient manipulable.
  - **liste de mots ordonnée** (glisser-déposer, plus des boutons ↑/↓ pour le clavier) : les mots du haut sont
    les plus importants, et chaque mot se bascule entre **obligatoire** (la grille échoue sans lui) et
    **souhaité** (placé s'il rentre, jamais bloquant) ;
  - **difficulté annoncée pendant la saisie** ([ADR 0009](docs/adr/0009-annoncer-la-difficulte.md)) : taux de
    réussite estimé, mot qui pèse le plus et raison, mise à jour après chaque frappe ;
  - **choix des dictionnaires thématiques** quand on est connecté, les mêmes que dans la recherche par motif ;
    le dictionnaire actif est signalé comme toujours inclus, puisque l'API l'ajoute d'office ;
  - **refus expliqués** : un mot trop long pour toute mise en page, un mot que le solveur n'a pas su croiser et
    un dépassement de budget ne disent pas la même chose et ne s'affichent plus pareil ;
  - **provenance des mots** dans la grille produite : cases colorées par pool et trois listes (obligatoires,
    souhaités, lexique), avec le ratio de mots voulus atteint.
  Reste hors périmètre : le **choix du layout dans un format** et le **rejeu d'un seed**, qui demandent
  `layout_id` dans le contrat d'API ([ADR 0007](docs/adr/0007-contrat-de-generation.md)).
- `POST /api/grids/difficulty` ([ADR 0009](docs/adr/0009-annoncer-la-difficulte.md), #73) : ce que coûtent des mots imposés, **sans générer**. Pour chaque mot, son niveau et pourquoi il est coûteux (longueur, lettres rares) ; pour la demande, un taux de réussite estimé, le mot qui pèse le plus, et l'issue proposée — le passer en mot **souhaité**, où il sera placé s'il rentre sans faire échouer la grille. Les taux sortent d'une table de 4 700 générations mesurées, pas d'une intuition ; au-delà de trois mots, rien n'ayant été mesuré, le taux à trois sert de borne haute et l'est signalé (`measured: false`). Plafonné comme la recherche (120/min) : il est appelé à chaque frappe. L'estimation tient compte de la **taille de grille** choisie (champ `size`), dont l'effet mesuré **s'inverse selon la demande** : pour des mots courts la petite grille gagne (100 % contre 77 %), pour des mots longs la grande (31 % contre 13 %).
- Benchmark : `--must-max-length` (plafonne la longueur des mots imposés) et `--layout-order`. Le plafond corrige un **biais de mesure** : sans lui, les grands formats recevaient des mots plus longs, donc plus durs, et la comparaison entre tailles était faussée. À demande égale, trois mots imposés de 6 lettres au plus réussissent 67 % du temps contre 39 % sans plafond — **c'est la longueur des mots qui domine**, pas leur nombre ni la taille de la grille ([mesures](backend/benchmarks/README.md), #73).
- Benchmark avec mots obligatoires (`--must-words N`) : N mots courants par grille, de longueurs distinctes présentes dans le layout, tirés selon la seed et reproductibles. Comble le trou que l'[ADR 0007](docs/adr/0007-contrat-de-generation.md) signalait — le moteur des mots imposés n'avait jamais été mesuré. **Résultat : 1 mot imposé fait tomber le succès de 99,5 % à 96 %, 3 mots le font tomber à 40 %**, tous les layouts sous le critère ([mesures](backend/benchmarks/README.md)). Les échecs sont majoritairement des mots non placés, pas des dépassements de budget.
- Dictionnaires thématiques dans la génération (Phase 3, [ADR 0007](docs/adr/0007-contrat-de-generation.md)) : `wish_dictionary_ids` verse les mots des dictionnaires choisis au pool « souhaité », en plus du dictionnaire actif. Dix au plus, et **uniquement ceux de l'utilisateur connecté** : tout autre dictionnaire répond 404, sans révéler son existence.
- Fréquence des mots dans le moteur (Phase 3) : le lexique curé porte une colonne zipf que le chargeur jetait. Elle est désormais lue, et `frequency_mode` (requête d'API, `--frequency-mode` au benchmark) choisit la place de la fréquence dans le tri des candidats. **Désactivé par défaut** : mesuré, le tri par fréquence ramène les mots absents des corpus de 33 % à 17 % des mots placés, mais fait tomber sept layouts sous 20/20 — sous le critère de la Phase 3. Le benchmark rapporte maintenant la qualité (`mean_zipf`, `unknown_share`), sans quoi rien ne mesurerait l'effet recherché ([mesures](backend/benchmarks/README.md)).
- Pipeline du lexique (`tools/lexicon/`, Phase 1a) :
  - téléchargement de Lexique 3.83 et du Wiktionnaire avec empreintes consignées ;
  - base locale (fréquence, lemme, définition, suggestion) ;
  - décisions de curation versionnées avec annulation par lot ;
  - export du lexique curé ; statistiques d'avancement ;
  - ADR 0005.
- Mini-app de curation du lexique (`tools/curator/`, `make curator`, Phase 1b) :
  - une carte par mot : définition, fréquence, lemme, suggestion ;
  - une touche par décision (← supprimer, → garder, ↓ annuler, ↑ passer, Maj + ← toute la famille) ;
  - glisser sur téléphone ;
  - accès par code PIN ; statistiques du jour et série.
- Curateur :
  - motivation : objectif du jour, série, niveaux, 14 badges, combos, fenêtre de progression avec les 7 derniers jours ;
  - `make curator-bg`, `curator-stop` et `curator-logs` pour le lancer en arrière-plan ;
  - accès hors du Wi-Fi documenté avec Tailscale.
- Lexique curé dans Terminator (Phase 1c) :
  - l'API charge le lexique curé s'il existe et le recharge à chaud quand il change ;
  - le curateur l'exporte tous les 500 mots triés et propose de tester les grilles ;
  - `GET /api/status` indique le lexique chargé.
- Format de layout v1 (Phase 2, #12, ADR 0006) :
  - `x` = case définition, `-` = case lettre ; l'ancien format `#` / `.` reste lu ;
  - caractère inconnu, lignes de longueurs différentes ou taille différente du dossier : erreur qui indique la ligne et la colonne ;
  - `convert_layouts.py` convertit les anciens fichiers ;
  - identifiant déduit du chemin (`11x6-001`).
- Validateur de layouts (Phase 2, #13) :
  - `make layouts-check` et étape de CI ;
  - erreurs : case lettre isolée, taille ou nom de fichier non conformes, grille sans mot ;
  - avertissements : grilles en double, proportion inhabituelle de cases définitions ;
  - statistiques : nombre de mots et mots par longueur.
- `GET /api/layouts` : catalogue des layouts valides avec leurs grilles et statistiques.
- Index des candidats par (position, lettre) en ensembles de bits (Phase 3, #20) : remplace le parcours du Trie et le cache par motif du solveur ; mêmes candidats dans le même ordre, donc mêmes grilles pour un même seed, calculées 2 à 6 fois plus vite. Benchmark : 11x6-001 de 11/20 à 20/20 (p50 3,1 s), 6x7-001 p95 0,29 s.
- Redémarrages du solveur (Phase 3, #19) : essais successifs de `300 × luby(i)` appels récursifs dans le budget temps, trajectoires dérivées du seed (même seed ⇒ même grille) ; benchmark `--restart-unit` et nombre d'essais par seed ([mesures](backend/benchmarks/README.md)).
- Pools de mots dans le moteur (Phase 3, #17, [ADR 0007](docs/adr/0007-contrat-de-generation.md)) : mots obligatoires, souhaités (dictionnaire personnel actif) et communs (lexique curé) ; chaque mot placé indique sa provenance (`source`) et la grille renvoie la part de mots de l'auteur (`wish_ratio`).
- Mots obligatoires et souhaités (Phase 3, #18, [ADR 0007](docs/adr/0007-contrat-de-generation.md)) : champs `must_words` et `wish_words` de `POST /api/grids/generate` ; les mots imposés sont placés avant tous les autres, en commençant par le plus contraint, avec retour arrière. Un mot qui n'entre pas dans le layout est refusé **avant toute résolution** (`reason: "must_words"`, problème mot par mot et layouts de repli) ; un mot que la recherche n'a pas su placer donne `reason: "must_words_unplaced"` et la liste des mots restants.
- Éditeur de layouts dans le curateur (Phase 2, #14, onglet « Layouts ») :
  - dessin au toucher ou au clavier (`x`, `-`, flèches, Entrée, Retour arrière) ;
  - remise à blanc de toute la grille, ou de son seul intérieur (première ligne et première colonne conservées) ;
  - vérification en direct par le serveur, cases fautives en rouge, statistiques ;
  - enregistrement dans `backend/layouts/` sous le prochain numéro, sans écrasement ni doublon ;
  - catalogue avec aperçus, copie d'un layout existant, brouillon conservé sur l'appareil ;
  - le curateur démarre sans la base du lexique (éditeur seul).
- Captures d'écran dans le README (#8) : recherche par motif et grille générée, régénérables par `frontend/tests/screenshots.spec.ts` (Playwright utilise le Chrome installé).
- Curateur : bulle « Chercher ce mot » avec les résultats Google (Serper) ou, sans clé, Wikipédia et Wiktionnaire.
- Documentation de relecture :
  - README réécrit ;
  - `docs/ARCHITECTURE.md`, `docs/ENGINE.md`, `docs/LAYOUTS.md`, `docs/LEXICON.md` ;
  - ADR 0001 à 0004 ;
  - PRD mis à jour ;
  - `CONTRIBUTING.md`, `CLAUDE.md`.
- `Makefile` (setup, dev, tests, benchmark).
- Modèles de PR et d'issues GitHub.
- Dependabot.
- CI frontend : ESLint et vérification TypeScript.
- Règles automatiques, filtre positif et révision des décisions ([ADR 0008](docs/adr/0008-regles-automatiques-et-revision.md)) :
  - `python -m tools.lexicon autorules` : aperçu (sans rien écrire), activation et désactivation des règles décrivant les classes de mots jamais gardées au tri — `formes-composees` (119 triées, 119 supprimées), `inconnues-sans-definition` (94,6 % de suppressions) et `flexions-rares-longues` (sur demande) ; activées dans `data/lexicon/auto_rules.json`, jamais écrites dans `decisions.csv`, et toujours battues par une décision « garder » ;
  - `python -m tools.lexicon export --filtre moyen` : ne garde que les mots connus de Lexique, définis pour eux-mêmes ou formés sur un lemme de fréquence zipf ≥ 2 (191 709 mots de 11 lettres ou moins, contre 393 720) ;
  - `python -m tools.lexicon revision` : décisions douteuses (famille jugée à l'opposé, mot courant supprimé, rafale de décisions dans la même seconde) ; confirmer ou corriger écrit un lot marqué `revision`, et le mot ne revient plus ;
  - `stats` compte à part les mots traités par les règles (`handled_by_rules`).
- Curateur : deux nouveaux onglets ([ADR 0008](docs/adr/0008-regles-automatiques-et-revision.md)) :
  - **Familles** (`/familles`) : une carte par lemme (définition, fréquence, toutes ses formes), une décision pour toute la famille (`←` supprimer, `→` garder, `↑` passer, `↓` annuler) ; les formes déjà décidées et les mots très courants ne sont jamais touchés ; une famille doit compter au moins trois formes à trier, et toucher une forme montre sa définition pour la trier seule (les familles qui mélangent deux mots, comme l'adverbe « hier » et le verbe « hier ») ;
  - **Révision** (`/revision`) : les décisions douteuses reproposées une par une, avec les touches du tri (`←` supprimer, `→` garder, `↑` passer, `↓` annuler) ; redonner la même réponse suffit à sortir le mot de la liste ;
  - filtre par suggestion dans **Familles** (probablement rare / à examiner / probablement courant) et tranche « 12 lettres et plus », comme dans « Trier les mots » : les deux files offrent désormais les mêmes tranches, sans quoi des mots n'auraient été visibles nulle part.
  - les mots visés par une règle automatique disparaissent de la file de tri et du reste à trier.

### Modifié
- **Le frontend se construit en site statique** (`pnpm build` → `out/`), prêt pour Cloudflare Pages
  ([ADR 0013](docs/adr/0013-cible-hebergement-production.md)) : pas de serveur Node en production. Les en-têtes de
  sécurité (CSP, HSTS…) sont écrits dans `out/_headers`, depuis la même définition que ceux de `next dev`.
  L'éditeur d'une grille passe de `/grids/12` à **`/grids/edit?id=12`** : un export statique ne génère pas une
  page par grille. `next start` disparaît.
- **Une génération ne recopie plus le lexique** : l'API désigne « tout le lexique jusqu'à N lettres »
  (`WholeLexicon`) au lieu de trier puis répartir 700 000 mots à chaque requête. La préparation passe de
  0,09 à 0,76 s à environ 1 ms. Le CPU moyen d'une génération libre baisse de 30 % (1,78 → 1,25 s), et les
  workers partagent désormais le lexique au lieu d'en porter chacun une copie (4 processus : 2 037 → 782 Mo).
  Les grilles produites sont identiques : le benchmark donne les mêmes trajectoires sur ses 420 générations,
  et 36 grilles du vrai lexique ont été comparées une à une.
- Les index du lexique sont construits **au chargement** au lieu de la première génération de chaque longueur.
- En production, le lexique **n'est plus rechargé à chaud** : il est livré avec l'application, et sous
  gunicorn le rechargement ne profiterait qu'au processus maître.
- La clé d'une définition est désormais la **position** de son emplacement (`1-2-across`) et non le texte
  du mot (`PORTE-1-2-across`) : corriger une lettre renomme le mot, et une clé fondée sur le texte aurait
  laissé la définition orpheline. Migration `0004` : les clés existantes sont réécrites.
- **Plus aucun dictionnaire personnel n'entre de lui-même dans une grille** ([ADR 0011](docs/adr/0011-dictionnaires-choisis.md)) :
  le dictionnaire *actif* y était versé en silence, si bien qu'une grille sur la musique héritait des mots
  de cuisine. Tous se cochent maintenant, l'actif compris — il ne sert plus qu'à la recherche par motif.
- Les garde-fous d'usage cessent de gêner l'auteur : 1 000 grilles conservées par compte au lieu de 200,
  et la génération n'est plus plafonnée à 10 par minute sur la pile de développement. Les valeurs du code
  restent celles de la production, où elles protègent d'un abus ; `MAX_GRIDS_PER_USER` et
  `RATELIMIT_GENERATE` se règlent par variable d'environnement partout ailleurs.
- Rendu des grilles repris pour ressembler à une grille de magazine (#26, #27) : police étroite
  (Archivo Narrow, embarquée), cadre extérieur plus fort que les traits intérieurs, flèches plus fines et
  plus petites. Le rendu connaît trois états — **édition** (lettres, flèches et définitions, cases
  cliquables), **vierge** (celle qu'on imprime) et **solution** (les lettres seules).
- `RATELIMIT_REGISTER` se règle par variable d'environnement **hors production**, où le quota reste celui du code : les parcours end-to-end créent un compte par exécution, et le quota de production les ferait échouer dès le deuxième (#25).
- Supprimer le dictionnaire **actif** n'en laissait aucun d'actif : la recherche et les grilles perdaient les mots personnels alors que le sélecteur en montrait toujours un. Un dictionnaire restant est réactivé aussitôt (#21).
- La recherche par motif passe de `/` à `/search` : `/` accueille désormais la page d'accueil (#22).
- Génération avec mots imposés : quand la requête nomme un **format**, le moteur passe au layout suivant une fois la recherche épuisée sur le courant, au lieu de s'entêter sur un unique tirage au sort. Mesuré (#73) : 6×7 à trois mots imposés de 6/20 à 11/20, et les formats à layout unique ne bougent pas d'une grille. **Sans mot imposé, les 420 trajectoires de la baseline sont identiques.** La vérification préalable porte désormais sur tous les layouts du format : un mot n'est refusé que s'il n'entre dans aucun, au lieu d'être jugé sur le layout tiré ([mesures](backend/benchmarks/README.md)).
- Benchmark : `--by-format` (le moteur choisit son layout, comme l'API) et `--max-layouts N`. Sans eux, un correctif agissant au niveau du format est invisible au harness, qui pilote layout par layout.
- Plafond de candidats du solveur porté de 100 à **300** : mesuré sur les 21 layouts, 420/420 dans les deux cas, mais médiane de 0,91 s à 0,71 s et p95 du 13×18 de 14,57 s à 8,72 s. Gain sec, sans contrepartie.
- Curateur : les mots d'une famille ne sont plus proposés dans « Trier les mots ». Ils s'y triaient en double, et décider une forme d'un côté périmait la carte affichée de l'autre. Les formes en plusieurs mots et les groupes de moins de trois formes y restent : ce sont les seuls endroits où on peut les voir.
- Curateur : les formes d'une famille s'affichent en **nuage de puces** au lieu d'une liste, et le détail d'une forme s'ouvre sous le nuage. Une famille de trente conjugaisons tient à l'écran, boutons de décision compris, sans faire défiler la page.
- Regroupement par famille : toutes les graphies d'un mot sont examinées, plus seulement la première. 774 mots comme `cava` (« ça va »), `aras` (« à ras ») ou `etal` (« et al. ») pouvaient former des familles. La règle de suppression, elle, continue de ne regarder que la graphie affichée : l'élargir viserait « avoir » (« à voir »), « savoir » (« s'avoir ») ou « avec » (« av. è. c. »).
- Anciens documents de cadrage (`READMESDD.md`, `amelioration-generate.md`) archivés dans `docs/archive/`.
- Layouts déplacés de `backend/templates/<L>x<H>/template_01.txt` vers `backend/layouts/<L>x<H>/001.txt` ; le champ `layout` de la grille générée et les clés du benchmark deviennent `6x7-001`. Variable de configuration `TEMPLATES_DIR` renommée `LAYOUTS_DIR`.
- Modèle d'issue « Nouveau layout » : grille au format v1, sans champ source.
- Dépendances Python figées (`backend/requirements.txt`, `tools/curator/requirements.txt`), suivies par Dependabot et auditées par `pip-audit` en CI (#6).
- Lint Python avec ruff (`make lint-backend`, `ruff.toml`, règles tolérantes pour commencer) et couverture des tests en CI : 80 % minimum sur le moteur, 70 % sur les outils (#5).

### Corrigé
- **Documentation qui contredisait le code** : le schéma d'[ARCHITECTURE](docs/ARCHITECTURE.md) montrait
  encore un jeton `Bearer` entre le frontend et l'API, alors que la session voyage en cookies depuis
  l'[ADR 0015](docs/adr/0015-session-en-cookies.md) ; ARCHITECTURE et le README du frontend donnaient
  `http://localhost:5001` comme repli de `getApiBaseUrl()`, qui renvoie une chaîne vide (même origine, que
  `next dev` relaie vers l'API) ; [SECURITY](docs/SECURITY.md) disait CORS « sans credentials ». Enfin, le
  commentaire d'`AUTO_MIGRATE` (`backend/app.py`) prévoyait encore des migrations jouées au déploiement,
  écartées par la [roadmap](docs/ROADMAP.md) (Phase 6). Aucun changement de comportement.
- **CI** : pnpm figé sur 12.5.1. La CI prenait « la dernière 12 », et pnpm 12.6.0 (sorti le 23/09/2026)
  laissait `pnpm dev`, lancé par Playwright, bloqué sans fin : les parcours end-to-end tournaient jusqu'à
  la limite de six heures. Le job a désormais une durée maximale de 20 minutes.
- **Mentions légales et confidentialité** (#78) : elles décrivaient un produit qui n'existe pas (cookies,
  collecte d'adresse IP et de navigateur, transferts à des tiers). Elles disent désormais ce qui est vrai, ce
  qui changera à la mise en ligne, et créditent le DELA, Lexique et la police des grilles.
- Les migrations jouées au démarrage éteignaient tous les loggers déjà créés (`fileConfig` d'Alembic) :
  sous gunicorn, plus aucun journal d'accès ni de démarrage des workers.
- Les définitions et les notes en cours de frappe étaient écrasées par le rechargement que provoque
  chaque lettre posée : elles ne sont plus relues qu'à l'ouverture de la grille. Elles s'enregistrent
  aussi en quittant le champ, sans attendre la pause de 600 ms.
- Conserver une grille répondait **500** dès que la migration des définitions était passée mais que
  l'API tournait encore sur le code d'avant : la colonne était `NOT NULL` sans valeur par défaut côté
  base, si bien que l'ancien code ne pouvait plus insérer une ligne. La base porte désormais le défaut
  (`'{}'`), et l'[ADR 0010](docs/adr/0010-migrations-de-schema.md) en fait une règle : une migration doit
  laisser écrire le code d'avant.
- Curateur : « Aucun mot à trier dans cette famille » bloquait l'écran jusqu'au rechargement de la page. Une famille déjà triée ailleurs n'est plus une erreur — la carte affichée était simplement périmée : le curateur passe à la suivante en le disant. Un mot inconnu du lexique reste refusé.
- Les mots très courants (bande `keep`, zipf ≥ 3,5) sont désormais hors d'atteinte des règles automatiques. `aujourd'hui`, `quelqu'un`, `parce que`, `d'abord` et `à tâtons` étaient visés par `formes-composees` et auraient quitté le lexique.
- L'export automatique du curateur ignorait les règles automatiques : les mots retirés de la file de tri restaient dans le lexique chargé par l'API, donc invisibles à l'auteur mais toujours placés dans les grilles. L'export applique désormais les mêmes règles que le tri, et `CURATOR_EXPORT_FILTER` permet d'y ajouter le filtre positif.
- Le forward checking refusait tout placement laissant un emplacement croisé avec moins de **3** candidats. En fin de grande grille, presque tous les emplacements restants sont dans ce cas : la recherche atteignait 62 mots sur 64, se voyait interdire la clôture, et chaque redémarrage jetait ces 62 placements corrects pour repartir de zéro. Le seuil passe à **2**, le minimum autorisé par l'invariant du solveur : les **21 layouts du catalogue réussissent 20/20** (contre 411/420), sans aucun layout dégradé, et les temps baissent partout — le 13×18 de 81 mots passe de 12,7 s à 2,0 s de médiane, les petits formats de 0,167 s à 0,127 s (#61).
- Les mots des dictionnaires personnels n'étaient **jamais placés** : l'index des candidats ne contenait que les mots du lexique, et les mots personnels transmis au générateur étaient silencieusement ignorés, à l'indexation comme aux croisements. Ils forment désormais le pool « souhaité » : ajoutés à l'index de leur longueur, essayés avant le lexique commun et acceptés comme mots croisés (#17).
- Le solveur exigeait qu'un mot perpendiculaire **en cours d'écriture** existe déjà au dictionnaire : deux rangées voisines traversant un emplacement de 5 cases y laissent « AB », que le solveur refusait faute d'être un mot. Sur les grilles de plus d'une trentaine de mots, il rejetait ainsi des placements valides en continu et n'aboutissait jamais. Seuls les mots **terminés** sont désormais vérifiés (#57). Les **16 layouts du catalogue réussissent maintenant 20/20**, du 6×7 (0,05 s) au 13×16 de 61 mots (1,9 s) ; les formats de plus de 30 mots n'aboutissaient jamais auparavant.

### Sécurité
- **CSP stricte sur le site statique** (#99) : chaque page n'exécute plus que ses propres scripts inline,
  autorisés par leur empreinte `sha256` dans une CSP posée en `<meta>` au build (`scripts/write-headers.mjs`).
  Un script injecté par une faille XSS ne s'exécute plus. `'unsafe-inline'` ne subsiste que pour `next dev`
  et pour les styles. Vérifié dans un navigateur sur les 13 pages et la 404 (`tests/csp.spec.ts`).
- **Audit ASVS** ([docs/AUDIT-SECURITE.md](docs/AUDIT-SECURITE.md)) : revue du code et essais sur l'image en
  configuration de production (jetons forgés, CSRF, contournement du rate limiting, méthodes, corps). Deux
  défauts corrigés : un mot de passe de plus de **72 octets** (100 caractères, ou 64 lettres accentuées)
  provoquait une **erreur 500** à l'inscription, bcrypt 5 refusant ce qu'il tronquait autrefois ; et des
  **clés secrètes courtes** étaient acceptées en production. Elles doivent maintenant faire 32 octets au moins,
  et être distinctes.
- **La session passe en cookies `httpOnly`** ([ADR 0015](docs/adr/0015-session-en-cookies.md), #28, remplace
  l'ADR 0003) : les jetons ne sont plus dans le `localStorage`, donc plus à portée d'une faille XSS, et
  l'API ne les met plus jamais dans ses réponses. Protection CSRF par double soumission (`X-CSRF-TOKEN`).
  La déconnexion **révoque** les jetons (`POST /api/auth/logout`, table `revoked_token`), et un changement de
  mot de passe ferme toutes les sessions ouvertes (migration `0006`). En développement, `next dev` relaie
  `/api` vers l'API : même origine, et `make preview-remote` n'ouvre plus qu'un tunnel. Il faut se
  reconnecter une fois.
- Supprimer son compte demande désormais le **mot de passe** (`DELETE /api/users/me`, 403 s'il est faux,
  même limite de débit que la connexion) : le jeton vit dans le navigateur, et volé, il suffisait à tout effacer.
- Plus de repli vers l'ancienne API Render : sans `NEXT_PUBLIC_API_BASE_URL`, un build de production visait
  `motsfleches-terminator-backend.onrender.com`, autorisé aussi par la CSP. Le service est supprimé, et son
  sous-domaine peut être réservé par n'importe qui, qui recevrait alors e-mails et mots de passe. Le build de
  production **échoue** désormais sans adresse d'API ; Render et Vercel sont retirés du code et de la
  documentation, ainsi que les images de démarrage de Next.js inutilisées.
- Rate limiting derrière Cloudflare Tunnel : toutes les requêtes arrivent de cloudflared, et le limiteur
  aurait bloqué tous les visiteurs ensemble. L'adresse vient désormais de `CF-Connecting-IP`, lue seulement
  si `CLIENT_IP_HEADER` le demande : sans tunnel, un client pourrait l'inventer pour échapper aux limites.
- Frontend : versions corrigées de postcss, nanoid et sharp imposées par des overrides pnpm (9 vulnérabilités transitives de next 15.5.25, #7).

## [0.1.0] — 2026-09-14

Première version stabilisée (Phase 0a et 0b de la [roadmap](docs/ROADMAP.md)).

### Ajouté
- Roadmap du projet (`docs/ROADMAP.md`).
- `GET /api/grids/formats` ; le frontend ne propose que les formats disposant d'un layout.
- Budget temps du solveur : erreurs `422` explicites (`timeout`, `no_solution`).
- Benchmark reproductible du générateur et baseline (`backend/benchmarks/`).
- Tests : moteur, endpoints de grille, configuration, validation, autorisation, sécurité (123 tests).
- Validation de toutes les entrées de l'API (pydantic), messages d'erreur en français.
- Rate limiting (connexion, inscription, refresh, recherche, génération).
- Plafonds de taille : corps de requête, nombre de dictionnaires et de mots.
- Endpoint `POST /api/auth/refresh` et renouvellement automatique de session côté frontend.
- En-têtes de sécurité (API et frontend), CORS strict.
- `docs/SECURITY.md`.
- `.env.example` ; identifiants docker compose sortis du code.

### Corrigé
- La génération de grille plantait à chaque appel (Trie pré-construit non transmis).
- La génération échouait presque toujours : les mots étaient tirés d'un échantillon de 30 000 mots (~4 % du dictionnaire).
- Un même seed ne donnait pas la même grille (état aléatoire global partagé).
- Les messages d'erreur de l'API n'étaient jamais affichés dans l'interface.
- La suppression de compte laissait les mots personnels en base.
- La connexion d'un ancien compte anonymisé provoquait une erreur 500.
- Le secret JWT était lu depuis la mauvaise variable d'environnement.

### Sécurité
- Next.js 15.5.4 → 15.5.25 (advisories critiques d'exécution de code à distance).
- Débogueur Werkzeug activé uniquement avec `FLASK_DEBUG=1`.
- Refus de démarrer en production avec des secrets par défaut, sans base de données ou avec CORS `*`.
- Jokers SQL échappés dans la recherche de mots personnels.

[Non publié]: https://github.com/maximefd/terminator-app/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/maximefd/terminator-app/releases/tag/v0.1.0
