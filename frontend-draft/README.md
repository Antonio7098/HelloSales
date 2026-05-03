# HelloSales Frontend Draft

## Prerequisites

- **Node.js 20+**
- **npm 10+**

## Project Structure

```
frontend-draft/
├── src/
│   ├── app/              # bootstrap, providers, router
│   ├── pages/            # route-level assembly
│   ├── features/         # bounded business capabilities
│   ├── entities/        # reusable business objects
│   ├── workflows/       # cross-feature orchestration
│   ├── shared/          # domain-neutral infrastructure
│   ├── design-system/  # tokens, primitives, patterns
│   └── test/            # shared test setup
├── docs/
│   └── local frontend architecture notes
├── package.json
└── vite.config.ts
```

This frontend is scaffolded as a pre-brief, contract-driven React application.

## What Works / What Doesn't

### Works
- React 19 + TypeScript 5.9 foundation
- Vite 7 dev server with HMR
- React Router 7 for navigation
- API proxy to backend for dev

### Doesn't Work Yet
- Full feature set
- Production deployment

## Getting Started

```bash
npm install
npm run dev
```

Dev server runs on `http://localhost:5173`.

## Commands

| Command | Description |
|---|---|
| `npm run dev` | Start dev server with HMR |
| `npm run build` | Build for production |
| `npm run lint` | Run ESLint |
| `npm run test` | Run tests (watch mode) |
| `npm run test:run` | Run tests (single run) |

## Tech Stack

- React 19.2
- TypeScript 5.9
- Vite 7.1
- React Router 7.9

## API Proxy

Vite proxies `/api/*` requests to the backend configured via `VITE_API_PROXY_TARGET`.
In Docker, this defaults to `http://backend:8000`.

## Troubleshooting

### Port 5173 already in use
- Change port: `npm run dev -- --port 5175`

### Module errors
- Reinstall: `rm -rf node_modules && npm install`

## Related Docs

- [../README.md](../README.md) - Project overview
- [../frontend/README.md](../frontend/README.md) - Main frontend docs