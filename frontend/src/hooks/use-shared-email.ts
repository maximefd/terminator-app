"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * L'adresse e-mail en cours de saisie, partagée entre connexion, inscription et mot de passe oublié.
 *
 * On se trompe souvent de formulaire : on tape son adresse pour s'inscrire alors qu'on avait déjà un
 * compte, ou l'inverse. Passer de l'un à l'autre ne doit pas la faire retaper. Elle est gardée pour
 * l'onglet seulement (`sessionStorage`), jamais dans l'adresse de la page — une adresse e-mail n'a rien
 * à faire dans un historique ou un journal de serveur —, et oubliée une fois connecté.
 * Le mot de passe, lui, n'est jamais gardé.
 */
const KEY = "terminator:email-saisi";

export function useSharedEmail() {
  const [email, setEmailState] = useState("");

  // Lu après le montage : le stockage n'existe pas au rendu statique
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(KEY);
      if (saved) setEmailState(saved);
    } catch {
      // Stockage refusé : le champ part vide, comme avant
    }
  }, []);

  const setEmail = useCallback((value: string) => {
    setEmailState(value);
    try {
      sessionStorage.setItem(KEY, value);
    } catch {
      // Sans stockage, l'adresse ne suivra pas d'un formulaire à l'autre : rien de plus
    }
  }, []);

  const forgetEmail = useCallback(() => {
    try {
      sessionStorage.removeItem(KEY);
    } catch {
      // Rien à oublier si le stockage est refusé
    }
  }, []);

  return { email, setEmail, forgetEmail };
}
