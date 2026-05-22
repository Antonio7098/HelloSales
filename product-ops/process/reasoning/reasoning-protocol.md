# Sprint Reasoning Protocol

This protocol defines how to create the Sprint Reasoning document.

## Purpose

The reasoning agent reads the governing contracts, the sprint research document, and relevant existing code, then produces a reasoning document that maps sprint scope to contract requirements and justifies the decisions needed to satisfy them.

The Sprint Reasoning is not a restatement of sprint scope and not merely an implementation blueprint.
It is a structured reasoning artifact whose job is to force deep analysis before coding:
- what requirements apply
- how they constrain the change
- what design options exist
- why one approach is chosen over another
- where uncertainty, trade-offs, and deviations remain

## Inputs

1. **Governing contracts** - The contract documents currently in force for the work being reviewed
2. **Linked feature documents** - Product requirements in `ops/features/`, when the sprint supports one or more features
3. **Sprint research** - `ops/sprints/sprint-[XX]-[name]/research.md`, containing codebase evidence and current external guidance gathered before reasoning
4. **Relevant existing code** - Code and tests relevant to the sprint scope, used to verify and deepen the research where needed
5. **Known dependencies or unfinished work** - Existing constraints that affect delivery
2. **Sprint research** - `ops/sprints/sprint-[XX]-[name]/research.md`, containing codebase evidence and current external guidance gathered before reasoning
3. **Relevant existing code** - Code and tests relevant to the sprint scope, used to verify and deepen the research where needed
4. **Known dependencies or unfinished work** - Existing constraints that affect delivery

## Output

`ops/sprints/sprint-[XX]-[name]/reasoning.md`

## Procedure

### Step 1: Read Governing Contracts

> **IMPORTANT**: You must read EVERY contract document that applies to this work. Do not skip or assume any contract is irrelevant without reading it first.

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

### Step 2: Read Linked Feature Documents

Read every feature document linked from the sprint research, tracker, or planning brief.

Extract:
- the product problem and desired outcome
- primary users and stakeholders
- observable product requirements
- product rules, edge cases, and out-of-scope items
- success criteria
- sprint relationship and delivery status

Reasoning must preserve the product intent while translating the sprint's portion into technical decisions. If a feature document is missing, stale, or too ambiguous to support reasoning, update it or record the ambiguity before finalizing affected decisions.

### Step 3: Read Relevant Existing Code

Read the codebase evidence in the sprint research document, then examine relevant code and tests as needed to verify or deepen that evidence.

Understand:
- how similar features are structured
- existing patterns and seams already in use
- where authoritative logic lives today
- whether the current implementation already constrains the design

The reasoning must stay grounded in the actual codebase rather than idealised structure.

### Step 4: Read Sprint Research And Identify Decision Inputs
### Step 3: Read Sprint Research And Identify Decision Inputs

Read `research.md` before making design decisions.

Extract:
- codebase findings that constrain the sprint
- current external guidance that affects tools, implementation options, security, reliability, or compatibility
- key repositories, examples, or code snippets that may guide implementation
- researched options that were rejected and why
- risks and open questions that reasoning must resolve

Reasoning must explicitly use the research where relevant.
If the research is incomplete, stale, or missing evidence needed for a confident decision, update or request an update to `research.md` before finalizing the affected reasoning.

### Step 5: Analyse Each Feature Against The Requirements
### Step 4: Analyse Each Feature Against The Requirements

For each in-scope feature, analyse:
- which linked product feature document it supports, if any
- which requirements apply
- which parts of the current system are affected
- what invariants or constraints must remain true
- which research findings affect the design
- what implementation options are plausible
- why one option is preferable to the alternatives
- what risks, trade-offs, and second-order effects follow from that choice
- what evidence execution and review must later produce

The emphasis is reasoning, not just listing components.
The document should capture the chain of analysis that leads from requirement to decision.

### Step 6: Justify Decisions Explicitly

For every meaningful design or implementation decision, record:
- **Requirement context** - which requirement or set of requirements drove the decision
- **Options considered** - credible alternatives that were available
- **Chosen approach** - what will be done
- **Why this approach** - why it best satisfies the requirements in the current codebase
- **Why not the alternatives** - what was rejected and why
- **Evidence to verify later** - how review will know the decision was implemented correctly

### Step 7: Record Deviations, Risks, Assumptions, and Unknowns

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

### Step 8: Write the Reasoning Document

Write the document using the template, ensuring:
1. **Readable prose format** - easy to read under delivery pressure
2. **Feature links recorded** - linked product feature docs are present or explicitly marked not applicable
3. **Clear requirement mapping** - show which requirements apply and how they shape the change
4. **Deep reasoning** - explain why each important decision follows from product intent, requirements, and codebase reality
5. **Explicit alternatives** - show what was considered and rejected when the choice is non-trivial
6. **Complete coverage** - every in-scope feature is analysed
7. **Explicit evidence expectations** - define what execution and review must later verify
8. **Trade-offs documented** - any deviations or compromises are explicit
9. **Research reflected** - findings from `research.md` are tied to decisions, alternatives, risks, and evidence expectations
2. **Clear requirement mapping** - show which requirements apply and how they shape the change
3. **Deep reasoning** - explain why each important decision follows from the requirements and codebase reality
4. **Explicit alternatives** - show what was considered and rejected when the choice is non-trivial
5. **Complete coverage** - every in-scope feature is analysed
6. **Explicit evidence expectations** - define what execution and review must later verify
7. **Trade-offs documented** - any deviations or compromises are explicit
8. **Research reflected** - findings from `research.md` are tied to decisions, alternatives, risks, and evidence expectations

### Step 9: Verify Exit Criteria

Before completing, verify:
- [ ] Every governing contract document was read in full
- [ ] Linked feature documents were read, or no direct feature link is recorded with reason
- [ ] Sprint research was read and used
- [ ] Sprint scope is covered
- [ ] Applicable requirements are mapped
- [ ] Non-applicable and ambiguous requirements are recorded when relevant
- [ ] Codebase and external research findings are tied to decisions, risks, alternatives, or evidence expectations where relevant
- [ ] Important decisions are justified against the requirements
- [ ] Alternatives are discussed where the choice is non-trivial
- [ ] Deviations, assumptions, risks, and unknowns are documented
- [ ] Execution evidence expectations are defined
- [ ] Linked feature documents backlink to this sprint when applicable

## Key Principles

1. **Be thorough** - the document is a reasoning artifact, not a shallow checklist
2. **Be requirement-driven** - map sprint scope to specific governing requirements
3. **Preserve product intent** - use linked feature documents as the product source of truth
4. **Stay grounded** - reference actual code patterns and seams
5. **Reason from research** - use `research.md` as the source of current codebase and external evidence
6. **Justify decisions explicitly** - do not jump from requirement to conclusion without explanation
7. **Record deviations explicitly** - do not bury them in prose
8. **Design for reviewability** - define evidence that later review can verify
3. **Stay grounded** - reference actual code patterns and seams
4. **Reason from research** - use `research.md` as the source of current codebase and external evidence
5. **Justify decisions explicitly** - do not jump from requirement to conclusion without explanation
6. **Record deviations explicitly** - do not bury them in prose
7. **Design for reviewability** - define evidence that later review can verify
