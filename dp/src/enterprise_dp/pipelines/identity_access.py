from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.pipelines.base import PipelineRunRequest, PipelineSpec


IDENTITY_TOPIC = "compliance.identity_subject.changed.v1"
PIPELINE_FROM_BRONZE_NAME = "identity.access_governance.from_approved_bronze.v1"
PRODUCT_ID = "identity-platform"

VALID_SUBJECT_TYPES = {"USER", "SERVICE_ACCOUNT", "ADMIN", "WORKFORCE_USER", "EMPLOYEE", "CUSTOMER_USER"}
VALID_LIFECYCLE_STATUSES = {"PENDING", "ACTIVE", "SUSPENDED", "DEPROVISIONED"}
VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_RISK_STATUSES = {"OK", "REVIEW", "CRITICAL"}
RISK_BASE_SCORE = {
    "LOW": 0,
    "MEDIUM": 25,
    "HIGH": 60,
    "CRITICAL": 90,
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
class IdentityAccessPipelineResult:
    snapshot_id: str
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class IdentityAccessGovernanceRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_FROM_BRONZE_NAME,
        name="Identity access governance from approved Bronze",
        product=PRODUCT_ID,
        domain="compliance",
        use_cases=("identity-access-governance",),
        input_kind="approved_bronze_jsonl",
        output_data_products=(
            "silver.identity_subject",
            "gold.access_risk_daily",
        ),
        description="Build Silver identity subject state and Gold access-risk evidence from approved Bronze identity events.",
        input_topics=(IDENTITY_TOPIC,),
        input_data_products=("bronze.events_identity_subject_changed",),
        primary_output="gold.access_risk_daily",
        evidence_capabilities=(
            "schema_registry",
            "access_policy",
            "catalog_lineage",
            "release_gates",
        ),
        optional_options=("upstream_manifest_path", "snapshot_id", "built_at"),
    )

    def run(self, request: PipelineRunRequest) -> IdentityAccessPipelineResult:
        return run_identity_access_governance_from_bronze(
            request.input_path,
            request.output_dir,
            upstream_manifest_path=request.options.get("upstream_manifest_path"),
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
        )


