# 0070 - Media Intelligence Service Package

Date: 2026-06-17
Owner: AI Platform Council

## Decision

Create `services/media-intelligence-service` as the shared AI Platform service
boundary for bounded document intelligence and speech transcript assessment.

The service is not LMS-specific. It serves:

- LMS CourseFlow document ingestion and video transcript summary workflows.
- Billing/Finance document intelligence workflows.
- Support Platform speech quality assurance workflows.

## Accepted Scope

- Serve bounded OCR-token document intelligence through
  `POST /v1/media-intelligence/document:analyze`.
- Serve transcript-segment speech quality assessment through
  `POST /v1/media-intelligence/speech:assess`.
- Enforce product, use-case and tenant grants from
  `platform/governance/policies/media-intelligence-access-policy.yaml`.
- Reject raw document, image, audio and storage URI submission on bounded routes.
- Expose health and tenant-safe metrics for document, speech, error, HITL and
  privacy-control counters.

## Deliberate Non-Scope

- Raw OCR/layout ingestion routes are not implemented yet.
- Raw ASR and diarization routes are not implemented yet.
- Production-ready storage, redaction runtime and release SLO evidence remain
  separate promotion requirements.

## Evidence

- Service package: `services/media-intelligence-service/service.yaml`
- Platform runtime: `platform/src/courseflow_ai_platform/media_intelligence_service.py`
- Access policy: `platform/governance/policies/media-intelligence-access-policy.yaml`
- Service tests: `services/media-intelligence-service/tests/test_service_contract.py`
- Platform tests: `platform/tests/test_media_intelligence_service.py`
- Media controls: `platform/governance/reports/media-privacy-review-v1.yaml`

## Acceptance Criteria

- CV/document and speech/audio modules move from runtime library to
  service-integrated baseline.
- LMS, Finance and Support use cases reference the same platform service.
- Raw-media adapter gaps remain explicit and cannot be confused with
  production-ready serving.
