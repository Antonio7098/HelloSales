# Roadmap: [Roadmap Name]

> Project: HelloSales
> Created: [YYYY-MM-DD]
> Owner: [Name / Team]
> Status: [Draft / Active / Complete / Deferred]
> Planning Principle: Aggressive incrementalism

## Purpose

[Describe the product or operational outcome this roadmap is meant to create.]

This roadmap is intentionally incremental. Each stage should be approximately one product feature and one sprint. If a stage cannot be described as one useful capability with one sprint-sized implementation slice, split it before planning.

## Foundations

Start from the current foundation described in `product-ops/README.md` and existing sprint history in `product-ops/sprints/`.

### Current Foundation

- [Existing platform, runtime, workflow, or product capability this roadmap builds on]
- [Existing contract, process, or operational constraint that governs the work]
- [Existing feature, sprint, or research artifact that provides prior context]

### Foundation Gaps

- [Gap that must be closed before the first product feature can land]
- [Gap that can be handled inside an early stage]
- [Gap that should remain deferred]

## Roadmap Guardrails

- Prefer the smallest useful product behavior over broad platform work.
- Each stage should produce a user-visible, stakeholder-visible, or operationally useful increment.
- Each stage should normally map to one feature document in `product-ops/features/`.
- Each stage should normally map to one sprint directory in `product-ops/sprints/`.
- Feature documents stay product-focused and non-technical.
- Sprint artifacts own research, reasoning, implementation tracking, and review evidence.
- Do not hide dependencies. If a foundation stage is needed, make it explicit and keep it sprint-sized.
- Do not advance a stage to sprint planning until the linked feature is at least sprint-planning ready or the maturity gap is explicitly accepted.

## Success Criteria

This roadmap is successful when:

- [Observable product or operational outcome]
- [Adoption, usage, quality, or reliability signal]
- [Business, customer, or internal workflow signal]

## Roadmap Sequence

| Stage | Feature | Sprint | Stage Outcome | Foundation Dependency | Status |
| --- | --- | --- | --- | --- | --- |
| 01 | `[feature-slug]` | `sprint-[XX]-[name]` | [One useful outcome] | [Foundation this builds on] | [Draft / Planned / Active / Done] |
| 02 | `[feature-slug]` | `sprint-[XX]-[name]` | [Next useful outcome] | [Previous stage or existing foundation] | [Draft / Planned / Active / Done] |
| 03 | `[feature-slug]` | `sprint-[XX]-[name]` | [Next useful outcome] | [Previous stage or existing foundation] | [Draft / Planned / Active / Done] |

## Stage Template

Copy this section for each roadmap stage.

### Stage [XX]: [Stage Name]

**Increment:** [One sentence describing the smallest useful capability this stage delivers.]

**Why This Stage Exists:** [Problem, opportunity, or foundation gap this stage addresses.]

**Aggressive Incrementalism Check:**

- **One-ish feature:** [Yes / No] - [If no, what must be split out]
- **One sprint:** [Yes / No] - [If no, what must be split out]
- **Smallest useful behavior:** [What users, stakeholders, or operators get after this stage]
- **Deferred on purpose:** [What tempting adjacent scope is left for later]

**Feature Link:**

- `product-ops/features/[backlog|active|done]/[feature-slug].md` - [Researches / Builds / Revises / Ships / Supports]

**Feature Readiness:**

- **Maturity score:** [0-100]
- **Maturity band:** [Raw Idea / Shaped Draft / Product-Defined / Sprint-Planning Ready / Delivery Mature]
- **Blocking product questions:** [None / List questions]

**Sprint Link:**

- `product-ops/sprints/[backlog|active|done]/sprint-[XX]-[name]/` - [Planned / Active / Done]

**Sprint Planning Notes:**

- **Research needed:** [Codebase evidence, external guidance, prior sprint artifacts]
- **Likely governing contracts:** [architecture / frontend / errors / observability / testing / workflows / llm / pre-brief-scope]
- **Reasoning focus:** [The decisions this sprint must justify]
- **Execution evidence:** [Tests, smoke checks, docs, screenshots, telemetry, or review evidence expected]

**Entry Criteria:**

- [ ] Feature document exists or is intentionally marked not applicable
- [ ] Feature links this sprint in its Sprint Links table
- [ ] Sprint `research.md`, `reasoning.md`, and `tracker.md` backlink to the feature
- [ ] Sprint scope is no larger than this stage's increment
- [ ] Foundation dependency is available or explicitly included in this sprint
- [ ] Open questions and deferred scope are visible

**Exit Criteria:**

- [ ] Stage outcome is delivered or explicitly deferred
- [ ] Sprint tracker evidence is complete
- [ ] Review/report evidence is complete when required
- [ ] Feature maturity and status are updated
- [ ] Roadmap status is updated
- [ ] Follow-on stage changes are recorded

## Dependencies And Ordering

| Dependency | Required Before Stage | Type | Notes |
| --- | --- | --- | --- |
| [Dependency] | [Stage XX] | [Product / Technical / Operational / Research / Contract] | [Why it matters] |

## Deferred Scope

| Deferred Item | Deferred From Stage | Target Stage Or Parking Lot | Reason |
| --- | --- | --- | --- |
| [Item] | [Stage XX] | [Stage YY / Parking Lot] | [Why this should wait] |

## Risks And Assumptions

| Item | Type | Affected Stage | Impact | Next Step |
| --- | --- | --- | --- | --- |
| [Risk, assumption, or open question] | [Risk / Assumption / Question] | [Stage XX] | [Why it matters] | [How to resolve] |

## Review Cadence

- **After every stage:** update this roadmap with what actually shipped, what changed, and what should be split or deferred.
- **Before each new sprint:** confirm the next stage is still the smallest valuable increment.
- **When scope grows:** split the stage instead of expanding the sprint.
- **When foundations change:** update the affected stage dependencies and sprint planning notes.

## Change Log

| Date | Change | Reason |
| --- | --- | --- |
| [YYYY-MM-DD] | [Created roadmap] | [Initial planning] |
