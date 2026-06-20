from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_routing_policy_service.cli import main
from courseflow_routing_policy_service.service import (
    ROUTING_POLICY_SERVICE_ID,
    RoutingPolicyService,
    RoutingPolicyServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def high_priority_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ops",
        "product": "enterprise-operations",
        "useCaseId": "operations-routing-optimization",
        "policyId": "routing-policy-v1",
        "safeExplorationBudget": 0.0,
        "baselineQueueId": "queue-general",
        "workItem": {
            "workItemId": "work-1001",
            "workType": "identity_outage",
            "priority": "p1",
            "requiredSkillIds": ["identity", "integration"],
            "expectedEffortMinutes": 30,
        },
        "queues": [
            {
                "queueId": "queue-general",
                "availableAgentCount": 3,
                "backlogCount": 9,
                "averageHandleTimeMinutes": 45,
                "skillIds": ["general"],
                "maxConcurrency": 4,
            },
            {
                "queueId": "queue-identity",
                "availableAgentCount": 2,
                "backlogCount": 2,
                "averageHandleTimeMinutes": 30,
                "skillIds": ["identity", "integration"],
                "maxConcurrency": 3,
            },
        ],
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "routing-policy-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "routing-policy-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == ROUTING_POLICY_SERVICE_ID
    assert service_yaml["service_id"] == ROUTING_POLICY_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_recommends_route_and_tracks_metrics() -> None:
    service = RoutingPolicyService(
        RoutingPolicyServiceConfig.from_paths(ai_root=ai_root())
    )

    response = service.handle_request(
        "POST",
        "/v1/routing-policy/recommend",
        high_priority_body(),
        principal_id="service:enterprise-operations-routing",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/routing-policy/metrics",
        principal_id="service:ai-platform-routing-ops",
    )

    assert response.status_code == 200
    assert response.body["model_id"] == "operations-routing-policy-simulator-v1"
    assert response.body["assigned_queue_id"] == "queue-identity"
    assert response.body["onlinePolicyActivationAllowed"] is False
    assert metrics.body["metrics"]["recommendationCount"] == 1
    assert metrics.body["metrics"]["byUseCase"] == {
        "operations-routing-optimization": 1
    }


def test_service_rejects_missing_auth_cross_tenant_and_direct_identifier() -> None:
    service = RoutingPolicyService(
        RoutingPolicyServiceConfig.from_paths(ai_root=ai_root())
    )

    missing_auth = service.handle_request(
        "POST",
        "/v1/routing-policy/recommend",
        high_priority_body(),
    )
    denied = service.handle_request(
        "POST",
        "/v1/routing-policy/recommend",
        {**high_priority_body(), "tenantId": "tenant-finance"},
        principal_id="service:enterprise-operations-routing",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/routing-policy/recommend",
        {**high_priority_body(), "agentId": "agent-raw-001"},
        principal_id="service:enterprise-operations-routing",
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
            "courseflow-routing-policy",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-routing-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-routing-policy", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == ROUTING_POLICY_SERVICE_ID
    assert len(payload["routes"]) == 3
