from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.contracts import load_yaml
from enterprise_dp.schema import validate_json_schema


PIPELINE_NAME = "bronze_ingestion.local_jsonl.v1"
SENSITIVE_PAYLOAD_KEYS = {
    "email",
    "first_name",
    "firstname",
    "full_name",
    "fullname",
    "last_name",
    "lastname",
    "learnerid",
    "name",
    "password",
    "phone",
    "profileid",
    "sessionid",
    "studentid",
    "userid",
}
SENSITIVE_HEADER_KEYS = {
    "apikey",
    "authorization",
    "cookie",
    "secret",
    "setcookie",
    "token",
    "xapikey",
}


@dataclass(frozen=True)
class BronzeIngestionResult:
    topic: str
    approved_path: Path
    quarantine_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


def run_bronze_ingestion(
    root: str | Path,
    topic_name: str,
    input_path: str | Path,
    output_dir: str | Path,
    *,
    ingested_at: str | None = None,
    ingest_run_id: str | None = None,
    schema_id: str | None = None,
    source_system: str | None = None,
) -> BronzeIngestionResult:
    platform_root = Path(root)
    source_path = Path(input_path)
    target_dir = Path(output_dir)
    landing_time = ingested_at or _utc_now()
    run_id = ingest_run_id or f"bronze-{_compact_timestamp(landing_time)}"

    topic_contract_path = platform_root / "contracts" / "topics" / f"{topic_name}.yaml"
    topic_contract = load_yaml(topic_contract_path)
    topic = _require_mapping(topic_contract, "topic", topic_contract_path)
    schema = _require_mapping(topic_contract, "schema", topic_contract_path)
    ingestion = _require_mapping(topic_contract, "ingestion", topic_contract_path)
    privacy = _require_mapping(topic_contract, "privacy", topic_contract_path)
    bronze_target = _require_string(ingestion, "bronzeTarget", topic_contract_path)
    bronze_contract = _load_data_product_contract(platform_root, bronze_target)
    bronze_columns = _data_product_columns(bronze_contract)

    envelope_schema_path = platform_root / _require_string(schema, "envelopeSchema", topic_contract_path)
    payload_schema_path = platform_root / _require_string(schema, "payloadSchema", topic_contract_path)
    envelope_schema = _load_json(envelope_schema_path)
    payload_schema = _load_json(payload_schema_path)
    resolved_schema_id = schema_id or f"local:{hash_file(payload_schema_path)}"
    schema_subject = f"{topic_name}-value"

    approved_path = target_dir / "bronze" / f"{bronze_target.removeprefix('bronze.')}.jsonl"
    quarantine_path = target_dir / "quarantine" / f"{topic_name}.jsonl"
    manifest_path = target_dir / "manifests" / f"{bronze_target.removeprefix('bronze.')}.{run_id}.json"
    existing_rows = read_jsonl(approved_path) if approved_path.exists() else []
    existing_source_hashes = _source_hashes_by_position(existing_rows)

    approved_rows: list[dict[str, Any]] = list(existing_rows)
    quarantine_rows: list[dict[str, Any]] = []
    seen_source_positions: set[tuple[str, Any, Any]] = set()
    new_approved_count = 0
    replay_skipped_count = 0
    records = read_jsonl(source_path)

    for ordinal, record in enumerate(records):
        source_position = _source_position(record, topic_name, ordinal)
        reasons, errors = _record_errors(
            record=record,
            topic=topic,
            privacy=privacy,
            envelope_schema=envelope_schema,
            payload_schema=payload_schema,
            topic_name=topic_name,
            source_position=source_position,
            seen_source_positions=seen_source_positions,
            existing_source_hashes=existing_source_hashes,
        )
        if reasons:
            quarantine_rows.append(
                _quarantine_row(
                    record=record,
                    ordinal=ordinal,
                    topic_name=topic_name,
                    source_position=source_position,
                    reason_codes=reasons,
                    errors=errors,
                )
            )
            continue
        source_hash = _source_record_hash(source_position, record)
        if existing_source_hashes.get(source_position) == source_hash:
            replay_skipped_count += 1
            continue
        seen_source_positions.add(source_position)
        approved_rows.append(
            _bronze_row(
                record=record,
                topic=topic,
                topic_name=topic_name,
                bronze_columns=bronze_columns,
                source_position=source_position,
                ordinal=ordinal,
                ingested_at=landing_time,
                ingest_run_id=run_id,
                schema_subject=schema_subject,
                schema_id=resolved_schema_id,
                source_system=source_system,
            )
        )
        existing_source_hashes[source_position] = source_hash
        new_approved_count += 1

    approved_hash = write_jsonl(approved_path, approved_rows)
    quarantine_hash = write_jsonl(quarantine_path, quarantine_rows)
    manifest = _manifest(
        topic_name=topic_name,
        bronze_target=bronze_target,
        product_id=str(topic.get("product")),
        input_path=source_path,
        approved_path=approved_path,
        quarantine_path=quarantine_path,
        output_dir=target_dir,
        approved_rows=approved_rows,
        quarantine_rows=quarantine_rows,
        new_approved_count=new_approved_count,
        replay_skipped_count=replay_skipped_count,
        approved_hash=approved_hash,
        quarantine_hash=quarantine_hash,
        ingested_at=landing_time,
        ingest_run_id=run_id,
        schema_subject=schema_subject,
        schema_id=resolved_schema_id,
    )
    write_manifest(manifest_path, manifest)

    return BronzeIngestionResult(
        topic=topic_name,
        approved_path=approved_path,
        quarantine_path=quarantine_path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL record") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: JSONL record must be an object")
            records.append(record)
    return records


