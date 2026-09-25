"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { NotFoundContent } from "@/components/layout/not-found-content";
import { useAuth } from "@/contexts/auth-context";
import { ApiError, apiFetch } from "@/lib/api-client";
import { site } from "@/config/site";

/** Les chiffres de `GET /api/admin/stats` (backend/stats.py, `as_json`) : des agrégats seulement. */
type Period = {
  label: string;
  days: number;
  visitors: number;
  searches: number;
  generations: number;
  grids: number;
  success: string;
  busy: number;
  rate_limited: number;
  p50: number | null;
  p95: number | null;
  cpu_s: number;
  cpu_share: number;
  register: number;
  verify: number;
  login: number;
  delete: number;
  saved: number;
  errors: number;
  server_errors: number;
};

type Split = { grid: number; failed: number };

type AdminStats = {
  now: string;
  periods: Period[];
  thresholds: { p95_ms: number | null; p95_limit_ms: number; busy_share: number; busy_limit: number };
  outcomes: { outcome: string; count: number }[];
  formats: ({ format: string } & Split)[];
  by_must_count: ({ must: number } & Split)[];
  unknown_words: { word: string; count: number }[];
  countries: { country: string; events: number }[];
  errors: { route: string; status: number; count: number }[];
  latest: { at: string; format: string | null; layout: string | null; outcome: string | null; duration_ms: number | null; must: number }[];
};

const number = new Intl.NumberFormat("fr-FR");
const dateTime = new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short", timeZone: "UTC" });

function seconds(ms: number | null) {
  return ms === null ? "—" : `${(ms / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 2 })} s`;
}

function percent(share: number, digits = 1) {
  return `${(100 * share).toLocaleString("fr-FR", { maximumFractionDigits: digits })} %`;
}

function rate({ grid, failed }: Split) {
  const total = grid + failed;
  return total ? `${Math.round((100 * grid) / total)} %` : "—";
}

const ROWS: { label: string; value: (period: Period) => string; indent?: boolean }[] = [
  { label: "Visiteurs (somme par jour)", value: (p) => number.format(p.visitors) },
  { label: "Recherches", value: (p) => number.format(p.searches) },
  { label: "Générations demandées", value: (p) => number.format(p.generations) },
  { label: "grilles obtenues", value: (p) => number.format(p.grids), indent: true },
  { label: "taux de réussite", value: (p) => p.success, indent: true },
  { label: "refus « occupé »", value: (p) => number.format(p.busy), indent: true },
  { label: "refus de limite de débit", value: (p) => number.format(p.rate_limited), indent: true },
  { label: "durée médiane (réussies)", value: (p) => seconds(p.p50), indent: true },
  { label: "durée p95 (réussies)", value: (p) => seconds(p.p95), indent: true },
  { label: "temps CPU", value: (p) => `${number.format(Math.round(p.cpu_s))} s`, indent: true },
  { label: "part de la capacité CPU", value: (p) => percent(p.cpu_share, 2), indent: true },
  { label: "Inscriptions", value: (p) => number.format(p.register) },
  { label: "Adresses confirmées", value: (p) => number.format(p.verify) },
  { label: "Connexions", value: (p) => number.format(p.login) },
  { label: "Comptes supprimés", value: (p) => number.format(p.delete) },
  { label: "Grilles conservées", value: (p) => number.format(p.saved) },
  { label: "Erreurs (4xx et 5xx)", value: (p) => number.format(p.errors) },
  { label: "dont 5xx", value: (p) => number.format(p.server_errors), indent: true },
];

