# Consola del analista — CENTINELA (HU-02)

App Next.js (App Router + TypeScript) para la bandeja de casos de fraude.

## Arranque local

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Abre [http://localhost:3000](http://localhost:3000) → redirige a `/cases`.

## Variables de entorno

| Variable | Alcance | Descripción |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE` | Build / servidor | URL base de la API FastAPI (p. ej. `http://localhost:8000`) |
| `API_BASE_URL` | Solo servidor | Override opcional de la base (prioridad sobre `NEXT_PUBLIC_API_BASE`) |
| `ANALYST_API_KEY` | **Solo servidor** | Clave `X-API-Key` con rol `analista`. **Nunca** usar prefijo `NEXT_PUBLIC_` |

El navegador solo llama a `/api/*` (BFF). La API key se inyecta en los route handlers.

## Scripts

| Comando | Uso |
|---------|-----|
| `npm run dev` | Desarrollo |
| `npm run build` | Build de producción |
| `npm run start` | Servir build |
| `npm run lint` | ESLint |
| `npm run test` | Vitest + Testing Library |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run format` | Prettier |

## Arquitectura

```
Browser  →  /api/cases (Next BFF)  →  GET {API}/cases  (+ X-API-Key)
                ↑
         TanStack Query + DTOs tipados (CaseSummaryDto, CaseDetailDto, ExplanationDto)
```

## Autenticación de usuario (fuera de alcance)

Esta historia **no** implementa login de usuarios (OIDC / sesión). La autorización
hacia la API backend se hace con la API key de analista en el servidor Next.
Auth de usuario real queda para una historia posterior.

## Hosting (Jorge)

Build listo con `npm run build`. Configurar en el hosting:

- `NEXT_PUBLIC_API_BASE` = URL pública de la API
- `ANALYST_API_KEY` = secreto del Key Vault / App Settings (no en el cliente)