def write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> str:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(f"{canonical_json(record)}\n" for record in records)
    target.write_text(content, encoding="utf-8")
    return content_hash(content)


def write_manifest(path: str | Path, manifest: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def content_hash(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _record_errors(
    *,
    record: dict[str, Any],
    topic: dict[str, Any],
    privacy: dict[str, Any],
    envelope_schema: dict[str, Any],
    payload_schema: dict[str, Any],
    topic_name: str,
    source_position: tuple[str, Any, Any],
    seen_source_positions: set[tuple[str, Any, Any]],
    existing_source_hashes: dict[tuple[str, Any, Any], str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    reasons: list[str] = []
    errors: list[str] = []

    envelope_errors = validate_json_schema(record, envelope_schema)
    payload = record.get("payload")
    payload_errors = validate_json_schema(payload, payload_schema) if isinstance(payload, dict) else ("$.payload must be object",)
    if envelope_errors or payload_errors:
        reasons.append("SCHEMA_INVALID")
        errors.extend(envelope_errors)
        errors.extend(payload_errors)

    product_id = record.get("productId")
    if product_id != topic.get("product"):
        reasons.append("PRODUCT_MISMATCH")
        errors.append(f"productId {product_id!r} does not match topic product {topic.get('product')!r}")

    source_service = record.get("sourceService")
    source_services = topic.get("sourceServices")
    if isinstance(source_services, list) and source_service not in source_services:
        reasons.append("SOURCE_SERVICE_NOT_ALLOWED")
        errors.append(f"sourceService {source_service!r} is not allowed for {topic_name}")

    if _source_position_missing(source_position):
        reasons.append("SOURCE_POSITION_MISSING")
        errors.append("sourceTopic, sourcePartition and sourceOffset are required for approved Bronze")
    elif source_position in seen_source_positions:
        reasons.append("DUPLICATE_SOURCE_POSITION")
        errors.append(f"duplicate source position {source_position!r}")
    elif source_position in existing_source_hashes:
        source_hash = _source_record_hash(source_position, record)
        if existing_source_hashes[source_position] != source_hash:
            reasons.append("HASH_MISMATCH")
            errors.append(f"source position {source_position!r} was already landed with a different hash")

    if _contains_sensitive_payload_key(payload):
        reasons.append("PII_POLICY_VIOLATION")
        errors.append("payload contains a forbidden direct identifier key")
    subject_key_errors = _subject_key_errors(payload, privacy)
    if subject_key_errors:
        reasons.append("SUBJECT_KEY_MISSING")
        errors.extend(subject_key_errors)
    if _contains_sensitive_header_key(record.get("headers")):
        reasons.append("PII_POLICY_VIOLATION")
        errors.append("headers contain a forbidden secret key")

    return tuple(dict.fromkeys(reasons)), tuple(errors)


def _subject_key_errors(payload: object, privacy: dict[str, Any]) -> list[str]:
    if not isinstance(payload, dict):
        return []
    errors: list[str] = []
    subject_keys = privacy.get("subjectKeys")
    if not isinstance(subject_keys, list):
        return errors
    for index, spec in enumerate(subject_keys):
        if not isinstance(spec, dict) or spec.get("required") is not True:
            continue
        topic_path = spec.get("topicPath")
        if not isinstance(topic_path, str) or not topic_path.startswith("$.payload."):
            continue
        field_name = topic_path.removeprefix("$.payload.")
        value = payload.get(field_name)
        if value in (None, ""):
            errors.append(f"required subject key {spec.get('name') or index} is missing at {topic_path}")
    return errors


def _bronze_row(
    *,
    record: dict[str, Any],
    topic: dict[str, Any],
    topic_name: str,
    bronze_columns: list[str],
    source_position: tuple[str, Any, Any],
    ordinal: int,
    ingested_at: str,
    ingest_run_id: str,
    schema_subject: str,
    schema_id: str,
    source_system: str | None,
) -> dict[str, Any]:
    payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
    occurred_at = payload.get("occurredAt") or record.get("occurredAt")
    product_id = record.get("productId")
    source_topic, source_partition, source_offset = source_position
    base = {
        "product_id": product_id,
        "domain_id": record.get("domainId") or topic.get("domain"),
        "event_id": record.get("eventId"),
        "event_type": payload.get("eventType") or record.get("eventType"),
        "envelope_event_type": record.get("eventType"),
        "event_version": record.get("eventVersion"),
        "source_service": record.get("sourceService"),
        "tenant_id": record.get("tenantId"),
        "org_id": payload.get("orgId") or record.get("orgId"),
        "learner_id_hash": payload.get("learnerIdHash"),
        "session_id_hash": payload.get("sessionIdHash"),
        "course_id": payload.get("courseId"),
        "related_course_id": payload.get("relatedCourseId"),
        "occurred_at": occurred_at,
        "published_at": record.get("publishedAt"),
        "ingested_at": ingested_at,
        "source_system": source_system or str(product_id),
        "source_topic": source_topic,
        "source_partition": source_partition,
        "source_offset": source_offset,
        "source_snapshot_id": record.get("sourceSnapshotId"),
        "source_record_key": record.get("eventId") or f"{topic_name}:{ordinal}",
        "source_record_hash_sha256": content_hash(canonical_json({"source_position": source_position, "record": record})),
        "payload_hash_sha256": content_hash(canonical_json(payload)),
        "schema_subject": schema_subject,
        "schema_id": schema_id,
        "raw_headers": record.get("headers") or {},
        "raw_payload": payload,
        "ingest_run_id": ingest_run_id,
        "event_date": _date_part(occurred_at),
        "ingest_date": _date_part(ingested_at),
    }
    for key, value in payload.items():
        snake_key = _camel_to_snake(key)
        base.setdefault(snake_key, value)

    row = {column: base.get(column) for column in bronze_columns}
    for key, value in base.items():
        row.setdefault(key, value)
    return row


def _quarantine_row(
    *,
    record: dict[str, Any],
    ordinal: int,
    topic_name: str,
    source_position: tuple[str, Any, Any],
    reason_codes: tuple[str, ...],
    errors: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "topic": topic_name,
        "record_ordinal": ordinal,
        "event_id": record.get("eventId"),
        "product_id": record.get("productId"),
        "source_service": record.get("sourceService"),
        "source_topic": source_position[0],
        "source_partition": source_position[1],
        "source_offset": source_position[2],
        "reason_codes": list(reason_codes),
        "errors": list(errors),
        "raw_record_hash_sha256": content_hash(canonical_json(record)),
        "raw_record": record,
    }


def _manifest(
    *,
    topic_name: str,
    bronze_target: str,
    product_id: str,
    input_path: Path,
    approved_path: Path,
    quarantine_path: Path,
    output_dir: Path,
    approved_rows: list[dict[str, Any]],
    quarantine_rows: list[dict[str, Any]],
    new_approved_count: int,
    replay_skipped_count: int,
    approved_hash: str,
    quarantine_hash: str,
    ingested_at: str,
    ingest_run_id: str,
    schema_subject: str,
    schema_id: str,
) -> dict[str, Any]:
    return {
        "pipeline": PIPELINE_NAME,
        "product_id": product_id,
        "topic": topic_name,
        "bronze_target": bronze_target,
        "ingested_at": ingested_at,
        "ingest_run_id": ingest_run_id,
        "schema_subject": schema_subject,
        "schema_id": schema_id,
        "input": {
            "path": input_path.as_posix(),
            "content_hash": hash_file(input_path),
        },
        "approved": {
            "path": approved_path.relative_to(output_dir).as_posix(),
            "row_count": len(approved_rows),
            "new_row_count": new_approved_count,
            "replay_skipped_count": replay_skipped_count,
            "content_hash": approved_hash,
        },
        "quarantine": {
            "path": quarantine_path.relative_to(output_dir).as_posix(),
            "row_count": len(quarantine_rows),
            "content_hash": quarantine_hash,
            "reason_counts": _reason_counts(quarantine_rows),
        },
        "source_positions": _source_position_summary(approved_rows),
        "quality_passed": not quarantine_rows,
    }


def _source_position(record: dict[str, Any], topic_name: str, ordinal: int) -> tuple[str, Any, Any]:
    topic = _first_present(record, "sourceTopic", "source_topic", "topic", default=None)
    partition = _first_present(record, "sourcePartition", "source_partition", "partition", default=None)
    offset = _first_present(record, "sourceOffset", "source_offset", "offset", default=None)
    return str(topic) if topic is not None else topic_name, partition, offset


def _source_position_missing(source_position: tuple[str, Any, Any]) -> bool:
    topic, partition, offset = source_position
    return not topic or partition is None or offset is None


def _source_record_hash(source_position: tuple[str, Any, Any], record: dict[str, Any]) -> str:
    return content_hash(canonical_json({"source_position": source_position, "record": record}))


def _source_hashes_by_position(rows: list[dict[str, Any]]) -> dict[tuple[str, Any, Any], str]:
    hashes: dict[tuple[str, Any, Any], str] = {}
    for row in rows:
        position = (row.get("source_topic"), row.get("source_partition"), row.get("source_offset"))
        source_hash = row.get("source_record_hash_sha256")
        if not _source_position_missing(position) and isinstance(source_hash, str):
            hashes[position] = source_hash
    return hashes


def _source_position_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, Any], list[Any]] = {}
    for row in rows:
        key = (row.get("source_topic"), row.get("source_partition"))
        grouped.setdefault(key, []).append(row.get("source_offset"))
    summary: list[dict[str, Any]] = []
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


def _reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for reason in row.get("reason_codes", []):
            if isinstance(reason, str):
                counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _data_product_columns(contract: dict[str, Any]) -> list[str]:
    columns = contract.get("schema", {}).get("columns")
    if not isinstance(columns, list):
        return []
    names: list[str] = []
    for column in columns:
        if isinstance(column, dict) and isinstance(column.get("name"), str):
            names.append(column["name"])
    return names


def _load_data_product_contract(root: Path, data_product_name: str) -> dict[str, Any]:
    candidates = sorted((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))
    if not candidates:
        raise FileNotFoundError(f"data product contract does not exist: {data_product_name}")
    return load_yaml(candidates[0])


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _require_mapping(mapping: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: {key} must be an object")
    return value


def _require_string(mapping: dict[str, Any], key: str, path: Path) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: {key} must be a non-empty string")
    return value


def _first_present(mapping: dict[str, Any], *keys: str, default: Any) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


def _contains_sensitive_payload_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = _normalize_sensitive_key(key)
            if normalized in SENSITIVE_PAYLOAD_KEYS:
                return True
            if _contains_sensitive_payload_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_payload_key(item) for item in value)
    return False


def _contains_sensitive_header_key(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(_normalize_sensitive_key(key) in SENSITIVE_HEADER_KEYS for key in value)


def _normalize_sensitive_key(value: str) -> str:
    return value.replace("-", "").replace("_", "").replace(" ", "").lower()


def _camel_to_snake(value: str) -> str:
    output: list[str] = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            output.append("_")
        output.append(char.lower())
    return "".join(output)


def _date_part(value: object) -> str | None:
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return None


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _compact_timestamp(value: str) -> str:
    return (
        value.replace("-", "")
        .replace(":", "")
        .replace(".", "")
        .replace("+", "")
        .replace("Z", "z")
    )
