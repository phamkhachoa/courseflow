from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.pipelines.base import PipelineRunRequest, PipelineSpec


SUPPORT_TOPIC = "customer.support_case.changed.v1"
PIPELINE_FROM_BRONZE_NAME = "support.sla.from_approved_bronze.v1"
PRODUCT_ID = "support-platform"

VALID_CHANNELS = {"WEB", "EMAIL", "CHAT", "PHONE", "API", "SOCIAL", "INTERNAL"}
VALID_PRIORITIES = {"LOW", "NORMAL", "HIGH", "URGENT", "CRITICAL"}
VALID_CASE_TYPES = {"INCIDENT", "QUESTION", "BILLING", "TECHNICAL", "ACCOUNT", "FEATURE_REQUEST", "OTHER"}
VALID_CASE_STATUSES = {"OPEN", "PENDING", "RESOLVED", "CLOSED", "ESCALATED"}
VALID_SLA_HEALTH_STATUSES = {"HEALTHY", "WATCH", "BREACH"}


@dataclass(frozen=True)
class LayerSnapshot:
    name: str
    path: Path
    row_count: int
    content_hash: str
    quality_passed: bool
    quality_errors: tuple[str, ...]

    def as_manifest_entry(self, output_dir: Path) -> dict[str, Any]:
        try:
            relative_path = self.path.relative_to(output_dir).as_posix()
        except ValueError:
            relative_path = self.path.as_posix()
        return {
            "path": relative_path,
            "row_count": self.row_count,
            "content_hash": self.content_hash,
            "quality_passed": self.quality_passed,
            "quality_errors": list(self.quality_errors),
        }


@dataclass(frozen=True)
class SupportPipelineResult:
    snapshot_id: str
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class SupportSlaRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_FROM_BRONZE_NAME,
        name="Support SLA from approved Bronze",
        product=PRODUCT_ID,
        domain="customer",
        use_cases=("customer-support-experience-intelligence",),
        input_kind="approved_bronze_jsonl",
        output_data_products=(
            "silver.support_case",
            "gold.support_sla_daily",
        ),
        description="Build Silver support case state and Gold daily support SLA aggregates from approved Bronze support events.",
        input_topics=(SUPPORT_TOPIC,),
        input_data_products=("bronze.events_support_case_changed",),
        primary_output="gold.support_sla_daily",
        evidence_capabilities=(
            "schema_registry",
            "access_policy",
            "catalog_lineage",
            "release_gates",
        ),
        optional_options=("upstream_manifest_path", "snapshot_id", "built_at"),
    )

    def run(self, request: PipelineRunRequest) -> SupportPipelineResult:
        return run_support_sla_from_bronze(
            request.input_path,
            request.output_dir,
            upstream_manifest_path=request.options.get("upstream_manifest_path"),
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
        )


