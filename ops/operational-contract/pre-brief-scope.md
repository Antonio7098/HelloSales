# Pre-Brief Scope Contract

## Purpose
This contract defines what is safe to build before the product brief is known.

It governs:
- what scaffolding may be built now
- what product commitments must be deferred
- what assumptions are prohibited before the brief
- how generic the foundation must remain
- both backend and frontend pre-brief boundaries

## Scope
This contract applies when the product brief is incomplete, unknown, or not yet stable.

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | scaffold-stage work | Low |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | domain logic and product surfaces | High |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | infrastructure and plumbing | Medium |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | transport and public surfaces | Medium |
| PRE-SCOPE-005 | Frontend foundation work may proceed before the brief | frontend scaffold-stage work | Low |
| PRE-SCOPE-006 | Frontend product surfaces must remain generic before the brief | frontend domain flows and UI commitments | High |

## Requirements

### PRE-SCOPE-001: Foundation Work May Proceed Before The Brief

**Rule**
Generic foundation work may be built before the brief when it does not commit the project to product-specific behavior.

**Safe to build now**
- package layout
- app factory and composition package
- config and settings loading
- async DB engine and session factory
- migration wiring
- task runner
- workflow runtime wrapper
- logging, tracing, and middleware
- error model and handlers
- health and diagnostics surfaces
- one sample module shell with ports and bootstrap
- test harness and smoke harness

This includes frontend foundation work when it remains generic and non-committal.

### PRE-SCOPE-002: Product-Specific Commitments Must Wait For The Brief

**Rule**
Product-specific commitments must wait until the brief supplies the necessary constraints.

**Must wait for the brief**
- real bounded contexts
- real product database schema beyond operational core
- product-specific workflows
- prompt structures and domain personas
- auth and tenancy details unless already known
- broad public API surfaces beyond internal diagnostics and health

**Forbidden**
- inventing domain concepts without strong prior constraints
- overfitting the architecture to guessed product behavior

### PRE-SCOPE-003: Operational Scaffolding Should Be Favored Over Product Assumptions

**Rule**
Before the brief, prefer infrastructure, plumbing, seams, and observability over speculative business behavior.

**Required**
- bias toward reusable runtime scaffolding
- make the system easy to extend once the brief arrives
- preserve replaceability of providers, orchestration, and adapters

**Evidence**
- pre-brief changes primarily strengthen scaffolding, seams, and runtime visibility

### PRE-SCOPE-004: Public APIs Must Remain Intentionally Narrow Before The Brief

**Rule**
Before the brief, public transport surfaces should remain narrow and mostly operational.

**Required**
- keep public endpoints minimal and scaffold-oriented
- prefer internal diagnostics and operational APIs over speculative product endpoints

**Evidence**
- pre-brief transport surfaces are narrow and justified by scaffolding needs

### PRE-SCOPE-005: Frontend Foundation Work May Proceed Before The Brief

**Rule**
Generic frontend foundation work may be built before the brief when it creates extension paths without committing the project to speculative product behavior.

**Safe to build now**
- frontend package and source layout
- Vite, TypeScript, and test tooling setup
- frontend path aliases and import-boundary enforcement
- app bootstrap, provider wiring, and router shell
- route shell and page composition pattern
- design-system foundations such as tokens, primitives, and domain-neutral patterns
- generic app chrome shells such as sidebar, header, panel, split-view, and content frame without product assumptions
- generic form infrastructure such as field wrappers, validation adapters, and submission-state handling
- generic data display infrastructure such as table shell, empty states, loading states, error states, and filter bar patterns
- frontend error boundary, not-found shell, and app-level loading boundary
- generic API client, request helpers, response parsing, and typed transport seams
- frontend test harness, render helpers, builders, mocks, and fixture strategy
- feature scaffolding templates and generation scripts
- frontend architecture docs, conventions, and decision-record templates
- accessibility, theming, responsiveness, and motion foundations

**Safe placeholder work with explicit limits**
- one or two sample features that demonstrate structure only
- one generic entity example for shape and typing only
- one generic workflow example for orchestration shape only

These placeholders must be obviously scaffold-grade and easy to replace.

### PRE-SCOPE-006: Frontend Product Surfaces Must Remain Generic Before The Brief

**Rule**
Before the brief, frontend work must avoid locking the project into guessed product capabilities, guessed information architecture, or guessed interaction models.

**Must wait for the brief**
- real feature taxonomy beyond generic examples
- real navigation model and final information architecture
- product-specific workflows and multi-step journeys
- product-specific dashboard composition
- final forms, filters, and field semantics tied to guessed business objects
- product-specific data models, labels, and business terminology
- role- or persona-specific UI commitments unless already known
- speculative onboarding, billing, CRM, analytics, or assistant experiences
- permanent design language choices tied to an invented brand or audience

**Forbidden**
- inventing product entities and screens as if they are settled requirements
- creating many speculative features to “fill out” the app
- hard-coding guessed assumptions about users, permissions, or business process
- baking speculative workflow ordering into routing or global state
- building domain-specific components in the design system before the brief exists
- treating placeholder sample features as production feature commitments

**Required**
- label placeholder capabilities clearly as scaffolding
- keep names generic where domain certainty does not yet exist
- optimize for replacement, deletion, and extension rather than completeness
- prefer structural examples over broad speculative UI coverage

**Evidence**
- pre-brief frontend work mostly improves architecture, tooling, and extension seams
- any sample screens or features are visibly generic and non-binding
- the frontend remains easy to reshape once the product brief arrives

## Review Rejection Criteria
Reject a change if it:
- introduces product-specific domain commitments without brief support
- creates broad public APIs based on guessed requirements
- commits the persistence model to speculative product entities
- adds product-specific workflows or prompts before the brief exists
- creates speculative frontend features or navigation as if they are settled product requirements
- bakes guessed domain language, user roles, or workflow order into the frontend foundation
- expands the design system with business-specific components before product constraints are known
