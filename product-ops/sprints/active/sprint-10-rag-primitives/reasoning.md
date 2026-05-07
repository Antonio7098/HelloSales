# Sprint Reasoning: RAG Primitives

> Project: HelloSales
> Sprint ID: sprint-10-rag-primitives
> Created: 2026-04-24
> Output: `ops/sprints/sprint-10-rag-primitives/reasoning.md`

## Overview

**Sprint:** RAG Primitives
**Purpose:** Introduce flexible, modular, provider-neutral retrieval-augmented generation primitives that future memory, document, and conversation retrieval features can reuse without coupling retrieval infrastructure to concrete agents.
**Tracker:** `ops/sprints/sprint-10-rag-primitives/tracker.md`
**Depends On:** `ops/sprints/done/sprint-09-context-engineering/tracker.md`

## Sprint Scope

Sprint 10 creates the first reusable RAG substrate for:
- `backend/src/hello_sales_backend/platform/rag/`
- optional composition wiring in `backend/src/hello_sales_backend/platform/composition/`
- optional diagnostics extension through `backend/src/hello_sales_backend/modules/system/`
- future context-source integration with Sprint 9 context engineering

The target outcome is a set of replaceable primitives, not a product-specific knowledge base:
- source document and chunk models with stable ids, source hashes, metadata, visibility scope, and provenance
- deterministic chunking policy with token/character budget metadata
- embedding provider and vector index ports with fake/in-memory implementations for tests
- retrieval query/result models with metadata filters, scoring, ranked evidence blocks, and citation-ready refs
- optional reranking contract that can be implemented later without changing callers
- ingestion/retrieval observability and failure semantics
- retrieval evaluation fixtures and metrics that can run without a real provider

The sprint explicitly includes:
- a provider-neutral RAG module under platform/runtime ownership
- test doubles and deterministic in-memory implementations
- a thin adapter shape for Sprint 9 context sources to consume ranked retrieval results
- documentation of how future real vector stores, embedding providers, and retrieval profiles plug in

The sprint explicitly excludes:
- building a product-specific document ingestion UI or public document-management API
- committing to a production vector database vendor
- sending private customer or internal data to a public embedding provider by default
- replacing the existing web-search tool
- making concrete agents own retrieval policy directly
- broad multi-agent or workflow orchestration unless indexing later proves it needs long-running background ownership

