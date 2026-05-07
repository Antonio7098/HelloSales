# Sprint Reasoning: [Sprint Name]

> Project: HelloSales
> Sprint ID: sprint-[XX]-[name]
> Output: `ops/sprints/sprint-[XX]-[name]/reasoning.md`

## Overview

**Sprint:** [Name]
**Purpose:** [What this sprint delivers]
**Research:** [Reference to research document]
**Tracker:** [Reference to tracker document]
**Depends On:** [Earlier sprint outputs or "None"]

## Feature Links

- `ops/features/[feature-slug].md` - [How this sprint researches, builds, revises, ships, or supports the feature]
- [Use "None - [reason]" when this sprint has no direct product feature link]

## Requirement Map

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| [ARCH-CORE-001] | [Title] | [Architecture / Errors / Testing / ...] | [Applicable / Non-Applicable / Ambiguous] | [Reason] |
| [TEST-SMOKE-002] | [Title] | [Testing] | [Applicable] | [Reason] |

### Applicable Requirements

- **[Requirement ID]:** [Why it applies, what it seems to require, and what part of the sprint it constrains]
- **[Requirement ID]:** [Why it applies, what it seems to require, and what part of the sprint it constrains]

### Non-Applicable Requirements

- **[Requirement ID]:** [Why it does not apply to this sprint]

### Ambiguous Or Conflicting Requirements

- **[Requirement ID or pair]:** [What is unclear or in conflict]
- **[Requirement ID or pair]:** [Why interpretation is difficult]

### Open Questions

- [Question 1]
- [Question 2]

## Research Basis

**Research Source:** `ops/sprints/sprint-[XX]-[name]/research.md`
**Research Status:** [Complete and used / Incomplete with reason / Not needed with reason]

### Codebase Evidence Used

- `[path]`: [Finding used in reasoning]
- `[path]`: [Finding used in reasoning]

### External Guidance Used

- **[Tool / technology / option / practice]:** [Latest finding and how it affects this sprint]
- **[Tool / technology / option / practice]:** [Latest finding and how it affects this sprint]

### Research Findings Rejected

- **[Option or guidance]:** [Why it is not applicable in this codebase or sprint]
- **[Option or guidance]:** [Why it is not applicable in this codebase or sprint]

### Impact On Reasoning

- [Decision, risk, alternative, or evidence expectation changed or confirmed by current research]
- [Decision, risk, alternative, or evidence expectation changed or confirmed by current research]

## Feature Analysis

### Feature 1: [Feature Name]

**Description:** [What the feature does]

**Affected Areas**
- [Code paths, modules, entrypoints, runtime surfaces, or data boundaries touched]

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| [ARCH-ENTRY-001] | [Constraint] | [Affected boundary] | [Test/log/review evidence] |
| [ERR-CORE-001] | [Constraint] | [Affected failure path] | [Error/event evidence] |

**Current-System Analysis**
- [Relevant existing code, seams, or constraints]
- [What must remain true]

**Research Evidence Applied**
- [Codebase or external research finding that affects this feature]
- [If no research affects this feature, explain why the feature is constrained only by requirements and existing code]

**Options Considered**
- **Option A:** [Description]
- **Option B:** [Description]
- **Option C:** [Description or "Not needed"]

**Chosen Approach**
- [What will be done]

**Decision Justification**
- [Why the chosen approach best satisfies the requirements in this codebase]
- [Why the rejected alternatives are worse here]
- [Trade-offs and second-order effects]

**Execution Notes**
- [What must be preserved during implementation]
- [What discovery would force reasoning revision]

**Expected Evidence**
- **Tests:** [Unit / integration / smoke / failure-path evidence expected]
- **Runtime Evidence:** [Logs / events / diagnostics / health / task state expected]
- **Review Checks:** [What review must be able to confirm]

---

### Feature 2: [Feature Name]

**Description:** [What the feature does]

**Affected Areas**
- [Code paths, modules, entrypoints, runtime surfaces, or data boundaries touched]

**Requirement Mapping**
| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| [Requirement ID] | [Constraint] | [Affected boundary] | [Evidence] |
| [Requirement ID] | [Constraint] | [Affected boundary] | [Evidence] |

**Current-System Analysis**
- [Relevant existing code, seams, or constraints]
- [What must remain true]

**Research Evidence Applied**
- [Codebase or external research finding that affects this feature]
- [If no research affects this feature, explain why the feature is constrained only by requirements and existing code]

**Options Considered**
- **Option A:** [Description]
- **Option B:** [Description]
- **Option C:** [Description or "Not needed"]

**Chosen Approach**
- [What will be done]

**Decision Justification**
- [Why the chosen approach best satisfies the requirements in this codebase]
- [Why the rejected alternatives are worse here]
- [Trade-offs and second-order effects]

**Execution Notes**
- [What must be preserved during implementation]
- [What discovery would force reasoning revision]

**Expected Evidence**
- **Tests:** [Unit / integration / smoke / failure-path evidence expected]
- **Runtime Evidence:** [Logs / events / diagnostics / health / task state expected]
- **Review Checks:** [What review must be able to confirm]

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| [Requirement ID] | [Deviation] | [Why needed] | [Impact] | [Temporary/Permanent] | [Action] |

## Cross-Cutting Reasoning

### Major Decision Summary

- **[Decision 1]:** [Requirement IDs + why chosen]
- **[Decision 2]:** [Requirement IDs + why chosen]

### Trade-offs

- [Trade-off 1]: [Reason]
- [Trade-off 2]: [Reason]

### Assumptions

- [Assumption 1]
- [Assumption 2]

### Dependencies

- [Previous sprint or system dependency]: [What is needed]
- [Unfinished work]: [Impact]

### Evidence Review Checklist

- [Review can trace every feature decision back to explicit requirement IDs]
- [Review can trace relevant research to decisions, alternatives, risks, or evidence expectations]
- [Review can verify the planned tests and runtime evidence exist]
- [Review can identify any planned or unplanned deviations by requirement ID]

## Phase Exit Criteria

- [ ] Tracker scope is fully covered
- [ ] Sprint research was read and used
- [ ] Applicable requirements are mapped
- [ ] Ambiguous and non-applicable requirements are recorded where relevant
- [ ] Codebase and external research findings are tied to decisions, risks, alternatives, or evidence expectations where relevant
- [ ] Important decisions are explicitly justified
- [ ] Non-trivial alternatives are discussed
- [ ] Deviations, assumptions, risks, and unknowns are documented
- [ ] Expected evidence is defined

## Documentation Updates

- [Contract or doc]: [Why it must change]
- [Contract or doc]: [Why it must change]
