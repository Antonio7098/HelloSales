# Cowork Changelog — feature/Oliviercontribution

A log of every Cowork-applied change on this branch. Keeps the May 3rd review to one document.

---

## 2026-05-22 — 7.1 Frontend data-provider abstraction

- **By:** Antonio (/Antonio7098)
- **Change:** Introduced a centralized, swappable data-provider layer for the frontend (`frontend-draft/`). Feature hooks and components now depend on an `AppDataProvider` interface instead of importing concrete API clients directly.

  **Interface** (`src/shared/data/provider.ts`):
  Single `AppDataProvider` interface covering all data access: auth/signup, onboarding, dashboard/company-profile, products, pipeline (deals), engagement log, team, comments, pins, exhaustive salesbook view, and chat sessions/events/approvals.

  **Provider implementations:**
  - `src/shared/data/real-data-provider.ts` — delegates to existing `getSalesbookApi()` and `requestJson()` calls; chat uses `fetch` + `EventSource` directly via the same HTTP transport.
  - `src/shared/data/mock-data-provider.ts` — fully offline, stateful in-memory implementation with realistic seed data for every route; mutations persisted to `localStorage` per profile.

  **Resolver** (`src/shared/data/get-provider.ts`): Single factory selects implementation via `VITE_DATA_PROVIDER=mock|real`. Defaults to `real`.

  **React context** (`src/shared/data/context.tsx`): `AppDataProviderRoot` context + `useAppData()` hook expose the selected provider throughout the component tree. `useCurrentUser` refactored to consume from context instead of directly managing localStorage.

  **Refactored features:**
  - `useSignupForm` → calls `provider.signup()` instead of `getSalesbookApi()` directly
  - `useOnboardingFlow` → calls `provider.getOnboardingRegistry/Progress/Responses/submitOnboardingResponse`
  - `useDashboardData` → calls `provider.getDashboardData()`
  - `useAgentChat` → calls `provider.createChatSession/sendChatMessage/getChatSession/getChatSessionItems/getChatSessionEvents/subscribeToChatSessionEvents/decideChatApproval`

  **Mock provider coverage:** auth (localStorage user), onboarding (registry from `/onboarding-registry.json`, responses persisted, progress computed), dashboard (seed `CompanyProfileResponse`), products (CRUD, seed array), pipeline (seed deals, create/update persisted per profile), engagement log (create/list persisted per profile), team (seed + add/remove per profile), comments (add/list/review per profile), pins (seed + pin/unpin per profile), exhaustive view (aggregates mock data), chat (in-memory sessions, `setInterval`-driven mock SSE events, approval decisions).

  **Auth types moved:** `CurrentUser` and `UserRole` extracted to `src/shared/auth/types.ts` so the provider interface and `useCurrentUser` share the same types without circular dependency.

- **Files added:**
  - `src/shared/data/provider.ts`
  - `src/shared/data/real-data-provider.ts`
  - `src/shared/data/mock-data-provider.ts`
  - `src/shared/data/get-provider.ts`
  - `src/shared/data/context.tsx`
  - `src/shared/auth/types.ts`
- **Files modified:**
  - `src/app/providers/AppProviders.tsx` — wraps with `AppDataProviderRoot`
  - `src/shared/auth/useCurrentUser.ts` — consumes from provider context
  - `src/features/salesbook/hooks/useSignupForm.ts`
  - `src/features/salesbook/hooks/useOnboardingFlow.ts`
  - `src/features/dashboard-data/model/use-dashboard-data.ts`
  - `src/features/chat/model/use-agent-chat.ts`
  - `frontend-draft/.env` — added `VITE_DATA_PROVIDER=mock`
  - `frontend-draft/.env.example` — added `VITE_DATA_PROVIDER` with comments
- **Switch:** Set `VITE_DATA_PROVIDER=mock` in `.env` (or Docker `environment:`) to run fully offline with mock data. `VITE_DATA_PROVIDER=real` (default) hits the backend.
- **Verified:** `npm run build` passes — 114 modules transformed, 324KB JS / 101KB gzipped.

---

## 2026-05-20 — 6.1 Architecture contract fixes

