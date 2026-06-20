from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.media_intelligence_service import (
    MEDIA_DOCUMENT_ANALYZE_SCOPE,
    MEDIA_SPEECH_ASSESS_SCOPE,
    MediaIntelligenceRuntime,
    MediaIntelligenceServiceError,
    MediaPrivacyControlError,
    load_media_intelligence_access_policy,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def finance_document_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-finance",
        "product": "billing-finance",
        "useCaseId": "finance-document-intelligence",
        "documentId": "invoice-1001",
        "documentChecksum": "sha256-doc-1001",
        "mimeType": "application/pdf",
        "documentLanguage": "en",
        "vendorNameHint": "Acme Learning",
        "tokens": [
            {"text": "Invoice", "page": 1, "bbox": [0.1, 0.1, 0.2, 0.2]},
            {"text": "INV-1001", "page": 1, "bbox": [0.2, 0.1, 0.3, 0.2]},
            {"text": "Total USD 1200.00", "page": 1, "bbox": [0.1, 0.3, 0.4, 0.4]},
            {"text": "Due 2026-06-30", "page": 1, "bbox": [0.1, 0.5, 0.4, 0.6]},
        ],
    }


def support_speech_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-support",
        "product": "support-platform",
        "useCaseId": "support-speech-quality-assurance",
        "audioId": "call-2001",
        "audioChecksum": "sha256-audio-2001",
        "transcriptLanguage": "en",
        "durationSeconds": 320,
        "consentCaptured": True,
        "segments": [
            {
                "speaker_role": "customer",
                "text": "I need help with a billing refund.",
                "start_ms": 0,
                "end_ms": 4200,
                "confidence": 0.96,
            },
            {
                "speaker_role": "agent",
                "text": "I can review the invoice and payment details.",
                "start_ms": 4200,
                "end_ms": 8600,
                "confidence": 0.95,
            },
        ],
    }


def test_media_intelligence_runtime_serves_document_under_policy_and_privacy_controls() -> None:
    root = ai_root()
    policy = load_media_intelligence_access_policy(root)
    principal = policy.resolve_principal(
        "service:billing-finance-media",
        (MEDIA_DOCUMENT_ANALYZE_SCOPE,),
    )
    runtime = MediaIntelligenceRuntime(root)

    response = runtime.analyze_document(finance_document_body(), principal).to_dict()

    assert response["modelId"] == "finance-document-intelligence-baseline-v1"
    assert response["tenantId"] == "tenant-finance"
    assert response["documentType"] == "invoice"
    assert response["extractedFields"]["document_number"] == "1001"
    assert response["requiresHumanReview"] is False
    assert runtime.health()["mediaPrivacy"]["reviewStatus"] == "approved"
    assert runtime.snapshot_metrics().document_analyze_count == 1


def test_media_intelligence_runtime_serves_speech_under_policy_and_tracks_metrics() -> None:
    root = ai_root()
    policy = load_media_intelligence_access_policy(root)
    principal = policy.resolve_principal(
        "service:support-platform-media",
        (MEDIA_SPEECH_ASSESS_SCOPE,),
    )
    runtime = MediaIntelligenceRuntime(root)

    response = runtime.assess_speech(support_speech_body(), principal).to_dict()
    metrics = runtime.snapshot_metrics()

    assert response["modelId"] == "speech-quality-baseline-v1"
    assert response["intent"] == "billing_support"
    assert response["qualityBand"] == "good"
    assert response["complianceRisk"] == "low"
    assert metrics.speech_assess_count == 1
    assert metrics.by_product == {"support-platform": 1}


def test_media_intelligence_policy_rejects_cross_product_and_raw_uris() -> None:
    root = ai_root()
    policy = load_media_intelligence_access_policy(root)
    principal = policy.resolve_principal(
        "service:support-platform-media",
        (MEDIA_SPEECH_ASSESS_SCOPE,),
    )
    runtime = MediaIntelligenceRuntime(root)

    with pytest.raises(MediaIntelligenceServiceError, match="product is not granted"):
        runtime.assess_speech(
            {
                **support_speech_body(),
                "product": "lms-courseflow",
            },
            principal,
        )

    with pytest.raises(MediaPrivacyControlError, match="raw media URI"):
        runtime.assess_speech(
            {
                **support_speech_body(),
                "rawAudioUri": "s3://raw-audio/call-2001.wav",
            },
            principal,
        )
    assert runtime.snapshot_metrics().privacy_control_violation_count == 1


def test_media_intelligence_policy_exposes_lms_document_and_speech_scopes() -> None:
    policy = load_media_intelligence_access_policy(ai_root())
    principal = policy.resolve_principal(
        "service:lms-courseflow-media",
        (MEDIA_DOCUMENT_ANALYZE_SCOPE, MEDIA_SPEECH_ASSESS_SCOPE),
    )

    assert principal.tenant_ids == ("tenant-lms",)
    assert principal.product_ids == ("lms-courseflow",)
    assert set(principal.use_case_ids) == {
        "lms-document-vision-ingestion",
        "lms-video-transcript-summary",
    }
