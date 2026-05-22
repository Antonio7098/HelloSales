# Sprint Tracker: RAG Primitives

> Project: HelloSales
> Sprint ID: sprint-10-rag-primitives
> Created: 2026-04-24

## Sprint Overview

- **Sprint Name:** RAG Primitives
- **Sprint Focus:** Build provider-neutral retrieval, ingestion, embedding, indexing, provenance, and evaluation primitives that future context profiles can use without coupling agents to RAG infrastructure.
- **Depends On:** `ops/sprints/sprint-09-context-engineering/tracker.md`
- **Status:** Not Started

## Sprint Goals

- **Primary Goal:** Add a modular `platform/rag` substrate with contracts, deterministic fakes, retrieval orchestration, provenance, and tests.
- **Secondary Goals:**
  - Keep RAG generic and safe, with no product-specific document sources or public UX commitments.
  - Make retrieval results citation-ready and context-source-ready without generating answers inside the RAG layer.
  - Add deterministic retrieval evaluation helpers so ranking quality can be tested before real provider integration.
  - Preserve observability and redaction discipline for ingestion, indexing, and retrieval failures.

## Execution Checklist

- [ ] **Task 1: Create RAG core package and public contracts**
  > *Description: Establish the provider-neutral runtime boundary for RAG primitives before adding implementation details.*
  - [ ] **Sub-task 1.1:** Add `platform/rag/` package with compact public exports for source refs, chunks, embeddings, index records, retrieval queries, ranked evidence, provenance, and visibility scope.
  - [ ] **Sub-task 1.2:** Define narrow ports for embedding providers, index writers/readers, retrievers, rerankers, and diagnostics snapshots.
  - [ ] **Sub-task 1.3:** Add RAG-specific structured error helpers/codes for malformed source data, embedding failures, index failures, retrieval failures, and invalid filters.

- [ ] **Task 2: Add deterministic ingestion and chunking primitives**
  > *Description: Convert generic text-like inputs into stable, citation-ready chunks without committing to product document types.*
  - [ ] **Sub-task 2.1:** Implement source normalization with source id, source type, source URI/name, content hash, metadata, visibility scope, and provenance.
  - [ ] **Sub-task 2.2:** Implement a deterministic chunking policy with max size, overlap, chunk sequence, policy id/version, and budget metadata.
  - [ ] **Sub-task 2.3:** Add unit tests for stable chunk ids, overlap behavior, empty input, malformed source metadata, and redacted diagnostic/error payloads.

- [ ] **Task 3: Add embedding and index implementations for tests**
  > *Description: Prove the RAG seams with deterministic fakes before introducing production provider or vector-store dependencies.*
  - [ ] **Sub-task 3.1:** Add a fake embedding provider with deterministic dimensions and stable vectors suitable for repeatable ranking tests.
  - [ ] **Sub-task 3.2:** Add an in-memory index store that supports upsert, delete, query, metadata filters, score ordering, and diagnostics counts.
  - [ ] **Sub-task 3.3:** Add tests for embedding metadata, vector dimensions, index upsert/search/delete, filter behavior, and empty-result vs failed-result distinction.

- [ ] **Task 4: Implement retrieval orchestration and context adapter shape**
  > *Description: Return ranked evidence blocks that Sprint 9 context profiles can format and budget later.*
  - [ ] **Sub-task 4.1:** Add a retrieval service that accepts query text or query embedding, visibility scope, metadata filters, `top_k`, score threshold, and correlation metadata.
  - [ ] **Sub-task 4.2:** Add a no-op reranker plus reranker protocol so future cross-encoder or LLM rerankers can be injected without changing callers.
  - [ ] **Sub-task 4.3:** Add a context-source adapter model/contract that maps ranked evidence into context blocks with data-only formatting guidance and source refs, without requiring Sprint 9 implementation changes.
  - [ ] **Sub-task 4.4:** Add tests for ranking, filtering, reranker invocation, query validation, context block shaping, and failure policy.

- [ ] **Task 5: Add observability, diagnostics, and privacy guardrails**
  > *Description: Make RAG operations inspectable while keeping raw source text and sensitive metadata out of logs and diagnostics by default.*
  - [ ] **Sub-task 5.1:** Emit or model canonical operational signals for ingestion completed/failed, index updated/failed, and retrieval completed/failed when runtime operations are invoked.
  - [ ] **Sub-task 5.2:** Add diagnostics snapshot support for provider configured state, index ids, chunk counts, embedding dimension/model metadata, recent failure codes, and last update time.
  - [ ] **Sub-task 5.3:** Add redaction helpers/tests that preserve ids, counts, hashes, metadata keys, and failure codes while excluding raw chunk text and secret-bearing values.

