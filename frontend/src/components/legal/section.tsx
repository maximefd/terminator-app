import { type ReactNode } from "react";

/** Mise en forme commune des pages de texte : contact, mentions légales, confidentialité, conditions. */
export function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-xl font-semibold text-foreground">{title}</h2>
      {children}
    </section>
  );
}

export const linkClass = "underline underline-offset-2 hover:text-foreground";
