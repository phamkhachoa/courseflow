from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_forecasting_service.cli import main
from courseflow_forecasting_service.service import (
    FORECASTING_SERVICE_ID,
    ForecastingService,
    ForecastingServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def high_demand_body() -> dict[str, object]:
    return {
        "tenantId": "tenant-ops",
        "product": "enterprise-operations",
        "useCaseId": "operations-demand-forecasting",
        "forecastId": "fc-1001",
        "queueId": "support-identity",
        "historicalDemand": [78, 82, 84, 96, 114, 132],
        "plannedCapacity": 110,
        "backlogOpenItems": 28,
        "avgHandleMinutes": 52,
        "seasonalIndex": 1.08,
        "specialEvent": True,
        "incidentOpen": True,
        "forecastHorizonDays": 7,
        "serviceLevelTarget": 0.92,
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (ai_root() / "services" / "forecasting-service" / "service.yaml").read_text(
            encoding="utf-8"
        )
    )
    policy = load_yaml(
        ai_root()
        / "platform"
        / "governance"
        / "policies"
        / "forecasting-access-policy.yaml"
    )
    scopes = set(policy["scope_aliases"].values())

    assert manifest["serviceId"] == FORECASTING_SERVICE_ID
    assert service_yaml["service_id"] == FORECASTING_SERVICE_ID
    assert len(manifest["routes"]) == 3
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {route["scope"] for route in manifest["routes"]} == scopes


def test_service_scores_forecast_and_tracks_metrics() -> None:
    service = ForecastingService(ForecastingServiceConfig.from_paths(ai_root=ai_root()))

    response = service.handle_request(
        "POST",
        "/v1/forecasting/demand/score",
        high_demand_body(),
        principal_id="service:enterprise-operations-forecasting",
    )
    metrics = service.handle_request(
        "GET",
        "/v1/forecasting/metrics",
        principal_id="service:ai-platform-forecasting-ops",
    )

    assert response.status_code == 200
    assert response.body["modelId"] == "operations-demand-forecast-baseline-v1"
    assert response.body["demandBand"] == "high"
    assert response.body["requiresHumanReview"] is True
    assert response.body["automatedCapacityChangeAllowed"] is False
    assert metrics.body["metrics"]["scoreCount"] == 1
    assert metrics.body["metrics"]["highDemandCount"] == 1
    assert metrics.body["metrics"]["byUseCase"] == {
        "operations-demand-forecasting": 1
    }


def test_service_rejects_missing_auth_cross_tenant_and_direct_identifier() -> None:
    service = ForecastingService(ForecastingServiceConfig.from_paths(ai_root=ai_root()))

    missing_auth = service.handle_request(
        "POST",
        "/v1/forecasting/demand/score",
        high_demand_body(),
    )
    denied = service.handle_request(
        "POST",
        "/v1/forecasting/demand/score",
        {**high_demand_body(), "tenantId": "tenant-finance"},
        principal_id="service:enterprise-operations-forecasting",
    )
    direct_identifier = service.handle_request(
        "POST",
        "/v1/forecasting/demand/score",
        {**high_demand_body(), "employeeId": "emp-raw-001"},
        principal_id="service:enterprise-operations-forecasting",
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
            "courseflow-forecasting",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-forecasting-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["serviceStatus"] == "healthy"
    assert payload["body"]["routeCount"] == 3


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-forecasting", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == FORECASTING_SERVICE_ID
    assert len(payload["routes"]) == 3