def run_identity_access_governance_from_bronze(
    bronze_path: str | Path,
    output_dir: str | Path,
    *,
    upstream_manifest_path: str | Path | None = None,
    snapshot_id: str | None = None,
    built_at: str | None = None,
) -> IdentityAccessPipelineResult:
    source_path = Path(bronze_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    resolved_snapshot_id = snapshot_id or f"identity-access-{_compact_timestamp(build_time)}"
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
        name="bronze.events_identity_subject_changed",
        path=source_path,
        row_count=len(bronze_rows),
        content_hash=hash_file(source_path),
        quality_passed=not bronze_errors,
        quality_errors=bronze_errors,
    )
    silver_snapshot = write_layer_snapshot(
        "silver.identity_subject",
        target_dir / "silver" / "identity_subject.jsonl",
        silver_rows,
        quality_errors=validate_silver_rows(silver_rows),
    )
    gold_snapshot = write_layer_snapshot(
        "gold.access_risk_daily",
        target_dir / "gold" / "access_risk_daily.jsonl",
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
    manifest_path = target_dir / "manifests" / f"identity_access_governance.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return IdentityAccessPipelineResult(
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
        rows.append(
            {
                "subject_state_id": stable_id(
                    "identity-subject-state",
                    snapshot_id,
                    bronze.get("event_id"),
                    bronze.get("subject_id_hash"),
                ),
                "product_id": bronze.get("product_id"),
                "org_id": bronze.get("org_id"),
                "subject_id_hash": bronze.get("subject_id_hash"),
                "subject_type": bronze.get("subject_type"),
                "lifecycle_status": bronze.get("lifecycle_status"),
                "risk_level": bronze.get("risk_level"),
                "entitlement_count": _int_value(bronze.get("entitlement_count")),
                "privileged_entitlement_count": _int_value(bronze.get("privileged_entitlement_count")),
                "mfa_enabled": _bool_value(bronze.get("mfa_enabled")),
                "last_access_at": bronze.get("last_access_at"),
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
    rows: list[dict[str, Any]] = []
    for silver in silver_rows:
        score, status, reason = access_risk(
            lifecycle_status=str(silver.get("lifecycle_status") or ""),
            risk_level=str(silver.get("risk_level") or ""),
            entitlement_count=_int_value(silver.get("entitlement_count")),
            privileged_entitlement_count=_int_value(silver.get("privileged_entitlement_count")),
            mfa_enabled=_bool_value(silver.get("mfa_enabled")),
        )
        report_date = _date_part(silver.get("changed_at")) or _date_part(built_at)
        rows.append(
            {
                "product_id": silver.get("product_id"),
                "dataset_snapshot_id": snapshot_id,
                "access_risk_id": stable_id("access-risk-daily", snapshot_id, silver.get("subject_id_hash"), report_date),
                "org_id": silver.get("org_id"),
                "report_date": report_date,
                "subject_id_hash": silver.get("subject_id_hash"),
                "subject_type": silver.get("subject_type"),
                "lifecycle_status": silver.get("lifecycle_status"),
                "risk_level": silver.get("risk_level"),
                "entitlement_count": silver.get("entitlement_count"),
                "privileged_entitlement_count": silver.get("privileged_entitlement_count"),
                "mfa_enabled": silver.get("mfa_enabled"),
                "access_risk_score": score,
                "risk_status": status,
                "reason_code": reason,
                "last_access_at": silver.get("last_access_at"),
                "source_event_id": silver.get("source_event_id"),
                "source_subject_state_id": silver.get("subject_state_id"),
                "built_at": built_at,
                "quality_passed": True,
            }
        )
    return rows


def access_risk(
    *,
    lifecycle_status: str,
    risk_level: str,
    entitlement_count: int,
    privileged_entitlement_count: int,
    mfa_enabled: bool,
) -> tuple[int, str, str]:
    score = RISK_BASE_SCORE.get(risk_level, 50)
    reason = risk_level if risk_level in VALID_RISK_LEVELS else "UNKNOWN_RISK_LEVEL"
    if privileged_entitlement_count > 0:
        score += 20
        reason = "PRIVILEGED_ACCESS"
    if not mfa_enabled:
        score += 20
        reason = "MFA_DISABLED"
    if lifecycle_status == "DEPROVISIONED" and entitlement_count > 0:
        score += 40
        reason = "DEPROVISIONED_WITH_ACCESS"
    score = min(score, 100)
    if score >= 90:
        return score, "CRITICAL", reason
    if score >= 50:
        return score, "REVIEW", reason
    return score, "OK", "LOW_RISK"


def validate_bronze_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("bronze snapshot must contain at least one identity subject event")
        return tuple(errors)
    for column in (
        "event_id",
        "product_id",
        "tenant_id",
        "org_id",
        "subject_id_hash",
        "subject_type",
        "lifecycle_status",
        "risk_level",
        "source_record_hash_sha256",
    ):
        _require_not_null(errors, rows, column, f"bronze {column}_not_null")
    _require_allowed_values(errors, rows, "event_type", {"IDENTITY_SUBJECT_CHANGED"}, "bronze event_type_allowed")
    return tuple(errors)


def validate_silver_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("silver snapshot must contain at least one identity subject")
        return tuple(errors)
    for column in ("subject_state_id", "product_id", "org_id", "subject_id_hash", "changed_at", "source_event_id"):
        _require_not_null(errors, rows, column, f"silver {column}_not_null")
    _require_unique(errors, rows, ("subject_state_id",), "silver subject_state_id_unique")
    _require_allowed_values(errors, rows, "subject_type", VALID_SUBJECT_TYPES, "silver subject_type_allowed")
    _require_allowed_values(errors, rows, "lifecycle_status", VALID_LIFECYCLE_STATUSES, "silver lifecycle_status_allowed")
    _require_allowed_values(errors, rows, "risk_level", VALID_RISK_LEVELS, "silver risk_level_allowed")
    return tuple(errors)


def validate_gold_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("gold snapshot must contain at least one access risk row")
        return tuple(errors)
    for column in (
        "dataset_snapshot_id",
        "access_risk_id",
        "org_id",
        "report_date",
        "subject_id_hash",
        "risk_status",
        "reason_code",
        "built_at",
    ):
        _require_not_null(errors, rows, column, f"gold {column}_not_null")
    _require_allowed_values(errors, rows, "risk_status", VALID_RISK_STATUSES, "gold risk_status_allowed")
    _require_unique(errors, rows, ("dataset_snapshot_id", "subject_id_hash", "report_date"), "gold risk_snapshot_unique")
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
    gold = layers["gold.access_risk_daily"]
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


def _bool_value(value: object) -> bool:
    return value is True


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
