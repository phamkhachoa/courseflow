from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml
from courseflow_ai_platform.registry import load_yaml

from courseflow_model_serving_service.cli import main
from courseflow_model_serving_service.service import (
    MODEL_SERVING_SERVICE_ID,
    ModelServingService,
    ModelServingServiceConfig,
    build_service_manifest,
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[3]


def demand_forecast_body() -> dict[str, object]:
    return {
        "requestId": "req-service-1001",
        "tenantId": "tenant-ops",
        "modelId": "operations-demand-forecast-baseline-v1",
        "payload": {
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-service-1001",
            "queue_id": "support-identity",
            "historical_demand": [78, 82, 84, 96, 114, 132],
            "planned_capacity": 110,
            "backlog_open_items": 28,
            "avg_handle_minutes": 52,
            "seasonal_index": 1.08,
            "special_event": True,
            "incident_open": True,
            "forecast_horizon_days": 7,
            "service_level_target": 0.92,
        },
    }


def test_service_manifest_matches_service_yaml_and_policy_scopes() -> None:
    manifest = build_service_manifest()
    service_yaml = yaml.safe_load(
        (
            ai_root()
            / "services"
            / "model-serving-service"
            / "service.yaml"
        ).read_text(encoding="utf-8")
    )
    ai_governance = load_yaml(
        ai_root() / "platform" / "governance" / "policies" / "ai-governance-policy.yaml"
    )
    endpoint_scopes = ai_governance["policies"]["security"]["serving_endpoint_scopes"]

    assert manifest["serviceId"] == MODEL_SERVING_SERVICE_ID
    assert service_yaml["service_id"] == MODEL_SERVING_SERVICE_ID
    assert len(manifest["routes"]) == 6
    assert {route["path"] for route in manifest["routes"]} == {
        route["path"] for route in service_yaml["routes"]
    }
    assert {endpoint_scopes["catalog"], endpoint_scopes["invoke"], endpoint_scopes["ops"]} == {
        route["scope"] for route in manifest["routes"]
    }


def test_service_invokes_model_and_exports_metrics(tmp_path: Path) -> None:
    export_path = tmp_path / "model-serving-metrics.yaml"
    service = ModelServingService(
        ModelServingServiceConfig.from_paths(
            ai_root=ai_root(),
            audit_log_path=tmp_path / "audit.jsonl",
        )
    )

    response = service.invoke(
        demand_forecast_body(),
        principal_id="service:enterprise-operations-serving",
    )
    metrics = service.metrics(principal_id="service:ai-platform-ops")
    health = service.health(principal_id="service:ai-platform-ops")
    product_readiness = service.product_readiness(principal_id="service:ai-platform-ops")
    service.export_metrics(export_path, generated_at="2026-06-17")
    exported = load_yaml(export_path)

    assert response.status_code == 200
    assert response.body["status"] == "ok"
    assert response.body["output"]["demandBand"] == "high"
    assert metrics.status_code == 200
    assert metrics.body["metrics"]["requestCount"] == 1
    assert metrics.body["metrics"]["auditRecordCount"] == 1
    assert health.body["status"] == "healthy"
    assert product_readiness.status_code == 200
    assert product_readiness.body["report_id"] == "ai-platform-product-readiness-v1"
    assert product_readiness.body["summary"]["serving_status"] == "healthy"
    assert product_readiness.body["summary"]["serving_request_count"] == 1
    assert product_readiness.body["summary"]["serving_audit_record_count"] == 1
    assert product_readiness.body["summary"]["readiness_status"] == (
        "stakeholder_ready_with_followups"
    )
    assert exported["source_adapter"] == MODEL_SERVING_SERVICE_ID
    assert exported["summary"]["request_count"] == 1
    assert exported["summary"]["audit_record_count"] == 1


def test_service_rejects_unapproved_ops_scope_for_product_principal() -> None:
    service = ModelServingService(ModelServingServiceConfig.from_paths(ai_root=ai_root()))

    response = service.metrics(principal_id="service:enterprise-operations-serving")

    assert response.status_code == 403
    assert response.body["errorCode"] == "principal_policy_forbidden"
    assert "ungranted scopes" in response.body["errorMessage"]


def test_cli_health_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-model-serving",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-ops",
            "health",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["status"] == "no_serving_traffic"


def test_cli_product_readiness_uses_registered_ops_principal(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "courseflow-model-serving",
            "--ai-root",
            str(ai_root()),
            "--principal-id",
            "service:ai-platform-ops",
            "product-readiness",
        ],
    )

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["statusCode"] == 200
    assert payload["body"]["report_id"] == "ai-platform-product-readiness-v1"
    assert payload["body"]["summary"]["serving_status"] == "no_serving_traffic"
    assert payload["body"]["summary"]["readiness_status"] == "blocked"


def test_cli_manifest(capsys, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["courseflow-model-serving", "manifest"])

    assert main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["serviceId"] == MODEL_SERVING_SERVICE_ID
    assert len(payload["routes"]) == 6
    assert "/v1/model-serving/product-readiness" in {
        route["path"] for route in payload["routes"]
    }
