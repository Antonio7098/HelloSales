<<<<<<< HEAD
# Research: [Research Area]

> Project: HelloSales
> Research Area: [Area]
> Output: `ops/research/[research-area-slug].md`
> Research Date: [YYYY-MM-DD]

## Brief

**Research Area:** [Topic, capability, tool, product question, or operational question]
**Goals:** [What the user wants to learn, decide, compare, validate, or prepare to implement]
**Key Considerations:** [Important criteria, tradeoffs, preferences, or concerns]
**Constraints:** [Technical, product, operational, security, budget, time, compatibility, or policy constraints]
**Non-Goals / Exclusions:** [What should not be covered]
**Expected Use:** [Decision support, implementation planning, architecture comparison, vendor/tooling assessment, product direction, etc.]

## Research Questions

- [Question the research should answer]
- [Question the research should answer]
- [Question the research should answer]

## General Findings

### Summary

[Concise summary of the main findings that can be understood without knowing the HelloSales codebase.]

### Current Guidance, Tools, And Practices

- **[Finding]:** [Current guidance, tool, API, practice, or pattern and why it matters]
- **[Finding]:** [Current guidance, tool, API, practice, or pattern and why it matters]

### Options And Tradeoffs

| Option | Strengths | Weaknesses / Risks | Best Fit |
| --- | --- | --- | --- |
| [Option A] | [Strengths] | [Weaknesses or risks] | [When this option fits] |
| [Option B] | [Strengths] | [Weaknesses or risks] | [When this option fits] |

### Sources Consulted

| Source | Type | Finding | Credibility | Limits |
| --- | --- | --- | --- | --- |
| [Official docs / release notes / repo / standard] | [Primary / Secondary] | [Finding] | [Why reliable] | [Uncertainty, version limit, or missing context] |
| [Official docs / release notes / repo / standard] | [Primary / Secondary] | [Finding] | [Why reliable] | [Uncertainty, version limit, or missing context] |

### Rejected Or Low-Confidence Findings

- **[Option or guidance]:** [Why it is not applicable, too weak, obsolete, risky, or misaligned with the brief]
- **[Option or guidance]:** [Why it is not applicable, too weak, obsolete, risky, or misaligned with the brief]

## Codebase Survey

**Codebase Survey Status:** [Completed / Partial with reason / Not needed with reason]
=======
# Sprint Research: [Sprint Name]

> Project: HelloSales
> Sprint ID: sprint-[XX]-[name]
> Output: `ops/sprints/sprint-[XX]-[name]/research.md`

## Overview

**Sprint:** [Name]
**Purpose:** [What this sprint is expected to deliver or investigate]
**Reasoning Output:** `ops/sprints/sprint-[XX]-[name]/reasoning.md`
**Tracker Output:** `ops/sprints/sprint-[XX]-[name]/tracker.md`
**Depends On:** [Earlier sprint outputs or "None"]

## Research Questions

- [Question reasoning must answer later]
- [Question reasoning must answer later]
- [Question reasoning must answer later]

## Codebase Research

**Codebase Search Status:** [Completed / Partial with reason / Not needed with reason]
>>>>>>> origin/main

### Searches Run

- `[command or search terms]`: [What this was intended to find]
- `[command or search terms]`: [What this was intended to find]

### Key Codebase Evidence

<<<<<<< HEAD
| Evidence | Location | Finding | Relevance |
| --- | --- | --- | --- |
| [Module/service/test/doc/config] | `[path]` | [What exists] | [How it affects the research area] |
| [Module/service/test/doc/config] | `[path]` | [What exists] | [How it affects the research area] |

### Integration Points

- **[Integration point]:** [Relevant files, interfaces, workflows, or runtime paths]
- **[Integration point]:** [Relevant files, interfaces, workflows, or runtime paths]
=======
| Evidence | Location | Finding | Relevance For Reasoning |
| --- | --- | --- | --- |
| [Module/service/test/doc] | `[path]` | [What exists] | [How it should shape reasoning] |
| [Module/service/test/doc] | `[path]` | [What exists] | [How it should shape reasoning] |
>>>>>>> origin/main

### Existing Patterns To Preserve

- **[Pattern]:** [Where it appears and why it matters]
- **[Pattern]:** [Where it appears and why it matters]

<<<<<<< HEAD
### Constraints And Gaps

- **[Constraint or gap]:** [Evidence and implication]
- **[Constraint or gap]:** [Evidence and implication]
=======
### Constraints, Gaps, And Integration Points

- **[Constraint or gap]:** [Evidence and implication]
- **[Integration point]:** [Evidence and implication]
>>>>>>> origin/main

### Nearby Tests And Evidence Paths

