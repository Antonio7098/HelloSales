# Sprint Reasoning: Voice Primitives

> Project: HelloSales
> Sprint ID: sprint-11-voice-primitives
> Created: 2026-04-24
> Tracker: `ops/sprints/sprint-11-voice-primitives/tracker.md`

## Overview

Sprint 11 creates the first provider-neutral voice runtime primitives for HelloSales.

The scope is foundation work:
- speech-to-text primitives
- text-to-speech primitives
- streaming LLM text to TTS audio
- duplex session and interruption control primitives
- provider registry, settings, diagnostics, errors, tests, and smoke seams
- documentation for provider setup and future extension

The sprint should not create product-specific call flows, sales personas, telephony policy, or customer-facing voice UX before the product brief requires those commitments.

The desired design property is modularity. STT, TTS, realtime speech-to-speech, transport, turn detection, buffering, and orchestration must be separable ports. A caller should be able to compose a simple batch transcription path, a text-to-speech render path, a streaming `LLM -> TTS` path, or a duplex voice session without changing provider-specific adapters or agent prompt policy.

## Requirement Map

### Contract Coverage Reviewed For This Sprint

| Contract File | Area | Applicability | Why It Matters |
| --- | --- | --- | --- |
| `ops/operational-contract/architecture.md` | Layering, module boundaries, provider seams | Applicable | Voice adds provider-backed runtime infrastructure and must keep providers behind ports and composition. |
| `ops/operational-contract/errors.md` | Provider failures, streaming failures, redaction | Applicable | Audio provider calls, transport streams, cancellation, and unsupported format errors need stable failure shapes. |
| `ops/operational-contract/observability.md` | Correlation, diagnostics, lifecycle state | Applicable | Voice sessions are long-lived and must expose stream/session state, provider health, and terminal outcomes. |
| `ops/operational-contract/testing.md` | Unit, integration, smoke, real-provider checks | Applicable | Provider-backed voice paths need fake seams and at least one real-provider smoke or explicit deferral. |
| `ops/operational-contract/workflows.md` | Orchestration boundary and state | Applicable | Duplex voice spans multiple steps, but low-latency frame processing should not be hidden in generic workflow stages. |
| `ops/operational-contract/llm.md` | LLM substrate, lifecycle, prompt/version visibility | Applicable | Streaming LLM text to TTS extends the existing agent and provider runtime. |
| `ops/operational-contract/pre-brief-scope.md` | Generic foundation vs product assumptions | Applicable | Voice primitives are safe foundation only if they stay product-neutral and narrow. |
| `ops/operational-contract/frontend.md` | Browser transport and frontend ownership | Applicable if a browser capture/playback shell is added | Voice UI, if touched, must stay generic and app-owned or feature-owned according to the frontend contract. |

### Requirement Index Used In This Sprint

