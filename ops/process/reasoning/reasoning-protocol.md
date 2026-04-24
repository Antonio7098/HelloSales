# Sprint Reasoning Protocol

This protocol defines how to create the Sprint Reasoning document.

## Purpose

The reasoning agent reads the governing contracts and relevant existing code, then produces a reasoning document that maps sprint scope to contract requirements and justifies the decisions needed to satisfy them.

The Sprint Reasoning is not a restatement of sprint scope and not merely an implementation blueprint.
It is a structured reasoning artifact whose job is to force deep analysis before coding:
- what requirements apply
- how they constrain the change
- what design options exist
- why one approach is chosen over another
- where uncertainty, trade-offs, and deviations remain

## Inputs

1. **Governing contracts** - The contract documents currently in force for the work being reviewed
2. **Relevant existing code** - Code and tests relevant to the sprint scope
3. **Current external guidance** - Latest relevant tools, technologies, options, best practices, and official guidance, researched when not already known from recent verified context
4. **Known dependencies or unfinished work** - Existing constraints that affect delivery

## Output

`ops/sprints/sprint-[XX]-[name]/reasoning.md`

## Procedure

### Step 1: Read Governing Contracts

Read the governing contract documents and extract the requirements that apply to the sprint.

You must produce a requirement map with:
- **Applicable requirements** - contract requirements that directly constrain this sprint
- **Non-applicable requirements** - requirements reviewed but not relevant to the sprint scope
- **Ambiguous requirements** - requirements that are unclear, conflicting, or underspecified
- **Open questions** - anything that cannot be resolved from the docs and code alone

For each applicable requirement, determine:
- what the requirement appears to mean in this sprint's context
- what code or behavior it constrains
- what design choices are available
- what evidence would later show conformance or deviation

### Step 2: Read Relevant Existing Code

Examine existing code and tests to understand:
- how similar features are structured
- existing patterns and seams already in use
- where authoritative logic lives today
- whether the current implementation already constrains the design

The reasoning must stay grounded in the actual codebase rather than idealised structure.

### Step 3: Research Current Tools, Options, And Guidance

If you have not already done so from recent verified context, research the latest relevant tools, technologies, implementation options, best practices, and official guidance that could affect the sprint.

The research should establish:
- which current tools or technologies are relevant to the sprint scope
- whether any version-specific behavior, deprecation, security guidance, or recommended practice affects the design
- what credible implementation options exist outside the current codebase
- where current best practice conflicts with existing local patterns or governing contracts
- which sources are authoritative enough to influence a delivery decision

Record how the research affects reasoning:
- **Relevant findings** - current guidance or options that shape the sprint
- **Rejected findings** - researched options that are not applicable and why
- **Source basis** - official docs, release notes, standards, or other authoritative sources used
- **Impact on decisions** - which design choices, risks, or evidence expectations changed because of the research

If no external research is needed, state why the existing verified context is sufficient.

### Step 4: Analyse Each Feature Against The Requirements

For each in-scope feature, analyse:
- which requirements apply
- which parts of the current system are affected
- what invariants or constraints must remain true
- what implementation options are plausible
- why one option is preferable to the alternatives
- what risks, trade-offs, and second-order effects follow from that choice
- what evidence execution and review must later produce

The emphasis is reasoning, not just listing components.
The document should capture the chain of analysis that leads from requirement to decision.

### Step 5: Justify Decisions Explicitly

For every meaningful design or implementation decision, record:
- **Requirement context** - which requirement or set of requirements drove the decision
- **Options considered** - credible alternatives that were available
- **Chosen approach** - what will be done
- **Why this approach** - why it best satisfies the requirements in the current codebase
- **Why not the alternatives** - what was rejected and why
- **Evidence to verify later** - how review will know the decision was implemented correctly

### Step 6: Record Deviations, Risks, Assumptions, and Unknowns

If the sprint cannot fully satisfy a governing rule or the preferred design, document a deviation explicitly.

Each deviation must include:
- **Deviation** - which requirement or chosen approach is not being followed
- **Reason** - why the deviation is necessary
- **Risk** - what this introduces
- **Disposition** - temporary or permanent
- **Follow-up** - exact remediation task or next-sprint action

Also record:
- assumptions made during reasoning
- unresolved design questions
- external dependencies that could block delivery
- places where the contract language is too ambiguous to support a confident decision

### Step 7: Write the Reasoning Document

Write the document using the template, ensuring:
1. **Readable prose format** - easy to read under delivery pressure
2. **Clear requirement mapping** - show which requirements apply and how they shape the change
3. **Deep reasoning** - explain why each important decision follows from the requirements and codebase reality
4. **Explicit alternatives** - show what was considered and rejected when the choice is non-trivial
5. **Complete coverage** - every in-scope feature is analysed
6. **Explicit evidence expectations** - define what execution and review must later verify
7. **Trade-offs documented** - any deviations or compromises are explicit
8. **Current guidance reflected** - latest relevant research is either documented or explicitly deemed unnecessary

### Step 8: Verify Exit Criteria

Before completing, verify:
- [ ] Sprint scope is covered
- [ ] Applicable requirements are mapped
- [ ] Non-applicable and ambiguous requirements are recorded when relevant
- [ ] Latest relevant tools, technologies, options, best practices, and guidance were researched or explicitly deemed unnecessary
- [ ] Research findings are tied to decisions, risks, alternatives, or evidence expectations where relevant
- [ ] Important decisions are justified against the requirements
- [ ] Alternatives are discussed where the choice is non-trivial
- [ ] Deviations, assumptions, risks, and unknowns are documented
- [ ] Execution evidence expectations are defined

## Key Principles

1. **Be thorough** - the document is a reasoning artifact, not a shallow checklist
2. **Be requirement-driven** - map sprint scope to specific governing requirements
3. **Stay grounded** - reference actual code patterns and seams
4. **Stay current** - research latest relevant tools, technologies, options, best practices, and guidance when not already verified
5. **Justify decisions explicitly** - do not jump from requirement to conclusion without explanation
6. **Record deviations explicitly** - do not bury them in prose
7. **Design for reviewability** - define evidence that later review can verify
