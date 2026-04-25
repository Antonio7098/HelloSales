# Sprint Tracker: Voice Primitives

> Project: HelloSales
> Sprint ID: sprint-11-voice-primitives
> Created: 2026-04-24

## Sprint Overview

- **Sprint Name:** Voice Primitives
- **Sprint Focus:** Add provider-neutral voice runtime primitives for STT, TTS, streaming `LLM -> TTS`, and duplex session control.
- **Depends On:** `ops/sprints/sprint-01-observability-foundation/tracker.md`, `ops/sprints/sprint-02-worker-runtime-foundation/tracker.md`, `ops/sprints/sprint-04-session-substrate-foundation/tracker.md`, `ops/sprints/sprint-06-web-search-capabilities/tracker.md`, `ops/sprints/sprint-08-workos-auth-foundation/tracker.md`
- **Status:** Completed

## Sprint Goals

- **Primary Goal:** Ship modular, provider-neutral voice primitives that can be composed into batch STT, batch/streaming TTS, streaming `LLM -> TTS`, and duplex voice sessions without provider lock-in.
- **Secondary Goals:**
  - Add explicit STT, TTS, realtime voice, turn detection, and transport seams.
  - Reuse the existing agent runtime for text reasoning, tool lifecycle, prompt versioning, auth context, and observability.
  - Keep provider setup, diagnostics, failure mapping, and readiness aligned with the existing provider registry pattern.
  - Add deterministic fake-provider coverage plus real-provider smoke evidence or explicit deferral.
  - Document future WebRTC, WebSocket, SIP, and speech-to-speech extension paths without implementing a product-specific voice flow.

## Execution Checklist

- [x] **Task 1: Create provider-neutral voice substrate**
  > *Description: Add platform-level contracts and provider wiring for audio frames, transcript events, speech chunks, realtime voice sessions, and provider status.*
  - [x] **Sub-task 1.1:** Add `platform/voice/` contracts for audio input, audio chunks, transcript events, speech synthesis requests, voice events, and provider contexts.
  - [x] **Sub-task 1.2:** Define separate `STTProviderPort`, `TTSProviderPort`, `RealtimeVoiceProviderPort`, `TurnDetectionPort`, and `VoiceTransportPort` contracts.
  - [x] **Sub-task 1.3:** Add no-op/fake provider implementations for local development and deterministic tests.
  - [x] **Sub-task 1.4:** Extend settings, provider registry, close lifecycle, diagnostics, and readiness/degraded reporting for voice providers.

- [x] **Task 2: Add the voice application primitive module**
  > *Description: Introduce module-owned voice services that expose stable commands and views while depending only on provider ports.*
  - [x] **Sub-task 2.1:** Add `modules/voice/` bootstrap, service facade, commands, views, and use-case ports.
  - [x] **Sub-task 2.2:** Implement audio/text validation, format constraints, voice selection normalization, and provider disabled behavior.
  - [x] **Sub-task 2.3:** Preserve request, trace, actor, org, permission, session, and agent-run metadata through voice contexts.
  - [x] **Sub-task 2.4:** Keep raw audio persistence disabled by default and document any metadata/transcript retention.

- [x] **Task 3: Implement STT primitive**
  > *Description: Add a reusable speech-to-text service path that supports final transcripts now and streaming transcript events as the contract requires.*
  - [x] **Sub-task 3.1:** Implement `VoiceService.transcribe()` with fake provider coverage.
  - [x] **Sub-task 3.2:** Model interim/final transcript events, confidence, language, speaker metadata where available, and provider metadata.
  - [x] **Sub-task 3.3:** Normalize provider errors for invalid audio, unsupported format, timeout, rate limit, auth failure, remote failure, and malformed response.
  - [x] **Sub-task 3.4:** Add an env-gated real STT provider smoke or record explicit credential/setup deferral.

- [x] **Task 4: Implement TTS primitive**
  > *Description: Add reusable text-to-speech synthesis for complete audio and streaming audio chunks.*
  - [x] **Sub-task 4.1:** Implement `VoiceService.synthesize()` with fake provider coverage.
  - [x] **Sub-task 4.2:** Support configured voice, model, output format, sample rate, and streaming chunk metadata through provider-neutral fields.
  - [x] **Sub-task 4.3:** Normalize TTS provider failures and cancellation with stable `voice.tts.*` error codes.
  - [x] **Sub-task 4.4:** Add an env-gated real TTS provider smoke or record explicit credential/setup deferral.

