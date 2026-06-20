from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_governance_evaluation_service.cli import main
from courseflow_governance_evaluation_service.service import (
    GOVERNANCE_EVALUATION_SERVICE_ID,
    GovernanceEvaluationService,
    GovernanceEvaluationServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def lms_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-lms",
        "product": "lms-courseflow",
        "useCaseId": "lms-related-course-recommendation",
        "promotionId": "recommendation-item-cf-v1-active-baseline",
        "asOf": "2026-06-17",
    }


def support_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-support",
        "product": "support-platform",
        "useCaseId": "support-agent-assist",
        "promotionId": "support-agent-assist-baseline-approved",
        "riskLevel": "high",
        "asOf": "2026-06-17",
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (
            ai_root() / "services" / "governance-evaluation-service" / "service.yaml"
        ).read_text(encoding="utf-8")
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "governance-evaluation-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == GOVERNANCE_EVALUATION_SERVICE_ID
    assert service_yaml["service_id"] == GOVERNANCE_EVALUATION_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_assesses_lms_and_support_governance_decisions() -> None:
    service = GovernanceEvaluationService(
        GovernanceEvaluationServiceConfig.from_paths(ai_root=ai_root())
    )

    lms_response = service.handle_request(
        "POST",
        "/v1/governance-evaluation/assess",
        lms_body(),
        principal_id="service:lms-courseflow-governance-evaluation",
    )
    support_response = service.handle_request(
        "POST",
        "/v1/governance-evaluation/assess",
        support_body(),
        principal_id="service:support-platform-governance-evaluation",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/governance-evaluation/metrics",
        principal_id="service:ai-platform-governance-evaluation-ops",
    )

    assert lms_response.status_code == 200
    assert lms_response.body["decision"] == "approved"
    assert lms_response.body["readyForRelease"] is True
    assert support_response.status_code == 200
    assert support_response.body["decision"] == "review_required"
    assert support_response.body["requiresHumanReview"] is True
    assert metrics.body["metrics"]["assessmentCount"] == 2
    assert metrics.body["metrics"]["approvedCount"] == 1
    assert metrics.body["metrics"]["reviewRequiredCount"] == 1


def test_service_rejects_missing_auth_denied_scope_and_private_evidence() -> None:
    service = GovernanceEvaluationService(
        GovernanceEvaluationServiceConfig.from_paths(ai_root=ai_root())
    )

    missing_auth = service.handle_request(
        "POST",
        "/v1/governance-evaluation/assess",
        lms_body(),
    )
    denied_product = service.handle_request(
        "POST",
        "/v1/governance-evaluation/assess",
        support_body(),
        principal_id="service:lms-courseflow-governance-evaluation",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/governance-evaluation/assess",
        {**support_body(), "email": "agent@example.com"},
        principal_id="service:support-platform-governance-evaluation",
    )
    secret = service.handle_request(
        "POST",
        "/v1/governance-evaluation/assess",
        {**support_body(), "apiKey": "sk-not-allowed"},
        principal_id="service:support-platform-governance-evaluation",
    )

    assert missing_auth.status_code == 401
    assert missing_auth.body["errorCode"] == "auth_required"
    assert denied_product.status_code == 400
    assert "tenant is not granted" in denied_product.body["errorMessage"]
    assert direct_identifier.status_code == 403
    assert direct_identifier.body["errorCode"] == "privacy_control_violation"
    assert secret.status_code == 403
    assert secret.body["errorCode"] == "privacy_control_violation"


def test_service_blocks_external_auto_send_without_policy_approval() -> None:
    service = GovernanceEvaluationService(
        GovernanceEvaluationServiceConfig.from_paths(ai_root=ai_root())
    )

    response = service.handle_request(
        "POST",
        "/v1/governance-evaluation/assess",
        {**support_body(), "externalAutoSend": True},
        principal_id="service:support-platform-governance-evaluation",
    )

    assert response.status_code == 200
    assert response.body["decision"] == "blocked"
    assert response.body["blockedReasons"] == ("external_auto_send_forbidden",)


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-governance-evaluation",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-governance-evaluation-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-governance-evaluation", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == GOVERNANCE_EVALUATION_SERVICE_ID
    assert len(payload["routes"]) == 3