function Section({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function Empty() {
  return <p className="text-sm text-muted-foreground">Rien pour l&apos;instant.</p>;
}

function Indicator({ label, value, limit, exceeded }: { label: string; value: string; limit: string; exceeded: boolean }) {
  return (
    <div className={`rounded-lg border p-4 ${exceeded ? "border-destructive bg-destructive/5" : ""}`}>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      <p className={`mt-1 text-xs ${exceeded ? "font-medium text-destructive" : "text-muted-foreground"}`}>
        {exceeded ? `Seuil dépassé (${limit})` : `Seuil : ${limit}`}
      </p>
    </div>
  );
}

function Dashboard({ stats }: { stats: AdminStats }) {
  const { thresholds } = stats;
  // Le titre statique est celui de la page 404 (app/admin/page.tsx) : le vrai n'apparaît qu'ici
  useEffect(() => {
    document.title = `Poste de pilotage | ${site.name}`;
  }, []);
  const p95Exceeded = thresholds.p95_ms !== null && thresholds.p95_ms > thresholds.p95_limit_ms;
  const busyExceeded = thresholds.busy_share > thresholds.busy_limit;

  return (
    <main className="container mx-auto max-w-6xl space-y-6 p-4 md:p-8">
      <header>
        <h1 className="text-3xl font-bold">Poste de pilotage</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Mesure d&apos;usage au {dateTime.format(new Date(stats.now))} UTC, sans cookie ni adresse IP (ADR 0016).
          Un visiteur est une empreinte du jour : sur 7 ou 30 jours, c&apos;est la somme des visiteurs de chaque jour.
        </p>
      </header>

      <section aria-label="Seuils de l'ADR 0013" className="grid gap-4 sm:grid-cols-2">
        <Indicator label="Durée p95 des générations réussies (30 jours)" value={seconds(thresholds.p95_ms)}
          limit={seconds(thresholds.p95_limit_ms)} exceeded={p95Exceeded} />
        <Indicator label="Refus « occupé » (30 jours)" value={percent(thresholds.busy_share)}
          limit={percent(thresholds.busy_limit, 0)} exceeded={busyExceeded} />
      </section>

      <Section title="Chiffres" description="Aujourd'hui depuis minuit UTC, puis les 7 et 30 derniers jours.">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium" scope="col"><span className="sr-only">Mesure</span></th>
                {stats.periods.map((period) => (
                  <th key={period.label} className="py-2 pl-4 text-right font-medium" scope="col">{period.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.label} className="border-b last:border-0">
                  <th scope="row" className={`py-1.5 pr-4 text-left font-normal ${row.indent ? "pl-4 text-muted-foreground" : ""}`}>
                    {row.label}
                  </th>
                  {stats.periods.map((period) => (
                    <td key={period.label} className="py-1.5 pl-4 text-right tabular-nums">{row.value(period)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Formats" description="30 jours, hors refus.">
          {stats.formats.length === 0 ? <Empty /> : (
            <ul className="space-y-1 text-sm">
              {stats.formats.map((item) => (
                <li key={item.format} className="flex justify-between gap-4 tabular-nums">
                  <span>{item.format}</span>
                  <span>{number.format(item.grid + item.failed)} demandes, réussite {rate(item)}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Mots imposés" description="Réussite selon leur nombre, 30 jours.">
          {stats.by_must_count.length === 0 ? <Empty /> : (
            <ul className="space-y-1 text-sm">
              {stats.by_must_count.map((item) => (
                <li key={item.must} className="flex justify-between gap-4 tabular-nums">
                  <span>{item.must === 3 ? "3 et plus" : item.must}</span>
                  <span>{number.format(item.grid + item.failed)} demandes, réussite {rate(item)}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Mots imposés absents du lexique" description="30 jours : de quoi nourrir la curation.">
          {stats.unknown_words.length === 0 ? <Empty /> : (
            <ul className="flex flex-wrap gap-2 text-sm">
              {stats.unknown_words.map((item) => (
                <li key={item.word} className="rounded-md border px-2 py-0.5">
                  {item.word} <span className="text-muted-foreground tabular-nums">× {item.count}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Issues des générations" description="30 jours.">
          {stats.outcomes.length === 0 ? <Empty /> : (
            <ul className="space-y-1 text-sm">
              {stats.outcomes.map((item) => (
                <li key={item.outcome} className="flex justify-between gap-4 tabular-nums">
                  <span>{item.outcome}</span>
                  <span>{number.format(item.count)}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Pays" description="30 jours, en événements (CF-IPCountry).">
          {stats.countries.length === 0 ? <Empty /> : (
            <ul className="space-y-1 text-sm">
              {stats.countries.map((item) => (
                <li key={item.country} className="flex justify-between gap-4 tabular-nums">
                  <span>{item.country}</span>
                  <span>{number.format(item.events)}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Erreurs par route" description="30 jours.">
          {stats.errors.length === 0 ? <Empty /> : (
            <ul className="space-y-1 text-sm">
              {stats.errors.map((item) => (
                <li key={`${item.route} ${item.status}`} className="flex justify-between gap-4 tabular-nums">
                  <span className="break-all"><span className="font-medium">{item.status}</span> {item.route}</span>
                  <span>{number.format(item.count)}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <Section title="Dernières générations">
        {stats.latest.length === 0 ? <Empty /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th scope="col" className="py-2 pr-4 font-medium">Quand (UTC)</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Format</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Mise en page</th>
                  <th scope="col" className="py-2 pr-4 font-medium">Issue</th>
                  <th scope="col" className="py-2 pr-4 text-right font-medium">Durée</th>
                  <th scope="col" className="py-2 text-right font-medium">Mots imposés</th>
                </tr>
              </thead>
              <tbody>
                {stats.latest.map((item) => (
                  <tr key={item.at + (item.layout ?? "")} className="border-b last:border-0 tabular-nums">
                    <td className="py-1.5 pr-4">{dateTime.format(new Date(item.at))}</td>
                    <td className="py-1.5 pr-4">{item.format ?? "?"}</td>
                    <td className="py-1.5 pr-4">{item.layout ?? "—"}</td>
                    <td className="py-1.5 pr-4">{item.outcome ?? "?"}</td>
                    <td className="py-1.5 pr-4 text-right">{seconds(item.duration_ms)}</td>
                    <td className="py-1.5 text-right">{item.must}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </main>
  );
}

/**
 * Le poste de pilotage (ADR 0016, point 6). La page est dans l'export statique, donc publique : c'est l'API
 * qui garde les chiffres, et qui répond 404 à tout autre compte. Ici, tout autre visiteur voit la page 404.
 */
export function AdminDashboard() {
  const { isAuthenticated, isLoading } = useAuth();
  const stats = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    enabled: isAuthenticated,
    retry: false,
    queryFn: async () => {
      // /api/admin répond 404 à un jeton expiré, jamais 401 : apiFetch ne renouvellerait pas la session.
      // Une lecture ordinaire la renouvelle d'abord si besoin.
      await apiFetch("/api/users/me");
      return apiFetch("/api/admin/stats");
    },
  });

  if (isLoading || (isAuthenticated && stats.isPending)) {
    return <main className="container mx-auto p-4 py-16 text-center text-muted-foreground md:p-8">Chargement…</main>;
  }
  if (!isAuthenticated || (stats.error instanceof ApiError && stats.error.status === 404)) {
    return <NotFoundContent />;
  }
  if (stats.error || !stats.data) {
    return (
      <main className="container mx-auto p-4 py-16 text-center md:p-8">
        <p className="text-destructive">{stats.error?.message ?? "Chiffres indisponibles."}</p>
      </main>
    );
  }
  return <Dashboard stats={stats.data} />;
}