def run_support_sla_from_bronze(
    bronze_path: str | Path,
    output_dir: str | Path,
    *,
    upstream_manifest_path: str | Path | None = None,
    snapshot_id: str | None = None,
    built_at: str | None = None,
) -> SupportPipelineResult:
    source_path = Path(bronze_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    resolved_snapshot_id = snapshot_id or f"support-sla-{_compact_timestamp(build_time)}"
    upstream_manifest = load_manifest(upstream_manifest_path) if upstream_manifest_path else None

    bronze_rows = read_jsonl(source_path)
    silver_rows = build_silver_rows(bronze_rows, snapshot_id=resolved_snapshot_id)
    gold_rows = build_gold_rows(
        silver_rows,
        snapshot_id=resolved_snapshot_id,
        built_at=build_time,
    )

    bronze_errors = validate_bronze_rows(bronze_rows)
    bronze_snapshot = LayerSnapshot(
        name="bronze.events_support_case_changed",
        path=source_path,
        row_count=len(bronze_rows),
        content_hash=hash_file(source_path),
        quality_passed=not bronze_errors,
        quality_errors=bronze_errors,
    )
    silver_snapshot = write_layer_snapshot(
        "silver.support_case",
        target_dir / "silver" / "support_case.jsonl",
        silver_rows,
        quality_errors=validate_silver_rows(silver_rows),
    )
    gold_snapshot = write_layer_snapshot(
        "gold.support_sla_daily",
        target_dir / "gold" / "support_sla_daily.jsonl",
        gold_rows,
        quality_errors=validate_gold_rows(gold_rows),
    )

    layer_snapshots = (bronze_snapshot, silver_snapshot, gold_snapshot)
    manifest = build_manifest(
        snapshot_id=resolved_snapshot_id,
        generated_at=build_time,
        input_path=source_path,
        output_dir=target_dir,
        layer_snapshots=layer_snapshots,
        upstream_manifest_path=Path(upstream_manifest_path) if upstream_manifest_path else None,
        upstream_manifest=upstream_manifest,
    )
    manifest_path = target_dir / "manifests" / f"support_sla.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return SupportPipelineResult(
        snapshot_id=resolved_snapshot_id,
        bronze_path=source_path,
        silver_path=silver_snapshot.path,
        gold_path=gold_snapshot.path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def build_silver_rows(bronze_rows: list[dict[str, Any]], *, snapshot_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bronze in bronze_rows:
        first_response_minutes = _int_value(bronze.get("first_response_minutes"))
        resolution_minutes = _int_value(bronze.get("resolution_minutes"))
        first_response_target = _int_value(bronze.get("first_response_sla_target_minutes"))
        resolution_target = _int_value(bronze.get("resolution_sla_target_minutes"))
        rows.append(
            {
                "support_case_state_id": stable_id(
                    "support-case-state",
                    snapshot_id,
                    bronze.get("event_id"),
                    bronze.get("case_id"),
                ),
                "product_id": bronze.get("product_id"),
                "org_id": bronze.get("org_id"),
                "account_id": bronze.get("account_id"),
                "customer_id_hash": bronze.get("customer_id_hash"),
                "case_id": bronze.get("case_id"),
                "channel": bronze.get("channel"),
                "priority": bronze.get("priority"),
                "case_type": bronze.get("case_type"),
                "case_status": bronze.get("case_status"),
                "created_at": bronze.get("created_at"),
                "first_response_at": bronze.get("first_response_at"),
                "resolved_at": bronze.get("resolved_at"),
                "first_response_sla_target_minutes": first_response_target,
                "resolution_sla_target_minutes": resolution_target,
                "first_response_minutes": first_response_minutes,
                "resolution_minutes": resolution_minutes,
                "first_response_sla_breached": first_response_minutes > first_response_target,
                "resolution_sla_breached": resolution_minutes > resolution_target,
                "reopened_count": _int_value(bronze.get("reopened_count")),
                "escalation_count": _int_value(bronze.get("escalation_count")),
                "satisfaction_score": _nullable_int_value(bronze.get("satisfaction_score")),
                "changed_at": bronze.get("changed_at") or bronze.get("occurred_at"),
                "source_event_id": bronze.get("event_id"),
                "source_record_hash_sha256": bronze.get("source_record_hash_sha256"),
            }
        )
    return rows


def build_gold_rows(
    silver_rows: list[dict[str, Any]],
    *,
    snapshot_id: str,
    built_at: str,
) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in silver_rows:
        report_date = _date_part(row.get("created_at")) or _date_part(row.get("changed_at")) or _date_part(built_at)
        key = (
            row.get("product_id"),
            row.get("org_id"),
            report_date,
            row.get("account_id"),
            row.get("customer_id_hash"),
            row.get("channel"),
            row.get("priority"),
        )
        groups.setdefault(key, []).append(row)

    gold_rows: list[dict[str, Any]] = []
    for key, rows in sorted(groups.items(), key=lambda item: tuple("" if part is None else str(part) for part in item[0])):
        product_id, org_id, report_date, account_id, customer_id_hash, channel, priority = key
        case_count = len(rows)
        open_case_count = sum(1 for row in rows if row.get("case_status") in {"OPEN", "PENDING", "ESCALATED"})
        resolved_case_count = sum(1 for row in rows if row.get("case_status") in {"RESOLVED", "CLOSED"})
        first_response_breaches = sum(1 for row in rows if row.get("first_response_sla_breached") is True)
        resolution_breaches = sum(1 for row in rows if row.get("resolution_sla_breached") is True)
        reopened_count = sum(1 for row in rows if _int_value(row.get("reopened_count")) > 0)
        escalated_count = sum(1 for row in rows if _int_value(row.get("escalation_count")) > 0)
        satisfaction_scores = [
            _int_value(row.get("satisfaction_score"))
            for row in rows
            if row.get("satisfaction_score") is not None
        ]
        breach_count = first_response_breaches + resolution_breaches
        gold_rows.append(
            {
                "product_id": product_id,
                "dataset_snapshot_id": snapshot_id,
                "support_sla_id": stable_id(
                    "support-sla-daily",
                    snapshot_id,
                    org_id,
                    report_date,
                    account_id,
                    customer_id_hash,
                    channel,
                    priority,
                ),
                "org_id": org_id,
                "report_date": report_date,
                "account_id": account_id,
                "customer_id_hash": customer_id_hash,
                "channel": channel,
                "priority": priority,
                "case_count": case_count,
                "open_case_count": open_case_count,
                "resolved_case_count": resolved_case_count,
                "first_response_sla_breached_count": first_response_breaches,
                "resolution_sla_breached_count": resolution_breaches,
                "reopened_case_count": reopened_count,
                "escalated_case_count": escalated_count,
                "average_first_response_minutes": _average(row.get("first_response_minutes") for row in rows),
                "average_resolution_minutes": _average(row.get("resolution_minutes") for row in rows),
                "csat_response_count": len(satisfaction_scores),
                "average_satisfaction_score": _average(satisfaction_scores) if satisfaction_scores else None,
                "sla_health_status": sla_health_status(breach_count=breach_count, case_count=case_count),
                "built_at": built_at,
                "quality_passed": True,
            }
        )
    return gold_rows


def sla_health_status(*, breach_count: int, case_count: int) -> str:
    if case_count <= 0 or breach_count <= 0:
        return "HEALTHY"
    if breach_count / case_count >= 0.5:
        return "BREACH"
    return "WATCH"


def validate_bronze_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("bronze snapshot must contain at least one support case event")
        return tuple(errors)
    for column in (
        "event_id",
        "product_id",
        "tenant_id",
        "org_id",
        "case_id",
        "account_id",
        "customer_id_hash",
        "case_status",
        "priority",
        "channel",
        "source_record_hash_sha256",
    ):
        _require_not_null(errors, rows, column, f"bronze {column}_not_null")
    _require_allowed_values(errors, rows, "event_type", {"SUPPORT_CASE_CHANGED"}, "bronze event_type_allowed")
    _require_allowed_values(errors, rows, "channel", VALID_CHANNELS, "bronze channel_allowed")
    _require_allowed_values(errors, rows, "priority", VALID_PRIORITIES, "bronze priority_allowed")
    _require_allowed_values(errors, rows, "case_type", VALID_CASE_TYPES, "bronze case_type_allowed")
    _require_allowed_values(errors, rows, "case_status", VALID_CASE_STATUSES, "bronze case_status_allowed")
    return tuple(errors)


def validate_silver_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("silver snapshot must contain at least one support case")
        return tuple(errors)
    for column in (
        "support_case_state_id",
        "product_id",
        "org_id",
        "case_id",
        "account_id",
        "customer_id_hash",
        "created_at",
        "changed_at",
        "source_event_id",
    ):
        _require_not_null(errors, rows, column, f"silver {column}_not_null")
    _require_unique(errors, rows, ("support_case_state_id",), "silver support_case_state_id_unique")
    _require_allowed_values(errors, rows, "channel", VALID_CHANNELS, "silver channel_allowed")
    _require_allowed_values(errors, rows, "priority", VALID_PRIORITIES, "silver priority_allowed")
    _require_allowed_values(errors, rows, "case_type", VALID_CASE_TYPES, "silver case_type_allowed")
    _require_allowed_values(errors, rows, "case_status", VALID_CASE_STATUSES, "silver case_status_allowed")
    return tuple(errors)


def validate_gold_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("gold snapshot must contain at least one support SLA row")
        return tuple(errors)
    for column in (
        "dataset_snapshot_id",
        "support_sla_id",
        "org_id",
        "report_date",
        "channel",
        "priority",
        "account_id",
        "customer_id_hash",
        "case_count",
        "sla_health_status",
        "built_at",
    ):
        _require_not_null(errors, rows, column, f"gold {column}_not_null")
    _require_allowed_values(errors, rows, "sla_health_status", VALID_SLA_HEALTH_STATUSES, "gold sla_health_status_allowed")
    _require_unique(
        errors,
        rows,
        ("dataset_snapshot_id", "org_id", "report_date", "account_id", "customer_id_hash", "channel", "priority"),
        "gold support_sla_daily_unique",
    )
    return tuple(errors)


def write_layer_snapshot(
    name: str,
    path: Path,
    rows: list[dict[str, Any]],
    *,
    quality_errors: tuple[str, ...],
) -> LayerSnapshot:
    content_hash_value = write_jsonl(path, rows)
    return LayerSnapshot(
        name=name,
        path=path,
        row_count=len(rows),
        content_hash=content_hash_value,
        quality_passed=not quality_errors,
        quality_errors=quality_errors,
    )


def build_manifest(
    *,
    snapshot_id: str,
    generated_at: str,
    input_path: Path,
    output_dir: Path,
    layer_snapshots: tuple[LayerSnapshot, ...],
    upstream_manifest_path: Path | None = None,
    upstream_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    layers = {
        snapshot.name: snapshot.as_manifest_entry(output_dir)
        for snapshot in layer_snapshots
    }
    gold = layers["gold.support_sla_daily"]
    upstream_quality_passed = upstream_manifest is None or upstream_manifest.get("quality_passed") is True
    quality_passed = upstream_quality_passed and all(snapshot.quality_passed for snapshot in layer_snapshots)
    source_positions = upstream_manifest.get("source_positions", []) if upstream_manifest else []
    input_entry: dict[str, Any] = {
        "path": input_path.as_posix(),
        "content_hash": hash_file(input_path),
    }
    if upstream_manifest_path:
        input_entry["upstream_manifest_path"] = upstream_manifest_path.as_posix()
        input_entry["upstream_manifest_hash"] = hash_file(upstream_manifest_path)
    return {
        "pipeline": PIPELINE_FROM_BRONZE_NAME,
        "product_id": PRODUCT_ID,
        "snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "input": input_entry,
        "layers": layers,
        "lineage_edges": layer_lineage_edges(layer_snapshots),
        "source_positions": source_positions,
        "upstream_quality_passed": upstream_quality_passed,
        "row_count": gold["row_count"],
        "content_hash": gold["content_hash"],
        "quality_passed": quality_passed,
    }


def layer_lineage_edges(layer_snapshots: tuple[LayerSnapshot, ...]) -> list[dict[str, str]]:
    names = [snapshot.name for snapshot in layer_snapshots]
    return [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": source,
            "target": target,
        }
        for source, target in zip(names, names[1:])
    ]


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


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a JSON object")
    return data


def stable_id(*parts: object) -> str:
    value = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _average(values: Any) -> float:
    numbers = [_int_value(value) for value in values]
    return round(sum(numbers) / len(numbers), 2) if numbers else 0.0


def _int_value(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _nullable_int_value(value: object) -> int | None:
    if value is None:
        return None
    return _int_value(value)


def _require_not_null(
    errors: list[str],
    rows: list[dict[str, Any]],
    column: str,
    check_name: str,
) -> None:
    for index, row in enumerate(rows):
        if row.get(column) is None:
            errors.append(f"{check_name}: row {index} has null {column}")


def _require_allowed_values(
    errors: list[str],
    rows: list[dict[str, Any]],
    column: str,
    allowed_values: set[str],
    check_name: str,
) -> None:
    for index, row in enumerate(rows):
        if row.get(column) not in allowed_values:
            errors.append(f"{check_name}: row {index} has invalid {column}={row.get(column)!r}")


def _require_unique(
    errors: list[str],
    rows: list[dict[str, Any]],
    columns: tuple[str, ...],
    check_name: str,
) -> None:
    seen: set[tuple[Any, ...]] = set()
    for index, row in enumerate(rows):
        key = tuple(row.get(column) for column in columns)
        if key in seen:
            errors.append(f"{check_name}: row {index} duplicates {columns}={key!r}")
            continue
        seen.add(key)


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
