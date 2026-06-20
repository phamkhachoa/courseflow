from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.pipelines.base import PipelineRunRequest, PipelineSpec


RECOMMENDATION_TOPIC = "recommendation.tracking.v1"
PIPELINE_NAME = "recommendation.local_jsonl.v1"
PIPELINE_FROM_BRONZE_NAME = "recommendation.from_approved_bronze.v1"
PRODUCT_ID = "lms-courseflow"

ALLOWED_EVENT_TYPES = {"IMPRESSION", "CLICK", "ENROLLMENT"}
ACTIVITY_TYPES = {
    "IMPRESSION": "RECOMMENDATION_IMPRESSION",
    "CLICK": "RECOMMENDATION_CLICK",
    "ENROLLMENT": "RECOMMENDATION_ENROLLMENT",
}
EVENT_WEIGHTS = {
    "IMPRESSION": 0.1,
    "CLICK": 1.0,
    "ENROLLMENT": 3.0,
}
SENSITIVE_PAYLOAD_KEYS = {
    "email",
    "first_name",
    "firstname",
    "full_name",
    "fullname",
    "last_name",
    "lastname",
    "name",
    "password",
    "phone",
}


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
class PipelineResult:
    snapshot_id: str
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class RecommendationFromBronzeRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_FROM_BRONZE_NAME,
        name="Recommendation from approved Bronze",
        product=PRODUCT_ID,
        domain="recommendation",
        use_cases=("ml-feature-governance",),
        input_kind="approved_bronze_jsonl",
        output_data_products=("silver.learner_activity", "gold.recsys_interactions"),
        description="Build Silver learner activity and Gold recommendation interaction snapshots from approved Bronze.",
        input_topics=(RECOMMENDATION_TOPIC,),
        input_data_products=("bronze.events_recommendation_tracking",),
        primary_output="gold.recsys_interactions",
        evidence_capabilities=(
            "schema_registry",
            "access_policy",
            "catalog_lineage",
            "release_gates",
        ),
        optional_options=("upstream_manifest_path", "snapshot_id", "built_at"),
    )

    def run(self, request: PipelineRunRequest) -> PipelineResult:
        return run_recommendation_pipeline_from_bronze(
            request.input_path,
            request.output_dir,
            upstream_manifest_path=request.options.get("upstream_manifest_path"),
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
        )


class RecommendationRawJsonlRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_NAME,
        name="Recommendation raw JSONL local pipeline",
        product=PRODUCT_ID,
        domain="recommendation",
        use_cases=("ml-feature-governance",),
        input_kind="raw_event_jsonl",
        output_data_products=(
            "bronze.events_recommendation_tracking",
            "silver.learner_activity",
            "gold.recsys_interactions",
        ),
        description="Build local Bronze, Silver and Gold recommendation snapshots from raw event JSONL.",
        input_topics=(RECOMMENDATION_TOPIC,),
        primary_output="gold.recsys_interactions",
        evidence_capabilities=(
            "schema_registry",
            "access_policy",
            "catalog_lineage",
            "release_gates",
        ),
        optional_options=("snapshot_id", "built_at", "ingested_at"),
    )

    def run(self, request: PipelineRunRequest) -> PipelineResult:
        return run_recommendation_pipeline(
            request.input_path,
            request.output_dir,
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
            ingested_at=request.options.get("ingested_at"),
        )


