# Pre-Brief Scope Contract

## Purpose
This contract defines what is safe to build before the product brief is known.

It governs:
- what scaffolding may be built now
- what product commitments must be deferred
- what assumptions are prohibited before the brief
- how generic the foundation must remain

## Scope
This contract applies when the product brief is incomplete, unknown, or not yet stable.

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | scaffold-stage work | Low |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | domain logic and product surfaces | High |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | infrastructure and plumbing | Medium |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | transport and public surfaces | Medium |

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

## Review Rejection Criteria
Reject a change if it:
- introduces product-specific domain commitments without brief support
- creates broad public APIs based on guessed requirements
- commits the persistence model to speculative product entities
- adds product-specific workflows or prompts before the brief exists
