# Frontend Conventions

## Placement Rules

- New routes belong in `src/pages/`.
- New business capabilities belong in `src/features/`.
- Reusable business-object code shared by multiple features belongs in `src/entities/`.
- Cross-feature flows belong in `src/workflows/`.
- Domain-neutral helpers belong in `src/shared/`.
- UI primitives and domain-neutral patterns belong in `src/design-system/`.

## Public Boundaries

- Each feature, entity, and workflow should expose a narrow `index.ts`.
- Do not import another feature's internal files directly.
- Prefer adding a new export over reaching into private folders.

## State Strategy

- Keep server state in explicit API/query layers.
- Keep URL-relevant state in the router when possible.
- Keep ephemeral UI state local.
- Add global client state only with clear justification.

## API Strategy

- Keep generic transport concerns in `src/shared/api/`.
- Keep endpoint-specific DTOs and calls inside the owning feature.
- Map transport payloads before broad UI use when the shape matters.

## Pre-Brief Discipline

- Use generic examples to demonstrate structure.
- Avoid speculative product labels, flows, and role assumptions.
- Prefer replaceable scaffolding over broad placeholder implementation.
