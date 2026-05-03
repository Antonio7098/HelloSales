# HelloSales Frontend

> **Note**: Project overview lives in the root [README.md](../README.md).

## Prerequisites

- **Node.js 20+**
- **npm 10+**

## Project Structure

```
frontend/
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
│   ├── frontend-architecture.md
│   ├── conventions.md
│   └── decision-records/
├── package.json
└── vite.config.ts
```

This frontend is scaffolded as a pre-brief, contract-driven React application.

## What Works / What Doesn't

### Works
- React 19 + TypeScript 5.9 foundation
- Vite 7 dev server with HMR
- React Router 7 for navigation
- Design system tokens and primitives
- Vitest testing with React Testing Library
- ESLint + Prettier setup
- API proxy to backend

### Doesn't Work Yet
- Real API integration (proxies to backend-draft)
- Feature modules
- Authentication flow

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
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
| `npm run test` | Run tests (watch mode) |
| `npm run test:run` | Run tests (single run) |
| `npm run test:coverage` | Run tests with coverage |

## Tech Stack

- React 19.2
- TypeScript 5.9
- Vite 7.1
- React Router 7.9
- Vitest 4.0
- ESLint 9.24

## API Proxy

Vite proxies `/api/*` requests to the backend configured via `VITE_API_PROXY_TARGET`.
In development, this defaults to `http://localhost:8000`.

## Documentation

- [docs/frontend-architecture.md](docs/frontend-architecture.md) - Architecture overview
- [docs/conventions.md](docs/conventions.md) - Code conventions
- [docs/decision-records/](docs/decision-records/) - ADRs

## Troubleshooting

### "module not found" errors
- Run `npm install` again
- Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`

### Port 5173 already in use
- Stop other Vite processes: `pkill -f vite`
- Or change port in `.env`: `VITE_PORT=5175`

### Backend not connecting
- Ensure backend is running: `curl http://localhost:8000/api/system/health`
- Check `VITE_API_PROXY_TARGET` in Vite config

### Typescript errors
- Check `tsconfig.json` settings
- Ensure Node types installed: `npm i -D @types/node`

## Related Docs

- [../README.md](../README.md) - Project overview
- [docs/frontend-architecture.md](docs/frontend-architecture.md) - Architecture
- [docs/conventions.md](docs/conventions.md) - Code conventions