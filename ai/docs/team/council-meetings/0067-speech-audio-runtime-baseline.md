# Council 0067 - Speech Audio Runtime Baseline

Date: 2026-06-17

## Attendees

- SA AI Platform
- SA AI Engineer
- PO/BA
- Governance Reviewer
- Admin/Ops

## Decision

Add `speech-quality-baseline-v1` as the first speech/audio runtime-library baseline for the Enterprise AI Platform. The baseline accepts bounded transcript segments only, rejects raw audio URIs, detects raw PII transcript signals, and forces human review for low-quality, escalation or privacy-risk calls.

Raw audio ingestion, ASR, diarization and speaker-biometric processing remain privacy-gated until a separate media processing review is approved.

## Delivered

- Added a deterministic transcript-segment speech quality model under `models/speech/audio_quality_baseline`.
- Added feature and model IO contracts for speech quality input/output.
- Added model card, artifact manifest and golden evaluation report.
- Added `speech-quality-golden` to the executable evaluation registry.
- Updated AI coverage and taxonomy so `speech-audio-ai` is now `runtime_library`, not `registry_only`.
- Kept LMS coverage through the `lms-video-transcript-summary` path and non-LMS coverage through `support-speech-quality-assurance`.

## PO/BA Translation

The platform can now answer "do we have speech/audio AI?" with a qualified yes:

- Yes for transcript-based speech quality, learning-support transcripts and support QA triage.
- Not yet for raw audio ASR, diarization, voice biometrics or media storage.
- Human review is required when transcript quality, escalation or PII risk is detected.

## SA AI Platform Notes

- The module remains product-neutral enough for LMS and support workflows.
- The model card and manifest make the baseline visible to registry, evidence and operating reports.
- The runtime roadmap still keeps `speech-audio-ai` as P1 because raw media processing is intentionally blocked.

## SA AI Engineer Notes

- The baseline is deterministic and suitable for golden regression tests.
- The evaluation runner checks intent, quality band, reason-code recall, evidence-term recall, human-review policy and privacy guardrail pass rate.
- A future ASR adapter must publish a governed audio snapshot contract before service integration.

## Governance Notes

- `raw_audio_uri` is rejected by the runtime library.
- Raw PII transcript signals produce `RAW_AUDIO_PII_DETECTED` and require human review.
- The output omits raw PII as structured fields and keeps evidence bounded to transcript snippets.

## Admin/Ops Notes

- Required evaluation count increases because speech now has an executable quality gate.
- Artifact evidence count increases because speech now has a source manifest.
- The cockpit should still show attention required until raw audio privacy review and service integration are approved.

## Next Step

Complete audio privacy review, then decide whether the next slice should be ASR adapter, diarization adapter or a hosted speech-quality service boundary.