- [ ] **Task 6: Add retrieval evaluation helpers**
  > *Description: Provide deterministic retrieval-quality checks before answer generation or production corpora exist.*
  - [ ] **Sub-task 6.1:** Add fixture models for query ids, expected chunk ids, retrieved chunk ids, ranks, and scores.
  - [ ] **Sub-task 6.2:** Implement hit rate, mean reciprocal rank, and simple context precision/recall helpers over retrieval results.
  - [ ] **Sub-task 6.3:** Add unit tests showing metric behavior for perfect retrieval, partially correct retrieval, empty retrieval, and wrong ordering.

- [ ] **Task 7: Wire composition seams and docs**
  > *Description: Make the primitives discoverable and replaceable without exposing broad product APIs.*
  - [ ] **Sub-task 7.1:** Add composition/override seams for fake or in-memory RAG services if the implementation is assembled by the app container.
  - [ ] **Sub-task 7.2:** Extend system diagnostics only if RAG runtime state is composed; keep any transport changes thin and module-owned.
  - [ ] **Sub-task 7.3:** Add `backend/docs/rag-primitives.md` and update `backend/docs/codebase-map.md` plus `backend/docs/runtime-overview.md`.
  - [ ] **Sub-task 7.4:** Record explicit real-provider smoke evidence or deferral if no real embedding provider is added.

## Testing And Documentation Checklist

- [ ] **Unit Tests:** deterministic coverage for models, chunking, fake embeddings, in-memory index behavior, retrieval ranking/filtering, redaction, and eval metrics
- [ ] **Integration Tests:** composition and diagnostics coverage if RAG services are wired into the app container or system module
- [ ] **Smoke Tests:** run existing agent/session smoke if RAG is wired into agent context; otherwise record that runtime smoke is not applicable for primitives-only work
- [ ] **Real Provider Smoke:** run only if a real embedding provider path is introduced; otherwise record an explicit deferral
- [ ] **Documentation Updates:** add/update canonical backend docs for RAG ownership, extension points, privacy rules, and eval strategy

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| RAG abstractions become too broad to implement | High | Start with source/chunk/embed/index/retrieve/eval primitives and reject product-specific features | Open |
| Vector database choice leaks into contracts | High | Keep vector-store APIs behind ports and use in-memory/fake implementations first | Open |
| Retrieved text leaks into logs or diagnostics | High | Add redaction tests and log ids/counts/hashes instead of raw content | Open |
| Empty retrieval is confused with failed retrieval | Medium | Model empty result as success with zero ranked blocks; model failed retrieval as structured error | Open |
| Sprint 9 context-source shape changes | Medium | Keep Sprint 10 context adapter primitive and ranked-block based, then adapt during execution if Sprint 9 lands differently | Open |
| Real embedding provider behavior remains unverified | Medium | Defer real provider path explicitly or add real-provider smoke when the adapter is introduced | Open |

## Success Criteria

- [ ] **Success Criteria 1:** A domain-neutral `platform/rag` package defines stable RAG primitives and ports.
- [ ] **Success Criteria 2:** Deterministic chunking, fake embeddings, and in-memory retrieval can be tested without network or provider credentials.
- [ ] **Success Criteria 3:** Retrieval returns ranked, citation-ready evidence blocks with provenance and visibility metadata, not generated answers.
- [ ] **Success Criteria 4:** RAG failures, diagnostics, and redaction behavior follow the operational contracts.
- [ ] **Success Criteria 5:** Retrieval eval helpers measure hit rate, MRR, and simple context precision/recall over deterministic fixtures.
- [ ] **Success Criteria 6:** Backend docs explain how future real providers, vector stores, and Sprint 9 context sources plug into the primitives.

## Review And Sign-Off

- Sprint Status: Not Started
- Completion Date: [Date]

## Execution Evidence

- Created Sprint 10 reasoning and tracker artifacts.
- External research completed on 2026-04-24 and recorded in `reasoning.md`.
- [Record implementation test runs, smoke evidence, documentation updates, explicit deferrals, and review notes here as execution progresses.]
