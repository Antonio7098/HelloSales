# Plan Sprint

Use this runbook to create the planning artifacts for a new sprint.

The planning order is:

1. **Research** - gather codebase evidence and current external guidance
2. **Reason** - map scope to contracts and justify decisions using the research
3. **Create tracker** - turn the reasoned plan into executable tasks

## Inputs

- Sprint name or working topic
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

## Step 1: Research

Use:
- `ops/process/sprint-research/sprint-research-protocol.md`
- `ops/process/sprint-research/sprint-research-template.md`

Create:

`ops/sprints/sprint-[XX]-[name]/research.md`

The research phase must happen before reasoning.

Research must:
- search the codebase for key evidence first
- identify existing modules, tests, docs, prompts, settings, patterns, seams, and prior sprint artifacts
- search the web for current best practices, latest tools, latest guidance, key repositories, relevant implementation examples, and focused code snippets where the topic may have changed
- prefer official docs, release notes, standards, security guidance, and maintained repositories
- record rejected or obsolete options so reasoning does not re-litigate weak paths
- hand off clear findings, options, risks, and evidence expectations to reasoning

## Step 2: Reason

Use:
- `ops/process/reasoning/reasoning-protocol.md`
- `ops/process/reasoning/reasoning-template.md`

Create:

`ops/sprints/sprint-[XX]-[name]/reasoning.md`

The reasoning phase must read `research.md` and reason with that information.

Reasoning must:
- read every applicable governing contract
- map sprint scope to explicit requirement IDs
- use codebase and web research findings when evaluating options
- justify chosen approaches against requirements, current codebase reality, and research evidence
- record rejected alternatives, trade-offs, deviations, assumptions, and unknowns
- define the evidence execution and review must produce later

If reasoning discovers the research is missing current or decision-critical evidence, update `research.md` before finalizing the affected reasoning.

## Step 3: Create Tracker

Use:
- `ops/process/execute/tracker-template.md`

Create:

`ops/sprints/sprint-[XX]-[name]/tracker.md`

The tracker is created after research and reasoning.

Tracker creation must:
- translate the chosen reasoning into concrete tasks and sub-tasks
- keep tasks aligned with the decisions, constraints, and evidence expectations in `reasoning.md`
- include testing, smoke, documentation, risk, blocker, success criteria, and execution evidence sections
- avoid adding implementation scope that was not researched or reasoned about

## Exit Criteria

- [ ] Sprint directory exists under `ops/sprints/`
- [ ] `research.md` exists and follows the research template
- [ ] `reasoning.md` exists and explicitly uses `research.md`
- [ ] `tracker.md` exists and reflects the chosen reasoning
- [ ] Research, reasoning, and tracker agree on sprint scope and dependencies
- [ ] Open questions, risks, and deferred items are visible before execution begins
