# Project Instructions

## Package Manager
- ALWAYS use `bun` for all package management (install, run scripts, etc.)
- NEVER use npm, yarn, or pnpm

## Tech Stack
- Next.js 15 (App Router)
- Convex backend (self-hosted via Docker)
- BetterAuth with Convex integration
- Tailwind v4
- shadcn/ui components

## Adding UI Components
- Use `bun dlx shadcn@latest add <component>` to add new components
- Components are installed to `components/ui/`

## Development Setup

### 1. Start the Convex backend (Docker)
```bash
cd backend && docker compose up -d
```

### 2. Set Convex environment variables (one-time setup)
These must be set in the Convex deployment, not just .env.local:
```bash
cd frontend
CONVEX_SELF_HOSTED_URL=http://localhost:3001 CONVEX_SELF_HOSTED_ADMIN_KEY="<key from backend>" bunx convex env set BETTER_AUTH_SECRET <secret>
CONVEX_SELF_HOSTED_URL=http://localhost:3001 CONVEX_SELF_HOSTED_ADMIN_KEY="<key from backend>" bunx convex env set SITE_URL http://localhost:3000
CONVEX_SELF_HOSTED_URL=http://localhost:3001 CONVEX_SELF_HOSTED_ADMIN_KEY="<key from backend>" bunx convex env set BETTER_AUTH_URL http://localhost:3000
```

### 3. Run Convex dev (via mcproc)
```bash
cd frontend && CONVEX_SELF_HOSTED_URL=http://localhost:3001 CONVEX_SELF_HOSTED_ADMIN_KEY="<key>" bunx convex dev
```

### 4. Run Next.js dev server (via mcproc)
```bash
cd frontend && bun run dev
```

## Development Commands
- `cd backend && docker compose up -d` - Start local development backend services
- `cd backend && docker compose down` - Stop backend services
- `cd frontend && bunx convex dev` - Run Convex backend (keep running during development)
- `cd frontend && bun run dev` - Start Next.js development server
- `cd frontend && bun run lint` - Run ESLint

## Auth Endpoints
- Sign up: `POST /api/auth/sign-up/email`
- Sign in: `POST /api/auth/sign-in/email`

## Notes
- Keep `bunx convex dev` running while developing
- Better Auth runs on Convex, not in Next.js
- Auth routes are proxied through `app/api/auth/[...all]/route.ts`
- Convex env vars must be set via `bunx convex env set` not just .env.local

## Default Test Credentials
- Default name: Test User
- Default email: test@example.com
- Default password: Password