# Sprint Tracker: Web Search Capabilities

> Project: HelloSales
> Sprint ID: sprint-06-web-search-capabilities
> Created: 2026-04-23

## Sprint Overview

- **Sprint Name:** Web Search Capabilities
- **Sprint Focus:** Add provider-neutral web search primitives and one strict `search_web` agent tool, with explicit provider wiring, observability, tests, and a future path for fanout/research orchestration.
- **Depends On:** `ops/sprints/done/sprint-01-observability-foundation/tracker.md`, `ops/sprints/done/sprint-02-worker-runtime-foundation/tracker.md`, `ops/sprints/done/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/done/sprint-05-governed-sql-tool/tracker.md`
- **Status:** Complete

## Sprint Goals

- **Primary Goal:** Ship one provider-neutral web search primitive and one explicit `search_web` agent tool that can answer public/current-information questions while preserving strict schemas, provider error mapping, diagnostics, and persisted tool lifecycle.
- **Secondary Goals:**
  - Add one concrete provider adapter, preferably Tavily if credentials are available, behind a replaceable `WebSearchProviderPort`.
  - Add a module-owned `WebSearchService.search()` primitive for use by agent tools now and workflows later.
  - Update generic-agent prompt policy and versioning so the model distinguishes public web search from governed internal analytics SQL.
  - Record the future fanout/research seam without implementing premature workflow orchestration in this sprint.

## Execution Checklist

- [x] **Task 1: Formalize web search provider substrate**
  > *Description: Add provider-neutral runtime contracts, settings, diagnostics, and one concrete adapter for public web search.*
  - [x] **Sub-task 1.1:** Add `platform/web_search/` contracts for request, response, result, context, provider port, and noop provider.
  - [x] **Sub-task 1.2:** Add web search settings for provider selection, API keys, timeout, max results, required/readiness policy, and approval policy.
  - [x] **Sub-task 1.3:** Extend `ProviderRegistry`, app overrides, close lifecycle, diagnostics, and readiness/degraded reporting for web search.
  - [x] **Sub-task 1.4:** Implement the first concrete provider adapter, preferably Tavily, with normalized results and stable `AppError` mapping.

- [x] **Task 2: Add the web-search application primitive**
  > *Description: Introduce a module-owned service primitive that workflows and tools can call without depending on provider adapters.*
  - [x] **Sub-task 2.1:** Add `modules/web_search/` bootstrap, service/facade, commands, views, and use-case ports.
  - [x] **Sub-task 2.2:** Implement command validation for query length, reason, result limits, search depth/topic, time range, and domain filters.
  - [x] **Sub-task 2.3:** Preserve request, trace, and actor metadata through the service and provider call context.
  - [x] **Sub-task 2.4:** Return normalized source objects and metadata only; do not synthesize final answers in the service.

- [x] **Task 3: Expose `search_web` as one native agent tool**
  > *Description: Register one strict agent tool that calls the web-search service through the existing tool lifecycle.*
  - [x] **Sub-task 3.1:** Add `application/tools/web_search.py` with a strict Pydantic argument schema and bounded output shape.
  - [x] **Sub-task 3.2:** Register `search_web` on the generic agent tool catalog through normal agent bootstrap dependencies.
  - [x] **Sub-task 3.3:** Make the tool approval stance explicit and configurable through settings.
  - [x] **Sub-task 3.4:** Ensure tool results include source URLs, snippets/content where available, provider metadata, and enough information for citation.

- [x] **Task 4: Update agent prompt policy and documentation**
  > *Description: Teach the generic agent when and how to use public web search without leaking private or internal data.*
  - [x] **Sub-task 4.1:** Update the generic-agent system prompt and bump the prompt version.
  - [x] **Sub-task 4.2:** State that `search_web` is for public/current web information and that governed SQL remains preferred for approved internal analytics data.
  - [x] **Sub-task 4.3:** State that the agent must not send secrets, private customer data, or internal-only data to search providers.
  - [x] **Sub-task 4.4:** Update backend docs for provider setup, agent behavior, diagnostics, and real-provider smoke expectations.

- [x] **Task 5: Preserve operational visibility and failure semantics**
  > *Description: Make search provider calls and failures inspectable through canonical error, diagnostics, and observability surfaces.*
  - [x] **Sub-task 5.1:** Emit stable provider error codes for disabled provider, timeout, rate limit, authentication failure, remote 5xx, malformed response, and configuration failure.
  - [x] **Sub-task 5.2:** Redact API keys and safely handle query text in logs/error details without destroying diagnosis.
  - [x] **Sub-task 5.3:** Ensure diagnostics expose search provider configured/degraded/available status.
  - [x] **Sub-task 5.4:** Confirm agent run/session/tool-call inspection remains sufficient to diagnose search behavior.

- [x] **Task 6: Add verification and smoke coverage**
  > *Description: Prove the search capability through deterministic tests, centralized smoke coverage, and real-provider verification or explicit deferral.*
  - [x] **Sub-task 6.1:** Add unit tests for settings, provider registry, noop provider, provider adapter normalization, and error mapping.
  - [x] **Sub-task 6.2:** Add unit tests for `WebSearchService` command validation and fake-provider behavior.
  - [x] **Sub-task 6.3:** Add integration tests for composition, diagnostics, tool registration, and tool execution through the agent runtime.
  - [x] **Sub-task 6.4:** Add a centralized smoke scenario for the generic agent using `search_web`.
  - [x] **Sub-task 6.5:** Run a real-provider web-search smoke or explicitly record a justified deferral with the missing credential/setup reason.