| Requirement ID | Title | Area | Applicability | Why It Matters For This Sprint |
| --- | --- | --- | --- | --- |
| PRE-SCOPE-001 | Foundation work may proceed before the brief | Pre-Brief Scope | Applicable | Provider-neutral audio/runtime primitives are scaffolding. |
| PRE-SCOPE-002 | Product-specific commitments must wait for the brief | Pre-Brief Scope | Applicable | The sprint must not define sales-call scripts, coaching personas, telephony routing, or lead workflows. |
| PRE-SCOPE-003 | Operational scaffolding should be favored over product assumptions | Pre-Brief Scope | Applicable | Ports, adapters, diagnostics, and smokes are preferred over a polished product flow. |
| PRE-SCOPE-004 | Public APIs must remain intentionally narrow before the brief | Pre-Brief Scope | Applicable | Initial voice surfaces should be operational, internal, or smoke-oriented. |
| ARCH-CORE-001 | Module boundaries must remain explicit | Architecture | Applicable | Voice primitives need a bounded module or runtime package with a small public API. |
| ARCH-CORE-002 | Dependency direction must point inward | Architecture | Applicable | Use cases and services must depend on STT/TTS/realtime ports, not SDK clients. |
| ARCH-LAYER-002 | Use cases depend on ports, not infra | Architecture | Applicable | Fake STT/TTS/realtime providers must replace concrete adapters in tests. |
| ARCH-ENTRY-001 | Transport adapters must stay thin | Architecture | Applicable | WebSocket, SSE, upload, or WebRTC helper routes should validate, authorize, and delegate only. |
| ARCH-MODULE-001 | Module public APIs must stay small and stable | Architecture | Applicable | The voice module should expose commands, views, and facades, not provider internals. |
| ARCH-COMP-001 | Composition must happen through registrars | Architecture | Applicable | Voice providers and services must be wired through the composition root and registry. |
| ARCH-SHARED-001 | Shared and platform code must stay domain-neutral | Architecture | Applicable | Audio frame types and provider ports are platform-level; business behavior remains outside them. |
| ERR-CORE-001 | No failure may disappear | Errors | Applicable | Stream errors, provider disconnects, unsupported audio formats, and cancellation must end explicitly. |
| ERR-SHAPE-001 | Operational errors must preserve the canonical shape | Errors | Applicable | Voice errors need code, category, retryable, component, operation, and correlation metadata. |
| ERR-CODE-001 | Error codes must be stable and machine-usable | Errors | Applicable | Operators need distinct codes for STT timeout, TTS failure, stream closed, provider auth, and barge-in cancellation. |
| ERR-TRANS-001 | Error translation must preserve cause and context | Errors | Applicable | SDK/WebSocket/HTTP errors must preserve remote status, request id, model, endpoint, and audio config. |
| ERR-STARTUP-001 | Known-fatal startup failures must fail before traffic | Errors | Ambiguous | Voice providers may be optional locally but required when configured as production-required. |
| ERR-HTTP-001 | Transport adapters must preserve the operational signal | Errors | Applicable if routes are added | Upload, stream, and token routes must return structured failures. |
| ERR-BG-001 | Background work must end in explicit inspectable failure state | Errors | Applicable | Long-lived duplex sessions and stream tasks must have terminal state. |
| ERR-PROVIDER-001 | Provider failures must remain classified and observable | Errors | Applicable | STT, TTS, realtime, and telephony providers are external dependencies. |
| ERR-REDACT-001 | Redaction must protect secrets without destroying diagnosis | Errors | Applicable | Audio payloads, transcripts, API keys, and provider tokens need redaction rules. |
| OBS-CORE-001 | Failures must produce structured operational signals | Observability | Applicable | Stream/session/provider failures must be visible. |
| OBS-CORR-001 | Correlation identifiers must survive subsystem boundaries | Observability | Applicable | Request, session, run, turn, voice session, provider call, and task ids must correlate. |
| OBS-HEALTH-001 | Health endpoints must reflect operational truth | Observability | Applicable | Required voice providers should affect readiness; optional providers should show degraded/disabled state. |
| OBS-DIAG-001 | Diagnostics surfaces must expose operator-relevant state | Observability | Applicable | Diagnostics should include configured voice providers and recent voice session summaries. |
| OBS-BG-001 | Background work must have visible terminal state | Observability | Applicable | Duplex tasks, stream bridges, and cancellation must be inspectable. |
| OBS-ALERT-001 | High-severity signals must be machine-usable for alerting | Observability | Applicable | Stable component and failure codes are needed for voice provider incidents. |
| TEST-SEAM-001 | Collaborators must be replaceable through public seams | Testing | Applicable | Fake STT/TTS/realtime providers and fake transports are mandatory. |
| TEST-UNIT-001 | Business logic must have unit coverage | Testing | Applicable | Chunking, buffering, format validation, session state, and interruption decisions are deterministic. |
| TEST-INT-001 | Wiring and persistence changes must have integration coverage | Testing | Applicable | Provider registry, diagnostics, routes, and event streams need integration coverage. |
| TEST-SMOKE-001 | Critical runtime paths must have smoke coverage | Testing | Applicable | Batch STT, TTS, streaming `LLM -> TTS`, and duplex loop smokes should be centralized. |
| TEST-SMOKE-002 | Critical external provider paths must have real-provider smoke coverage | Testing | Applicable | Any supported real OpenAI/Deepgram/ElevenLabs/etc. path needs smoke evidence or explicit deferral. |
| TEST-FAIL-001 | Failure paths must be tested explicitly | Testing | Applicable | Timeout, invalid format, provider disabled, stream disconnect, and cancellation paths need tests. |
| TEST-DET-001 | Tests must remain deterministic and non-brittle | Testing | Applicable | Voice tests should assert events, state, bytes/chunks, and metadata rather than exact wording. |
| WF-SCOPE-001 | Workflows must be used only for real orchestration | Workflows | Applicable | Low-latency frame processing should be an async runtime, not a generic workflow substitute. |
| WF-BOUNDARY-001 | Workflow engines must stay behind app-owned boundaries | Workflows | Applicable | If a later call workflow uses a workflow engine, voice provider details must remain behind app boundaries. |
| WF-STATE-001 | Workflow outcomes must be explicit and inspectable | Workflows | Applicable | Voice sessions need terminal state, step outcomes, and partial-failure detail. |
| WF-RETRY-001 | Retry and cancellation semantics must be explicit | Workflows | Applicable | Provider retry, stream timeout, user interruption, and shutdown cancellation must be declared. |
| LLM-BOUNDARY-001 | Shared substrate, runtime mechanics, and mode-specific policy must stay separated | LLM Runtime | Applicable | Voice should extend generic LLM streaming without mixing prompt policy into audio providers. |
| LLM-TOOL-001 | Tool execution boundaries must stay explicit and mode-scoped | LLM Runtime | Applicable | Duplex agent sessions may use tools; tool lifecycle must remain persisted and inspectable. |
| LLM-IO-001 | Structured input and output boundaries must stay explicit when used | LLM Runtime | Non-Applicable | This sprint is not adding structured worker output. |
| LLM-LIFECYCLE-001 | Lifecycle controls must stay explicit and inspectable | LLM Runtime | Applicable | Voice sessions need explicit start, active, interrupted, cancelled, completed, and failed states. |
| LLM-RUN-001 | Runs and events must be durable or inspectable | LLM Runtime | Applicable | Voice-linked agent runs and stream events must not vanish into transient logs. |
| LLM-PROMPT-001 | Prompts must be explicitly versioned and version propagation must stay observable | LLM Runtime | Applicable if voice-specific prompt policy changes | If a voice agent prompt is added, it needs prompt identity/version propagation. |
| LLM-EXPOSE-001 | Operational exposure must flow through application modules | LLM Runtime | Applicable | Routes should expose module-owned voice services, not runtime internals. |
| LLM-OBS-001 | LLM runtime monitoring must reuse the canonical observability runtime | LLM Runtime | Applicable | Voice LLM spans/events should reuse existing observability. |
| FE-APP-001 | App layer must only compose global runtime concerns | Frontend | Applicable if frontend is touched | Browser audio permissions/session bootstrap belong at app/runtime edges. |
| FE-API-001 | API access must be explicit, typed, and feature-owned | Frontend | Applicable if frontend is touched | Any voice API client must be typed and not scattered across components. |
| FE-STATE-001 | State must be placed by responsibility | Frontend | Applicable if frontend is touched | Mic state, playback state, and connection state need clear ownership. |

