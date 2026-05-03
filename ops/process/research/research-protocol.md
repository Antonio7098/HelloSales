# Sprint Research Protocol

This protocol defines how to create the Sprint Research document.

## Purpose

The research agent gathers the codebase evidence and current external guidance needed for sprint reasoning.

The Sprint Research is not a design decision document and not a tracker.
It is a structured evidence artifact whose job is to make reasoning current and grounded before design choices are justified:
- what the existing code already does
- where relevant patterns, seams, and constraints live
- what current external guidance says
- which tools, libraries, repositories, examples, and snippets may guide the sprint
- which findings are credible enough to influence reasoning

## Inputs

1. **Sprint scope or brief** - The proposed change, problem, or capability being planned
2. **Existing codebase** - Source, tests, docs, configs, and sprint artifacts relevant to the scope
3. **Governing contracts** - Contract documents that may constrain research focus
4. **External sources** - Official docs, release notes, standards, current best-practice guidance, key repositories, and credible implementation examples

## Output

`ops/sprints/sprint-[XX]-[name]/research.md`

## Procedure

### Step 1: Clarify Research Scope

Identify the sprint topic, expected delivery surface, and likely affected areas.

Record:
- the sprint name or working title
- the problem or capability being researched
- known dependencies or prior sprint artifacts
- any explicit exclusions
- the questions reasoning must be able to answer later

### Step 2: Search The Codebase For Key Evidence

Search the codebase before searching externally.

Use repository search and file reads to find:
- existing modules, services, routes, tools, workflows, tests, prompts, settings, diagnostics, and docs related to the scope
- similar implemented features or prior sprint artifacts
- established naming, layering, composition, error, observability, testing, and documentation patterns
- current seams that can be reused
- constraints, TODOs, gaps, brittle areas, and likely integration points

Record codebase evidence with file paths and concise notes.
Distinguish direct evidence from inference.

The research must answer:
- what already exists
- what should probably be reused
- what should probably not be duplicated
- what current implementation details could constrain the design
- what tests or smoke paths already cover nearby behavior

### Step 3: Search The Web For Current Guidance

Search the web for current information when the sprint touches technologies, tools, providers, security practices, standards, model behavior, frameworks, third-party APIs, or implementation patterns that may have changed.

Research should cover, where relevant:
- official documentation and release notes
- current best practices and security guidance
- latest supported tools, SDKs, APIs, models, frameworks, or provider capabilities
- deprecations, migrations, pricing or quota constraints, and breaking changes
- key repositories that show mature implementation patterns
- focused code snippets that demonstrate a concrete integration or edge case
- credible comparison material for options the reasoning phase may need to choose between

Prefer authoritative sources:
- official docs and API references
- standards bodies and security advisories
- maintainers' release notes and repository examples
- well-maintained source repositories

Use secondary sources only when they help discover primary sources or when clearly labeled as non-authoritative.

### Step 4: Evaluate Findings

For each important finding, record:
- **Source** - where it came from
- **Finding** - what it says
- **Credibility** - why the source is reliable enough to matter
- **Relevance** - how it affects this sprint
- **Limits** - uncertainty, version constraints, missing context, or reasons it may not apply

Reject weak or irrelevant findings explicitly when they could otherwise distract reasoning.

### Step 5: Extract Guidance For Reasoning

Summarize what the reasoning phase should use.

This should include:
- codebase patterns reasoning should preserve
- external guidance reasoning should consider
- options that appear viable
- options that appear risky or obsolete
- risks, constraints, or open questions that reasoning must resolve
- evidence expectations suggested by the research

Do not choose the final design unless the evidence makes an option plainly mandatory.
The reasoning document owns the decision and justification.

### Step 6: Write The Research Document

Write the document using the template, ensuring:
1. **Codebase evidence first** - local reality is documented before external guidance
2. **Current external guidance** - latest relevant tools, technologies, options, best practices, and official guidance are researched where they could affect the sprint
3. **Source-backed claims** - important claims cite code paths or external sources
4. **Clear separation** - distinguish evidence, inference, recommendation, and open question
5. **Reasoning handoff** - make it clear what the reasoning phase should use and what it still needs to decide

### Step 7: Verify Exit Criteria

Before completing, verify:
- [ ] Sprint scope and research questions are clear
- [ ] Codebase search was performed first
- [ ] Relevant existing code, tests, docs, and sprint artifacts are cited
- [ ] Current web research was performed or explicitly deemed unnecessary with reason
- [ ] Official or authoritative sources are preferred for external claims
- [ ] Latest tools, guidance, repos, examples, and snippets are captured where relevant
- [ ] Weak, obsolete, or inapplicable findings are rejected where relevant
- [ ] Open questions and risks are visible
- [ ] The reasoning handoff identifies what evidence should shape later decisions

## Key Principles

1. **Search before deciding** - research gathers evidence; reasoning makes decisions
2. **Start local** - understand the current codebase before importing outside patterns
3. **Stay current** - web research is required when guidance, tools, APIs, or practices may have changed
4. **Prefer primary sources** - official docs, release notes, standards, and maintained repositories carry the most weight
5. **Preserve context** - include enough source detail for reasoning and review to verify claims
6. **Reject distractions** - researched but unsuitable options should be recorded and set aside
7. **Hand off cleanly** - the research document should make reasoning faster, sharper, and less assumption-driven
