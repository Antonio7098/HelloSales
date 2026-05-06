# Sprint Report: Context Engineering (sprint-09-context-engineering)

> Review Date: 2026-04-24  
> Reviewer: Agent Review  
> Status: SIGN-OFF WITH MINOR NOTES

## TL;DR

The sprint delivers a clean, provider-neutral context assembly layer with named profiles, replaceable sources, and observable metadata. The default `basic-session-v1` profile preserves existing behavior. The implementation satisfies all applicable architectural, error, observability, and testing requirements. No RAG primitives were introduced per sprint exclusion. **Sign-off granted with two minor notes.**

---

## 1. Intent Summary

| Area | Intent |
|------|--------|
| **What changed** | Added `platform/agents/context.py` with context profiles, source protocols, deterministic assembler, session context source, fake sources, and future retrieval seam. Wired `GenericAgentRuntime` to delegate to the assembler before provider calls. Made profile selection runtime/configuration-driven. |
| **What did NOT change** | Provider-specific LLM APIs, prompt definitions, frontend code, concrete memory storage, RAG primitives (vector stores, embeddings, chunking). |
| **Most likely risks** | Profile misconfiguration in production; optional source failure can silently degrade context for some profiles; retrieval port needs a real implementation to matter. |

---

## 2. Review Findings

### 2.1 Risk Scan

| Risk | Finding | Severity |
|------|---------|----------|
| Security | Event payloads correctly redact provenance metadata without raw context text. Error codes are stable machine-usable strings. No injection risk. | Pass |
| Data loss | Default profile preserves exact behavior; no data loss path introduced. | Pass |
| Correctness | Assembler handles required vs optional source failures, budget truncation, message ordering, and duplicate input handling correctly. | Pass |
| Availability | Miswired assembler raises explicit `agent.context.assembler_missing` error before provider call. | Pass |
| Operational regression | Default profile output matches previous inline assembly shape (verified in test). | Pass |

### 2.2 Design Review

| Aspect | Finding |
|--------|---------|
| **Cohesion** | Context layer correctly owns profile abstraction, source protocols, and assembly logic in `platform/agents/`. |
| **Coupling** | Runtime depends on `AgentContextAssembler` protocol—no concrete source. Application agents (definitions) do not import session stores, memory stores, or retrieval adapters. Satisfies ARCH-CORE-002 and ARCH-LAYER-002. |
| **Layering** | Runtime delegates before provider call (`runtime.py:265-273`). Correct flow: runtime → assembler → sources → session store port. |
| **Interfaces** | `AgentContextAssembler` and `AgentContextSource` protocols are narrow and testable. `SessionStorePort` abstraction is the only infra dependency. |
| **Invariants** | Profile always selected by ID; profile must exist; sources are resolved by `source_id`; message budget applies to aggregated context source output. |
| **Failure modes** | Required source failure → explicit `AppError` with profile/source metadata. Optional source failure → recorded in `skipped_sources`, warning event emitted. No session → empty provenance with `reason`, not error. |

### 2.3 Correctness Review

| Area | Finding |
|------|---------|
| Edge cases | Handles no session, session without summary, summary with partial coverage, recent-item deduplication (correctly excludes current input), budget truncation, duplicate tool results. |
| Error handling | Required vs optional failure correctly differentiated with stable error codes. Profile-not-found errors include available profile IDs. |
| Resource management | Uses existing `SessionStorePort` without adding new connections. No unmanaged async or connection leaks. |

### 2.4 Security Review

| Area | Finding |
|------|---------|
| Auth boundaries | Assembler receives run metadata with actor/org permissions but does not enforce auth—correctly delegated to runtime flow. |
| Injection risk | No—context sources render messages through typed `ChatMessage` dataclass. |
| Secret handling | No secrets in context assembly. |
| Unsafe deserialization | No—JSON rendering is explicit (`json.dumps`). |
| Dependency | No new dependencies added. |

### 2.5 Performance Review

| Area | Finding |
|------|---------|
| Algorithmic complexity | Single `await` per source in profile order; message aggregation is O(n) in source count and recent-item slicing is O(k). No O(n²) paths. |
| Hot paths | Context assembly runs once per turn before LLM call—appropriate. |
| Caching | Not applicable for first release; can be added as future optimization. |
| Backpressure | None introduced. |

### 2.6 Maintainability Review

| Area | Finding |
|------|---------|
| Structure | Clean. Profiles, sources, and assembler are separate. Dataclasses use frozen+slots. |
| Duplication | Minimal. |
| Readability | Well-modelled. Profile IDs like `basic-session-v1`, source IDs like `session-history` are descriptive. |
| Configuration | Profile selection via `HELLO_SALES_AGENT_CONTEXT_PROFILE` environment variable (documented in configuration docs). |
| Naming | Consistent enums (`AgentContextSourceCategory`, `AgentContextFailurePolicy` etc). |

### 2.7 Test Review

| Area | Finding |
|------|---------|
| Adequacy | Unit tests cover source ordering, budget/truncation, required vs optional failure, provenance metadata, basic session profile shape. |
| Determinism | All unit tests use fakes and deterministic assertions. |
| Negative coverage | Tests for missing profile (`profile_not_found`), unregistered source (`source_not_registered`), required vs optional source failure. |
| Regression protection | Regression test proves `basic-session-v1` message shape matches pre-sprint behavior. |

### 2.8 Documentation Review

| Area | Finding |
|------|---------|
| Public behavior | Documented in `backend/docs/agent-runtime.md` and `backend/docs/runtime-overview.md`. |
| Operator-facing | Configuration documented in `backend/docs/configuration-and-environment.md`. |
| Diagnostics | Event payload structure documented (no raw context text). |
| Follow-up | No follow-up docs required. |

