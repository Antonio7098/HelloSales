# Testing Contract

## Purpose
This contract defines the minimum testing expectations for backend changes.

It governs:
- test seam requirements
- unit, integration, and smoke expectations
- failure-path coverage
- determinism and flakiness constraints
- collaborator replacement strategy

## Scope
This contract applies when a change:
- adds or changes backend logic
- changes dependency wiring or persistence
- changes background, workflow, or provider behavior
- changes public adapters or operational surfaces

## Requirement Index

| ID | Title | Applies To | Severity If Violated |
| --- | --- | --- | --- |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | all testable components | High |
| TEST-UNIT-001 | Business logic must have unit coverage | domain and use-case logic | Medium |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | composition, persistence, adapters | High |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | startup and key runtime flows | Medium |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | real-provider runtime paths | High |
| TEST-FAIL-001 | Failure paths must be tested explicitly | failure-producing changes | High |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | all tests | Medium |

## Requirements

### TEST-SEAM-001: Collaborators Must Be Replaceable Through Public Seams

**Rule**
Major collaborators must be replaceable in tests without mutating private fields.

**Required**
- use constructor injection, builder overrides, or public bootstrap seams
- provide fake or test-double implementations for important ports
- keep container overrides explicit

**Forbidden**
- tests mutating private service fields
- tests depending on hidden container internals normal code should not know about

**Evidence**
- tests use fake ports or documented overrides
- no private patching is required to isolate business logic

### TEST-UNIT-001: Business Logic Must Have Unit Coverage

**Rule**
Domain logic and use-case logic must have deterministic unit coverage.

**Required**
- test invariants, branching rules, validation, and transformation logic
- keep unit tests fast and dependency-light

**Evidence**
- domain and use-case tests exist for changed business logic

### TEST-INT-001: Wiring And Persistence Changes Must Have Integration Coverage

**Rule**
Changes to persistence, composition, or adapter behavior must be exercised through integration tests.

**Required**
- test DB mappings and transaction behavior when persistence changes
- test bootstrap wiring when composition changes
- test adapters through realistic boundaries where appropriate

**Evidence**
- integration tests cover changed runtime seams and wiring

### TEST-SMOKE-001: Critical Runtime Paths Must Have Smoke Coverage

**Rule**
Critical runtime paths must be validated through smoke tests or equivalent high-signal end-to-end checks.

**Required**
- keep smoke execution centralized
- cover startup and the most important runtime behaviors
- prefer stable behavior checks over exact phrasing assertions

**Forbidden**
- ad hoc duplicate smoke scripts with separate boot logic
- brittle provider smokes that assert cosmetic output wording

**Evidence**
- smoke suites exist for critical runtime paths
- smoke commands are documented and reusable

### TEST-SMOKE-002: Critical External Provider Paths Must Have Real-Provider Smoke Coverage

**Rule**
External provider paths that are intended to work against the real provider in production must have real-provider smoke coverage at the appropriate boundary.

**Applies when**
- adding or changing a provider-backed runtime path
- changing provider configuration, transport, approval, streaming, or lifecycle behavior
- changing an external-provider path that is part of the supported operational surface

**Required**
- run/add at least one real-provider smoke for critical supported provider-backed paths
- keep one cheap baseline real-provider smoke available for fast verification
- use real-provider smokes to verify durable behavior such as lifecycle state, approvals, persistence, streaming, or replay rather than cosmetic phrasing

**Forbidden**
- treating fake-provider or mocked integration coverage as sufficient for critical real-provider behavior
- shipping changes to critical provider-backed paths with no real-provider verification plan

**Evidence**
- documented real-provider smoke suites exist for supported critical provider-backed paths
- review can point to the exact real-provider smoke run or explicit justified deferral

### TEST-FAIL-001: Failure Paths Must Be Tested Explicitly

**Rule**
A change that introduces or modifies a failure mode must include explicit failure-path verification.

**Required**
- test at least one expected failure path when adding failure-handling logic
- test unexpected or wrapped failure behavior where the boundary matters
- verify the resulting status, error shape, or observable failure signal

**Evidence**
- tests cover negative cases, not just happy paths

### TEST-DET-001: Tests Must Remain Deterministic And Non-Brittle

**Rule**
Tests must prefer deterministic signals and avoid flaky or over-coupled assertions.

**Required**
- assert on stable behavior, structure, lifecycle, and state transitions
- keep provider-backed smokes focused on durable runtime behavior

**Forbidden**
- fragile tests that depend on exact phrasing with no need
- tests that only pass because of hidden timing assumptions

**Evidence**
- assertions target stable fields and behavior
- retries, timing, and external dependencies are controlled or isolated in tests

## Review Rejection Criteria
Reject a change if it:
- requires tests to patch private fields to replace collaborators
- changes persistence or wiring with no integration coverage
- adds a meaningful failure path with no negative-case verification
- introduces brittle smoke or provider assertions that check cosmetic phrasing instead of durable behavior
