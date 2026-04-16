# Review Agent Protocol

This protocol defines how to create the Sprint Report, perform a high-signal code review, and verify conformance to the governing contracts that apply to the sprint.

## Purpose

The review agent performs:
1. General design and correctness review of the implementation
2. Explicit conformance verification against the sprint reasoning document and the governing contracts it mapped
3. Contract-aware review of architecture, correctness, risk, and operational consequences where relevant
4. Retrospective assessment and next-step recommendations

## Input

1. **Tracker document** - `ops/sprints/sprint-[XX]-[name]/tracker.md`
2. **Reasoning document** - `ops/sprints/sprint-[XX]-[name]/reasoning.md`
3. **Working code** - The implemented features
4. **Test results** - Unit, integration, and smoke test outputs
5. **Execution evidence** - Diagnostics, logs, screenshots, or notes collected during implementation

## Output

`ops/sprints/sprint-[XX]-[name]/report.md`

## Procedure

### Step 1: Read Context And Confirm Review Scope

Read the tracker, sprint reasoning document, and relevant governing contracts to determine:
- what the change was meant to do
- what it explicitly did not aim to do
- which requirements were declared applicable
- which evidence the sprint said review should verify

If critical review context is missing, ask targeted questions instead of guessing.

### Step 2: Summarise Intent

Briefly summarise:
- what changed
- what did not change
- what risks are most likely to matter for this sprint

### Step 3: Perform The Review In Order

Review in this order:
1. **Risk scan** - security, data loss, correctness, availability, and operational regression risk
2. **Design review** - cohesion, coupling, layering, interfaces, invariants, and failure modes
3. **Correctness review** - edge cases, error handling, determinism, and resource management
4. **Security review** - auth boundaries, injection risk, secret handling, unsafe deserialization, dependency and supply-chain concerns
5. **Performance review** - algorithmic complexity, hot paths, I/O patterns, caching, backpressure, and unnecessary work where relevant
6. **Maintainability review** - structure, duplication, readability, configuration, naming, and long-term operability
7. **Test review** - adequacy, determinism, negative coverage, and regression protection
8. **Documentation review** - public behavior, operator-facing notes, diagnostics, and follow-up docs
   - If backend code changed, verify that `backend/docs` has been updated to reflect the new reality

Focus on correctness, security, architecture, and operational truth before style.
Do not add low-value nitpicks unless they affect comprehension or violate a hard project standard.

### Step 4: Verify Contract Adherence

For each feature and each applicable requirement from the sprint reasoning document, verify conformance with evidence.

Review against the governing contracts the sprint reasoning document identified as applicable.

Confirm specifically where relevant:
- layering and dependency direction remain valid
- interfaces, seams, and boundaries remain coherent
- failure handling matches the applicable requirements
- observability, diagnostics, or other non-functional obligations are satisfied when required
- tests exercise required failure paths as well as happy paths when applicable

If the implementation deviates, record whether the deviation was planned or unplanned.

### Step 5: Record Findings With Severity And Evidence

Group findings by severity:
- **Blockers** - must fix before sign-off
- **High**
- **Medium**
- **Low / Nits**

For each finding, include:
- **Location** - file, module, feature, or requirement area
- **Issue** - what is wrong
- **Why it matters** - risk or consequence
- **Suggested fix** - the smallest credible correction
- **Evidence** - tests, code paths, runtime behavior, or missing proof

Severity policy:
- **Blocker** - security vulnerability, data corruption or loss, breaking change, crash or deadlock risk, or clearly incorrect behavior
- **High** - likely bug in edge cases, major maintainability issue, serious architecture drift, or significant performance regression
- **Medium** - meaningful improvement, missing coverage, or observable quality gap
- **Low / Nits** - minor readability or hygiene issues that do not threaten safe delivery

### Step 6: Finalise The Report

The report should leave a future reader able to answer:
- what was planned
- what was delivered
- whether the sprint conforms to the reasoning document and governing contracts
- what evidence supports that conclusion
- what must be fixed now versus later

Conclude with:
- a concise TL;DR
- testing and verification status
- security notes
- technical debt and carried-forward risks
- recommendations for the next sprint
