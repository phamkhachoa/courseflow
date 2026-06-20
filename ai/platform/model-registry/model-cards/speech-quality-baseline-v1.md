# Model Card: Speech Quality Baseline V1

## Identity

| Field | Value |
|---|---|
| Model ID | `speech-quality-baseline-v1` |
| Algorithm | deterministic transcript audio quality |
| Use case | `support-speech-quality-assurance` |
| Product | `support-platform` |
| Owner | `ai-platform` |
| Status | runtime library baseline |

## Intended Use

Classify bounded transcript segments into support intent, quality band,
compliance risk, evidence terms and human-review flags for speech/audio
governance workflows.

## Not Intended For

- Raw audio ingestion or ASR without privacy approval.
- Speaker biometric identification.
- Fully automated agent performance decisions.
- Extracting raw payment, identity or contact details.
- Cross-tenant audio or transcript matching.

## Inputs

| Input | Description |
|---|---|
| tenant ID | Tenant boundary |
| audio ID | Product audio or transcript identifier |
| audio checksum | Immutable source checksum |
| transcript language | Language tag |
| duration seconds | Bounded audio duration |
| consent captured | Notice/consent indicator |
| transcript segments | Redacted speaker-role, text and timing segments |

## Outputs

| Output | Description |
|---|---|
| intent | Support or learning intent |
| quality band | `good`, `low_confidence`, `escalation_review` or `long_call_review` |
| compliance risk | `low`, `raw_pii_detected`, `consent_missing` or `regulated_review` |
| summary terms | Bounded intent terms |
| evidence terms | Transcript snippets supporting decisions |
| reason codes | Transparent quality, intent and privacy signals |
| human-review flag | Required for raw PII, low quality, missing consent or escalations |

## Runtime Method

The runtime library uses deterministic transcript heuristics over redacted
segments. It detects common support and learning intents, quality escalation
signals, raw PII phrases and consent gaps.

This is a speech/audio runtime baseline over transcript metadata. It is not an
ASR, diarization, sentiment model or raw waveform model.

## Governance

- Tenant ID and audio checksum are required.
- Raw audio processing remains privacy gated.
- Raw PII is never emitted as a structured output field.
- Human review is required for low confidence, escalations, missing consent or
  raw PII.
- Future ASR or diarization variants must pass privacy review and golden evals
  before promotion.

## Known Limitations

- Rule-based transcript classification only.
- No raw audio, speaker diarization or acoustic quality signal.
- No multilingual calibration beyond language metadata.
- No production service integration yet.
- Golden dataset is small and contract-oriented.

## Monitoring

Track transcript confidence, review rate, raw-PII detection rate, escalation
override rate, intent drift, language mix, audio checksum coverage and reviewer
agreement before shadow or active promotion.
