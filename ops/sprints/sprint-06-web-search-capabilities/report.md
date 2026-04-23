# Sprint Review Report: Web Search Capabilities

> Sprint ID: sprint-06-web-search-capabilities
> Review Date: 2026-04-23

## Intent Summary

**Changed:** Provider-neutral `platform/web_search/` contracts, Tavily adapter, `modules/web_search/` service, `search_web` agent tool, prompt v6, diagnostics/readiness extensions, unit/integration/smoke tests, real-provider smoke passed.

**Unchanged:** No public HTTP routes; no workflow/fanout; no sales-specific research logic; observer profile does not expose `search_web`.

**Top risk:** Private data sent to third-party search provider -- mitigated by prompt policy, strict tool description, optional approval gate, and bounded input validation.

---

## Findings

### Blockers
*None.*

### High
*None.*

### Medium

1. **Missing negative-path unit tests for Tavily HTTP error mapping**
   - **Location:** `backend/tests/unit/test_web_search.py`
   - **Issue:** Only 429 (`rate_limit`) is tested. Timeout, 401/403, >=500, and malformed response paths are not unit-tested despite the reasoning document explicitly requiring them.
   - **Fix:** Add three short `httpx.MockTransport` tests for 408/timeout, 401, and 500 responses asserting `AppError.code` and `retryable`. Add one malformed-body test.

2. **Startup log omits web-search provider state**
   - **Location:** `backend/src/hello_sales_backend/platform/composition/startup.py:77-84`
   - **Issue:** Startup completion logs `llm_provider` and `llm_available` but not `web_search_provider` / `web_search_available`.
   - **Fix:** Add those two fields to the startup log and startup event payload.

### Low / Nits

3. **Prompt version jump from v3 to v6 is non-monotonic in the same file**
   - **Location:** `backend/src/hello_sales_backend/application/agents/definitions/generic_agent/prompts.py`
   - **Issue:** Static `GENERIC_AGENT_RESPONSE_PROMPT` remains `v3` while the active builder returns `v6`.
   - **Fix:** Remove the unused static prompt or align its version.

4. **Tavily registry test lives in the wrong file**
   - **Location:** `backend/tests/unit/test_web_search.py`
   - **Issue:** `test_provider_registry_builds_tavily_adapter_from_settings` belongs in `test_provider_registry.py`.
   - **Fix:** Move the test.

---

## Contract Adherence

| Requirement | Status | Evidence |
|---|---|---|
| PRE-SCOPE-001 / 003 / 004 | Pass | One narrow tool + neutral substrate. |
| PRE-SCOPE-002 | Pass | No sales-specific workflows. |
| ARCH-CORE-001 / LAYER-002 / COMP-001 / SHARED-001 | Pass | Clean module/service/tool layering; provider details stay in adapter. |
| ERR-CORE-001 / PROVIDER-001 / TRANS-001 / REDACT-001 | Pass | Stable error codes, redacted logs, preserved remote context. |
| OBS-CORE-001 / CORR-001 / DIAG-001 | Pass | Diagnostics show `kind=web_search`; trace/request metadata flow through `WebSearchCallContext`. |
| TEST-SMOKE-002 | Pass | Tracker records real Tavily smoke completed. |
| WF-SCOPE-001 / STATE-001 / RETRY-001 | Pass | Fanout documented, not implemented. |
| LLM-TOOL-001 / LIFECYCLE-001 / RUN-001 / PROMPT-001 / EXPOSE-001 | Pass | Strict native tool, persisted lifecycle, prompt v6, explicit tool description. |

**Deviations:** None. Fanout deferral matches planned temporary deviation.

---

## Design & Correctness

- **Security:** No injection paths; keys redacted in logs; query validated before external call.
- **Availability:** Readiness fails only if `web_search_required=true` and misconfigured. Default is optional/degraded.
- **Layering:** `platform/` -> `modules/` -> `application/tools/` is inward-pointing and fakeable.
- **Failure mapping:** Timeout, auth, rate-limit, remote 5xx, malformed response, and not-configured codes are all implemented.
- **Resource management:** `TavilyWebSearchProvider.aclose()` closes self-owned client; `ProviderRegistry.aclose()` delegates to both providers; `shutdown_container` calls it.

---

## Testing & CI

| Check | Status |
|---|---|
| ruff | Pass |
| mypy | Pass |
| compileall | Pass |
| Unit + Integration (non-Postgres) | 92 passed, 2 skipped, 2 deselected |
| Postgres tests | Skipped locally (no Postgres) |
| Real-provider smoke | Passed with Tavily |

**Coverage gap:** Negative-path Tavily error mappings need unit tests (see Medium #1).

---
K
## Documentation

- `backend/docs/web-search.md` -- present and accurate.
- `backend/docs/configuration-and-environment.md` -- updated with provider settings.
- `backend/docs/agent-runtime.md` -- updated with tool policy and lifecycle.
- `backend/docs/README.md` -- lists the new doc.

---

## TL;DR

Sprint 6 is **ready for sign-off** with minor follow-ups. The architecture is clean, the contract boundaries are respected, and real-provider smoke passed. Add the missing Tavily HTTP error unit tests and the startup log fields before the next sprint starts.

---

## Recommendations For Next Sprint

1. **Add missing Tavily negative-path tests** (timeout, auth, 5xx, malformed response).
2. **Add startup log fields** for web-search provider status.
3. **Plan Sprint 7 fanout/research seam:** define `WebSearchBatchService.search_many()` or a `ResearchWebWorkflow` with concurrency limits, per-query status, partial-failure semantics, cancellation, and retry budgets. Reuse the existing `WebSearchService.search()` primitive without changing the single-query `search_web` tool contract.
