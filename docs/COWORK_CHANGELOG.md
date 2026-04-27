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
