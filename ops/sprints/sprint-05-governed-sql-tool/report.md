# Sprint Report: Governed SQL Tool

> Project: HelloSales
> Sprint ID: sprint-05-governed-sql-tool
> Review Date: 2026-04-21
> Status: Completed With Explicit Test Deferrals

## Intent Summary

**What changed:**
- One new bounded context, `modules/analytics_query/`, owns catalog loading, AST validation, bounded execution, result redaction, and observability for governed analytics queries.
- One new agent tool, `query_analytics_data`, is registered on the generic agent with static approval, strict input schema, and bounded output shape.
- A schema-agnostic semantic YAML catalog manifest format was introduced, with one scaffold-grade catalog at `backend/catalogs/analytics/scaffold_stage.yaml`.
- `sqlglot`-based AST validation enforces single-statement, read-only `SELECT` against approved relations and columns.
- A PostgreSQL/SQLAlchemy executor enforces statement timeout, row limit, and read-only transactions.
- Semantics-aware redaction masks `restricted`-sensitivity columns and truncates oversized cell values.
- Observability adapter emits `analytics_query.executed` and `analytics_query.failed` operational events.

**What did not change:**
- The agent runtime mechanics, session substrate, and tool lifecycle persistence were not redesigned.
- No new HTTP routes were added; the tool is exercised through existing conversational/session entrypoints.
- No workflow was introduced; execution remains an ordinary tool call.
- No dynamic approval policy was added; approval remains static.

**Most likely risks:**
1. SQL validation edge cases in complex AST constructs (subqueries, lateral joins, window functions).
2. The `SELECT *` blanket ban may be overly restrictive for some safe aggregate queries, but it is intentional for catalog-driven governance.
3. Real-provider smoke coverage for the analytics-query path is deferred due to a teardown stall in provider-backed session tests.
4. The initial catalog is small and scaffold-grade; future product-specific semantics must not drift into premature domain modeling.

---

## Review Findings

### Risk Scan

| Area | Finding | Severity |
| --- | --- | --- |
| SQL injection / data mutation | AST validation rejects DDL/DML and wraps execution in `SET TRANSACTION READ ONLY` for PostgreSQL. No raw SQL is passed unvalidated. | None |
| Schema escape | Only relations present in the loaded catalog are allowed; unknown tables raise `forbidden_relation`. | None |
| Sensitive data leakage | `restricted`-sensitivity columns are redacted to `***REDACTED***` in results. Metadata still reveals that a restricted column was queried (via `risk_flags`). | None |
| Unbounded execution | `LIMIT max_rows + 1` wrapper + `statement_timeout_ms` guard execution time and row volume. | None |
| Operational regression | The new module is assembled through the normal composition root and does not alter existing runtime paths. | None |

### Design Review

**Layering and coupling:**
- The module boundary is clean. `use_cases/ports.py` defines narrow replaceable ports: `AnalyticsCatalogPort`, `AnalyticsQueryValidatorPort`, `AnalyticsQueryExecutorPort`, `AnalyticsResultRedactorPort`, and `AnalyticsQueryDiagnosticsPort`.
- The service (`analytics_query_service.py`) depends only on ports, not concrete infra. This satisfies `ARCH-LAYER-002`.
- Concrete adapters live in `infra/`: YAML catalog store, `sqlglot` validator, SQLAlchemy executor, redactor, and observability adapter.
- The tool definition (`application/tools/analytics_query.py`) is a thin adapter over the module service, satisfying `LLM-EXPOSE-001`.

**Interfaces and seams:**
- The module public API (`__init__.py`) exports only `AnalyticsQueryModule` and `build_analytics_query_module`. Concrete infra is not exported.
- Composition happens through `platform/composition/app_container.py` and `module_registry.py`, satisfying `ARCH-COMP-001`.
- `platform/` remains domain-neutral; no analytics-specific policy leaked into shared or platform code.

