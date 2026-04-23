# Sprint Reasoning: Web Search Capabilities

> Project: HelloSales
> Sprint ID: sprint-06-web-search-capabilities
> Output: `ops/sprints/sprint-06-web-search-capabilities/reasoning.md`

## Overview

**Sprint:** Web Search Capabilities
**Purpose:** Add provider-neutral web search capabilities for the agent and reusable workflow primitives, while preserving explicit tool lifecycle, replaceable provider adapters, operational visibility, and a clean path toward later subagent fanout or research orchestration.
**Tracker:** `ops/sprints/sprint-06-web-search-capabilities/tracker.md`
**Depends On:** `ops/sprints/sprint-01-observability-foundation/tracker.md`, `ops/sprints/sprint-02-worker-runtime-foundation/tracker.md`, `ops/sprints/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/sprint-05-governed-sql-tool/tracker.md`

This sprint introduces public-web search as a bounded capability, not as hidden model behavior.
The first deliverable is intentionally narrow:
- one provider-neutral web search service primitive
- one concrete provider adapter
- one strict agent tool, `search_web`
- provider diagnostics, failure mapping, and test/smoke coverage
- an explicit design seam for later batch search, fanout, and research workflows

This sprint does not implement subagent fanout.
Fanout has real orchestration semantics and should be designed after the base search primitive exists.
The MVP should expose a stable `WebSearchService.search()` primitive that a later `WebSearchBatchService` or `ResearchWebWorkflow` can compose without changing the agent tool contract.

## Requirement Map

