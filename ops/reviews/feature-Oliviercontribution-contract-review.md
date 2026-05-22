# Contract Audit Report: `feature/Oliviercontribution`

> **Branch:** `feature/Oliviercontribution`
> **Diff:** 167 files changed, ~10,500 additions, ~6,500 deletions
> **Date:** 2026-05-20
> **Scope:** Full contract audit against all `ops/operational-contract/` contracts

## TL;DR

- **Verdict: REJECT** — 2 of 7 contracts FAIL, 2 N/A, 3 PASS overall
- **Architecture violations resolved** — all 4 issues fixed: lazy-loading registry, Alembic metadata wrapper, SheetPushPort protocol, re-exported permissions
- **Error handling & observability contracts now pass** — structured salesbook errors, bounded sheets retries, owned background execution, correlation propagation, and diagnostics wiring are all in place
- **Test coverage improved but insufficient** — backend coverage now includes domain/value object tests, service-layer unit tests, registry tests, retry/failure-path tests, HTTP integration, and DB-backed persistence coverage, and frontend coverage now exists for the extracted hooks/model/API client, but overall scope coverage is still not exhaustive for a change of this size
- **Frontend still partially out of contract** — all structural/placement/thickness violations closed; remaining gap is test breadth and one Medium sub-page assembly item on OnboardingPage

---

## Change Summary

This branch introduces a large new `modules/salesbook/` backend module (onboarding, pipeline, engagement, team management, moderation), corresponding Alembic migrations (8 new DB tables), 25+ HTTP routes at `/salesbook/`, a complete frontend marketing/presence funnel (landing page, signup page, onboarding wizard), frontend entity types and API client, and restructuring of `product-ops/` into `ops/`. The branch was authored by Olivier with 19 commits.

---

## Contract Conformance Matrix

| Contract | Applicable Requirements | Status | Key Findings |
|---|---|---|---|
| **architecture.md** | ARCH-CORE-001/002, ARCH-LAYER-001/002, ARCH-ENTRY-001, ARCH-MODULE-001, ARCH-COMP-001, ARCH-SHARED-001 | **PASS** | All 4 violations resolved: lazy-loading registry, Alembic metadata wrapper, SheetPushPort protocol, re-exported permissions |
| **errors.md** | ERR-SHAPE-001, ERR-CODE-001, ERR-RETRY-001, ERR-PROVIDER-001 | **PASS** | Structured salesbook errors exist, sheets sync now retries through a bounded policy, and retry exhaustion is surfaced with stable codes |
| **frontend.md** | FE-STRUCT-001, FE-BOUNDARY-001, FE-APP-001, FE-PAGE-001, FE-FEATURE-001, FE-ENTITY-001, FE-WORKFLOW-001, FE-SHARED-001, FE-DS-001, FE-STATE-001, FE-API-001, FE-TEST-001 | **FAIL** | All structural/placement/page-thickness violations closed; remaining gap is overall test breadth and one Medium sub-page assembly item on OnboardingPage |
| **llm.md** | LLM-BOUNDARY-001 through LLM-OBS-001 | **N/A** | No LLM/agent/worker runtime code touched |
| **observability.md** | OBS-CORE-001, OBS-CORR-001, OBS-DIAG-001, OBS-BG-001, OBS-ALERT-001 | **PASS** | Salesbook now emits structured signals with stable codes, preserves correlation, exposes diagnostics, and uses owned background execution |
| **testing.md** | TEST-SEAM-001, TEST-UNIT-001, TEST-INT-001, TEST-SMOKE-001, TEST-SMOKE-002, TEST-FAIL-001, TEST-DET-001 | **FAIL** | Coverage now spans backend domain/registry/service/persistence plus frontend hooks/model/API seams, but breadth is still partial relative to the overall branch size |
| **workflows.md** | WF-SCOPE-001, WF-BOUNDARY-001, WF-STATE-001, WF-RETRY-001 | **N/A** | No workflows added (empty `workflows/__init__.py` is scaffold artifact) |

---

## Detailed Findings

### Architecture — PASS

All 4 violations have been resolved:

| Severity | Location | Issue | Fix Applied |
|---|---|---|---|
| **High** | `modules/salesbook/domain/onboarding_registry.py` | JSON file loaded at module import time — I/O side effect in pure domain layer | Moved to lazy `_ensure_loaded()` pattern with `lru_cache`; module import is now side-effect free |
| **High** | `platform/db/migrations.py` | Star-import from module infra at module load time | Replaced with `_MetadataWrapper` lazy proxy that registers salesbook models on first metadata access |
| **Medium** | `modules/salesbook/use_cases/salesbook_service.py` | Constructor accepts concrete `SalesbookSheetsProvider` type | Defined `SheetPushPort` protocol in `use_cases/ports.py`; constructor now accepts `SheetPushPort \| None` |
| **Low** | `entrypoints/http/routes/salesbook.py` | Permissions imported from internal submodule | All permissions re-exported through `modules/salesbook/__init__.py`; routes updated to import from module root |

### Error Handling — PASS

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **Resolved** | `modules/salesbook/domain/exceptions.py`, `infra/repository.py`, `infra/memory.py` | Salesbook not-found paths now raise structured `AppError`-based exceptions with stable codes such as `salesbook.deal.not_found` and `salesbook.comment.not_found` | This closes the earlier ERR-CODE-001 / ERR-SHAPE-001 / ERR-TRANS-001 gap around raw `KeyError` and unstructured not-found handling | Preserve the same structured pattern for future failure classes |
| **Resolved** | `modules/salesbook/use_cases/salesbook_service.py`, `platform/composition/app_container.py` | `_maybe_push()` now routes sheets sync through `BackgroundTaskRunner` with task identity and terminal failure recording instead of swallowing failures | This closes the earlier ERR-CORE-001 / ERR-BG-001 failure-disappearance problem for sheets sync | Keep background work owned by the shared task runner |
| **Resolved** | `modules/salesbook/use_cases/salesbook_service.py` | Sheets sync now retries through an explicit bounded policy with stable retry and retry-exhaustion codes | This satisfies ERR-RETRY-001 and ERR-PROVIDER-001 for the salesbook sheets path by making retry behavior explicit and terminal exhaustion inspectable | Reuse the same retry pattern for future retryable provider paths |
| **Resolved** | `backend/tests/unit/test_salesbook_error_handling.py` | Failure-path tests now cover structured not-found errors, retry exhaustion, and recovery before retry budget exhaustion | This provides direct verification evidence for the patched error-handling paths | Extend coverage as more failure paths are introduced |

### Frontend — FAIL

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **Resolved** | `frontend-draft/src/features/salesbook/` | Salesbook now has a vertical feature slice with `api/`, `components/`, `hooks/`, `model/`, and `index.ts` | This closes the original FE-FEATURE-001 structural scatter problem | Keep future salesbook UI logic inside this slice |
| **Resolved** | `frontend-draft/src/features/salesbook/api/salesbook-api.ts` | Salesbook API client is now feature-owned instead of living in `shared/api/` | This closes the original FE-SHARED-001 / FE-API-001 placement issue | Keep domain API clients feature-local |
| **Resolved** | `frontend-draft/src/features/salesbook/OnboardingLayout.tsx` | Onboarding-specific layout is no longer in `shared/` | This closes the original FE-SHARED-001 layout-boundary issue | Keep branded/product-specific layouts feature-local |
| **Resolved** | `frontend-draft/src/pages/onboarding/OnboardingPage.tsx`, `frontend-draft/src/features/salesbook/hooks/useOnboardingFlow.ts`, `frontend-draft/src/features/salesbook/components/*` | The onboarding page now delegates data loading, autosave, redirects, and recap/progress UI to the feature layer instead of owning that business logic inline | This materially improves FE-PAGE-001 conformance by reducing the page to route/paging assembly | Continue extracting any future onboarding-specific UI into `features/salesbook/components/` |
| **Resolved** | `frontend-draft/src/pages/signup/SignupPage.tsx`, `frontend-draft/src/features/salesbook/components/{HeroSection,CompetitiveGapTable,ManifestoSection,ChallengeSolutionTable,SignupForm}.tsx` | Each funnel section is now a feature-owned component. The page is 5 lines — pure route-level assembly. | This closes the original FE-PAGE-001 violation on the signup funnel | Keep future marketing/funnel sections as feature components |
| **Medium** | `frontend-draft/src/pages/onboarding/OnboardingPage.tsx` | The page is much thinner now, but it still owns local sub-page navigation/presentation assembly for the wizard route | This is acceptable progress, but the contract trend favors even thinner route files over time | If the wizard grows further, extract paging assembly into a feature component |