## Requirement Map

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | RAG needs a clear runtime substrate boundary rather than being scattered through agents, sessions, and tools. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Application agents and context sources must depend on retrieval contracts, not concrete vector stores or provider SDKs. |
| ARCH-LAYER-001 | Domain layer must remain pure | Architecture | Applicable | If a future product module owns domain documents, RAG infra must not leak provider or persistence concerns into domain models. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | Embeddings, indexes, stores, rerankers, and retrieval sources must be swappable through narrow ports. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Non-Applicable initially | The sprint should avoid new public transport surfaces unless an operational diagnostics endpoint is explicitly needed. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | `platform/rag` should expose a compact contract surface and hide fake/in-memory internals. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | RAG provider/index implementations should be assembled through composition, not constructed inside agents. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | RAG primitives are runtime infrastructure and must not encode HelloSales product assumptions. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Ingestion, embedding, indexing, and retrieval failures must become explicit results or structured failures. |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | Errors | Applicable | Provider/index errors need stable error codes, categories, operation, component, and redacted details. |
| ERR-CODE-001 | Error codes must be stable and machine-usable | Errors | Applicable | Retrieval failures should be alertable and distinguishable by stage. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | Provider, vector index, serialization, and malformed-source errors must preserve cause chains. |
| ERR-PROVIDER-001 | Provider failures must remain classified and observable | Errors | Applicable when real embeddings are added | Embedding provider failures must preserve remote status, retryability, model, timeout, and provider request ids when available. |
| ERR-DATA-001 | Persistence and data failures must be loud and distinct | Errors | Applicable | Bad source metadata, vector index corruption, and missing chunks must not look like empty retrieval. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | Chunk text, source metadata, and retrieved context can contain sensitive data. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | RAG stage failures need logs/events with stable fields. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Retrieval calls should preserve request/run/session/task correlation. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Operators need index health, counts, provider configured state, and recent failures without raw text leakage. |
| OBS-BG-001 | Background work must have visible terminal state | Observability | Ambiguous | Only applies if ingestion/indexing is implemented as background work in this sprint. |
| LLM-BOUNDARY-001 | Shared substrate, runtime mechanics, and mode-specific policy must stay separated | LLM | Applicable | RAG mechanics must stay separate from concrete prompts, agent policy, and LLM provider calls. |
| LLM-TOOL-001 | Tool execution boundaries must stay explicit and mode-scoped | LLM | Applicable | Retrieval may be exposed as a context source or tool later; it must not be hidden tool execution. |
| LLM-LIFECYCLE-001 | Lifecycle controls must stay explicit and inspectable | LLM | Applicable | Retrieval fallback, timeout, optional-source behavior, and reranking must be explicit. |
| LLM-RUN-001 | Runs and events must be durable or inspectable | LLM | Applicable when used by agents | Retrieval provenance and selected evidence should be inspectable through run events or context metadata. |
| LLM-PROMPT-001 | Prompts must be explicitly versioned and version propagation must stay observable | LLM | Applicable if prompt-driven query rewriting/reranking is added | Any prompt-based retriever or reranker must carry prompt identity/version metadata. |
| LLM-EXPOSE-001 | Operational exposure must flow through application modules | LLM | Applicable | Public retrieval behavior should be module-owned, not exposed directly from platform internals. |
| LLM-OBS-001 | LLM runtime monitoring must reuse the canonical observability runtime | LLM | Applicable | RAG events used by agent context must use the canonical observability runtime. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Fake embedding providers, fake index stores, and fake rerankers are required for deterministic tests. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Chunking, filtering, ranking normalization, provenance, and failure policy are deterministic logic. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable if composition or storage changes | Composition and any SQL-backed storage must be covered through realistic boundaries. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable if RAG is wired into agent runtime | The default agent path should remain healthy when a no-op or fake RAG source is present. |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | Testing | Applicable if real embedding provider path is supported | Real provider embedding/retrieval smoke must run or be explicitly deferred. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Provider timeout, malformed chunks, index failure, and optional retrieval failure need negative tests. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Retrieval tests should assert stable ids, scores, ordering, and metadata, not generated answer phrasing. |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | Workflows | Ambiguous | Simple in-process ingestion does not justify workflows; durable batch indexing might later. |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief | Applicable | Generic RAG infrastructure is safe scaffold-stage foundation work. |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | Pre-Brief | Applicable | Do not invent product document types, user journeys, or final retrieval UX. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief | Applicable | Build seams, contracts, diagnostics, and tests before product retrieval behavior. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief | Applicable | Keep transport surface internal/diagnostic unless a narrow operational API is necessary. |
| Frontend requirements | Frontend structure and UI rules | Frontend | Non-Applicable | Sprint 10 is backend/runtime infrastructure and does not add frontend code. |

### Applicable Requirements

- **ARCH-CORE-001 / ARCH-SHARED-001:** RAG primitives belong in a domain-neutral platform runtime package, not in application agent definitions or `shared/`.
- **ARCH-CORE-002 / ARCH-LAYER-002:** The central design seam is ports: embedding provider, chunk store/index writer, retriever, reranker, and optional context-source adapter.
- **ARCH-COMP-001:** Real implementations and fake/test implementations should be wired by composition or explicit tests, not constructed ad hoc by callers.
- **ERR-CORE-001 / OBS-CORE-001:** Empty retrieval is a valid result; failed retrieval is not. The sprint must distinguish both states in code and evidence.
- **ERR-REDACT-001:** Retrieved source text and metadata require deliberate redaction rules for logs, events, diagnostics, and error payloads.
- **LLM-BOUNDARY-001 / LLM-EXPOSE-001:** Retrieval can feed model-visible context, but generation remains owned by the agent/context runtime.
- **LLM-PROMPT-001:** If query rewriting, synthetic question generation, or LLM reranking is introduced, the prompt must be versioned. The initial primitive set should avoid prompt-driven steps unless necessary.
- **TEST-SEAM-001 / TEST-DET-001:** The first implementation must prove behavior with deterministic fake embeddings and in-memory index/search rather than relying on nondeterministic provider behavior.
- **PRE-SCOPE-002 / PRE-SCOPE-004:** Keep data models generic and public APIs narrow until the product brief defines real data sources and user flows.