- [x] **Task 5: Build streaming `LLM -> TTS` bridge**
  > *Description: Convert existing LLM text deltas into buffered text segments and ordered TTS audio events without forking the agent runtime.*
  - [x] **Sub-task 5.1:** Add a text segmenter with punctuation, max-character, max-delay, and explicit flush behavior.
  - [x] **Sub-task 5.2:** Add a voice stream sink or bridge that consumes agent text deltas and emits `voice.text.segment` and `voice.audio.delta` events.
  - [x] **Sub-task 5.3:** Handle partial audio, TTS failure after streaming starts, cancellation, final flush, and backpressure explicitly.
  - [x] **Sub-task 5.4:** Add deterministic tests for segment ordering, chunk ordering, finalization, cancellation, and failure state.

- [x] **Task 6: Add duplex voice session runtime**
  > *Description: Coordinate audio input, STT, turn detection, agent execution, TTS output, interruption, cancellation, and terminal state.*
  - [x] **Sub-task 6.1:** Add voice session lifecycle states such as pending, listening, transcribing, thinking, speaking, interrupted, completed, failed, and cancelled.
  - [x] **Sub-task 6.2:** Implement fake/in-process transport support for deterministic duplex tests.
  - [x] **Sub-task 6.3:** Implement interruption/barge-in semantics where user speech can stop active TTS and mark the prior output interrupted.
  - [x] **Sub-task 6.4:** Ensure all stream tasks are owned, cancellable, correlated, and visible through diagnostics.

- [x] **Task 7: Add optional internal transport surface**
  > *Description: Provide the narrowest route or harness needed to verify voice primitives without committing to a product UI.*
  - [x] **Sub-task 7.1:** Prefer an in-process smoke harness; add an internal WebSocket/SSE route only if needed for meaningful verification.
  - [x] **Sub-task 7.2:** Keep any route thin: auth, validation, service delegation, structured error mapping, and no provider SDK access.
  - [x] **Sub-task 7.3:** Document why WebRTC and SIP are future transport adapters rather than Sprint 11 deliverables.

- [x] **Task 8: Preserve operational visibility and privacy**
  > *Description: Make voice provider state, session lifecycle, stream failures, and sensitive-data handling inspectable and reviewable.*
  - [x] **Sub-task 8.1:** Add stable error codes for STT, TTS, realtime, transport, turn detection, interruption, and cancellation failures.
  - [x] **Sub-task 8.2:** Extend diagnostics with configured voice providers, degraded/required state, active session count, and recent terminal failures.
  - [x] **Sub-task 8.3:** Emit canonical observability events for session start, transcript final, LLM segment, TTS first chunk, interruption, cancellation, completion, and failure.
  - [x] **Sub-task 8.4:** Redact API keys, provider tokens, raw audio, and sensitive transcript data from logs and error details.

- [x] **Task 9: Add tests, smokes, and docs**
  > *Description: Finish the sprint with deterministic coverage, centralized smoke scenarios, and canonical documentation.*
  - [x] **Sub-task 9.1:** Add unit tests for contracts, validation, segmenter behavior, fake providers, session state transitions, and failure mapping.
  - [x] **Sub-task 9.2:** Add integration tests for provider registry, diagnostics, optional transport surface, and agent `LLM -> TTS` bridge.
  - [x] **Sub-task 9.3:** Add centralized smoke scenarios for STT, TTS, streaming `LLM -> TTS`, and fake duplex session flow.
  - [x] **Sub-task 9.4:** Run real-provider smokes where credentials exist or record explicit deferrals.
  - [x] **Sub-task 9.5:** Add `backend/docs/voice-primitives.md` and update configuration, diagnostics, and testing docs.

## Testing And Documentation Checklist

- [x] **Unit Tests:** deterministic coverage for provider contracts, validation, chunking/segmenting, fake providers, error mapping, cancellation, and voice session state.
- [x] **Integration Tests:** provider registry, diagnostics, optional transport route, agent bridge, and event ordering for the sprint scope.
- [x] **Smoke Tests:** centralized STT, TTS, streaming `LLM -> TTS`, and fake duplex runtime smoke scenarios.
- [x] **Real Provider Smoke:** run at least one supported real-provider STT/TTS smoke, or record explicit credentials/setup deferral.
- [x] **Documentation Updates:** add canonical voice primitives docs and update provider configuration, diagnostics/events, and testing operations docs.