### LLM Runtime — N/A

No LLM-backed runtime code was added or modified. The salesbook module is a pure product-domain CRUD module. `smoke_generic_agent_provider.py` is a pass-through entrypoint to pre-existing smoke harnesses. No requirements triggered.

### Observability — PASS

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **Resolved** | `entrypoints/http/routes/salesbook.py`, `modules/salesbook/use_cases/salesbook_service.py` | Request and trace context are now threaded from HTTP routes into salesbook service calls | This satisfies OBS-CORR-001 for the patched salesbook paths | Preserve this pattern for future routes |
| **Resolved** | `modules/salesbook/use_cases/salesbook_service.py` | Sheets sync background work now has task identity, retry visibility, terminal state capture, and structured failure recording through `BackgroundTaskRunner` | This satisfies OBS-BG-001 for that path | Keep salesbook background execution on the shared runner |
| **Resolved** | `modules/salesbook/use_cases/salesbook_service.py`, `shared/errors.py` | Salesbook now emits structured logs and operational events with stable codes such as `salesbook.sheets.retry_scheduled`, `salesbook.sheets.retry_exhausted`, and `salesbook.sheets.push_failed` | This satisfies OBS-CORE-001 and OBS-ALERT-001 for the new salesbook operational paths | Keep stable code usage consistent as new failure paths are added |
| **Resolved** | `modules/salesbook/use_cases/ports.py`, `modules/salesbook/bootstrap.py`, `modules/system/use_cases/system_service.py`, `modules/system/use_cases/views.py`, `platform/composition/app_container.py` | Salesbook diagnostics are now exposed through the canonical `/api/system/diagnostics` surface | This satisfies OBS-DIAG-001 by making salesbook operational state visible through the system diagnostics contract | Extend the diagnostics payload as salesbook runtime state grows |

### Testing — FAIL

| Severity | Location | Issue | Why It Matters | Suggested Fix |
|---|---|---|---|---|
| **High** | `modules/salesbook/domain/value_objects.py` | Tests cover enum values, `CLOSED_STAGES`, phase question counts | Basic unit coverage exists for value objects | Extend to edge cases and boundary conditions |
| **High** | `modules/salesbook/domain/entities.py` | Tests cover frozen dataclass behavior, enum status fields, entity field defaults, permissions | Basic entity construction and immutability tests exist | Extend to domain logic (state transitions, validation) |
| **High** | `modules/salesbook/domain/exceptions.py` | Tests cover all 6 exception subclasses, base class inheritance | Exception hierarchy is tested | Add error code, category, status_code assertions on each |
| **High** | `modules/salesbook/use_cases/salesbook_service.py` | Service tests now cover contact upsert, onboarding progress recomputation, batch response handling, pipeline stage updates, exhaustive-view aggregation, and remove/unpin flows | This materially improves TEST-UNIT-001 coverage over core business seams | Extend to additional edge cases and permission-sensitive behavior |
| **High** | `modules/salesbook/domain/onboarding_registry.py` | Registry helper tests now cover loading, phase filtering, section filtering, and total counts | This verifies the lazy-load registry seam and its contract-facing helpers | Keep totals/shape assertions in sync with generator output |
| **Medium** | `entrypoints/http/routes/salesbook.py` | HTTP integration tests now cover route wiring for onboarding registry and client contact round-trips with explicit salesbook permissions | This gives a small integration slice proving route wiring and auth for key endpoints | Extend to more endpoints and negative transport cases |
| **Resolved** | `modules/salesbook/infra/repository.py` | DB-backed integration tests now exercise SQLAlchemy persistence for contacts, onboarding, pipeline, engagement, team membership, comments, pins, and structured not-found errors | This materially closes the TEST-INT-001 gap for the salesbook persistence layer | Extend to more cross-module and migration-evolution scenarios as the module grows |
| **High** | `modules/salesbook/use_cases/salesbook_service.py` | Failure-path unit tests cover missing deal and missing comment | Partial failure-path coverage exists | Add tests for invalid phase transitions, permission errors, provider retry/exhaustion |
| **Resolved** | `modules/salesbook/use_cases/salesbook_service.py` | Background task failure capture and retry/exhaustion behavior are tested via `BackgroundTaskRunner` | Sheets sync failure recording and bounded retry behavior now have direct coverage | Preserve this pattern for future background providers |
| **Resolved** | `frontend-draft/src/features/salesbook/` | Vitest coverage now exists for `useSignupForm`, `useOnboardingFlow`, `groupBySection` / `pctNumber`, and the feature API client transport behavior | This materially closes FE-TEST-001 for the extracted salesbook seams | Extend coverage to page-level flows and more negative UI cases as the feature evolves |

