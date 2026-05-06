# Feature Protocol

This protocol defines how to create and maintain product-focused feature documents.

## Purpose

A feature document captures non-technical requirements before or alongside sprint planning.

It is not a sprint tracker, technical design, architecture proposal, or implementation plan.
Its job is to make the product intent clear:
- who the feature is for
- why it matters
- what user journey should exist
- what product behavior is required
- what success looks like
- what is explicitly out of scope
- which sprints are connected to delivery

## Inputs

1. **Product brief or user request** - The feature idea, customer need, internal problem, or workflow gap
2. **Existing feature documents** - Related product requirements in `ops/features/`
3. **Sprint artifacts** - Existing or planned work in `ops/sprints/`
4. **Relevant research** - Product, market, customer, operational, or codebase research when available

## Output

`ops/features/[feature-slug].md`

Use `ops/process/feature/feature-template.md`.

## Procedure

### Step 1: Define The Feature Boundary

Write the feature name, feature slug, owner if known, status, priority, and target timing.

Clarify:
- what user or business problem the feature addresses
- who the primary user is
- what outcome should be different after the feature exists
- whether this is a new feature, revision, or continuation of an existing feature
- what is not included in this version

If the feature is too broad to describe clearly, split it into smaller feature documents before sprint planning.

### Step 2: Keep The Document Product-Focused

Describe the feature in plain language.

Include:
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

### Step 3: Link Features And Sprints Both Ways

Feature documents and sprint artifacts must cross-reference each other.

In the feature document, update **Sprint Links** with every sprint that researches, builds, revises, ships, or supports the feature.

In each linked sprint, add a **Feature Links** section to `research.md`, `reasoning.md`, and `tracker.md`:

```md
## Feature Links

- `ops/features/[feature-slug].md` - [How this sprint supports the feature]
```

When a sprint only delivers part of a feature, state the partial relationship clearly. Do not imply the whole feature is shipped unless the success criteria are actually satisfied.

### Step 4: Define Observable Product Requirements

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

### Step 5: Make Scope Explicit

Record what is in scope and out of scope for the first useful version.

The feature document should make it easy to see:
- what must be true for the feature to count as successful
- which edge cases need product behavior
- what can wait
- which open questions block sprint planning
- which open questions can be answered during sprint research

### Step 6: Maintain The Feature Through Delivery

Update the feature document when sprint work changes product understanding.

Update:
- status
- sprint links
- success criteria if product scope changes
- out-of-scope items if they become planned work
- open questions as they are answered
- final product summary when shipped

Do not rewrite a shipped feature to hide earlier uncertainty. Preserve useful context and mark decisions as resolved.

### Step 7: Verify Exit Criteria

Before handing a feature to sprint planning, verify:
- [ ] Feature file exists in `ops/features/`
- [ ] Feature name, slug, status, priority, and target timing are recorded
- [ ] Primary user and stakeholders are clear
- [ ] Problem today and desired outcome are clear
- [ ] Happy-path journey is described
- [ ] Product requirements are observable and non-technical
- [ ] Business rules and product logic are captured
- [ ] Success criteria are concrete enough for sprint planning
- [ ] Edge cases and exceptions are visible
- [ ] Out-of-scope items are explicit
- [ ] Sprint links are present or marked as not planned yet
- [ ] Linked sprint artifacts backlink to this feature when sprints exist

## Key Principles

1. **Product first** - define the user and business outcome before technical planning
2. **Plain language** - a non-engineer should understand the feature document
3. **Observable behavior** - requirements should describe what users see, do, or experience
4. **Small first version** - make initial scope clear enough to plan and ship
5. **Bidirectional traceability** - every linked sprint should point back to the feature, and every feature should list its linked sprints
6. **No hidden implementation design** - keep technical decisions in the sprint process
