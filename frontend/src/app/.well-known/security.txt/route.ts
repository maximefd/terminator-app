import { site } from "@/config/site";

// Écrit au build dans out/.well-known/security.txt (RFC 9116), pour qui a trouvé une faille
export const dynamic = "force-static";

// La RFC demande une date d'expiration de moins d'un an : chaque déploiement la repousse
const VALIDITY_DAYS = 360;

export function GET() {
  const expires = new Date(Date.now() + VALIDITY_DAYS * 24 * 60 * 60 * 1000);
  const body = [
    `Contact: mailto:${site.securityEmail}`,
    `Expires: ${expires.toISOString().replace(/\.\d{3}Z$/, "Z")}`,
    "Preferred-Languages: fr, en",
    `Canonical: ${site.url}/.well-known/security.txt`,
    `Policy: ${site.url}/contact`,
    "",
  ].join("\n");
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