def run_recommendation_pipeline(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    snapshot_id: str | None = None,
    built_at: str | None = None,
    ingested_at: str | None = None,
) -> PipelineResult:
    """Build local Bronze, Silver and Gold recommendation JSONL snapshots."""

    source_path = Path(input_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    ingest_time = ingested_at or build_time
    resolved_snapshot_id = snapshot_id or f"recsys-{_compact_timestamp(build_time)}"

    envelopes = read_jsonl(source_path)
    bronze_rows = build_bronze_rows(envelopes, ingested_at=ingest_time)
    silver_rows = build_silver_rows(bronze_rows)
    gold_rows = build_gold_rows(
        silver_rows,
        snapshot_id=resolved_snapshot_id,
        built_at=build_time,
    )

    bronze_snapshot = write_layer_snapshot(
        "bronze.events_recommendation_tracking",
        target_dir / "bronze" / "events_recommendation_tracking.jsonl",
        bronze_rows,
        quality_errors=validate_bronze_rows(bronze_rows),
    )
    silver_snapshot = write_layer_snapshot(
        "silver.learner_activity",
        target_dir / "silver" / "learner_activity.jsonl",
        silver_rows,
        quality_errors=validate_silver_rows(silver_rows),
    )
    gold_snapshot = write_layer_snapshot(
        "gold.recsys_interactions",
        target_dir / "gold" / "recsys_interactions.jsonl",
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
    )
    manifest_path = target_dir / "manifests" / f"recsys_interactions.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return PipelineResult(
        snapshot_id=resolved_snapshot_id,
        bronze_path=bronze_snapshot.path,
        silver_path=silver_snapshot.path,
        gold_path=gold_snapshot.path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def run_recommendation_pipeline_from_bronze(
    bronze_path: str | Path,
    output_dir: str | Path,
    *,
    upstream_manifest_path: str | Path | None = None,
    snapshot_id: str | None = None,
    built_at: str | None = None,
) -> PipelineResult:
    """Build Silver and Gold recommendation outputs from approved Bronze rows."""

    source_path = Path(bronze_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    resolved_snapshot_id = snapshot_id or f"recsys-{_compact_timestamp(build_time)}"
    upstream_manifest = load_manifest(upstream_manifest_path) if upstream_manifest_path else None

    bronze_rows = read_jsonl(source_path)
    silver_rows = build_silver_rows(bronze_rows)
    gold_rows = build_gold_rows(
        silver_rows,
        snapshot_id=resolved_snapshot_id,
        built_at=build_time,
    )

    bronze_quality_errors = validate_bronze_rows(bronze_rows)
    bronze_snapshot = LayerSnapshot(
        name="bronze.events_recommendation_tracking",
        path=source_path,
        row_count=len(bronze_rows),
        content_hash=hash_file(source_path),
        quality_passed=not bronze_quality_errors,
        quality_errors=bronze_quality_errors,
    )
    silver_snapshot = write_layer_snapshot(
        "silver.learner_activity",
        target_dir / "silver" / "learner_activity.jsonl",
        silver_rows,
        quality_errors=validate_silver_rows(silver_rows),
    )
    gold_snapshot = write_layer_snapshot(
        "gold.recsys_interactions",
        target_dir / "gold" / "recsys_interactions.jsonl",
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
        pipeline=PIPELINE_FROM_BRONZE_NAME,
        upstream_manifest_path=Path(upstream_manifest_path) if upstream_manifest_path else None,
        upstream_manifest=upstream_manifest,
    )
    manifest_path = target_dir / "manifests" / f"recsys_interactions.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return PipelineResult(
        snapshot_id=resolved_snapshot_id,
        bronze_path=source_path,
        silver_path=silver_snapshot.path,
        gold_path=gold_snapshot.path,
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


def build_bronze_rows(
    envelopes: list[dict[str, Any]],
    *,
    ingested_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for offset, envelope in enumerate(envelopes):
        payload = _payload(envelope)
        event_type = payload.get("eventType") or envelope.get("eventType")
        rows.append(
            {
                "event_id": envelope.get("eventId"),
                "event_type": event_type,
                "event_version": envelope.get("eventVersion"),
                "product_id": envelope.get("productId") or payload.get("productId") or PRODUCT_ID,
                "source_service": envelope.get("sourceService"),
                "org_id": payload.get("orgId") or envelope.get("orgId") or envelope.get("tenantId"),
                "learner_id_hash": payload.get("learnerIdHash"),
                "session_id_hash": payload.get("sessionIdHash"),
                "course_id": payload.get("courseId"),
                "related_course_id": payload.get("relatedCourseId"),
                "occurred_at": payload.get("occurredAt") or envelope.get("occurredAt"),
                "published_at": envelope.get("publishedAt"),
                "ingested_at": ingested_at,
                "source_topic": _first_present(
                    envelope,
                    "sourceTopic",
                    "source_topic",
                    "topic",
                    default=RECOMMENDATION_TOPIC,
                ),
                "source_partition": _first_present(
                    envelope,
                    "sourcePartition",
                    "source_partition",
                    "partition",
                    default=0,
                ),
                "source_offset": _first_present(
                    envelope,
                    "sourceOffset",
                    "source_offset",
                    "offset",
                    default=offset,
                ),
                "raw_payload": payload,
            }
        )
    return rows


def build_silver_rows(bronze_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bronze in bronze_rows:
        event_type = bronze.get("event_type")
        activity_type = ACTIVITY_TYPES.get(event_type)
        if not activity_type:
            continue
        source_event_id = bronze.get("event_id")
        rows.append(
            {
                "activity_id": stable_id("learner-activity", source_event_id, activity_type),
                "product_id": bronze.get("product_id"),
                "org_id": bronze.get("org_id"),
                "learner_id_hash": bronze.get("learner_id_hash"),
                "session_id_hash": bronze.get("session_id_hash"),
                "course_id": bronze.get("course_id"),
                "related_course_id": bronze.get("related_course_id"),
                "activity_type": activity_type,
                "occurred_at": bronze.get("occurred_at"),
                "source_event_id": source_event_id,
                "source_service": bronze.get("source_service"),
                "ingested_at": bronze.get("ingested_at"),
            }
        )
    return rows


def build_gold_rows(
    silver_rows: list[dict[str, Any]],
    *,
    snapshot_id: str,
    built_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for silver in silver_rows:
        event_type = _gold_event_type(silver.get("activity_type"))
        course_id = silver.get("course_id")
        related_course_id = silver.get("related_course_id")
        if event_type is None or related_course_id is None:
            continue
        quality_passed = bool(
            snapshot_id
            and course_id
            and related_course_id
            and course_id != related_course_id
            and event_type in EVENT_WEIGHTS
            and silver.get("source_event_id")
            and silver.get("activity_id")
        )
        rows.append(
            {
                "dataset_snapshot_id": snapshot_id,
                "product_id": silver.get("product_id"),
                "org_id": silver.get("org_id"),
                "learner_id_hash": silver.get("learner_id_hash"),
                "course_id": course_id,
                "related_course_id": related_course_id,
                "event_type": event_type,
                "event_weight": EVENT_WEIGHTS[event_type],
                "occurred_at": silver.get("occurred_at"),
                "source_event_id": silver.get("source_event_id"),
                "source_activity_id": silver.get("activity_id"),
                "built_at": built_at,
                "quality_passed": quality_passed,
            }
        )
    return rows


def validate_bronze_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    _require_not_null(errors, rows, "event_id", "bronze event_id_not_null")
    _require_not_null(errors, rows, "product_id", "bronze product_id_not_null")
    _require_not_null(errors, rows, "occurred_at", "bronze occurred_at_not_null")
    _require_allowed_values(errors, rows, "event_type", ALLOWED_EVENT_TYPES, "bronze event_type_allowed")
    _require_unique(
        errors,
        rows,
        ("source_topic", "source_partition", "source_offset"),
        "bronze source_position_unique",
    )
    for index, row in enumerate(rows):
        payload = row.get("raw_payload")
        if not isinstance(payload, dict):
            errors.append(f"bronze row {index} raw_payload must be an object")
        elif _contains_sensitive_payload_key(payload):
            errors.append(f"bronze row {index} raw_payload contains a sensitive direct identifier key")
    return tuple(errors)


def validate_silver_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    _require_not_null(errors, rows, "activity_id", "silver activity_id_not_null")
    _require_not_null(errors, rows, "product_id", "silver product_id_not_null")
    _require_not_null(errors, rows, "source_event_id", "silver source_event_id_not_null")
    _require_allowed_values(
        errors,
        rows,
        "activity_type",
        set(ACTIVITY_TYPES.values()),
        "silver activity_type_allowed",
    )
    _require_unique(errors, rows, ("activity_id",), "silver activity_id_unique")
    return tuple(errors)


def validate_gold_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("gold snapshot must contain at least one publishable interaction")
        return tuple(errors)

    for column in (
        "dataset_snapshot_id",
        "product_id",
        "course_id",
        "related_course_id",
        "event_weight",
        "occurred_at",
        "source_event_id",
        "source_activity_id",
        "built_at",
    ):
        _require_not_null(errors, rows, column, f"gold {column}_not_null")
    _require_allowed_values(errors, rows, "event_type", ALLOWED_EVENT_TYPES, "gold event_type_allowed")
    _require_unique(
        errors,
        rows,
        ("dataset_snapshot_id", "source_event_id", "course_id", "related_course_id"),
        "gold interaction_key_unique",
    )
    for index, row in enumerate(rows):
        if row.get("course_id") == row.get("related_course_id"):
            errors.append(f"gold row {index} violates no_self_recommendation")
        if row.get("quality_passed") is not True:
            errors.append(f"gold row {index} quality_passed must be true")
    return tuple(errors)


def write_layer_snapshot(
    name: str,
    path: Path,
    rows: list[dict[str, Any]],
    *,
    quality_errors: tuple[str, ...],
) -> LayerSnapshot:
    content_hash = write_jsonl(path, rows)
    return LayerSnapshot(
        name=name,
        path=path,
        row_count=len(rows),
        content_hash=content_hash,
        quality_passed=not quality_errors,
        quality_errors=quality_errors,
    )


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


def build_manifest(
    *,
    snapshot_id: str,
    generated_at: str,
    input_path: Path,
    output_dir: Path,
    layer_snapshots: tuple[LayerSnapshot, ...],
    pipeline: str = PIPELINE_NAME,
    upstream_manifest_path: Path | None = None,
    upstream_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    layers = {
        snapshot.name: snapshot.as_manifest_entry(output_dir)
        for snapshot in layer_snapshots
    }
    gold = layers["gold.recsys_interactions"]
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
        "pipeline": pipeline,
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


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return read_jsonl(path)


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: manifest must be a JSON object")
    return data


def stable_id(*parts: object) -> str:
    value = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def content_hash(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def canonical_json(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _payload(envelope: dict[str, Any]) -> dict[str, Any]:
    payload = envelope.get("payload")
    return payload if isinstance(payload, dict) else {}


def _first_present(
    mapping: dict[str, Any],
    *keys: str,
    default: Any,
) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


def _gold_event_type(activity_type: object) -> str | None:
    if not isinstance(activity_type, str):
        return None
    prefix = "RECOMMENDATION_"
    if not activity_type.startswith(prefix):
        return None
    event_type = activity_type.removeprefix(prefix)
    return event_type if event_type in EVENT_WEIGHTS else None


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
            joined = ", ".join(columns)
            errors.append(f"{check_name}: row {index} duplicates ({joined})={key!r}")
            continue
        seen.add(key)


def _contains_sensitive_payload_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = key.replace("-", "_").lower()
            if normalized in SENSITIVE_PAYLOAD_KEYS:
                return True
            if _contains_sensitive_payload_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_payload_key(item) for item in value)
    return False