### Non-Applicable Requirements

- **ARCH-ENTRY-001:** No broad new transport adapter is planned. If a route is added, it should be diagnostics-only and thin over a module service.
- **Frontend requirements:** No frontend code is planned.
- **LLM-IO-001:** The sprint does not add structured-output generation. Retrieval results are structured data, but they are local runtime models rather than LLM structured outputs.

### Ambiguous Or Conflicting Requirements

- **Platform package vs application module exposure:** Platform owns generic RAG mechanics, but any public/operational exposure must flow through modules. Resolution: implement core primitives in `platform/rag`; expose only diagnostics or future application behavior through module facades.
- **Ingestion lifecycle vs workflow rules:** Ingestion can be a simple synchronous library primitive or a background indexed job. Resolution: start with synchronous primitives and test seams; use background tasks/workflows only when the implementation actually coordinates long-running provider/index work.
- **Real embedding provider now vs provider-neutral scaffold:** Current research favors embeddings/vector stores for semantic search, but the repo has no vector DB dependency and pre-brief scope discourages vendor lock-in. Resolution: create the provider port and fake implementation now; real provider adapter is optional and must carry smoke/deferral evidence.
- **RAG context source vs tool:** Sprint 9 expects retrieval to plug into context profiles, while agentic RAG can expose retrieval as a tool. Resolution: design retrieval primitives independent of both call sites; add a context-source adapter first and leave tool exposure as future module-owned work.

### Open Questions

- Whether Sprint 10 should include a real OpenAI embeddings adapter or only the provider port plus fake/in-memory implementation.
- Whether the first durable index store should be SQL-backed, vector-DB-backed, or deferred until source volume and privacy constraints are known.
- Whether retrieval scope should default to session, actor, org, agent profile, or an explicit caller-supplied visibility filter. The primitives should support all without choosing a product default.
- Whether future indexing should be attached to session-summary tasks, independent jobs, or a dedicated ingestion scheduler.

## Current Research

**Research Status:** Completed on 2026-04-24.

### Sources Consulted

