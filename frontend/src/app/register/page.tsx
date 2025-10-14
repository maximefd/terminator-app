"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { register } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await register(email, password);
      router.push("/");
    } catch (err: unknown) { // CORRECTION ICI : on utilise 'unknown' au lieu de 'any'
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Une erreur inattendue est survenue.");
      }
    }
  };

  return (
    <main className="flex items-center justify-center py-16 md:py-24">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-2xl">Inscription</CardTitle>
          <CardDescription>
            Créez votre compte pour sauvegarder vos dictionnaires personnels.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="nom@exemple.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full">
              Créer un compte
            </Button>
          </form>
          <div className="mt-4 text-center text-sm">
            Vous avez déjà un compte ?{" "}
            <Link href="/login" className="underline">
              Se connecter
            </Link>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}

