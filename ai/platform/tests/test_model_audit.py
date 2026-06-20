from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from courseflow_ai_platform.model_audit import (
    JsonlModelAuditStore,
    ModelAuditLedger,
    build_model_audit_record,
    contains_unredacted_sensitive_value,
)
from courseflow_ai_platform.model_serving import ModelServingGateway, ModelServingRequest


def demand_forecast_request() -> ModelServingRequest:
    return ModelServingRequest(
        request_id="req-2001",
        tenant_id="tenant-ops",
        model_id="operations-demand-forecast-baseline-v1",
        payload={
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-2001",
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
            "operator_email": "ops.owner@example.com",
            "api_token": "sk-live-secret",
        },
    )


def test_model_audit_record_hashes_payload_output_and_redacts_sensitive_values() -> None:
    request = demand_forecast_request()
    gateway = ModelServingGateway(Path(__file__).resolve().parents[2])
    response = gateway.invoke(request)

    record = build_model_audit_record(
        request,
        response,
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )

    assert record.request_id == "req-2001"
    assert record.tenant_id == "tenant-ops"
    assert record.model_id == "operations-demand-forecast-baseline-v1"
    assert record.status == "ok"
    assert record.requires_human_review is True
    assert len(record.payload_hash) == 64
    assert len(record.output_hash) == 64
    assert "ops.owner@example.com" not in record.audit_payload
    assert "sk-live-secret" not in record.audit_payload
    assert "[REDACTED_EMAIL]" in record.audit_payload
    assert "[REDACTED_SECRET]" in record.audit_payload
    assert contains_unredacted_sensitive_value(record.audit_payload) is False


def test_model_audit_ledger_exports_deletes_and_purges_by_tenant() -> None:
    request = demand_forecast_request()
    response = ModelServingGateway(Path(__file__).resolve().parents[2]).invoke(request)
    now = datetime(2026, 6, 17, tzinfo=UTC)
    ledger = ModelAuditLedger()

    ledger.append(build_model_audit_record(request, response, now=now, retention_days=1))
    assert len(ledger.export_tenant("tenant-ops")) == 1
    assert ledger.purge_expired(now + timedelta(days=2)) == 1
    assert ledger.list_records() == ()

    ledger.append(build_model_audit_record(request, response, now=now))
    assert ledger.delete_tenant("tenant-ops") == 1
    assert ledger.export_tenant("tenant-ops") == ()


def test_jsonl_model_audit_store_persists_exports_deletes_and_purges(
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "model-audit.jsonl"
    request = demand_forecast_request()
    response = ModelServingGateway(Path(__file__).resolve().parents[2]).invoke(request)
    now = datetime(2026, 6, 17, tzinfo=UTC)
    record = build_model_audit_record(request, response, now=now, retention_days=1)

    store = JsonlModelAuditStore(store_path)
    store.append(record)
    persisted_store = JsonlModelAuditStore(store_path)
    persisted_records = persisted_store.list_records()

    assert len(persisted_records) == 1
    assert persisted_records[0].event_id == record.event_id
    assert persisted_records[0].created_at == now
    assert len(persisted_store.export_tenant("tenant-ops")) == 1
    assert persisted_store.purge_expired(now + timedelta(days=2)) == 1
    assert persisted_store.list_records() == ()

    persisted_store.append(build_model_audit_record(request, response, now=now))
    assert persisted_store.delete_tenant("tenant-ops") == 1
    assert persisted_store.export_tenant("tenant-ops") == ()


def test_jsonl_model_audit_store_rejects_unsafe_payload(tmp_path: Path) -> None:
    request = demand_forecast_request()
    response = ModelServingGateway(Path(__file__).resolve().parents[2]).invoke(request)
    record = build_model_audit_record(request, response)
    unsafe_record = replace(record, audit_payload='{"email": "ops.owner@example.com"}')

    with pytest.raises(ValueError, match="unredacted sensitive value"):
        JsonlModelAuditStore(tmp_path / "model-audit.jsonl").append(unsafe_record)
