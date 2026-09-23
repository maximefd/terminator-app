"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useAuth } from "@/contexts/auth-context";
import { apiFetch } from "@/lib/api-client";

type Account = { email: string; dictionaries: number; words: number; grids: number };

function count(value: number, singular: string, plural: string) {
  return `${value} ${value > 1 ? plural : singular}`;
}

/** Ce que la suppression efface, compté : « 2 dictionnaires, 14 mots et 3 grilles ». */
function contents(account: Account) {
  const parts = [
    count(account.dictionaries, "dictionnaire", "dictionnaires"),
    count(account.words, "mot", "mots"),
    count(account.grids, "grille conservée", "grilles conservées"),
  ];
  return `${parts.slice(0, -1).join(", ")} et ${parts.at(-1)}`;
}

export function AccountClientLayout() {
  const { isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirming, setConfirming] = useState(false);

  const account = useQuery<Account>({
    queryKey: ["account"],
    queryFn: () => apiFetch("/api/users/me"),
    enabled: isAuthenticated,
  });

  const deletion = useMutation({
    mutationFn: () => apiFetch("/api/users/me", { method: "DELETE", body: { password } }),
    onSuccess: () => {
      setConfirming(false);
      logout();
      toast.success("Votre compte et toutes ses données ont été supprimés.");
      router.push("/");
    },
    // Mauvais mot de passe : on referme la confirmation pour laisser corriger le champ
    onError: (error: Error) => {
      setConfirming(false);
      toast.error(error.message);
    },
  });

  if (isLoading) {
    return (
      <main className="container mx-auto max-w-2xl p-4 md:p-8">
        <p className="text-center text-sm text-muted-foreground">Chargement…</p>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <main className="container mx-auto max-w-2xl p-4 md:p-8">
        <div className="rounded-lg border bg-secondary/20 p-6 text-center">
          <h1 className="text-xl font-semibold">Vous n&apos;êtes pas connecté</h1>
          <p className="mt-2 text-sm text-muted-foreground">Connectez-vous pour voir votre compte.</p>
          <Button asChild size="sm" className="mt-4">
            <Link href="/login">Se connecter</Link>
          </Button>
        </div>
      </main>
    );
  }

  return (
    <main className="container mx-auto max-w-2xl space-y-8 p-4 md:p-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Mon compte</h1>
        {account.data ? (
          <p className="mt-2 text-muted-foreground">
            Connecté avec <span className="font-medium text-foreground">{account.data.email}</span>.
            Votre compte contient {contents(account.data)}.
          </p>
        ) : account.isError ? (
          <p className="mt-2 text-sm text-destructive">{account.error.message}</p>
        ) : (
          <p className="mt-2 text-sm text-muted-foreground">Chargement…</p>
        )}
        <p className="mt-2 text-sm text-muted-foreground">
          Ce que Terminator conserve, et rien d&apos;autre : voir la{" "}
          <Link href="/privacy" className="underline underline-offset-2 hover:text-foreground">
            page de confidentialité
          </Link>
          .
        </p>
      </div>

      <section className="space-y-4 rounded-lg border border-destructive/40 p-6">
        <div>
          <h2 className="text-lg font-semibold">Supprimer mon compte</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Votre adresse e-mail, votre mot de passe, vos dictionnaires, leurs mots et vos grilles conservées
            sont effacés. C&apos;est <strong className="text-foreground">définitif</strong> : rien ne pourra être
            récupéré.
          </p>
        </div>
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            setConfirming(true);
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="delete-password">Votre mot de passe, pour confirmer</Label>
            <Input
              id="delete-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="max-w-sm"
            />
          </div>
          <Button type="submit" variant="destructive" disabled={!password || deletion.isPending}>
            Supprimer mon compte…
          </Button>
        </form>
      </section>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Supprimer définitivement votre compte ?</DialogTitle>
            <DialogDescription>
              {account.data
                ? `${account.data.email} et ${contents(account.data)} seront effacés. Cette action est irréversible.`
                : "Votre compte et toutes ses données seront effacés. Cette action est irréversible."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Annuler</Button>
            </DialogClose>
            <Button variant="destructive" onClick={() => deletion.mutate()} disabled={deletion.isPending}>
              {deletion.isPending ? "Suppression…" : "Supprimer définitivement"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
