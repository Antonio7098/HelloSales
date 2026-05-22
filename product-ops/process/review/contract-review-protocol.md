# Review Agent Protocol

This protocol defines how a specialised review agent creates or updates the Sprint Report for its assigned governing requirement area.

## Purpose

A specialised review agent is assigned a specific requirement area, concern, or section of the governing contracts.

It verifies conformance for that area and updates the report with evidence-based findings, severity, and recommended fixes.

## Input

1. **Assigned Requirement Area** - The specific requirement area this agent is reviewing
2. **Tracker document** - `ops/sprints/sprint-[XX]-[name]/tracker.md`
3. **Reasoning document** - `ops/sprints/sprint-[XX]-[name]/reasoning.md`
4. **Working code** - The implemented features
5. **Test results** - Unit, integration, and smoke test outputs
6. **Existing Report** (if any) - `ops/sprints/sprint-[XX]-[name]/report.md`

## Output

Updated `ops/sprints/sprint-[XX]-[name]/report.md` with findings for the assigned requirement area.

## Procedure

### Step 1: Read The Assigned Area In Context

Read the sprint reasoning document and governing contracts, then identify the requirements relevant to your assigned area.

Determine:
- which features are affected
- what the sprint reasoning document says must be satisfied in this area
- what evidence should exist if the implementation conforms

### Step 2: Review The Implementation For That Area

Review the implementation using the same high-signal review order as the main review protocol, but specialise your analysis to the assigned area.

Examples:
- boundary reviewer focuses on layering, interfaces, and dependency direction
- failure-handling reviewer focuses on classification, propagation, and visibility of failures
- testing reviewer focuses on determinism, negative coverage, and regression protection

### Step 3: Verify Evidence And Tests

Check that tests, diagnostics, logs, and runtime behavior adequately cover the assigned area.

Do not treat absence of evidence as conformance.

### Step 4: Update Report

Update the report with findings for this requirement area:

```
## [Requirement Area Name]

### Conformance
- Status: [Conforming / Planned Deviation / Unplanned Deviation / Not Verifiable]
- Applicable Requirements: [List]
- Evidence: [Files, tests, diagnostics, or runtime proof]
- Notes: [Details]

### Findings
- [Severity] [Location]: [Issue] - [Why it matters] - [Suggested fix]
- [Severity] [Location]: [Issue] - [Why it matters] - [Suggested fix]
```

### Step 5: Document Issues

Note any issues found:
- Non-conformances
- Missing tests
- Missing evidence
- Technical debt in this area
- Follow-up work required before final sign-off or next sprint
