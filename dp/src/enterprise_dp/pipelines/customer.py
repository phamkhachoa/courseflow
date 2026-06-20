from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.pipelines.base import PipelineRunRequest, PipelineSpec


CUSTOMER_TOPIC = "customer.account.changed.v1"
PIPELINE_FROM_BRONZE_NAME = "customer.account_health.from_approved_bronze.v1"
PRODUCT_ID = "crm-sales"

VALID_ACCOUNT_TYPES = {"BUSINESS", "INDIVIDUAL", "PUBLIC_SECTOR", "PARTNER", "UNKNOWN"}
VALID_LIFECYCLE_STAGES = {"PROSPECT", "TRIAL", "ACTIVE_CUSTOMER", "EXPANSION", "RENEWAL", "DORMANT", "CHURNED"}
VALID_ACCOUNT_STATUSES = {"ACTIVE", "INACTIVE", "TRIAL", "AT_RISK", "CHURNED", "SUSPENDED"}
VALID_CONSENT_STATUSES = {"OPTED_IN", "OPTED_OUT", "UNKNOWN", "NOT_APPLICABLE"}
VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
VALID_PROFILE_STATUSES = {"HEALTHY", "WATCH", "RISK", "CHURNED"}


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
class CustomerPipelineResult:
    snapshot_id: str
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class CustomerAccountHealthRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_FROM_BRONZE_NAME,
        name="Customer account health from approved Bronze",
        product=PRODUCT_ID,
        domain="customer",
        use_cases=("customer-account-health",),
        input_kind="approved_bronze_jsonl",
        output_data_products=(
            "silver.customer_identity_link",
            "gold.customer_360_profile",
        ),
        description="Build Silver customer identity links and Gold Customer 360 account-health profiles from approved Bronze CRM account events.",
        input_topics=(CUSTOMER_TOPIC,),
        input_data_products=("bronze.events_customer_account_changed",),
        primary_output="gold.customer_360_profile",
        evidence_capabilities=(
            "schema_registry",
            "access_policy",
            "catalog_lineage",
            "release_gates",
        ),
        optional_options=("upstream_manifest_path", "snapshot_id", "built_at"),
    )

    def run(self, request: PipelineRunRequest) -> CustomerPipelineResult:
        return run_customer_account_health_from_bronze(
            request.input_path,
            request.output_dir,
            upstream_manifest_path=request.options.get("upstream_manifest_path"),
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
        )


def run_customer_account_health_from_bronze(
    bronze_path: str | Path,
    output_dir: str | Path,
    *,
    upstream_manifest_path: str | Path | None = None,
    snapshot_id: str | None = None,
    built_at: str | None = None,
) -> CustomerPipelineResult:
    source_path = Path(bronze_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    resolved_snapshot_id = snapshot_id or f"customer-account-health-{_compact_timestamp(build_time)}"
    upstream_manifest = load_manifest(upstream_manifest_path) if upstream_manifest_path else None

    bronze_rows = read_jsonl(source_path)
    silver_rows = build_silver_rows(bronze_rows, snapshot_id=resolved_snapshot_id)
    gold_rows = build_gold_rows(
        bronze_rows,
        silver_rows,
        snapshot_id=resolved_snapshot_id,
        built_at=build_time,
    )

    bronze_errors = validate_bronze_rows(bronze_rows)
    bronze_snapshot = LayerSnapshot(
        name="bronze.events_customer_account_changed",
        path=source_path,
        row_count=len(bronze_rows),
        content_hash=hash_file(source_path),
        quality_passed=not bronze_errors,
        quality_errors=bronze_errors,
    )
    silver_snapshot = write_layer_snapshot(
        "silver.customer_identity_link",
        target_dir / "silver" / "customer_identity_link.jsonl",
        silver_rows,
        quality_errors=validate_silver_rows(silver_rows),
    )
    gold_snapshot = write_layer_snapshot(
        "gold.customer_360_profile",
        target_dir / "gold" / "customer_360_profile.jsonl",
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
    manifest_path = target_dir / "manifests" / f"customer_account_health.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return CustomerPipelineResult(
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
                "customer_identity_link_id": stable_id(
                    "customer-identity-link",
                    snapshot_id,
                    bronze.get("event_id"),
                    bronze.get("customer_id_hash"),
                    bronze.get("account_id"),
                ),
                "product_id": bronze.get("product_id"),
                "org_id": bronze.get("org_id"),
                "account_id": bronze.get("account_id"),
                "customer_id_hash": bronze.get("customer_id_hash"),
                "external_account_id_hash": bronze.get("external_account_id_hash"),
                "source_system_record_id_hash": bronze.get("source_system_record_id_hash"),
                "source_system": bronze.get("source_system"),
                "account_type": bronze.get("account_type"),
                "lifecycle_stage": bronze.get("lifecycle_stage"),
                "account_status": bronze.get("account_status"),
                "consent_status": bronze.get("consent_status"),
                "identity_confidence_score": 100,
                "link_status": "CURRENT",
                "valid_from": bronze.get("changed_at") or bronze.get("occurred_at"),
                "source_event_id": bronze.get("event_id"),
                "source_record_hash_sha256": bronze.get("source_record_hash_sha256"),
            }
        )
    return rows


