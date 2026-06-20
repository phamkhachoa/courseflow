# Media Intelligence Service

Policy-enforced service package for bounded document intelligence and transcript
speech assessment. It is shared by the Enterprise AI Platform and can be reused by
LMS, Finance and Support products without turning media AI into an LMS-only
feature.

## Routes

| Route | Scope | Purpose |
|---|---|---|
| `POST /v1/media-intelligence/document:analyze` | `internal:ai-platform:media-intelligence:document:analyze` | Run the finance/document baseline over bounded OCR tokens. |
| `POST /v1/media-intelligence/speech:assess` | `internal:ai-platform:media-intelligence:speech:assess` | Run the speech quality baseline over transcript segments. |
| `GET /v1/media-intelligence/health` | `internal:ai-platform:media-intelligence:ops` | Report model and media privacy control readiness. |
| `GET /v1/media-intelligence/metrics` | `internal:ai-platform:media-intelligence:ops` | Report tenant-safe request, error, HITL and privacy counters. |

## Boundary

The current service routes do not accept raw document or raw audio URIs. Raw
OCR/layout and ASR/diarization controls are approved, but these baseline serving
routes consume only bounded OCR tokens and transcript segments. Raw-media adapters
can be added behind the same access policy after they have their own service
contract, retention path and evidence tests.

## Local Commands

```bash
make test
make lint
make manifest
make health
```
