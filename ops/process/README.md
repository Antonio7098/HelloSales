# Operational Process

This directory contains the protocols and templates for the operational process.

## Purpose

The operational process defines how sprints are planned, executed, and reviewed in HelloSales.

## Process Phases

### Reasoning
Location: `ops/process/reasoning/`

The reasoning phase produces a document that maps sprint scope to governing contract requirements, justifies decisions, and defines evidence expectations.

### Execution
Location: `ops/process/execute/`

The execution phase implements the work while adhering to the reasoning document and mapped requirements.

### Review
Location: `ops/process/review/`

The review phase verifies conformance to the reasoning document and governing contracts, and produces a structured report.

## Contract-Agnostic Process

The process is contract-agnostic:
- it does not hard-code specific operational contracts
- reasoning documents map to whichever contracts apply to the sprint scope
- review verifies conformance against the requirements mapped in reasoning

## Artifacts

- `reasoning.md` - Sprint reasoning document (requirement mapping and decision rationale)
- `tracker.md` - Sprint tracker (tasks and progress)
- `report.md` - Sprint report (conformance verification and findings)