def build_gold_rows(
    bronze_rows: list[dict[str, Any]],
    silver_rows: list[dict[str, Any]],
    *,
    snapshot_id: str,
    built_at: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bronze, silver in zip(bronze_rows, silver_rows, strict=False):
        health_score = _bounded_score(bronze.get("health_signal_score"))
        engagement_score = _bounded_score(bronze.get("product_usage_score"))
        risk_level = str(bronze.get("risk_level") or "")
        account_status = str(silver.get("account_status") or "")
        profile_status = customer_profile_status(
            account_status=account_status,
            health_score=health_score,
            risk_level=risk_level,
        )
        report_date = _date_part(silver.get("valid_from")) or _date_part(built_at)
        rows.append(
            {
                "product_id": silver.get("product_id"),
                "dataset_snapshot_id": snapshot_id,
                "customer_profile_id": stable_id(
                    "customer-360-profile",
                    snapshot_id,
                    silver.get("customer_id_hash"),
                    report_date,
                ),
                "org_id": silver.get("org_id"),
                "report_date": report_date,
                "account_id": silver.get("account_id"),
                "customer_id_hash": silver.get("customer_id_hash"),
                "external_account_id_hash": silver.get("external_account_id_hash"),
                "account_type": silver.get("account_type"),
                "lifecycle_stage": silver.get("lifecycle_stage"),
                "account_status": silver.get("account_status"),
                "market_segment": bronze.get("market_segment"),
                "region_code": bronze.get("region_code"),
                "consent_status": silver.get("consent_status"),
                "health_score": health_score,
                "engagement_score": engagement_score,
                "revenue_signal_cents": _int_value(bronze.get("mrr_cents")),
                "open_opportunity_count": _int_value(bronze.get("open_opportunity_count")),
                "open_support_case_count": _int_value(bronze.get("open_support_case_count")),
                "product_usage_score": engagement_score,
                "risk_level": risk_level,
                "profile_status": profile_status,
                "source_coverage_count": 1,
                "source_event_id": silver.get("source_event_id"),
                "source_customer_identity_link_id": silver.get("customer_identity_link_id"),
                "last_signal_at": silver.get("valid_from"),
                "built_at": built_at,
                "quality_passed": True,
            }
        )
    return rows


def customer_profile_status(*, account_status: str, health_score: int, risk_level: str) -> str:
    if account_status == "CHURNED":
        return "CHURNED"
    if risk_level in {"HIGH", "CRITICAL"} or health_score < 40:
        return "RISK"
    if risk_level == "MEDIUM" or health_score < 70:
        return "WATCH"
    return "HEALTHY"


def validate_bronze_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("bronze snapshot must contain at least one customer account event")
        return tuple(errors)
    for column in (
        "event_id",
        "product_id",
        "tenant_id",
        "org_id",
        "account_id",
        "customer_id_hash",
        "external_account_id_hash",
        "account_status",
        "consent_status",
        "source_record_hash_sha256",
    ):
        _require_not_null(errors, rows, column, f"bronze {column}_not_null")
    _require_allowed_values(errors, rows, "event_type", {"CUSTOMER_ACCOUNT_CHANGED"}, "bronze event_type_allowed")
    _require_allowed_values(errors, rows, "account_type", VALID_ACCOUNT_TYPES, "bronze account_type_allowed")
    _require_allowed_values(errors, rows, "lifecycle_stage", VALID_LIFECYCLE_STAGES, "bronze lifecycle_stage_allowed")
    _require_allowed_values(errors, rows, "account_status", VALID_ACCOUNT_STATUSES, "bronze account_status_allowed")
    _require_allowed_values(errors, rows, "consent_status", VALID_CONSENT_STATUSES, "bronze consent_status_allowed")
    _require_allowed_values(errors, rows, "risk_level", VALID_RISK_LEVELS, "bronze risk_level_allowed")
    return tuple(errors)


def validate_silver_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("silver snapshot must contain at least one customer identity link")
        return tuple(errors)
    for column in (
        "customer_identity_link_id",
        "product_id",
        "org_id",
        "account_id",
        "customer_id_hash",
        "external_account_id_hash",
        "valid_from",
        "source_event_id",
    ):
        _require_not_null(errors, rows, column, f"silver {column}_not_null")
    _require_unique(errors, rows, ("customer_identity_link_id",), "silver customer_identity_link_id_unique")
    _require_allowed_values(errors, rows, "account_type", VALID_ACCOUNT_TYPES, "silver account_type_allowed")
    _require_allowed_values(errors, rows, "lifecycle_stage", VALID_LIFECYCLE_STAGES, "silver lifecycle_stage_allowed")
    _require_allowed_values(errors, rows, "account_status", VALID_ACCOUNT_STATUSES, "silver account_status_allowed")
    _require_allowed_values(errors, rows, "consent_status", VALID_CONSENT_STATUSES, "silver consent_status_allowed")
    _require_allowed_values(errors, rows, "link_status", {"CURRENT", "STALE", "CONFLICTED"}, "silver link_status_allowed")
    return tuple(errors)


def validate_gold_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("gold snapshot must contain at least one customer profile")
        return tuple(errors)
    for column in (
        "dataset_snapshot_id",
        "customer_profile_id",
        "org_id",
        "report_date",
        "customer_id_hash",
        "profile_status",
        "health_score",
        "built_at",
    ):
        _require_not_null(errors, rows, column, f"gold {column}_not_null")
    _require_allowed_values(errors, rows, "profile_status", VALID_PROFILE_STATUSES, "gold profile_status_allowed")
    _require_allowed_values(errors, rows, "risk_level", VALID_RISK_LEVELS, "gold risk_level_allowed")
    _require_unique(errors, rows, ("dataset_snapshot_id", "customer_id_hash", "report_date"), "gold customer_profile_snapshot_unique")
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
    gold = layers["gold.customer_360_profile"]
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


def _bounded_score(value: object) -> int:
    return max(0, min(100, _int_value(value)))


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
