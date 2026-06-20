from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_media_intelligence_service.cli import main
from courseflow_media_intelligence_service.service import (
    MEDIA_INTELLIGENCE_SERVICE_ID,
    MediaIntelligenceService,
    MediaIntelligenceServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


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


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "media-intelligence-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "media-intelligence-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == MEDIA_INTELLIGENCE_SERVICE_ID
    assert service_yaml["service_id"] == MEDIA_INTELLIGENCE_SERVICE_ID
    assert len(manifest["routes"]) == 4
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_allows_finance_document_analysis_and_tracks_metrics() -> None:
    service = MediaIntelligenceService(MediaIntelligenceServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/media-intelligence/document:analyze",
        finance_document_body(),
        principal_id="service:billing-finance-media",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/media-intelligence/metrics",
        principal_id="service:ai-platform-media-ops",
    )

    assert response.status_code == 200
    assert response.body["modelId"] == "finance-document-intelligence-baseline-v1"
    assert response.body["tenantId"] == "tenant-finance"
    assert response.body["documentType"] == "invoice"
    assert response.body["requiresHumanReview"] is False
    assert metrics.body["metrics"]["documentAnalyzeCount"] == 1
    assert metrics.body["metrics"]["byUseCase"] == {"finance-document-intelligence": 1}


def test_service_allows_support_speech_assessment_and_rejects_cross_product() -> None:
    service = MediaIntelligenceService(MediaIntelligenceServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/media-intelligence/speech:assess",
        support_speech_body(),
        principal_id="service:support-platform-media",
    )
    denied = service.handle_request(
        "POST",
        "/v1/media-intelligence/speech:assess",
        {
            **support_speech_body(),
            "product": "lms-courseflow",
        },
        principal_id="service:support-platform-media",
    )

    assert response.status_code == 200
    assert response.body["intent"] == "billing_support"
    assert response.body["qualityBand"] == "good"
    assert denied.status_code == 400
    assert denied.body["errorCode"] == "bad_request"
    assert "product is not granted" in denied.body["errorMessage"]


def test_service_rejects_missing_auth_and_raw_media_uri() -> None:
    service = MediaIntelligenceService(MediaIntelligenceServiceConfig.from_paths(ai_root=ai_root()))

    missing_auth = service.handle_request(
        "POST",
        "/v1/media-intelligence/document:analyze",
        finance_document_body(),
    )
    raw_uri = service.handle_request(
        "POST",
        "/v1/media-intelligence/speech:assess",
        {
            **support_speech_body(),
            "rawAudioUri": "s3://raw-audio/call-2001.wav",
        },
        principal_id="service:support-platform-media",
    )

    assert missing_auth.status_code == 401
    assert missing_auth.body["errorCode"] == "auth_required"
    assert raw_uri.status_code == 403
    assert raw_uri.body["errorCode"] == "privacy_control_violation"


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-media-intelligence",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-media-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 4


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-media-intelligence", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == MEDIA_INTELLIGENCE_SERVICE_ID
    assert len(payload["routes"]) == 4
