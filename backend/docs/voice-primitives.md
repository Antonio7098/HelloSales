# Voice Primitives

## Purpose
Sprint 11 adds provider-neutral backend voice primitives:
- speech-to-text through `STTProviderPort`
- text-to-speech through `TTSProviderPort`
- streaming `LLM -> TTS` segmentation and ordered audio events
- a fake in-process duplex session runtime for interruption, cancellation, and terminal-state testing
- realtime speech-to-speech, turn-detection, and transport seams for future adapters

The sprint intentionally does not add a product call flow, browser voice UI, telephony routing, or sales-specific voice persona.

## Architecture
Voice contracts live in `platform/voice/` and stay domain-neutral.

The platform layer defines:
- `AudioInput`, `TranscriptEvent`, `SpeechChunk`, and `VoiceEvent`
- `STTProviderPort`, `TTSProviderPort`, `RealtimeVoiceProviderPort`, `TurnDetectionPort`, and `VoiceTransportPort`
- stable lifecycle states such as `listening`, `transcribing`, `thinking`, `speaking`, `interrupted`, `completed`, `failed`, and `cancelled`

The application-owned facade lives in `modules/voice/`.
It exposes:
- `VoiceService.transcribe()`
- `VoiceService.synthesize()`
- `VoiceService.stream_text_to_speech()`
- `VoiceService.run_fake_duplex()`

Provider SDKs must stay behind provider ports. Routes, smokes, future jobs, and future WebSocket/WebRTC/SIP adapters should call the voice module facade, not provider clients.

## Current Providers
The implemented provider path is deterministic fake-only:
- `fake-stt`
- `fake-tts`
- `fake-realtime-voice`
- `fake-turn-detection`

Empty provider settings resolve to disabled providers. Set provider names to `fake` for local smoke execution.

Real-provider STT/TTS adapters are deferred because no voice provider credentials or SDK selection are committed in this workspace.

## Streaming Bridge
The streaming bridge buffers text deltas before TTS.

Flush behavior:
- punctuation terminators flush immediately
- `max_segment_chars` flushes long partial text
- `max_delay_ms` can flush stale partial text
- final completion explicitly flushes remaining buffered text

The bridge emits ordered events:
- `voice.text.segment`
- `voice.audio.delta`
- `voice.audio.completed`
- `voice.session.failed`
- `voice.session.cancelled`

This keeps TTS chunk ordering explicit and avoids token-by-token synthesis, which is a poor default for quality and provider latency.

## Duplex Runtime
The current duplex runtime is an in-process harness.

It coordinates:
- audio input
- STT final transcript generation
- turn detection
- response text streaming to TTS
- barge-in interruption state
- cancellation and terminal state

The runtime owns task cancellation hooks and reports active task count in the returned session view. Future transports should adapt audio ingress/egress into `VoiceTransportPort` without changing STT/TTS contracts.

## Privacy
Raw audio persistence is disabled by default.

Default behavior:
- raw audio bytes are passed to providers but not logged
- errors mark raw audio as redacted
- diagnostics expose provider/session metadata, not audio payloads
- transcript and text payload handling remains bounded to service results and operational events used in deterministic tests

If product requirements later require retention, add explicit settings, retention docs, and redaction tests before persisting raw audio or full transcripts.

## Future Transport Adapters
Current guidance supports keeping transports separate:
- Browser realtime voice should prefer WebRTC when implemented.
- Server-side realtime and telephony/SIP flows can use WebSocket/SIP adapters.
- Provider-native speech-to-speech should stay behind `RealtimeVoiceProviderPort`.
- Chained `STT -> LLM -> TTS` remains useful when HelloSales needs transcript, tool, prompt, and event inspectability.

Sprint 11 ships the backend seams and fake runtime only.

## Smokes
Run from `backend/`:
- `python -m hello_sales_backend.smoke voice-stt`
- `python -m hello_sales_backend.smoke voice-tts`
- `python -m hello_sales_backend.smoke voice-llm-to-tts`
- `python -m hello_sales_backend.smoke voice-duplex`

These smokes force fake providers in their local app instance so they do not require external voice credentials.