---

## 3. Contract Adherence

### 3.1 Architecture Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **ARCH-CORE-001 / ARCH-SHARED-001** | ✅ | Context layer is under `platform/agents/`, domain-neutral. |
| **ARCH-CORE-002 / ARCH-LAYER-002** | ✅ | Agent definitions do NOT import session/memory/retrieval stores. |
| **ARCH-COMP-001** | ✅ | Profile/sources wired in composition via `build_basic_context_assembler`. |

### 3.2 Error Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **ERR-CORE-001** | ✅ | Required source failure raises `AppError` with cause. |
| **ERR-CODE-001** | ✅ | Stable codes: `agent.context.profile_not_found`, `agent.context.source_failed`. |
| **ERR-TRANS-001** | ✅ | Source adapter failures wrap original cause. |
| **ERR-DATA-001** | ✅ | No-session returns provenance (`reason: "run_has_no_session"`) not error. |
| **ERR-REDACT-001** | ✅ | Event payloads are profile/source metadata only. |

### 3.3 Observability Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **OBS-CORE-001** | ✅ | `agent.context.assembled` events emitted. |
| **OBS-CORR-001** | ✅ | `run_id`, `turn_id`, `session_id`, `profile_id` in event. |
| **OBS-DIAG-001** | ✅ | Event payload includes source counts and truncation. |

### 3.4 LLM Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **LLM-BOUNDARY-001** | ✅ | Context assembly is separate from provider call. |
| **LLM-TOOL-001** | ✅ | Tool replay is explicit in runtime after assembly. |
| **LLM-PROMPT-001** | ✅ | `context_profile_id`/`version` in event metadata. |
| **LLM-OBS-001** | ✅ | Uses existing runtime event surface. |

### 3.5 Pre-Brief Scope Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **PRE-SCOPE-001 / PRE-SCOPE-003** | ✅ | Context engineering is generic runtime scaffolding. |
| **PRE-SCOPE-002 / PRE-SCOPE-004** | ✅ | No product memory behavior or broad public APIs invented. |

### 3.6 Testing Requirements

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **TEST-SEAM-001** | ✅ | `FakeAgentContextSource`, `FakeLongTermMemoryContextSource` are replaceable. |
| **TEST-UNIT-001** | ✅ | Unit tests cover assembler ordering, failure, budget. |
| **TEST-INT-001** | ✅ | Integration/smoke tests use composed app. |
| **TEST-FAIL-001** | ✅ | Missing profiles, unregistered sources tested. |

---

## 4. Testing And Verification Status

| Check | Command | Result |
|-------|---------|-------|
| Unit tests | `PYTHONPATH=src pytest tests/unit/test_agent_context.py` | ✅ 22 passed |
| Runtime unit tests | `PYTHONPATH=src pytest tests/unit/test_generic_agent_runtime.py` | ✅ passed |
| Lint | `ruff check src tests/unit/test_agent_context.py` | ✅ passed |
| Typecheck | `mypy src/hello_sales_backend/platform/agents/` | ✅ passed |
| Integration tests | `PYTHONPATH=src pytest tests/integration/test_app_factory.py` | ✅ passed |
| Smoke tests | `PYTHONPATH=src pytest tests/smoke/test_agent_runs.py` | ✅ passed |
| Real provider smoke | `HELLO_SALES_AUTH_REQUIRED=false python -m hello_sales_backend.smoke generic-agent-provider` | ✅ passed |

---

## 5. CI Checks Status

✅ Ruff: passed  
✅ Mypy: passed (234 source files)  
✅ Tests: 125 passed, 6 skipped (smoke), 2 skipped (postgres)

---

## 6. Security Notes

- Context events correctly avoid leaking raw prompt, memory, retrieval, or tool payload text.
- Error codes are stable machine-usable strings.
- No new authentication or authorization logic introduced.
- No new surface area for injection.

---

## 7. Minor Notes

| Note | Location | Description |
|------|---------|------------|
| **Nit 1** | `context.py:74` | The `budget` field in `AgentContextProfile` is defined but not connected to meaningful enforcement in this release—currently defaults to `None` (no limit). This is acceptable since the first release preserves behavior, but future profiles should use it. |
| **Nit 2** | `context.py:518-605` | `FutureConversationRetrievalPort` and `RetrievalContextSource` are defined but not wired in the default profile. This is expected per sprint exclusion, but the port remains ready for parallel RAG work. |

**Recommendation:** Both notes are acceptable for the first release and aligned with sprint reasoning. No action required now.

---

## 8. Technical Debt / Carried-Forward Risks

| Risk | Area | Mitigation |
|------|------|-----------|
| Profile configuration drift | Configuration | Validate profile IDs exist at startup or clearly error on first use. |
| Optional source silent degradation | Observability | Future profiles using optional sources should surface warnings in run summaries. |
| Retrieval port remains unused | Parallel work | Parallel RAG work must wire retrieval into a specific profile to be used. |

---

## 9. Recommendations For Next Sprint

1. Consider adding a `memory-enabled` profile that wires `FakeLongTermMemoryContextSource` or a real memory source for early testing.
2. Explore using the `budget` field in `AgentContextProfile` to enforce token/message budgets for high-volume sessions.
3. If parallel RAG work lands, wire `RetrievalContextSource` into a profile and verify end-to-end retrieval context appears in assembled messages.

---

## 10. Final Verdict

| Item | Verdict |
|------|--------|
| Conforms to reasoning document | ✅ Yes |
| Conforms to governing contracts | ✅ Yes |
| Evidence supports conclusion | ✅ Yes |
| Must fix before sign-off | **No (blockers: none)** |
| Minor notes | 2 (acceptable) |

**SIGN-OFF GRANTED**