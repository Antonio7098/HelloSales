# Plan Sprint

Use this runbook to create the planning artifacts for a new sprint.

The planning order is:

1. **Link product features** - identify or create product requirements in `ops/features/`
2. **Research** - gather codebase evidence and current external guidance
3. **Reason** - map scope to contracts and justify decisions using the research
4. **Create tracker** - turn the reasoned plan into executable tasks

## Inputs

- Sprint name or working topic
- One or more related feature documents in `ops/features/`, or enough product context to create them
- Known sprint purpose and exclusions
- Relevant prior sprint artifacts in `ops/sprints/`
- Governing contracts in `ops/operational-contract/`

## Outputs

Create a sprint directory:

`ops/sprints/sprint-[XX]-[name]/`

The directory should contain:
- `research.md`
- `reasoning.md`
- `tracker.md`

## Step 1: Link Product Features

Use:
- `ops/process/feature/feature-protocol.md`
- `ops/process/feature/feature-template.md`

Confirm whether the sprint supports an existing feature or needs a new feature document.

For substantial new feature implementation work, the sprint should normally begin from one or more existing feature documents.
If the feature documents do not exist yet, create or shape them first using the feature process before finalizing sprint planning.

Feature linking must:
- keep product requirements in `ops/features/[feature-slug].md`
- keep implementation planning in sprint artifacts
- support one feature, multiple features, or a clearly defined slice across features when needed
- add the sprint to the feature document's **Sprint Links** table
- add a **Feature Links** section to sprint `research.md`, `reasoning.md`, and `tracker.md`
- state whether the sprint researches, builds, revises, ships, or supports the feature

If the sprint is infrastructure-only and does not support a product feature directly, record `Feature Links: None - [reason]` in the sprint artifacts.

## Step 2: Research

Use:
- `ops/process/sprint-research/sprint-research-protocol.md`
- `ops/process/sprint-research/sprint-research-template.md`

Create:

`ops/sprints/sprint-[XX]-[name]/research.md`

The research phase must happen before reasoning.

Research must:
- read linked feature documents before codebase search when they exist
- treat linked feature documents as product inputs when the sprint is implementing a substantial feature or feature slice
- search the codebase for key evidence first
- identify existing modules, tests, docs, prompts, settings, patterns, seams, and prior sprint artifacts
- search the web for current best practices, latest tools, latest guidance, key repositories, relevant implementation examples, and focused code snippets where the topic may have changed
- prefer official docs, release notes, standards, security guidance, and maintained repositories
- record rejected or obsolete options so reasoning does not re-litigate weak paths
- hand off clear findings, options, risks, and evidence expectations to reasoning

## Step 3: Reason

Use:
- `ops/process/reasoning/reasoning-protocol.md`
- `ops/process/reasoning/reasoning-template.md`

Create:

`ops/sprints/sprint-[XX]-[name]/reasoning.md`

The reasoning phase must read `research.md` and reason with that information.

Reasoning must:
- preserve the product intent from linked feature documents
- make clear which part of each linked feature the sprint is actually implementing when multiple feature docs are in scope
- read every applicable governing contract
- map sprint scope to explicit requirement IDs
- use codebase and web research findings when evaluating options
- justify chosen approaches against requirements, current codebase reality, and research evidence
- record rejected alternatives, trade-offs, deviations, assumptions, and unknowns
- define the evidence execution and review must produce later

If reasoning discovers the research is missing current or decision-critical evidence, update `research.md` before finalizing the affected reasoning.

## Step 4: Create Tracker

Use:
- `ops/process/execute/tracker-template.md`

Create:

`ops/sprints/sprint-[XX]-[name]/tracker.md`

The tracker is created after research and reasoning.

Tracker creation must:
- link back to related feature documents
- make the implementation slice explicit when the sprint covers only part of a feature or spans multiple features
- translate the chosen reasoning into concrete tasks and sub-tasks
- keep tasks aligned with the decisions, constraints, and evidence expectations in `reasoning.md`
- include testing, smoke, documentation, risk, blocker, success criteria, and execution evidence sections
- avoid adding implementation scope that was not researched or reasoned about

## Exit Criteria

- [ ] Related product feature documents are linked or explicitly marked not applicable
- [ ] Sprint directory exists under `ops/sprints/`
- [ ] `research.md` exists and follows the research template
- [ ] `reasoning.md` exists and explicitly uses `research.md`
- [ ] `tracker.md` exists and reflects the chosen reasoning
- [ ] Feature documents link to the sprint, and sprint artifacts backlink to the feature where applicable
- [ ] Research, reasoning, and tracker agree on sprint scope and dependencies
- [ ] Open questions, risks, and deferred items are visible before execution begins
