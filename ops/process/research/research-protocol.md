# General Research Protocol

This protocol defines how to create a standalone research document.

## Purpose

The research agent gathers current external guidance and local codebase evidence for a user-provided research area, then explains how the findings may apply to HelloSales.

The research document is not a design decision document, not a sprint artifact, and not a tracker.
It is a structured evidence artifact whose job is to make later decisions more current, grounded, and implementation-aware:
- what the research area is trying to answer
- what current external guidance, tools, examples, or practices say
- what the existing codebase already does
- where likely integration points, constraints, and risks live
- which implementation approaches appear viable or risky
- what remains uncertain

## Inputs

1. **Research area** - The topic, capability, technology, workflow, product question, or operational question being researched
2. **User goals** - What the user wants to learn, decide, compare, validate, or prepare to implement
3. **Key considerations** - Criteria, concerns, tradeoffs, preferences, or themes the user wants included
4. **Constraints** - Technical, product, operational, security, budget, time, compatibility, or policy constraints
5. **Non-goals and exclusions** - Areas the research should avoid or treat as out of scope
6. **Existing codebase** - Source, tests, docs, configs, operational contracts, and artifacts relevant to the research area
7. **External sources** - Official docs, release notes, standards, current best-practice guidance, key repositories, credible implementation examples, and relevant comparison material

## Output

`ops/research/[research-area-slug].md`

Use a short, stable, lowercase slug based on the research area.

## Procedure

### Step 1: Clarify Research Brief

Identify the research area, user goals, key considerations, constraints, and likely decisions the research should support.

Record:
- the research area
- the user's goals
- key considerations and decision criteria
- constraints and non-goals
- expected audience or downstream use
- the questions the research should answer

If important inputs are missing, make conservative assumptions and label them clearly unless the missing detail would make the research misleading.

### Step 2: Survey The Codebase And Integration Points

Search the codebase before searching externally.

Use repository search and file reads to find:
- existing modules, services, routes, tools, workflows, tests, prompts, settings, diagnostics, docs, and operational contracts related to the area
- similar implemented features or prior work
- existing abstractions, seams, ownership boundaries, naming patterns, error handling, observability, testing, and documentation conventions
- direct integration points the research may affect
- constraints, TODOs, gaps, brittle areas, and compatibility concerns

Record codebase evidence with file paths and concise notes.
Distinguish direct evidence from inference.

The codebase survey must answer:
- what already exists
- which integration points matter
- what should probably be reused
- what should probably not be duplicated
- what local constraints could shape implementation
- what tests, smoke paths, or runtime evidence already cover nearby behavior

### Step 3: Search The Web For Current Guidance

Search the web for current information when the research touches technologies, tools, providers, security practices, standards, model behavior, frameworks, third-party APIs, product practices, or implementation patterns that may have changed.

Research should cover, where relevant:
- official documentation and release notes
- current best practices and security guidance
- latest supported tools, SDKs, APIs, models, frameworks, or provider capabilities
- deprecations, migrations, pricing or quota constraints, and breaking changes
- key repositories that show mature implementation patterns
- focused code snippets that demonstrate concrete integrations or edge cases
- credible comparison material for options the user may need to choose between

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
- **Relevance** - how it relates to the user's goals and constraints
- **Limits** - uncertainty, version constraints, missing context, or reasons it may not apply

Reject weak or irrelevant findings explicitly when they could otherwise distract the implementation discussion.

### Step 5: Present General Findings First

Write the high-level findings before codebase-specific recommendations.

The general findings should explain:
- the current state of the research area
- important tools, patterns, options, or practices
- what looks broadly recommended, emerging, deprecated, risky, or context-dependent
- the tradeoffs relevant to the user's goals and constraints
- which sources were strongest and which findings are uncertain

This section should be understandable without knowing the HelloSales codebase.

### Step 6: Connect Findings To The Codebase

After presenting general findings, explain how they map to HelloSales.

This should include:
- relevant local modules, services, docs, tests, configs, prompts, tools, and workflows
- integration points and ownership boundaries
- local patterns that should shape implementation
- mismatches between external guidance and the current codebase
- implementation paths that appear viable
- implementation paths that appear risky, obsolete, or misaligned
- open questions that need product, engineering, or operational judgment

Do not choose a final design unless the evidence makes an option plainly mandatory.
The document may recommend likely implementation approaches, but it must separate evidence from recommendation.

### Step 7: Write The Research Document

Write the document using `ops/process/research/research-template.md`, ensuring:
1. **Brief captured** - user-provided area, goals, considerations, constraints, and non-goals are visible
2. **Codebase surveyed first** - local reality is inspected before importing outside patterns
3. **General findings first in the report** - external/current findings are presented before codebase-specific mapping
4. **Current external guidance** - latest relevant tools, technologies, options, best practices, and official guidance are researched where they could affect the answer
5. **Source-backed claims** - important claims cite code paths or external sources
6. **Clear separation** - distinguish evidence, inference, recommendation, and open question
7. **Implementation link** - explain how the research may best be implemented in this codebase

### Step 8: Verify Exit Criteria

Before completing, verify:
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

## Key Principles

1. **Start local, report clearly** - inspect the codebase first, then present the final report from general findings to local implications
2. **Stay current** - web research is required when guidance, tools, APIs, or practices may have changed
3. **Prefer primary sources** - official docs, release notes, standards, and maintained repositories carry the most weight
4. **Respect the brief** - user goals, considerations, and constraints define what matters
5. **Preserve context** - include enough source detail for another person to verify claims
6. **Separate evidence from recommendation** - make clear what was found, what is inferred, and what is advised
7. **Reject distractions** - researched but unsuitable options should be recorded and set aside
8. **Make implementation concrete** - tie findings to real codebase integration points and likely implementation paths