- `[test path or smoke command]`: [What it already verifies]
- `[test path or smoke command]`: [How it may need to change]

<<<<<<< HEAD
## Codebase Implications

### How The Findings Map To HelloSales

- [General finding and how it applies to the current codebase]
- [General finding and how it applies to the current codebase]

### Likely Implementation Paths

- **Path A:** [Evidence-backed implementation approach, affected areas, and tradeoffs]
- **Path B:** [Evidence-backed implementation approach, affected areas, and tradeoffs]
- **Path C:** [Evidence-backed implementation approach or "Not needed"]

### Recommended Direction

[Recommendation, if the evidence supports one. Separate the recommendation from facts and cite the evidence it depends on.]

### Risks And Open Questions

- **[Risk or question]:** [Why it matters and what evidence is missing]
- **[Risk or question]:** [Why it matters and what evidence is missing]

### Suggested Evidence Expectations

- **Tests:** [Evidence an implementation should provide]
- **Runtime Evidence:** [Logs/events/diagnostics/smoke evidence suggested by research]
- **Review Checks:** [What review should be able to confirm]

## Research Log

### Codebase Searches

- `[command or search terms]`: [Result summary]
- `[command or search terms]`: [Result summary]

### Web Searches

- `[search query]`: [What this was intended to find]
- `[search query]`: [What this was intended to find]

## Exit Criteria

- [ ] Research area, goals, key considerations, constraints, and non-goals are clear
- [ ] Codebase survey was performed before web research
- [ ] Relevant existing code, tests, docs, configs, and operational artifacts are cited
- [ ] Current web research was performed or explicitly deemed unnecessary with reason
- [ ] Official or authoritative sources are preferred for external claims
- [ ] Latest tools, guidance, repos, examples, and snippets are captured where relevant
- [ ] General findings are presented before codebase-specific implications
- [ ] Codebase integration points and implementation paths are identified
- [ ] Weak, obsolete, or inapplicable findings are rejected where relevant
- [ ] Risks, open questions, and evidence gaps are visible
=======
## Web Research

**Web Research Status:** [Completed / Not needed because current verified context is sufficient / Deferred with reason]
**Search Date:** [YYYY-MM-DD]

### Searches Run

- `[search query]`: [What this was intended to find]
- `[search query]`: [What this was intended to find]

### Sources Consulted

| Source | Type | Finding | Credibility | Relevance For Reasoning |
| --- | --- | --- | --- | --- |
| [Official docs / release notes / repo / standard] | [Primary / Secondary] | [Finding] | [Why reliable] | [How it should shape reasoning] |
| [Official docs / release notes / repo / standard] | [Primary / Secondary] | [Finding] | [Why reliable] | [How it should shape reasoning] |

### Latest Tools, Guidance, And Practices

- **[Tool / API / practice]:** [Latest finding and how it affects this sprint]
- **[Tool / API / practice]:** [Latest finding and how it affects this sprint]

### Key Repositories Or Code Examples

- **[Repository / snippet source]:** [Relevant implementation idea, snippet summary, or pattern]
- **[Repository / snippet source]:** [Relevant implementation idea, snippet summary, or pattern]

### Options Or Guidance Rejected

- **[Option or guidance]:** [Why it is not applicable, too weak, obsolete, risky, or misaligned with this codebase]
- **[Option or guidance]:** [Why it is not applicable, too weak, obsolete, risky, or misaligned with this codebase]

## Research Handoff To Reasoning

### Findings Reasoning Should Use

- [Codebase or external finding that should influence decisions]
- [Codebase or external finding that should influence decisions]

### Viable Options To Consider

- **Option A:** [Evidence-backed option]
- **Option B:** [Evidence-backed option]
- **Option C:** [Evidence-backed option or "Not needed"]

### Risks And Open Questions

- **[Risk or question]:** [Why reasoning must address it]
- **[Risk or question]:** [Why reasoning must address it]

### Suggested Evidence Expectations

- **Tests:** [Evidence the eventual tracker/reasoning should require]
- **Runtime Evidence:** [Logs/events/diagnostics/smoke evidence suggested by research]
- **Review Checks:** [What review should be able to confirm]

## Phase Exit Criteria

- [ ] Sprint scope and research questions are clear
- [ ] Codebase search was performed first
- [ ] Relevant existing code, tests, docs, and sprint artifacts are cited
- [ ] Current web research was performed or explicitly deemed unnecessary with reason
- [ ] Official or authoritative sources are preferred for external claims
- [ ] Latest tools, guidance, repos, examples, and snippets are captured where relevant
- [ ] Weak, obsolete, or inapplicable findings are rejected where relevant
- [ ] Open questions and risks are visible
- [ ] The reasoning handoff identifies what evidence should shape later decisions
>>>>>>> origin/main
