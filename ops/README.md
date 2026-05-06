# Operations

This directory contains the operational infrastructure for HelloSales—including product features, sprint artifacts, governance contracts, and research documentation. It provides the structure for translating product intent into delivered, reviewable engineering work.

## What This Directory Contains

```
ops/
├── README.md                    # This file - ops overview
├── operational-contract/         # Governance contracts (requirements)
│   ├── README.md
│   ├── architecture.md
│   ├── errors.md
│   ├── frontend.md
│   ├── llm.md
│   ├── observability.md
│   ├── pre-brief-scope.md
│   ├── testing.md
│   └── workflows.md
├── process/                   # Operational process (how work flows)
│   ├── README.md
│   ├── plan-sprint.md
│   ├── olivers-protocol.md
│   ├── feature/
│   ├── research/
│   ├── sprint-research/
│   ├── reasoning/
│   ├── execute/
│   └── review/
├── features/                 # Product-focused feature documents
├── sprints/                 # Sprint artifacts (research, reasoning, trackers, reports)
│   ├── backlog/
│   ├── active/
│   └── done/
└── research/                # Standalone research documents
    └── deep-research/
```

## Overview

The ops directory is organized into five main areas:

| Area | Purpose |
|---|---|
| **operational-contract/** | Governance contracts defining must/must-not rules for implementation and review |
| **process/** | Protocols, templates, and guides that define how work flows |
| **features/** | Product-focused feature documents capturing user intent and requirements |
| **sprints/** | Sprint artifacts including research, reasoning, trackers, and reports |
| **research/** | Standalone research documents |

## Operational Contract

**Location:** `ops/operational-contract/`

The governance contracts define the normative rules that implementation must follow and review must verify. Each contract contains:

- Requirement IDs
- Clear applicability
- Evidence expectations
- Rejection criteria

### Contract Areas

| Contract | Purpose |
|---|---|
| `architecture.md` | Core architecture rules and layering principles |
| `frontend.md` | Frontend structure, ownership boundaries, state placement |
| `errors.md` | Error handling, logging, failure visibility |
| `observability.md` | Logging, correlation, health, diagnostics |
| `testing.md` | Test seams, coverage, determinism |
| `workflows.md` | Workflow boundaries, retry/cancellation |
| `llm.md` | Agent/worker runtime, prompt versioning |
| `pre-brief-scope.md` | What is safe before product brief |

### How Contracts Work

Contracts are used throughout the operational process:

1. **Reasoning** - Sprint reasoning maps design decisions to applicable contract requirements
2. **Review** - Review verifies conformance against mapped requirements
3. **Execution** - Implementers preserve constraints and collect evidence

The process is contract-agnostic—reasoning documents explicitly map to whichever contracts apply to the sprint scope.

## Operational Process

**Location:** `ops/process/`

The process directory defines how work flows through the system. It provides:

- **Protocols** - Detailed instructions for each phase
- **Templates** - Output structures for artifacts
- **Guides** - High-level runbooks for common workflows

### Core Workflow

```
Brief → Feature → Research → Reason → Execute → Review
```

| Phase | Protocol | Output |
|---|---|---|
| Feature | `feature/feature-protocol.md` | Feature document |
| Research | `sprint-research/sprint-research-protocol.md` | Sprint research |
| Reason | `reasoning/reasoning-protocol.md` | Sprint reasoning |
| Execute | `execute/execution-protocol.md` | Implementation + tracker |
| Review | `review/review-protocol.md` | Sprint report |

### Supporting Processes

- **Standalone Research** (`research/research-protocol.md`) - For research areas outside specific sprints
- **Sprint Planning** (`plan-sprint.md`) - Runbook for starting new sprints
- **Oliver's Protocol** (`olivers-protocol.md`) - Collaboration guidance

### Template Pairing

Each protocol pairs with a corresponding template:

- `feature-protocol.md` → `feature-template.md`
- `research-protocol.md` → `research-template.md`
- `sprint-research-protocol.md` → `sprint-research-template.md`
- `reasoning-protocol.md` → `reasoning-template.md`
- `execution-protocol.md` → `tracker-template.md`
- `review-protocol.md` → `report-template.md`

## Features

**Location:** `ops/features/`

Product-focused feature documents capture non-technical requirements before implementation. They describe:

- User problems and desired outcomes
- Primary users and stakeholders
- Observable product requirements
- Success criteria
- Edge cases and exceptions
- Sprint relationships

### Directory Structure

```
features/
├── active/      # Features currently being implemented
├── backlog/     # Features planned but not started
└── done/       # Features delivered
```

### Feature Maturity

Features include a maturity score (0-100) with bands:

- **0-24: Raw idea** - User, problem, and outcome unclear
- **25-49: Shaped draft** - Problem and user emerging
- **50-69: Product-defined** - Main thinking present
- **70-84: Sprint-planning ready** - Clear for research/reasoning
- **85-100: Delivery mature** - Strong clarity, validated assumptions

Features should reach at least **70** before moving to sprint planning.

## Sprints

**Location:** `ops/sprints/`

Sprint artifacts capture the complete lifecycle of implementation work:

| Artifact | Purpose |
|---|---|
| `research.md` | Codebase evidence and external guidance |
| `reasoning.md` | Requirement mapping and decision justification |
| `tracker.md` | Task execution and progress |
| `report.md` | Review findings and conformance verification |

### Directory Structure

```
sprints/
├── backlog/     # Sprints planned but not started
├── active/      # Sprints currently in progress
└── done/        # Completed sprints
```

### Sprint Flow

```
1. Plan → Move to backlog
2. Execute → Move to active
3. Complete → Move to done
```

## Research

**Location:** `ops/research/`

Standalone research documents capture investigation into specific areas:

- Technology evaluations
- Tool comparisons
- Implementation patterns
- Best practice surveys

### Directory Structure

```
research/
├── [research-area-slug].md    # Individual research documents
└── deep-research/              # Comprehensive investigations
```

### Research Types

- **Standalone** - Created with `research/research-protocol.md`, stored in `ops/research/`
- **Sprint-local** - Created with `sprint-research/sprint-research-protocol.md`, stored with sprint

## Process Architecture

### Bidirectional Traceability

Every link in the operational chain goes both ways:

```
Feature ↔ Sprint
Sprint → Research → Reasoning → Tracker → Report
Reasoning → Contracts
```

This ensures nothing is lost and every decision can be traced back to its source.

### Contract-Agnostic Process

The process itself does not hard-code specific contracts:

- Reasoning documents explicitly map to applicable requirements
- Review verifies against mapped requirements
- The same process works across different governance contexts

### Artifact Flow

```
Product Intent
     │
     ├── Feature Process ──→ Feature Document
     │                          │
     ▼                          ▼
Sprint Planning            Sprint Artifacts
     │                          │
     ├── Research ──→ research.md
     │
     ├── Reason ────→ reasoning.md
     │
     ├── Execute ──→ tracker.md + code
     │
     ▼
    Review ──────────────────→ report.md
```

## Quick Reference

### Starting Work

1. **For a new feature**: Use `ops/process/feature/feature-protocol.md`
2. **For a new sprint**: Use `ops/process/plan-sprint.md`
3. **For standalone research**: Use `ops/process/research/research-protocol.md`

### Finding Context

- **Product requirements**: See `ops/features/`
- **Implementation planning**: See sprint artifacts in `ops/sprints/`
- **Governance rules**: See `ops/operational-contract/`
- **How to do something**: See `ops/process/`

### Linking Requirements

- Feature documents link to sprints
- Sprint artifacts back-link to features
- Sprint reasoning maps to contract requirements
- Sprint review verifies conformance

## Related Documentation

- **[ops/process/README.md](process/README.md)** - Detailed process documentation
- **[ops/operational-contract/README.md](operational-contract/README.md)** - Contract reference
- **[ops/features/README.md](features/README.md)** - Feature management
- **[ops/sprints/README.md](sprints/README.md)** - Sprint inventory