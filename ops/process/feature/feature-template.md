# Feature: [Feature Name]

> Project: HelloSales
> Feature ID: [feature-slug]
> Output: `ops/features/[feature-slug].md`
> Created: [YYYY-MM-DD]
> Status: [Draft / Ready For Sprint Planning / In Delivery / Shipped / Deferred]
> Maturity Score: [0-100] - [Raw Idea / Shaped Draft / Product-Defined / Sprint-Planning Ready / Delivery Mature]

## Product Summary

**Feature Name:** [Plain-language name]
**Short Description:** [One or two sentences describing what the feature gives the user]
**Primary User:** [Who mainly uses or benefits from this feature]
**Secondary Users:** [Other users or "None"]
**Priority:** [High / Medium / Low]
**Target Timing:** [Date, milestone, customer commitment, or "None"]
**Documentation Depth:** [Leverage / Neutral / Overhead]

## Maturity Score

**Score:** [0-100]
**Band:** [Raw Idea / Shaped Draft / Product-Defined / Sprint-Planning Ready / Delivery Mature]
**Last Scored:** [YYYY-MM-DD]

### Score Rationale

- **Why this score:** [Top reasons the feature is at this maturity level]
- **Main gaps:** [The biggest missing decisions, evidence, or clarity]
- **Highest-leverage next questions:** [Questions or edits that would raise maturity most]

### Scoring Breakdown

| Dimension | Score / 10 | Notes |
| --- | ---: | --- |
| Problem clarity | [0-10] | [Specific pain or opportunity and evidence] |
| Outcome clarity | [0-10] | [Measurable or observable desired result] |
| User/JTBD clarity | [0-10] | [Primary user, context, and job to be done] |
| Journey clarity | [0-10] | [Happy path and key moments] |
| Requirements quality | [0-10] | [Observable, non-technical, precise behavior] |
| Rules and permissions | [0-10] | [Role, visibility, eligibility, and business rules] |
| Scope control | [0-10] | [V1, later phases, and out-of-scope separation] |
| Edge cases | [0-10] | [Exceptions and failure states] |
| Risks and assumptions | [0-10] | [Value, usability, feasibility, viability, pre-mortem] |
| Delivery linkage | [0-10] | [Sprint links, dependencies, rollout, adoption] |

## Sprint Links

| Sprint | Relationship | Status | Notes |
| --- | --- | --- | --- |
| `ops/sprints/sprint-[XX]-[name]/` | [Researches / Builds / Revises / Ships / Supports] | [Planned / In Progress / Complete / Deferred] | [What this sprint contributes] |

## Outcome And Opportunity

### Desired Outcome

[Describe the user or business outcome this feature is expected to move. Include a metric if known, or an observable behavior if a metric is not yet available.]

### Opportunity Or Pain

[Describe the specific customer need, sales workflow pain, operational gap, or product opportunity.]

### Why Now

[Explain why this matters now. Include customer pressure, strategic timing, workflow cost, risk, or "Unknown" if not yet clear.]

## Why This Matters

[Explain the business problem, user pain, sales workflow issue, operational gap, or customer outcome this feature addresses.]

## Problem Today

[Describe what happens without this feature. Keep this product-focused: manual work, confusion, missed opportunities, unclear status, slow follow-up, poor handoff, or similar.]

## Desired Outcome

[Describe what should be better after this feature exists.]

## Users And Context

### Primary User

[Who they are, what they are trying to do, and when this feature matters to them.]

### Job To Be Done

When [situation or trigger], the user wants to [motivation or action], so they can [desired progress or outcome].

### Other Stakeholders

- **[Stakeholder]:** [What they need from the feature]
- **[Stakeholder]:** [What they need from the feature]

## Trigger

[What causes the user to need or start this feature?]

Examples:
- a new lead arrives
- a sales rep finishes a call
- a manager reviews pipeline health
- a customer asks for a follow-up

## User Journey

Describe the happy path in plain language.

1. [User action or system moment]
2. [User action or system response]
3. [User action or system response]
4. [Outcome]

## Product Requirements

Write observable product behavior, not implementation details.

- **[Requirement 1]:** [What the user or system must be able to do]
- **[Requirement 2]:** [What must be shown, captured, prevented, or confirmed]
- **[Requirement 3]:** [Rule or behavior]