- **By:** Antonio (/Antonio7098)
- **Change:** Resolved all 4 architecture contract violations from the contract audit:
  · **High** — `modules/salesbook/domain/onboarding_registry.py`: Moved JSON file loaded at module import time to lazy `_ensure_loaded()` + `lru_cache` pattern; module import now side-effect free.
  · **High** — `platform/db/migrations.py`: Replaced star-import from module infra with `_MetadataWrapper` lazy proxy that registers salesbook models on first metadata access.
  · **Medium** — `modules/salesbook/use_cases/salesbook_service.py`: Defined `SheetPushPort` protocol in `use_cases/ports.py`; constructor accepts `SheetPushPort | None` instead of concrete `SalesbookSheetsProvider`.
  · **Low** — `modules/salesbook/__init__.py` + `entrypoints/http/routes/salesbook.py`: All permissions re-exported through module root; routes import from module root instead of internal submodule.
- **Anto-file touches:** `platform/db/migrations.py` — star import replaced with lazy metadata proxy
- **Verified:** Architecture contract now PASSes (ARCH-CORE-001/002, ARCH-LAYER-001/002, ARCH-ENTRY-001, ARCH-MODULE-001, ARCH-COMP-001, ARCH-SHARED-001).

## 2026-05-20 — 6.2 Error handling & observability contract fixes

- **By:** Antonio (/Antonio7098)
- **Change:** Resolved error handling and observability contract gaps:
  · **Structured errors:** Salesbook not-found paths now raise `AppError`-based exceptions with stable codes (`salesbook.deal.not_found`, `salesbook.comment.not_found`) in `modules/salesbook/domain/exceptions.py`, `infra/repository.py`, `infra/memory.py`.
  · **Background task ownership:** `_maybe_push()` in `salesbook_service.py` routes sheets sync through `BackgroundTaskRunner` with task identity and terminal failure recording (eliminated swallowed failures).
  · **Bounded retry:** Sheets sync retries through explicit bounded policy with stable retry and retry-exhaustion codes.
  · **Correlation propagation:** Request/trace context threaded from `entrypoints/http/routes/salesbook.py` into salesbook service calls.
  · **Structured signals:** Salesbook emits logs/events with stable codes (`salesbook.sheets.retry_scheduled`, `salesbook.sheets.retry_exhausted`, `salesbook.sheets.push_failed`).
  · **Diagnostics:** Salesbook state exposed through canonical `/api/system/diagnostics` via `modules/salesbook/bootstrap.py`, `modules/salesbook/use_cases/ports.py`, `modules/system/use_cases/system_service.py`, `modules/system/use_cases/views.py`, `platform/composition/app_container.py`.
- **Anto-file touches:** `platform/composition/app_container.py`, `modules/system/use_cases/system_service.py`, `modules/system/use_cases/views.py` — diagnostics wiring
- **Verified:** Error handling (ERR-SHAPE-001, ERR-CODE-001, ERR-RETRY-001, ERR-PROVIDER-001) and observability (OBS-CORE-001, OBS-CORR-001, OBS-DIAG-001, OBS-BG-001, OBS-ALERT-001) contracts now PASS.

## 2026-05-20 — 6.3 Frontend contract fixes

- **By:** Antonio (/Antonio7098)
- **Change:** Closed all structural/placement/thickness FE violations:
  · **FE-FEATURE-001:** Vertical feature slice at `features/salesbook/` with `api/`, `components/`, `hooks/`, `model/`, `index.ts`.
  · **FE-SHARED-001 / FE-API-001:** API client moved to `features/salesbook/api/salesbook-api.ts` (feature-owned instead of `shared/api/`).
  · **FE-SHARED-001:** Onboarding layout moved to `features/salesbook/OnboardingLayout.tsx` (no longer in `shared/`).
  · **FE-PAGE-001 (onboarding):** `pages/onboarding/OnboardingPage.tsx` delegates data loading, autosave, redirects, recap/progress UI to feature layer via `hooks/useOnboardingFlow.ts` and `components/`.
  · **FE-PAGE-001 (signup):** `pages/signup/SignupPage.tsx` reduced to 5-line route assembly; funnel sections (`HeroSection`, `CompetitiveGapTable`, `ManifestoSection`, `ChallengeSolutionTable`, `SignupForm`) are feature-owned components.
  · **Remaining (Medium):** `OnboardingPage.tsx` still owns local wizard sub-page navigation — acceptable, extractable if wizard grows.
- **Verified:** FE-STRUCT-001, FE-BOUNDARY-001, FE-APP-001, FE-PAGE-001, FE-FEATURE-001, FE-ENTITY-001, FE-WORKFLOW-001, FE-SHARED-001, FE-DS-001, FE-STATE-001, FE-API-001 now PASS; overall frontend contract still FAILs due to test breadth.

## 2026-05-20 — 6.4 Testing expansion

