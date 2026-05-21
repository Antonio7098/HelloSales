# Contract Audit Report: `feature/Oliviercontribution`

> **Branch:** `feature/Oliviercontribution`
> **Diff:** 167 files changed, ~10,500 additions, ~6,500 deletions
> **Date:** 2026-05-20
> **Scope:** Full contract audit against all `ops/operational-contract/` contracts

## TL;DR

- **Verdict: REJECT** — 5 of 8 contracts FAIL, 2 N/A, 0 PASS overall
- **Pre-brief scope** is the fundamental blocker: this branch builds a complete product bounded context (salesbook module with 8 DB tables, 25+ HTTP endpoints, full frontend funnel) before the product brief exists
- **Error handling & observability** are completely absent — zero structured logging, zero error codes, zero use of the existing `AppError` / `OperationalEvent` infrastructure
- **Zero tests** for approximately 3,000 lines of new backend code and extensive frontend additions
- **Frontend structural violations** — no `features/salesbook/` directory, domain-specific code in `shared/`, thick business logic in pages

---

## Change Summary

This branch introduces a large new `modules/salesbook/` backend module (onboarding, pipeline, engagement, team management, moderation), corresponding Alembic migrations (8 new DB tables), 25+ HTTP routes at `/salesbook/`, a complete frontend marketing/presence funnel (landing page, signup page, onboarding wizard), frontend entity types and API client, and restructuring of `product-ops/` into `ops/`. The branch was authored by Olivier with 19 commits.

---

## Contract Conformance Matrix

| Contract | Applicable Requirements | Status | Key Findings |
|---|---|---|---|
| **architecture.md** | ARCH-CORE-001/002, ARCH-LAYER-001/002, ARCH-ENTRY-001, ARCH-MODULE-001, ARCH-COMP-001, ARCH-SHARED-001 | **FAIL** | Domain I/O side-effect at import time; platform depends on module infra; sheets_provider is concrete type |
| **errors.md** | ERR-CORE-001, ERR-SHAPE-001, ERR-CODE-001, ERR-TRANS-001, ERR-RETRY-001, ERR-STARTUP-001, ERR-HTTP-001, ERR-BG-001, ERR-PROVIDER-001, ERR-DATA-001, ERR-REDACT-001 | **FAIL (Blocker)** | Silent failure swallow (`pass`), fire-and-forget background tasks, raw `KeyError`, zero error codes, zero `AppError` usage |
| **frontend.md** | FE-STRUCT-001, FE-BOUNDARY-001, FE-APP-001, FE-PAGE-001, FE-FEATURE-001, FE-ENTITY-001, FE-WORKFLOW-001, FE-SHARED-001, FE-DS-001, FE-STATE-001, FE-API-001, FE-TEST-001 | **FAIL** | No `features/salesbook/` directory, domain-specific code in `shared/`, thick pages, API client in wrong layer |
| **llm.md** | LLM-BOUNDARY-001 through LLM-OBS-001 | **N/A** | No LLM/agent/worker runtime code touched |
| **observability.md** | OBS-CORE-001, OBS-CORR-001, OBS-HEALTH-001, OBS-DIAG-001, OBS-BG-001, OBS-ALERT-001 | **FAIL** | Zero structured logging, zero correlation propagation, fire-and-forget tasks, no diagnostics exposure |
| **testing.md** | TEST-SEAM-001, TEST-UNIT-001, TEST-INT-001, TEST-SMOKE-001, TEST-SMOKE-002, TEST-FAIL-001, TEST-DET-001 | **FAIL** | Zero tests for ~3,000 lines backend + significant frontend additions |
| **workflows.md** | WF-SCOPE-001, WF-BOUNDARY-001, WF-STATE-001, WF-RETRY-001 | **N/A** | No workflows added (empty `workflows/__init__.py` is scaffold artifact) |
| **pre-brief-scope.md** | PRE-SCOPE-001 through PRE-SCOPE-006 | **FAIL (Blocker)** | Complete product bounded context built before brief; 8 DB tables, 25+ endpoints, full frontend product surfaces |

---

## Detailed Findings

