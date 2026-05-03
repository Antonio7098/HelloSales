# Operational Process

This directory contains the protocols and templates for the operational process.

## Prerequisites

- Understanding of the sprint scope
- Access to relevant contracts in `ops/operational-contract/`

## Purpose

The operational process defines how sprints are planned, executed, and reviewed in HelloSales.

## Process Phases

### 1. Reasoning
Location: `reasoning/`

The reasoning phase produces a document that:
- maps sprint scope to governing contract requirements
- justifies design decisions
- defines evidence expectations

**Files:**
- [reasoning-protocol.md](reasoning/reasoning-protocol.md)
- [reasoning-template.md](reasoning/reasoning-template.md)

### 2. Execution
Location: `execute/`

The execution phase implements work while:
- adhering to the reasoning document
- preserving constraints and invariants
- collecting review evidence

**Files:**
- [execution-protocol.md](execute/execution-protocol.md)
- [tracker-template.md](execute/tracker-template.md)

### 3. Review
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
| `reasoning.md` | Per-sprint | Requirement mapping and decision rationale |
| `tracker.md` | Per-sprint | Tasks and progress |
| `report.md` | Per-sprint | Conformance verification and findings |

## Related Docs

- [ops/operational-contract/README.md](../operational-contract/README.md) - Contracts