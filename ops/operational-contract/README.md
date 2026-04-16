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
- `errors.md` - Error handling, logging, and failure visibility requirements
- `observability.md` - Logging, correlation, health, and diagnostics requirements
- `testing.md` - Test seams, coverage, and determinism requirements
- `workflows.md` - Workflow eligibility, boundaries, and retry/cancellation semantics
- `agents.md` - Agent runtime boundaries, tool execution, and lifecycle rules
- `pre-brief-scope.md` - What is safe to build before the product brief exists

## How To Use Contracts

Contracts are used in:
- reasoning documents to map requirements to design decisions
- review to verify conformance against mapped requirements
- execution to preserve constraints and collect evidence

Contracts are contract-agnostic in the process docs, meaning the process does not hard-code specific contracts.
Instead, reasoning maps to whichever contracts apply to the sprint scope.
