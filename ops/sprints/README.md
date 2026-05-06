# Sprints

This directory contains all sprint artifacts for HelloSales.

## Overview

The sprints have built a complete pre-brief foundation for a sales application, spanning observability, agent and worker runtimes, session management, authentication, and capabilities like web search, governed SQL, semantic catalog, RAG, and voice primitives.

The work follows a contract-driven operational process with reasoning, execution, and review phases.

Product feature requirements live in `ops/features/`. When a sprint supports a feature, the feature document should list the sprint and the sprint's `research.md`, `reasoning.md`, and `tracker.md` should backlink to the feature.

## Sprints

### sprint-11: Voice Primitives

Provider-neutral voice primitives: speech-to-text, text-to-speech, streaming LLM-to-TTS, duplex session and interruption control.

**Location:** `ops/sprints/sprint-11-voice-primitives/`

---

### sprint-10: RAG Primitives

Flexible, modular, provider-neutral retrieval-augmented generation primitives for future memory, document, and conversation retrieval.

**Location:** `ops/sprints/sprint-10-rag-primitives/`

---

### sprint-09: Context Engineering

Flexible, extendable context and prompt assembly system for the conversational agent runtime.

**Location:** `ops/sprints/sprint-09-context-engineering/`

---

### sprint-08: WorkOS Auth Foundation

First real authentication and authorization foundation with WorkOS adapter, API auth middleware, and permission propagation.

**Location:** `ops/sprints/sprint-08-workos-auth-foundation/`

---

### sprint-07: Semantic Catalog and Entity Mutations

Canonical semantic data catalog with generic entity create/edit tools and undo mechanics.

**Location:** `ops/sprints/sprint-07-semantic-catalog-entity-mutations/`

---

### sprint-06: Web Search Capabilities

Provider-neutral web search service, agent tool, and design seam for later batch search and research workflows.

**Location:** `ops/sprints/sprint-06-web-search-capabilities/`

---

### sprint-05: Governed SQL Tool

Governed read-only SQL tool for analytics questions against curated views.

**Location:** `ops/sprints/sprint-05-governed-sql-tool/`

---

### sprint-04: Session Substrate Foundation

First-class session substrate for conversational chronology, summaries, and trusted context.

**Location:** `ops/sprints/sprint-04-session-substrate-foundation/`

---

### sprint-03: Self-Hosted Monitoring Dashboard

Self-hosted observability pipeline with Grafana, Prometheus, Loki, and Tempo.

**Location:** `ops/sprints/sprint-03-self-hosted-monitoring-dashboard/`

---

### sprint-02: Worker Runtime Foundation

Structured worker runtime as sibling to conversational agent runtime, grounded in neutral LLM substrate.

**Location:** `ops/sprints/sprint-02-worker-runtime-foundation/`

---

### sprint-01: Observability Foundation

Scaffold-stage monitoring, telemetry, and metrics infrastructure.

**Location:** `ops/sprints/sprint-01-observability-foundation/`

---

## Related Docs

- [ops/features/README.md](../features/README.md) - Product feature documents and sprint linking rules
- [ops/process/README.md](../process/README.md) - Operational process
- [ops/process/execute/execution-protocol.md](../process/execute/execution-protocol.md) - Execution protocol
