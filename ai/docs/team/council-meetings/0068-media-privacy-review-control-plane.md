# Council 0068 - Media Privacy Review Control Plane

Date: 2026-06-17

## Attendees

- SA AI Platform
- SA AI Engineer
- PO/BA
- Governance Reviewer
- Admin/Ops

## Decision

Add a media privacy review control plane for raw document, image, audio and video processing. The platform now separates safe bounded baselines from raw-media activation:

- Transcript-only speech quality is approved for the current support baseline.
- Raw document OCR/layout remains waiting for retention, access, storage and layout-redaction controls.
- Raw audio ASR/diarization remains waiting for access, storage and speaker-role minimization controls.
- Speaker biometric processing remains blocked until explicit policy approval exists.

## Delivered

- Added `media-privacy-review-policy-v1` as policy-as-data.
- Added `media-privacy-review-requests.yaml` with transcript, document OCR/layout and audio ASR/diarization review requests.
- Added `media-privacy-review-v1` report builder and generated snapshot.
- Projected media privacy status into the operating cockpit and delivery backlog.
- Added CLI writer support through `--write-media-privacy-review-report`.

## PO/BA Translation

Product can now ask one concrete question: "Can this use case process raw media yet?"

Current answer:

- `support-speech-transcript-baseline-review`: yes, transcript-only baseline is approved.
- `finance-document-raw-ocr-review`: not yet, 4 controls are missing.
- `speech-audio-raw-asr-diarization-review`: not yet, 3 controls are missing.

## SA AI Platform Notes

- The report validates product, use case, taxonomy module, refs, status, media type and processing modes.
- Missing controls become cockpit/backlog actions rather than hidden architecture notes.
- This keeps CV/document and speech/audio P1 work actionable without weakening privacy gates.

## SA AI Engineer Notes

- Raw media adapters must link to this review before promotion.
- Future ASR, OCR/layout or diarization artifacts must pass both model eval gates and media privacy controls.
- Transcript-only and OCR-token baselines can continue as runtime libraries while raw media remains gated.

## Governance Notes

- Approved reviews require all required controls and evidence refs.
- Raw media modes add mode-specific control requirements on top of global controls.
- Blocked processing modes, including speaker biometrics, cannot be approved by artifact tests alone.

## Admin/Ops Notes

- Cockpit now shows `mediaPrivacyReviewStatus`.
- Delivery backlog now includes 2 `complete_media_privacy_controls` items.
- Owner views show the SA AI Platform + Governance queue as overloaded until raw-media controls are closed or rejected.

## Next Step

Attach missing raw-media control evidence for document OCR/layout and audio ASR/diarization, or explicitly reject the raw-media processing request and keep only bounded transcript/OCR-token baselines active.