### Applicable Requirements

- **PRE-SCOPE-001 / PRE-SCOPE-003:** Voice primitives are valid foundation work if they stay provider-neutral and reusable.
- **PRE-SCOPE-002 / PRE-SCOPE-004:** Avoid sales-call flows, personas, telephony routing, or broad public APIs.
- **ARCH-CORE-001 / ARCH-LAYER-002 / ARCH-COMP-001:** STT, TTS, realtime voice, and transport must be explicit ports wired through composition.
- **ERR-PROVIDER-001 / ERR-TRANS-001 / ERR-REDACT-001:** Provider failures and audio/transcript data require classified errors and careful redaction.
- **OBS-CORR-001 / OBS-DIAG-001 / OBS-BG-001:** Voice sessions and streams need correlation, diagnostics, and visible terminal state.
- **TEST-SEAM-001 / TEST-SMOKE-002:** Fake provider seams are mandatory, and any supported real provider must have smoke coverage or an explicit deferral.
- **WF-SCOPE-001 / WF-RETRY-001:** Use explicit async stream/session runtimes for low-latency frame processing; reserve workflow engines for later multi-step business orchestration.
- **LLM-LIFECYCLE-001 / LLM-RUN-001 / LLM-OBS-001:** LLM-to-TTS and duplex agent paths must keep lifecycle and observability inspectable.

### Non-Applicable Requirements

- **LLM-IO-001:** No structured worker input/output contract is introduced in this sprint.
- **FE-FEATURE-001 / FE-WORKFLOW-001:** No frontend feature or user journey is required unless the tracker is revised to add a browser voice demo.

### Ambiguous Or Conflicting Requirements

