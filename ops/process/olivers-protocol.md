# Oliver's Protocol

## Purpose

This protocol tells Claude Code how to operate in HelloSales when collaborating with Oliver, a product lead who may understand basic GitHub and technical concepts but is not expected to manage engineering process details.

Claude's job is to help Oliver turn product intent into well-scoped, reviewable engineering work while preserving Antonio's operating model for the repository.

## Project Context

HelloSales is a pre-brief sales application scaffold. It currently contains:

- `backend/` - Python 3.12+ FastAPI backend scaffold with async SQLAlchemy, Alembic, observability, workers, smoke tests, and LLM provider seams.
- `frontend/` - main React 19, TypeScript, Vite frontend scaffold.
- `frontend-draft/` - draft/pre-brief React frontend.
- `central-pulse/` - central operation frontend.
- `ops/` - operational contracts, sprint process, templates, and sprint artifacts.
- `.github/workflows/` - backend and frontend CI definitions.

The project is still governed by the pre-brief scope rules unless Antonio says otherwise. Do not invent product-specific domain commitments, workflows, data models, prompts, or information architecture without a brief or explicit approval.

## Operating Principle

Follow the repository's operating process before writing code.

Claude must treat `ops/operational-contract/` as normative. The contracts define what implementation and review must accept or reject. Every meaningful change must preserve the applicable contract requirements.

The most important starting points are:

- `ops/operational-contract/README.md`
- `ops/operational-contract/pre-brief-scope.md`
- `ops/operational-contract/architecture.md`
- `ops/operational-contract/frontend.md`
- `ops/operational-contract/testing.md`
- `ops/operational-contract/errors.md`
- `ops/operational-contract/observability.md`
- `ops/operational-contract/workflows.md`
- `ops/operational-contract/llm.md`
<<<<<<< HEAD
- `ops/process/plan-sprint.md`
=======
- `ops/plan-sprint.md`
>>>>>>> origin/main

## Collaboration With Oliver

Oliver may describe work in product language rather than implementation language. Claude should translate that into scoped engineering artifacts, explain trade-offs plainly, and keep Oliver informed about what is safe to do next.

When requirements are unclear, ask concise clarifying questions. Do not fill gaps by silently inventing business rules.

When explaining technical choices to Oliver:

- use plain language first
- name the concrete files or contracts involved
- separate product decisions from implementation decisions
- surface risks, assumptions, and deferred decisions
- avoid presenting speculative product behavior as settled

Claude may help Oliver draft feature ideas, acceptance criteria, and product notes, but implementation must still follow the process below.

<<<<<<< HEAD
## Feature Discovery With Oliver

When Oliver wants to create, shape, or evaluate a product feature, Claude should use the feature process:

- `ops/process/feature/feature-protocol.md`
- `ops/process/feature/feature-template.md`
- `ops/features/README.md`

The default behavior is to coach Oliver through the feature thinking before writing the final document.

Claude should guide the conversation through:
- the user problem and why it matters now
- the desired product or business outcome
- the target user, stakeholder, and job to be done
- the trigger or context where the need appears
- the current workaround or pain without the feature
- the smallest useful V1
- later phases and out-of-scope boundaries
- observable product requirements
- permissions, roles, and visibility
- edge cases and exception behavior
- success criteria, adoption signals, and rollout considerations
- risks, assumptions, and open questions

Do not turn this into a long questionnaire by default. Ask the next highest-value question, explain why the answer matters when useful, and keep a running view of what is known, assumed, and unresolved.

If Oliver says he wants a lighter version, fewer details, or wants Claude to fill in gaps, Claude should comply. In that case:
- ask only the minimum clarifying questions needed to avoid misleading requirements
- mark inferred content as assumptions
- keep unresolved decisions visible
- create a usable draft even if the maturity score is lower

### Feature Maturity Scoring

Every feature document should receive a maturity score from 0 to 100.

Claude should be ready to provide or update this score while the feature is being developed, not only at the end. The score is a readiness signal, not a personal grade.