- [OpenAI API retrieval guide](https://platform.openai.com/docs/guides/retrieval): Semantic search is powered by vector stores, and searchable files carry attributes usable for filtering.
- [OpenAI API embeddings guide](https://platform.openai.com/docs/guides/embeddings): Embeddings turn text into vectors for search; current OpenAI embedding models expose dimension/cost trade-offs and max input constraints.
- [OpenAI API evaluation best practices](https://platform.openai.com/docs/guides/evaluation-best-practices): Q&A-over-docs evals should measure context recall, context precision, and user-rated answer quality.
- [OpenAI Cookbook, Evaluate RAG with LlamaIndex](https://cookbook.openai.com/examples/evaluation/evaluate_rag_with_llamaindex): RAG evaluation should separate retrieval quality from response quality and can use hit rate and MRR for retrieval.
- [LangChain retrieval docs](https://docs.langchain.com/oss/python/langchain/retrieval): Retrieval addresses finite-context and static-knowledge limits; building blocks include loaders, text splitters, embedding models, vector stores, and retrievers.
- [LangChain RAG tutorial](https://docs.langchain.com/oss/python/langchain/rag): Common RAG indexing flows load, split, and store documents, then retrieve relevant splits before generation; retrieved text should be treated as data to mitigate indirect prompt injection.
- [LlamaIndex ingestion pipeline docs](https://docs.llamaindex.ai/en/stable/module_guides/loading/ingestion_pipeline/): Ingestion pipelines apply transformations, can cache node+transformation outputs, and can optionally insert nodes into vector stores.

### Relevant Current Guidance

- **RAG is a pipeline of swappable stages:** Current documentation converges on source loading, splitting/chunking, embedding, storing/indexing, retrieval, optional reranking, and generation. Sprint 10 should model these as separable primitives.
- **Retrieval and generation should be decoupled:** Retrieval can support 2-step, agentic, or hybrid RAG. The primitives should return ranked evidence blocks, not generated answers.
- **Metadata filtering is first-class:** OpenAI retrieval uses attribute filters; HelloSales should carry actor/org/session/source metadata and filter before ranking where possible.
- **Embeddings have cost, dimension, and input limits:** Embedding model choice belongs behind configuration and provider ports, not hard-coded in chunking or retrieval logic.
- **Evaluation must start before production scale:** Context recall, context precision, hit rate, and MRR should exist as deterministic evaluation hooks from the first sprint.
- **Prompt injection risk is inherent to retrieved context:** Retrieved content must be wrapped as data, carry provenance, and never silently override system/developer instructions.
- **Caching/idempotency matters for ingestion:** Source hashes and transformation identities should be part of chunk/index metadata so repeated ingestion can skip unchanged inputs later.

### Options Or Guidance Rejected

- **Adopt a full RAG framework as the app architecture:** Rejected because the backend already has explicit contracts, composition, observability, and runtime boundaries. Framework docs inform the design, but the implementation should preserve local architecture.
- **Commit to OpenAI vector stores as the only store:** Rejected because it would couple RAG persistence to one provider before product privacy, tenancy, and volume constraints are known.
- **Use a production vector database immediately:** Rejected for the first primitive sprint because it adds infra before the calling surfaces and privacy boundaries are proven.
- **Let retrieved chunks be plain strings only:** Rejected because citations, redaction, filters, evals, and diagnostics all need stable provenance and metadata.
- **Evaluate only generated answers:** Rejected because retrieval can fail independently of generation. The sprint needs retrieval-level metrics first.

### Impact On Reasoning

- The first implementation should expose contracts and deterministic fakes before real provider adapters.
- Chunk records need source identity, hash, chunk sequence, metadata, visibility scope, and provenance.
- Retrieval results need `score`, `rank`, `source_ref`, `chunk_ref`, `metadata`, and a redacted/log-safe summary shape.
- Context-source integration should receive ranked blocks and decide prompt placement under Sprint 9's context budget rules.
- Any real embedding provider path must include provider failure mapping, timeout/retry policy, redaction, and real-provider smoke evidence or explicit deferral.

## Feature Analysis

### Feature 1: RAG Core Contracts And Models

**Description:** Add a provider-neutral RAG package that defines source documents, chunks, embedding requests/results, index records, retrieval queries, ranked evidence blocks, provenance, and errors.

**Affected Areas**
- new `backend/src/hello_sales_backend/platform/rag/`
- `backend/src/hello_sales_backend/platform/composition/app_container.py` if default services are assembled
- `backend/docs/codebase-map.md`

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-SHARED-001 | Keep primitives domain-neutral | `platform/rag` models and contracts | Import review and docs |
| ARCH-MODULE-001 | Expose a small stable surface | `platform/rag/__init__.py` | Public export review |
| ERR-SHAPE-001 | Structured errors for malformed sources and invalid queries | RAG error helpers | Failure-path unit tests |
| TEST-SEAM-001 | Ports can be faked | Embedding/index/retrieval/rerank protocols | Unit tests using fakes |

**Current-System Analysis**
- The repo has strong runtime packages under `platform/` and module-owned public facades under `modules/`.
- There is no RAG package, vector store dependency, embedding provider port, or retrieval index today.
- Sprint 9 explicitly excludes RAG primitives but needs a future retrieval source contract, making `platform/rag` the natural provider-neutral owner.

**Current Research Applied**
- LangChain and LlamaIndex both model RAG as modular stages.
- OpenAI retrieval treats vector stores and file attributes as core retrieval concepts, so metadata and filterable attributes should be part of the local model from the start.

**Options Considered**
- **Option A:** Add RAG models inside `platform/agents/`.
- **Option B:** Add a dedicated `platform/rag/` package with no agent dependency.
- **Option C:** Add a product module such as `modules/knowledge_base/`.

**Chosen Approach**
- Adopt Option B.

**Decision Justification**
- `platform/rag` keeps retrieval reusable across agents, workers, sessions, and future product modules.
- Option A would make RAG an agent concern and reduce reuse.
- Option C would invent a product capability before the brief and violate pre-brief scope.

**Execution Notes**
- Prefer Pydantic models for structured request/result boundaries where validation matters.
- Use stable ids and refs: source id, chunk id, chunk sequence, source URI/type, content hash, metadata, visibility scope, provenance.
- Keep raw chunk text out of diagnostics by default.

**Expected Evidence**
- **Tests:** model validation, stable id/hash behavior, redacted diagnostics shape.
- **Runtime Evidence:** none required until the primitives are wired into runtime execution.
- **Review Checks:** `platform/rag` does not import concrete agent definitions, HTTP routes, or product modules.

---

### Feature 2: Ingestion And Chunking Primitives

**Description:** Add deterministic source normalization and chunking primitives that can ingest text-like inputs into citation-ready chunks without committing to a concrete data source.

**Affected Areas**
- new `platform/rag/ingestion.py` or equivalent
- tests under `backend/tests/unit/`

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ERR-DATA-001 | Bad source shape differs from empty input | Source normalization/chunking | Negative tests |
| ERR-REDACT-001 | Sensitive chunk text is not logged wholesale | Error/event payloads | Redaction tests |
| TEST-UNIT-001 | Chunking behavior is deterministic | chunk sequence and budgets | Unit tests |
| PRE-SCOPE-002 | No product document types | source metadata names | Review |

**Current-System Analysis**
- Existing sessions have chronology and summaries, but no chunk representation.
- Existing docs emphasize scaffold-stage generic foundations, so source inputs should be generic and metadata-driven.

**Current Research Applied**
- LangChain describes splitting large documents into chunks that can fit retrieval and model context.
- LlamaIndex ingestion pipelines use transformations and cache transformation outputs, which supports storing a chunking policy id/version and source hash.

**Options Considered**
- **Option A:** Implement a minimal character/token-ish chunker with overlap, policy id, and deterministic chunk ids.
- **Option B:** Pull in a full document parsing/chunking framework.
- **Option C:** Defer chunking and only define models.

**Chosen Approach**
- Adopt Option A.

**Decision Justification**
- A deterministic local chunker is enough to prove contracts, tests, provenance, and future index seams.
- Option B adds dependency and behavior surface before product document formats are known.
- Option C would leave retrieval primitives too abstract to test meaningfully.

**Execution Notes**
- Start with text chunks only.
- Include chunk budget metadata even if exact tokenizer integration is deferred.
- Store source hash and chunking policy version so later re-ingestion can detect unchanged inputs.

**Expected Evidence**
- **Tests:** chunk ids stable across repeated runs; overlap and max-size behavior; empty/malformed source failure.
- **Runtime Evidence:** if any ingestion operation emits events, include counts and ids only, not raw text.
- **Review Checks:** chunking has no product-specific source names.

---

### Feature 3: Embedding And Index Ports With Deterministic Fakes

**Description:** Define embedding provider and index store ports, then implement fake/in-memory adapters for deterministic unit and integration tests.

**Affected Areas**
- `platform/rag/contracts.py`
- `platform/rag/memory.py` or equivalent
- `platform/composition/overrides.py` if composition needs replacement seams

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-LAYER-002 | Callers depend on ports | embedding/index interfaces | Import review |
| ERR-PROVIDER-001 | Real provider failures are classified | optional future OpenAI adapter | Smoke or deferral |
| TEST-SEAM-001 | Fake providers replace real providers | fakes and overrides | Unit/integration tests |
| TEST-DET-001 | Search tests avoid provider nondeterminism | fake embeddings/index | Stable ordering tests |

**Current-System Analysis**
- The LLM substrate has provider ports, but embeddings are a separate capability and should not be forced through chat/text generation contracts.
- The repo uses in-memory stores for scaffold-stage runtime paths in SQLite/test mode, which fits a deterministic first index adapter.

**Current Research Applied**
- OpenAI embeddings docs confirm embeddings are vector outputs for search and carry dimension/cost trade-offs.
- OpenAI retrieval and LangChain docs both treat vector stores as replaceable storage/search components.

**Options Considered**
- **Option A:** Add only protocols plus deterministic fake/in-memory implementations.
- **Option B:** Add OpenAI embeddings and a vector database in the first sprint.
- **Option C:** Reuse the LLM provider interface for embeddings.

**Chosen Approach**
- Adopt Option A, with an explicit optional follow-up or deferral for real embedding provider work.

**Decision Justification**
- Option A satisfies modularity and testability while avoiding provider lock-in.
- Option B adds operational and privacy complexity before the calling path is proven.
- Option C conflates provider modes and violates LLM substrate separation.

**Execution Notes**
- Embedding result metadata should include provider, model, dimension, input hash, and usage when available.
- The in-memory index should be clear scaffold/test infrastructure, not a production store.
- If real OpenAI embeddings are added, implement timeout/error mapping and provider smoke evidence.

**Expected Evidence**
- **Tests:** fake embedding dimensions, vector index upsert/search/delete, metadata filter behavior, stable score ordering.
- **Runtime Evidence:** provider configured state and index counts through diagnostics if wired.
- **Review Checks:** no concrete provider SDK leaks into caller-facing contracts.

---

### Feature 4: Retrieval Service, Reranker Port, And Context Adapter Shape

**Description:** Add a retrieval orchestration service that takes a query plus filters and returns ranked evidence blocks; define a reranker port and an adapter shape that Sprint 9 context sources can consume.

**Affected Areas**
- `platform/rag/retrieval.py`
- optional `platform/agents/context` integration after Sprint 9 lands
- `backend/docs/agent-runtime.md` or new RAG docs

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-BOUNDARY-001 | Retrieval does not generate answers | retrieval service | Unit tests and docs |
| LLM-TOOL-001 | Retrieval as context/tool stays explicit | context adapter contract | Event/metadata expectations |
| LLM-RUN-001 | Retrieved evidence is inspectable | ranked block metadata | Tests and event shape |
| ERR-CORE-001 | Retrieval failures are not empty results | retrieval orchestration | Failure tests |

**Current-System Analysis**
- Agent runtime currently builds prompt messages and executes tools; Sprint 9 intends to route future retrieval through context sources.
- Web search already returns sources and metadata but is public internet search, not private corpus RAG.

**Current Research Applied**
- LangChain retrieval docs distinguish 2-step, agentic, and hybrid RAG architectures. A neutral retrieval service can serve all three later.
- LangChain RAG security guidance requires treating retrieved context as data, not instructions.

**Options Considered**
- **Option A:** Return ranked evidence blocks and let context assembly decide how to present them.
- **Option B:** Return final prompt messages directly from retrieval.
- **Option C:** Make retrieval a native agent tool immediately.

**Chosen Approach**
- Adopt Option A.

**Decision Justification**
- Option A preserves separation: retrieval ranks evidence; context assembly budgets and formats model-visible context; agents generate answers.
- Option B would couple RAG to prompt formatting and make budgets harder to enforce.
- Option C may be valuable later for agentic RAG but is not required for primitives and would expand tool policy now.

**Execution Notes**
- Include `top_k`, score threshold, metadata filters, visibility scope, and optional reranker config.
- Reranking should be a protocol with a no-op/default implementation.
- Retrieved context formatting should mark content as data and preserve source refs for citation.

**Expected Evidence**
- **Tests:** query filters, empty result vs failed retrieval, no-op reranker, score/rank normalization.
- **Runtime Evidence:** retrieval events include query hash, result count, filter keys, index id, and latency, but not raw query/chunk text unless explicitly safe.
- **Review Checks:** retrieval service does not call LLM generation.

---

### Feature 5: Observability, Diagnostics, And Security Guardrails

**Description:** Make RAG operationally inspectable without leaking raw retrieved content or secrets.

**Affected Areas**
- `platform/observability/runtime.py` if new event helpers are justified
- `modules/system/` diagnostics views if RAG diagnostics are exposed
- RAG error/redaction helpers

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| OBS-CORE-001 | failures emit structured signals | ingestion/index/retrieval failures | Event tests |
| OBS-CORR-001 | request/task/run correlation survives | retrieval call context | Integration tests if wired |
| OBS-DIAG-001 | operator state is visible | diagnostics summary | View tests |
| ERR-REDACT-001 | secrets and raw content protected | logs/events/errors | Redaction tests |

**Current-System Analysis**
- The canonical observability runtime already supports operational events, diagnostics, metrics, and traces.
- Existing system diagnostics aggregate providers, tasks, agents, sessions, workers, and recent operational events.

**Current Research Applied**
- RAG systems need transparency into retrieval and context assembly, but prompt injection and privacy risks mean raw source content should not appear casually in logs.

**Options Considered**
- **Option A:** Emit structured stage-level metadata and expose only counts/config/recent failure summaries.
- **Option B:** Log raw chunks and queries for easy debugging.
- **Option C:** Add no diagnostics until production indexing exists.

**Chosen Approach**
- Adopt Option A.

**Decision Justification**
- Option A meets observability contracts while reducing content leakage risk.
- Option B is unsafe for private and internal data.
- Option C would make retrieval failures hard to diagnose and violate the operational contracts.

**Execution Notes**
- Use stable event names such as `rag.ingestion.completed`, `rag.index.updated`, `rag.retrieval.completed`, and `rag.retrieval.failed` only if events are added.
- Log query hashes, source ids, chunk counts, filter key names, model ids, provider names, and failure codes; avoid raw text.

**Expected Evidence**
- **Tests:** redacted event/error payloads; diagnostics summary contains index metadata and recent failure codes.
- **Runtime Evidence:** canonical operational events, not a parallel RAG telemetry store.
- **Review Checks:** no raw chunk text in logs or diagnostics.

---

### Feature 6: Retrieval Evaluation Harness And Documentation

**Description:** Add deterministic retrieval evaluation helpers and document the extension path for future real providers and vector stores.

**Affected Areas**
- `backend/tests/unit/`
- `backend/docs/rag-primitives.md`
- `backend/docs/codebase-map.md`
- `backend/docs/runtime-overview.md`

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| TEST-UNIT-001 | eval metric logic covered | hit rate/MRR/context precision helpers | Unit tests |
| TEST-SMOKE-001 | critical runtime path remains healthy if wired | no-op RAG source in agent runtime | Smoke or deferral |
| TEST-SMOKE-002 | real provider path verified or deferred | OpenAI embeddings adapter if added | Smoke evidence/deferral |
| PRE-SCOPE-003 | docs explain scaffold boundaries | backend docs | Review |

**Current-System Analysis**
- The backend already has centralized smoke and docs patterns.
- There is no RAG-specific evaluation harness today.

**Current Research Applied**
- OpenAI evaluation guidance calls out context recall and precision for Q&A-over-docs.
- The OpenAI Cookbook RAG eval example separates retrieval and response evaluation and uses hit rate/MRR for retrieval.

**Options Considered**
- **Option A:** Add retrieval-only deterministic eval helpers now.
- **Option B:** Add answer-quality LLM-as-judge evals immediately.
- **Option C:** Skip eval helpers until a production corpus exists.

**Chosen Approach**
- Adopt Option A.

**Decision Justification**
- Retrieval-only evals are deterministic and directly test the new primitives.
- Answer-quality evals require generation behavior and a product-specific answer rubric that is not ready.
- Skipping evals would leave ranking changes hard to review.

**Execution Notes**
- Start with fixtures mapping query ids to expected chunk ids.
- Implement hit rate, MRR, and simple context precision/recall helpers without a real provider.
- Document how response-level evals can be added once generation and product corpus are known.

**Expected Evidence**
- **Tests:** eval metric fixtures and regression tests.
- **Runtime Evidence:** not required for offline helpers.
- **Review Checks:** docs clearly distinguish primitive scaffold from production RAG product behavior.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| TEST-SMOKE-002 | Real provider embedding smoke may be deferred | Sprint can complete with provider-neutral ports and fake embeddings if real provider adapter is not added | Real provider behavior remains unverified | Temporary | Add real-provider smoke in the sprint that introduces a supported real embedding adapter |
| OBS-BG-001 / WF-SCOPE-001 | Background indexing may be deferred | Primitive sprint can prove synchronous ingestion and retrieval seams first | Large-source ingestion lifecycle remains unresolved | Temporary | Add task/workflow ownership when durable batch ingestion is introduced |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Use `platform/rag` as the runtime owner:** Driven by ARCH-SHARED-001, LLM-BOUNDARY-001, and PRE-SCOPE-003. RAG is generic infrastructure, not agent or product behavior.
- **Build ports before vendors:** Driven by ARCH-LAYER-002, TEST-SEAM-001, and current research on replaceable vector stores/retrievers.
- **Return evidence blocks, not generated answers:** Driven by LLM-BOUNDARY-001 and research separating retrieval from generation.
- **Make provenance mandatory:** Driven by ERR-REDACT-001, OBS-DIAG-001, and evaluation needs. Every retrieved block must be traceable without leaking raw content into operator surfaces.
- **Start with deterministic retrieval evals:** Driven by TEST-DET-001 and current eval guidance.

### Trade-offs

- **Less production capability now, better extension later:** Deferring a real vector database reduces immediate functionality but preserves vendor choice and testability.
- **More metadata on every chunk:** Provenance and visibility fields add model complexity but are necessary for filtering, citations, redaction, and evals.
- **No prompt-driven reranking initially:** This limits retrieval sophistication but avoids prompt-versioning and LLM nondeterminism in the primitive sprint.

### Assumptions

- Sprint 9 will provide or introduce a context-source seam that can consume ranked retrieval evidence.
- The product brief is still not stable enough to define real document sources, ingestion UI, or public retrieval APIs.
- RAG over private/session data must preserve actor/org/session visibility metadata from the beginning.
- Empty retrieval is a normal outcome and should be represented distinctly from failed retrieval.

### Dependencies

- `ops/sprints/done/sprint-09-context-engineering/`: context profiles and context-source extension points.
- Existing observability runtime: structured events and diagnostics should reuse this path.
- Existing auth/session metadata: actor, org, permissions, and session ids should shape future retrieval scope.

### Evidence Review Checklist

- [ ] Review can trace each RAG primitive to explicit architecture, error, observability, LLM, testing, and pre-brief requirements.
- [ ] Review can verify that agents and context profiles depend on retrieval contracts rather than concrete index/provider implementations.
- [ ] Review can distinguish empty retrieval from failed retrieval.
- [ ] Review can verify raw chunk text is not logged or exposed in diagnostics by default.
- [ ] Review can run deterministic retrieval unit tests without a real embedding provider.
- [ ] Review can see explicit smoke evidence or deferral if a real embedding provider path is added.

## Phase Exit Criteria

- [ ] Tracker scope is fully covered
- [ ] Applicable requirements are mapped
- [ ] Ambiguous and non-applicable requirements are recorded where relevant
- [ ] Latest relevant tools, technologies, options, best practices, and guidance were researched
- [ ] Research findings are tied to decisions, risks, alternatives, or evidence expectations
- [ ] Important decisions are explicitly justified
- [ ] Non-trivial alternatives are discussed
- [ ] Deviations, assumptions, risks, and unknowns are documented
- [ ] Expected evidence is defined

## Documentation Updates

- `backend/docs/rag-primitives.md`: New canonical doc for RAG contracts, extension points, privacy boundaries, and evaluation approach.
- `backend/docs/codebase-map.md`: Add `platform/rag/` ownership and high-signal files.
- `backend/docs/runtime-overview.md`: Explain how retrieval primitives fit the runtime graph once composed.
- `backend/docs/agent-runtime.md`: Update only if Sprint 10 wires a context-source adapter into agent execution.