**Failure modes:**
- Validation failures, catalog lookup failures, execution failures, and redaction failures each have stable machine-usable codes.
- Unexpected exceptions in the service are caught, wrapped in `AppError` with `analytics_query.unhandled_exception`, and emitted through diagnostics.

### Correctness Review

**AST validation:**
- `sqlglot.parse` parses exactly one statement. Multiple statements are rejected.
- The validator walks the AST and rejects forbidden node keys (DDL, DML, `union`, `truncate`, etc.).
- `SELECT *` is rejected because `star` is in the forbidden set; this is strong but intentional because redaction requires explicit column metadata.
- Relation resolution checks that every `exp.Table` exists in the catalog and is not a CTE.
- Column resolution handles qualified names, aliases, and unqualified ambiguous columns.

**Edge cases noted:**
- Projections with no resolvable columns (e.g., pure constants or some aggregates) receive `sensitivity="public"` and `semantic_type="derived"`. This is conservative for empty source sets.
- `pg_sleep` is explicitly rejected via `Anonymous` node check. Good defensive addition.

**Execution correctness:**
- The executor wraps the normalized SQL in `SELECT * FROM (...) AS governed_query LIMIT {max_rows + 1}`. This is generally safe for single `SELECT` statements and `WITH ... SELECT` in PostgreSQL, but complex CTE edge cases may require future refinement.
- Row truncation is detected by fetching `max_rows + 1` and comparing.
- `SET LOCAL statement_timeout` and `SET TRANSACTION READ ONLY` are PostgreSQL-specific guards.

### Security Review

- **Auth boundaries:** No new auth boundary was introduced. The tool inherits the existing session/agent approval boundary.
- **Injection risk:** SQL is validated against an allowlist of relations and columns via AST before execution. Read-only transaction mode is an additional defense in depth.
- **Secret handling:** No secrets are introduced in the new code. Database credentials remain external.
- **Dependency/supply chain:** `sqlglot` is the new parser dependency. The sprint reasoning justified this choice for dialect portability.

### Performance Review

- `LIMIT max_rows + 1` prevents unbounded result sets.
- `statement_timeout_ms` prevents runaway queries.
- Catalogs are loaded eagerly at module bootstrap and cached in memory. Given the intentionally small catalog set, this is appropriate.
- `sqlglot.parse` and AST walks are in-process and lightweight for the expected query sizes.

### Maintainability Review

- File structure follows the established module pattern: `bootstrap.py`, `use_cases/`, `infra/`.
- Naming is consistent and descriptive.
- The redactor and validator have no external side effects and are deterministic.
- Settings for the module (`analytics_query_catalog_dir`, `analytics_query_default_max_rows`, etc.) are injected at composition time.

### Test Review

- **Unit tests (`tests/unit/test_analytics_query.py`):**
  - YAML catalog manifest loading.
  - Multiple-statement rejection.
  - Join and sensitive-projection classification (risk flags, sensitivities).
  - Redaction of restricted values and cell truncation.
- **Integration tests (`tests/integration/test_analytics_query_tool.py`):**
  - End-to-end approval path with a fake provider and seeded SQLite data.
  - Validation failure translation and observability event emission.
- **Smoke tests (`tests/smoke/test_generic_agent_provider_smoke.py`):**
  - The generic-agent-provider smoke suite now includes an `analytics_query_completion` scenario.
  - Fake provider exercises `query_analytics_data` through the full session -> approval -> result lifecycle.

**Test gaps / deferrals:**
- A real-provider smoke for the analytics-query path was deferred. The tracker records this explicitly with justification: provider-backed session tests stall during pytest teardown in this workspace.
- The approval-path integration test `test_analytics_query_tool_requires_approval_and_returns_bounded_metadata` was previously stalling during teardown; the tracker notes it was fixed. Evidence: the test now passes in the current run.

### Documentation Review

