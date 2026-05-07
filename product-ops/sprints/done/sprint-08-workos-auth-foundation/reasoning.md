# Sprint Reasoning: WorkOS Auth Foundation

> Project: HelloSales
> Sprint ID: sprint-08-workos-auth-foundation
> Created: 2026-04-23

## Sprint Scope

Sprint 8 introduces the first real authentication and authorization foundation for HelloSales.

The sprint scope is:
- add an app-owned auth boundary with a provider-agnostic contract
- implement WorkOS as the first auth adapter
- add general API auth middleware and current-session resolution
- protect product-facing HTTP routes with backend-enforced permissions
- propagate org and permission snapshots into session-backed agent execution so long-lived runs do not lose authorization context
- update frontend app bootstrapping to use the new auth/session flow
- update canonical backend documentation and sprint evidence

The sprint does not attempt:
- full SCIM provisioning
- durable internal user/org/member persistence beyond the existing operational references
- resource-level FGA or relationship-based authorization
- customer-facing org/admin management UI

## Requirement Map

### Applicable Requirements

| Contract | Requirement | Why It Applies |
| --- | --- | --- |
| architecture.md | ARCH-CORE-001 | New auth module and platform auth adapter boundary must stay explicit. |
| architecture.md | ARCH-CORE-002 | Routes must depend on module services and dependencies, not provider SDK details. |
| architecture.md | ARCH-LAYER-002 | Authorization and identity resolution must depend on narrow provider ports, not WorkOS directly in use cases. |
| architecture.md | ARCH-ENTRY-001 | HTTP routes must stay thin while auth middleware/dependencies resolve actor context. |
| architecture.md | ARCH-COMP-001 | Auth assembly must be added through the composition root and provider registry. |
| errors.md | ERR-CORE-001 | Authentication and authorization failures must surface explicitly. |
| errors.md | ERR-SHAPE-001 | Auth failures must preserve the canonical error shape. |
| errors.md | ERR-CODE-001 | Stable auth error codes are needed for 401, 403, callback failure, refresh failure, and provider misconfiguration. |
| errors.md | ERR-TRANS-001 | WorkOS SDK and JWT failures must be translated without losing cause/context. |
| errors.md | ERR-STARTUP-001 | Partial WorkOS configuration must fail startup before traffic. |
| errors.md | ERR-HTTP-001 | Transport must preserve 401 vs 403 and include correlation metadata. |
| errors.md | ERR-PROVIDER-001 | WorkOS failures must remain classified and observable. |
| observability.md | OBS-CORE-001 | Auth failures and callback/refresh failures must emit structured signals. |
| observability.md | OBS-CORR-001 | Auth middleware and protected routes must preserve request/trace metadata. |
| observability.md | OBS-HEALTH-001 | Startup validation must keep readiness truthful when auth is required but misconfigured. |
| frontend.md | FE-APP-001 | Frontend auth bootstrap belongs in `src/app/`. |
| frontend.md | FE-STATE-001 | Auth session state is app-wide runtime state and should live at the app boundary, not in arbitrary features. |
| frontend.md | FE-API-001 | Frontend auth/session API access must stay explicit and typed. |
| testing.md | TEST-SEAM-001 | Auth provider behavior must be replaceable in tests through public seams. |
| testing.md | TEST-INT-001 | Route and middleware wiring changes require integration coverage. |
| testing.md | TEST-FAIL-001 | 401/403, callback failure, provider misconfiguration, and permission-denied paths need explicit tests. |
| testing.md | TEST-SMOKE-002 | The sprint adds a supported provider-backed path, so a real-provider smoke must exist or be explicitly deferred. |
| pre-brief-scope.md | PRE-SCOPE-002 | Auth and tenancy were previously deferred; now they are explicitly known scope and must be implemented deliberately rather than implicitly. |
| pre-brief-scope.md | PRE-SCOPE-003 | The auth foundation should favor replaceable seams and operational plumbing over premature product-specific policy. |

### Non-Applicable Requirements

| Contract | Requirement | Why Not |
| --- | --- | --- |
| workflows.md | WF-SCOPE-001 | Sprint 8 does not add new workflows. |
| llm.md | LLM-BOUNDARY-001 | The sprint touches agent runtime context propagation but does not alter LLM substrate mode separation. |
| frontend.md | FE-WORKFLOW-001 | No new multi-step frontend user journey is introduced beyond app auth bootstrapping. |

### Ambiguous Requirements

| Requirement | Ambiguity | Resolution For This Sprint |
| --- | --- | --- |
| PRE-SCOPE-002 | The contract previously deferred auth/tenancy details. | User direction now supplies enough certainty to implement generic auth foundations without locking in product-specific resource models. |
| FE-APP-001 | “App-level auth shell” is named but not structurally prescribed. | Use an app-owned auth provider plus route shell rather than scattering auth checks through features. |