- **ERR-STARTUP-001 vs optional voice providers:** Voice should be optional in local development and CI, but readiness should fail when a deployment explicitly marks a voice provider as required.
- **WF-SCOPE-001 vs duplex orchestration:** Duplex sessions coordinate many moving parts, but per-frame audio is latency-sensitive. The sprint should implement a voice session runtime with inspectable state rather than forcing every frame through a workflow engine.
- **Realtime speech-to-speech vs modular STT/TTS pipeline:** Realtime S2S is lower-latency, but a chained `STT -> LLM -> TTS` pipeline is more inspectable and extends the existing text-agent runtime. The sprint should support both as separate provider ports, while shipping the chained path first.
- **Transcript retention vs privacy:** Transcripts are useful for inspection, but raw audio and full transcripts can be sensitive. The first design should retain metadata and bounded transcript artifacts only where explicitly configured.

### Open Questions

- Which provider credentials will be available locally for real-provider smoke: OpenAI, Deepgram, ElevenLabs, Cartesia, or another provider?
- Should voice primitives target browser audio first, server-side batch jobs first, or telephony/SIP later?
- Should transcripts and audio chunks be persisted by default, or should persistence be metadata-only until product privacy requirements are settled?
- Should the first duplex surface use WebSocket, WebRTC, or server-side test harness only?

## Current Research

**Research Status:** Completed on 2026-04-24.

### Sources Consulted