- `backend/docs/runtime-overview.md` documents the new `modules/analytics_query` bounded context and its relationship to the conversational runtime.
- `backend/docs/agent-runtime.md` documents the governed SQL tool, approval stance, and result-shaping expectations.
- `backend/docs/testing-and-operations.md` records the SQL tool smoke path and the environment-gated real-provider evidence.
- Documentation is accurate and consistent with the implementation.

---

## Contract Adherence Verification

### Architecture Contract

| Requirement | Status | Evidence |
| --- | --- | --- |
| `ARCH-CORE-001` Module boundaries explicit | Pass | `modules/analytics_query/` is a standalone bounded context with small public API. |
| `ARCH-CORE-002` Dependency direction inward | Pass | `application/tools/` -> `modules/analytics_query/use_cases/` -> `ports`. Infra implements ports. |
| `ARCH-LAYER-002` Use cases depend on ports | Pass | `AnalyticsQueryService` accepts five ports in constructor. |
| `ARCH-COMP-001` Composition through registrars | Pass | `build_analytics_query_module` is called in `app_container.py`; result stored in `ModuleRegistry`. |
| `ARCH-MODULE-001` Small stable public API | Pass | `__init__.py` exports only `AnalyticsQueryModule` and `build_analytics_query_module`. |
| `ARCH-SHARED-001` Platform stays domain-neutral | Pass | No analytics policy in `platform/agents/`, `shared/`, or transport code. |

### Error Contract

| Requirement | Status | Evidence |
| --- | --- | --- |
| `ERR-CORE-001` No failure disappears | Pass | All catch blocks in service either re-raise `AppError` or wrap unexpected exceptions before re-raising. Diagnostics are emitted in both paths. |
| `ERR-SHAPE-001` Canonical error shape | Pass | All failures use `app_error(...)` with code, category, status_code, details, operation, component. |
| `ERR-CODE-001` Stable machine-usable codes | Pass | Codes follow `analytics_query.{area}.{reason}` pattern: `validation.invalid_sql`, `execution.timeout`, `catalog.not_found`, `redaction.failed`, etc. |
| `ERR-TRANS-001` Cause preserved | Pass | `from exc` is used on every wrapped exception. |
| `ERR-REDACT-001` Redaction safe | Pass | Restricted column values are replaced with `***REDACTED***`. Metadata (column name, sensitivity flag) is preserved for diagnosis. |
| `ERR-DATA-001` Data failures loud | Pass | SQLAlchemy errors are mapped to `analytics_query.execution.timeout` or `analytics_query.data_store.failed` with preserved cause. |

### Observability Contract

| Requirement | Status | Evidence |
| --- | --- | --- |
| `OBS-CORE-001` Structured signals on failure | Pass | `AnalyticsQueryObservabilityAdapter` emits `analytics_query.failed` with full error payload. |
| `OBS-CORR-001` Correlation survives | Pass | `request_id` and `trace_id` are threaded from tool context through service to diagnostics adapter. |
| `OBS-DIAG-001` Operator-relevant state | Pass | Events include catalog id/version, dialect, query fingerprint, risk flags, row count, truncated, execution time. |
| `OBS-ALERT-001` Machine-usable alerting | Pass | Stable codes and severity fields are present in every emitted event. |

### Testing Contract

| Requirement | Status | Evidence |
| --- | --- | --- |
| `TEST-SEAM-001` Replaceable collaborators | Pass | Unit tests use fake catalogs and in-memory redactor. Integration test uses fake LLM provider and SQLite seeding. |
| `TEST-UNIT-001` Business logic covered | Pass | Validator rules, risk classification, redaction, and output shaping have unit coverage. |
| `TEST-INT-001` Wiring covered | Pass | Integration tests verify module composition, failure translation, and approval lifecycle. |
| `TEST-SMOKE-001` Critical runtime smoke | Pass | `generic-agent-provider` smoke includes `analytics_query_completion` scenario. |
| `TEST-SMOKE-002` Real-provider smoke | Deferral | Explicit justified deferral recorded in tracker: real-provider analytics-query smoke not completed in this workspace due to teardown stall. |
| `TEST-FAIL-001` Failure paths tested | Pass | Multiple-statement rejection, forbidden relation, and validation-failure observability are explicitly tested. |
| `TEST-DET-001` Deterministic | Pass | Assertions target structure (status codes, error codes, result fields) not wording. |