Use these bands:
- **0-24: Raw idea** - mostly a concept; user, problem, and outcome are unclear.
- **25-49: Shaped draft** - problem and user are emerging, but requirements, risks, or scope are still thin.
- **50-69: Product-defined** - main product thinking is present; some assumptions or edge cases remain.
- **70-84: Sprint-planning ready** - product intent, requirements, success criteria, risks, and scope are clear enough for research/reasoning.
- **85-100: Delivery mature** - strong product clarity, validated assumptions where possible, crisp V1 scope, and current sprint links.

Score across ten dimensions worth 10 points each:
- problem clarity
- outcome clarity
- user and job-to-be-done clarity
- journey clarity
- observable requirement quality
- rules, permissions, and visibility
- scope control across V1, later phases, and out-of-scope items
- edge cases and exception behavior
- risks and assumptions
- delivery linkage, rollout, adoption, and dependencies

When giving a score, Claude should include:
- the numeric score and band
- the top reasons for the score
- the biggest maturity gaps
- the next few questions or edits that would raise the score most

### Feature To Sprint Handoff

A feature usually should not move into sprint planning until it is at least **70: Sprint-planning ready**.

Oliver can explicitly choose to proceed below 70, but Claude must make the trade-off visible:
- what assumptions sprint research must validate
- what product decisions remain unresolved
- what risk the team is accepting by planning early

When a sprint is created for a feature, Claude must keep links current both ways:
- the feature document lists the related sprint
- sprint `research.md`, `reasoning.md`, and `tracker.md` each include a **Feature Links** section

=======
>>>>>>> origin/main
## Work Classification

### Small Frontend Changes

Small, low-risk frontend changes may be made without opening the full sprint process.

Examples:

- copy changes
- minor styling adjustments
- small layout fixes
- isolated component polish
- minor accessibility improvements
- test-only improvements for existing frontend behavior

Even small frontend changes must:

- stay within existing frontend architecture
- avoid new product commitments
- update tests when behavior changes
- update documentation when the change affects usage or process
- run the relevant frontend checks before PR

If a frontend change starts touching routing, data flow, API contracts, state ownership, product workflows, or reusable architecture, treat it as major work.

### Major Additions And New Features

<<<<<<< HEAD
Major additions, substantial new feature implementations, backend changes, workflow changes, LLM/provider changes, persistence changes, public API changes, or architecture changes must go through the sprint process in `ops/process/plan-sprint.md`.

If the work is a substantial implementation of a product feature, the sprint process should start from one or more feature documents in `ops/features/`.
The sprint plan should treat those feature documents as the product source of truth for the work being implemented.
=======
Major additions, new features, backend changes, workflow changes, LLM/provider changes, persistence changes, public API changes, or architecture changes must go through the sprint process in `ops/plan-sprint.md`.
>>>>>>> origin/main

This means:

1. Research
2. Reason
3. Create tracker
4. Execute
5. Review

The sprint artifacts must live under:

```text
ops/sprints/sprint-[XX]-[name]/
```

Expected planning files:

- `research.md`
- `reasoning.md`
- `tracker.md`

Expected review output:

- `report.md`

## Sprint Planning Gate

For major work, Claude should normally stop after planning and ask Antonio to review the sprint plan before implementation begins.

The review point is after:

- `research.md` is complete
- `reasoning.md` maps the work to applicable operational contract requirement IDs
- `tracker.md` turns the reasoning into executable tasks
- open questions, assumptions, risks, testing expectations, and documentation expectations are visible

Preferred handoff:

```text
Antonio, the sprint plan is ready for review:
- research.md
- reasoning.md
- tracker.md

I have not started implementation yet.
```

If Oliver asks Claude to continue before Antonio reviews, Claude may implement the plan, but must make it clear that Antonio will review the result after implementation and that the work still needs PR review before merge.

## Branch And PR Rules

All new work must happen on a new branch.

Do not commit directly to `main`. Do not merge directly to `main`.

Use a focused branch name that describes the work, for example:

```text
feature/sprint-12-runtime-unification
fix/frontend-empty-state
docs/oliver-protocol
```

Every change must be merged through a pull request.

Before opening a PR:

- review the diff
- make sure generated or temporary files are not included accidentally
- run the local equivalents of the relevant GitHub Actions workflows
- document any checks that could not be run and why

## CI And Local Checks

Use `.github/workflows/` as the source of truth for required PR checks.

For backend changes, mirror `.github/workflows/backend-ci.yml` locally as far as practical:

```bash
cd backend
make verify-db
make migrate
python -m ruff check src tests scripts
python -m mypy src
make test
HELLO_SALES_RUN_POSTGRES_TESTS=1 python -m pytest tests/postgres -q
```

For frontend changes, mirror `.github/workflows/frontend-ci.yml` locally:

```bash
cd frontend
npm run lint
npm run build
npm run test:run
```

If dependencies are missing, install them using the repository's documented package manager commands. If a check requires external services, credentials, Docker, or provider access that is unavailable, record the exact limitation in the PR and in the sprint review evidence when applicable.

## Testing Requirements

New additions must be thoroughly tested at the right level.

Use `ops/operational-contract/testing.md` as the baseline. In practice:

- business logic needs deterministic unit coverage
- wiring, persistence, and adapter changes need integration coverage
- critical runtime paths need smoke coverage
- provider-backed paths need real-provider smoke coverage when they are production-relevant
- failure paths need explicit negative-case tests
- tests should assert stable behavior, not cosmetic phrasing or timing accidents

Do not treat a happy-path manual check as sufficient for a major feature.

## Documentation Requirements

Documentation must be updated when behavior, setup, commands, architecture, process, or user-visible functionality changes.

Depending on the change, update the relevant docs:

- root `README.md`
- `backend/README.md`
- `frontend/README.md`
- files under `backend/docs/`
- files under `ops/`
- sprint artifacts under `ops/sprints/`

For sprint work, the documentation expectation should appear in `tracker.md`, and the completed documentation evidence should appear in the review/report output.

## Execution Rules

When implementing:

- read the relevant existing code before editing
- follow established local patterns
- keep changes scoped to the sprint or issue
- preserve public seams and ownership boundaries
- avoid unrelated refactors
- avoid speculative product decisions
- keep errors observable and actionable
- keep workflow engines, LLM providers, and external services behind app-owned boundaries
- update tests and docs in the same branch
- keep the tracker current if the work is sprint-based

If implementation reveals that the plan is wrong or incomplete, update the sprint artifacts before continuing. Do not silently drift away from `reasoning.md`.

## Review Rules

Before asking for PR review, Claude must perform a structured self-review.

For sprint work, use the review process under:

- `ops/process/review/review-protocol.md`
- `ops/process/review/contract-review-protocol.md`
- `ops/process/review/report-template.md`

The review must verify:

- the implementation matches the planned scope
- applicable operational contracts are satisfied
- tests were added or updated appropriately
- documentation was updated
- CI-equivalent checks were run
- known risks, limitations, and deferrals are explicit

If the work violates a contract, do not present it as ready. Fix it or document the blocker clearly.

## Pull Request Expectations

Every PR should include:

- what changed
- why it changed
- whether sprint artifacts were used
- links or paths to relevant sprint docs
- applicable contracts considered
- tests and checks run
- documentation updated
- known risks or follow-up work

For Oliver-facing work, the PR should also include a short product-language summary that explains what the change means without assuming deep technical knowledge.

## What Claude Must Not Do

Claude must not:

- bypass `ops/operational-contract/`
- invent product-specific requirements without approval
- start major feature implementation without sprint planning
- commit directly to `main`
- open a PR without running relevant checks or documenting why checks were skipped
- merge its own PR
- hide unresolved assumptions from Oliver or Antonio
- treat generated code as correct without reading and testing it
- make broad architecture changes as part of a small frontend request
- leave documentation stale

## Default Flow

For a small frontend change:

1. Create a branch.
2. Make the focused change.
3. Update tests and docs if needed.
4. Run frontend checks.
5. Open a PR with a concise summary.

For major work:

1. Create a branch.
2. Read applicable contracts.
<<<<<<< HEAD
3. Follow `ops/process/plan-sprint.md`.
=======
3. Follow `ops/plan-sprint.md`.
>>>>>>> origin/main
4. Stop for Antonio's review after planning unless Oliver explicitly asks to continue.
5. Implement from the approved or acknowledged plan.
6. Keep tracker evidence current.
7. Run relevant checks from `.github/workflows/`.
8. Complete review artifacts.
9. Open a PR.
10. Wait for review and merge approval.
<<<<<<< HEAD
=======

>>>>>>> origin/main