- **By:** Antonio (/Antonio7098)
- **Change:** Expanded test coverage across multiple seams to address TEST-UNIT-001, TEST-INT-001, TEST-FAIL-001, and FE-TEST-001:
  · **Domain value objects:** Enum values, CLOSED_STAGES, phase question counts.
  · **Domain entities:** Frozen dataclass behavior, enum status fields, defaults, permissions.
  · **Domain exceptions:** All 6 subclasses, base class inheritance.
  · **Service layer:** Contact upsert, onboarding progress, batch responses, pipeline stage updates, exhaustive-view aggregation, remove/unpin.
  · **Registry helpers:** Loading, phase/section filtering, total counts.
  · **HTTP integration:** Route wiring for onboarding registry and client contact round-trips with explicit permissions.
  · **DB-backed persistence:** SQLAlchemy tests for contacts, onboarding, pipeline, engagement, team membership, comments, pins, structured not-found errors.
  · **Failure paths:** Missing deal, missing comment, retry exhaustion, recovery before retry budget exhaustion.
  · **Background tasks:** Failure capture and retry/exhaustion via `BackgroundTaskRunner`.
  · **Frontend:** Vitest coverage for `useSignupForm`, `useOnboardingFlow`, `groupBySection`/`pctNumber`, feature API client transport.
- **New files:** `backend/tests/unit/test_salesbook_error_handling.py`, various backend test additions, frontend Vitest files under `features/salesbook/`
- **Verified:** Backend coverage spans domain/service/registry/persistence + failure paths. Frontend coverage covers hooks/model/API seams. Testing contract overall still FAILs due to remaining breadth gaps relative to branch size.

## 2026-04-26 — 1.1 Setup
- **By:** Olivier (/Oliviercontribution)
- **Change:** Forked Antonio7098/HelloSales → HelloSalesGreki/HelloSales. Cloned to `~/Desktop/HS/CODE/HS-Code/`. Added `upstream` remote pointing at Anto's repo. Created branch `feature/Oliviercontribution`. Added `SALESBOOK_CONTEXT.md` at repo root describing the salesbook onboarding module scope.
- **Files touched:** `SALESBOOK_CONTEXT.md` (new), `docs/COWORK_CHANGELOG.md` (new).
- **No existing files modified.**

## 2026-04-26 — 2.1 Salesbook module scaffold
- **By:** Olivier (/Oliviercontribution)
- **Change:** Scaffolded `salesbook` bounded-context module via `scripts/scaffold_module.py salesbook`. Added 6 ORM Records (`SalesbookClientContactExtensionRecord`, `SalesbookOnboardingProgressRecord`, `SalesbookOnboardingResponseRecord`, `SalesbookPipelineDealRecord`, `SalesbookEngagementLogRecord`, `SalesbookTeamMembershipRecord`) inheriting from the central `Base`, all FK-ing to `company_profiles.profile_id`. Added 10 permission constants in `modules/salesbook/permissions.py` (does NOT touch `shared/auth.py`). Built full hex-arch: domain entities + value objects (enums) + exceptions, Pydantic views with `ConfigDict(extra="forbid")`, ports (5 Protocols), InMemory + SqlAlchemy repos for each port, `SalesbookService` exposing 14 public methods including the exhaustive view that drives the searchable salesbook viewer. Reuses `company_profile.list_products()` via `CompanyProfileProductReadAdapter`. Auto-extracted 114-question onboarding registry from canonical Google Sheet (`1HGSlYMtxE9...`) — 57 + 22 + 35; re-runnable via `backend/scripts/generate_onboarding_registry.py`. Fire-and-forget Sheets sync wired in (off by default).
- **Anto-file touch (1 line only):** `backend/src/hello_sales_backend/platform/db/migrations.py` — added `from hello_sales_backend.modules.salesbook.infra.persistence import *  # noqa F401,E402,F403  /Oliviercontribution` so Alembic autogenerate discovers the 6 new Records. The existing import block and `__all__` list are untouched.
- **New files (~16):** `backend/src/hello_sales_backend/modules/salesbook/{__init__,bootstrap,permissions}.py`; `modules/salesbook/domain/{entities,value_objects,exceptions,onboarding_registry,_onboarding_registry.json}`; `modules/salesbook/infra/{persistence,memory,repository}.py`; `modules/salesbook/use_cases/{views,ports,salesbook_service,commands}.py`; `modules/salesbook/{infra,workflows}/__init__.py`; `backend/scripts/generate_onboarding_registry.py`.
- **Tests:** smoke test (in-memory) — submitted onboarding response, recomputed progress (phase1=1.75% for 1/57), created deal, logged engagement, fetched exhaustive view (114 onboarding entries + pipeline + engagement). All passed.
- **Verified:** `PYTHONPATH=src python -c 'from hello_sales_backend.platform.db.migrations import metadata' → 17 tables (11 existing + 6 salesbook)`. Onboarding registry asserts `TOTAL_QUESTIONS == 114`.