**Positive:** The module architecture is testable — constructor injection via `Protocol` ports and in-memory repository doubles in `memory.py` make it straightforward to extend coverage.

### Workflows — N/A

The `workflows/__init__.py` is an empty scaffold artifact. No workflow code exists. Not triggered.

---

## Remediation Priority

### Must Fix Before Merge (Blockers)

1. **Test coverage is still not broad enough for the branch size** — backend domain/service/registry/error-handling routes/persistence and frontend hooks/model/API seams now have coverage, but route/page breadth and many edge-case paths remain untested

### Should Fix (High)

None remaining — all structural violations, API/layout placement, thick pages, and module boundary issues have been resolved.

### Nice to Fix (Medium)

1. **OnboardingPage wizard assembly** — the page is substantially thinner but still owns local sub-page navigation; could be extracted to a feature component if the wizard grows
2. **Diagnostics surface** — salesbook state is now exposed through canonical diagnostics, but the payload could be extended as runtime state grows

---

## Technical Debt

| Item | Type | Why | Impact | Follow-up |
|---|---|---|---|---|
| ~~Domain I/O at import time~~ | ~~Architecture~~ | ~~Module-load filesystem read~~ | ~~Breaks domain purity, testability~~ | ~~RESOLVED — lazy-load registry data~~ |
| ~~`platform/db/migrations.py` star import~~ | ~~Architecture~~ | ~~Upward dependency~~ | ~~Platform tied to module internals~~ | ~~RESOLVED — metadata wrapper proxy~~ |
| ~~Concrete infra coupling (`SalesbookSheetsProvider`)~~ | ~~Architecture~~ | ~~Use cases depend on concrete infra~~ | ~~Violates ARCH-LAYER-002~~ | ~~RESOLVED — `SheetPushPort` protocol~~ |
| ~~Module public API~~ | ~~Architecture~~ | ~~Permissions not re-exported~~ | ~~Routes import from internal submodule~~ | ~~RESOLVED — re-export through `__init__.py`~~ |
| Thin salesbook test coverage | Testing | Coverage now exercises core backend service paths, registry helpers, retry/failure handling, HTTP routes, DB-backed persistence, and frontend feature seams, but route/page breadth and edge cases remain limited | Regression risk remains on less-traveled paths and future feature growth | Expand page-level, transport-negative, and end-to-end scenario coverage |
| ~~Large salesbook page-level composition surfaces~~ | ~~Frontend~~ | ~~Both pages now thin route-level assembly; signup funnel split into 5 feature components + 1 extracted shared utility~~ | ~~Resolved — no FE-PAGE-001 remaining~~ | ~~RESOLVED — keep future sections as feature components~~ |

---

## Questions For The Author

1. Was the product brief intentionally deferred, or does a brief exist that was not referenced?
2. `sheets_provider.py` is imported in `bootstrap.py` but not present in this diff — does it exist on the target branch?
3. The frontend `cn.ts` utility was deleted — is this intentional, and were all consumers migrated?

---

## Sign-Off

- **Branch:** `feature/Oliviercontribution`
- **Audit date:** 2026-05-20
- **Status:** REJECTED — 2/7 contracts FAIL, 2 N/A, 3 PASS
