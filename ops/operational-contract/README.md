# Operational Contracts

This directory contains the normative operational contracts for HelloSales.

## Purpose

Contracts define the must / must not rules that govern implementation and review.

They are structured with:
- requirement IDs
- clear applicability
- evidence expectations
- rejection criteria

## Contract Files

- `architecture.md` - Core architecture rules and layering principles
- `frontend.md` - Frontend structure, ownership boundaries, state placement, API access, and extension rules
- `errors.md` - Error handling, logging, and failure visibility requirements
- `observability.md` - Logging, correlation, health, and diagnostics requirements
- `testing.md` - Test seams, coverage, and determinism requirements
- `workflows.md` - Workflow eligibility, boundaries, and retry/cancellation semantics
- `llm.md` - Agent and worker runtime boundaries, prompt versioning and propagation rules, tool and structured-output rules, lifecycle semantics, and operational exposure

## How To Use Contracts

Contracts are used in:
- reasoning documents to map requirements to design decisions
- review to verify conformance against mapped requirements
- execution to preserve constraints and collect evidence

Contracts are contract-agnostic in the process docs, meaning the process does not hard-code specific contracts.
Instead, reasoning maps to whichever contracts apply to the sprint scope.
