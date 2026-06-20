# Council 0069 - Raw Media Control Evidence Approval

Date: 2026-06-17

## Attendees

- SA AI Platform
- SA AI Engineer
- PO/BA
- Governance Reviewer
- Data Platform
- Admin/Ops

## Decision

Approve raw-media control evidence for finance document OCR/layout and support
audio ASR/diarization at the platform governance layer. Approval means the use
cases can proceed to solution design or promotion review under the attached
controls; it does not grant speaker biometric processing.

## Approved Controls

- `raw-media-storage-boundary-v1` defines tenant-scoped storage, audit,
  retention and deletion/export impact obligations for raw media.
- `finance-document-raw-ocr-layout-controls-v1` defines source document access,
  deletion/export impact and layout redaction controls.
- `speech-audio-raw-asr-diarization-controls-v1` defines raw audio access,
  transcript redaction and speaker-role minimization controls.

## Guardrails

- Raw media URIs stay out of model payloads.
- Derived outputs must be redacted before model output or downstream feature
  materialization.
- Speaker biometric processing remains blocked.
- Human review remains required for financial adjustments, complaint
  escalations and low-confidence extraction.

## Follow-Up

SA AI Platform can now move CV/document AI and speech/audio AI from privacy
blocked P1 work to service-integration P2 work, while promotion review still
checks model, evaluation and media privacy evidence.