### LLM Runtime Contract

| Requirement | Status | Evidence |
| --- | --- | --- |
| `LLM-BOUNDARY-001` Policy separated from substrate | Pass | SQL governance lives in module and tool service, not in `platform/llm/` or shared provider code. |
| `LLM-TOOL-001` Explicit tool boundary | Pass | `query_analytics_data` is one explicit tool with persisted tool-call lifecycle. |
| `LLM-LIFECYCLE-001` Approval explicit | Pass | Tool is registered with `requires_approval=True`. Approval id is assigned, persisted, and inspectable. |
| `LLM-RUN-001` Durable inspectable state | Pass | Tool calls and results are mirrored into session items and run/turn state. |
| `LLM-EXPOSE-001` Through application modules | Pass | Tool definition is in `application/tools/`, which delegates to `modules/analytics_query/`. |
| `LLM-OBS-001` Reuses canonical observability | Pass | `AnalyticsQueryObservabilityAdapter` delegates to `ObservabilityRuntime`. |

### Pre-Brief Scope Contract

| Requirement | Status | Evidence |
| --- | --- | --- |
| `PRE-SCOPE-001` Scaffold work acceptable | Pass | One governed query capability is valid runtime scaffolding. |
| `PRE-SCOPE-002` No product-specific commitments | Pass | Catalog relations are generic (`analytics_daily_pipeline`, `analytics_rep_performance`). No CRM-specific workflow or export semantics. |
| `PRE-SCOPE-003` Replaceable scaffolding | Pass | Catalog, validator, executor, and redactor are behind ports. |
| `PRE-SCOPE-004` Narrow public surface | Pass | Only one agent tool is added; no broad analytics API. |

### Workflow Contract

| Requirement | Status | Evidence |
| --- | --- | --- |
| `WF-SCOPE-001` No workflow for ordinary tool execution | Pass | SQL execution remains an ordinary service/tool path. No workflow engine involvement. |
| `WF-BOUNDARY-001` No workflow leakage | Pass | No workflow runtime interaction in analytics query services. |

---

## Findings

### Blockers

None.

### High

None.

### Medium

**M-1: `SELECT *` blanket ban may create friction for ad-hoc exploration**
- **Location:** `infra/validator.py` `_FORBIDDEN_NODE_KEYS` includes `"star"`.
- **Issue:** All queries must explicitly list columns. This is safe but may be overly restrictive for legitimate aggregate exploration once dynamic approval is introduced.
- **Why it matters:** Operator friction; the model may generate `SELECT *` naturally and fail validation.
- **Suggested fix:** Consider adding an explicit `allow_star` flag (default `False`) to the catalog manifest or validator config, with the requirement that star queries would still be subject to the same redaction rules by expanding against the catalog metadata at validation time.
- **Evidence:** Current unit tests confirm `star` is rejected implicitly via the forbidden-node walk.

**M-2: Real-provider smoke for analytics-query path is deferred**
- **Location:** `ops/sprints/sprint-05-governed-sql-tool/tracker.md`
- **Issue:** The tracker explicitly records that a provider-backed generic-agent smoke for the analytics-query scenario was not completed in this workspace.
- **Why it matters:** `TEST-SMOKE-002` requires real-provider evidence for critical provider-backed paths. The deferral is justified by a pytest teardown stall, but the gap remains.
- **Suggested fix:** Re-run the provider-backed generic-agent smoke for the analytics-query scenario once the teardown stall is fixed or in an environment closer to CI/runtime parity.
- **Evidence:** Tracker records deferral with reason. The fake-provider smoke passes.

### Low / Nits

