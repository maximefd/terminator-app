# Frontend — Terminator

Application Next.js 15 (App Router, React 19, TypeScript, Tailwind CSS 4, shadcn/ui, React Query), gérée avec **pnpm**.

Installation et démarrage : voir le [README principal](../README.md) (`make setup`, `make dev-front`).

| Commande (depuis `frontend/`) | Rôle |
|-------------------------------|------|
| `pnpm dev` | Serveur de développement (http://localhost:3000) |
| `pnpm lint` | ESLint |
| `pnpm exec tsc --noEmit` | Vérification TypeScript |
| `pnpm build` | Build de production |
| `pnpm exec playwright test` | Tests end-to-end (API démarrée) |

**URL de l'API** : `NEXT_PUBLIC_API_BASE_URL`, sinon `http://localhost:5001` en local (voir `src/lib/utils.ts`).

Organisation du code et authentification : [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md#frontend-frontend).
