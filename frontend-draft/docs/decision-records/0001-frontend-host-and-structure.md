# ADR 0001: Frontend Host And Structure

## Status
Accepted

## Decision

Use:
- Vite as the initial frontend host
- React with TypeScript
- a feature-first structure with explicit `app`, `pages`, `features`, `entities`, `workflows`, `shared`, and `design-system` layers

## Rationale

This keeps the pre-brief frontend:
- fast to scaffold
- strict about ownership
- easy to evolve
- easier to rehost later if Next.js becomes justified by the brief

## Consequences

- some host concerns may be replaced later if the app moves to Next.js
- most business and UI logic should remain portable if boundaries are respected
