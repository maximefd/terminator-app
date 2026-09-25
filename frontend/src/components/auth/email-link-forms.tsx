"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api-client";
import { useSharedEmail } from "@/hooks/use-shared-email";

/**
 * Les écrans des e-mails du compte (ADR 0014) : demander un lien, choisir un nouveau mot de passe,
 * confirmer son adresse. Les deux derniers lisent le jeton dans l'adresse (`?token=`) : leurs pages
 * les enveloppent dans un <Suspense>, que Next exige autour de useSearchParams.
 */

function errorMessage(err: unknown) {
  return err instanceof Error ? err.message : "Une erreur inattendue est survenue.";
}

function Frame({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return (
    <main className="flex items-center justify-center py-16 md:py-24">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>{children}</CardContent>
      </Card>
    </main>
  );
}

export function ForgotPasswordForm() {
  // La même adresse que sur la page de connexion, d'où l'on vient presque toujours
  const { email, setEmail } = useSharedEmail();
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const data = await apiFetch("/api/auth/password/forgot", { method: "POST", body: { email } });
      setSent(data.message);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Frame title="Mot de passe oublié" description="Un lien vous sera envoyé pour en choisir un nouveau.">
      {sent ? (
        <div className="space-y-4 text-sm">
          <p role="status">{sent}</p>
          <Link href="/login" className="underline">Retour à la connexion</Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="nom@exemple.com"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Envoi…" : "Recevoir le lien"}
          </Button>
        </form>
      )}
    </Frame>
  );
}

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const data = await apiFetch("/api/auth/password/reset", { method: "POST", body: { token, password } });
      setDone(data.message);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!token) {
    return (
      <Frame title="Nouveau mot de passe" description="Ce lien est incomplet.">
        <Link href="/forgot-password" className="text-sm underline">Demander un nouveau lien</Link>
      </Frame>
    );
  }

  return (
    <Frame title="Nouveau mot de passe" description="Entre 8 et 128 caractères.">
      {done ? (
        <div className="space-y-4 text-sm">
          <p role="status">{done}</p>
          <Button asChild className="w-full">
            <Link href="/login">Se connecter</Link>
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="password">Nouveau mot de passe</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error && (
            <p className="text-sm text-destructive">
              {error}{" "}
              <Link href="/forgot-password" className="underline">Nouveau lien</Link>
            </p>
          )}
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Enregistrement…" : "Changer le mot de passe"}
          </Button>
        </form>
      )}
    </Frame>
  );
}

export function VerifyEmail() {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<{ ok: boolean; message: string } | null>(null);
  // Le mode strict de React monte deux fois en développement : le lien ne doit partir qu'une fois
  const sent = useRef(false);

  useEffect(() => {
    if (!token || sent.current) return;
    sent.current = true;
    apiFetch("/api/auth/email/verify", { method: "POST", body: { token } })
      .then((data) => setState({ ok: true, message: data.message }))
      .catch((err) => setState({ ok: false, message: errorMessage(err) }));
  }, [token]);

  const message = !token ? "Ce lien est incomplet." : state?.message ?? "Vérification…";
  return (
    <Frame title="Confirmation de l'adresse" description="Le lien reçu par e-mail à l'inscription.">
      <div className="space-y-4 text-sm">
        <p role="status" className={state && !state.ok ? "text-destructive" : undefined}>{message}</p>
        {state && !state.ok && (
          <p className="text-muted-foreground">
            Un nouveau lien se demande depuis <Link href="/account" className="underline">Mon compte</Link>.
          </p>
        )}
        {state?.ok && <Link href="/" className="underline">Aller à l&apos;accueil</Link>}
      </div>
    </Frame>
  );
}