## Risks And Blockers

| Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- |
| Voice provider abstractions become a broad god interface | High | Keep STT, TTS, realtime, transport, and turn detection as separate ports | Mitigated |
| Realtime speech-to-speech bypasses existing agent/tool/prompt lifecycle | High | Ship chained `STT -> LLM -> TTS` first and model S2S as a separate port | Mitigated |
| TTS starts before enough text exists and produces poor audio or stalls | Medium | Add configurable text segmentation and flush policy | Mitigated |
| Raw audio or sensitive transcripts leak into logs or diagnostics | High | Redact by default and avoid raw-audio persistence unless explicitly configured | Mitigated |
| Duplex stream tasks fail silently or leak on disconnect | High | Own tasks through voice session state and test cancellation/terminal outcomes | Mitigated |
| Real-provider smoke cannot run due missing credentials | Medium | Add env-gated smokes and record exact deferral evidence | Deferred: no real voice adapter/credentials selected |
| WebRTC scope expands into a product UI before backend primitives stabilize | Medium | Keep Sprint 11 transport internal or fake unless tracker is revised | Mitigated |

## Success Criteria

- [x] **Success Criteria 1:** Voice provider contracts are modular, provider-neutral, fakeable, and wired through the existing provider registry pattern.
- [x] **Success Criteria 2:** `modules/voice/` exposes reusable STT and TTS primitives with stable commands/views and no provider SDK leakage.
- [x] **Success Criteria 3:** Existing agent LLM streaming can feed TTS through an ordered, cancellable, evented bridge.
- [x] **Success Criteria 4:** Duplex voice session runtime handles listening, turn detection, speaking, interruption, cancellation, failure, and terminal state explicitly.
- [x] **Success Criteria 5:** Diagnostics, structured errors, redaction, tests, smokes, and docs are review-ready.

## Review And Sign-Off

- Sprint Status: Completed
- Completion Date: 2026-04-24

## Execution Evidence

- Sprint artifacts created from:
  - `ops/process/reasoning/reasoning-protocol.md`
  - `ops/process/reasoning/reasoning-template.md`
  - `ops/process/execute/tracker-template.md`
- Online research completed on 2026-04-24 and refreshed during execution; summarized in `reasoning.md`.
- Implementation branch: current working tree.
- Verification commands:
  - `PYTHONPATH=src python -m pytest tests/unit/test_voice_primitives.py tests/integration/test_voice_provider_registry.py -q` -> 8 passed.
  - `PYTHONPATH=src python -m ruff check src tests/unit/test_voice_primitives.py tests/integration/test_voice_provider_registry.py` -> passed.
  - `PYTHONPATH=src python -m mypy src` -> passed.
  - `env HELLO_SALES_AUTH_PROVIDER= PYTHONPATH=src python -m pytest -q` -> 133 passed, 8 skipped.
  - `env HELLO_SALES_DATABASE_URL=sqlite+aiosqlite:////tmp/hello-sales-voice-stt.db HELLO_SALES_AUTH_PROVIDER= PYTHONPATH=src python -m hello_sales_backend.smoke voice-stt` -> completed.
  - `env HELLO_SALES_DATABASE_URL=sqlite+aiosqlite:////tmp/hello-sales-voice-tts.db HELLO_SALES_AUTH_PROVIDER= PYTHONPATH=src python -m hello_sales_backend.smoke voice-tts` -> completed.
  - `env HELLO_SALES_DATABASE_URL=sqlite+aiosqlite:////tmp/hello-sales-voice-bridge.db HELLO_SALES_AUTH_PROVIDER= PYTHONPATH=src python -m hello_sales_backend.smoke voice-llm-to-tts` -> completed.
  - `env HELLO_SALES_DATABASE_URL=sqlite+aiosqlite:////tmp/hello-sales-voice-duplex.db HELLO_SALES_AUTH_PROVIDER= PYTHONPATH=src python -m hello_sales_backend.smoke voice-duplex` -> completed.
- Real-provider smoke evidence or deferrals: deferred because Sprint 11 ships fake provider seams only; no real STT/TTS adapter and no committed voice credentials exist in this workspace.
