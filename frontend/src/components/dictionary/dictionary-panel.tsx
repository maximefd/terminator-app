// DANS src/components/dictionary/dictionary-panel.tsx
"use client";

// Importez useAuth si ce composant est utilisé dans le Header ou Dashboard,
// mais les données d'authentification sont désormais mieux gérées via les credentials
// et la gestion des erreurs (401) dans le fetcher.
// Pour rester simple, nous retirons useAuth pour le moment si le hook n'est pas utilisé directement ici.
// Si useAuth est toujours nécessaire (p. ex. pour l'UI), il faut le réintégrer.
// Pour l'instant, on se concentre sur la migration du fetching.

import { useQuery } from "@tanstack/react-query";
import { getApiBaseUrl } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
// NOTE : Vous n'avez plus besoin de useState et useEffect de React

// --- TYPES (inchangés) ---
type Dictionary = {
  id: number;
  name: string;
  is_active: boolean;
};

type Word = {
  id: number;
  mot: string;
  definition: string | null;
};
// --- FIN TYPES ---


// --- FONCTIONS DE FETCH (isolées et réutilisables) ---

const fetchDictionaries = async (): Promise<Dictionary[]> => {
  const response = await fetch(`${getApiBaseUrl()}/api/dictionaries`, { 
    credentials: "include" 
  });
  
  if (response.status === 401) {
    // Gérer spécifiquement la non-authentification ici si nécessaire,
    // mais le useQuery gère l'objet Error en cas de !response.ok
    throw new Error("Authentification requise pour charger les dictionnaires.");
  }
  if (!response.ok) {
    throw new Error("Erreur réseau: Impossible de charger les dictionnaires.");
  }
  return response.json();
};

const fetchWords = async (dictionaryId: number): Promise<Word[]> => {
  const response = await fetch(`${getApiBaseUrl()}/api/dictionaries/${dictionaryId}/words`, { 
    credentials: "include" 
  });
  
  if (!response.ok) {
    throw new Error(`Erreur réseau: Impossible de charger les mots du dictionnaire ${dictionaryId}.`);
  }
  return response.json();
};

// --- COMPOSANT PRINCIPAL ---

export function DictionaryPanel() {
  // 1. Hook pour les dictionnaires
  const { 
    data: dictionaries, 
    error: dictError, 
    isLoading: isDictLoading 
  } = useQuery<Dictionary[], Error>({
    queryKey: ['dictionaries'],
    queryFn: fetchDictionaries,
    // Note: Ajouter 'enabled: isAuthenticated' si vous utilisez useAuth
  });

  // Détermination du dictionnaire actif ou du premier
  const activeDictionary = dictionaries?.find(d => d.is_active) || dictionaries?.[0];

  // 2. Hook pour les mots (dépend de activeDictionary)
  const { 
    data: words,
    error: wordsError,
    isLoading: isWordsLoading
  } = useQuery<Word[], Error>({
    queryKey: ['words', activeDictionary?.id],
    // Assurez-vous que activeDictionary.id existe avant d'appeler fetchWords
    queryFn: () => fetchWords(activeDictionary!.id),
    // La requête est activée UNIQUEMENT si activeDictionary a été trouvé
    enabled: !!activeDictionary,
  });

  // --- RENDU CONDITIONNEL (Basé sur useQuery) ---

  // Affichage du chargement principal
  if (isDictLoading) {
    return <div className="p-4">Chargement des dictionnaires...</div>;
  }
  
  // Affichage des erreurs (dictionnaires ou mots)
  const currentError = dictError || wordsError;
  if (currentError) {
    return (
      <aside className="w-full max-w-sm rounded-lg border bg-destructive/10 p-4 text-destructive">
        <h2 className="text-lg font-semibold">Erreur</h2>
        <p className="text-sm">{currentError.message}</p>
      </aside>
    );
  }

  // Si on a les dictionnaires mais pas encore les mots (chargement secondaire)
  if (isWordsLoading && activeDictionary) {
     return <div className="p-4">Chargement des mots de {activeDictionary.name}...</div>;
  }
  
  // --- RENDU FINAL ---
  return (
    <aside className="w-full max-w-sm rounded-lg border bg-card p-4">
      <h2 className="text-lg font-semibold">Mes Dictionnaires</h2>
      <p className="text-sm text-muted-foreground mt-2">
        Actif : <strong>{activeDictionary?.name || "Aucun"}</strong>
      </p>

      <div className="mt-4">
        <h3 className="font-semibold">Mots</h3>
        <ScrollArea className="h-72 rounded-md border mt-2">
          <div className="p-4">
            {words && words.length > 0 ? (
              words.map((word) => (
                <div key={word.id} className="text-sm font-mono mb-2">
                  {word.mot}
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground italic">Aucun mot.</p>
            )}
          </div>
        </ScrollArea>
      </div>
    </aside>
  );
}

// NOTE: Si vous réintégrez useAuth pour la condition d'affichage, n'oubliez pas
// d'ajouter 'enabled: isAuthenticated' au useQuery pour fetchDictionaries.