### Architecture — FAIL

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **High** | `modules/salesbook/domain/onboarding_registry.py` | JSON file loaded at module import time (`json.loads(path.read_text())`) — I/O side effect in pure domain layer | Domain layer must remain infrastructure-free per ARCH-LAYER-001 | Move to lazy-loading or inject registry data through service layer |
| **High** | `platform/db/migrations.py` | `from hello_sales_backend.modules.salesbook.infra.persistence import *` — platform code imports from module infra | Platform must stay domain-neutral per ARCH-SHARED-001; creates hard upward dependency | Use Alembic `run_migrations_online()` with metadata registry or move import to neutral location |
| **Medium** | `modules/salesbook/use_cases/salesbook_service.py` | Constructor accepts `sheets_provider: "SalesbookSheetsProvider | None"` — concrete infra type, not abstract port | ARCH-LAYER-002 requires use cases depend on ports, not concrete infra | Define a `SheetPushPort` protocol in `use_cases/ports.py` |
| **Low** | `entrypoints/http/routes/salesbook.py` | Imports permission constants from `modules.salesbook.permissions` instead of through module public API | ARCH-MODULE-001 expects routes to consume module solely through `__init__.py` | Re-export permissions through `modules/salesbook/__init__.py` |

### Error Handling — FAIL (Blocker)

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **Blocker** | `modules/salesbook/use_cases/salesbook_service.py:5339-5346` | `_maybe_push()` catches `RuntimeError` with bare `pass` — silent failure swallow; uses `asyncio.create_task()` fire-and-forget with no ownership/retry | Violates ERR-CORE-001 (no failure may disappear) and ERR-BG-001 (background work must end in inspectable state) | Replace with proper task manager with retry budget, identity, and terminal state reporting |
| **Blocker** | `modules/salesbook/domain/exceptions.py` | 6 exception classes defined but never raised; no stable codes, no `AppError` subclass | Violates ERR-CODE-001 (no machine-usable codes) and ERR-CORE-001; entire error infrastructure unused | Make exceptions extend `AppError` with stable codes |
| **High** | `modules/salesbook/infra/repository.py:4512,4737` | Raises `KeyError(f"deal not found: {deal_id}")` — raw, unstructured exception | Violates ERR-TRANS-001 (error translation must preserve cause) and ERR-DATA-001 (data failures must be loud and distinct); no structured signal for operators | Replace with `app_error(code="data.not_found", ...)` |
| **High** | `entrypoints/http/routes/salesbook.py` | Every handler wraps in `ok_response()` with no `try/except` — all errors fall through to generic `internal.unhandled_exception` | Violates ERR-HTTP-001 (transport adapters must preserve operational signal); existing `error_handlers.py` bypassed entirely | Route handlers should raise `AppError` which is already handled by existing error handlers |
| **High** | `modules/salesbook/use_cases/salesbook_service.py:5339` | Fire-and-forget task `create_task(self._sheets.push(...))` with no retry policy, no cap, no exhaustion behavior | Violates ERR-RETRY-001 (retryable errors must be retried through explicit bounded policy) | Wrap in proper retry policy with attempt budget and terminal exhaustion |

### Frontend — FAIL

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **Critical** | `frontend-draft/src/` | No `features/salesbook/` directory created — salesbook code scattered across `shared/api/`, `shared/ui/`, `pages/` instead of vertical-slice feature | Violates FE-FEATURE-001 (features own business capabilities vertically) | Create `features/salesbook/` with `api/`, `components/`, `hooks/`, `model/`, `index.ts` |
| **High** | `frontend-draft/src/shared/api/salesbook.ts` | 215-line full Salesbook API client in `shared/api/` | Violates FE-SHARED-001 (shared must be domain-neutral) and FE-API-001 (API must be feature-owned) | Move to `features/salesbook/api/salesbook-api.ts` |
| **High** | `frontend-draft/src/pages/signup/SignupPage.tsx` | 433-line page with inline form submission, role routing logic, `getSalesbookApi` orchestration, `localStorage` fallback | Violates FE-PAGE-001 (pages must stay thin route-level assembly) | Extract business logic into `features/salesbook/` |
| **High** | `frontend-draft/src/pages/onboarding/OnboardingPage.tsx` | 340-line page with `groupBySection()`, auto-save, navigation logic, inline child components (`PhaseDot`, `FinalRecap`) | Violates FE-PAGE-001 (pages must stay thin) | Extract reusable logic to feature layer, keep page as route assembly |
| **High** | `frontend-draft/src/shared/ui/layouts/OnboardingLayout.tsx` | Onboarding-specific layout with product branding | Violates FE-SHARED-001 (shared must be domain-neutral) | Move to `features/salesbook/` |
| **Medium** | `frontend-draft/src/shared/api/salesbook.ts:8810-8827` | Imports entity types from `@/entities/salesbook/types` | Violates FE-BOUNDARY-001 (shared must not depend on entities) | When moved to features, this dependency is correct (features -> entities) |

