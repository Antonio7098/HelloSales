# Operational Process

This directory contains the protocols and templates for the operational process.

## Prerequisites

- A research brief, sprint scope, or implementation goal
- For sprint work, access to relevant contracts in `ops/operational-contract/`

## Purpose

The operational process defines how research, sprint planning, execution, and review are run in HelloSales.

## Process Phases

### Product Features
Location: `feature/`

The feature process produces product-focused, non-technical requirements in `ops/features/`.
It is used when a capability needs the user problem, desired outcome, product behavior, success criteria, and sprint relationships captured before or across sprint work.

Feature documents:
- describe product intent in plain language
- avoid implementation design
- can link to one or more sprints
- must be backlinked from linked sprint artifacts

**Files:**
- [feature-protocol.md](feature/feature-protocol.md)
- [feature-template.md](feature/feature-template.md)

### General Research
Location: `research/`

The general research process produces standalone documents in `ops/research/`.
It is used when the user provides a research area, goals, key considerations, constraints, or non-goals outside a specific sprint.

The general research process:
- surveys the codebase and integration points first
- searches the web for current guidance, tools, repositories, examples, and best practices where relevant
- presents general findings first
- then explains how those findings link to HelloSales and may be best implemented

**Files:**
- [research-protocol.md](research/research-protocol.md)
- [research-template.md](research/research-template.md)

### 1. Sprint Research
Location: `sprint-research/`

The sprint research phase produces a sprint-local `research.md` before reasoning begins.

**Files:**
- [sprint-research-protocol.md](sprint-research/sprint-research-protocol.md)
- [sprint-research-template.md](sprint-research/sprint-research-template.md)

### 2. Reasoning
Location: `reasoning/`

The reasoning phase produces a document that:
- maps sprint scope to governing contract requirements
- reasons from the research document
- justifies design decisions
- defines evidence expectations

**Files:**
- [reasoning-protocol.md](reasoning/reasoning-protocol.md)
- [reasoning-template.md](reasoning/reasoning-template.md)

### 3. Execution
Location: `execute/`

The execution phase implements work while:
- adhering to the reasoning document
- preserving constraints and invariants
- collecting review evidence

**Files:**
- [execution-protocol.md](execute/execution-protocol.md)
- [tracker-template.md](execute/tracker-template.md)

### 4. Review
Location: `review/`

The review phase:
- verifies conformance to reasoning and contracts
- produces a structured report

**Files:**
- [review-protocol.md](review/review-protocol.md)
- [contract-review-protocol.md](review/contract-review-protocol.md)
- [report-template.md](review/report-template.md)

## Contract-Agnostic Process

The process is contract-agnostic:
- it does not hard-code specific operational contracts
- reasoning documents map to whichever contracts apply
- review verifies conformance against mapped requirements

## Artifacts

| Artifact | Location | Description |
|---|---|---|
| `[feature-slug].md` | `ops/features/` | Product-focused non-technical requirements, success criteria, and sprint links |
| `[research-area-slug].md` | `ops/research/` | Standalone research findings and codebase implementation implications |
| `research.md` | Per-sprint | Sprint-specific codebase and external evidence gathered before reasoning |
| `reasoning.md` | Per-sprint | Requirement mapping and decision rationale |
| `tracker.md` | Per-sprint | Tasks and progress |
| `report.md` | Per-sprint | Conformance verification and findings |

## Related Docs

- [ops/process/plan-sprint.md](plan-sprint.md) - Sprint planning runbook
- [ops/operational-contract/README.md](../operational-contract/README.md) - Contracts