### Given / When / Then Scenarios

- **Scenario:** [Name]
  - **Given:** [User/context/state]
  - **When:** [Action or event]
  - **Then:** [Observable product result]

## Information And Controls

### The User Needs To See

- [Information, status, message, field, option, or result]
- [Information, status, message, field, option, or result]

### The User Needs To Do

- [Action, choice, confirmation, edit, approval, or dismissal]
- [Action, choice, confirmation, edit, approval, or dismissal]

## Rules And Product Logic

Keep this non-technical. Describe business rules and expected behavior.

- [Rule, permission, threshold, timing, visibility, or eligibility condition]
- [Rule, permission, threshold, timing, visibility, or eligibility condition]

## Permissions And Visibility

| Role / User Type | Can See | Can Do | Notes |
| --- | --- | --- | --- |
| [Sales rep / Manager / Admin / Customer] | [Data, status, control, or message] | [Allowed actions] | [Limits, ownership rules, or exceptions] |

## Success Criteria

The feature is successful when:

- [Concrete product outcome or behavior]
- [Concrete product outcome or behavior]
- [Concrete product outcome or behavior]

### Adoption And Success Signals

- **Usage signal:** [How we will know users are discovering or using it]
- **Outcome signal:** [How we will know the desired outcome is improving]
- **Quality signal:** [How we will know the experience is reliable or trusted]

## Edge Cases And Exceptions

- **[Case]:** [Expected product behavior]
- **[Case]:** [Expected product behavior]

## Scope And Phasing

### V1

- [Smallest useful version behavior]
- [Smallest useful version behavior]

### Later Phases

- [Future capability or enhancement]
- [Future capability or enhancement]

## Out Of Scope

- [What this version should not include]
- [What should be deferred to a future feature or sprint]

## Dependencies

- **Product dependency:** [Another feature, decision, user workflow, or policy]
- **Operational dependency:** [Relevant sprint, research, rollout condition, or "None"]

## Risks And Open Questions

| Item | Type | Impact | Owner / Next Step |
| --- | --- | --- | --- |
| [Question or risk] | [Question / Risk / Assumption] | [Why it matters] | [Who resolves it or what happens next] |

## Product Risks

| Risk Type | Current Assessment | Mitigation / Next Step |
| --- | --- | --- |
| Value risk | [Will users want or use this?] | [How to validate or reduce risk] |
| Usability risk | [Can users understand and use it?] | [How to validate or reduce risk] |
| Feasibility risk | [Is this likely buildable in the expected scope?] | [What sprint research or engineering input is needed] |
| Viability risk | [Does this work for the business, policy, security, legal, or operational model?] | [How to validate or reduce risk] |

## Pre-Mortem

Imagine this feature failed after launch. The likely reasons are:

- **Critical failure risk:** [What could make the feature fail outright]
- **Manageable risk:** [What could create friction but can be mitigated]
- **Unspoken concern:** [The obvious issue that needs to be made explicit]

## Rollout And Adoption

- **Rollout approach:** [All users / selected users / internal first / phased / unknown]
- **User communication:** [How users should learn this exists]
- **Adoption support:** [Onboarding, empty states, examples, manager guidance, or "None"]
- **Rollback or fallback:** [Expected product behavior if rollout pauses or fails]

## Release Notes Draft

[Plain-language release note or customer-facing summary. Keep it short.]

## Final Product Summary

[Describe the feature in 2 to 5 sentences for someone new to the work.]

## Handover Checklist

- [ ] The primary user is clear
- [ ] The problem and desired outcome are clear
- [ ] The desired outcome, opportunity, and why-now are clear
- [ ] The job to be done is clear
- [ ] The happy-path journey is described
- [ ] Product requirements are observable and non-technical
- [ ] Permissions and visibility are explicit
- [ ] Success criteria are concrete
- [ ] Adoption and success signals are identified
- [ ] Edge cases and exceptions are visible
- [ ] V1, later phases, and out-of-scope items are separated
- [ ] Product risks and pre-mortem concerns are captured
- [ ] Out-of-scope items are explicit
- [ ] Rollout and adoption considerations are captured or marked not needed
- [ ] Maturity score is current and includes rationale
- [ ] Sprint links are current
- [ ] Linked sprint artifacts backlink to this feature
