# Roadmap Migration : Moteur Solver vers Blazor WASM #

## Phase 0 : Préparation et Architecture ##

[ ] Stratégie Git : Créer un nouveau dossier solver-client/ à la racine pour le projet Blazor WASM.

[ ] Initialiser le projet : - [ ] Créer un projet Blazor WebAssembly Standalone (ex: Terminator.Solver.Wasm).

[ ] Créer un projet xUnit pour les tests unitaires (ex: Terminator.Solver.Tests).

[ ] Créer un projet Console App pour le pré-processeur (ex: Terminator.Dictionary.Processor).

[ ] Définir les Interfaces (IoC/DI) : Définir les interfaces C# pour l'injection de dépendances :

[ ] IWordRepository (gère le dictionnaire)

[ ] IGridSlots (trouve et choisit les slots)

[ ] IGridSolver (orchestre le backtracking)

[ ] ISearchService (expose la recherche par motif à l'UI)

## Phase 1 : Backend API - Route Candidates

[ ] Modifier [trie_engine.py](cci:7://file:///Users/maxfd/Desktop/terminator-app/backend/Users/maxfd/Desktop/terminator-app/backend/trie_engine.py:0:0-0:0) :
    [ ] Ajouter méthode [get_words_by_length(length)](cci:1://file:///Users/maxfd/Desktop/terminator-app/backend/engine/word_repository.py:8:4-10:57)
    [ ] Tester avec [dela_trie.get_words_by_length(6)](cci:1://file:///Users/maxfd/Desktop/terminator-app/backend/engine/word_repository.py:8:4-10:57) → doit renvoyer ~50k mots

[ ] Créer route `/api/dictionaries/candidates` dans [routes.py](cci:7://file:///Users/maxfd/Desktop/terminator-app/backend/routes.py:0:0-0:0)
    [ ] Accepte POST avec `{ lengths: [3,4,5,6,7], use_global: true }`
    [ ] Filtre DELA par longueurs
    [ ] Fusionne avec dictionnaire personnel actif
    [ ] Retourne JSON `{ words: [...], count: X }`

[ ] Tester la route :
    [ ] Avec Postman/curl pour grille 11x6 → doit renvoyer ~6000 mots en <100ms
    [ ] Vérifier la taille de la réponse → doit être <300 KB

## Phase 2 : Blazor Services Simplifiés

[ ] Créer `IWordApiService` + `WordApiService`
    [ ] Méthode `GetCandidatesAsync(int[] lengths)`
    [ ] Gérer JWT optionnel pour dictionnaires perso
    
[ ] Créer [WordRepository](cci:2://file:///Users/maxfd/Desktop/terminator-app/backend/engine/word_repository.py:2:0-30:94) (VERSION SIMPLE)
    [ ] `Dictionary<int, HashSet<string>>` au lieu de Trie
    [ ] `LoadWords(List<string> words)`
    [ ] `GetCandidates(string pattern)` avec Regex
    [ ] `IsWordValid(string word)`

[ ] Créer `GridSolverService`
    [ ] Injecte `IWordApiService`
    [ ] Méthode `async Task<GridData> GenerateAsync(int width, int height, int? seed)`
    [ ] 1. Calcule les longueurs nécessaires (min=3, max=max(width, height))
    [ ] 2. Appelle `_wordApi.GetCandidatesAsync(lengths)`
    [ ] 3. Charge les mots dans [WordRepository](cci:2://file:///Users/maxfd/Desktop/terminator-app/backend/engine/word_repository.py:2:0-30:94)
    [ ] 4. Lance `GridSolver.Solve()`
    
### Phase 2.5 : Infrastructure de Debugging
[ ] Créer un LogService injectable qui :
    [ ] En mode DEBUG : console.log() via JSInterop
    [ ] En mode RELEASE : désactivé
[ ] Ajouter un panneau debug dans l'UI Blazor :
    [ ] Affichage en temps réel des métriques (recursive_calls, backtracks)
    [ ] Bouton "Pause" pour stopper la génération
    [ ] Bouton "Export Logs" pour télécharger les logs détaillés

## Phase 3 : Validation et Tests Unitaires ##

[ ] Traduire test_harness.py :

[ ] Recréer un test xUnit qui injecte les services.

[ ] Charger le dictionary.bin (en utilisant HttpClient ou en l'important comme ressource).

[ ] Lancer le GridSolver.cs avec des seeds fixes (ex: 11x6).

[ ] Valider la performance : Vérifier que les grilles se génèrent et mesurer le temps (doit être < 1s).

[ ] Créer un script de comparaison Python ↔ C# :
    [ ] Exécuter le solver Python avec 50 seeds fixes
    [ ] Exporter les grilles résultantes en JSON
    [ ] Exécuter le solver C# avec les mêmes seeds
    [ ] Comparer les grilles caractère par caractère
    [ ] Valider que les métriques (backtracks, recursive_calls) sont similaires

## Phase 3.5 : Profiling Performance (Optimisation 4) ##

[ ] Créer un projet BenchmarkDotNet pour le GridSolver.cs.

[ ] Profiler les hotspots : Lancer les benchmarks et identifier les allocations mémoire (ex: création de string pour les patterns, LINQ).

[ ] Optimiser C# : Remplacer les string par des Span<char> ou char[] dans les boucles internes (ex: GetSlotPattern).

[ ] Mesurer l'empreinte mémoire totale du CompactDictionary en RAM
[ ] Tester avec plusieurs générations successives (détecter les memory leaks)
[ ] Vérifier que le GC de .NET libère bien les GridStateSnapshot après backtrack

## Phase 3.6 : Ajustement des Objectifs de Performance
[ ] Comparer les benchmarks C# vs Python
[ ] Ajuster les objectifs si nécessaire
[ ] Documenter les différences observées

## Phase 4 : Intégration de l'UI "Générateur de Grille" ##

[ ] Créer le composant UI : Faire une page Blazor (GridGenerator.razor) qui contient le bouton "Générer".

[ ] Gérer le "clic" (Non-bloquant) :

[ ] Créer une variable bool isGenerating.

[ ] Dans @onclick, appeler une fonction async Task GenerateGrid().

[ ] Dans cette fonction :

isGenerating = true;
await Task.Yield(); // Permet à l'UI de se rafraîchir

// L'ÉTAPE LA PLUS IMPORTANTE : Lancer le calcul sur un autre thread
// À la place de Task.Run, utiliser Task.Yield pour libérer l'UI
isGenerating = true;
StateHasChanged(); // Force le re-render avec le spinner
await Task.Yield(); // Libère le thread UI

GridData grid = solver.Solve(seed); // Exécute de façon synchrone mais l'UI a eu le temps de se mettre à jour

isGenerating = false;
StateHasChanged();

[ ] Afficher le spinner : Dans le HTML Blazor, afficher un spinner : @if (isGenerating) { <Spinner /> }.

[ ] Afficher la grille : Créer un composant GridDisplay.razor qui prend GridData en paramètre (similaire à grid-display.tsx).

[ ] Implémenter une version async du solver avec yield périodique :
    [ ] Ajouter un compteur dans _solve_recursive
    [ ] Tous les 100 appels récursifs, appeler await Task.Yield()
    [ ] Permet de garder l'UI responsive pendant les générations longues

## Phase 4.5 : Feature Flag et Transition
[ ] Implémenter le feature flag USE_BLAZOR_SOLVER
[ ] Tester en A/B testing avec 10% des utilisateurs
[ ] Monitorer les erreurs et feedbacks

## Phase 5 : Intégration de l'UI "Recherche par Motifs" ##

[ ] Créer le composant UI :

[ ] Faire une page/composant Blazor (Search.razor).

[ ] Ajouter un champ de texte : <input @bind="searchTerm" @bind:event="oninput" />.

[ ] Gérer la saisie (Instantané) :

[ ] Injecter le ISearchService.

[ ] Appeler le service à chaque modification de searchTerm.

[ ] (Optimisation V2) : Ajouter un "debounce" de 150-250ms si la recherche s'avère trop lourde à chaque frappe.

[ ] Afficher les résultats : Lister les mots trouvés (List<string> searchResults).