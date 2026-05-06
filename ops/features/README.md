# Features

This directory contains product-focused feature documents for HelloSales.

Feature documents describe what should exist from the user's and business's point of view. They are intentionally non-technical requirements documents. They should explain the problem, users, desired outcome, product behavior, scope, and acceptance criteria before implementation is planned through sprints.

## Purpose

Use `ops/features/` when a capability needs product definition before or across sprint work.

A feature can:
- be delivered by one sprint
- span multiple sprints
- be partially delivered by a sprint
- depend on earlier feature or sprint work
- remain product-owned while technical implementation evolves through sprint artifacts

## File Naming

Create one Markdown file per feature:

`ops/features/[feature-slug].md`

Examples:
- `ops/features/lead-follow-up-reminders.md`
- `ops/features/manager-pipeline-insights.md`
- `ops/features/conversation-history-search.md`

## Required Links

Feature and sprint artifacts must link both ways.

In each feature document, maintain:
- **Related Sprints** - sprint artifacts that research, build, revise, or ship the feature
- **Delivery Status** - what each linked sprint contributes

In each sprint artifact, maintain:
- **Feature Links** - product feature docs the sprint supports

At minimum, add feature links to:
- `ops/sprints/sprint-[XX]-[name]/research.md`
- `ops/sprints/sprint-[XX]-[name]/reasoning.md`
- `ops/sprints/sprint-[XX]-[name]/tracker.md`

## Process

Use:
- `ops/process/feature/feature-protocol.md`
- `ops/process/feature/feature-template.md`

The feature document should be written before sprint planning when product requirements are still being shaped. If sprint execution changes the product understanding, update the feature document and keep the sprint backlinks current.
