# 🧩 Product Requirements Document (PRD)

## 1. 🎯 Objectif global et proposition de valeur

### Problème à résoudre
Les créateurs de mots croisés et fléchés perdent un temps précieux à chercher manuellement des mots rares qui s’adaptent à des motifs complexes (ex : avec accents ou tirets) ou sont contraints à des dictionnaires statiques et désuets.

### Proposition de valeur unique
Fournir le **moteur de recherche et de génération de grilles le plus rapide du marché francophone**, combinant :
- un **Trie lexical optimisé (<200 ms)** pour la recherche par masque,
- la **gestion de dictionnaires personnels et communs**,
- une **heuristique de génération MRV (Minimum Remaining Values)** pour des grilles denses et valides.

L’objectif final est de permettre aux utilisateurs d’utiliser simultanément les dictionnaires commun (DELA) et personnels pour générer des grilles de haute qualité et densité.

---

## 2. 👥 Public cible et critères de succès

### A. Public cible

| Type d’utilisateur | Objectif principal | Accès |
|--------------------|--------------------|--------|
| **Invité** | Découvrir l'outil et tester la recherche par motif. | Lecture seule sur le dictionnaire commun. |
| **Utilisateur enregistré** | Créer et gérer ses propres dictionnaires (multiples), et utiliser les fonctionnalités avancées de génération de grilles. | Lecture/écriture sur dictionnaires personnels. |
| **Auteur/Éditeur (Premium – V2)** | Générer des grilles professionnelles, denses et esthétiques, avec un gain de temps significatif. | Accès complet (fonctions premium à venir). |

---

### B. Critères de succès (KPIs V1)

| Exigence | Métrique | Statut |
|-----------|-----------|--------|
| **Performance recherche** | Temps de réponse API `/search` < **200 ms (P95)** | ✅ Critique |
| **Performance génération** | Temps de génération < **5 s** pour une grille 15×15 standard | ✅ Critique |
| **Adoption utilisateur** | X utilisateurs enregistrés après 3 mois de lancement | 📈 À définir |
| **Qualité technique** | Couverture de tests unitaires/intégration ≥ **70 %** sur les modules Trie et Algorithme | ✅ Critique |

---

## 3. 🧠 Fonctionnalités et scénarios d’usage (V1)

### 3.1. Authentification & Comptes (EPIC C)
- Inscription / Connexion / Déconnexion.
- Session persistante via cookie sécurisé (JWT prévu pour la V2).

---

### 3.2. Dictionnaires & Recherche (EPIC A)

| Fonctionnalité | Spécification / Amélioration | État |
|----------------|-------------------------------|------|
| **Dictionnaire commun (`global_words`)** | Lecture seule. Indexé pour la recherche rapide (DELA). | ✅ OK |
| **Dictionnaires personnels (`user_words`)** | L’utilisateur peut créer/gérer plusieurs dictionnaires personnels. | 🧩 À faire (EPIC A4) |
| **Recherche par motif** | Recherche multi-critères : par motif (`P??LE`), par longueur, par lettres incluses/exclues, gestion des accents et espaces. | 🧩 À faire (EPIC A1) |
| **Fusion des résultats** | `search_scope = "global" ∪ "user"` : résultats fusionnés et triés par priorité utilisateur. | 🔄 En conception |

---

### 3.3. Génération de grilles (EPIC B)

| Fonctionnalité | Spécification / Amélioration | État |
|----------------|-------------------------------|------|
| **Algorithme MRV** | Heuristique MRV (Minimum Remaining Values) pour la sélection dynamique des slots. | ✅ Intégré |
| **Contrôle performance** | Limite de candidats (Top N) lors du backtracking (ex. max 100 tentatives/slot). | 🧩 À faire (EPIC A2) |
| **Contraintes pro** | Application du motif de damier sur la bordure (`x=0`, `y=0`). Validation croisée de tous les mots formés. | ✅ OK |
| **Visualisation** | Composant Front-End (`GridDisplay`) pour afficher la grille (cases, lettres, croisements). | 🧩 À faire (EPIC B3) |

---

## 4. ⚙️ Architecture technique & exploitation

### 4.1. Schéma d’architecture

| Composant | Technologie | Rôle |
|------------|-------------|------|
| **Frontend** | Next.js (App Router), React Query, Tailwind CSS / shadcn-ui | Interface utilisateur, SSR/SEO, affichage de grilles. |
| **API** | Flask (Python) | Service REST principal (auth, recherche, génération). |
| **Base de données** | PostgreSQL + SQLAlchemy | Utilisateurs, dictionnaires personnels, métadonnées de grilles. |
| **Moteur lexical** | DictionnaireTrie (Python) | Recherche ultra-rapide par masque et préfixe sur dictionnaire DELA. |

#### 🔍 Notes sur la base de données
- En **développement local** : SQLite (léger, sans serveur).  
- En **production** : PostgreSQL (multi-utilisateur, transactions concurrentes, support JSONB pour les métadonnées lexicales).  
- Le **dictionnaire global** (lecture seule) est commun à tous.  
- Les **dictionnaires personnels** (`user_words`) sont isolés par utilisateur pour préserver confidentialité et performance.

---

### 4.2. Qualité et stabilité (EPIC D & E)

| Exigence | Mesure | Statut |
|-----------|--------|--------|
| **Stabilité dev** | Démarrage Docker fiable (résolution du “Connection refused” entre API et DB). | 🧩 À faire |
| **Débogage** | Logging structuré (module `logging` déjà intégré). | ✅ OK |
| **CI/CD** | Pipeline complète (Lint, Tests, Build, Deploy) via GitHub Actions vers Vercel/Render. | 🧩 À faire (EPIC D5) |
| **Conformité** | Implémentation des pages RGPD (cookies, privacy). | 🧩 À faire (EPIC E5) |

---

## 5. 🗺️ Roadmap produit

| Version | Objectif principal | Contenu clé |
|----------|--------------------|--------------|
| **V1** | Base stable & performante | Auth, recherche, dictionnaire commun/perso, MRV stable |
| **V1.5** | Passage SQLite → PostgreSQL | Optimisation multi-utilisateur, indexations lexicales |
| **V2** | Expansion produit | Comptes premium, stockage cloud, statistiques lexicales, collab |
| **V3** | Éditeur complet de grilles | Interface web de création, export PDF/PNG, auto-vérification |

---

### 📚 Annexes techniques
- **Langage principal** : Python 3.11
- **Normes de code** : PEP8 + Flake8
- **Documentation** : Docstrings + MkDocs (V2)
- **Tests** : pytest + coverage
- **Performance cible** : `<200 ms` pour la recherche et `<5 s` pour la génération standard

---

### 💬 Auteur
Document rédigé et maintenu par **[ton nom ou pseudo]**  
Rôle : *Product Owner & Dev Lead du projet de moteur lexical et de génération de grilles*

Dernière mise à jour : **octobre 2025**
