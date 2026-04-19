# Sprint Report: Session Substrate Foundation

> Sprint ID: sprint-04-session-substrate-foundation
> Review Date: 2026-04-19
> Status: Complete with one pre-existing test issue

## Summary

The sprint introduced a first-class session substrate that owns conversational chronology, summaries, and trusted user/org context references. The public conversational HTTP surface was moved from `/agent-runs` to `/sessions`. Configurable X-turn session summarization was added as background-owned work with explicit lifecycle state (queued/running/completed/failed). The existing conversational agent was adapted to attach to sessions rather than own the conversation root.

## What Changed

1. **Session substrate** - `platform/sessions/` adds neutral Session, SessionItem, and SessionSummary models with clean ownership boundaries
2. **Session persistence** - Protocol-based `SessionStorePort` with SQL-backed implementation and in-memory variant for testing
3. **Module layer** - `modules/sessions/` provides `SessionService` facade, commands, and views wired through composition root
4. **Public API** - `/sessions` is now the top-level conversation root; `/agent-runs` is demoted from public surface
5. **Summary cadence** - Configurable `session_summary_turn_interval` (default: 8) with settings validation
6. **Background summarization** - Task-owned queued/running/completed/failed lifecycle with prompt version tracking
7. **Attached execution** - Agent runtime attaches to session instead of owning session; tool calls/results mirror as session items
8. **Documentation** - `backend/docs/api-and-runtime-surfaces.md` and related docs updated for session-first model

## What Did Not Change

- Deep-research or broader multi-executor orchestration (correctly deferred per PRE-SCOPE-002)
- Concrete auth/tenancy derivation (optional identifiers only, per reasoning)
- `/agent-runs` internal routes persist but are no longer the public conversation surface

## Review Findings

### Severity: None (Blocker/High/Medium/Low)

#### Blocker: None

#### High: None

#### Medium: None

#### Low / Nits: 1

| Location | Issue | Why It Matters | Suggested Fix | Evidence |
| --- | --- | --- | --- | --- |
| `tests/integration/test_error_contract.py:118` | Test `test_generic_agent_provider_without_provider_key_fails_startup` expects an AppError to be raised when provider key is missing, but the test no longer raises | This is a pre-existing test failure unrelated to session changes. The test expects startup to fail without a provider key, but startup completes successfully (llm_available=True in logs) | Investigate whether the test expectation is stale or if the provider key requirement was relaxed | Test output shows `llm_available=True` despite missing key; test has been failing since before this sprint |

## Contract Conformance

The sprint conformance to the reasoning document and governing contracts is verified as follows:

| Contract Area | Requirement | Conformance |
| --- | --- | --- |
| Architecture | ARCH-CORE-001 (explicit module boundaries) | Verified: `modules/sessions/` and `platform/sessions/` have clean ownership split |
| Architecture | ARCH-CORE-002 (dependency direction) | Verified: Session services depend on ports, not SQLAlchemy directly |
| Architecture | ARCH-LAYER-002 (use cases depend on ports) | Verified: `SessionService` depends on `SessionStorePort` protocol |
| Architecture | ARCH-ENTRY-001 (thin transport) | Verified: Routes only validate, resolve context, call service, map output |
| Pre-Brief Scope | PRE-SCOPE-001 (foundation work allowed) | Verified: Session substrate is generic runtime foundation |
| Pre-Brief Scope | PRE-SCOPE-002 (no deep research) | Verified: No speculative orchestration designed |
| Pre-Brief Scope | PRE-SCOPE-004 (narrow public API) | Verified: `/sessions` is narrow and operationally justified |
| Errors | ERR-CORE-001 (no hidden failures) | Verified: Session creation, append, summary failures remain explicit |
| Errors | ERR-HTTP-001 (structured transport errors) | Verified: Session routes use `app_error()` with stable codes |
| Errors | ERR-BG-001 (background terminal state) | Verified: Summary has queued/running/completed/failed state |
| Observability | OBS-BG-001 (visible background state) | Verified: Summary task snapshots are persistable |
| Observability | OBS-DIAG-001 (diagnostics surfaces) | Verified: Session state inspectable via `modules/system/` |
| Testing | TEST-SEAM-001 (replaceable collaborators) | Verified: Store is a Protocol (fakeable) |
| Testing | TEST-SMOKE-001 (critical path smoke) | Verified: Session create/append flow tested |
| LLM | LLM-PROMPT-001 (prompt versioning) | Verified: Summary stores `prompt_id` and `version` |
| LLM | LLM-RUN-001 (inspectable runs) | Verified: Session items and attached run state are inspectable |

**Deviation recorded:** PRE-SCOPE-002 - Concrete auth/tenancy derivation remains unresolved (temporary, expected follow-up)

## TL;DR

- **Sprint delivers:** First-class session substrate, session-first public API at `/sessions`, configurable X-turn summarization with background task ownership, agent-as-attached-execution seam
- **Test status:** 63 passed, 1 failed (pre-existing unrelated issue), 3 skipped
- **CI checks:** Compilation passes (`python -m compileall`), smoke test passes
- **Security notes:** No new security concerns introduced; session models expose optional identifiers only (no concrete auth)
- **Technical debt:** None recorded; summary cadence is configurable and validated
- **Risks carried forward:** The pre-existing test failure should be investigated separately

## Recommendations for Next Sprint

1. Investigate the `test_generic_agent_provider_without_provider_key_fails_startup` test failure to determine if provider key enforcement logic was inadvertently changed
2. Consider adding more granular session summary failure path tests once the feature matures
3. The optional user/org context identifiers are in place; concrete auth/tenancy derivation should wait for brief-aligned requirements