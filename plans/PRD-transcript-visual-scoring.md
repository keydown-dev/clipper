# PRD — Transcript Quality and Visual-Aware Scoring

## Problem Statement

Clipper's current transcript and scoring artifacts are useful for basic audio-first clipping, but they are not yet readable or precise enough for higher-quality editorial workflows. faster-whisper segments do not reliably align to complete sentences, score results do not include the selected dialogue, and scoring cannot yet use visual evidence from the source video.

The user wants Clipper to preserve more accurate word-level transcript timing, derive readable sentence-level transcript artifacts, enrich score results with dialogue, detect significant visual shots, analyze representative frames with a vision-capable LLM endpoint, and support explicit transcript-only, visual-only, or combined scoring contexts.

## Solution

Improve the local-first pipeline in six steps:

- Enable faster-whisper word timestamps by default and persist word timing data in raw transcript segments.
- Automatically create a sentence-grouped transcript artifact during transcription.
- Enrich scored candidate clips with overlapping dialogue from the sentence transcript.
- Add PySceneDetect-based shot detection with representative frame extraction.
- Add optional visual frame analysis using an OpenAI-compatible multimodal chat endpoint.
- Update scoring so callers explicitly choose transcript context, visual context, or both.

The default transcription path remains faster-whisper on CPU with `int8` compute so the system remains VPS-friendly. More advanced transcription backends such as stable-ts are deferred.

## User Stories

1. As a user, I want word-level transcript timestamps, so that later processing can avoid guessing where words and sentences begin or end.
2. As a user, I want word timestamps enabled by default, so that every new transcript is suitable for sentence grouping and dialogue extraction.
3. As a user, I want raw transcript segments to preserve source timing, so that generated artifacts remain traceable to faster-whisper output.
4. As a user, I want a sentence-grouped transcript, so that I can read complete thoughts rather than arbitrary model segments.
5. As a user, I want sentence timestamps derived from word timestamps, so that sentence boundaries are accurate enough for clipping.
6. As a user, I want sentence artifacts created automatically during transcription, so that I do not need to remember a separate cleanup command.
7. As a user, I want scoring prompts to use sentence transcripts when transcript context is requested, so that the scorer evaluates coherent dialogue.
8. As a user, I want scored clips to include the selected dialogue, so that I can understand why a clip was chosen without opening the full transcript.
9. As a user, I want scored clips to include sentence timing details, so that dialogue remains auditable and traceable.
10. As a user, I want trailer shots detected automatically, so that I can inspect significant visual changes without sampling every frame.
11. As a user, I want one representative frame per detected shot, so that I can quickly review the visual content of a video.
12. As a user, I want the representative frame to be chosen for clarity, so that blurry transitional frames are avoided.
13. As a user, I want shot artifacts cached, so that later visual analysis and scoring can reuse them.
14. As a user, I want optional contact sheets, so that I can visually scan all detected shots.
15. As a user, I want representative frames analyzed by a vision-capable model, so that visual descriptions can be used during scoring.
16. As a user, I want visual analysis to use an OpenAI-compatible multimodal endpoint, so that I can use local Ollama models or compatible cloud models.
17. As a user, I want visual analysis output to be structured JSON, so that scoring can consume it reliably.
18. As a user, I want scoring to require explicit context flags, so that I know whether transcript, visuals, or both are being used.
19. As a user, I want scoring to fail when no context is selected, so that I do not accidentally ask the LLM to score without evidence.
20. As a user, I want transcript-only scoring, so that I can find sound bites from dialogue.
21. As a user, I want visual-only scoring, so that I can create silent visual montages.
22. As a user, I want combined transcript and visual scoring, so that I can find moments where dialogue and visual evidence reinforce each other.
23. As a user, I want visual scoring to use cached visual analysis, so that scoring remains reproducible and does not unexpectedly perform expensive model calls.
24. As a tester, I want word timestamp, sentence grouping, shot detection, visual analysis, and scoring-context behavior covered with mocked dependencies, so that default tests remain deterministic.
25. As a tester, I want real Whisper and LLM behavior to remain env-gated, so that model downloads and external calls do not happen accidentally.

## Implementation Decisions

- faster-whisper word timestamps are enabled by default for all new transcripts.
- New transcript segments include a `words` array with word text, start time, and end time.
- Generated transcripts must include word timestamps; if faster-whisper does not provide them, transcription fails clearly.
- Transcript schema validation may continue to tolerate older transcripts without `words` for compatibility, but sentence grouping requires word timestamps and should instruct users to rerun transcription with force when they are missing.
- `clipper transcribe` automatically writes both the raw transcript artifact and a sentence-grouped transcript artifact.
- Sentence artifacts contain sentence start time, end time, text, source segment references, and source word index ranges for traceability.
- Sentence boundaries are derived programmatically from word-level timing and punctuation rather than guessed from raw segment durations.
- Transcript scoring uses the sentence transcript rather than raw faster-whisper segments once sentence artifacts are available.
- Score results embed overlapping sentence objects and a joined dialogue string for each scored candidate segment.
- PySceneDetect is the basis for shot detection.
- Shot detection writes a shot manifest and representative frame images by default; contact sheet generation is optional.
- Representative frames are selected with deterministic programmatic quality metrics such as sharpness, exposure, and contrast.
- Visual frame analysis is a separate cached phase that consumes representative shot frames.
- Visual frame analysis targets an OpenAI-compatible multimodal chat endpoint, defaulting naturally to local Ollama-compatible configuration but allowing compatible cloud endpoints.
- Visual frame analysis writes structured JSON observations for each analyzed frame.
- Reference-image/person matching is deferred.
- Scoring context is explicit. Callers must provide `--with-transcript`, `--with-visuals`, or both.
- `--with-visuals` depends on cached shot and visual index artifacts.
- Scoring fails clearly if requested context artifacts are missing.
- Scoring fails clearly if no scoring context is selected.
- Directive expansion, auto-context selection, and tool-based agentic context retrieval are deferred.

## Testing Decisions

- Test public command behavior and artifact contracts rather than private implementation details.
- Mock faster-whisper output with word timestamps in default transcription tests.
- Test that transcription fails when word timestamps are missing from generated output.
- Test sentence grouping with punctuation, multi-segment sentences, and traceability references.
- Test scoring dialogue enrichment from sentence artifacts without calling a real LLM.
- Test shot detection behavior with mocked or deterministic small video inputs and avoid committing binary fixtures.
- Test representative frame selection through deterministic image quality fixtures or generated frames.
- Mock OpenAI-compatible vision responses in default visual analysis tests.
- Keep real Whisper tests gated behind `CLIPPER_RUN_WHISPER_TESTS=1`.
- Keep real LLM or vision-model tests gated behind explicit environment variables.

## Out of Scope

- stable-ts or WhisperX transcription backends.
- Speaker diarization.
- Reference-image or person identity matching.
- Agentic scoring where the LLM calls tools to fetch context artifacts.
- Automatic directive expansion or context selection.
- Manual clip trim/crop UI.
- Cut handles around matched moments.
- Audio fade-in/fade-out controls.
- Web UI or rich terminal UI.
- Guaranteed compatibility with every OpenAI-compatible provider's multimodal API quirks.

## Further Notes

Future work should revisit stable-ts as an optional higher-resource transcription backend, reference-image/person matching for visual search, directive expansion for casual user requests, tool-based context retrieval during scoring, and clip editing workflows where scorer-selected matched ranges are preserved separately from padded/manual cut ranges.
