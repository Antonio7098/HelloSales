# Frontend Contract

## Purpose
This contract defines the structural and architectural rules for frontend code in this project.

It governs:
- frontend directory structure
- ownership boundaries between app, pages, features, entities, workflows, shared, and design system
- dependency direction
- state placement strategy
- API boundary handling
- testing and extension discipline

It does not replace the general contracts in `ops/operational-contract/`.
Use those contracts alongside this document for testing, error handling, observability, and broader architectural review.

## Scope
This contract applies when a change:
- creates or edits `frontend/`
- introduces a new frontend route, feature, entity, workflow, or shared utility
- changes frontend state management patterns
- changes frontend API access patterns
- changes frontend design-system boundaries
- adds reusable frontend scaffolding or conventions

## How To Use This Contract
Use this contract in three ways:
- during reasoning, map the applicable requirement IDs to the planned frontend change
- during implementation, place code in the correct ownership boundary and preserve allowed dependencies
- during review, verify the change against the evidence guidance and rejection criteria

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| FE-STRUCT-001 | Frontend structure must follow explicit ownership layers | all frontend additions and edits | High |
| FE-BOUNDARY-001 | Dependency direction must remain constrained | cross-folder imports and architecture changes | Blocker |
| FE-APP-001 | App layer must only compose global runtime concerns | `src/app/` | High |
| FE-PAGE-001 | Pages must stay route-level and thin | `src/pages/` | High |
| FE-FEATURE-001 | Features must own business capabilities vertically | `src/features/` | High |
| FE-ENTITY-001 | Entities must model reusable business objects, not global feature logic | `src/entities/` | Medium |
| FE-WORKFLOW-001 | Cross-feature user journeys must live in workflows | `src/workflows/` | Medium |
| FE-SHARED-001 | Shared code must remain domain-neutral and difficult to expand casually | `src/shared/` | High |
| FE-DS-001 | Design system must stay separate from business behavior | `src/design-system/` | High |
| FE-STATE-001 | State must be placed by responsibility, not convenience | all client state decisions | Blocker |
| FE-API-001 | API access must be explicit, typed, and feature-owned | API calls, DTOs, query hooks, mappers | High |
| FE-TEST-001 | Frontend logic must be testable through stable seams | components, hooks, models, workflows | High |
| FE-EXT-001 | New frontend capabilities must be scaffoldable and consistent | new features and routes | Medium |

## Target Structure

The frontend should converge on this structure:

```text
frontend/
├─ public/
├─ src/
│  ├─ app/
│  ├─ pages/
│  ├─ features/
│  ├─ entities/
│  ├─ workflows/
│  ├─ shared/
│  ├─ design-system/
│  ├─ styles/
│  ├─ test/
│  ├─ main.tsx
│  └─ vite-env.d.ts
├─ docs/
└─ package.json
```

The structure is not cosmetic.
Each top-level frontend folder exists to enforce ownership and reduce architectural drift.

## Core Principles

1. Frontend code is organized around business capability ownership, not generic file-type buckets.
2. Composition happens at the edges. Business behavior lives in features and workflows.
3. Shared code is a narrow exception, not the default destination.
4. Route files assemble behavior. They do not become the behavior.
5. API transport models and UI-facing domain models must remain intentionally separated.
6. State location must reflect responsibility: server, route, local UI, and only rarely global client state.
7. The design system is infrastructure for UI consistency, not a hiding place for product logic.

## Requirements

### FE-STRUCT-001: Frontend Structure Must Follow Explicit Ownership Layers

**Rule**
Frontend code must be placed in an explicit ownership layer rather than in broad, top-level dumping grounds.

**Required**
- use `app/` for application bootstrap and top-level composition
- use `pages/` for route-level assembly
- use `features/` for bounded business capabilities
- use `entities/` for reusable business-object representations shared across features
- use `workflows/` for cross-feature user journeys and flows
- use `shared/` for domain-neutral helpers and infrastructure only
- use `design-system/` for visual system primitives and patterns

**Forbidden**
- top-level `src/components/` as a catch-all for product UI
- top-level `src/hooks/` as a catch-all for unrelated logic
- top-level `src/services/` that mixes transport, domain, and view concerns
- top-level `src/contexts/` as the default home for state

**Evidence**
- new code lands in one of the intended ownership layers
- similar frontend capabilities follow the same placement logic

### FE-BOUNDARY-001: Dependency Direction Must Remain Constrained

