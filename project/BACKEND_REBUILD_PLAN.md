# HelloSales Backend Rebuild Plan

## Vision Statement

Rebuild the HelloSales backend with a **minimal, observable, SOLID architecture** that serves as a clean foundation for the AI-powered sales content platform. Every component should be traceable, every error typed, and every decision reversible.

**Core Product**: AI-powered generation and management of sales scripts and emails for clients, products, and client-product combinations.

---

## Table of Contents

1. [Core Principles](#1-core-principles)
2. [Architecture Overview](#2-architecture-overview)
3. [Database Schema](#3-database-schema)
4. [Stageflow Pipeline Architecture](#4-stageflow-pipeline-architecture)
5. [Observability Architecture](#5-observability-architecture)
6. [Error Handling System](#6-error-handling-system)
7. [Directory Structure](#7-directory-structure)
8. [Implementation Phases](#8-implementation-phases)
9. [Quality Recommendations](#9-quality-recommendations)
10. [Central Pulse Compatibility](#10-central-pulse-compatibility)

---

## 1. Core Principles

### 1.1 SOLID Principles Applied

| Principle | Application |
|-----------|-------------|
| **S - Single Responsibility** | Each stage handles one concern. Repositories handle persistence. Handlers handle HTTP/WS. |
| **O - Open/Closed** | Use abstract base classes and protocols. Extend via new stages, not modification. |
| **L - Liskov Substitution** | Provider interfaces (LLM, STT, TTS) are interchangeable. Any provider implementing the protocol works. |
| **I - Interface Segregation** | Small, focused protocols. `LLMProvider` doesn't know about `STTProvider`. Modular ports (CorePorts, LLMPorts). |
| **D - Dependency Inversion** | Stages depend on abstractions (protocols), not concrete implementations. Ports inject dependencies. |

### 1.2 Observability Doctrine

**"If it's not observable, it didn't happen."**

- **Wide Events**: Every significant operation emits a structured event with full context via stageflow's `WideEventEmitter`
- **OpenTelemetry**: Traces span the full request lifecycle via stageflow's `TracingInterceptor`
- **Structured Logging**: JSON logs with correlation IDs via stageflow's `LoggingInterceptor`
- **Typed Errors**: Every error is a typed exception with code, message, context, retryability
- **Cost Attribution**: Every external call tracks cost in cents via `ProviderCallLogger`
- **Latency Breakdown**: TTFT, TTFA, TTFC for AI pipeline stages via `PipelineRunLogger`

### 1.3 Design Constraints

- **No Magic**: Explicit is better than implicit. No hidden side effects.
- **Fail Fast**: Validate inputs at boundaries. Crash early with clear errors.
- **Idempotent Operations**: Safe to retry. Use request IDs for deduplication.
- **Async First**: All I/O is async. No blocking calls in the request path.
- **Multi-Tenant by Default**: org_id on every model. Scoped queries everywhere.
- **Pipeline-First**: All AI operations flow through stageflow pipelines.

---

## 2. Architecture Overview

### 2.1 Layered Architecture with Stageflow

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ HTTP Routes │  │  WebSocket  │  │  Background Tasks   │  │
│  │  (FastAPI)  │  │  Handlers   │  │    (async jobs)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                   STAGEFLOW PIPELINE LAYER                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Stages    │  │Interceptors │  │    Event Sinks      │  │
│  │(GUARD,LLM,  │  │ (timeout,   │  │ (DB, OTEL, Wide)    │  │
│  │ ENRICH,etc) │  │  circuit)   │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                     APPLICATION LAYER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Services  │  │  Pipeline   │  │   Domain Events     │  │
│  │ (use cases) │  │  Factories  │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Entities  │  │  Protocols  │  │   Typed Errors      │  │
│  │  (models)   │  │ (interfaces)│  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Repositories│  │  Providers  │  │   Observability     │  │
│  │    (DB)     │  │(LLM/STT/TTS)│  │  (OTEL, logging)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Request Flow with Stageflow

```
Request → Middleware (trace, auth, context)
        → Handler (validate, dispatch)
        → Pipeline Factory (create pipeline)
        → StageGraph.run(ctx)
            → [InputGuard] → [ProfileEnrich] ┐
                                             ├→ [LLM] → [OutputGuard] → [Persist]
            → [SummaryEnrich] ───────────────┘
        → Response
```

---

## 3. Database Schema

### 3.1 Core Identity Tables

```sql
-- Users: Authentication and identity
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'workos',
    auth_subject VARCHAR(255) NOT NULL UNIQUE,  -- WorkOS user ID
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT users_auth_unique UNIQUE (auth_provider, auth_subject)
);

-- Organizations: Multi-tenant containers
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(255) NOT NULL UNIQUE,  -- WorkOS org ID
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Organization Memberships: User-Org relationships
CREATE TABLE organization_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT org_membership_unique UNIQUE (user_id, organization_id)
);

-- Company Profiles: Detailed company information for sales context
CREATE TABLE company_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE UNIQUE,

    -- Company basics
    industry VARCHAR(100),
    company_size VARCHAR(50),  -- 'startup', '1-10', '10-50', '50-200', '200-1000', '1000+'
    headquarters_city VARCHAR(100),
    headquarters_country VARCHAR(100),
    website TEXT,

    -- Sales operations
    sales_team_size INTEGER,
    average_deal_size_usd INTEGER,
    sales_cycle_days INTEGER,
    target_market TEXT,
    market_segments JSONB DEFAULT '[]',  -- e.g., ['SMB', 'Enterprise', 'Mid-market']

    -- Product/service context
    primary_products JSONB DEFAULT '[]',  -- Primary offerings they sell
    sales_regions JSONB DEFAULT '[]',     -- Geographic regions
    deal_types JSONB DEFAULT '[]',        -- e.g., 'outbound', 'inbound', 'renewal', 'expansion'

    -- Sales maturity & process
    sales_methodology VARCHAR(100),       -- e.g., 'consultative', 'transactional', 'solution-selling'
    sales_stage VARCHAR(50),              -- 'early', 'growing', 'mature', 'enterprise'
    typical_buying_cycle JSONB DEFAULT '{}', -- Detailed buying cycle stages

    -- Competitive context
    main_competitors JSONB DEFAULT '[]',
    competitive_advantages JSONB DEFAULT '[]',
    unique_selling_points JSONB DEFAULT '[]',

    -- Additional context
    company_description TEXT,
    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_company_profiles_org_id ON company_profiles(org_id);
```

### 3.2 Session & Interaction Tables

```sql
-- Sessions: Conversation containers
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,

    -- State
    state VARCHAR(20) NOT NULL DEFAULT 'active',  -- 'active', 'ended'
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,

    -- Metrics (denormalized for query performance)
    interaction_count INTEGER NOT NULL DEFAULT 0,
    total_cost_cents INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER,

    -- Metadata
    session_type VARCHAR(50) DEFAULT 'chat',  -- 'chat', 'script_generation', 'email_generation'
    metadata JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_org_id ON sessions(org_id);
CREATE INDEX idx_sessions_state ON sessions(state);
CREATE INDEX idx_sessions_created_at ON sessions(created_at DESC);

-- Interactions: Individual messages in a session
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    -- Identity
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    message_id VARCHAR(100),    -- Client-generated for deduplication

    -- Content
    input_type VARCHAR(20) NOT NULL DEFAULT 'text',  -- 'text', 'voice'
    content TEXT,               -- Text content or transcript
    transcript TEXT,            -- Original transcript (if voice)

    -- Audio (if voice)
    audio_url TEXT,
    audio_duration_ms INTEGER,

    -- Provider call references
    llm_provider_call_id UUID,
    stt_provider_call_id UUID,
    tts_provider_call_id UUID,

    -- Ordering
    sequence_number INTEGER NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interactions_session_id ON interactions(session_id);
CREATE INDEX idx_interactions_session_seq ON interactions(session_id, sequence_number);
CREATE INDEX idx_interactions_created_at ON interactions(created_at DESC);

-- Session Summaries: Context compression
CREATE TABLE session_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    version INTEGER NOT NULL,           -- Incremental version number
    summary_text TEXT NOT NULL,         -- The compressed context
    cutoff_sequence INTEGER NOT NULL,   -- Messages before this are summarized
    token_count INTEGER,                -- Tokens in summary

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT session_summary_version_unique UNIQUE (session_id, version)
);

CREATE INDEX idx_session_summaries_session_id ON session_summaries(session_id);

-- Summary State: Mutable tracking for summary cadence
CREATE TABLE summary_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE UNIQUE,

    turns_since_summary INTEGER NOT NULL DEFAULT 0,
    last_cutoff_sequence INTEGER NOT NULL DEFAULT 0,
    last_summary_at TIMESTAMPTZ,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Interaction Embeddings: Vector storage for semantic search
CREATE TABLE interaction_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_id UUID NOT NULL REFERENCES interactions(id) ON DELETE CASCADE UNIQUE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,

    embedding VECTOR(1536),  -- OpenAI ada-002 dimensions, adjust as needed
    model_id VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interaction_embeddings_session_id ON interaction_embeddings(session_id);
```

### 3.3 Observability Tables

```sql
-- Provider Calls: Single source of truth for ALL external API calls
CREATE TABLE provider_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classification
    service VARCHAR(50) NOT NULL,       -- 'chat', 'script', 'email', 'summary'
    operation VARCHAR(20) NOT NULL,     -- 'llm', 'stt', 'tts', 'embedding'
    provider VARCHAR(50) NOT NULL,      -- 'groq', 'google', 'deepgram'
    model_id VARCHAR(100),

    -- Correlation
    request_id VARCHAR(100),
    pipeline_run_id UUID,
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    interaction_id UUID REFERENCES interactions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,

    -- Input/Output capture
    prompt_messages JSONB,              -- For LLM: array of messages
    prompt_text TEXT,                   -- For STT: audio reference
    output_content TEXT,                -- Raw output
    output_parsed JSONB,                -- Structured output

    -- Metrics
    latency_ms INTEGER,
    tokens_in INTEGER,
    tokens_out INTEGER,
    audio_duration_ms INTEGER,
    cost_cents INTEGER,

    -- Status
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error TEXT,
    error_code VARCHAR(100),

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_provider_calls_request_id ON provider_calls(request_id);
CREATE INDEX idx_provider_calls_pipeline_run_id ON provider_calls(pipeline_run_id);
CREATE INDEX idx_provider_calls_session_id ON provider_calls(session_id);
CREATE INDEX idx_provider_calls_user_id ON provider_calls(user_id);
CREATE INDEX idx_provider_calls_org_id ON provider_calls(org_id);
CREATE INDEX idx_provider_calls_provider ON provider_calls(provider, model_id);
CREATE INDEX idx_provider_calls_created_at ON provider_calls(created_at DESC);

-- Pipeline Runs: End-to-end pipeline execution tracking
CREATE TABLE pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classification
    service VARCHAR(50) NOT NULL,       -- 'chat', 'script', 'email'
    topology VARCHAR(50),               -- Pipeline configuration name
    behavior VARCHAR(50),               -- Execution behavior
    quality_mode VARCHAR(20),           -- 'fast', 'balanced', 'quality'

    -- Correlation
    request_id VARCHAR(100),
    session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    interaction_id UUID REFERENCES interactions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,

    -- Provider call references
    stt_provider_call_id UUID REFERENCES provider_calls(id) ON DELETE SET NULL,
    llm_provider_call_id UUID REFERENCES provider_calls(id) ON DELETE SET NULL,
    tts_provider_call_id UUID REFERENCES provider_calls(id) ON DELETE SET NULL,

    -- Latency metrics (all in milliseconds)
    total_latency_ms INTEGER,
    ttft_ms INTEGER,                    -- Time to first token (LLM)
    ttfa_ms INTEGER,                    -- Time to first audio
    ttfc_ms INTEGER,                    -- Time to first chunk (for TTS)

    -- Token metrics
    tokens_in INTEGER,
    tokens_out INTEGER,
    tokens_per_second FLOAT,

    -- Audio metrics
    input_audio_duration_ms INTEGER,
    output_audio_duration_ms INTEGER,

    -- Cost
    total_cost_cents INTEGER,

    -- Status
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error TEXT,
    error_code VARCHAR(100),

    -- Detailed breakdown
    stages JSONB DEFAULT '{}',          -- Per-stage metrics from stageflow
    run_metadata JSONB DEFAULT '{}',    -- Additional context
    context_snapshot JSONB,             -- State at execution time

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pipeline_runs_request_id ON pipeline_runs(request_id);
CREATE INDEX idx_pipeline_runs_session_id ON pipeline_runs(session_id);
CREATE INDEX idx_pipeline_runs_user_id ON pipeline_runs(user_id);
CREATE INDEX idx_pipeline_runs_org_id ON pipeline_runs(org_id);
CREATE INDEX idx_pipeline_runs_service ON pipeline_runs(service);
CREATE INDEX idx_pipeline_runs_success ON pipeline_runs(success);
CREATE INDEX idx_pipeline_runs_created_at ON pipeline_runs(created_at DESC);

-- Pipeline Events: Granular event stream within pipeline runs (stageflow events)
CREATE TABLE pipeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,

    -- Event data (from stageflow EventSink)
    event_type VARCHAR(100) NOT NULL,   -- 'stage.llm.started', 'stage.guard.completed', etc.
    event_data JSONB DEFAULT '{}',

    -- Correlation (denormalized for query performance)
    request_id VARCHAR(100),
    session_id UUID,
    user_id UUID,
    org_id UUID,

    -- Timestamp (high precision)
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pipeline_events_run_id ON pipeline_events(pipeline_run_id);
CREATE INDEX idx_pipeline_events_type ON pipeline_events(event_type);
CREATE INDEX idx_pipeline_events_occurred_at ON pipeline_events(occurred_at DESC);

-- Dead Letter Queue: Failed pipeline recovery
CREATE TABLE dead_letter_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,

    -- Failure context
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT,
    error_code VARCHAR(100),
    failed_stage VARCHAR(100),          -- Stage name from stageflow
    stack_trace TEXT,

    -- Request context snapshot
    context_snapshot JSONB NOT NULL,    -- Full ContextSnapshot from stageflow
    input_data JSONB,

    -- Correlation
    request_id VARCHAR(100),
    session_id UUID,
    user_id UUID,
    org_id UUID,

    -- Retry tracking
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    last_retry_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ,

    -- Resolution
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'investigating', 'resolved', 'abandoned'
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dlq_status ON dead_letter_queue(status);
CREATE INDEX idx_dlq_error_type ON dead_letter_queue(error_type);
CREATE INDEX idx_dlq_created_at ON dead_letter_queue(created_at DESC);
```

### 3.4 HelloSales Content Tables

```sql
-- Products: Items being sold
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),

    -- Product details for AI context
    key_features JSONB DEFAULT '[]',
    pricing_info JSONB DEFAULT '{}',
    target_audience TEXT,
    competitive_advantages TEXT,
    use_cases JSONB DEFAULT '[]',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_org_id ON products(org_id);
CREATE INDEX idx_products_active ON products(org_id, is_active);

-- Clients: Prospective/current customers
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    name VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    title VARCHAR(255),
    industry VARCHAR(100),
    email VARCHAR(255),

    -- Client profile for AI context
    pain_points JSONB DEFAULT '[]',
    goals JSONB DEFAULT '[]',
    objection_patterns JSONB DEFAULT '[]',
    communication_style TEXT,
    decision_criteria JSONB DEFAULT '[]',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clients_org_id ON clients(org_id);
CREATE INDEX idx_clients_active ON clients(org_id, is_active);

-- Sales Scripts: Generated/managed sales scripts
CREATE TABLE sales_scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Associations (can be any combination)
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,

    -- Script metadata
    name VARCHAR(255) NOT NULL,
    description TEXT,
    script_type VARCHAR(50) NOT NULL DEFAULT 'general',  -- 'cold_call', 'follow_up', 'demo', 'closing', 'general'

    -- Script content
    content TEXT NOT NULL,              -- The actual script
    key_talking_points JSONB DEFAULT '[]',
    objection_handlers JSONB DEFAULT '{}',
    discovery_questions JSONB DEFAULT '[]',
    closing_techniques JSONB DEFAULT '[]',

    -- Generation metadata
    generated_by_session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    generation_prompt TEXT,             -- Original prompt used
    model_id VARCHAR(100),

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    parent_script_id UUID REFERENCES sales_scripts(id) ON DELETE SET NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sales_scripts_org_id ON sales_scripts(org_id);
CREATE INDEX idx_sales_scripts_product_id ON sales_scripts(product_id);
CREATE INDEX idx_sales_scripts_client_id ON sales_scripts(client_id);
CREATE INDEX idx_sales_scripts_type ON sales_scripts(org_id, script_type);

-- Sales Emails: Generated/managed sales emails
CREATE TABLE sales_emails (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Associations (can be any combination)
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,

    -- Email metadata
    name VARCHAR(255) NOT NULL,
    description TEXT,
    email_type VARCHAR(50) NOT NULL DEFAULT 'general',  -- 'cold_outreach', 'follow_up', 'proposal', 'closing', 'general'

    -- Email content
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    call_to_action TEXT,

    -- Personalization hints
    personalization_fields JSONB DEFAULT '[]',  -- Fields that should be customized per-send

    -- Generation metadata
    generated_by_session_id UUID REFERENCES sessions(id) ON DELETE SET NULL,
    generation_prompt TEXT,
    model_id VARCHAR(100),

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    parent_email_id UUID REFERENCES sales_emails(id) ON DELETE SET NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sales_emails_org_id ON sales_emails(org_id);
CREATE INDEX idx_sales_emails_product_id ON sales_emails(product_id);
CREATE INDEX idx_sales_emails_client_id ON sales_emails(client_id);
CREATE INDEX idx_sales_emails_type ON sales_emails(org_id, email_type);
```

### 3.5 Tables Being REMOVED

The following tables will NOT be included in the new schema:

```
REMOVED - Evaluation & Testing:
- eval_test_suites
- eval_benchmark_runs
- eval_test_cases

REMOVED - User Features & Profiles:
- assessments
- skills
- user_skills
- user_profiles
- user_meta_summaries

REMOVED - Feedback & Triage:
- feedback_events
- triage_datasets
- triage_annotations

REMOVED - Old Sailwind:
- sailwind_playbook_strategies (replaced by sales_scripts)
- sailwind_rep_assignments (removed entirely)
- sailwind_practice_sessions (removed entirely)
```

---

## 4. Stageflow Pipeline Architecture

### 4.1 Stageflow Overview

HelloSales uses **stageflow** as the DAG-based execution substrate for all AI pipelines. This provides:

- **Parallel execution** of independent stages (enrichment stages run concurrently)
- **Built-in observability** via interceptors (logging, metrics, tracing, timeouts, circuit breakers)
- **Typed context** with immutable snapshots
- **Wide event emission** for comprehensive telemetry
- **Graceful cancellation** support

### 4.2 Core Chat Pipeline

The primary pipeline for conversational AI interactions:

```
Pipeline: chat_pipeline

DAG:
    [input_guard] ───────────────────────────┐
                                             │
    [profile_enrich] ────────────────────────┼──> [llm] ──> [output_guard] ──> [persist]
                                             │
    [summary_enrich] ────────────────────────┘
```

```python
# app/pipelines/chat.py

from stageflow import Pipeline, StageKind

def create_chat_pipeline(
    guard_service,
    profile_service,
    summary_service,
    llm_provider,
    interaction_repo,
) -> Pipeline:
    """Create the core chat pipeline.

    DAG:
        [input_guard] ───────────────────────────┐
                                                 │
        [profile_enrich] ────────────────────────┼──> [llm] ──> [output_guard] ──> [persist]
                                                 │
        [summary_enrich] ────────────────────────┘

    Features:
    - Input validation (guardrails)
    - Parallel context enrichment (profile + summary)
    - LLM response generation
    - Output validation (guardrails)
    - Message persistence
    """
    return (
        Pipeline()
        # Guard: Validate input before processing
        .with_stage(
            name="input_guard",
            runner=InputGuardStage(guard_service),
            kind=StageKind.GUARD,
        )
        # Parallel enrichment (no dependencies on each other)
        .with_stage(
            name="profile_enrich",
            runner=ProfileEnrichStage(profile_service),
            kind=StageKind.ENRICH,
        )
        .with_stage(
            name="summary_enrich",
            runner=SummaryEnrichStage(summary_service),
            kind=StageKind.ENRICH,
        )
        # LLM: Generate response (waits for guard + enrichments)
        .with_stage(
            name="llm",
            runner=LLMStage(llm_provider),
            kind=StageKind.TRANSFORM,
            dependencies=("input_guard", "profile_enrich", "summary_enrich"),
        )
        # Guard: Validate output
        .with_stage(
            name="output_guard",
            runner=OutputGuardStage(guard_service),
            kind=StageKind.GUARD,
            dependencies=("llm",),
        )
        # Persist: Save interaction
        .with_stage(
            name="persist",
            runner=PersistStage(interaction_repo),
            kind=StageKind.WORK,
            dependencies=("output_guard",),
        )
    )
```

### 4.3 Stage Implementations

#### InputGuardStage (GUARD)

```python
# app/pipelines/stages/guards.py

from stageflow import StageContext, StageKind, StageOutput

class InputGuardStage:
    """Validate user input against safety policies."""

    name = "input_guard"
    kind = StageKind.GUARD

    def __init__(self, guard_service):
        self.guard_service = guard_service

    async def execute(self, ctx: StageContext) -> StageOutput:
        inputs = ctx.config.get("inputs")
        input_text = inputs.snapshot.input_text if inputs else ctx.snapshot.input_text

        if not input_text or not input_text.strip():
            return StageOutput.cancel(
                reason="Empty input",
                data={"blocked": True, "reason": "empty_input"},
            )

        # Check against guardrails
        result = await self.guard_service.check_input(input_text)

        if not result.is_safe:
            ctx.emit_event("guard.input.blocked", {
                "reason": result.reason,
                "category": result.category,
            })
            return StageOutput.cancel(
                reason=f"Input blocked: {result.reason}",
                data={"blocked": True, "reason": result.reason},
            )

        return StageOutput.ok(
            validated=True,
            input_text=input_text,
        )
```

#### ProfileEnrichStage (ENRICH)

```python
# app/pipelines/stages/enrichers.py

class ProfileEnrichStage:
    """Enrich context with user/org profile information."""

    name = "profile_enrich"
    kind = StageKind.ENRICH

    def __init__(self, profile_service):
        self.profile_service = profile_service

    async def execute(self, ctx: StageContext) -> StageOutput:
        user_id = ctx.snapshot.user_id
        org_id = ctx.snapshot.org_id

        if not user_id:
            return StageOutput.skip(reason="No user_id provided")

        profile = await self.profile_service.get_profile(user_id, org_id)

        if not profile:
            return StageOutput.skip(reason="No profile found")

        return StageOutput.ok(
            profile={
                "user_id": str(user_id),
                "display_name": profile.display_name,
                "preferences": profile.preferences,
                "org_context": profile.org_context,
            }
        )
```

#### SummaryEnrichStage (ENRICH)

```python
class SummaryEnrichStage:
    """Enrich context with conversation summary."""

    name = "summary_enrich"
    kind = StageKind.ENRICH

    def __init__(self, summary_service):
        self.summary_service = summary_service

    async def execute(self, ctx: StageContext) -> StageOutput:
        session_id = ctx.snapshot.session_id

        if not session_id:
            return StageOutput.skip(reason="No session_id provided")

        summary = await self.summary_service.get_latest_summary(session_id)

        if not summary:
            return StageOutput.ok(summary=None, has_summary=False)

        return StageOutput.ok(
            summary={
                "text": summary.summary_text,
                "cutoff_sequence": summary.cutoff_sequence,
                "version": summary.version,
            },
            has_summary=True,
        )
```

#### LLMStage (TRANSFORM)

```python
# app/pipelines/stages/llm.py

class LLMStage:
    """Generate LLM response with enriched context."""

    name = "llm"
    kind = StageKind.TRANSFORM

    def __init__(self, llm_provider):
        self.llm_provider = llm_provider

    async def execute(self, ctx: StageContext) -> StageOutput:
        inputs = ctx.config.get("inputs")

        # Get input text
        input_text = inputs.get("input_text") if inputs else ctx.snapshot.input_text

        # Get enrichments
        profile = inputs.get("profile", {}) if inputs else {}
        summary_data = inputs.get("summary") if inputs else None

        # Build messages
        messages = self._build_messages(
            input_text=input_text,
            history=ctx.snapshot.messages,
            profile=profile,
            summary=summary_data,
        )

        # Emit start event
        ctx.emit_event("llm.generation.started", {
            "message_count": len(messages),
            "has_summary": bool(summary_data),
        })

        try:
            start_time = ctx.timer.elapsed_ms()
            response = await self.llm_provider.chat(
                messages=messages,
                model=ctx.config.get("model", "llama-3.1-8b-instant"),
                temperature=ctx.config.get("temperature", 0.7),
                max_tokens=ctx.config.get("max_tokens", 1024),
            )
            duration = ctx.timer.elapsed_ms() - start_time

            ctx.emit_event("llm.generation.completed", {
                "duration_ms": duration,
                "tokens_out": len(response.split()),  # Approximate
            })

            return StageOutput.ok(
                response=response,
                model=ctx.config.get("model", "llama-3.1-8b-instant"),
            )

        except Exception as e:
            return StageOutput.fail(
                error=f"LLM generation failed: {str(e)}",
                data={"error_type": type(e).__name__},
            )

    def _build_messages(self, input_text, history, profile, summary):
        messages = []

        # System prompt with context
        system_parts = ["You are a helpful AI sales assistant."]

        if profile.get("display_name"):
            system_parts.append(f"You're talking to {profile['display_name']}.")

        if profile.get("org_context"):
            system_parts.append(f"Organization: {profile['org_context']}")

        if summary:
            system_parts.append(f"\nConversation summary: {summary['text']}")

        messages.append({"role": "system", "content": " ".join(system_parts)})

        # Add recent history (after summary cutoff)
        cutoff = summary.get("cutoff_sequence", 0) if summary else 0
        for msg in history:
            if getattr(msg, "sequence_number", 0) > cutoff:
                messages.append({"role": msg.role, "content": msg.content})

        # Add current input
        if input_text:
            messages.append({"role": "user", "content": input_text})

        return messages
```

#### OutputGuardStage (GUARD)

```python
class OutputGuardStage:
    """Validate LLM output against safety policies."""

    name = "output_guard"
    kind = StageKind.GUARD

    def __init__(self, guard_service):
        self.guard_service = guard_service

    async def execute(self, ctx: StageContext) -> StageOutput:
        inputs = ctx.config.get("inputs")
        response = inputs.get("response", "") if inputs else ""

        result = await self.guard_service.check_output(response)

        if not result.is_safe:
            ctx.emit_event("guard.output.filtered", {
                "reason": result.reason,
            })
            # Replace with safe response instead of cancelling
            return StageOutput.ok(
                response="I apologize, but I cannot provide that response.",
                filtered=True,
                filter_reason=result.reason,
            )

        return StageOutput.ok(
            response=response,
            validated=True,
        )
```

#### PersistStage (WORK)

```python
# app/pipelines/stages/persistence.py

class PersistStage:
    """Persist interaction to database."""

    name = "persist"
    kind = StageKind.WORK

    def __init__(self, interaction_repo):
        self.interaction_repo = interaction_repo

    async def execute(self, ctx: StageContext) -> StageOutput:
        inputs = ctx.config.get("inputs")

        response = inputs.get("response", "") if inputs else ""
        filtered = inputs.get("filtered", False) if inputs else False

        session_id = ctx.snapshot.session_id
        if not session_id:
            return StageOutput.skip(reason="No session_id for persistence")

        # Create assistant interaction
        interaction = await self.interaction_repo.create(
            session_id=session_id,
            role="assistant",
            content=response,
            input_type="text",
            metadata={
                "filtered": filtered,
                "pipeline_run_id": str(ctx.snapshot.pipeline_run_id),
            },
        )

        return StageOutput.ok(
            persisted=True,
            interaction_id=str(interaction.id),
        )
```

### 4.4 Pipeline Execution

```python
# app/services/chat_service.py

from stageflow import StageContext, StageGraph
from stageflow.context import ContextSnapshot
from stageflow.observability import WideEventEmitter
from uuid import uuid4

class ChatService:
    def __init__(self, pipeline_factory, event_sink):
        self.pipeline_factory = pipeline_factory
        self.event_sink = event_sink

    async def process_message(
        self,
        session_id: UUID,
        user_id: UUID,
        org_id: UUID,
        input_text: str,
        messages: list,
    ) -> str:
        # Create pipeline run ID for correlation
        pipeline_run_id = uuid4()

        # Create immutable context snapshot
        snapshot = ContextSnapshot(
            pipeline_run_id=pipeline_run_id,
            request_id=uuid4(),
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            interaction_id=uuid4(),
            topology="chat_pipeline",
            execution_mode="default",
            input_text=input_text,
            messages=messages,
        )

        # Get pipeline and build graph with wide events
        pipeline = self.pipeline_factory.create_chat_pipeline()
        graph = pipeline.build(
            emit_stage_wide_events=True,
            emit_pipeline_wide_event=True,
            wide_event_emitter=WideEventEmitter(),
        )

        # Create execution context
        ctx = StageContext(
            snapshot=snapshot,
            config={
                "model": "llama-3.1-8b-instant",
                "event_sink": self.event_sink,
            },
        )

        # Run pipeline
        results = await graph.run(ctx)

        # Extract response from output_guard or persist stage
        output_guard_result = results.get("output_guard")
        if output_guard_result and output_guard_result.data:
            return output_guard_result.data.get("response", "")

        return ""
```

### 4.5 Custom Interceptors

#### DbEventSinkInterceptor

Persist stageflow events to the `pipeline_events` table:

```python
# app/infrastructure/telemetry/sinks/db_sink.py

from stageflow import EventSink
import asyncio

class DbPipelineEventSink(EventSink):
    """Persist pipeline events to database."""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._pending_tasks = []

    async def emit(self, *, type: str, data: dict) -> None:
        """Emit event synchronously."""
        async with self.db_session_factory() as session:
            event = PipelineEvent(
                pipeline_run_id=data.get("pipeline_run_id"),
                event_type=type,
                event_data=data,
                request_id=data.get("request_id"),
                session_id=data.get("session_id"),
                user_id=data.get("user_id"),
                org_id=data.get("org_id"),
            )
            session.add(event)
            await session.commit()

    def try_emit(self, *, type: str, data: dict) -> None:
        """Fire-and-forget event emission."""
        task = asyncio.create_task(self.emit(type=type, data=data))
        self._pending_tasks.append(task)
        task.add_done_callback(lambda t: self._pending_tasks.remove(t))
```

### 4.6 Pipeline Registry

```python
# app/pipelines/registry.py

from stageflow import pipeline_registry

def register_pipelines(
    guard_service,
    profile_service,
    summary_service,
    llm_provider,
    interaction_repo,
):
    """Register all application pipelines."""

    # Chat pipeline
    pipeline_registry.register(
        "chat",
        create_chat_pipeline(
            guard_service=guard_service,
            profile_service=profile_service,
            summary_service=summary_service,
            llm_provider=llm_provider,
            interaction_repo=interaction_repo,
        ),
    )

    # Script generation pipeline (future)
    # pipeline_registry.register("script_generation", ...)

    # Email generation pipeline (future)
    # pipeline_registry.register("email_generation", ...)
```

### 4.7 Summary Cadence Integration

The summary cadence is tracked via the `summary_states` table and triggered by the `SummaryEnrichStage`:

```python
# app/services/summary_service.py

SUMMARY_THRESHOLD = 8  # Trigger summary every 8 turns
ALWAYS_INCLUDE_LAST_N = 6  # Always include last N messages

class SummaryService:
    def __init__(self, summary_repo, llm_provider):
        self.summary_repo = summary_repo
        self.llm_provider = llm_provider

    async def get_latest_summary(self, session_id: UUID) -> SessionSummary | None:
        return await self.summary_repo.get_latest(session_id)

    async def check_and_create_summary(
        self,
        session_id: UUID,
        interactions: list,
    ) -> SessionSummary | None:
        """Check if summary is needed and create if so."""
        state = await self.summary_repo.get_or_create_state(session_id)

        # Increment turn counter
        state.turns_since_summary += 1

        if state.turns_since_summary < SUMMARY_THRESHOLD:
            await self.summary_repo.update_state(state)
            return None

        # Time to summarize
        messages_to_summarize = [
            i for i in interactions
            if i.sequence_number > state.last_cutoff_sequence
            and i.sequence_number <= len(interactions) - ALWAYS_INCLUDE_LAST_N
        ]

        if not messages_to_summarize:
            return None

        # Generate summary via LLM
        summary_text = await self._generate_summary(messages_to_summarize)

        # Create summary record
        new_cutoff = max(m.sequence_number for m in messages_to_summarize)
        summary = await self.summary_repo.create_summary(
            session_id=session_id,
            summary_text=summary_text,
            cutoff_sequence=new_cutoff,
        )

        # Update state
        state.turns_since_summary = 0
        state.last_cutoff_sequence = new_cutoff
        state.last_summary_at = datetime.now(UTC)
        await self.summary_repo.update_state(state)

        return summary
```

---

## 5. Observability Architecture

### 5.1 Stageflow Observability Integration

Stageflow provides built-in observability via interceptors:

```python
# app/infrastructure/telemetry/setup.py

from stageflow import get_default_interceptors
from stageflow.observability import WideEventEmitter, PipelineRunLogger

def create_interceptor_stack(
    include_auth: bool = True,
    pipeline_run_logger: PipelineRunLogger = None,
) -> list:
    """Create the interceptor stack for pipeline execution."""

    interceptors = get_default_interceptors(include_auth=include_auth)
    # Default includes:
    # - TimeoutInterceptor (priority 5)
    # - CircuitBreakerInterceptor (priority 10)
    # - TracingInterceptor (priority 20)
    # - MetricsInterceptor (priority 40)
    # - ChildTrackerMetricsInterceptor (priority 45)
    # - LoggingInterceptor (priority 50)

    return interceptors
```

### 5.2 Wide Events

Enable wide events for comprehensive telemetry:

```python
from stageflow.observability import WideEventEmitter

# Build pipeline with wide events enabled
graph = pipeline.build(
    emit_stage_wide_events=True,      # Emit after each stage
    emit_pipeline_wide_event=True,    # Emit summary after run
    wide_event_emitter=WideEventEmitter(),
)
```

Wide events include:
- `stage.wide`: Per-stage completion with duration, status, correlation IDs
- `pipeline.wide`: Full run summary with all stage results

### 5.3 OpenTelemetry Integration

```python
# app/infrastructure/telemetry/otel.py

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def init_telemetry(app: FastAPI, settings: Settings):
    """Initialize OpenTelemetry with exporters."""
    resource = Resource.create({
        "service.name": "hellosales-backend",
        "service.version": settings.version,
        "deployment.environment": settings.environment,
    })

    # Traces
    trace_provider = TracerProvider(resource=resource)
    if settings.otel_endpoint:
        trace_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_endpoint))
        )
    trace.set_tracer_provider(trace_provider)

    # Auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
```

### 5.4 Structured Logging with Context

```python
# app/infrastructure/telemetry/logging.py

import json
import logging
from contextvars import ContextVar

# Context variables (compatible with stageflow)
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
org_id_var: ContextVar[str | None] = ContextVar("org_id", default=None)
session_id_var: ContextVar[str | None] = ContextVar("session_id", default=None)
pipeline_run_id_var: ContextVar[str | None] = ContextVar("pipeline_run_id", default=None)

class StructuredFormatter(logging.Formatter):
    """JSON formatter with automatic context injection."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "ts": self.formatTime(record),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "org_id": org_id_var.get(),
            "session_id": session_id_var.get(),
            "pipeline_run_id": pipeline_run_id_var.get(),
        }

        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps({k: v for k, v in log_data.items() if v is not None}, default=str)
```

### 5.5 Metrics Collection

```python
# app/infrastructure/telemetry/metrics.py

from opentelemetry import metrics

meter = metrics.get_meter("hellosales")

# Pipeline metrics (integrated with stageflow)
pipeline_runs_total = meter.create_counter(
    "pipeline_runs_total",
    description="Total pipeline runs by service and status",
)

pipeline_duration_ms = meter.create_histogram(
    "pipeline_duration_ms",
    description="Pipeline execution duration",
    unit="ms",
)

stage_duration_ms = meter.create_histogram(
    "stage_duration_ms",
    description="Stage execution duration",
    unit="ms",
)

# Provider metrics
provider_calls_total = meter.create_counter(
    "provider_calls_total",
    description="Total provider API calls",
)

provider_latency_ms = meter.create_histogram(
    "provider_latency_ms",
    description="Provider API latency",
    unit="ms",
)

provider_cost_cents = meter.create_counter(
    "provider_cost_cents",
    description="Provider API cost",
    unit="cents",
)
```

---

## 6. Error Handling System

### 6.1 Typed Error Hierarchy

```python
# app/domain/errors.py

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

@dataclass
class AppError(Exception):
    """Base application error with full context."""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "retryable": self.retryable,
            "timestamp": self.timestamp.isoformat(),
        }

# --- Not Found Errors ---

@dataclass
class NotFoundError(AppError):
    """Resource not found."""
    retryable: bool = False

@dataclass
class SessionNotFoundError(NotFoundError):
    code: str = "SESSION_NOT_FOUND"

@dataclass
class ProductNotFoundError(NotFoundError):
    code: str = "PRODUCT_NOT_FOUND"

@dataclass
class ClientNotFoundError(NotFoundError):
    code: str = "CLIENT_NOT_FOUND"

@dataclass
class ScriptNotFoundError(NotFoundError):
    code: str = "SCRIPT_NOT_FOUND"

@dataclass
class EmailNotFoundError(NotFoundError):
    code: str = "EMAIL_NOT_FOUND"

# --- Validation Errors ---

@dataclass
class ValidationError(AppError):
    """Input validation failed."""
    retryable: bool = False

@dataclass
class InvalidStateError(ValidationError):
    code: str = "INVALID_STATE"

@dataclass
class GuardBlockedError(ValidationError):
    """Input/output blocked by guardrails."""
    code: str = "GUARD_BLOCKED"

# --- Provider Errors ---

@dataclass
class ProviderError(AppError):
    """External provider failed."""
    provider: str = ""
    operation: str = ""

@dataclass
class ProviderTimeoutError(ProviderError):
    """Provider call timed out."""
    code: str = "PROVIDER_TIMEOUT"
    retryable: bool = True

@dataclass
class ProviderRateLimitError(ProviderError):
    """Provider rate limit exceeded."""
    code: str = "PROVIDER_RATE_LIMITED"
    retryable: bool = True
    retry_after_seconds: int = 60

# --- Pipeline Errors ---

@dataclass
class PipelineError(AppError):
    """Pipeline execution failed."""
    stage: str = ""
    pipeline_run_id: str = ""

@dataclass
class StageFailedError(PipelineError):
    """A stage in the pipeline failed."""
    code: str = "STAGE_FAILED"

@dataclass
class PipelineCancelledError(PipelineError):
    """Pipeline was cancelled (not an error condition)."""
    code: str = "PIPELINE_CANCELLED"
    retryable: bool = False

# --- Auth Errors ---

@dataclass
class AuthError(AppError):
    """Authentication/authorization failed."""
    retryable: bool = False

@dataclass
class TokenExpiredError(AuthError):
    code: str = "TOKEN_EXPIRED"
    retryable: bool = True

@dataclass
class InsufficientPermissionsError(AuthError):
    code: str = "INSUFFICIENT_PERMISSIONS"
```

### 6.2 Stageflow Error Mapping

Map stageflow errors to application errors:

```python
# app/infrastructure/middleware/error_handler.py

from stageflow import StageExecutionError
from stageflow.pipeline.dag import UnifiedPipelineCancelled
from stageflow.observability import summarize_pipeline_error

async def handle_pipeline_error(error: Exception) -> AppError:
    """Convert stageflow errors to application errors."""

    if isinstance(error, UnifiedPipelineCancelled):
        return PipelineCancelledError(
            message=error.reason,
            details={
                "stage": error.stage,
                "partial_results": list(error.results.keys()),
            },
            stage=error.stage,
        )

    if isinstance(error, StageExecutionError):
        summary = summarize_pipeline_error(error)
        return StageFailedError(
            message=summary.get("message", str(error)),
            details={
                "stage": error.stage,
                "error_type": summary.get("type"),
                "retryable": summary.get("retryable", False),
            },
            stage=error.stage,
            retryable=summary.get("retryable", False),
        )

    return AppError(
        code="UNKNOWN_ERROR",
        message=str(error),
        retryable=False,
    )
```

---

## 7. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory
│   ├── config.py                   # Pydantic settings
│   │
│   ├── domain/                     # Domain layer (pure Python)
│   │   ├── __init__.py
│   │   ├── errors.py               # Typed error hierarchy
│   │   ├── events.py               # Domain event types
│   │   │
│   │   ├── entities/               # Domain entities (dataclasses)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── organization.py
│   │   │   ├── company_profile.py
│   │   │   ├── session.py
│   │   │   ├── interaction.py
│   │   │   ├── product.py
│   │   │   ├── client.py
│   │   │   ├── sales_script.py
│   │   │   └── sales_email.py
│   │   │
│   │   └── protocols/              # Abstract interfaces
│   │       ├── __init__.py
│   │       ├── repositories.py
│   │       ├── providers.py        # LLM protocol
│   │       └── services.py
│   │
│   ├── pipelines/                  # Stageflow pipelines
│   │   ├── __init__.py
│   │   ├── registry.py             # Pipeline registration
│   │   ├── chat.py                 # Chat pipeline factory
│   │   │
│   │   └── stages/                 # Stage implementations
│   │       ├── __init__.py
│   │       ├── guards.py           # InputGuard, OutputGuard
│   │       ├── enrichers.py        # ProfileEnrich, SummaryEnrich
│   │       ├── llm.py              # LLMStage
│   │       └── persistence.py      # PersistStage
│   │
│   ├── application/                # Application layer
│   │   ├── __init__.py
│   │   │
│   │   └── services/               # Application services
│   │       ├── __init__.py
│   │       ├── session_service.py
│   │       ├── chat_service.py     # Uses chat pipeline
│   │       ├── summary_service.py
│   │       ├── company_profile_service.py
│   │       ├── product_service.py
│   │       ├── client_service.py
│   │       ├── script_service.py
│   │       └── email_service.py
│   │
│   ├── infrastructure/             # Infrastructure layer
│   │   ├── __init__.py
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── user.py
│   │   │       ├── organization.py
│   │   │       ├── company_profile.py
│   │   │       ├── session.py
│   │   │       ├── interaction.py
│   │   │       ├── observability.py
│   │   │       └── hellosales.py   # products, clients, scripts, emails
│   │   │
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── user_repository.py
│   │   │   ├── company_profile_repository.py
│   │   │   ├── session_repository.py
│   │   │   ├── interaction_repository.py
│   │   │   ├── summary_repository.py
│   │   │   ├── pipeline_repository.py
│   │   │   ├── product_repository.py
│   │   │   ├── client_repository.py
│   │   │   ├── script_repository.py
│   │   │   └── email_repository.py
│   │   │
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── llm/
│   │   │       ├── __init__.py
│   │   │       ├── groq.py
│   │   │       └── google.py
│   │   │
│   │   ├── telemetry/
│   │   │   ├── __init__.py
│   │   │   ├── otel.py
│   │   │   ├── logging.py
│   │   │   ├── metrics.py
│   │   │   └── sinks/
│   │   │       ├── __init__.py
│   │   │       ├── db_sink.py
│   │   │       └── composite_sink.py
│   │   │
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── workos.py
│   │   │   └── context.py
│   │   │
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── request_context.py
│   │       └── error_handler.py
│   │
│   ├── presentation/               # Presentation layer
│   │   ├── __init__.py
│   │   │
│   │   ├── http/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   ├── health.py
│   │   │   ├── auth.py
│   │   │   ├── company_profiles.py
│   │   │   ├── sessions.py
│   │   │   ├── pulse.py
│   │   │   ├── products.py
│   │   │   ├── clients.py
│   │   │   ├── scripts.py
│   │   │   └── emails.py
│   │   │
│   │   └── ws/
│   │       ├── __init__.py
│   │       ├── manager.py
│   │       ├── router.py
│   │       └── handlers/
│   │           ├── __init__.py
│   │           └── chat.py
│   │
│   └── prompts/
│       ├── __init__.py
│       ├── chat.py
│       ├── scripts.py
│       └── emails.py
│
├── migrations/
│   ├── env.py
│   ├── versions/
│   └── alembic.ini
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   │
│   ├── unit/
│   │   ├── pipelines/              # Test stages in isolation
│   │   ├── domain/
│   │   └── application/
│   │
│   └── integration/
│       ├── api/
│       └── pipelines/              # Test full pipeline execution
│
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

## 8. Implementation Phases

### Phase 1: Foundation

**Goal**: Bootable application with auth, database, and stageflow setup.

- [ ] Initialize FastAPI app with configuration
- [ ] Set up SQLAlchemy async with Alembic
- [ ] Create base models (users, organizations, memberships)
- [ ] Implement WorkOS JWT verification
- [ ] Add health check endpoints
- [ ] Set up structured logging
- [ ] Install and configure stageflow
- [ ] Create first migration

**Deliverable**: `GET /health` returns 200, `POST /auth/me` returns user context.

### Phase 2: Observability Core

**Goal**: Full observability pipeline with stageflow integration.

- [ ] Configure OpenTelemetry
- [ ] Create provider_calls, pipeline_runs, pipeline_events models
- [ ] Implement DbPipelineEventSink for stageflow
- [ ] Configure stageflow interceptors (timeout, circuit breaker, tracing, metrics)
- [ ] Add request context middleware
- [ ] Create Pulse API endpoints
- [ ] Add Prometheus metrics endpoint

**Deliverable**: Pipeline runs visible in Pulse dashboard with full event trace.

### Phase 3: Chat Pipeline

**Goal**: Working chat with stageflow pipeline.

- [ ] Create sessions, interactions, summaries models
- [ ] Implement InputGuardStage and OutputGuardStage
- [ ] Implement ProfileEnrichStage
- [ ] Implement SummaryEnrichStage
- [ ] Implement LLMStage with Groq provider
- [ ] Implement PersistStage
- [ ] Wire up chat_pipeline factory
- [ ] Implement ChatService
- [ ] Add WebSocket chat handler
- [ ] Implement summary cadence logic

**Deliverable**: Chat messages flow through stageflow pipeline with full trace.

### Phase 4: HelloSales Content

**Goal**: Products, clients, scripts, and emails.

- [ ] Create products and clients models
- [ ] Create sales_scripts and sales_emails models
- [ ] Implement ProductService, ClientService
- [ ] Implement ScriptService (CRUD + generation)
- [ ] Implement EmailService (CRUD + generation)
- [ ] Create HTTP routes for all entities
- [ ] Add script generation pipeline (optional)
- [ ] Add email generation pipeline (optional)

**Deliverable**: Full CRUD for products, clients, scripts, emails with AI generation.

### Phase 5: Polish & Harden

**Goal**: Production-ready quality.

- [ ] Configure circuit breaker thresholds
- [ ] Implement dead letter queue handling
- [ ] Add rate limiting
- [ ] Write unit tests for stages
- [ ] Write integration tests for pipelines
- [ ] Performance testing
- [ ] Security audit

**Deliverable**: Ready for production traffic.

---

## 9. Quality Recommendations

### 9.1 Robustness

| Technique | Implementation |
|-----------|----------------|
| **Circuit Breaker** | Stageflow's `CircuitBreakerInterceptor` wraps all stages. 3 failures in 60s trips circuit. |
| **Timeout Enforcement** | Stageflow's `TimeoutInterceptor` enforces per-stage timeouts. Default 30s. |
| **Retry with Backoff** | RetryInterceptor for retryable errors. Exponential backoff. |
| **Dead Letter Queue** | Failed pipelines captured with full `ContextSnapshot` for replay. |
| **Graceful Degradation** | OutputGuard replaces blocked content instead of failing. |

### 9.2 Safety

| Technique | Implementation |
|-----------|----------------|
| **Input Validation** | InputGuardStage validates all user input. |
| **Output Validation** | OutputGuardStage validates all LLM output. |
| **SQL Injection Prevention** | SQLAlchemy ORM only. No raw SQL. |
| **Rate Limiting** | Per-user, per-endpoint limits. |
| **Secrets Management** | Environment variables only. Never logged. |
| **Multi-Tenant Isolation** | org_id on every query. Enforced in repositories. |

### 9.3 Scalability

| Technique | Implementation |
|-----------|----------------|
| **Async Everything** | All I/O is async. Stageflow runs stages concurrently. |
| **Parallel Enrichment** | ProfileEnrich and SummaryEnrich run in parallel. |
| **Connection Pooling** | SQLAlchemy pool with min=5, max=20. |
| **Stateless Design** | No in-memory state. All state in Postgres. |
| **Index Strategy** | Indexes on all foreign keys and common queries. |

### 9.4 Maintainability

| Technique | Implementation |
|-----------|----------------|
| **Pipeline Architecture** | All AI flows through stageflow DAGs. Easy to modify, test, observe. |
| **Stage Isolation** | Each stage has single responsibility. Testable in isolation. |
| **Protocol-Based Design** | Providers, repositories implement protocols. Swappable. |
| **Comprehensive Events** | Wide events capture full context for debugging. |
| **Test Coverage** | Unit tests for stages. Integration tests for pipelines. |

---

## 10. Central Pulse Compatibility

### 10.1 Required API Endpoints

Compatible with eloquence-ui-tweaks/central pulse dashboard:

```python
# presentation/http/pulse.py

@router.get("/pulse/pipeline-runs")
async def list_pipeline_runs(
    service: str | None = None,
    topology: str | None = None,
    success: bool | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PipelineRunListResponse:
    """List pipeline runs with filters."""

@router.get("/pulse/pipeline-runs/{run_id}")
async def get_pipeline_run(run_id: UUID) -> PipelineRunDetailResponse:
    """Get detailed pipeline run with all events."""

@router.get("/pulse/pipeline-runs/{run_id}/events")
async def list_pipeline_events(run_id: UUID) -> list[PipelineEventResponse]:
    """Get stageflow events for a pipeline run."""

@router.get("/pulse/provider-calls")
async def list_provider_calls(
    provider: str | None = None,
    operation: str | None = None,
    success: bool | None = None,
    limit: int = 50,
) -> list[ProviderCallResponse]:
    """List provider calls with filters."""

@router.get("/pulse/metrics")
async def get_metrics() -> MetricsResponse:
    """Get aggregated metrics for dashboard."""

@router.get("/pulse/dead-letter-queue")
async def list_dlq_entries(
    status: str | None = None,
    limit: int = 50,
) -> list[DLQEntryResponse]:
    """List dead letter queue entries."""
```

### 10.2 Response Schemas

```python
class PipelineRunResponse(BaseModel):
    id: UUID
    service: str
    topology: str | None
    behavior: str | None

    request_id: str | None
    session_id: UUID | None
    user_id: UUID | None
    org_id: UUID | None

    # Stageflow-specific
    stages: dict[str, StageResultSummary]

    total_latency_ms: int | None
    ttft_ms: int | None
    tokens_in: int | None
    tokens_out: int | None
    total_cost_cents: int | None

    success: bool
    error: str | None

    started_at: datetime
    completed_at: datetime | None

class StageResultSummary(BaseModel):
    status: str  # 'ok', 'skip', 'cancel', 'fail'
    duration_ms: int
    error: str | None

class PipelineEventResponse(BaseModel):
    id: UUID
    pipeline_run_id: UUID
    event_type: str  # e.g., 'stage.llm.completed', 'stage.wide'
    event_data: dict
    occurred_at: datetime
```

---

## Appendix A: Key Dependencies

```toml
# pyproject.toml

[project]
dependencies = [
    # Web framework
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "websockets>=12.0",

    # Database
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",

    # Validation
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",

    # Auth
    "pyjwt>=2.8.0",
    "cryptography>=42.0.0",

    # HTTP client
    "httpx>=0.27.0",

    # AI providers
    "groq>=0.9.0",
    "google-genai>=1.0.0",

    # Pipeline framework
    "stageflow",  # Local dependency: ../stageflow

    # Observability
    "opentelemetry-api>=1.24.0",
    "opentelemetry-sdk>=1.24.0",
    "opentelemetry-exporter-otlp>=1.24.0",
    "opentelemetry-instrumentation-fastapi>=0.45b0",
    "opentelemetry-instrumentation-sqlalchemy>=0.45b0",
    "opentelemetry-instrumentation-httpx>=0.45b0",
    "prometheus-client>=0.20.0",

    # Vector embeddings
    "pgvector>=0.2.5",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]
```

---

## Appendix B: Environment Variables

```bash
# .env.example

# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/hellosales

# Auth (WorkOS)
WORKOS_CLIENT_ID=client_xxx
WORKOS_API_KEY=sk_xxx
WORKOS_ISSUER=https://api.workos.com
WORKOS_AUDIENCE=xxx

# AI Providers
GROQ_API_KEY=gsk_xxx
GOOGLE_API_KEY=xxx

# Observability
LOG_LEVEL=INFO
OTEL_ENDPOINT=http://localhost:4317
PROMETHEUS_METRICS_ENABLED=true

# Stageflow settings
STAGE_TIMEOUT_MS=30000
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_OPEN_SECONDS=60

# Feature flags
SUMMARY_ENABLED=true
SUMMARY_THRESHOLD=8
GUARDRAILS_ENABLED=true
```

---

## Appendix C: Testing Strategy

### Unit Tests for Stages

```python
# tests/unit/pipelines/test_guards.py

import pytest
from unittest.mock import Mock, AsyncMock
from stageflow import StageContext, StageStatus
from stageflow.context import ContextSnapshot

from app.pipelines.stages.guards import InputGuardStage

@pytest.fixture
def guard_service():
    service = Mock()
    service.check_input = AsyncMock()
    return service

@pytest.fixture
def ctx():
    snapshot = ContextSnapshot(
        pipeline_run_id=uuid4(),
        request_id=uuid4(),
        session_id=uuid4(),
        user_id=uuid4(),
        org_id=uuid4(),
        interaction_id=uuid4(),
        topology="test",
        execution_mode="test",
        input_text="Hello, how are you?",
    )
    return StageContext(snapshot=snapshot)

async def test_input_guard_allows_safe_input(guard_service, ctx):
    guard_service.check_input.return_value = Mock(is_safe=True)

    stage = InputGuardStage(guard_service)
    result = await stage.execute(ctx)

    assert result.status == StageStatus.OK
    assert result.data["validated"] is True

async def test_input_guard_blocks_unsafe_input(guard_service, ctx):
    guard_service.check_input.return_value = Mock(
        is_safe=False,
        reason="Contains blocked content",
    )

    stage = InputGuardStage(guard_service)
    result = await stage.execute(ctx)

    assert result.status == StageStatus.CANCEL
    assert result.data["blocked"] is True
```

### Integration Tests for Pipelines

```python
# tests/integration/pipelines/test_chat_pipeline.py

import pytest
from stageflow import StageContext
from stageflow.context import ContextSnapshot

from app.pipelines.chat import create_chat_pipeline

@pytest.fixture
def chat_pipeline(
    guard_service,
    profile_service,
    summary_service,
    llm_provider,
    interaction_repo,
):
    return create_chat_pipeline(
        guard_service=guard_service,
        profile_service=profile_service,
        summary_service=summary_service,
        llm_provider=llm_provider,
        interaction_repo=interaction_repo,
    )

async def test_chat_pipeline_full_execution(chat_pipeline):
    snapshot = ContextSnapshot(
        pipeline_run_id=uuid4(),
        request_id=uuid4(),
        session_id=uuid4(),
        user_id=uuid4(),
        org_id=uuid4(),
        interaction_id=uuid4(),
        topology="chat_pipeline",
        execution_mode="test",
        input_text="Hello!",
        messages=[],
    )

    graph = chat_pipeline.build()
    ctx = StageContext(snapshot=snapshot)

    results = await graph.run(ctx)

    # All stages should complete
    assert "input_guard" in results
    assert "profile_enrich" in results
    assert "summary_enrich" in results
    assert "llm" in results
    assert "output_guard" in results
    assert "persist" in results

    # Should have a response
    assert results["output_guard"].data.get("response")
```

---

*Document Version: 2.0*
*Created: 2026-01-09*
*Updated: 2026-01-09*
*Author: Claude (Opus 4.5)*