### LLM Runtime — N/A

No LLM-backed runtime code was added or modified. The salesbook module is a pure product-domain CRUD module. `smoke_generic_agent_provider.py` is a pass-through entrypoint to pre-existing smoke harnesses. No requirements triggered.

### Observability — FAIL

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **Blocker** | Entire `modules/salesbook/` | Zero calls to `get_logger`, zero `OperationalEvent` emissions, zero `structlog` usage | Violates OBS-CORE-001 (failures must produce structured operational signals) | Add structured logging at every failure path; emit operational events |
| **Blocker** | `modules/salesbook/use_cases/salesbook_service.py` | Service methods accept no `correlation_id`/`trace_id` — correlation dropped at route→service boundary | Violates OBS-CORR-001 (correlation must survive subsystem boundaries) | Accept correlation context in service methods or use contextvars |
| **Blocker** | `modules/salesbook/use_cases/salesbook_service.py:5339-5346` | Fire-and-forget background tasks with no identity, no status tracking, no failure capture | Violates OBS-BG-001 (background work must have visible terminal state) | Use proper task runner with identity, status transitions, and error capture |
| **High** | `modules/salesbook/domain/exceptions.py` | No stable error codes, no severity/component fields | Violates OBS-ALERT-001 (high-severity signals must be machine-usable for alerting) | Define stable codes and severity on all exception types |
| **Medium** | `platform/composition/app_container.py` | Salesbook module wired for HTTP routing but no diagnostics adapter registered | Violates OBS-DIAG-001 (new operational state not exposed through canonical diagnostics) | Add diagnostics surface for salesbook state |

### Testing — FAIL

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **Blocker** | Whole module | Zero test files added for ~3,000 lines of new backend code | Violates TEST-UNIT-001, TEST-INT-001, TEST-FAIL-001 | Add unit tests for domain logic and use cases; add integration tests for persistence and wiring |
| **Blocker** | `modules/salesbook/` | Alembic migrations (8 tables) with no integration tests | Violates TEST-INT-001 (wiring/persistence changes must have integration coverage) | Add DB-backed integration tests |
| **High** | `modules/salesbook/` | No negative/failure-path tests despite extensive failure-handling logic | Violates TEST-FAIL-001 (failure paths must be tested explicitly) | Add tests for missing entities, invalid transitions, permission errors |
| **Medium** | `frontend-draft/` | No frontend tests for new pages, hooks, or API client | Violates FE-TEST-001 (frontend logic must be testable through stable seams) | Add vitest tests for hooks, API client, and extracted business logic |

**Positive:** The module architecture is testable — constructor injection via `Protocol` ports, in-memory repository doubles exist in `memory.py`. Test seams are in place; just no tests.

### Workflows — N/A

The `workflows/__init__.py` is an empty scaffold artifact. No workflow code exists. Not triggered.

