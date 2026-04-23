# Web Search

## Runtime Shape

Public web search is implemented as a provider-neutral capability.
The layers are:
- `platform/web_search/` owns neutral provider contracts and provider adapters
- `modules/web_search/` owns the reusable `WebSearchService.search()` primitive
- `application/tools/web_search.py` exposes one strict native agent tool named `search_web`
- `application/agents/definitions/generic_agent/` registers the tool and prompt policy

The service returns normalized source objects and metadata.
It does not synthesize final answers.
The agent is responsible for answering the user from returned sources and citing URLs.

## Provider Configuration

The first concrete provider adapter is Tavily.

Relevant settings:
- `HELLO_SALES_WEB_SEARCH_PROVIDER=tavily`
- `HELLO_SALES_TAVILY_API_KEY`
- `HELLO_SALES_WEB_SEARCH_API_KEY`
- `HELLO_SALES_WEB_SEARCH_TIMEOUT_SECONDS`
- `HELLO_SALES_WEB_SEARCH_DEFAULT_MAX_RESULTS`
- `HELLO_SALES_WEB_SEARCH_REQUIRED`
- `HELLO_SALES_WEB_SEARCH_REQUIRES_APPROVAL`

`HELLO_SALES_WEB_SEARCH_API_KEY` is a generic override.
If it is empty and the provider is `tavily`, `HELLO_SALES_TAVILY_API_KEY` is used.

## Agent Policy

`search_web` is for current, external, or public internet information.
It must not be used for secrets, private customer data, confidential internal data, or internal-only analytics facts.
For approved internal analytics questions, the generic agent should prefer `query_analytics_data`.

Approval defaults to disabled for ordinary public-web searches.
Set `HELLO_SALES_WEB_SEARCH_REQUIRES_APPROVAL=true` when deployments require a human approval gate before any third-party search call.

## Diagnostics And Failure Semantics

Provider diagnostics include a separate `kind=web_search` entry with availability, required state, and degraded state.
Readiness fails only when web search is explicitly required and selected without usable credentials.

Stable provider error codes include:
- `provider.web_search.not_configured`
- `provider.web_search.timeout`
- `provider.web_search.rate_limit`
- `provider.web_search.authentication_failed`
- `provider.web_search.remote_5xx`
- `provider.web_search.http_failure`
- `provider.web_search.malformed_response`

Provider logs include query length and request metadata rather than raw API keys.
Secrets are redacted through the shared error/detail normalization path.

## Smoke Coverage

The centralized smoke registry includes `generic-agent-provider-web-search`.
It requires both a configured generic-agent LLM provider and a configured web-search provider.
If no Tavily or generic web-search key is available, real-provider web-search smoke is explicitly deferred by configuration rather than faked.

## Future Fanout Seam

Sprint 6 intentionally does not implement research fanout.
A future `WebSearchBatchService.search_many()` or `ResearchWebWorkflow` should compose `WebSearchService.search()` and define:
- concurrency limit
- per-query status
- partial-failure behavior
- cancellation semantics
- retry budget
- provider metadata propagation

That future workflow should live behind an application-owned boundary and should not require changing the current single-query `search_web` tool contract.
