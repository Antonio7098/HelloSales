# General Research Process

This directory contains the protocol and template for standalone research work.

## Purpose

The general research process produces source-backed research documents for a user-provided research area.
It is not tied to a sprint and does not assume the output will become sprint reasoning or a tracker.

Use it when the user provides a research area, goals, key considerations, constraints, non-goals, or open questions and wants grounded findings that connect current external guidance to this codebase.
# Research Phase

This directory contains the protocol and template for the research phase.

## Purpose

The research phase produces a document that gathers current codebase and external evidence before reasoning begins.

## Key Characteristics

The research document is:
- evidence-focused
- source-backed
- current where external guidance can change
- explicit about user goals, constraints, and exclusions
- grounded in the existing codebase before external recommendations are applied
- organized so general findings appear before codebase-specific implications

## Files

- `research-protocol.md` - Protocol for creating a standalone research document
- `research-template.md` - Template for a standalone research document

## Output Location

Standalone research documents belong in:

`ops/research/[research-area-slug].md`

## When To Use

Use this process for research that informs product, engineering, architecture, implementation, tooling, vendor, or operational decisions outside a specific sprint.

For sprint planning research, use `ops/process/sprint-research/`.
- explicit about what was searched, what was found, and what was rejected

## Files

- `research-protocol.md` - Protocol for creating the research document
- `research-template.md` - Template for the research document

## When To Use

The research phase is the first step in sprint planning.
It should be completed before the reasoning phase begins so reasoning can use current codebase evidence and external guidance instead of relying on memory or assumptions.
