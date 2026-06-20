from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_causal_uplift_service.cli import main
from courseflow_causal_uplift_service.service import (
    CAUSAL_UPLIFT_SERVICE_ID,
    CausalUpliftService,
    CausalUpliftServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def enterprise_uplift_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ai",
        "product": "ai-platform",
        "useCaseId": "enterprise-experimentation-uplift",
        "experimentId": "exp-1001",
        "outcomeName": "activation",
        "treatmentName": "new_onboarding",
        "controlName": "current_onboarding",
        "treatmentCount": 320,
        "treatmentSuccesses": 154,
        "controlCount": 320,
        "controlSuccesses": 112,
        "minimumDetectableLift": 0.03,
        "confidenceLevel": 0.95,
        "guardrailMetricDelta": 0.0,
        "highImpact": True,
        "segmentCount": 3,
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "causal-uplift-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "causal-uplift-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == CAUSAL_UPLIFT_SERVICE_ID
    assert service_yaml["service_id"] == CAUSAL_UPLIFT_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_evaluates_uplift_and_tracks_metrics() -> None:
    service = CausalUpliftService(
        CausalUpliftServiceConfig.from_paths(ai_root=ai_root())
    )

    response = service.handle_request(
        "POST",
        "/v1/causal-uplift/evaluate",
        enterprise_uplift_body(),
        principal_id="service:ai-platform-experimentation",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/causal-uplift/metrics",
        principal_id="service:ai-platform-causal-ops",
    )

    assert response.status_code == 200
    assert response.body["modelId"] == "causal-uplift-baseline-v1"
    assert response.body["decisionBand"] == "positive_lift"
    assert response.body["automatedRolloutAllowed"] is False
    assert metrics.body["metrics"]["evaluationCount"] == 1
    assert metrics.body["metrics"]["byUseCase"] == {
        "enterprise-experimentation-uplift": 1
    }


def test_service_rejects_missing_auth_cross_tenant_and_direct_identifier() -> None:
    service = CausalUpliftService(
        CausalUpliftServiceConfig.from_paths(ai_root=ai_root())
    )

    missing_auth = service.handle_request(
        "POST",
        "/v1/causal-uplift/evaluate",
        enterprise_uplift_body(),
    )
    denied = service.handle_request(
        "POST",
        "/v1/causal-uplift/evaluate",
        {**enterprise_uplift_body(), "tenantId": "tenant-lms"},
        principal_id="service:ai-platform-experimentation",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/causal-uplift/evaluate",
        {**enterprise_uplift_body(), "participantId": "participant-raw-001"},
        principal_id="service:ai-platform-experimentation",
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
            "courseflow-causal-uplift",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-causal-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-causal-uplift", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == CAUSAL_UPLIFT_SERVICE_ID
    assert len(payload["routes"]) == 3