### Contract Coverage Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/architecture.md` | Layering, provider boundaries, composition | Applicable | Web search adds a provider-backed bounded capability and must not leak adapter details into routes, agent runtime, or workflows. |
| `ops/operational-contract/errors.md` | Provider failures, redaction, startup/readiness, error shape | Applicable | Search provider failures, rate limits, authentication failures, timeout, and unsafe query handling need stable codes and inspectable context. |
| `ops/operational-contract/observability.md` | Correlation, diagnostics, provider visibility | Applicable | Search calls cross an external dependency boundary and must preserve request/trace metadata and operational signals. |
| `ops/operational-contract/testing.md` | Unit, integration, smoke, real-provider verification | Applicable | The sprint adds a supported external-provider path and an agent tool path. |
| `ops/operational-contract/workflows.md` | Workflow eligibility and orchestration boundaries | Applicable | The base search call is not a workflow, but later fanout/research orchestration must have explicit lifecycle semantics. |
| `ops/operational-contract/llm.md` | Tool boundaries, lifecycle, prompt versioning, runtime exposure | Applicable | Search is exposed to the conversational agent through native tool calling and must remain an explicit inspectable tool. |
| `ops/operational-contract/pre-brief-scope.md` | Foundation vs product-specific scope | Applicable | Web search is generic runtime scaffolding, but product-specific research workflows and CRM search semantics should not be invented yet. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | Provider-neutral public-web search is reusable runtime foundation. |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | Pre-Brief Scope | Applicable | The sprint must not define sales-specific lead research or CRM enrichment policy. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | A replaceable search provider port and reusable service primitive are safer than bespoke product workflows. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | The sprint should add one narrow tool and service primitive, not a broad research product API. |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | Search behavior needs an explicit module/service owner and a neutral provider layer. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Application services depend on search ports, not concrete HTTP adapters. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | `WebSearchService` should accept a provider port and fake cleanly in tests. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Non-Applicable | No new HTTP route is required in the MVP. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | A new module should expose only service, command, and result views if a module is introduced. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | Provider and module wiring must happen in the app container/provider registry. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | Search provider contracts can be platform-neutral; agent/tool policy belongs outside platform. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Search timeouts, auth failures, rate limits, malformed provider responses, and disabled provider state must be explicit. |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | Errors | Applicable | Provider errors must include stable code, category, retryability, provider metadata, and correlation. |
| ERR-CODE-001 | Error codes must be stable and machine-usable | Errors | Applicable | Operators must distinguish search timeout, rate limit, auth failure, remote 5xx, and configuration failures. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | HTTP/provider exceptions must be normalized without losing remote status, request id, or endpoint context. |
| ERR-STARTUP-001 | Known-fatal startup failures must fail before traffic | Errors | Ambiguous | Search may be optional in development but required when explicitly configured for production; settings need clear readiness semantics. |
| ERR-PROVIDER-001 | Provider failures must remain classified and observable | Errors | Applicable | Search is an external provider path. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | API keys and potentially sensitive query text must be redacted carefully in logs and error details. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Provider failures and degraded search availability must be visible. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Agent run/turn metadata must flow into provider calls. |
| OBS-HEALTH-001 | Health endpoints must reflect operational truth | Observability | Applicable | Readiness/diagnostics should show search provider configured/degraded/disabled state. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | System diagnostics should include search provider availability. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Repeated provider failures should have stable codes and provider labels. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Search service, provider adapter, and agent tool must be testable with fake providers. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Query validation, provider normalization, result shaping, and error mapping are deterministic. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable | Composition, provider registry, diagnostics, and agent tool wiring need integration tests. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | The agent should be able to call the search tool through the centralized smoke harness. |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | Testing | Applicable | A real-provider web search smoke is required or must be explicitly deferred with justification. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Disabled provider, invalid arguments, timeout, rate limit, auth failure, and malformed provider payloads need negative tests. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Tests should assert normalized structure and lifecycle state, not provider wording. |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | Workflows | Applicable | Single search calls are not workflows; future fanout/research may be. |
| WF-BOUNDARY-001 | Workflow engines must stay behind app-owned boundaries | Workflows | Applicable | Later fanout must compose service primitives through app-owned workflow boundaries. |
| WF-STATE-001 | Workflow outcomes must be explicit and inspectable | Workflows | Applicable For Later Fanout | Batch/fanout search needs per-query status and partial-failure state when implemented. |
| WF-RETRY-001 | Retry and cancellation semantics must be explicit | Workflows | Applicable For Later Fanout | Research/fanout retries and cancellation must be bounded and observable later. |
| LLM-BOUNDARY-001 | Shared substrate, runtime mechanics, and mode-specific policy must stay separated | LLM Runtime | Applicable | Search provider mechanics belong in neutral provider code; agent prompt/tool policy belongs in application definitions. |
| LLM-TOOL-001 | Tool execution boundaries must stay explicit and mode-scoped | LLM Runtime | Applicable | Search must be an explicit native tool with strict schema and persisted lifecycle. |
| LLM-LIFECYCLE-001 | Lifecycle controls must stay explicit and inspectable | LLM Runtime | Applicable | Search approval stance, retry behavior, and provider failure states must be visible. |
| LLM-RUN-001 | Runs and events must be durable or inspectable | LLM Runtime | Applicable | Search tool calls/results must remain in run/turn/session history. |
| LLM-PROMPT-001 | Prompts must be explicitly versioned and version propagation must stay observable | LLM Runtime | Applicable | Adding web search changes agent behavior and requires prompt version bump. |
| LLM-EXPOSE-001 | Operational exposure must flow through application modules | LLM Runtime | Applicable | Search should flow through service/tool definitions, not direct transport/runtime internals. |
| LLM-OBS-001 | LLM runtime monitoring must reuse the canonical observability runtime | LLM Runtime | Applicable | Search tool monitoring should reuse existing agent/provider observability patterns. |

### Applicable Requirements

