# Operational Process

This directory contains the protocols and templates for the operational process.

## Prerequisites

- Understanding of the sprint scope
- Access to relevant contracts in `ops/operational-contract/`

## Purpose

The operational process defines how sprints are planned, executed, and reviewed in HelloSales.

## Process Phases

### 1. Research
Location: `research/`

The research phase produces a document that:
- searches the codebase for key evidence
- searches the web for current best practices, latest tools, latest guidance, key repositories, and useful implementation examples where relevant
- hands off findings, options, risks, and evidence expectations to reasoning

**Files:**
- [research-protocol.md](research/research-protocol.md)
- [research-template.md](research/research-template.md)

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
| `research.md` | Per-sprint | Codebase and external evidence gathered before reasoning |
| `reasoning.md` | Per-sprint | Requirement mapping and decision rationale |
| `tracker.md` | Per-sprint | Tasks and progress |
| `report.md` | Per-sprint | Conformance verification and findings |

## Related Docs

- [ops/plan-sprint.md](../plan-sprint.md) - Sprint planning runbook
- [ops/operational-contract/README.md](../operational-contract/README.md) - Contracts