- [x] **Task 7: Record future fanout/research follow-up**
  > *Description: Leave a clear extension path for subagent fanout without shipping premature orchestration.*
  - [x] **Sub-task 7.1:** Document a future `WebSearchBatchService.search_many()` or `ResearchWebWorkflow` seam.
  - [x] **Sub-task 7.2:** Record required fanout semantics: concurrency limit, per-query status, partial failures, cancellation, retry budget, and provider metadata.
  - [x] **Sub-task 7.3:** Keep fanout out of Sprint 6 implementation unless the tracker is explicitly revised.

## Testing And Documentation Checklist

- [x] **Unit Tests:** deterministic coverage for settings, provider registry, provider adapter normalization, command validation, service behavior, tool schema, and failure mapping
- [x] **Integration Tests:** composition, diagnostics, agent tool registration, persisted tool lifecycle, and provider disabled/degraded behavior
- [x] **Smoke Tests:** centralized generic-agent smoke exercises `search_web` through the runtime
- [x] **Real Provider Smoke:** run one real-provider web-search smoke or record explicit justified deferral
- [x] **Documentation Updates:** update canonical backend docs for web search provider setup, agent behavior, and operational verification

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Provider choice gets hard-coded into service/tool contracts | High | Keep Tavily/Brave/Exa details inside adapters and normalize through provider-neutral models | Mitigated |
| The agent sends private or internal data to a third-party search provider | High | Add prompt policy, concise tool description, optional approval config, and tests/review checks for tool scope | Mitigated |
| Search tool competes with governed SQL for internal analytics questions | Medium | Prompt policy must route public/current web information to search and approved internal analytics to SQL | Mitigated |
| Real-provider smoke cannot run because no search API key is configured | High | Add env-gated smoke and record explicit deferral if credentials are unavailable | Mitigated: Tavily smoke passed |
| Fanout is implemented prematurely without explicit workflow state/retry/cancellation semantics | Medium | Keep fanout as documented follow-up unless tracker scope is intentionally revised | Mitigated |
| Provider result shape changes or includes malformed data | Medium | Normalize defensively and test malformed/missing fields with stable provider errors | Mitigated |

## Success Criteria

- [x] **Success Criteria 1:** The app has a provider-neutral web search substrate and one concrete provider adapter behind explicit settings and diagnostics.
- [x] **Success Criteria 2:** `modules/web_search/` exposes a reusable `WebSearchService.search()` primitive with fakeable provider seams and normalized source results.
- [x] **Success Criteria 3:** The generic agent can call one strict `search_web` tool through the existing native tool-calling runtime and persisted lifecycle.
- [x] **Success Criteria 4:** Provider failures, disabled/degraded state, correlation metadata, and redaction are covered by stable tests and operational surfaces.
- [x] **Success Criteria 5:** Documentation and tracker evidence clearly distinguish Sprint 6 MVP search from future fanout/research orchestration.

## Review And Sign-Off

- Sprint Status: Complete
- Completion Date: 2026-04-23

## Execution Evidence

- Sprint artifacts created from:
  - `ops/process/reasoning/reasoning-protocol.md`
  - `ops/process/reasoning/reasoning-template.md`
  - `ops/process/execute/tracker-template.md`
- Provider research summary captured in `reasoning.md`.
- Implementation branch: `sprint/sprint-06-web-search-capabilities`
- Implemented provider-neutral substrate in `backend/src/hello_sales_backend/platform/web_search/` with no-op and Tavily adapters.
- Implemented reusable module primitive in `backend/src/hello_sales_backend/modules/web_search/`.
- Registered strict generic-agent `search_web` tool and bumped generic prompt version to `v6`.
- Added centralized smoke registry entry: `generic-agent-provider-web-search`.
- Added backend docs: `backend/docs/web-search.md`, plus updates to configuration and agent runtime docs.
- Verification commands:
  - `python -m compileall backend/src/hello_sales_backend` passed.
  - `cd backend && PYTHONPATH=src ruff check .` passed.
  - `cd backend && PYTHONPATH=src mypy src` passed.
  - `cd backend && PYTHONPATH=src pytest tests/unit/test_web_search.py tests/unit/test_provider_registry.py tests/integration/test_web_search_tool.py` passed: 8 passed before the final unsupported-provider settings test was added; the full non-Postgres suite below includes that added test.
  - `cd backend && PYTHONPATH=src python -m hello_sales_backend.smoke --list` passed and listed `generic-agent-provider-web-search`.
  - `cd backend && PYTHONPATH=src pytest -m 'not postgres'` passed: 92 passed, 2 skipped, 2 deselected.
  - `cd backend && PYTHONPATH=src pytest -m postgres` ran: 2 skipped, 93 deselected because local Postgres-dependent tests self-skipped.
  - `cd backend && timeout 180 env HELLO_SALES_WEB_SEARCH_PROVIDER=tavily PYTHONPATH=src python -m hello_sales_backend.smoke generic-agent-provider-web-search` passed with real providers.
- Real-provider web-search smoke evidence:
  - `HELLO_SALES_TAVILY_API_KEY` was present in `backend/.env`.
  - `HELLO_SALES_WEB_SEARCH_PROVIDER=tavily` was supplied for the smoke command because provider selection was not set in `backend/.env`.
  - Smoke result: `status=completed`, LLM provider `groq`, model `openai/gpt-oss-20b`.
  - Search tool lifecycle persisted `search_web` tool call and result.
  - Tavily result evidence: `tool_name=search_web`, `source_count=5`, `provider=tavily`.
