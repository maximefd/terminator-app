"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useState, useRef, useMemo, useEffect, KeyboardEvent } from "react";
import { Trash2, PlusCircle } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { toast } from "sonner";

// --- TYPES ---
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

// --- FONCTIONS DE FETCH (mises à jour pour utiliser apiFetch) ---
const fetchDictionaries = async (): Promise<Dictionary[]> => {
  return apiFetch(`/api/dictionaries`);
};

const fetchWords = async (dictionaryId: number): Promise<Word[]> => {
  return apiFetch(`/api/dictionaries/${dictionaryId}/words`);
};

const addWord = async (vars: { dictionaryId: number; mot: string; definition: string }) => {
  return apiFetch(`/api/dictionaries/${vars.dictionaryId}/words`, {
    method: 'POST',
    body: { mot: vars.mot, definition: vars.definition },
  });
};

const deleteWord = async (vars: { dictionaryId: number; wordId: number }) => {
  return apiFetch(`/api/dictionaries/${vars.dictionaryId}/words/${vars.wordId}`, {
    method: 'DELETE',
  });
};

const setActiveDictionary = async (dictionaryId: number) => {
  return apiFetch(`/api/dictionaries/${dictionaryId}`, {
    method: 'PATCH',
    body: { is_active: true },
  });
};

const deleteDictionary = async (dictionaryId: number) => {
  return apiFetch(`/api/dictionaries/${dictionaryId}`, { method: 'DELETE' });
};

const createDictionary = async (name: string) => {
  return apiFetch(`/api/dictionaries`, {
    method: 'POST',
    body: { name },
  });
};

