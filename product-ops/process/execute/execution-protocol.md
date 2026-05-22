# Sprint Execution Protocol

This document describes how to execute a sprint in HelloSales.

## Overview

A sprint is executed using two documents:

1. **Tracker** - Defines what to do
2. **Reasoning** - Defines the requirement mapping, decision rationale, and evidence expectations for the sprint

The executor works through the tracker tasks while adhering to the sprint reasoning document and the governing contracts in force for the work.
If the sprint links to product feature documents in `ops/features/`, the executor preserves that product intent and keeps feature/sprint links current when scope changes.

## Input

- **Tracker** - `ops/sprints/sprint-[XX]-[name]/tracker.md`
- **Reasoning** - `ops/sprints/sprint-[XX]-[name]/reasoning.md`

## Sprint Directory Structure

Sprints are organized into three directories:

- `ops/sprints/backlog/` - Sprints planned but not started
- `ops/sprints/active/` - Sprints currently in progress
- `ops/sprints/done/` - Completed sprints

## Procedure

### Step 1: Read Documents And Confirm Entry Criteria

Read the tracker and reasoning document to understand:
- what is in scope
- which feature documents are linked, if any
- what decisions were made and why
- what governing requirements apply
- what tests and evidence must be produced

Before coding, confirm:
- feature links are present or explicitly marked not applicable
- the tracker scope is clear
- the reasoning document exists and covers the sprint scope
- applicable requirements are identified
- known risks, assumptions, ambiguities, and deviations are visible
- you are on the correct git branch for the sprint (e.g., `sprint/sprint-XX-name`)

### Step 1.5: Move Sprint To Active

When starting execution of a sprint from backlog:
1. Move the sprint directory from `ops/sprints/backlog/` to `ops/sprints/active/`
2. Update any internal file references that point to the sprint (e.g., in other sprint tracker files)
3. Update `ops/sprints/README.md` to reflect the new directory location
4. Update any references in `ops/process/` files if applicable
5. For any linked features in `ops/features/backlog/`, move them to `ops/features/active/`

### Step 2: Execute The Sprint Against The Reasoning

Work through each task and sub-task in the tracker:
- Execute the implementation
- Run tests
- Update tracker as items complete

Follow the mapped requirements and the justified decisions in the reasoning document throughout execution.

During implementation:
- preserve the constraints and invariants identified in the reasoning document
- keep implementation aligned with the recorded reasoning
- collect the execution evidence the reasoning document says review will need later
- keep implementation grounded in the actual codebase rather than improvising a parallel pattern
- consider using `scripts/scaffold_module.py` to bootstrap new modules

### Step 3: Handle Discoveries And Deviations Explicitly

If implementation reveals that the reasoning document is incomplete or wrong:
- pause and update the reasoning document before continuing with the affected work
- update linked feature documents if the product requirement, scope, user journey, or success criteria changed
- record newly discovered assumptions, risks, or blockers
- document any required deviation or change in reasoning explicitly rather than hiding it in commit history or ad hoc notes

Each deviation should record:
- what requirement mapping or chosen approach changed
- why it changed
- what risk it introduces
- whether it is temporary or permanent
- what follow-up work is required

### Step 4: Update Progress Continuously

As tasks complete:
- mark items done in the tracker
- note blockers, discoveries, or scope pressure
- keep reasoning, tracker, and implementation aligned

### Step 5: Verify Exit Criteria Before Marking Complete

Before declaring the sprint execution complete, verify:
- [ ] tracker tasks are complete or explicitly deferred
- [ ] linked feature documents still reflect the delivered product scope, or no direct feature link applies
- [ ] code matches the agreed sprint reasoning or recorded deviations
- [ ] unit, integration, smoke, and failure-path testing has been run or explicitly deferred with reason
- [ ] documentation changes are complete
- [ ] search for all README.md files in the repo and update any that are relevant to the changes made
- [ ] execution evidence is ready for review
- [ ] blockers, risks, and deviations are recorded in the sprint artifacts

### Step 6: Move Sprint To Done After Sign-Off

After the sprint is signed off (PR merged and review complete):
1. Move the sprint directory from `ops/sprints/active/` to `ops/sprints/done/`
2. Update any internal file references that point to the sprint (e.g., in other sprint tracker files)
3. Update `ops/sprints/README.md` to reflect the new directory location
4. Update any references in `ops/process/` files if applicable
5. For any linked features where all sprints are now done, move them from `ops/features/active/` to `ops/features/done/`

## Output

- Completed code implementation
- Tests passing
- Updated tracker with progress
- Updated reasoning document when scope discoveries or deviations occurred
- Review-ready evidence for conformance verification