- **PRE-SCOPE-001 / PRE-SCOPE-003 / PRE-SCOPE-004:** Web search is valid foundation work if scoped to a provider-neutral primitive and one narrow agent tool.
- **PRE-SCOPE-002:** The sprint must not design sales-specific lead research, enrichment, or outreach workflows before the product brief requires them.
- **ARCH-CORE-001 / ARCH-LAYER-002 / ARCH-COMP-001:** Search service ownership and provider wiring must be explicit, fakeable, and composed through the normal app container/provider registry.
- **ERR-CORE-001 / ERR-PROVIDER-001 / ERR-TRANS-001 / ERR-REDACT-001:** Search provider calls need classified failures, preserved remote context, bounded retryability, and safe redaction.
- **OBS-CORE-001 / OBS-CORR-001 / OBS-DIAG-001:** Search provider calls and degradation need structured, correlated operational visibility.
- **TEST-SMOKE-002:** Because search is a supported external-provider path, at least one real-provider smoke should exist or an explicit justified deferral must be recorded.
- **WF-SCOPE-001 / WF-STATE-001 / WF-RETRY-001:** The MVP search call should not be a workflow, but the design must leave space for later fanout with explicit per-query state and retry semantics.
- **LLM-TOOL-001 / LLM-LIFECYCLE-001 / LLM-RUN-001 / LLM-PROMPT-001:** The agent search capability must be explicit, prompt-versioned, persisted, inspectable, and bounded.

### Non-Applicable Requirements

- **ARCH-ENTRY-001 as a primary driver:** The MVP does not require a new public HTTP route.
- **LLM-IO-001:** The sprint does not add a structured worker output path; local validation still applies to tool arguments and provider normalization, but not as a worker structured-output contract.
- **ERR-HTTP-001 as a primary driver:** No new transport adapter is expected, though existing session/agent routes must continue preserving structured errors.

### Ambiguous Or Conflicting Requirements

- **ERR-STARTUP-001 vs optional search capability:** Search is useful but may not be required for every deployment. The safe interpretation is to make readiness fail only when search is explicitly marked required and misconfigured, while diagnostics should show disabled/degraded state otherwise.
- **LLM-LIFECYCLE-001 vs approval friction:** Web search sends user queries to a third-party provider. Static approval could be safest but would make search cumbersome. The initial stance should be configurable, defaulting to no approval for ordinary public-web searches if query input is validated and prompts prohibit secrets, while allowing `HELLO_SALES_WEB_SEARCH_REQUIRES_APPROVAL=true` for stricter deployments.
- **WF-SCOPE-001 vs later fanout:** Fanout is not justified for one query, but a later research workflow may be justified because it spans multiple provider calls, retries, partial failures, and subagent coordination. The MVP must avoid implementing workflow scaffolding prematurely while designing service primitives that can support it.

### Open Questions

- Which provider key will be available for real-provider smoke in this environment: Tavily, Brave, Exa, or another adapter?
- Should production deployments treat public web search as required readiness or optional degraded capability?
- Should the first agent expose `search_web` only on the generic agent, or also on observer/admin profiles after a separate policy review?

## Feature Analysis

### Feature 1: Provider-Neutral Web Search Substrate

