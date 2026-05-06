# Operational Process

This directory contains the protocols, templates, and process guides that define how research, planning, execution, and review work in HelloSales. It provides the operational infrastructure for translating product intent into delivered, reviewable engineering work.

## What This Directory Contains

```
ops/process/
├── README.md                    # This file - process overview
├── plan-sprint.md              # Sprint planning runbook
├── olivers-protocol.md        # Collaboration protocol for working with Oliver
├── feature/                  # Product feature process
│   ├── README.md
│   ├── feature-protocol.md
│   └── feature-template.md
├── research/                  # General research process
│   ├── README.md
│   ├── research-protocol.md
│   └── research_template.md
├── sprint-research/            # Sprint-specific research phase
│   ├── README.md
│   ├── sprint-research-protocol.md
│   └── sprint-research-template.md
├── reasoning/                 # Sprint reasoning phase
│   ├── README.md
│   ├── reasoning-protocol.md
│   └── reasoning-template.md
├── execute/                  # Sprint execution phase
│   ├── README.md
│   ├── execution-protocol.md
│   └── tracker-template.md
└── review/                  # Sprint review phase
    ├── README.md
    ├── review-protocol.md
    ├── contract-review-protocol.md
    └── report-template.md
```

## Process Overview

The operational process defines how HelloSales moves from product intent through to delivered, reviewable code. It consists of several integrated workflows:

### Core Sprint Process

The primary workflow for implementing substantial changes follows four phases:

```
Research → Reason → Execute → Review
```

| Phase | Purpose | Output |
|---|---|---|
| **Research** | Gather codebase evidence and current external guidance | `research.md` |
| **Reason** | Map scope to contracts and justify decisions | `reasoning.md` |
| **Execute** | Implement while adhering to reasoning | Code + `tracker.md` |
| **Review** | Verify conformance and produce findings | `report.md` |

### Supporting Processes

Two additional processes support the core sprint workflow:

- **Feature Process** (`feature/`) - Produces product-focused, non-technical requirements in `ops/features/`. Used when a capability needs user problems, desired outcomes, product behavior, success criteria, and sprint relationships captured before or across sprint work.

- **General Research Process** (`research/`) - Produces standalone documents in `ops/research/`. Used when the user provides a research area, goals, key considerations, constraints, or non-goals outside a specific sprint.

### High-Level Process Guides

- **Oliver's Protocol** (`olivers-protocol.md`) - Claude's collaboration protocol for working with Oliver, the product lead. Defines how to translate product intent into scoped engineering work while preserving the repository's operating model.

- **Plan Sprint** (`plan-sprint.md`) - Sprint planning runbook that ties together feature linking, research, reasoning, and tracker creation.

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

**Starting point:** A research brief, sprint scope, or implementation goal. For sprint work, access to relevant contracts in `ops/operational-contract/` is required.

## Process Architecture

### Contract-Agnostic Design

The process is intentionally contract-agnostic:

- It does not hard-code specific operational contracts
- Reasoning documents map to whichever contracts apply
- Review verifies conformance against mapped requirements

This allows the same process to work across different governance contexts while maintaining the connection to specific requirements through explicit mapping.

### Artifact Flow

```
Product Intent
     │
     ├── Feature Process ──→ Feature Document ──┐
     │                                    │
     ▼                                    ▼
Sprint Planning                    Sprint Artifacts
     │                                    │
     ├── Sprint Research ──→ research.md ────┤
     │                                    │
     ├── Sprint Reason ────→ reasoning.md ───┤
     │                                    │
     ├── Sprint Execute ──→ tracker.md ────┤
     │                        code         │
     │                                    ▼
     ▼                                   Review ──────────────────────→ report.md ──┘
```

### Bidirectional Traceability

Every process link maintains bidirectional traceability:

- Feature documents link to sprints
- Sprint artifacts back-link to feature documents
- Reasoning documents map to specific contract requirements
- Review artifacts verify against mapped requirements

## Key Protocols

### Feature Protocol

**Location:** `feature/feature-protocol.md`

Defines how to create and maintain product-focused feature documents. Feature documents are not technical designs or implementation plans—they capture the product intent:

- User problem and desired outcome
- Primary users and stakeholders
- Observable product requirements
- Success criteria
- Edge cases and exceptions
- Sprint relationships

The feature process includes a maturity scoring system (0-100) with bands from "Raw idea" to "Delivery mature." This helps determine when a feature is ready for sprint planning.

**Output:** `ops/features/[status]/[feature-slug].md`

### Research Protocol

**Location:** `research/research-protocol.md`

Defines how to create standalone research documents for a user-provided research area. The research agent:

1. Clarifies the research brief
2. Surveys the codebase first
3. Searches the web for current guidance
4. Evaluates findings with source credibility
5. Presents general findings first, then codebase implications