### Open Questions

- Whether org-level admins should be able to inspect any user’s conversational sessions by default or only through explicit elevated permissions.
- Whether future API consumers need first-class bearer-token support beyond the SPA session-cookie flow.
- Whether company profile and product data will later become org-partitioned in persistence rather than only permission-gated at transport.

## Existing Code Constraints

The current codebase already contains the right seams for a provider-agnostic design:
- provider-backed integrations already assemble through `platform/composition/providers.py`
- routes stay thin and resolve services through `entrypoints/http/dependencies.py`
- sessions already persist neutral `actor_id`, `user_id`, and `org_id`
- session routes and agent runs currently pass `actor_id=None`, so identity resolution is missing rather than conflicting
- agent tool execution only carries `actor_id` today, which is insufficient once permissions must survive approval and async continuation

These existing seams strongly favor adding:
- a provider-neutral auth port in `platform/auth/`
- a module-owned auth facade in `modules/auth/`
- middleware for current-session resolution
- permission snapshots on agent runs so tool execution and approvals remain backend-authoritative

## Feature Analysis And Decisions

### 1. General API Auth

**Requirement context**
- ARCH-ENTRY-001, ERR-HTTP-001, FE-APP-001, TEST-INT-001

**Options considered**
- Route-by-route auth resolution only
- Global auth middleware with route dependencies for authorization

**Chosen approach**
- Add global auth middleware that resolves the current session once per request and attaches `auth_context` to request state.
- Keep authorization as explicit route dependencies so each endpoint declares the permissions it requires.

**Why this approach**
- Middleware centralizes cookie refresh/clear behavior and current-session parsing.
- Route dependencies keep permission requirements explicit and reviewable.
- This matches the existing thin-route architecture instead of pushing provider logic into routes.

**Why not the alternative**
- Route-by-route authentication would duplicate cookie/session handling and make refresh behavior inconsistent.

**Evidence to verify later**
- Middleware integration tests show session resolution and cookie refresh/clear behavior.
- Protected route tests distinguish 401 from 403.

### 2. Provider-Agnostic Auth Boundary

**Requirement context**
- ARCH-LAYER-002, ARCH-COMP-001, PRE-SCOPE-003, TEST-SEAM-001

**Options considered**
- Integrate WorkOS SDK directly inside routes/services
- Add a provider-neutral auth port with a WorkOS adapter

**Chosen approach**
- Create `platform/auth/contracts.py` and implement WorkOS in `platform/auth/providers/workos.py`.
- Expose auth use cases through `modules/auth/`.

**Why this approach**
- It keeps WorkOS replaceable, matches the provider-registry pattern already used for LLM and web search, and gives tests a clean fake seam.

**Why not the alternative**
- Direct WorkOS integration would violate the existing architecture contract and make future provider swaps expensive.

**Evidence to verify later**
- Composition root wires an auth provider through the provider registry.
- Tests can override the auth provider without patching internals.

### 3. Permission Model

**Requirement context**
- PRE-SCOPE-003, ERR-CODE-001, TEST-FAIL-001

**Options considered**
- Hard-code `admin`/`user`
- Use explicit permission slugs with roles remaining provider-configurable

**Chosen approach**
- Backend authorization uses permission slugs such as `app.access`, `sessions.read`, `sessions.write`, `company_profile.read`, `company_profile.write`, `jobs.read`, `jobs.run`, `workers.read`, `workers.run`, `workers.cancel`, `system.read`, `analytics.read`, `web_search.use`, and `entity_operations.write`.

**Why this approach**
- It satisfies the user request for more flexibility than admin/user while keeping the first sprint implementable.
- Roles remain a provider concern; permissions remain the backend’s authoritative decision surface.

**Why not the alternative**
- Binary role modeling would immediately create role explosion once diagnostics, jobs, analytics, and entity mutation capabilities diverge.

**Evidence to verify later**
- Protected routes declare explicit permission dependencies.
- Agent tool execution denies missing permissions even after approvals or async continuation.

### 4. Long-Lived Runtime Authorization

**Requirement context**
- ERR-CORE-001, OBS-CORR-001, TEST-FAIL-001

**Options considered**
- Authorize only at HTTP ingress
- Snapshot org/permission context into agent runs and propagate it into tool execution

**Chosen approach**
- Extend agent-run persistence and tool execution context with `org_id` and permission snapshots.

**Why this approach**
- Runs and approvals can continue after the original request, so route-level authorization alone is insufficient.
- Persisted permission snapshots preserve the authorization decision basis that existed when the run was started.

