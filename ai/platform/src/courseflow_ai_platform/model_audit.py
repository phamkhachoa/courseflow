from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from courseflow_ai_platform.model_serving import (
    ModelServingGatewayResponse,
    ModelServingRequest,
)
from courseflow_ai_platform.prompt_audit import (
    contains_unredacted_sensitive_value,
    redact_prompt_text,
    sha256_text,
)

DEFAULT_MODEL_AUDIT_RETENTION_DAYS = 30
MAX_MODEL_AUDIT_RETENTION_DAYS = 180
ModelAuditExportValue = bool | float | int | str
ModelAuditExportRow = dict[str, ModelAuditExportValue]


class ModelAuditStore(Protocol):
    def append(self, record: ModelAuditRecord) -> None: ...

    def list_records(self) -> tuple[ModelAuditRecord, ...]: ...

    def export_tenant(self, tenant_id: str) -> tuple[ModelAuditExportRow, ...]: ...

    def delete_tenant(self, tenant_id: str) -> int: ...

    def purge_expired(self, now: datetime | None = None) -> int: ...


@dataclass(frozen=True, slots=True)
class ModelAuditRecord:
    event_id: str
    request_id: str
    tenant_id: str
    model_id: str
    status: str
    artifact_id: str
    artifact_manifest: str
    method: str
    latency_ms: float
    model_latency_ms: float
    requires_human_review: bool
    fallback_used: bool
    error_code: str
    payload_hash: str
    output_hash: str
    audit_payload: str
    created_at: datetime
    retention_expires_at: datetime

    def to_dict(self) -> ModelAuditExportRow:
        return {
            "artifactId": self.artifact_id,
            "artifactManifest": self.artifact_manifest,
            "auditPayload": self.audit_payload,
            "createdAt": self.created_at.isoformat(),
            "errorCode": self.error_code,
            "eventId": self.event_id,
            "fallbackUsed": self.fallback_used,
            "latencyMs": self.latency_ms,
            "method": self.method,
            "modelId": self.model_id,
            "modelLatencyMs": self.model_latency_ms,
            "outputHash": self.output_hash,
            "payloadHash": self.payload_hash,
            "requestId": self.request_id,
            "requiresHumanReview": self.requires_human_review,
            "retentionExpiresAt": self.retention_expires_at.isoformat(),
            "status": self.status,
            "tenantId": self.tenant_id,
        }


class ModelAuditLedger:
    def __init__(self) -> None:
        self._records: list[ModelAuditRecord] = []

    def append(self, record: ModelAuditRecord) -> None:
        ensure_safe_model_audit_record(record)
        self._records.append(record)

    def list_records(self) -> tuple[ModelAuditRecord, ...]:
        return tuple(self._records)

    def export_tenant(self, tenant_id: str) -> tuple[ModelAuditExportRow, ...]:
        return tuple(record.to_dict() for record in self._records if record.tenant_id == tenant_id)

    def delete_tenant(self, tenant_id: str) -> int:
        before = len(self._records)
        self._records = [record for record in self._records if record.tenant_id != tenant_id]
        return before - len(self._records)

    def purge_expired(self, now: datetime | None = None) -> int:
        cutoff = normalize_datetime(now)
        before = len(self._records)
        self._records = [
            record for record in self._records if record.retention_expires_at > cutoff
        ]
        return before - len(self._records)


class JsonlModelAuditStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: ModelAuditRecord) -> None:
        ensure_safe_model_audit_record(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")

    def list_records(self) -> tuple[ModelAuditRecord, ...]:
        return tuple(self._load_records())

    def export_tenant(self, tenant_id: str) -> tuple[ModelAuditExportRow, ...]:
        return tuple(
            record.to_dict() for record in self._load_records() if record.tenant_id == tenant_id
        )

    def delete_tenant(self, tenant_id: str) -> int:
        records = self._load_records()
        kept = [record for record in records if record.tenant_id != tenant_id]
        self._rewrite_records(kept)
        return len(records) - len(kept)

    def purge_expired(self, now: datetime | None = None) -> int:
        cutoff = normalize_datetime(now)
        records = self._load_records()
        kept = [record for record in records if record.retention_expires_at > cutoff]
        self._rewrite_records(kept)
        return len(records) - len(kept)

    def _load_records(self) -> list[ModelAuditRecord]:
        if not self.path.exists():
            return []

        records: list[ModelAuditRecord] = []
        with self.path.open("r", encoding="utf-8") as audit_file:
            for line_number, line in enumerate(audit_file, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(model_audit_record_from_dict(json.loads(line)))
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(
                        f"invalid model audit JSONL record at line {line_number}"
                    ) from exc
        return records

    def _rewrite_records(self, records: list[ModelAuditRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        with temp_path.open("w", encoding="utf-8") as audit_file:
            for record in records:
                ensure_safe_model_audit_record(record)
                audit_file.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
        temp_path.replace(self.path)


def build_model_audit_record(
    request: ModelServingRequest,
    response: ModelServingGatewayResponse,
    now: datetime | None = None,
    retention_days: int = DEFAULT_MODEL_AUDIT_RETENTION_DAYS,
) -> ModelAuditRecord:
    created_at = normalize_datetime(now)
    bounded_retention_days = min(
        max(1, retention_days),
        MAX_MODEL_AUDIT_RETENTION_DAYS,
    )
    sanitized_payload = sanitize_model_payload(request.payload)
    sanitized_output = sanitize_model_payload(response.output)
    audit_payload = build_sanitized_model_audit_payload(
        request=request,
        response=response,
        sanitized_payload=sanitized_payload,
        sanitized_output=sanitized_output,
    )
    return ModelAuditRecord(
        event_id=str(uuid4()),
        request_id=request.request_id,
        tenant_id=request.tenant_id,
        model_id=request.model_id,
        status=response.status,
        artifact_id=response.artifact_id,
        artifact_manifest=response.artifact_manifest,
        method=response.method,
        latency_ms=response.latency_ms,
        model_latency_ms=response.model_latency_ms,
        requires_human_review=response.requires_human_review,
        fallback_used=response.fallback_used,
        error_code=response.error_code,
        payload_hash=sha256_text(json.dumps(sanitized_payload, sort_keys=True)),
        output_hash=sha256_text(json.dumps(sanitized_output, sort_keys=True)),
        audit_payload=audit_payload,
        created_at=created_at,
        retention_expires_at=created_at + timedelta(days=bounded_retention_days),
    )


def model_audit_record_from_dict(row: Mapping[str, object]) -> ModelAuditRecord:
    return ModelAuditRecord(
        event_id=required_str(row, "eventId"),
        request_id=required_str(row, "requestId"),
        tenant_id=required_str(row, "tenantId"),
        model_id=required_str(row, "modelId"),
        status=required_str(row, "status"),
        artifact_id=required_str_allow_empty(row, "artifactId"),
        artifact_manifest=required_str_allow_empty(row, "artifactManifest"),
        method=required_str_allow_empty(row, "method"),
        latency_ms=required_float(row, "latencyMs"),
        model_latency_ms=required_float(row, "modelLatencyMs"),
        requires_human_review=required_bool(row, "requiresHumanReview"),
        fallback_used=required_bool(row, "fallbackUsed"),
        error_code=required_str_allow_empty(row, "errorCode"),
        payload_hash=required_str(row, "payloadHash"),
        output_hash=required_str(row, "outputHash"),
        audit_payload=required_str(row, "auditPayload"),
        created_at=parse_audit_datetime(required_str(row, "createdAt")),
        retention_expires_at=parse_audit_datetime(required_str(row, "retentionExpiresAt")),
    )


def sanitize_model_payload(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): sanitize_model_payload(item)
            for key, item in sorted(value.items(), key=lambda row: str(row[0]))
        }
    if isinstance(value, list):
        return [sanitize_model_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_model_payload(item) for item in value)
    if isinstance(value, str):
        return redact_prompt_text(value)
    return value


def build_sanitized_model_audit_payload(
    request: ModelServingRequest,
    response: ModelServingGatewayResponse,
    sanitized_payload: object,
    sanitized_output: object,
) -> str:
    payload = json.dumps(
        {
            "artifact_id": response.artifact_id,
            "artifact_manifest": response.artifact_manifest,
            "error_code": response.error_code,
            "fallback_used": response.fallback_used,
            "latency_ms": response.latency_ms,
            "method": response.method,
            "model_id": request.model_id,
            "model_latency_ms": response.model_latency_ms,
            "payload": sanitized_payload,
            "request_id": request.request_id,
            "requires_human_review": response.requires_human_review,
            "status": response.status,
            "tenant_id": request.tenant_id,
            "output": sanitized_output,
        },
        sort_keys=True,
    )
    if contains_unredacted_sensitive_value(payload):
        raise ValueError("sanitized model audit payload still contains sensitive value")
    return payload


def ensure_safe_model_audit_record(record: ModelAuditRecord) -> None:
    if contains_unredacted_sensitive_value(record.audit_payload):
        raise ValueError("model audit payload contains unredacted sensitive value")


def normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_audit_datetime(value: str) -> datetime:
    return normalize_datetime(datetime.fromisoformat(value))


def required_str(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"model audit field {key} must be a non-empty string")
    return value


def required_str_allow_empty(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str):
        raise ValueError(f"model audit field {key} must be a string")
    return value


def required_bool(row: Mapping[str, object], key: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"model audit field {key} must be a boolean")
    return value


def required_float(row: Mapping[str, object], key: str) -> float:
    value = row.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"model audit field {key} must be numeric")
    return float(value)
