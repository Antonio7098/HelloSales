# Feature Protocol

This protocol defines how to create and maintain product-focused feature documents.

## Purpose

A feature document captures non-technical requirements before or alongside sprint planning.

It is not a sprint tracker, technical design, architecture proposal, or implementation plan.
Its job is to make the product intent clear:
- who the feature is for
- why it matters
- what outcome the feature is expected to move
- what user opportunity or pain justifies it
- what user journey should exist
- what product behavior is required
- what risks and assumptions need attention
- what success looks like
- what is explicitly out of scope
- which sprints are connected to delivery

This protocol incorporates the product discovery guidance in `ops/research/deep-research/feature-thinking-and-documentation-framework(gemini-3-flash).md`.

## Inputs

1. **Product brief or user request** - The feature idea, customer need, internal problem, or workflow gap
2. **Existing feature documents** - Related product requirements in `ops/features/`
3. **Sprint artifacts** - Existing or planned work in `ops/sprints/`
4. **Relevant research** - Product, market, customer, operational, or codebase research when available

## Output

`ops/features/[feature-slug].md`

Use `ops/process/feature/feature-template.md`.

## Procedure

### Step 1: Coach Before Writing

The default mode is product coaching before document writing.

The agent should help the user think through the feature with concise, practical questions before producing the final feature document. The goal is not to interrogate forever; it is to expose the decisions that matter before sprint planning.

Coach through:
- the user problem and why it matters now
- the desired outcome or business metric the feature should move
- the target user, stakeholder, and job to be done
- the trigger or context where the need appears
- the current workaround or pain without the feature
- the smallest valuable V1
- what should wait for later phases
- product rules, permissions, and visibility
- edge cases and exception behavior
- success criteria and adoption signals
- risks, assumptions, and open questions

If the user says they want a lightweight version, fewer questions, or wants the agent to fill gaps, comply. In that case:
- ask only the highest-impact missing questions
- mark inferred answers clearly as assumptions
- keep open questions visible instead of inventing certainty
- produce a usable draft with a lower maturity score if needed

### Step 2: Define The Feature Boundary

Write the feature name, feature slug, owner if known, status, priority, and target timing.

Clarify:
- what user or business problem the feature addresses
- what outcome or metric it is expected to improve
- who the primary user is
- what outcome should be different after the feature exists
- whether this is a new feature, revision, or continuation of an existing feature
- what is not included in this version

If the feature is too broad to describe clearly, split it into smaller feature documents before sprint planning.

### Step 3: Use Product Discovery Frames

Use these frames as thinking aids, not rigid bureaucracy:

- **Outcome-Opportunity-Solution:** define the desired outcome, the user opportunity or pain, then the product solution.
- **Jobs To Be Done:** describe when the user needs the feature, what they want to accomplish, and why.
- **Four Product Risks:** check value risk, usability risk, feasibility risk, and business viability risk.
- **Pre-Mortem:** imagine the feature failed after launch and record why.
- **LNO Scope:** decide whether the feature deserves deep documentation because it is high leverage, standard treatment because it is neutral, or minimal treatment because it is overhead.

For HelloSales, pay special attention to:
- sales workflow value, such as faster follow-up, clearer pipeline visibility, better rep productivity, higher data quality, or reduced ramp time
- permission and visibility rules, because CRM-like product behavior often depends on role, ownership, team, and account context
- adoption and rollout, because sales teams need to discover and trust workflow changes

### Step 4: Keep The Document Product-Focused

Describe the feature in plain language.

Include:
- desired outcome
- opportunity or pain
- job to be done
- user context
- trigger
- happy-path journey
- information the user needs to see
- actions the user needs to take
- product rules and expected behavior
- success criteria
- edge cases and exceptions

Avoid:
- database schemas
- API routes
- class names
- provider choices
- implementation tasks
- test strategy
- architecture decisions

Technical details belong in sprint research, sprint reasoning, trackers, and code review evidence.

### Step 5: Link Features And Sprints Both Ways

Feature documents and sprint artifacts must cross-reference each other.

In the feature document, update **Sprint Links** with every sprint that researches, builds, revises, ships, or supports the feature.

In each linked sprint, add a **Feature Links** section to `research.md`, `reasoning.md`, and `tracker.md`:

```md
## Feature Links

- `ops/features/[feature-slug].md` - [How this sprint supports the feature]
```

When a sprint only delivers part of a feature, state the partial relationship clearly. Do not imply the whole feature is shipped unless the success criteria are actually satisfied.

### Step 6: Define Observable Product Requirements

Write requirements as product behavior that can be observed by a user or stakeholder.

