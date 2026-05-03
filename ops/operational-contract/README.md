# Operational Contracts

This directory contains the normative operational contracts for HelloSales.

## Prerequisites

- Review requires understanding of the project scope
- Contracts define must/must-not rules - review the full contract before implementing

## Purpose

Contracts define the must / must not rules that govern implementation and review.

They are structured with:
- requirement IDs
- clear applicability
- evidence expectations
- rejection criteria

## Contract Files

| File | Purpose |
|---|---|
| [architecture.md](architecture.md) | Core architecture rules and layering principles |
| [frontend.md](frontend.md) | Frontend structure, ownership boundaries, state placement |
| [errors.md](errors.md) | Error handling, logging, failure visibility |
| [observability.md](observability.md) | Logging, correlation, health, diagnostics |
| [testing.md](testing.md) | Test seams, coverage, determinism |
| [workflows.md](workflows.md) | Workflow boundaries, retry/cancellation |
| [llm.md](llm.md) | Agent/worker runtime, prompt versioning |
| [pre-brief-scope.md](pre-brief-scope.md) | What is safe before product brief |

## How To Use Contracts

Contracts are used in:
- **reasoning** - map requirements to design decisions
- **review** - verify conformance against requirements
- **execution** - preserve constraints and collect evidence

Contracts are contract-agnostic in the process docs - reasoning maps to whichever contracts apply to the sprint scope.

## Related Docs

- [ops/process/README.md](../process/README.md) - Operational process
- [ops/process/reasoning/README.md](../process/reasoning/README.md) - Reasoning phase
- [ops/process/review/README.md](../process/review/README.md) - Review phase