// --- COMPOSANT PRINCIPAL ---
export function DictionaryPanel() {
  const [newWord, setNewWord] = useState("");
  const [newDefinition, setNewDefinition] = useState("");
  const [newDictionaryName, setNewDictionaryName] = useState("");
  const [isCreateDictOpen, setCreateDictOpen] = useState(false);
  const [isDeleteDictOpen, setDeleteDictOpen] = useState(false);
  const queryClient = useQueryClient();
  const wordInputRef = useRef<HTMLInputElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const [sortOrder, setSortOrder] = useState<'date' | 'alpha'>('date');
  const [filterLength, setFilterLength] = useState<string>('all');

  const { data: dictionaries, error: dictError, isLoading: isDictLoading } = useQuery<Dictionary[], Error>({ queryKey: ['dictionaries'], queryFn: fetchDictionaries });
  const activeDictionary = dictionaries?.find(d => d.is_active) || dictionaries?.[0];
  const { data: words, error: wordsError } = useQuery<Word[], Error>({ queryKey: ['words', activeDictionary?.id], queryFn: () => fetchWords(activeDictionary!.id), enabled: !!activeDictionary });

  const addWordMutation = useMutation({
    mutationFn: addWord,
    onSuccess: (data) => {
      toast.success(`Le mot "${data.mot}" a été ajouté.`);
      queryClient.invalidateQueries({ queryKey: ['words', activeDictionary?.id] });
      setNewWord("");
      setNewDefinition("");
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });
  
  useEffect(() => {
    if (addWordMutation.isSuccess) {
      wordInputRef.current?.focus();
      addWordMutation.reset();
    }
  }, [addWordMutation, addWordMutation.isSuccess]);

  const deleteWordMutation = useMutation({
    mutationFn: deleteWord,
    onSuccess: () => {
      toast.success("Mot supprimé.");
      queryClient.invalidateQueries({ queryKey: ['words', activeDictionary?.id] });
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const setActiveDictionaryMutation = useMutation({
    mutationFn: setActiveDictionary,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dictionaries'] });
    },
     onError: (error) => {
      toast.error(error.message);
    },
  });

  const createDictionaryMutation = useMutation({
    mutationFn: createDictionary,
    onSuccess: () => {
      toast.success("Dictionnaire créé !");
      queryClient.invalidateQueries({ queryKey: ['dictionaries'] });
      setNewDictionaryName("");
      setCreateDictOpen(false);
    },
     onError: (error) => {
      toast.error(error.message);
    },
  });

  const deleteDictionaryMutation = useMutation({
    mutationFn: deleteDictionary,
    onSuccess: async (_data, deletedId: number) => {
      toast.success("Dictionnaire supprimé.");
      setDeleteDictOpen(false);
      // Supprimer l'actif n'en laisse aucun d'actif côté serveur : la recherche et les grilles
      // perdraient les mots personnels alors que le sélecteur en montre toujours un. On réactive.
      const deleted = dictionaries?.find(d => d.id === deletedId);
      const remaining = (dictionaries ?? []).filter(d => d.id !== deletedId);
      if (deleted?.is_active && remaining.length > 0) {
        await setActiveDictionary(remaining[0].id).catch(() => undefined);
      }
      queryClient.invalidateQueries({ queryKey: ['dictionaries'] });
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const sortedAndFilteredWords = useMemo(() => {
    if (!words) return [];
    let processedWords = [...words];
    if (filterLength !== 'all') {
      const length = parseInt(filterLength, 10);
      if (!isNaN(length) && length > 0) {
        processedWords = processedWords.filter(word => word.mot.length === length);
      }
    }
    if (sortOrder === 'alpha') {
      processedWords.sort((a, b) => a.mot.localeCompare(b.mot));
    } else {
      processedWords.sort((a, b) => b.id - a.id);
    }
    return processedWords;
  }, [words, sortOrder, filterLength]);
  
  const handleAddWordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newWord && activeDictionary) {
      addWordMutation.mutate({ dictionaryId: activeDictionary.id, mot: newWord, definition: newDefinition });
    }
  };
  
  const handleActiveDictionaryChange = (dictionaryId: string) => {
    const id = parseInt(dictionaryId, 10);
    if (!isNaN(id)) {
      setActiveDictionaryMutation.mutate(id);
    }
  };
  
  const handleCreateDictionarySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newDictionaryName) {
      createDictionaryMutation.mutate(newDictionaryName);
    }
  };

  const handleDefinitionKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      formRef.current?.requestSubmit();
    }
  };

  if (isDictLoading) return <div className="p-4 text-sm text-muted-foreground">Chargement...</div>;
  const currentError = dictError || wordsError;
  if (currentError) return <aside className="w-full rounded-lg border bg-destructive/10 p-4 text-destructive"><h2 className="text-lg font-semibold">Erreur</h2><p className="text-sm">{currentError.message}</p></aside>;

  return (
    <aside className="flex w-full flex-col rounded-lg border bg-card p-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Mes dictionnaires</h2>
        <Dialog open={isCreateDictOpen} onOpenChange={setCreateDictOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Créer un dictionnaire"><PlusCircle className="h-5 w-5" /></Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Créer un nouveau dictionnaire</DialogTitle>
             <DialogDescription>
                Entrez le nom de votre nouvelle liste de mots. Vous pourrez y ajouter des mots par la suite.
              </DialogDescription></DialogHeader>
            <form onSubmit={handleCreateDictionarySubmit} className="grid gap-4 py-4">
              <div className="grid grid-cols-4 items-center gap-4">
                <Label htmlFor="dict-name" className="text-right">Nom</Label>
                <Input id="dict-name" value={newDictionaryName} onChange={(e) => setNewDictionaryName(e.target.value)} className="col-span-3" required />
              </div>
              <Button type="submit" disabled={createDictionaryMutation.isPending}>{createDictionaryMutation.isPending ? "Création..." : "Créer le dictionnaire"}</Button>
              {createDictionaryMutation.isError && <p className="text-sm text-destructive text-center">{createDictionaryMutation.error.message}</p>}
            </form>
          </DialogContent>
        </Dialog>
      </div>
      
      <div className="mt-2 flex items-center gap-2">
        <Select value={activeDictionary?.id.toString()} onValueChange={handleActiveDictionaryChange} disabled={setActiveDictionaryMutation.isPending}>
          <SelectTrigger className="flex-1" aria-label="Dictionnaire actif"><SelectValue placeholder="Sélectionner un dictionnaire..." /></SelectTrigger>
          <SelectContent>
            {dictionaries?.map(dict => (<SelectItem key={dict.id} value={dict.id.toString()}>{dict.name}</SelectItem>))}
          </SelectContent>
        </Select>
        <Dialog open={isDeleteDictOpen} onOpenChange={setDeleteDictOpen}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0" aria-label="Supprimer ce dictionnaire" disabled={!activeDictionary}>
              <Trash2 className="h-4 w-4 text-muted-foreground" />
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Supprimer « {activeDictionary?.name} » ?</DialogTitle>
              <DialogDescription>
                Ses {words?.length ?? 0} mot{(words?.length ?? 0) > 1 ? "s" : ""} seront effacés avec lui.
                C&apos;est définitif : Terminator ne garde pas de copie.
                {dictionaries?.length === 1 && " C'est votre dernier : un « Dictionnaire par défaut » vide prendra sa place."}
              </DialogDescription>
            </DialogHeader>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setDeleteDictOpen(false)}>Annuler</Button>
              <Button
                variant="destructive"
                disabled={deleteDictionaryMutation.isPending}
                onClick={() => activeDictionary && deleteDictionaryMutation.mutate(activeDictionary.id)}
              >
                {deleteDictionaryMutation.isPending ? "Suppression…" : "Supprimer définitivement"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <p className="mt-2 text-xs text-muted-foreground">
        Le dictionnaire choisi ici est l&apos;<strong>actif</strong> : ses mots remontent en tête de la
        recherche par motif et sont proposés aux grilles que vous générez.
      </p>

      <div className="mt-4 flex flex-col flex-1">
        <h3 className="font-semibold mb-2">Mots ({sortedAndFilteredWords?.length || 0})</h3>
      
        <form ref={formRef} onSubmit={handleAddWordSubmit} className="mb-4 border-b pb-4">
          <div className="grid gap-2">
             <Label htmlFor="mot" className="text-xs font-semibold">Nouveau mot</Label>
             <Input id="mot" ref={wordInputRef} value={newWord} onChange={(e) => setNewWord(e.target.value)} placeholder="Appuyer sur Entrée pour ajouter" disabled={!activeDictionary || addWordMutation.isPending} required />
             <Label htmlFor="definition" className="text-xs font-semibold">Définition (optionnel)</Label>
             <Input id="definition" value={newDefinition} onChange={(e) => setNewDefinition(e.target.value)} placeholder="Définition du mot..." disabled={!activeDictionary || addWordMutation.isPending} onKeyDown={handleDefinitionKeyDown} />
             <Button type="submit" size="sm" className="mt-2" disabled={!activeDictionary || addWordMutation.isPending}>{addWordMutation.isPending ? "Ajout en cours..." : "Ajouter le mot"}</Button>
             {addWordMutation.isError && <p className="text-xs text-destructive mt-2">{addWordMutation.error.message}</p>}
          </div>
        </form>

        <div className="flex items-center justify-between gap-2 mb-2">
            <Select value={sortOrder} onValueChange={(value: 'date' | 'alpha') => setSortOrder(value)}>
                <SelectTrigger className="flex-1"><SelectValue placeholder="Trier par..." /></SelectTrigger>
                <SelectContent>
                    <SelectItem value="date">Plus récents d&apos;abord</SelectItem>
                    <SelectItem value="alpha">Ordre alphabétique</SelectItem>
                </SelectContent>
            </Select>
            <Input type="number" min="1" placeholder="Lg." className="w-20" aria-label="Filtrer par longueur" onChange={(e) => setFilterLength(e.target.value || 'all')} />
        </div>

        <ScrollArea className="flex-1 rounded-md border mt-2">
          <div className="p-4">
            {sortedAndFilteredWords.length > 0 ? (
              sortedAndFilteredWords.map((word) => (
                <div key={word.id} className="group mb-2 flex items-start justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <p className="font-mono font-semibold">{word.mot}</p>
                    {word.definition && <p className="text-xs text-muted-foreground">{word.definition}</p>}
                  </div>
                  {/* Visible au survol, mais aussi au focus : sinon le bouton est inatteignable au clavier */}
                  <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0 opacity-0 focus-visible:opacity-100 group-hover:opacity-100" aria-label={`Supprimer ${word.mot}`} onClick={() => {if (activeDictionary) {deleteWordMutation.mutate({ dictionaryId: activeDictionary.id, wordId: word.id });}}} disabled={deleteWordMutation.isPending}>
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
              ))
            ) : (
              <p className="text-sm italic text-muted-foreground">
                {words?.length
                  ? "Aucun mot de cette longueur dans ce dictionnaire."
                  : "Ce dictionnaire est vide : ajoutez un premier mot ci-dessus."}
              </p>
            )}
          </div>
        </ScrollArea>
      </div>
    </aside>
  );
}