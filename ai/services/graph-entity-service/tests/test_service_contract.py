from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_graph_entity_service.cli import main
from courseflow_graph_entity_service.service import (
    GRAPH_ENTITY_SERVICE_ID,
    GraphEntityService,
    GraphEntityServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def graph_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-finance",
        "product": "billing-finance",
        "useCaseId": "finance-payment-fraud-scoring",
        "graphContextId": "graph-payment-1001",
        "accountHash": "acct_hash_001",
        "counterpartyHash": "counterparty_hash_007",
        "deviceFingerprintHash": "device_hash_003",
        "linkedAccountCount": 6,
        "sharedCounterpartyCount": 5,
        "velocity1h": 6,
        "velocity24h": 14,
        "priorFailedAttempts7d": 4,
        "priorChargebackCount": 1,
        "amountMinor": 1250000,
        "accountAgeDays": 4,
        "verifiedPaymentMethodsCount": 0,
        "currency": "USD",
        "paymentMethod": "card_not_present",
        "countryCode": "US",
        "riskReviewOutcome": "manual_review",
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "graph-entity-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "graph-entity-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == GRAPH_ENTITY_SERVICE_ID
    assert service_yaml["service_id"] == GRAPH_ENTITY_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_analyzes_entity_links_and_tracks_metrics() -> None:
    service = GraphEntityService(GraphEntityServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/graph-entity/analyze",
        graph_body(),
        principal_id="service:finance-graph-risk",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/graph-entity/metrics",
        principal_id="service:ai-platform-graph-ops",
    )

    assert response.status_code == 200
    assert response.body["modelId"] == "finance-payment-fraud-baseline-v1"
    assert response.body["adverseActionAllowed"] is False
    assert response.body["graphReviewRequired"] is True
    assert metrics.body["metrics"]["analysisCount"] == 1
    assert metrics.body["metrics"]["byUseCase"] == {"finance-payment-fraud-scoring": 1}


def test_service_rejects_missing_auth_cross_tenant_and_direct_identifier() -> None:
    service = GraphEntityService(GraphEntityServiceConfig.from_paths(ai_root=ai_root()))

    missing_auth = service.handle_request(
        "POST",
        "/v1/graph-entity/analyze",
        graph_body(),
    )
    denied = service.handle_request(
        "POST",
        "/v1/graph-entity/analyze",
        {**graph_body(), "tenantId": "tenant-ops"},
        principal_id="service:finance-graph-risk",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/graph-entity/analyze",
        {**graph_body(), "customerId": "customer-raw-001"},
        principal_id="service:finance-graph-risk",
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
            "courseflow-graph-entity",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-graph-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-graph-entity", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == GRAPH_ENTITY_SERVICE_ID
    assert len(payload["routes"]) == 3