## 2026-04-26 — 3.1 Alembic migration
- **By:** Olivier (/Oliviercontribution)
- **Change:** Generated Alembic migration `0007_add_salesbook_tables.py` via autogenerate against the registered Records. Creates 6 tables, 9 indexes, 1 unique constraint (profile_id+question_key on responses), and 6 FK CASCADE-on-delete to `company_profiles.profile_id`. Removed an autogenerate false-positive that wanted to drop `uq_session_summaries_session_id` (SQLite vs Postgres index/unique difference) — neutralized in both upgrade() and downgrade() with /Oliviercontribution-marked comments.
- **Anto-file touch:** NONE in this commit. The 1-line registration was already in place from 2.1.
- **New files:** `backend/alembic/versions/0007_add_salesbook_tables.py`
- **Verified:** `alembic upgrade head` against fresh SQLite created all 6 tables with correct column counts (11/11/9/14/12/8 = 65 columns total).

## 2026-04-26 — 4.1 HTTP routes + module wiring
- **By:** Olivier (/Oliviercontribution)
- **Change:** Wired the salesbook module into the HTTP transport. New file `entrypoints/http/routes/salesbook.py` exposes 16 endpoints under `/api/salesbook/*` covering: client_contact upsert/get, onboarding (registry, progress, responses single+batch+list, exhaustive view), pipeline (list/create/update with stage transition stamping), engagement-log (create + per-profile + per-deal + all-org feed), team (list/add/remove). Every handler is async, returns `ApiEnvelope` via `ok_response()`, and is gated by `Depends(require_permissions(APP_ACCESS_PERMISSION, ...))` using the constants from `modules/salesbook/permissions.py`.
- **Anto-file touches (4 files, all additive, all /Oliviercontribution-marked):**
  · `platform/composition/module_registry.py` — 1 import + 1 field on `ModuleRegistry`
  · `platform/composition/app_container.py` — 1 import + 1 build call (passes `company_profile_service`) + 1 ctor kwarg in `ModuleRegistry(...)`. `AppContainer` dataclass UNCHANGED.
  · `entrypoints/http/dependencies.py` — 1 import + 1 async factory `get_salesbook_service`
  · `entrypoints/http/router.py` — 1 import name + 1 `include_router(salesbook.router, prefix="/salesbook", ...)`
- **New files:** `backend/src/hello_sales_backend/entrypoints/http/routes/salesbook.py` (16 handlers, ~250 lines)
- **Verified:** App boots cleanly. 13 unique paths registered under `/api/salesbook/*` (multiple HTTP verbs share some paths). `GET /api/salesbook/onboarding/registry` without auth returns `401 {ok: false, error: {code: "auth.unauthenticated", ...}}` — confirms `require_permissions` chain fires before the handler.

