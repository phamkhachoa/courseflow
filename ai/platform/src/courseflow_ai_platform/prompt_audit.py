from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from courseflow_ai_platform.prompt_gateway import (
    PromptGatewayRequest,
    PromptGatewayResult,
    redact_prompt_text,
)

DEFAULT_RETENTION_DAYS = 30
MAX_RETENTION_DAYS = 90
AuditExportValue = bool | int | str | tuple[str, ...]
AuditExportRow = dict[str, AuditExportValue]


class PromptAuditStore(Protocol):
    def append(self, record: PromptAuditRecord) -> None: ...

    def list_records(self) -> tuple[PromptAuditRecord, ...]: ...

    def export_tenant(self, tenant_id: str) -> tuple[AuditExportRow, ...]: ...

    def delete_tenant(self, tenant_id: str) -> int: ...

    def purge_expired(self, now: datetime | None = None) -> int: ...


@dataclass(frozen=True, slots=True)
class PromptAuditRecord:
    event_id: str
    tenant_id: str
    product: str
    use_case_id: str
    gateway_allowed: bool
    blocked_reasons: tuple[str, ...]
    context_ids: tuple[str, ...]
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_total_tokens: int
    sanitized_prompt_hash: str
    sanitized_response_hash: str
    audit_payload: str
    created_at: datetime
    retention_expires_at: datetime

    def to_dict(self) -> AuditExportRow:
        return {
            "auditPayload": self.audit_payload,
            "blockedReasons": self.blocked_reasons,
            "contextIds": self.context_ids,
            "createdAt": self.created_at.isoformat(),
            "estimatedInputTokens": self.estimated_input_tokens,
            "estimatedOutputTokens": self.estimated_output_tokens,
            "estimatedTotalTokens": self.estimated_total_tokens,
            "eventId": self.event_id,
            "gatewayAllowed": self.gateway_allowed,
            "product": self.product,
            "retentionExpiresAt": self.retention_expires_at.isoformat(),
            "sanitizedPromptHash": self.sanitized_prompt_hash,
            "sanitizedResponseHash": self.sanitized_response_hash,
            "tenantId": self.tenant_id,
            "useCaseId": self.use_case_id,
        }


class PromptAuditLedger:
    def __init__(self) -> None:
        self._records: list[PromptAuditRecord] = []

    def append(self, record: PromptAuditRecord) -> None:
        ensure_safe_prompt_audit_record(record)
        self._records.append(record)

    def list_records(self) -> tuple[PromptAuditRecord, ...]:
        return tuple(self._records)

    def export_tenant(self, tenant_id: str) -> tuple[AuditExportRow, ...]:
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


class JsonlPromptAuditStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: PromptAuditRecord) -> None:
        ensure_safe_prompt_audit_record(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")

    def list_records(self) -> tuple[PromptAuditRecord, ...]:
        return tuple(self._load_records())

    def export_tenant(self, tenant_id: str) -> tuple[AuditExportRow, ...]:
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

    def _load_records(self) -> list[PromptAuditRecord]:
        if not self.path.exists():
            return []

        records: list[PromptAuditRecord] = []
        with self.path.open("r", encoding="utf-8") as audit_file:
            for line_number, line in enumerate(audit_file, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(prompt_audit_record_from_dict(json.loads(line)))
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    raise ValueError(
                        f"invalid prompt audit JSONL record at line {line_number}"
                    ) from exc
        return records

    def _rewrite_records(self, records: list[PromptAuditRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        with temp_path.open("w", encoding="utf-8") as audit_file:
            for record in records:
                ensure_safe_prompt_audit_record(record)
                audit_file.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
        temp_path.replace(self.path)

def build_prompt_audit_record(
    request: PromptGatewayRequest,
    result: PromptGatewayResult,
    response_text: str = "",
    now: datetime | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> PromptAuditRecord:
    created_at = normalize_datetime(now)
    bounded_retention_days = min(max(1, retention_days), MAX_RETENTION_DAYS)
    sanitized_response = redact_prompt_text(response_text)
    audit_payload = build_sanitized_audit_payload(
        request=request,
        result=result,
        sanitized_response=sanitized_response,
    )
    return PromptAuditRecord(
        event_id=str(uuid4()),
        tenant_id=request.tenant_id,
        product=request.product,
        use_case_id=request.use_case_id,
        gateway_allowed=result.allowed,
        blocked_reasons=result.blocked_reasons,
        context_ids=result.context_ids,
        estimated_input_tokens=result.estimated_input_tokens,
        estimated_output_tokens=result.estimated_output_tokens,
        estimated_total_tokens=result.estimated_total_tokens,
        sanitized_prompt_hash=sha256_text(result.sanitized_prompt),
        sanitized_response_hash=sha256_text(sanitized_response),
        audit_payload=audit_payload,
        created_at=created_at,
        retention_expires_at=created_at + timedelta(days=bounded_retention_days),
    )


def prompt_audit_record_from_dict(row: Mapping[str, object]) -> PromptAuditRecord:
    return PromptAuditRecord(
        event_id=required_str(row, "eventId"),
        tenant_id=required_str(row, "tenantId"),
        product=required_str(row, "product"),
        use_case_id=required_str(row, "useCaseId"),
        gateway_allowed=required_bool(row, "gatewayAllowed"),
        blocked_reasons=required_str_tuple(row, "blockedReasons"),
        context_ids=required_str_tuple(row, "contextIds"),
        estimated_input_tokens=required_int(row, "estimatedInputTokens"),
        estimated_output_tokens=required_int(row, "estimatedOutputTokens"),
        estimated_total_tokens=required_int(row, "estimatedTotalTokens"),
        sanitized_prompt_hash=required_str(row, "sanitizedPromptHash"),
        sanitized_response_hash=required_str(row, "sanitizedResponseHash"),
        audit_payload=required_str(row, "auditPayload"),
        created_at=parse_audit_datetime(required_str(row, "createdAt")),
        retention_expires_at=parse_audit_datetime(required_str(row, "retentionExpiresAt")),
    )


def build_sanitized_audit_payload(
    request: PromptGatewayRequest,
    result: PromptGatewayResult,
    sanitized_response: str,
) -> str:
    payload = redact_prompt_text(
        json.dumps(
            {
                "blocked_reasons": result.blocked_reasons,
                "case_id": request.case_id,
                "context_ids": result.context_ids,
                "estimated_input_tokens": result.estimated_input_tokens,
                "estimated_output_tokens": result.estimated_output_tokens,
                "estimated_total_tokens": result.estimated_total_tokens,
                "gateway_allowed": result.allowed,
                "product": request.product,
                "require_human_review": result.require_human_review,
                "response": sanitized_response,
                "tenant_id": request.tenant_id,
                "use_case_id": request.use_case_id,
            },
            sort_keys=True,
        )
    )
    if contains_unredacted_sensitive_value(payload):
        raise ValueError("sanitized audit payload still contains sensitive value")
    return payload


def ensure_safe_prompt_audit_record(record: PromptAuditRecord) -> None:
    if contains_unredacted_sensitive_value(record.audit_payload):
        raise ValueError("prompt audit payload contains unredacted sensitive value")


def contains_unredacted_sensitive_value(text: str) -> bool:
    patterns = (
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        r"\bsk-[A-Za-z0-9_-]+\b",
        r"\bBearer\s+[A-Za-z0-9._-]+\b",
        r"\b(learner_id|principal_id)\s*=\s*(?!\[REDACTED_IDENTIFIER\])[^,\s]+",
    )
    if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
        return True
    return contains_unredacted_phone_like_value(text)


def contains_unredacted_phone_like_value(text: str) -> bool:
    candidates = re.findall(r"\+?\d[\d\s().-]{7,}\d", text)
    return any(is_phone_like_candidate(candidate) for candidate in candidates)


def is_phone_like_candidate(candidate: str) -> bool:
    stripped = candidate.strip()
    if re.fullmatch(r"\d+\.\d+", stripped):
        return False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stripped):
        return False
    return len(re.sub(r"\D", "", stripped)) >= 8


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        raise ValueError(f"prompt audit field {key} must be a non-empty string")
    return value


def required_bool(row: Mapping[str, object], key: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"prompt audit field {key} must be a boolean")
    return value


def required_int(row: Mapping[str, object], key: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"prompt audit field {key} must be an integer")
    return value


def required_str_tuple(row: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = row.get(key)
    if not isinstance(value, list | tuple) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"prompt audit field {key} must be a string array")
    return tuple(value)
