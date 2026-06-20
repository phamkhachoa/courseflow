from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_sequence_risk_service.cli import main
from courseflow_sequence_risk_service.service import (
    SEQUENCE_RISK_SERVICE_ID,
    SequenceRiskService,
    SequenceRiskServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def high_risk_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-lms",
        "product": "lms-courseflow",
        "useCaseId": "lms-at-risk-prediction",
        "subjectPrincipalHash": "learner-hash-001",
        "sequenceId": "course-python",
        "featureSnapshotAt": "2026-06-17T00:00:00Z",
        "events": [
            {"event_type": "missed_deadline", "days_ago": 1},
            {"event_type": "low_quiz_score", "days_ago": 2, "score": 0.38},
            {"event_type": "inactive_day", "days_ago": 2},
            {"event_type": "late_submission", "days_ago": 4},
        ],
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "sequence-risk-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "sequence-risk-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == SEQUENCE_RISK_SERVICE_ID
    assert service_yaml["service_id"] == SEQUENCE_RISK_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_scores_sequence_risk_and_tracks_metrics() -> None:
    service = SequenceRiskService(SequenceRiskServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/sequence-risk/score",
        high_risk_body(),
        principal_id="service:lms-courseflow-sequence",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/sequence-risk/metrics",
        principal_id="service:ai-platform-sequence-ops",
    )

    assert response.status_code == 200
    assert response.body["modelId"] == "sequence-risk-baseline-v1"
    assert response.body["riskBand"] == "high"
    assert response.body["requiresHumanReview"] is True
    assert metrics.body["metrics"]["scoreCount"] == 1
    assert metrics.body["metrics"]["highRiskCount"] == 1
    assert metrics.body["metrics"]["byUseCase"] == {"lms-at-risk-prediction": 1}


def test_service_rejects_missing_auth_cross_tenant_and_direct_identifier() -> None:
    service = SequenceRiskService(SequenceRiskServiceConfig.from_paths(ai_root=ai_root()))

    missing_auth = service.handle_request("POST", "/v1/sequence-risk/score", high_risk_body())
    denied = service.handle_request(
        "POST",
        "/v1/sequence-risk/score",
        {**high_risk_body(), "tenantId": "tenant-support"},
        principal_id="service:lms-courseflow-sequence",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/sequence-risk/score",
        {**high_risk_body(), "learnerId": "learner-raw-001"},
        principal_id="service:lms-courseflow-sequence",
    )

    assert missing_auth.status_code == 401
    assert missing_auth.body["errorCode"] == "auth_required"
    assert denied.status_code == 400
    assert "tenant is not granted" in denied.body["errorMessage"]
    assert direct_identifier.status_code == 403
    assert direct_identifier.body["errorCode"] == "privacy_control_violation"


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-sequence-risk",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-sequence-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-sequence-risk", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == SEQUENCE_RISK_SERVICE_ID
    assert len(payload["routes"]) == 3