**L-1: Executor ignores `max_cell_length` parameter**
- **Location:** `infra/executor.py` line 27: `del max_cell_length`
- **Issue:** The executor accepts `max_cell_length` in its constructor but does not use it; truncation is handled by the redactor.
- **Why it matters:** Slight interface inconsistency; no runtime impact.
- **Suggested fix:** Remove `max_cell_length` from the executor constructor or document why it is accepted but unused.

**L-2: `actor_id` is accepted but unused in service**
- **Location:** `use_cases/analytics_query_service.py` line 50: `del actor_id`
- **Issue:** `actor_id` is passed through the tool context but not used for authorization or auditing.
- **Why it matters:** Audit trails and actor-scoped policies will eventually need this field. Leaving it unused is fine for Sprint 5 but should be revisited when multi-tenant or RBAC policies are added.
- **Suggested fix:** Add a comment noting that `actor_id` is reserved for future authorization/audit usage.

---

## Finalisation

### TL;DR

Sprint 5 delivers a well-architected, module-owned governed SQL tool with clean ports, `sqlglot`-based AST validation, PostgreSQL-bound execution, semantics-aware redaction, and explicit observability. The implementation conforms to all applicable governing contracts. All success criteria are met. The only open items are an explicit justified deferral for real-provider smoke (recorded in the tracker) and two minor maintainability nits.

### Testing and Verification Status

- **Ruff:** `venv/bin/python -m ruff check src tests` — pass (exit 0).
- **Mypy:** `venv/bin/python -m mypy src` — pass (exit 0).
- **Unit + Integration + Smoke (fake provider):**
  ```
  venv/bin/python -m pytest tests/unit/test_analytics_query.py \
    tests/unit/test_agent_registry.py \
    tests/integration/test_app_factory.py \
    tests/integration/test_analytics_query_tool.py \
    tests/smoke/test_generic_agent_provider_smoke.py -q
  ```
  — all pass.
- **Real-provider smoke:** Deferred with explicit justification in tracker.

### Security Notes

- SQL validation happens before execution via AST walk.
- PostgreSQL execution uses `SET TRANSACTION READ ONLY` and `SET LOCAL statement_timeout`.
- Restricted-sensitivity columns are redacted in tool results.
- The tool requires explicit human approval before any query runs.
- No secrets or credentials are embedded in catalog manifests or source code.

### Technical Debt and Carried-Forward Risks

1. **Dynamic approval policy:** Static approval creates friction for safe aggregate queries. The reasoning document and tracker record this as a temporary deviation with a follow-up to design dynamic approval metadata.
2. **Real-provider smoke gap:** The provider-backed analytics-query smoke path lacks environment-backed evidence in this workspace. Follow-up is to re-run after fixing the teardown stall.
3. **Catalog drift risk:** The initial catalog is intentionally small and scaffold-grade. Future sprints must guard against letting it become a premature product-specific schema.
4. **CTE wrapping edge cases:** The executor's `SELECT * FROM (normalized_sql) AS governed_query LIMIT N` wrapper is safe for standard `SELECT` and `WITH ... SELECT` in PostgreSQL, but exotic CTE/syntax edge cases may need refinement as the dialect surface expands.

### Recommendations for Next Sprint

1. **Fix the pytest teardown stall** in provider-backed session tests so that real-provider smoke can be run reliably for the analytics-query path.
2. **Design dynamic approval metadata** so that low-risk aggregate queries (e.g., single-relation, no restricted columns, no joins) can bypass static approval while high-risk queries still pause.
3. **Expand negative test coverage** for exotic SQL constructs (lateral joins, window functions, subqueries in SELECT) if the validator is expected to support or reject them explicitly.
4. **Evaluate catalog refresh strategy** once the product brief stabilizes; hand-authored YAML is fine for scaffolding but will need a maintenance plan or replacement pipeline.
5. **Wire `actor_id` into audit/logging** when identity and authorization semantics are defined.
