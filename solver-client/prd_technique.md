# PRD Technique — Migration du Moteur de Génération vers Blazor WebAssembly

## 1. Contexte

L’application actuelle génère des grilles de mots croisés/fléchés via un solveur écrit en Python (Flask côté backend). Elle permet aussi la recherche par motifs (?A?A??) via une route API dédiée (/api/search).

Le solveur et la recherche reposent sur :

- Un Trie lexical basé sur le dictionnaire DELA
- Un système de backtracking avec heuristique MRV
- Une API REST consommée par un frontend Next.js / React 19

Problème actuel : Toute la logique métier (génération et recherche) tourne backend-side, ce qui impose :

- Charge serveur élevée (génération de grilles ET requêtes de recherche)
- Latence réseau sur la recherche par motif (l'utilisateur attend en tapant)
- Temps de génération dépendant de la charge serveur
- Débogage plus difficile


**Problème actuel** :  
Le solveur Python tourne uniquement **backend-side**, ce qui impose :

- Charge serveur élevée si plusieurs utilisateurs génèrent des grilles
- Besoin de scaling horizontal complexe
- Temps de génération dépend de la charge serveur
- Débogage plus difficile (le solveur n’est pas observable côté client)

## 2. Objectif de cette Migration

🎯 **Exécuter le solveur de génération et les fonctions de recherche par motif directement dans le navigateur, en utilisant Blazor WebAssembly (C# / .NET).**

### Avantages

| Aspect | Python Backend | Blazor WASM |
|---|---|---|
| Charge CPU | Centralisée → coûteuse | Distribuée → chaque client calcule |
| Latence solveur | Dépend du réseau | 0 ms (local) |
| Latence recherche | Dépend du réseau | 0 ms (local) |
| Scalabilité | Serveurs nécessaires | Illimitée (client-side) |
| Coût hébergement | Moyen → élevé | Très faible |
| UX | Attente possible | Instantanée / interactive |

---

## 3. Architecture Cible (REVUE - Approche Hybride)

### 🎯 Décision Architecturale Clé

**Problème identifié** : Le dictionnaire DELA fait 55.4 MB (900k mots).
- Temps de chargement initial inacceptable (7-10s)
- Empreinte mémoire WASM trop élevée (100-150 MB)

**Solution** : Architecture hybride optimisée

### 3.1 Séparation des Responsabilités

| Fonctionnalité | Localisation | Justification |
|---|---|---|
| **Recherche par motif** | 🔵 Backend Python | Dictionary trop lourd, Trie déjà optimisé, cache HTTP |
| **Génération de grille** | 🟢 Blazor WASM | Scalabilité client-side, calcul distribué |
| **Auth & Dictionnaires perso** | 🔵 Backend Python | Nécessite DB, sécurité |

### 3.2 Flux de Génération Optimisé

```
User clique "Générer" (11x6)
  ↓
Blazor → GET /api/dictionaries/candidates?lengths=3,4,5,6,7,8,9,10,11&seed=123
  ↓
Backend Python :
  - Filtre le Trie DELA par longueurs demandées
  - Fusionne avec dictionnaire personnel actif
  - Renvoie ~5000-8000 mots pertinents (~250 KB JSON)
  ↓
Blazor WASM :
  - Charge ces mots en mémoire
  - Lance GridSolver.Solve() localement
  - Affiche la grille générée
```

### 3.3 Impact sur l'API Backend (Python/Flask)

**Routes à CONSERVER** :
- ✅ `/api/auth/*` : Authentification JWT
- ✅ `/api/dictionaries/*` : Gestion dictionnaires perso
- ✅ `/api/search` : Recherche par motif (garde le Trie Python)
- ✅ **NOUVEAU** : `/api/dictionaries/candidates` : Fournit les mots filtrés

**Routes à DÉPRÉCIER** :
- ❌ `/api/grids/generate` : Remplacé par génération client-side

### 3.4 Architecture Frontend

```
Site Principal (WordPress/Next.js)
  └─ www.terminator.com
     ├─ SEO, marketing, blog
     └─ Lien vers → app.terminator.com

Application Blazor WASM (Standalone SPA)
  └─ app.terminator.com
     ├─ GridGenerator.razor (page principale)
     ├─ Search.razor (recherche par motif)
     └─ MyDictionaries.razor (gestion dictionnaires perso)
```

**Communication** :
- JWT passé via localStorage (partagé entre sous-domaines avec CORS)
- API calls vers `api.terminator.com` (backend Python)

### 3.5 Modules C# (Blazor WASM)

| Module | Rôle |
|---|---|
| `CompactDictionary` | Stockage précompilé du Trie + groupes de longueurs |
| `Trie` | Recherche par motif (pattern matching) |
| `WordRepository` | Renvoie les candidats pour un slot |
| `GridSlots` | Détection + MRV (choix du prochain slot) |
| `GridSolver` | Backtracking + validation croisée |
| `GridStateSnapshot` | Snapshot compact pour revert rapide |
| `SearchService` | Service C# simple qui expose le Trie.SearchPattern() à l'UI Blazor |

---

## 4. Pipeline de Données (SIMPLIFIÉ)

**Changement stratégique** : Pas de dictionary.bin côté client.

### 4.1 Backend Python (Inchangé)
- Garde le Trie DELA en mémoire (comme actuellement)
- Nouvelle route `/api/dictionaries/candidates` :
  ```python
  @main_bp.route('/dictionaries/candidates', methods=['POST'])
  @jwt_required(optional=True)
  def get_candidates_for_grid():
      data = request.json
      lengths = data.get('lengths', [])  # Ex: [3,4,5,6,7,8,9,10,11]
      use_global = data.get('use_global', True)
      
      candidates = []
      if use_global:
          for length in lengths:
              candidates.extend(dela_trie.get_words_by_length(length))
      
      # Ajouter mots perso de l'utilisateur
      if user and user.active_dictionary:
          candidates.extend([w.mot for w in user.active_dictionary.words if len(w.mot) in lengths])
      
      return jsonify({"words": list(set(candidates))}), 200
  ```

### 4.2 Blazor WASM
- **Pas de Trie client-side**
- Reçoit uniquement les mots nécessaires via API
- Construit un simple `HashSet<string>` ou `Dictionary<int, List<string>>` en mémoire

---

## 5. Backtracking — Règles Fonctionnelles à Respecter

| Règle | Description |
|---|---|
| MRV | Toujours choisir le slot avec le moins de candidats restants |
| Vérification locale | Chaque placement doit valider les intersections immédiatement |
| Snapshot | Le revert doit être **constant time** (GridStateSnapshot) |
| Limitation | `MAX_CANDIDATES_PER_SLOT = 50` (configurable) |
| NoGoods (optionnel V2) | Mémoriser les combinaisons invalides pour éviter les cycles |

---

## 6. Performance Attendues

| Test | Objectif |
|---|---|
| Génération grille 11x6 | < 200ms dans Chrome moderne |
| Génération grille 15x15 | < 3s |
| Chargement du Trie | < 100ms |
| Recherche par motif (?A?A??)	| < 10ms (après chargement) |

Profiling via **BenchmarkDotNet** obligatoire avant UI finale.

## 6.5 Chargement Initial
| Étape | Temps cible |
|---|---|
| Téléchargement dictionary.bin (avec gzip) | < 2s |
| Désérialisation en mémoire | < 500ms |
| Premier rendu UI | < 500ms après désérialisation |

---

## 7. Risques & Solutions

| Risque | Impact | Mitigation |
|---|---|---|
| Implémentation Trie incorrecte | Pas de candidats → solveur bloque | Tests unitaires + seeds fixes |
| Sérialisation binaire incompatible | Impossible de charger dans Blazor | Utiliser MessagePack ou BinaryWriter structuré |
| Copies de grille coûteuses | Solveur lent | `GridStateSnapshot` + `Span<char>` |
| Débogage difficile | Dev lente | Log sélectif + mode debug dans UI Blazor |
| Recherche UI lente | L'input de recherche "lag" | Éviter les appels Trie à chaque frappe (debounce)   

---

## 8. Critères de Validation de la Migration

✅ Grilles générées en Blazor identiques à celles du solveur Python   
✅ Performances respectées  
✅ Le solveur tourne entièrement **sans backend**  
✅ Next.js peut l'intégrer proprement sur une page dédiée `/grid`
✅ La recherche par motif est instantanée (client-side) et renvoie les mêmes résultats que l'API Python. 
✅ Les routes API /api/generate et /api/search sont supprimées.

---

## 9. Roadmap de Développement (Référence à la TODO)

Voir fichier : `solver-client/TODO.md`

