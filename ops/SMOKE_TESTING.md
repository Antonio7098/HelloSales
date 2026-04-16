# Smoke Testing

## Purpose
This document defines the current smoke-testing strategy for the backend scaffold, especially the real-provider agent smokes.

Use this document when:
- running manual provider-backed checks
- deciding which smoke suite to run after a change
- extending the smoke harness

Use [GENERIC_AGENT_PLAN.md](/home/antonioborgerees/coding/HelloSales/ops/GENERIC_AGENT_PLAN.md) for the architectural placement of agents, tools, and runtime concerns.
Use [OPERATIONAL_CONTRACT.md](/home/antonioborgerees/coding/HelloSales/ops/OPERATIONAL_CONTRACT.md) for operational failure-handling requirements.

## Current Shape

The smoke harness is centralized in:
- [backend/src/hello_sales_backend/smoke](/home/antonioborgerees/coding/HelloSales/backend/src/hello_sales_backend/smoke)

It provides:
- a registry of smoke suites
- a shared smoke runner
- reusable in-process app/client helpers
- provider-backed smoke suites for the agent runtime

The local checkout entrypoint is:
- [backend/scripts/smoke.py](/home/antonioborgerees/coding/HelloSales/backend/scripts/smoke.py)

## Provider-Backed Agent Smoke Suites

The real-provider suites currently exposed are:
- `generic-agent-provider`
  Runs the full provider-backed scenario set.
- `generic-agent-provider-baseline`
  Runs one minimal provider-backed completion.
- `observer-agent-provider`
  Verifies the observer profile can complete with the real provider.
- `generic-agent-provider-append-turn`
  Verifies append-turn lifecycle on an existing run.
- `generic-agent-provider-approval-boundary`
  Verifies the run pauses correctly at the approval boundary.
- `generic-agent-provider-event-stream`
  Verifies SSE event streaming and replay behavior.

## Recommended Usage

Use the cheapest suite that answers the question you have.

Suggested defaults:
- after provider or env changes:
  run `generic-agent-provider-baseline`
- after prompt or profile routing changes:
  run `generic-agent-provider-baseline` and `observer-agent-provider`
- after turn lifecycle or persistence changes:
  run `generic-agent-provider-append-turn`
- after approval-flow changes:
  run `generic-agent-provider-approval-boundary`
- after SSE or event-log changes:
  run `generic-agent-provider-event-stream`
- before merging major runtime plumbing changes:
  run `generic-agent-provider`

## Commands

From `backend/`:

```bash
python3 scripts/smoke.py --list
python3 scripts/smoke.py generic-agent-provider
python3 scripts/smoke.py generic-agent-provider-baseline
python3 scripts/smoke.py observer-agent-provider
python3 scripts/smoke.py generic-agent-provider-append-turn
python3 scripts/smoke.py generic-agent-provider-approval-boundary
python3 scripts/smoke.py generic-agent-provider-event-stream
```

Convenience `make` targets:

```bash
make smoke
make smoke-provider-baseline
make smoke-provider-observer
make smoke-provider-append
make smoke-provider-approval
make smoke-provider-events
```

## Design Rules

When adding new smoke suites:
- keep the smoke harness centralized rather than creating ad hoc scripts
- prefer reusable scenario helpers over duplicated HTTP orchestration
- use real providers only for high-signal scenarios
- keep suite names stable because they are part of the operator command surface
- make failure payloads structured and machine-readable

When extending provider-backed suites:
- test distinct runtime behaviors, not cosmetic output phrasing
- prefer assertions on lifecycle state, event types, tool usage, approvals, and replay behavior
- avoid turning provider smokes into brittle prompt-golden tests
- keep one cheap baseline suite available for fast manual checks
