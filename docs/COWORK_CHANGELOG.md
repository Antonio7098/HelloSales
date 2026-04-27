# Cowork Changelog — feature/Oliviercontribution

A log of every Cowork-applied change on this branch. Keeps the May 3rd review to one document.

---

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