**Rule**
Dependency direction must move from composition layers toward narrower ownership layers without backflow into higher-level product code.

**Required**
- `app -> pages -> features -> entities -> shared`
- `pages -> workflows -> features -> entities -> shared`
- `design-system -> shared` is allowed when the dependency is domain-neutral
- `features` may depend on `entities`, `shared`, and `design-system`
- `workflows` may depend on `features`, `entities`, `shared`, and `design-system`

**Forbidden**
- `shared -> features`
- `shared -> pages`
- `shared -> workflows`
- `entities -> features`
- `design-system -> features`
- one feature importing private internals from another feature

**Evidence**
- imports follow the permitted direction
- cross-feature use goes through public exports such as `index.ts`

### FE-APP-001: App Layer Must Only Compose Global Runtime Concerns

**Rule**
`src/app/` owns application-wide composition only.

**Required**
- keep router setup, providers, bootstrap, global boundaries, and app-wide runtime configuration in `app/`
- keep app-level auth shell, query-client wiring, and global error boundaries in `app/`

**Forbidden**
- feature-specific business logic in `app/`
- route-specific view logic in `app/`
- direct API endpoint implementations in `app/` beyond generic client wiring

**Evidence**
- files in `app/` read as composition or bootstrap code
- business rules are delegated into features, entities, or workflows

### FE-PAGE-001: Pages Must Stay Route-Level And Thin

**Rule**
`src/pages/` must remain route-level assembly, not become a hidden business layer.

**Required**
- use pages to compose route-specific layout, loaders, guards, and feature sections
- keep page files focused on route concerns, URL state, and orchestration

**Forbidden**
- placing reusable business logic directly in page components
- burying data mapping and business rules inside page files
- using pages as feature catch-alls

**Evidence**
- pages primarily compose exported feature or workflow components
- page files remain smaller and thinner than the business logic they assemble

### FE-FEATURE-001: Features Must Own Business Capabilities Vertically

**Rule**
Each business capability must own its own UI, hooks, API access, model transforms, and tests within a single feature boundary.

**Required**
- organize each feature as a vertical slice
- keep feature-local components, hooks, API calls, model helpers, and tests together
- expose a narrow public API for each feature through `index.ts`

**Recommended internal shape**

```text
features/<feature>/
├─ api/
├─ components/
├─ hooks/
├─ model/
├─ routes/
├─ utils/
├─ __tests__/
└─ index.ts
```

**Forbidden**
- scattering one feature's logic across unrelated top-level folders
- reaching into another feature's internal files when a public export should exist
- moving business logic into `shared/` just because two features currently use it

**Evidence**
- a feature can be understood mostly from its own directory
- the feature root export stays small and intentional

### FE-ENTITY-001: Entities Must Model Reusable Business Objects, Not Global Feature Logic

**Rule**
`src/entities/` may represent reusable business objects shared by multiple features, but it must not become a second feature layer.

**Required**
- keep entity types, mappers, small reusable view helpers, and object-specific utilities in entities when shared across features
- keep entities focused on business objects such as accounts, contacts, deals, sessions, or users

**Forbidden**
- placing whole user journeys in entities
- centralizing feature orchestration in entities
- letting entities absorb unrelated reusable code that belongs in `shared/`

**Evidence**
- entity code is object-centric and reusable across multiple features
- feature-specific orchestration remains outside entities

### FE-WORKFLOW-001: Cross-Feature User Journeys Must Live In Workflows

**Rule**
Multi-step flows that coordinate multiple features must live in `src/workflows/`.

**Required**
- place cross-feature journeys, guided flows, and user progressions in workflows
- let workflows compose feature-level capabilities rather than duplicating them

**Forbidden**
- hiding cross-feature orchestration in pages
- embedding cross-feature process logic into a single feature that does not own the full flow

**Evidence**
- multi-step flows have an explicit ownership location
- workflow code reads as orchestration across features

### FE-SHARED-001: Shared Code Must Remain Domain-Neutral And Difficult To Expand Casually

**Rule**
`src/shared/` is reserved for generic, domain-neutral code and must not become the default destination for reusable product logic.

**Required**
- use `shared/` for transport clients, config, typed primitives, general helpers, generic hooks, constants, and utilities with no product-domain knowledge
- keep shared APIs boring, stable, and reusable across many parts of the app