- [OpenAI Voice Agents](https://platform.openai.com/docs/guides/voice-agents): Compares speech-to-speech sessions with chained voice pipelines and recommends Realtime sessions for browser voice and chained pipelines when extending text agents.
- [OpenAI Realtime API with WebRTC](https://platform.openai.com/docs/guides/realtime-webrtc): Recommends WebRTC over WebSocket for browser clients connecting to realtime models, with server-mediated session setup.
- [OpenAI Speech to Text](https://platform.openai.com/docs/guides/speech-to-text): Documents transcription endpoints, newer transcribe models, streaming transcription, realtime transcription sessions, VAD settings, and ephemeral-token auth.
- [OpenAI Text to Speech](https://platform.openai.com/docs/guides/text-to-speech): Documents streaming TTS, supported formats, and recommends `wav` or `pcm` for fastest response times.
- [LiveKit Agents](https://docs.livekit.io/agents/): Describes production voice-agent concerns including streaming audio, STT-LLM-TTS pipelines, turn detection, interruptions, tool use, integrations, and deployment orchestration.
- [Pipecat Pipeline and Frame Processing](https://docs.pipecat.ai/guides/learn/pipeline): Provides a frame-based model separating input audio, transcription, LLM text, TTS text, output audio, interruptions, and errors.
- [Deepgram Endpointing and Interim Results](https://developers.deepgram.com/docs/understand-endpointing-interim-results): Shows how endpointing and interim transcripts can drive turn segmentation and downstream processing.
- [ElevenLabs Realtime TTS WebSockets](https://elevenlabs.io/docs/websockets): Documents bidirectional TTS streaming, audio chunks, buffering, and TTFB/quality latency trade-offs.

### Relevant Current Guidance

- **Two architecture families must be represented:** Current OpenAI guidance distinguishes direct speech-to-speech sessions from chained voice pipelines. HelloSales should not collapse these into one provider interface.
- **Browser duplex voice should prefer WebRTC eventually:** Current Realtime guidance recommends WebRTC for browser clients. Sprint 11 should design transport ports so WebRTC can be added later without rewriting STT/TTS primitives.
- **Chained pipelines remain valuable:** Chained `STT -> LLM -> TTS` keeps transcription, tool calls, prompt versions, and output text inspectable. That matches existing HelloSales runtime constraints better than hidden provider-native speech-to-speech as the only path.
- **Streaming must be frame/event based:** Pipecat and LiveKit both reinforce that interruptions, partial transcripts, LLM deltas, and TTS chunks are different event/frame classes. HelloSales should model these explicitly.
- **Turn detection is a first-class primitive:** Endpointing, interim results, VAD, and barge-in should be configurable policies, not baked into a provider adapter.
- **TTS chunking has quality/latency trade-offs:** Streaming TTS providers buffer partial text to balance naturalness and latency. The sprint needs a text segmenter and flush policy, not direct token-by-token forwarding.

### Options Or Guidance Rejected

- **Use only provider-native speech-to-speech:** Rejected as the only MVP path because it hides STT/TTS boundaries and makes it harder to reuse existing text-agent lifecycle, tools, prompt versioning, and tests.
- **Build a full browser WebRTC product flow now:** Rejected for this sprint because it would add UX and transport commitments before the backend primitives exist.
- **Send every LLM token directly to TTS:** Rejected because TTS providers often need buffered text for quality and latency control. The runtime should segment by punctuation, size, timeout, and explicit flush.
- **Persist raw audio by default:** Rejected until privacy/product requirements are explicit. Metadata and bounded text/event artifacts are safer defaults.

### Impact On Reasoning

- The sprint should introduce independent `STTProviderPort`, `TTSProviderPort`, `RealtimeVoiceProviderPort`, and `VoiceTransportPort` contracts.
- The first implemented path should be chained and inspectable: audio/transcript input, existing agent streaming text output, text segmentation, streaming TTS chunks, and ordered voice events.
- Realtime S2S support should be an explicit extension point, not a shortcut through the existing LLM provider.
- Duplex session state should model interruption and cancellation explicitly.

## Existing Code Constraints

- Provider-backed integrations already assemble through `platform/composition/providers.py`.
- Current providers include auth, LLM, and web search. Voice should extend this pattern rather than create another registry.
- The LLM provider port already supports `complete_with_tools(..., on_text_delta=...)`, and the agent runtime persists `agent.response.delta` events.
- Agent runs, turns, tool calls, approvals, permissions, sessions, and event streams are already inspectable.
- Session attachment already stores user, assistant, and tool chronology; voice should add bounded voice session metadata without assuming raw-audio persistence.
- HTTP routes are thin and resolve services through dependencies; any voice route should follow the same style.
- The frontend exists but voice UI should not be introduced unless explicitly scoped as a generic shell.

## Feature Analysis

### Feature 1: Provider-Neutral Audio And Voice Contracts

**Description:** Add platform-level voice contracts for audio frames, transcripts, speech chunks, realtime voice events, voice sessions, and provider ports.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/voice/`
- `backend/src/hello_sales_backend/platform/composition/providers.py`
- `backend/src/hello_sales_backend/platform/config/settings.py`
- `backend/src/hello_sales_backend/platform/observability/health.py`

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-SHARED-001 | Voice contracts stay domain-neutral | `platform/voice/` models and ports | Import and naming review |
| ARCH-COMP-001 | Providers are wired centrally | provider registry and settings | Provider registry tests |
| ERR-PROVIDER-001 | Provider failures normalize remote context | adapter error mapping | Failure-path unit tests |
| OBS-DIAG-001 | Provider availability is inspectable | diagnostics and readiness | Integration tests |
| TEST-SEAM-001 | Providers are fakeable | port definitions and overrides | Fake-provider tests |

**Current-System Analysis**
- Voice belongs near existing `platform/llm`, `platform/web_search`, and `platform/auth` provider boundaries.
- Use cases should not depend on concrete SDKs, WebSocket clients, or audio formats beyond normalized platform types.

**Options Considered**
- **Option A:** Add one broad `VoiceProviderPort` with every capability.
- **Option B:** Add separate STT, TTS, realtime voice, turn detection, and transport ports.
- **Option C:** Put all voice behavior inside the existing LLM provider.

**Chosen Approach**
- Adopt Option B. Define narrow ports and compose them into higher-level services.

**Decision Justification**
- Separate ports preserve provider choice and allow OpenAI STT with ElevenLabs TTS, or Deepgram STT with OpenAI LLM, or later OpenAI Realtime S2S.
- Option A would become a god interface.
- Option C would violate the LLM substrate boundary and make non-LLM audio providers awkward.

**Expected Evidence**
- **Tests:** provider registry settings, disabled providers, fake STT/TTS/realtime adapters.
- **Runtime Evidence:** diagnostics expose voice provider kinds, configured state, required state, and degraded state.
- **Review Checks:** platform voice code has no product-domain language or prompt policy.

---

### Feature 2: STT Primitive

**Description:** Add a reusable STT service that accepts audio input, validates format constraints, calls a provider port, and returns normalized transcript events or final transcript views.

**Affected Areas**
- `backend/src/hello_sales_backend/modules/voice/`
- `backend/src/hello_sales_backend/platform/voice/stt.py`
- optional `backend/src/hello_sales_backend/platform/voice/providers/openai.py`
- tests and docs

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-LAYER-002 | Service depends on STT port | `VoiceService.transcribe()` | Unit tests with fake STT |
| ERR-CODE-001 | Invalid format and provider failures are distinct | STT validation and adapter mapping | Negative tests |
| ERR-REDACT-001 | Raw audio is not logged | logging and error details | Review and tests |
| TEST-SMOKE-002 | Real provider path is smoke-tested if supported | smoke suite | Smoke evidence or deferral |

**Current-System Analysis**
- No current audio primitives exist, so this service should be small and command/view driven like `modules/web_search`.
- Current error and provider patterns are mature enough to reuse.

**Options Considered**
- **Option A:** Batch-only STT first.
- **Option B:** Streaming STT first.
- **Option C:** Model both final transcript and streaming transcript events in the contract, but ship batch or provider-gated streaming based on credentials.

**Chosen Approach**
- Adopt Option C. Contract for both, implement the cheapest reliable path first.

**Decision Justification**
- Batch STT is easy to test, but future duplex needs interim/final events.
- Streaming STT should not be bolted on later with incompatible models.
- A unified event model lets Deepgram-style interim/final events and OpenAI realtime transcription events map to the same application surface.

**Expected Evidence**
- **Tests:** audio format validation, size/duration limits, final transcript normalization, provider disabled, provider timeout.
- **Runtime Evidence:** STT events include voice session id, provider, model, language, duration metadata, and correlation ids.
- **Review Checks:** no raw audio bytes in logs or structured errors.

---

### Feature 3: TTS Primitive

**Description:** Add a reusable TTS service that turns text into audio chunks or a final audio payload through a provider-neutral TTS port.

**Affected Areas**
- `backend/src/hello_sales_backend/modules/voice/`
- `backend/src/hello_sales_backend/platform/voice/tts.py`
- optional TTS provider adapters
- docs and smoke harness

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-LAYER-002 | Service depends on TTS port | `VoiceService.synthesize()` | Fake-provider unit tests |
| ERR-PROVIDER-001 | TTS failures preserve provider context | adapter errors | Failure tests |
| OBS-CORR-001 | Correlation follows synthesis | TTS context and events | Integration tests |
| TEST-DET-001 | Tests avoid brittle audio quality checks | test strategy | Stable chunk/metadata assertions |

**Current-System Analysis**
- The existing LLM runtime can emit deltas, but no audio output path exists.
- The TTS primitive should be usable by agents, workers, and future frontend routes without knowing provider-specific voice names.

**Options Considered**
- **Option A:** Return only complete files.
- **Option B:** Return only streaming chunks.
- **Option C:** Support both final render and async chunk stream through one TTS port.

**Chosen Approach**
- Adopt Option C.

**Decision Justification**
- Complete files are useful for smokes and tests.
- Streaming chunks are required for low-latency voice.
- Both should share validation, provider settings, redaction, and diagnostics.

**Expected Evidence**
- **Tests:** text validation, voice selection, output format selection, chunk ordering, provider disabled, timeout/error mapping.
- **Runtime Evidence:** TTS events include provider, model, voice id, output format, first-byte timing where available, and terminal status.
- **Review Checks:** provider-specific voice names stay settings/config concerns, not public service contract requirements.

---

### Feature 4: Streaming LLM Text To TTS Audio Bridge

**Description:** Connect existing LLM streaming deltas to TTS through a text segmenter and ordered audio event stream.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/voice/streaming.py`
- `backend/src/hello_sales_backend/modules/voice/`
- `backend/src/hello_sales_backend/platform/agents/runtime.py` only if a minimal extension point is needed
- agent event stream tests

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| LLM-BOUNDARY-001 | LLM deltas and TTS remain separate mechanics | bridge design | Import/review checks |
| LLM-RUN-001 | Stream events are inspectable | voice-linked agent events | Integration tests |
| WF-RETRY-001 | Flush, cancellation, and retry are explicit | bridge runtime | Unit failure tests |
| OBS-BG-001 | Bridge tasks have terminal state | stream task lifecycle | Diagnostics/tests |

**Current-System Analysis**
- `GenericAgentRuntime._complete_with_retry()` already supports `on_text_delta`.
- `agent.response.delta` events are persisted. The bridge can either subscribe to those events or use a direct callback extension that fans out text to both persistence and TTS.

**Options Considered**
- **Option A:** Subscribe to persisted agent delta events and synthesize after the fact.
- **Option B:** Add a direct text-delta sink interface to the agent runtime.
- **Option C:** Fork a separate voice-specific agent runtime.

**Chosen Approach**
- Prefer Option B if implementation remains small; otherwise use Option A as a lower-risk bridge. Do not fork the agent runtime.

**Decision Justification**
- A text-delta sink lets TTS begin before the turn completes and keeps latency down.
- Persisted event subscription is easier but may add avoidable latency and backpressure complexity.
- Forking runtime would duplicate tool, approval, prompt, retry, and observability behavior.

**Expected Evidence**
- **Tests:** text segmentation by punctuation/length/time, ordered chunk emission, final flush, cancellation, TTS failure after partial audio, and no additional LLM retries after audio has streamed unless explicitly safe.
- **Runtime Evidence:** ordered `voice.text.segment`, `voice.audio.delta`, `voice.audio.completed`, and `voice.session.failed/cancelled` events.
- **Review Checks:** existing agent tool lifecycle remains unchanged and inspectable.

---

### Feature 5: Duplex Voice Session Runtime

**Description:** Add a voice session runtime that coordinates input audio, STT, turn detection, agent execution, TTS playback chunks, interruption/barge-in, cancellation, and terminal state.

**Affected Areas**
- `backend/src/hello_sales_backend/modules/voice/`
- `backend/src/hello_sales_backend/platform/voice/session.py`
- optional `entrypoints/http/routes/voice.py` for internal/testing surfaces
- diagnostics and smoke harness

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| WF-SCOPE-001 | Duplex runtime is real orchestration but not per-frame workflow abuse | voice session runtime | Reasoning/review |
| WF-STATE-001 | Outcomes are explicit | session state machine | Unit/integration tests |
| LLM-LIFECYCLE-001 | Interruptions and cancellation are inspectable | session events | Failure/cancel tests |
| OBS-BG-001 | Long-lived sessions expose terminal state | diagnostics | Integration tests |
| ERR-BG-001 | Stream tasks do not disappear | task ownership | Unit/integration tests |

**Current-System Analysis**
- Background task runner and agent/session stores already provide lifecycle patterns.
- Duplex voice should build on existing agent runs and sessions rather than inventing a hidden conversation store.

**Options Considered**
- **Option A:** Full-duplex browser WebRTC implementation in Sprint 11.
- **Option B:** Server-side duplex runtime with fake transport, STT/TTS providers, and optional thin internal stream route.
- **Option C:** Only batch STT/TTS utilities with no duplex runtime.

**Chosen Approach**
- Adopt Option B.

**Decision Justification**
- It proves orchestration semantics, cancellation, interruption, and event ordering without taking on browser/WebRTC UX.
- It gives future WebRTC, WebSocket, and telephony transports a stable runtime to call.
- Batch-only primitives would not address the user request for duplex systems.

**Expected Evidence**
- **Tests:** session state transitions, user speech start interrupts TTS, cancellation stops provider streams, provider failure marks session failed, and terminal state is visible.
- **Runtime Evidence:** diagnostics show active/failed/recent voice sessions and provider status.
- **Review Checks:** transport adapters remain thin and replaceable.

---

### Feature 6: Transport Extension Seams

**Description:** Define transport-facing contracts for audio ingress and egress without committing to one public browser or telephony product surface.

**Affected Areas**
- `backend/src/hello_sales_backend/platform/voice/transport.py`
- optional internal WebSocket/SSE route
- backend docs

**Requirement Mapping**

| Requirement ID | What It Requires Here | Constrained Code / Behavior | Planned Evidence |
| --- | --- | --- | --- |
| ARCH-ENTRY-001 | Routes stay thin | optional route | Integration tests |
| PRE-SCOPE-004 | Public surface remains narrow | route design | Review |
| FE-API-001 | Frontend API remains typed if touched | optional client | Frontend tests if added |
| ERR-HTTP-001 | Transport errors stay structured | route error mapping | Integration tests |

**Current-System Analysis**
- Existing `/agent-runs/{run_id}/events/stream` uses SSE for agent events.
- Duplex binary audio may need WebSocket or WebRTC later; Sprint 11 should not force SSE into a role it cannot play well.

**Options Considered**
- **Option A:** Build WebRTC now.
- **Option B:** Build WebSocket now.
- **Option C:** Define transport port and use fake/in-process transport for smokes, with optional internal WebSocket if cheap.

**Chosen Approach**
- Adopt Option C.

**Decision Justification**
- This keeps the sprint focused on reusable backend primitives.
- It leaves WebRTC as the right future browser path while allowing testable duplex behavior now.

**Expected Evidence**
- **Tests:** fake transport drives audio input and receives ordered audio output/events.
- **Runtime Evidence:** transport session id maps to voice session id, request id, trace id, actor id, and agent run id.
- **Review Checks:** no provider SDK or business policy appears in route files.

## Cross-Cutting Decisions

### Major Decision Summary

- **Model voice as frames/events:** Driven by observability, duplex, interruption, and testing requirements.
- **Separate provider ports:** STT, TTS, realtime voice, turn detection, and transport remain independently replaceable.
- **Ship chained pipeline first:** Chained `STT -> existing agent LLM -> TTS` best matches current HelloSales inspectability.
- **Keep realtime S2S as a port:** Realtime models are supported by the architecture without becoming the only implementation path.
- **Avoid raw-audio persistence by default:** Store metadata and bounded text artifacts unless a setting explicitly allows retention.
- **Prefer async runtime over workflow engine for per-frame audio:** Duplex has orchestration state, but frame processing needs latency-aware control.

### Trade-offs

- **Lower latency vs inspectability:** Direct speech-to-speech may be fastest, but chained voice gives clearer transcript, prompt, tool, and audio evidence. The design supports both, with chained MVP first.
- **Provider breadth vs delivery:** Sprint 11 should add one concrete provider path only if credentials and SDK complexity are manageable. The key deliverable is the seam.
- **Browser readiness vs backend foundation:** WebRTC is likely the future browser path, but implementing it before stable backend primitives increases risk.

### Assumptions

- Existing agent runtime remains the authoritative text reasoning and tool lifecycle layer.
- Voice providers are optional unless explicitly marked required in settings.
- The first voice docs and smokes may use fake providers if real credentials are unavailable.
- Audio payloads and transcripts are sensitive operational data.

### Dependencies

- Sprint 1 observability foundation for diagnostics, structured events, and correlation.
- Sprint 2 worker/runtime patterns for provider wiring and smoke discipline.
- Sprint 4 session substrate for conversation chronology.
- Sprint 6 web search provider pattern for provider-neutral external integrations.
- Sprint 8 auth context propagation for voice session permissions.

## Deviations

| Requirement ID | Deviation | Reason | Risk | Disposition | Follow-up |
| --- | --- | --- | --- | --- | --- |
| TEST-SMOKE-002 | Real provider smoke may be deferred | Voice credentials may not be present in this workspace | Provider adapter behavior may only be fake-tested locally | Temporary | Record exact missing credentials and add env-gated smoke. |
| PRE-SCOPE-004 | An internal voice route may be added for smoke/demo only | A stream route may be the simplest way to verify runtime behavior | Public surface could grow before product brief | Temporary | Keep route internal/operational and document scope. |
| LLM-PROMPT-001 | No voice prompt version is needed if using existing generic prompt unchanged | Voice may initially wrap existing agent behavior only | Later voice persona changes may slip into prompt text | Conditional | If any voice-specific prompt policy is added, add prompt id/version immediately. |

## Evidence Review Checklist

- [ ] Review can trace every voice primitive to a narrow provider or application boundary.
- [ ] Review can verify STT, TTS, realtime voice, and transport are independently replaceable.
- [ ] Review can verify voice provider settings and diagnostics are surfaced through the provider registry.
- [ ] Review can verify raw audio and sensitive transcripts are not logged by default.
- [ ] Review can verify voice sessions have explicit terminal state.
- [ ] Review can verify stream ordering, cancellation, and interruption behavior through deterministic tests.
- [ ] Review can verify real-provider smoke evidence or an explicit credentials-based deferral.

## Phase Exit Criteria

- [ ] Tracker scope is fully covered.
- [ ] Applicable requirements are mapped.
- [ ] Current external research is tied to design decisions.
- [ ] STT and TTS primitives are provider-neutral and fakeable.
- [ ] Streaming `LLM -> TTS` path is evented, ordered, and cancellable.
- [ ] Duplex session runtime has explicit lifecycle and interruption semantics.
- [ ] Diagnostics and readiness reflect voice provider state.
- [ ] Tests and smoke evidence are recorded in the tracker.

## Documentation Updates

- `backend/docs/voice-primitives.md`: New canonical guide for provider setup, contracts, runtime flows, diagnostics, and smokes.
- `backend/docs/configuration-and-environment.md`: Voice provider settings and required/optional readiness policy.
- `backend/docs/diagnostics-and-events.md`: Voice events, diagnostics fields, and failure codes.
- `backend/docs/testing-and-operations.md`: Voice smoke commands and real-provider deferral policy.
