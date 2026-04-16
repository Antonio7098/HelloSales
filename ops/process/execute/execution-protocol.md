# Sprint Execution Protocol

This document describes how to execute a sprint in HelloSales.

## Overview

A sprint is executed using two documents:

1. **Tracker** - Defines what to do
2. **Reasoning** - Defines the requirement mapping, decision rationale, and evidence expectations for the sprint

The executor works through the tracker tasks while adhering to the sprint reasoning document and the governing contracts in force for the work.

## Input

- **Tracker** - `ops/sprints/sprint-[XX]-[name]/tracker.md`
- **Reasoning** - `ops/sprints/sprint-[XX]-[name]/reasoning.md`

## Procedure

### Step 1: Read Documents And Confirm Entry Criteria

Read the tracker and reasoning document to understand:
- what is in scope
- what decisions were made and why
- what governing requirements apply
- what tests and evidence must be produced

Before coding, confirm:
- the tracker scope is clear
- the reasoning document exists and covers the sprint scope
- applicable requirements are identified
- known risks, assumptions, ambiguities, and deviations are visible
- you are on the correct git branch for the sprint (e.g., `sprint/sprint-XX-name`)

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

### Step 3: Handle Discoveries And Deviations Explicitly

If implementation reveals that the reasoning document is incomplete or wrong:
- pause and update the reasoning document before continuing with the affected work
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
- [ ] code matches the agreed sprint reasoning or recorded deviations
- [ ] unit, integration, smoke, and failure-path testing has been run or explicitly deferred with reason
- [ ] documentation changes are complete
- [ ] if backend code changed, `backend/docs/` has been updated to reflect the new reality
- [ ] execution evidence is ready for review
- [ ] blockers, risks, and deviations are recorded in the sprint artifacts

## Output

- Completed code implementation
- Tests passing
- Updated tracker with progress
- Updated reasoning document when scope discoveries or deviations occurred
- Review-ready evidence for conformance verification