**Output:** `ops/research/[research-area-slug].md`

### Sprint Research Protocol

**Location:** `sprint-research/sprint-research-protocol.md`

Defines how to create sprint-local research before reasoning begins. The research phase:

1. Clarifies sprint scope and research questions
2. Searches the codebase for key evidence
3. Searches the web for current external guidance
4. Evaluates findings and extracts guidance for reasoning
5. Hands off clean findings to the reasoning phase

**Output:** `ops/sprints/sprint-[XX]-[name]/research.md`

### Sprint Reasoning Protocol

**Location:** `reasoning/reasoning-protocol.md`

Defines how to create the Sprint Reasoning document. The reasoning phase:

1. Reads every governing contract that applies
2. Reads linked feature documents
3. Reads relevant existing code
4. Analyzes features against requirements
5. Justifies decisions explicitly
6. Records deviations, risks, and assumptions

**Output:** `ops/sprints/sprint-[XX]-[name]/reasoning.md`

### Execution Protocol

**Location:** `execute/execution-protocol.md`

Describes how to execute a sprint. The executor:

1. Reads tracker and reasoning documents
2. Confirms entry criteria
3. Executes against the reasoning
4. Handles discoveries and deviations explicitly
5. Updates progress continuously
6. Verifies exit criteria before marking complete

### Review Protocol

**Location:** `review/review-protocol.md`

Defines how to create the Sprint Report. The review agent performs:

1. Design and correctness review
2. Conformance verification against sprint reasoning
3. Contract-aware review
4. Structured findings with severity

**Output:** `ops/sprints/sprint-[XX]-[name]/report.md`

### Contract Review Protocol

**Location:** `review/contract-review-protocol.md`

A specialized review agent reviews a specific requirement area and updates the report with evidence-based findings for that area. Used when the review needs domain-specific expertise.

## Template Structure

Each protocol pairs with a corresponding template that provides the output structure:

| Protocol | Template | Output |
|---|---|---|
| Feature | `feature-template.md` | Feature document |
| Research | `research-template.md` | Research document |
| Sprint Research | `sprint-research-template.md` | Sprint research |
| Reasoning | `reasoning-template.md` | Sprint reasoning |
| Execution | `tracker-template.md` | Sprint tracker |
| Review | `report-template.md` | Sprint report |

Templates include structured sections, tables, and checklists that ensure consistency across all artifacts.

## Related Documentation

### Operational Contracts

The operational contracts define what implementation and review must accept or reject. Key contracts:

- `ops/operational-contract/README.md` - Contracts overview
- `ops/operational-contract/architecture.md` - Architecture requirements
- `ops/operational-contract/pre-brief-scope.md` - Pre-brief scope rules
- `ops/operational-contract/frontend.md` - Frontend standards
- `ops/operational-contract/testing.md` - Testing requirements
- `ops/operational-contract/errors.md` - Error handling requirements
- `ops/operational-contract/observability.md` - Observability requirements

### Sprint Artifacts

Completed sprints produce artifacts stored in:

- `ops/sprints/backlog/` - Sprints planned but not started
- `ops/sprints/active/` - Sprints currently in progress
- `ops/sprints/done/` - Completed sprints

### Features

Feature documents are stored in:

- `ops/features/backlog/` - Features planned but not started
- `ops/features/active/` - Features currently being implemented
- `ops/features/done/` - Features delivered

## Quick Reference

### Starting a New Sprint

1. Confirm sprint scope and linked features
2. Create sprint directory in `ops/sprints/backlog/`
3. Run `plan-sprint.md` process
4. Move to `active/` when ready to execute
5. Execute against tracker
6. Move to `done/` after sign-off

### Creating a Feature

1. Use `feature/feature-protocol.md`
2. Coach product thinking first
3. Fill in `feature-template.md`
4. Score maturity
5. Link to sprints when planned

### Doing Standalone Research

1. Use `research/research-protocol.md`
2. Codebase survey first
3. Web research for current guidance
4. Fill in `research-template.md`
5. Present general findings, then codebase implications

### Running a Review

1. Read tracker and reasoning
2. Read applicable contracts
3. Review in priority order (risk → design → correctness → security → performance → maintainability → test → docs)
4. Verify contract adherence
5. Fill in `report-template.md`

## Process Principles

1. **Product first** - Define user and business outcomes before technical planning
2. **Search before deciding** - Research gathers evidence; reasoning makes decisions
3. **Stay grounded** - Reference actual code patterns and seams
4. **Justify explicitly** - Do not jump from requirement to conclusion
5. **Record deviations** - Do not bury them in prose
6. **Preserve traceability** - Every link goes both ways
7. **Coach thinking** - Help users make decisions before documenting
8. **Score maturity** - Use scores to guide discovery, not create false precision