**Forbidden**
- putting deal, lead, pipeline, or other product-domain logic in `shared/`
- moving code into `shared/` after only one or two uses without proving domain neutrality
- introducing feature-specific UI components into `shared/ui/`

**Evidence**
- shared code has no dependency on product-specific feature folders
- domain language is absent or minimal in shared modules

### FE-DS-001: Design System Must Stay Separate From Business Behavior

**Rule**
`src/design-system/` owns the visual system and reusable UI building blocks, not business-specific components.

**Required**
- use `tokens/` for foundational design values
- use `primitives/` for low-level reusable UI components
- use `patterns/` for repeated UI compositions that stay domain-neutral

**Forbidden**
- feature-specific product widgets in the design system
- business rules embedded in primitives or patterns
- coupling the design system to a specific product capability

**Evidence**
- design-system components are reusable across multiple product areas
- business-specific widgets remain in feature folders

### FE-STATE-001: State Must Be Placed By Responsibility, Not Convenience

**Rule**
Frontend state must be placed according to its responsibility boundary.

**Required**
- keep server state in explicit data-fetching and caching layers
- keep URL-relevant state in route state where practical
- keep ephemeral UI state local to the component or nearest owner
- introduce global client state only when the state is both cross-cutting and not server-owned

**Forbidden**
- using a global store for server data by default
- placing route state in hidden component state when it should be shareable or navigable
- introducing app-wide context or stores for local-only concerns

**Evidence**
- each major stateful concern has a clear reason for its location
- global state surface stays small and intentionally justified

### FE-API-001: API Access Must Be Explicit, Typed, And Feature-Owned

**Rule**
Frontend API access must be centralized at the transport edge and owned by the feature that uses it.

**Required**
- keep the generic HTTP client and transport infrastructure in `shared/api/` or equivalent
- keep feature endpoints, DTOs, query hooks, and transport-specific logic in the consuming feature
- map transport DTOs to UI-facing models before broad UI consumption
- keep request and response validation explicit where the boundary matters

**Forbidden**
- raw `fetch` calls scattered across arbitrary components
- passing raw backend payloads deep into feature UI without mapping or normalization where needed
- centralizing all product API logic in one global `services/` folder

**Evidence**
- API access is discoverable from the owning feature
- DTOs and UI models are intentionally separated

### FE-TEST-001: Frontend Logic Must Be Testable Through Stable Seams

**Rule**
Frontend logic must remain testable through public, stable seams without private patching.

**Required**
- keep pure transformations and rules in testable functions
- keep hooks testable with controllable collaborators
- keep feature and workflow behavior testable through public exports
- centralize shared test harness setup in `src/test/`

**Forbidden**
- tests that rely on private component internals to replace collaborators
- burying important decision logic directly in JSX trees where it cannot be isolated

**Evidence**
- tests can target pure functions, hooks, and exported components through stable seams
- test setup remains reusable and explicit

### FE-EXT-001: New Frontend Capabilities Must Be Scaffoldable And Consistent

**Rule**
New routes, features, and workflows must follow a repeatable shape so the codebase remains easy to extend.

**Required**
- keep folder naming, public exports, and internal structure consistent across capabilities
- prefer generating or scaffolding repeatable feature structure where practical
- document conventions in `frontend/docs/` or equivalent project documentation

**Forbidden**
- inventing a new structural pattern for each feature without a clear architectural need
- allowing capability-specific one-off placement rules to become the norm

**Evidence**
- a new frontend contributor can infer placement from existing examples
- similar frontend capabilities look structurally similar

## Review Rejection Criteria

Reject a frontend change if it:
- introduces a new top-level dumping ground such as `src/components/`, `src/hooks/`, or `src/services/` for product logic
- allows dependency flow from `shared/` or `design-system/` into product features
- puts business logic in `app/` or turns `pages/` into a hidden service layer
- uses global state for convenience when local, route, or server state would be correct
- scatters API calls through arbitrary components instead of feature-owned boundaries
- moves product-domain logic into `shared/` without proving domain neutrality
- places business-specific widgets inside the design system
- adds a new feature with no clear public boundary or no consistent internal structure

## Expected Companion Documentation

Frontend work should maintain or introduce:
- `frontend/docs/frontend-architecture.md`
- `frontend/docs/conventions.md`
- `frontend/docs/decision-records/`

These documents should explain:
- ownership rules and dependency direction
- state management strategy
- API boundary strategy
- design-system usage rules
- scaffolding and extension conventions