### Pre-Brief Scope — FAIL (Blocker)

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **Blocker** | Entire branch | Complete product bounded context built before the product brief exists | Explicitly forbidden by PRE-SCOPE-002: "real bounded contexts" and "real product database schema beyond operational core" must wait for the brief | Defer product-specific code until brief provides necessary constraints |
| **Blocker** | `entrypoints/http/routes/salesbook.py` | 25+ product-specific endpoints registered at `/salesbook/` | Violates PRE-SCOPE-004: public APIs must remain intentionally narrow before the brief | Keep only internal/diagnostics endpoints; defer product APIs |
| **Blocker** | `frontend-draft/src/pages/` | Landing, Signup, Onboarding pages with full brand, marketing copy, role-based routing | Violates PRE-SCOPE-006: frontend product surfaces must remain generic before the brief | Revert to generic scaffold pages; defer product surfaces |
| **Blocker** | `backend/alembic/versions/0007_*, 0008_*` | 8 product tables for client contacts, pipeline, engagement, team, moderation | Violates PRE-SCOPE-002: product DB schema must wait for the brief | Revert product migrations; keep only operational core tables |
| **High** | `modules/salesbook/domain/value_objects.py` | Product-specific enums: `PipelineStage`, `ActionType`, `ClientStatus`, `RoleLevel` | Violates PRE-SCOPE-002: inventing domain concepts without strong prior constraints | Defer until brief defines domain language |
| **High** | `SALESBOOK_CONTEXT.md` | Explicit product context document describing real product behavior | Demonstrates the work is product-specific, not scaffold-grade | Should not exist pre-brief |

---

## Remediation Priority

### Must Fix Before Merge (Blockers)

1. **Pre-brief scope violation** — the most fundamental issue. Either produce a brief that validates these product commitments, or revert product-specific code to scaffold-only
2. **Silent failure swallowing** — `_maybe_push` fire-and-forget with `pass` must be replaced with proper error handling
3. **Zero tests** — no code of this size should merge without at minimum unit tests for domain logic
4. **Zero observability** — every failure path needs structured logging and error codes

### Should Fix (High)

5. **Domain layer I/O** — `onboarding_registry.py` import-time JSON load violates domain purity
6. **Platform→module dependency** — `migrations.py` star import creates upward dependency
7. **Frontend feature structure** — create `features/salesbook/` and move code out of `shared/`
8. **Thick pages** — extract business logic from SignupPage and OnboardingPage
9. **Concrete infra coupling** — abstract `SalesbookSheetsProvider` behind a port protocol
10. **Correlation propagation** — pass request/trace context through service layer

### Nice to Fix (Medium)

11. **Diagnostics surface** — expose salesbook state through canonical diagnostics
12. **Module public API** — re-export permissions through `__init__.py`
13. **Frontend API client** — move from `shared/api/` to `features/salesbook/api/`

---

## Technical Debt

| Item | Type | Why | Impact | Follow-up |
|---|---|---|---|---|
| `_maybe_push` fire-and-forget | Error handling | Silent failure swallow | Production data loss on webhook failures | Replace with proper task manager |
| No error codes across salesbook | Architecture | No AppError usage | Ops cannot alert on specific failures | Define salesbook error codes |
| `platform/db/migrations.py` star import | Architecture | Upward dependency | Platform tied to module internals | Use Alembic metadata registry |
| Domain I/O at import time | Architecture | Module-load filesystem read | Breaks domain purity, testability | Lazy-load registry data |
| Zero test coverage | Testing | No tests added | Regression risk on every change | Add unit/integration/smoke tests |
| No `features/salesbook/` directory | Frontend | Code scattered | Structural inconsistency, harder to extend | Create feature directory pattern |

---

## Questions For The Author

1. Was the product brief intentionally deferred, or does a brief exist that was not referenced?
2. The `_maybe_push` fire-and-forget pattern appears to be a known limitation — was this tracked as a follow-up somewhere?
3. `sheets_provider.py` is imported in `bootstrap.py` but not present in this diff — does it exist on the target branch?
4. The frontend `cn.ts` utility was deleted — is this intentional, and were all consumers migrated?

---

## Sign-Off

- **Branch:** `feature/Oliviercontribution`
- **Audit date:** 2026-05-20
- **Status:** REJECTED — 5/8 contracts FAIL, 2 N/A, 0 PASS
- **Primary blocker:** Pre-brief scope — complete product bounded context built without a product brief