**Why not the alternative**
- Route-only authorization would allow privileged tool execution to continue later without an authoritative permission context.

**Evidence to verify later**
- Agent-run persistence contains org/permission snapshots.
- Tool-catalog tests show permission denial with stable error codes.

### 5. Frontend App Auth Shell

**Requirement context**
- FE-APP-001, FE-STATE-001, FE-API-001

**Options considered**
- Scatter auth fetch logic through pages
- Add an app-owned auth provider and route shell

**Chosen approach**
- Add auth bootstrap in `frontend/src/app/providers/` and require credentials on API calls.

**Why this approach**
- It matches the frontend contract and keeps auth as a runtime concern rather than feature logic.

**Why not the alternative**
- Page-local auth logic would immediately become inconsistent and violate the ownership model.

**Evidence to verify later**
- App startup loads current session once.
- Authenticated and unauthenticated UI states are handled through app-owned components.

## Risks, Assumptions, And Deviations

### Risks

1. WorkOS Python SDK sealed-session support is partly hand-maintained and requires raw request handling for callback/session sealing.
   Mitigation: keep the WorkOS-specific request logic isolated in the adapter and cover it with fake-provider integration tests.

2. Session ownership policy may be too narrow for future org-admin support.
   Mitigation: allow elevated `sessions.read:any` / `sessions.write:any` permissions now and document the policy gap.

3. Company profile data is not yet partitioned by org in persistence.
   Mitigation: enforce permissions now and record org partitioning as follow-up work once the product data model is ready.

### Assumptions

- WorkOS organization and permission claims are authoritative for the active session.
- The first production integration path is browser-based hosted auth with session cookies.
- API middleware is acceptable for request-scoped session refresh and current-session attachment.

### Explicit Deviations

1. **Deviation**
   Durable internal user/org/member tables are not introduced in Sprint 8.

   **Reason**
   Existing operational models only need trusted auth references, and the user explicitly prioritized provider flexibility and immediate auth over identity warehousing.

   **Risk**
   Future analytics, audit, or internal admin features may need durable identity replication.

   **Disposition**
   Temporary.

   **Follow-up**
   Add durable identity sync/storage when product data ownership and org lifecycle rules are finalized.

2. **Deviation**
   Resource-level FGA is not implemented in this sprint.

   **Reason**
   The current product codebase has org/session-level needs but not yet the stable resource hierarchy needed for a good relation-based model.

   **Risk**
   Some future resource-sharing cases will require another authorization layer.

   **Disposition**
   Temporary.

   **Follow-up**
   Introduce internal authorizer/resource grants or FGA once team/pipeline/account sharing rules are explicit.

3. **Deviation**
   Real WorkOS smoke was not executed in this workspace.

   **Reason**
   The workspace does not include WorkOS client id, API key, cookie password, or a configured AuthKit redirect environment.

   **Risk**
   The provider-neutral API boundary is covered, but live WorkOS hosted-auth behavior still needs environment validation.

   **Disposition**
   Temporary.

   **Follow-up**
   Run the callback/session/logout path against a WorkOS sandbox once credentials and redirect URLs are provisioned.

## Implementation Evidence

- General API auth middleware resolves cookie and bearer credentials once per request and stores `AuthContext` on request state.
- HTTP authorization is explicit through reusable permission dependencies.
- WorkOS is isolated behind `AuthProviderPort`; tests use a fake provider through composition overrides.
- Session-backed agent runs persist actor, org, and permission context for approvals and background tool execution.
- Tool definitions declare required permission slugs and the catalog denies missing permissions with `auth.permission_denied`.
- Frontend API calls use credentials and the app shell bootstraps from `/api/auth/session`.

## Verification Evidence

- `pytest backend/tests/integration/test_auth_api.py backend/tests/unit/test_agent_tool_permissions.py -q` -> `7 passed`.
- `pytest backend/tests/unit backend/tests/integration backend/tests/smoke -q` -> `116 passed, 6 skipped`.
- `ruff check src tests` from `backend/` -> passed.
- `mypy src` from `backend/` -> passed.
- `npm run build` from `frontend/` -> passed.
- `npm run test:run` from `frontend/` -> `1 passed`.
- `npm run lint` from `frontend/` -> passed with one pre-existing Fast Refresh warning in `frontend/src/test/test-utils.tsx`.

## Execution Evidence Expectations

Execution and review should be able to point to:
- a new provider-neutral auth boundary and WorkOS adapter
- auth middleware attached at app startup
- protected routes with explicit permission dependencies
- session and agent-run propagation of actor/org/permission context
- structured 401/403/provider failure tests
- integration tests proving auth override seams
- updated backend documentation covering configuration, routes, and runtime behavior
- an explicit real-provider smoke deferral if WorkOS credentials are not available locally
