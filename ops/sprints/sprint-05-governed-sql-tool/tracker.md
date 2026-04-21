# Sprint Tracker: Governed SQL Tool

> Project: HelloSales
> Sprint ID: sprint-05-governed-sql-tool
> Created: 2026-04-21

## Sprint Overview

- **Sprint Name:** Governed SQL Tool
- **Sprint Focus:** Add one governed agent tool that executes validated read-only SQL against a curated analytics catalog through the existing native tool-calling runtime.
- **Depends On:** `ops/sprints/sprint-01-observability-foundation/tracker.md`, `ops/sprints/sprint-02-worker-runtime-foundation/tracker.md`, `ops/sprints/sprint-04-session-substrate-foundation/tracker.md`
- **Status:** Not Started

## Sprint Goals

- **Primary Goal:** Ship one schema-agnostic, governed SQL tool for the generic agent, backed by a module-owned analytics query service with validation, redaction, and bounded execution.
- **Secondary Goals:**
  - Add a semantic catalog format and one initial catalog implementation suitable for scaffold-stage analytics views.
  - Preserve explicit tool lifecycle, approval, error classification, and observability through the existing conversational runtime.
  - Add deterministic test coverage and centralized smoke coverage, including a real-provider generic-agent smoke or an explicit justified deferral.

## Execution Checklist

- [ ] **Task 1: Formalize Sprint 5 artifacts and execution context**
  > *Description: Prepare sprint artifacts and execution context before implementation begins.*
  - [ ] **Sub-task 1.1:** Finalize `reasoning.md` and `tracker.md` under `ops/sprints/sprint-05-governed-sql-tool/`.
  - [ ] **Sub-task 1.2:** Start work from `sprint/sprint-05-governed-sql-tool` or explicitly record any branch deviation.
  - [x] **Sub-task 1.3:** Confirm the initial parser, dialect, and catalog source for Sprint 5: `sqlglot`, hand-authored YAML manifests, and PostgreSQL over curated views.

- [ ] **Task 2: Add the analytics-query bounded context**
  > *Description: Introduce a module-owned analytics query service with narrow ports for catalog loading, validation, execution, and result redaction.*
  - [ ] **Sub-task 2.1:** Add `modules/analytics_query/` bootstrap, public service/facade, commands/views as needed, and use-case ports.
  - [ ] **Sub-task 2.2:** Define the semantic YAML catalog manifest shape keyed by `catalog_id`, `catalog_version`, and `dialect`.
  - [ ] **Sub-task 2.3:** Add one initial YAML-backed catalog implementation suitable for scaffold-stage curated PostgreSQL analytics views.

- [ ] **Task 3: Implement governed SQL validation and execution**
  > *Description: Validate incoming SQL against the semantic catalog and policy before read-only execution, then return bounded, redacted results.*
  - [ ] **Sub-task 3.1:** Implement `sqlglot`-based AST validation that allows only a single read-only statement and rejects unapproved constructs.
  - [ ] **Sub-task 3.2:** Implement the first concrete PostgreSQL read-only executor with statement timeout, row limit, and result truncation.
  - [ ] **Sub-task 3.3:** Implement semantics-aware result redaction and bounded output shaping.

- [ ] **Task 4: Expose the capability as one agent tool**
  > *Description: Add `query_analytics_data` as a strict agent tool that calls the analytics-query service through existing application-tool seams.*
  - [ ] **Sub-task 4.1:** Add the application tool definition with strict input schema and bounded output shape.
  - [ ] **Sub-task 4.2:** Register the tool with the generic agent and any additional profile explicitly meant to use it.
  - [ ] **Sub-task 4.3:** Keep approval explicit by shipping the first version conservatively with static approval unless a safe dynamic path is implemented within sprint scope.

- [ ] **Task 5: Preserve operational visibility and machine-usable failures**
  > *Description: Ensure query execution remains visible through the canonical observability and error-handling surfaces.*
  - [ ] **Sub-task 5.1:** Emit stable machine-usable error codes for query validation, forbidden access, execution timeout, redaction failure, and data-store failures.
  - [ ] **Sub-task 5.2:** Persist and expose query metadata needed for inspection, such as catalog id/version, dialect, truncation, and risk flags.
  - [ ] **Sub-task 5.3:** Ensure session/run/tool-call inspection surfaces remain sufficient to diagnose SQL tool behavior without raw sensitive result leakage.

- [ ] **Task 6: Add verification and documentation**
  > *Description: Prove the new capability through deterministic tests, smoke coverage, and canonical documentation updates.*
  - [ ] **Sub-task 6.1:** Add unit tests for manifest handling, AST validation, risk classification, and result redaction.
  - [ ] **Sub-task 6.2:** Add integration tests for module wiring, concrete executor behavior, failure translation, and approval/failure lifecycle.
  - [ ] **Sub-task 6.3:** Extend centralized smoke coverage to exercise the SQL tool through the agent runtime.
  - [ ] **Sub-task 6.4:** Run at least one real-provider generic-agent smoke that proves the SQL tool path or explicitly record a justified deferral.
  - [ ] **Sub-task 6.5:** Update canonical backend docs to reflect the new bounded context and governed tool behavior.

## Testing And Documentation Checklist

- [ ] **Unit Tests:** deterministic coverage for catalog manifest handling, AST validation, risk flags, redaction, and output shaping
- [ ] **Integration Tests:** module wiring, executor behavior, failure translation, approval semantics, and inspectable tool lifecycle coverage
- [ ] **Smoke Tests:** critical conversational runtime path exercises the SQL tool through the centralized smoke harness
- [ ] **Real Provider Smoke:** run at least one provider-backed generic-agent smoke covering the SQL tool path or record an explicit justified deferral
- [ ] **Documentation Updates:** update canonical documentation in `backend/docs/`

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| The initial catalog drifts into product-specific semantics instead of scaffold-stage generic metadata | High | Keep the first catalog small, view-backed, and explicitly framed as a generic semantic manifest | Open |
| SQL validation is implemented with shallow heuristics rather than a real parser/AST | High | Require `sqlglot`-based AST validation and explicit negative tests for unsafe constructs | Open |
| Result redaction is treated like generic key-name masking and leaks semantically sensitive columns | High | Drive redaction from manifest sensitivity metadata and bounded result shaping | Open |
| Static approval creates too much friction for safe aggregate queries | Medium | Accept conservative approval in Sprint 5 and record dynamic approval as a follow-up if needed | Open |
| Real-provider smoke is skipped because the local environment lacks the YAML catalog or PostgreSQL curated-view setup | High | Provision a minimal smoke catalog and Postgres view path or record an explicit, review-visible deferral with reason | Open |

## Success Criteria

- [ ] **Success Criteria 1:** The generic agent can call one explicit SQL tool that executes only validated read-only queries against a curated analytics catalog.
- [ ] **Success Criteria 2:** SQL validation, execution, redaction, and failure handling are module-owned, inspectable, and governed by stable machine-usable policy and error codes.
- [ ] **Success Criteria 3:** Query tool behavior remains visible through existing run/session/tool-call and observability surfaces without introducing a parallel runtime stack.
- [ ] **Success Criteria 4:** The sprint records deterministic unit/integration coverage, centralized smoke coverage, and real-provider smoke evidence or an explicit justified deferral.

## Review And Sign-Off

- Sprint Status: Not Started
- Completion Date: [Date]

## Execution Evidence

- [Record tests run, explicit deferrals, notable commands, or review-ready evidence here as execution progresses]
