# Sprint Tracker: WorkOS Auth Foundation

> Project: HelloSales
> Sprint ID: sprint-08-workos-auth-foundation
> Created: 2026-04-23

## Sprint Overview

- **Sprint Name:** WorkOS Auth Foundation
- **Sprint Focus:** Introduce provider-agnostic API auth with WorkOS as the first adapter and enforce backend permissions across product-facing routes.
- **Depends On:** `ops/sprints/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/sprint-06-web-search-capabilities/tracker.md`, `ops/sprints/sprint-07-semantic-catalog-entity-mutations/tracker.md`
- **Status:** Complete

## Sprint Goals

- **Primary Goal:** Ship general API auth middleware, provider-neutral auth seams, and backend-enforced permissions with WorkOS as the first adapter.
- **Secondary Goals:**
  - Propagate auth context into session-backed agent execution so permissions survive approvals and async runtime boundaries.
  - Update the frontend app shell to use the new auth/session flow.
  - Update canonical backend docs and sprint evidence for the new auth runtime.

## Execution Checklist

- [x] **Task 1: Create sprint artifacts and auth architecture seams**
  > *Description: Establish reasoning, tracker, provider-neutral auth contracts, and composition wiring before touching product routes.*
  - [x] **Sub-task 1.1:** Create Sprint 8 reasoning and tracker documents.
  - [x] **Sub-task 1.2:** Add shared auth context and permission definitions.
  - [x] **Sub-task 1.3:** Add platform auth contracts, provider registry wiring, and composition overrides for auth providers.

- [x] **Task 2: Implement WorkOS-backed auth module and middleware**
  > *Description: Add module-owned auth use cases, WorkOS adapter behavior, current-session middleware, startup validation, and auth routes.*
  - [x] **Sub-task 2.1:** Add `modules/auth/` and `platform/auth/providers/workos.py`.
  - [x] **Sub-task 2.2:** Add auth middleware and request-state current-session resolution.
  - [x] **Sub-task 2.3:** Add `/api/auth/login`, `/api/auth/callback`, `/api/auth/session`, and `/api/auth/logout`.
  - [x] **Sub-task 2.4:** Add startup/config validation and provider diagnostics for auth.

- [x] **Task 3: Enforce permissions across product-facing APIs**
  > *Description: Protect general product routes with explicit backend permission checks instead of limiting auth to run/session entrypoints.*
  - [x] **Sub-task 3.1:** Add reusable permission dependencies for HTTP routes.
  - [x] **Sub-task 3.2:** Protect sessions, agent runs, worker runs, jobs, system, company profile, and product routes.
  - [x] **Sub-task 3.3:** Add session ownership filtering and elevated access behavior for session reads/writes.

- [x] **Task 4: Propagate authorization into long-lived runtime execution**
  > *Description: Ensure agent and tool execution preserve org and permission context after the initial HTTP request completes.*
  - [x] **Sub-task 4.1:** Extend agent-run persistence with org and permission snapshots.
  - [x] **Sub-task 4.2:** Propagate auth context into tool execution.
  - [x] **Sub-task 4.3:** Enforce tool-level permissions using the persisted auth snapshot.

- [x] **Task 5: Update frontend auth bootstrapping**
  > *Description: Add app-level auth bootstrapping, sign-in/sign-out flow wiring, and credentialed API access in the frontend.*
  - [x] **Sub-task 5.1:** Add app-owned auth provider/session loading.
  - [x] **Sub-task 5.2:** Require credentials on frontend API calls and surface unauthenticated UI state.
  - [x] **Sub-task 5.3:** Add app-shell sign-in/sign-out controls and current-user context.

- [x] **Task 6: Testing, documentation, and execution evidence**
  > *Description: Finish the sprint with conformance evidence, docs, and explicit deferrals where real WorkOS credentials are unavailable.*
  - [x] **Sub-task 6.1:** Add unit and integration coverage for middleware, auth routes, permission checks, and tool authorization.
  - [x] **Sub-task 6.2:** Add or update migration(s) and relevant persistence coverage.
  - [x] **Sub-task 6.3:** Update canonical backend docs for auth configuration and runtime surfaces.
  - [x] **Sub-task 6.4:** Record explicit real-provider smoke deferral or run evidence.

## Testing And Documentation Checklist

- [x] **Unit Tests:** deterministic coverage for auth context mapping, permission evaluation, and tool-level authorization
- [x] **Integration Tests:** API, middleware, callback/logout/session behavior, and protected route coverage for the sprint scope
- [x] **Smoke Tests:** critical auth-protected runtime paths are exercised through the backend smoke suite with fake auth provider seams
- [x] **Real Provider Smoke:** deferred because local WorkOS credentials are not available in this workspace
- [x] **Documentation Updates:** update canonical documentation in `backend/docs/`

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| WorkOS sealed-session callback flow requires raw SDK request handling | High | Isolate raw request logic inside the WorkOS adapter and cover the app boundary with fake-provider tests | Mitigated |
| Product routes are currently unauthenticated and many tests assume open access | High | Add a fake auth provider override in tests and migrate route coverage systematically | Closed |
| Company profile persistence is not yet org-partitioned | Medium | Enforce permissions now and record org-partitioning follow-up in sprint evidence | Deferred |

## Success Criteria

- [x] **Success Criteria 1:** Product-facing API routes require authenticated sessions and explicit permissions.
- [x] **Success Criteria 2:** WorkOS is integrated through a provider-neutral auth boundary and app-owned auth module.
- [x] **Success Criteria 3:** Session-backed agent execution preserves org and permission context for later approvals/tool execution.
- [x] **Success Criteria 4:** Frontend app bootstrap uses the new auth/session flow and credentialed API access.

## Review And Sign-Off

- Sprint Status: Complete
- Completion Date: 2026-04-24

## Execution Evidence

- Created sprint branch `sprint/sprint-08-workos-auth-foundation`.
- Created Sprint 8 reasoning and tracker artifacts before implementation.
- Added provider-neutral auth contracts, `AuthContext`, permission slugs, WorkOS adapter, no-op adapter, auth module, auth middleware, and `/api/auth/*` routes.
- Protected general product APIs including sessions, agent runs, worker runs, jobs, system, company profile, and product profile surfaces through explicit permission dependencies.
- Added agent-run org and permission snapshots plus tool-level permission enforcement for long-lived background execution.
- Added frontend auth provider, credentialed API requests, app-shell auth state, and sign-out flow.
- Added migration `0006_add_auth_context_to_agent_runs.py`.
- Updated `backend/.env.example` and canonical backend docs for auth configuration, API/runtime surfaces, diagnostics, and testing operations.
- Verification: `pytest backend/tests/integration/test_auth_api.py backend/tests/unit/test_agent_tool_permissions.py -q` -> `7 passed`.
- Verification: `pytest backend/tests/unit backend/tests/integration backend/tests/smoke -q` -> `116 passed, 6 skipped`.
- Verification: `ruff check src tests` from `backend/` -> passed.
- Verification: `mypy src` from `backend/` -> passed.
- Verification: `npm run build` from `frontend/` -> passed.
- Verification: `npm run test:run` from `frontend/` -> `1 passed`.
- Verification: `npm run lint` from `frontend/` -> passed with one pre-existing Fast Refresh warning in `frontend/src/test/test-utils.tsx`.
- Real WorkOS smoke: deferred because this workspace does not include `HELLO_SALES_WORKOS_CLIENT_ID`, `HELLO_SALES_WORKOS_API_KEY`, and `HELLO_SALES_WORKOS_COOKIE_PASSWORD`.
