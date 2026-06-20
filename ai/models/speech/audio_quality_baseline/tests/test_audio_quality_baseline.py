from __future__ import annotations

import pytest
from ai.models.speech.audio_quality_baseline.audio_quality_baseline import (
    AudioQualityBaseline,
)


def test_audio_quality_baseline_detects_account_access_quality() -> None:
    model = AudioQualityBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-support",
            "audio_id": "call-1001",
            "audio_checksum": "sha256-call-1001",
            "transcript_language": "en",
            "duration_seconds": 420,
            "consent_captured": True,
            "segments": [
                {
                    "speaker_role": "customer",
                    "text": "I cannot login after the MFA reset",
                    "start_ms": 0,
                    "end_ms": 4000,
                    "confidence": 0.96,
                },
                {
                    "speaker_role": "agent",
                    "text": "We reset the account password and confirmed login",
                    "start_ms": 4200,
                    "end_ms": 9000,
                    "confidence": 0.98,
                },
            ],
        }
    )

    assert prediction.model_id == "speech-quality-baseline-v1"
    assert prediction.intent == "account_access"
    assert prediction.quality_band == "good"
    assert prediction.compliance_risk == "low"
    assert prediction.requires_human_review is False
    assert "INTENT_ACCOUNT_ACCESS" in prediction.reason_codes


def test_audio_quality_baseline_routes_escalations_to_review() -> None:
    model = AudioQualityBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-support",
            "audio_id": "call-refund",
            "audio_checksum": "sha256-call-refund",
            "transcript_language": "en",
            "duration_seconds": 760,
            "consent_captured": True,
            "segments": [
                {
                    "speaker_role": "customer",
                    "text": "I am angry about the refund and want a manager",
                    "start_ms": 0,
                    "end_ms": 5000,
                    "confidence": 0.91,
                },
                {
                    "speaker_role": "agent",
                    "text": "I can escalate the billing refund complaint",
                    "start_ms": 5200,
                    "end_ms": 10000,
                    "confidence": 0.92,
                },
            ],
        }
    )

    assert prediction.intent == "billing_support"
    assert prediction.quality_band == "escalation_review"
    assert prediction.requires_human_review is True
    assert "QUALITY_REVIEW_REQUIRED" in prediction.reason_codes


def test_audio_quality_baseline_detects_raw_pii() -> None:
    model = AudioQualityBaseline()

    prediction = model.predict(
        {
            "tenant_id": "tenant-support",
            "audio_id": "call-pii",
            "audio_checksum": "sha256-call-pii",
            "transcript_language": "en",
            "duration_seconds": 300,
            "consent_captured": True,
            "segments": [
                {
                    "speaker_role": "customer",
                    "text": "My credit card is 4111 1111 1111 1111",
                    "start_ms": 0,
                    "end_ms": 4000,
                    "confidence": 0.95,
                }
            ],
        }
    )

    assert prediction.compliance_risk == "raw_pii_detected"
    assert prediction.requires_human_review is True
    assert "RAW_AUDIO_PII_DETECTED" in prediction.reason_codes


def test_audio_quality_baseline_rejects_raw_audio_uri() -> None:
    model = AudioQualityBaseline()

    with pytest.raises(ValueError, match="raw_audio_uri"):
        model.predict(
            {
                "tenant_id": "tenant-support",
                "audio_id": "call-raw",
                "audio_checksum": "sha256-call-raw",
                "transcript_language": "en",
                "duration_seconds": 60,
                "consent_captured": True,
                "raw_audio_uri": "s3://bucket/raw.wav",
                "segments": [
                    {
                        "speaker_role": "customer",
                        "text": "Need help",
                        "start_ms": 0,
                        "end_ms": 1000,
                    }
                ],
            }
        )