**Description:** Add a neutral search provider contract, response models, provider registry wiring, configuration, diagnostics, and one concrete adapter.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/web_search/`
- `backend/src/hello_sales_backend/platform/composition/providers.py`
- `backend/src/hello_sales_backend/platform/config/settings.py`
- `backend/src/hello_sales_backend/platform/observability/health.py`
- `backend/src/hello_sales_backend/modules/system/`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-SHARED-001 | Provider contracts stay domain-neutral | `platform/web_search/` models and adapters | Import and naming review |
| ARCH-COMP-001 | Provider is wired through composition | provider registry and settings | Unit/integration tests |
| ERR-PROVIDER-001 | Provider failures retain remote context | adapter error mapping | Unit failure tests |
| OBS-DIAG-001 | Search provider state is inspectable | system diagnostics/provider status | Integration tests |
| TEST-SEAM-001 | Provider can be replaced in tests | provider port and app override | Unit/integration tests |

**Current-System Analysis**
- The LLM provider path already uses provider-neutral contracts and an app-level `ProviderRegistry`.
- `ProviderRegistry` currently exposes only `llm` diagnostics, so search should extend this pattern without coupling search to LLMs.
- The existing OpenAI-compatible adapter provides useful precedent for `httpx.AsyncClient`, timeout handling, redaction, and `AppError` mapping.
- What must remain true is that platform search code does not know about agent prompts, sales policy, or workflow-specific fanout behavior.

**Options Considered**
- **Option A:** Use OpenAI built-in web search through the LLM provider path.
- **Option B:** Add a provider-neutral `WebSearchProviderPort` with one concrete adapter.
- **Option C:** Call a search API directly from the agent tool.

**Chosen Approach**
- Adopt Option B. Build a provider-neutral web search substrate and one concrete adapter, with Tavily as the preferred MVP provider if a key is available.

**Decision Justification**
- Option B creates a reusable primitive for workflows and future subagent fanout.
- Option A couples search to one model vendor and makes it harder to reuse search from non-agent workflow code.
- Option C would violate provider and architecture boundaries by burying HTTP/provider behavior inside a tool.
- Tavily is the best MVP fit because its API is designed for agent search and has search-depth, topic, domain, date, raw-content, and usage metadata that map cleanly into normalized result models.
- Brave should be the next adapter if independent-index search or privacy/scale is preferred. Exa can be added later for semantic/deep search. Bing and Google Programmable Search should not be MVP defaults because Bing Search APIs retired on August 11, 2025 and Google Custom Search JSON API is closed to new customers with an existing-customer transition deadline of January 1, 2027.

**Execution Notes**
- Define `WebSearchRequest`, `WebSearchResult`, `WebSearchResponse`, `WebSearchProviderPort`, and `NoopWebSearchProvider`.
- Normalize provider fields into stable output: `title`, `url`, `snippet`, `content`, `published_at`, `score`, `source_provider`, `provider_request_id`, `raw_metadata`.
- Add settings such as `web_search_provider`, `web_search_api_key` or provider-specific key fields, `web_search_timeout_seconds`, `web_search_default_max_results`, `web_search_required`, and `web_search_requires_approval`.
- Add `web_search_provider` to provider diagnostics and readiness/degraded checks.

**Expected Evidence**
- **Tests:** adapter success normalization, timeout/rate-limit/auth/5xx mapping, settings resolution, provider registry diagnostics, disabled-provider behavior.
- **Runtime Evidence:** diagnostics show provider name, configured state, and availability; errors include provider, endpoint, status code, provider request id when available, timeout, and retryability.
- **Review Checks:** no agent or workflow policy is embedded in the platform provider adapter.

---

### Feature 2: Web Search Application Primitive

**Description:** Add an application-owned `WebSearchService.search()` primitive that validates commands, calls the provider port, normalizes results, and exposes a stable interface for agent tools and future workflows.

**Affected Areas**
- `backend/src/hello_sales_backend/modules/web_search/`
- `backend/src/hello_sales_backend/platform/composition/app_container.py`
- `backend/src/hello_sales_backend/platform/composition/module_registry.py`
- `backend/src/hello_sales_backend/platform/composition/overrides.py`

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-CORE-001 | Search use-case behavior has explicit ownership | `modules/web_search/` | File layout/import review |
| ARCH-LAYER-002 | Service depends on ports, not HTTP adapters | service constructor | Unit tests with fake provider |
| PRE-SCOPE-003 | Primitive stays reusable and product-neutral | command/view shapes | Review and tests |
| WF-SCOPE-001 | Avoid premature workflow engine usage | service method, no workflow for single search | Review |
| TEST-UNIT-001 | Deterministic validation/output shaping is covered | command validation/result mapping | Unit tests |

**Current-System Analysis**
- Sprint 5’s analytics query tool established a pattern: application tools should be thin adapters over a module-owned service.
- Future workflows need primitives that can be called without depending on native agent tool definitions.
- What must remain true is that direct provider calls are not scattered across tools or workflows.

**Options Considered**
- **Option A:** Skip a module and expose only a platform provider plus an agent tool.
- **Option B:** Add a `modules/web_search/` service primitive over the provider port.
- **Option C:** Put workflow-friendly helpers in `platform/workflows/`.

**Chosen Approach**
- Adopt Option B. Add a small `web_search` bounded context with command/view models and a service facade over the provider port.

**Decision Justification**
- Option B gives workflows a stable primitive without forcing every caller to understand provider-specific request fields.
- Option A would work for the first agent tool but would make later fanout code depend on provider details or duplicate normalization.
- Option C would blur orchestration and business/application capability boundaries.
- The module should stay small: command validation, policy-neutral limits, provider call orchestration, result normalization, and failure translation.

**Execution Notes**
- Use `SearchWebCommand` fields such as `query`, `reason`, `max_results`, `topic`, `time_range`, `include_domains`, `exclude_domains`, `country`, `search_depth`, and `include_raw_content`.
- Enforce query length and result limits locally before provider calls.
- Preserve request/trace/actor metadata through a `WebSearchCallContext`.
- Do not synthesize an answer in the service; return normalized source objects and metadata only.

**Expected Evidence**
- **Tests:** fake-provider service tests for validation, max-results clamping, provider disabled state, provider failure propagation, and normalized views.
- **Runtime Evidence:** service call events or provider logs preserve request and trace identifiers.
- **Review Checks:** future workflow code can call the service primitive without importing an adapter or agent tool.

---

### Feature 3: `search_web` Agent Tool And Prompt Policy

**Description:** Expose the search primitive to the generic agent as one strict native tool and update prompt policy so the agent uses public web search only when appropriate.

**Affected Areas**
- `backend/src/hello_sales_backend/application/tools/web_search.py`
- `backend/src/hello_sales_backend/application/agents/bootstrap.py`
- `backend/src/hello_sales_backend/application/agents/definitions/generic_agent/tools.py`
- `backend/src/hello_sales_backend/application/agents/definitions/generic_agent/prompts.py`
- agent runtime tests and smoke suites

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-TOOL-001 | Search is explicit native tool | tool definition and registration | Runtime/tool tests |
| LLM-LIFECYCLE-001 | Approval stance is explicit | tool `requires_approval` from config | Unit/integration tests |
| LLM-RUN-001 | Tool calls/results are inspectable | existing persisted tool lifecycle | Integration/smoke tests |
| LLM-PROMPT-001 | Prompt behavior change is versioned | generic prompt version bump | Prompt metadata review |
| ERR-REDACT-001 | Prompt prohibits leaking secrets to search | system prompt/tool description | Review and tests where possible |
| TEST-SMOKE-001 | Critical agent path is smoke-tested | centralized smoke scenario | Smoke evidence |

**Current-System Analysis**
- Agent tools already use strict Pydantic schemas and are sorted into provider-facing definitions.
- Tool calls are persisted, replayed, and appended to session history by the existing runtime.
- The generic prompt currently says the only external capability is governed analytics SQL; that must be updated or the model will underuse/avoid the search tool.
- What must remain true is that internal analytics questions still prefer `query_analytics_data`; public/current information uses `search_web`.

**Options Considered**
- **Option A:** Add search only to prompts and let the LLM provider do native web search if supported.
- **Option B:** Add one strict `search_web` native tool that calls `WebSearchService`.
- **Option C:** Add multiple tools immediately, such as `search_web`, `fetch_page`, `research_web`, and `search_news`.

**Chosen Approach**
- Adopt Option B. Add one `search_web` tool now and defer additional browsing/fetch/research tools until there is concrete need.

**Decision Justification**
- Option B preserves explicit lifecycle and avoids hidden provider behavior.
- Option A would not create reusable workflow primitives and would weaken inspectability.
- Option C adds tool-selection complexity before the base primitive has been proven.
- The agent should receive source objects and answer with citations grounded in the returned URLs. The tool should not return synthesized claims as authoritative without URLs.

**Execution Notes**
- Tool args should mirror the service command but stay concise and model-friendly.
- Tool description should say: use for public/current web information; do not use for private/customer/internal data; cite returned URLs; use governed SQL for approved internal analytics data.
- Prompt version should bump from the current generic agent prompt version.
- Consider default `requires_approval=False` with a config override for deployments that require approval before any third-party search call.

**Expected Evidence**
- **Tests:** tool schema strictness, tool execution through fake service/provider, provider argument validation failure, prompt metadata version change, runtime tool-call completion.
- **Runtime Evidence:** agent run/turn/tool-call history includes `search_web` arguments and result metadata.
- **Review Checks:** prompt policy clearly separates public web search from internal analytics SQL and prohibits sending secrets/private data to search.

---

### Feature 4: Future Fanout And Research Extension Seams

**Description:** Design but do not fully implement the seam for later subagent fanout and research workflows.

**Affected Areas**
- `modules/web_search/use_cases/ports.py`
- `modules/web_search/use_cases/web_search_service.py`
- optional docs under `backend/docs/`
- sprint follow-up notes

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| WF-SCOPE-001 | Do not use workflows for one search | MVP scope | Review |
| WF-STATE-001 | Future fanout must have explicit per-query state | service/result model extensibility | Design notes |
| WF-RETRY-001 | Future retries/cancellation must be explicit | follow-up workflow contract | Tracker follow-up |
| TEST-SEAM-001 | Batch/fanout can reuse fakeable primitive | service/provider port shape | Unit tests |

**Current-System Analysis**
- The platform already has a workflow runtime and background task runner, but contracts warn against workflows for trivial one-step logic.
- A fanout system will likely need sub-query planning, parallel provider calls, partial-failure handling, cancellation, retry budgets, and possibly subagent ownership.
- What must remain true is that the MVP does not hard-code a fanout shape that later conflicts with actual research requirements.

**Options Considered**
- **Option A:** Implement subagent fanout in Sprint 6 with search.
- **Option B:** Implement only single-search primitive but shape commands/results to support later batch composition.
- **Option C:** Ignore future fanout entirely and design only for the immediate agent tool.

**Chosen Approach**
- Adopt Option B. Record the fanout seam and future workflow requirements, but ship only the base primitive and tool.

**Decision Justification**
- Option B keeps Sprint 6 deliverable and reviewable while avoiding a premature orchestration design.
- Option A would violate workflow scope discipline because fanout requirements are not yet concrete.
- Option C would create a likely refactor by baking provider-specific or single-agent assumptions into the service.

**Execution Notes**
- Keep normalized results source-centric and provider-neutral.
- Add command fields that batch/fanout can reuse later, such as domain filters, time range, topic, and depth.
- Document a future `WebSearchBatchService.search_many()` or `ResearchWebWorkflow` with per-query status, retry budgets, and partial-failure semantics, but do not implement it unless explicitly added to sprint scope.

**Expected Evidence**
- **Tests:** the MVP service is fakeable and does not depend on runtime agent state.
- **Runtime Evidence:** none beyond the MVP.
- **Review Checks:** tracker records fanout as a follow-up, not a hidden half-implementation.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| TEST-SMOKE-002 | Real-provider smoke may be deferred if no search API key is available in the execution environment | External provider credentials may not exist locally | A provider adapter could pass mocked tests but fail against real API details | Temporary only if needed | Add env-gated real-provider smoke and record exact deferral reason if not run |
| WF-STATE-001 / WF-RETRY-001 | Fanout workflow state and retry semantics are designed but not implemented in Sprint 6 | MVP should prove the base search primitive before orchestration | Later fanout still requires a separate design pass | Temporary | Create Sprint 7 or follow-up tracker item for batch/fanout/research orchestration |

## Cross-Cutting Reasoning

### Major Decision Summary

- **Provider-neutral primitive over model-native web search:** Driven by ARCH-LAYER-002, LLM-TOOL-001, and TEST-SEAM-001. This keeps search reusable by workflows and fakeable in tests.
- **Tavily-first adapter with replaceable provider port:** Driven by ERR-PROVIDER-001 and PRE-SCOPE-003. Tavily is agent-search-friendly, while Brave/Exa can be added later through the same port.
- **One `search_web` tool now:** Driven by PRE-SCOPE-004 and LLM-TOOL-001. This avoids a broad speculative tool surface.
- **Fanout deferred but shaped by service primitives:** Driven by WF-SCOPE-001, WF-STATE-001, and WF-RETRY-001. Fanout is orchestration and needs explicit state once implemented.
- **Prompt version bump:** Driven by LLM-PROMPT-001. Adding public web search materially changes agent behavior.

### Provider Research Notes

- **Tavily:** Best MVP fit for agentic search because its API supports search depth, topics, time/domain filters, raw content, answer/image options, usage metadata, and query guidance aimed at AI agents.
- **Brave:** Good second adapter for independent-index web/news/image/video/search data and freshness filters.
- **Exa:** Useful later for semantic/deep search. Avoid the deprecated Exa `/research/v1` task API and prefer Exa search/deep-reasoning if adding Exa.
- **OpenAI web search:** Useful for model-native cited answers, but not ideal as the primary workflow primitive because it couples search to a model provider and Responses API semantics.
- **Bing Search APIs:** Not an MVP option because Microsoft retired Bing Search APIs on August 11, 2025.
- **Google Custom Search JSON API:** Not an MVP option because Google documents it as closed to new customers with existing-customer transition required by January 1, 2027.

### Trade-offs

- A provider-neutral substrate is slightly more work than a direct Tavily tool, but it prevents an immediate rewrite when workflows or a second provider are added.
- Returning source objects instead of synthesized answers keeps the primitive inspectable and citation-friendly, but requires the agent to do final synthesis.
- Configurable approval for search balances third-party data-sharing risk with usability, but deployments must choose a policy intentionally.
- Deferring fanout keeps Sprint 6 smaller, but the next sprint must revisit explicit state, cancellation, retry, and partial-failure semantics before shipping research orchestration.

### Assumptions

- The first search capability is for public web information, not private customer data or internal analytics.
- The generic agent is the first intended consumer of `search_web`.
- A Tavily key is likely the easiest provider key to use for MVP real-provider smoke, but the implementation should not hard-code Tavily concepts into service or tool contracts.
- Existing agent runtime persisted tool-call lifecycle is sufficient for single-search inspectability.

### Dependencies

- Sprint 1 observability foundation supplies canonical metrics/tracing/events patterns.
- Sprint 2 worker/runtime foundation supplies provider and runtime boundary precedent.
- Sprint 4 session substrate supplies session-backed tool/result inspection surfaces.
- Sprint 5 governed SQL tool supplies the pattern for strict application tools over module-owned services.
- External provider credentials are needed for real-provider smoke evidence.

### Evidence Review Checklist

- Review can trace every new search surface to either platform provider substrate, application module service, or application tool definition.
- Review can verify there is no hidden provider call in prompts, routes, workflows, or agent runtime internals.
- Review can verify provider failures preserve stable codes, retryability, redacted details, provider metadata, and correlation identifiers.
- Review can verify tests cover fake-provider behavior, adapter normalization, failure mapping, app wiring, prompt/tool registration, and smoke coverage.
- Review can identify whether real-provider smoke was run or explicitly deferred with a concrete reason.

## Phase Exit Criteria

- [ ] Tracker scope is fully covered
- [ ] Applicable requirements are mapped
- [ ] Ambiguous and non-applicable requirements are recorded where relevant
- [ ] Important decisions are explicitly justified
- [ ] Non-trivial alternatives are discussed
- [ ] Deviations, assumptions, risks, and unknowns are documented
- [ ] Expected evidence is defined

## Documentation Updates

- `backend/docs/runtime-overview.md`: document the web search provider/substrate and optional readiness/diagnostics behavior.
- `backend/docs/agent-runtime.md`: document `search_web`, prompt policy, citations, and public-vs-internal data routing.
- `backend/docs/testing-and-operations.md`: document fake-provider tests, real-provider smoke env requirements, and explicit deferral rules.
- Optional `backend/docs/web-search.md`: add if the implementation needs a dedicated operator guide for provider setup and supported provider behavior.