Good examples:
- Sales reps can see which leads need follow-up today.
- Managers can filter pipeline risk by owner and stage.
- Users are warned before closing a draft with unsaved notes.
- Duplicate contacts are blocked before the rep saves the record.

Avoid technical phrasing:
- Add a `follow_up_due_at` column.
- Create a `/tasks/reminders` endpoint.
- Use background jobs for reminders.
- Store state in Redis.

Implementation choices are decided later by sprint research and reasoning.

When helpful, use Given/When/Then wording:
- **Given** [user/context/state]
- **When** [action or event]
- **Then** [observable result]

### Step 7: Make Scope Explicit

Record what is in scope and out of scope for the first useful version.

The feature document should make it easy to see:
- what must be true for the feature to count as successful
- which edge cases need product behavior
- what can wait
- which open questions block sprint planning
- which open questions can be answered during sprint research

### Step 8: Score Feature Maturity

Every feature document must include a maturity score.

The score is not a quality grade for the person writing it. It is a readiness signal that helps the agent and user decide whether to keep discovering, move to sprint planning, or intentionally proceed with known gaps.

Use a 0 to 100 score:
- **0-24: Raw idea** - the feature is mostly a concept; user, problem, and outcome are unclear.
- **25-49: Shaped draft** - the problem and user are emerging, but requirements, risks, or scope are still thin.
- **50-69: Product-defined** - the main product thinking is present; some assumptions or edge cases remain.
- **70-84: Sprint-planning ready** - product intent, requirements, success criteria, risks, and scope are clear enough for research/reasoning.
- **85-100: Delivery mature** - the feature has strong product clarity, validated assumptions where possible, crisp V1 scope, and current sprint links.

Score across these dimensions, 10 points each:
- **Problem clarity:** the pain or opportunity is specific and evidenced.
- **Outcome clarity:** the desired user or business outcome is measurable or observable.
- **User/JTBD clarity:** primary user, context, and job to be done are clear.
- **Journey clarity:** happy path and key user moments are understandable.
- **Requirements quality:** requirements are observable, non-technical, and precise.
- **Rules and permissions:** product logic, role, visibility, and eligibility rules are explicit.
- **Scope control:** V1, later phases, and out-of-scope items are separated.
- **Edge cases:** important exceptions and failure states have expected product behavior.
- **Risks and assumptions:** value, usability, feasibility, viability, and pre-mortem risks are visible.
- **Delivery linkage:** sprint links, dependencies, rollout, and adoption considerations are current.

The agent should be ready to give or update the score while the feature is being developed. When scoring, include:
- the numeric score
- the maturity band
- the top 2 or 3 reasons for the score
- the next 2 or 3 questions or edits that would raise the score most

### Step 9: Maintain The Feature Through Delivery

Update the feature document when sprint work changes product understanding.

Update:
- status
- maturity score
- sprint links
- success criteria if product scope changes
- out-of-scope items if they become planned work
- open questions as they are answered
- final product summary when shipped

Do not rewrite a shipped feature to hide earlier uncertainty. Preserve useful context and mark decisions as resolved.

### Step 10: Verify Exit Criteria

Before handing a feature to sprint planning, verify:
- [ ] Feature file exists in `ops/features/`
- [ ] Feature name, slug, status, priority, and target timing are recorded
- [ ] Maturity score is present with rationale
- [ ] Primary user and stakeholders are clear
- [ ] Desired outcome or metric is clear
- [ ] Problem today and desired outcome are clear
- [ ] Job to be done and trigger/context are clear
- [ ] Happy-path journey is described
- [ ] Product requirements are observable and non-technical
- [ ] Business rules, permissions, visibility, and product logic are captured
- [ ] Success criteria are concrete enough for sprint planning
- [ ] Value, usability, feasibility, and viability risks are considered
- [ ] Pre-mortem risks or failure modes are visible
- [ ] Edge cases and exceptions are visible
- [ ] Out-of-scope items are explicit
- [ ] V1 and later phases are separated where relevant
- [ ] Rollout and adoption considerations are captured or marked not needed
- [ ] Sprint links are present or marked as not planned yet
- [ ] Linked sprint artifacts backlink to this feature when sprints exist

## Key Principles

1. **Product first** - define the user and business outcome before technical planning
2. **Plain language** - a non-engineer should understand the feature document
3. **Observable behavior** - requirements should describe what users see, do, or experience
4. **Small first version** - make initial scope clear enough to plan and ship
5. **Bidirectional traceability** - every linked sprint should point back to the feature, and every feature should list its linked sprints
6. **No hidden implementation design** - keep technical decisions in the sprint process
7. **Coach the thinking** - help the user make product decisions before turning them into a document
8. **Score maturity openly** - use the score to guide discovery, not to create false precision
