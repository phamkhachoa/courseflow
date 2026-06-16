from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from enterprise_df.catalog import canonical_json
from enterprise_df.contracts import load_yaml
from enterprise_df.ingestion import read_jsonl, write_jsonl
from enterprise_df.source_registry import find_source_entry


PIPELINE_NAME = "source_bridge.local_normalizer.v1"
REPORT_VERSION = 1


@dataclass(frozen=True)
class SourceBridgeResult:
    source_id: str
    canonical_topic: str
    normalized_path: Path
    quarantine_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


def run_source_bridge_preflight(
    root: str | Path,
    source_id: str,
    input_path: str | Path,
    output_dir: str | Path,
    *,
    normalized_at: str | None = None,
    bridge_run_id: str | None = None,
) -> SourceBridgeResult:
    platform_root = Path(root)
    source_entry = find_source_entry(platform_root, source_id)
    if source_entry is None:
        raise KeyError(f"source is not registered: {source_id}")
    source = mapping(source_entry, "source")
    canonical = mapping(source_entry, "canonical")
    bridge = mapping(source_entry, "bridge")
    if bridge.get("required") is not True:
        raise ValueError(f"{source_id}: source bridge is not required")
    if not bridge.get("normalizerId") or bridge.get("normalizerId") == "none":
        raise ValueError(f"{source_id}: bridge.normalizerId is required")
    normalizer = load_normalizer(platform_root, source_entry, str(bridge.get("normalizerId")))

    source_path = Path(input_path)
    target_dir = Path(output_dir)
    normalized_time = normalized_at or utc_now()
    run_id = bridge_run_id or f"source-bridge-{compact_timestamp(normalized_time)}"
    raw_records = read_jsonl(source_path)
    normalized_records: list[dict[str, Any]] = []
    quarantine_records: list[dict[str, Any]] = []
    seen_positions: set[tuple[Any, Any, Any]] = set()

    for ordinal, raw_record in enumerate(raw_records):
        normalized, errors = normalize_record(
            source_entry,
            normalizer,
            raw_record,
            ordinal=ordinal,
            normalized_at=normalized_time,
        )
        if normalized is not None:
            position = (
                normalized.get("sourceTopic"),
                normalized.get("sourcePartition"),
                normalized.get("sourceOffset"),
            )
            if position in seen_positions:
                errors = [*errors, "duplicate source position in bridge input"]
            else:
                seen_positions.add(position)
        if errors or normalized is None:
            quarantine_records.append(
                {
                    "source_id": source_id,
                    "normalizer_id": bridge.get("normalizerId"),
                    "record_ordinal": ordinal,
                    "raw_record_hash": stable_hash(raw_record),
                    "errors": errors or ["normalizer returned no envelope"],
                    "raw_record": raw_record,
                }
            )
            continue
        normalized_records.append(normalized)

    normalized_path = target_dir / "normalized" / f"{source_id}.jsonl"
    quarantine_path = target_dir / "quarantine" / f"{source_id}.jsonl"
    manifest_path = target_dir / "manifests" / f"{source_id}.{run_id}.json"
    normalized_hash = write_jsonl(normalized_path, normalized_records)
    quarantine_hash = write_jsonl(quarantine_path, quarantine_records)
    manifest = {
        "pipeline": PIPELINE_NAME,
        "report_version": REPORT_VERSION,
        "source_id": source_id,
        "product_id": source_entry.get("product"),
        "domain_id": source_entry.get("domain"),
        "normalizer_id": bridge.get("normalizerId"),
        "bridge_mode": bridge.get("mode"),
        "bridge_run_id": run_id,
        "generated_at": normalized_time,
        "source": {
            "raw_topic": source.get("rawTopic"),
            "canonical_topic": canonical.get("topic"),
            "bronze_target": canonical.get("bronzeTarget"),
            "schema_subject": canonical.get("schemaSubject"),
        },
        "input": {
            "path": source_path.as_posix(),
            "content_hash": hash_file(source_path),
            "row_count": len(raw_records),
        },
        "normalized": {
            "path": normalized_path.relative_to(target_dir).as_posix(),
            "row_count": len(normalized_records),
            "content_hash": normalized_hash,
        },
        "quarantine": {
            "path": quarantine_path.relative_to(target_dir).as_posix(),
            "row_count": len(quarantine_records),
            "content_hash": quarantine_hash,
            "reason_counts": reason_counts(quarantine_records),
        },
        "source_positions": source_position_summary(normalized_records),
        "quality_passed": not quarantine_records and bool(normalized_records),
    }
    write_json(manifest_path, manifest)
    return SourceBridgeResult(
        source_id=source_id,
        canonical_topic=str(canonical.get("topic")),
        normalized_path=normalized_path,
        quarantine_path=quarantine_path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def normalize_record(
    source_entry: dict[str, Any],
    normalizer: dict[str, Any],
    raw_record: dict[str, Any],
    *,
    ordinal: int,
    normalized_at: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    source_id = str(source_entry.get("sourceId"))
    canonical = mapping(source_entry, "canonical")
    source = mapping(source_entry, "source")
    topic = str(canonical.get("topic"))
    raw_topic = str(first_present(raw_record, "sourceTopic", "source_topic", "topic", default=source.get("rawTopic")))
    source_partition = first_present(raw_record, "sourcePartition", "source_partition", "partition", default=0)
    source_offset = first_present(raw_record, "sourceOffset", "source_offset", "offset", default=None)
    errors = []
    if source_offset is None:
        errors.append("sourceOffset is required for replay-safe bridge output")
    payload, payload_errors = canonical_payload(normalizer, raw_record)
    errors.extend(payload_errors)
    if errors:
        return None, errors

    occurred_at = str(
        first_present(
            raw_record,
            "occurredAt",
            "occurred_at",
            default=first_configured([raw_record, payload], timestamp_sources(normalizer, "occurredAt")) or normalized_at,
        )
    )
    published_at = str(
        first_present(
            raw_record,
            "publishedAt",
            "published_at",
            default=first_configured([raw_record, payload], timestamp_sources(normalizer, "publishedAt")) or occurred_at,
        )
    )
    event_id = first_present(raw_record, "eventId", "event_id", default=None)
    if not isinstance(event_id, str) or not event_id:
        event_id = str(uuid5(NAMESPACE_URL, canonical_json([source_id, raw_topic, source_partition, source_offset, raw_record])))
    correlation_id = str(first_present(raw_record, "correlationId", "correlation_id", default=f"corr-{stable_id(source_id, raw_topic, source_partition, source_offset)[:16]}"))
    org_id = payload.get("orgId") or raw_record.get("orgId") or raw_record.get("org_id")

    return {
        "eventId": event_id,
        "eventType": topic,
        "eventVersion": 1,
        "productId": source_entry.get("product"),
        "domainId": source_entry.get("domain"),
        "sourceService": source.get("service"),
        "tenantId": raw_record.get("tenantId") or raw_record.get("tenant_id") or org_id,
        "orgId": org_id,
        "occurredAt": occurred_at,
        "publishedAt": published_at,
        "correlationId": correlation_id,
        "causationId": raw_record.get("causationId") or raw_record.get("causation_id"),
        "actor": raw_record.get("actor"),
        "payloadSchema": canonical.get("schemaSubject"),
        "sourceTopic": raw_topic,
        "sourcePartition": source_partition,
        "sourceOffset": source_offset,
        "sourceSnapshotId": raw_record.get("sourceSnapshotId") or raw_record.get("source_snapshot_id"),
        "headers": sanitize_headers(raw_record.get("headers")),
        "payload": payload,
    }, []


def load_normalizer(root: Path, source_entry: dict[str, Any], normalizer_id: str) -> dict[str, Any]:
    product = source_entry.get("product")
    if not isinstance(product, str) or not product:
        raise ValueError("source product is required to load source bridge normalizer")
    normalizer_path = root / "products" / product / "source-bridge-normalizers.yaml"
    if not normalizer_path.is_file():
        raise FileNotFoundError(f"source bridge normalizer manifest is missing: {normalizer_path}")
    manifest = load_yaml(normalizer_path)
    normalizers = manifest.get("normalizers")
    if not isinstance(normalizers, list):
        raise ValueError(f"{normalizer_path}: normalizers must be a list")
    for item in normalizers:
        if not isinstance(item, dict):
            continue
        if item.get("normalizerId") == normalizer_id:
            if item.get("sourceId") != source_entry.get("sourceId"):
                raise ValueError(f"{normalizer_id}: sourceId does not match registered source")
            return item
    raise KeyError(f"source bridge normalizer is not registered: {normalizer_id}")


def canonical_payload(normalizer: dict[str, Any], raw_record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    raw_payload = raw_record.get("payload") if isinstance(raw_record.get("payload"), dict) else raw_record
    payload: dict[str, Any] = {}
    errors: list[str] = []
    fields = mapping(normalizer, "payload")
    for target, spec in fields.items():
        if not isinstance(target, str) or not isinstance(spec, dict):
            continue
        value, field_errors = resolve_payload_value(raw_payload, target, spec)
        errors.extend(field_errors)
        if value is not None:
            payload[target] = value

    required = tuple(string_list(normalizer.get("requiredPayloadFields")))
    errors.extend(required_errors(payload, required))
    for group in normalizer.get("requiredAnyPayloadFields", []):
        keys = string_list(group)
        if keys and not any(payload.get(key) not in (None, "") for key in keys):
            errors.append(f"{' or '.join(keys)} is required")
    return compact(payload), errors


def resolve_payload_value(raw_payload: dict[str, Any], target: str, spec: dict[str, Any]) -> tuple[Any, list[str]]:
    errors: list[str] = []
    value = first_from_sources(raw_payload, string_list(spec.get("source")))
    if value in (None, "") and isinstance(spec.get("fallback"), dict):
        value, fallback_errors = resolve_payload_value(raw_payload, target, spec["fallback"])
        errors.extend(fallback_errors)
    if value in (None, "") and "default" in spec:
        value = spec["default"]
    value, transform_error = apply_transform(value, spec)
    if transform_error:
        errors.append(f"{target}: {transform_error}")
    allowed = string_list(spec.get("allowedValues"))
    if value not in (None, "") and allowed and value not in allowed:
        errors.append(f"{target} must be one of {sorted(allowed)}")
        value = None
    return value, errors


def apply_transform(value: Any, spec: dict[str, Any]) -> tuple[Any, str | None]:
    transform = spec.get("transform")
    if transform in (None, "identity"):
        return value, None
    if transform == "token_hash":
        return token_hash(value), None
    if transform == "safe_metadata":
        return safe_metadata(value), None
    if transform == "upper":
        return value.upper() if isinstance(value, str) else None, None
    if transform == "upper_strip_prefix":
        if not isinstance(value, str):
            return None, None
        normalized = value.upper()
        for prefix in string_list(spec.get("stripPrefixes")):
            upper_prefix = prefix.upper()
            if normalized.startswith(upper_prefix):
                normalized = normalized[len(upper_prefix) :]
        return normalized, None
    return None, f"unsupported transform {transform!r}"


def raw_value(mapping_value: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping_value and mapping_value[key] not in (None, ""):
            return mapping_value[key]
    return default


def first_from_sources(mapping_value: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in mapping_value and mapping_value[key] not in (None, ""):
            return mapping_value[key]
    return None


def first_configured(mappings: list[dict[str, Any]], keys: list[str]) -> Any:
    for mapping_value in mappings:
        value = first_from_sources(mapping_value, keys)
        if value not in (None, ""):
            return value
    return None


def first_present(mapping_value: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping_value:
            return mapping_value[key]
    return default


def compact(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def required_errors(payload: dict[str, Any], keys: tuple[str, ...]) -> list[str]:
    return [f"{key} is required" for key in keys if payload.get(key) in (None, "")]


def token_hash(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return hashlib.sha256(f"enterprise-df-token:{value}".encode("utf-8")).hexdigest()


def safe_metadata(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    safe: dict[str, Any] = {}
    for key, item in value.items():
        if not isinstance(key, str) or key.lower() in {"email", "phone", "name", "token", "authorization"}:
            continue
        if isinstance(item, (str, int, float, bool)) or item is None:
            safe[key] = item
    return safe or None


def sanitize_headers(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        str(key): item
        for key, item in value.items()
        if isinstance(key, str)
        and key.lower().replace("-", "").replace("_", "") not in {"authorization", "cookie", "token", "apikey"}
        and (isinstance(item, (str, int, float, bool)) or item is None)
    } or None


def source_position_summary(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, Any], list[Any]] = {}
    for record in records:
        key = (record.get("sourceTopic"), record.get("sourcePartition"))
        grouped.setdefault(key, []).append(record.get("sourceOffset"))
    summary = []
    for (topic, partition), offsets in sorted(grouped.items(), key=lambda item: (str(item[0][0]), str(item[0][1]))):
        numeric_offsets = [offset for offset in offsets if isinstance(offset, int)]
        summary.append(
            {
                "source_topic": topic,
                "source_partition": partition,
                "min_offset": min(numeric_offsets) if numeric_offsets else None,
                "max_offset": max(numeric_offsets) if numeric_offsets else None,
                "row_count": len(offsets),
            }
        )
    return summary


def reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for error in row.get("errors", []):
            if isinstance(error, str):
                reason = error.split(" is required", 1)[0] if " is required" in error else error
                counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def mapping(source_entry: dict[str, Any], key: str) -> dict[str, Any]:
    value = source_entry.get(key)
    return value if isinstance(value, dict) else {}


def timestamp_sources(normalizer: dict[str, Any], key: str) -> list[str]:
    return string_list(mapping(normalizer, "timestamps").get(key))


def string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")


def hash_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(*parts: Any) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compact_timestamp(value: str) -> str:
    return "".join(char for char in value if char.isdigit())[:14]
