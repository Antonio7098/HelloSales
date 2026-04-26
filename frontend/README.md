# HelloSales Frontend

> **Note**: Project overview lives in the root [README.md](../README.md).

This frontend is scaffolded as a pre-brief, contract-driven React application.

## Goals

- stay highly organized from day one
- keep product assumptions minimal before the brief arrives
- make future extension and possible rehosting straightforward

## Start

```bash
npm install
npm run dev
```

## Key Directories

- `src/app/` - bootstrap, providers, router
- `src/pages/` - route-level assembly
- `src/features/` - bounded business capabilities
- `src/entities/` - reusable business objects
- `src/workflows/` - cross-feature orchestration
- `src/shared/` - domain-neutral infrastructure
- `src/design-system/` - tokens, primitives, patterns
- `src/test/` - shared test setup
- `docs/` - local frontend architecture notes and ADRs

## Documentation

- [frontend-architecture.md](docs/frontend-architecture.md) - Architecture overview
- [conventions.md](docs/conventions.md) - Code conventions
- [decision-records/](docs/decision-records/) - ADRs