## 2026-04-26 — 4.2 Salesbook moderation (rep comments + admin pins)
- **By:** Olivier (/Oliviercontribution)
- **Change:** Extended salesbook with role-based moderation per Olivier's spec ("admin sees everything, approves rep contributions, marks sticky content"). Added 2 new ORM Records (`SalesbookCommentRecord`, `SalesbookPinnedRecord`), 4 new permission constants (COMMENT_WRITE/APPROVE, PIN_WRITE/READ), Pydantic views + ports + InMemory + SqlAlchemy repos for both. SalesbookService gained 6 methods: `add_comment`, `list_comments`, `review_comment`, `list_pins`, `pin_entry`, `unpin_entry`. The exhaustive view now includes approved comments + active pins so the searchable salesbook viewer surfaces them. Generated Alembic migration `0008_add_salesbook_moderation.py` with both tables (FK CASCADE to company_profiles, UNIQUE on (profile_id, target_type, target_id) for pins). Added 6 new HTTP endpoints under `/api/salesbook/`: POST/GET `/clients/{pid}/comments`, PATCH `/comments/{id}/review`, GET/POST/DELETE `/clients/{pid}/pins`.
- **Anto-file touches:** NONE in this commit. All additions live under `modules/salesbook/` + `entrypoints/http/routes/salesbook.py` (which is a new file from 4.1, not Anto's). The Alembic plumbing was already in place from 2.1.
- **New files:** `backend/alembic/versions/0008_add_salesbook_moderation.py`
- **Verified:** Migration applies cleanly (both tables created in fresh SQLite). End-to-end moderation flow tested: admin posts onboarding response → rep posts comment (status=pending) → admin lists pending (finds 1) → admin approves (status→approved) → admin pins original response → exhaustive view returns 1 approved comment + 1 pin. App boots with 16 unique salesbook paths registered (previously 13).

## 2026-04-26 — 5.1 Frontend signup + onboarding wizard
- **By:** Olivier (/Oliviercontribution)
- **Change:** Built the signup flow (mock, demo-mode) and the section-by-section onboarding wizard with recap cards in `frontend-draft/`.
  - **Brand identity applied**: copied Hello Sales logo + icon into `public/`. Updated `globals.css` design tokens to the brand palette (white/black/Hello Sales blue `#0050C5`) with `Inter` as default font. Added a scoped `.theme-salesbook` class that brings back the editorial paper+ink palette + `Lora` serif + paper texture for the Salesbook tab — so the salesbook reads like a traditional sales playbook while the rest of the app reads like a modern utility. Existing primitives (`Surface`, `Field`, `Button`) read CSS custom properties so they auto-adapt with no per-component edits.
  - **Created missing infrastructure**: `src/shared/lib/cn.ts` (className combiner — file was referenced by every primitive but didn't exist) + `src/design-system/index.ts` (aggregator export so callers can `import { Surface, Field, ... } from "@/design-system"`).
  - **Demo-mode user state**: `useCurrentUser` hook + localStorage. Stores `{profileId, email, name, companyName, role}` per browser. Drives role-based nav (admin sees Moderation + Team, rep does not).
  - **Dual-mode API client** (`shared/api/salesbook.ts`): single `SalesbookApi` interface with two implementations — FastAPI (default, hits `/api/salesbook/*`) and Sheets-mode (`VITE_USE_SHEETS=true`, POSTs to Apps Script webhook). Sheets mode also pulls the registry from `public/onboarding-registry.json` (auto-copied from backend on every `npm run dev`/`build`).
  - **TypeScript types** in `entities/salesbook/types.ts` mirroring backend Pydantic views.
  - **SignupPage**: name + email + company + role-card picker (admin/rep). Admin role redirects to `/onboarding`, rep to `/dashboard`.
  - **OnboardingPage**: section-by-section flow per Olivier's spec — fill a section's questions → "Recap this section →" shows a card with every answer + count of unanswered → "Add details" inline-edits more, "Continue to next section" advances. Auto-saves on input change (debounced 600ms). Polymorphic `QuestionInput` dispatches on `answer_type` (text/numeric/date/options/multi-choice/editable bullets/text-upload/file-upload).
  - **Routes**: `/signup` (open), `/dashboard`, `/onboarding`, `/onboarding/:sectionIndex` (all gated by `RequireUser` redirect to `/signup`). Updated `AppShell` to use the brand icon + role-aware nav (Moderation + Team admin-only).
- **Anto-file touches (additive, /Oliviercontribution-marked):**
  · `src/styles/globals.css` — replaced palette tokens with brand colors, swapped fonts, removed the body radial gradients, appended `.theme-salesbook` scoped overrides + signup/role-card/bullet-editor styles
  · `src/shared/ui/AppShell.tsx` — wholesale rewrite of nav (still uses existing primitives; supports unauthenticated state + role gating)
  · `src/app/router/AppRouter.tsx` — added 4 routes (signup, onboarding, onboarding/:idx, root-redirect)
  · `package.json` — added `copy-registry` script + made dev/build depend on it
- **New files (10):** `shared/lib/cn.ts`, `shared/auth/useCurrentUser.ts`, `shared/api/salesbook.ts`, `entities/salesbook/types.ts`, `design-system/index.ts`, `pages/signup/{SignupPage.tsx,index.ts}`, `pages/onboarding/{OnboardingPage.tsx,QuestionInput.tsx,index.ts}`, `scripts/copy-onboarding-registry.sh`, `.env.example`.
- **Brand assets**: `public/hello-sales-logo.png` + `public/hello-sales-icon.png` (copies of `~/Desktop/HS/Brand/Official_HS_*`).
- **Verified**: `npm run build` passes — 91 modules transformed, 273KB JS / 86KB gzipped, 20KB CSS, 425ms build time. TypeScript strict mode clean. Registry copy step runs automatically.
