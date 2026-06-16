from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.pipelines.base import PipelineRunRequest, PipelineSpec


FINANCE_TOPIC = "finance.benefit_settled.v1"
PIPELINE_FROM_BRONZE_NAME = "finance.benefit_reconciliation.from_approved_bronze.v1"
PRODUCT_ID = "enterprise-commerce"

VALID_SETTLEMENT_STATUSES = {"SETTLED", "PENDING", "FAILED", "REVERSED"}
VALID_BENEFIT_STATUSES = {"COMMITTED", "PENDING", "REVERSED", "MISSING"}
VALID_RECONCILIATION_STATUSES = {"MATCHED", "EXCEPTION", "PENDING_SOURCE"}


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
class FinancePipelineResult:
    snapshot_id: str
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class FinanceBenefitReconciliationRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_FROM_BRONZE_NAME,
        name="Finance benefit reconciliation from approved Bronze",
        product=PRODUCT_ID,
        domain="finance",
        use_cases=("finance-benefit-reconciliation",),
        input_kind="approved_bronze_jsonl",
        output_data_products=(
            "silver.finance_benefit_transactions",
            "gold.finance_benefit_reconciliation",
        ),
        description="Build Silver benefit transactions and Gold finance reconciliation evidence from approved Bronze.",
        input_topics=(FINANCE_TOPIC,),
        input_data_products=("bronze.events_benefit_settled",),
        primary_output="gold.finance_benefit_reconciliation",
        evidence_capabilities=(
            "schema_registry",
            "access_policy",
            "catalog_lineage",
            "release_gates",
        ),
        optional_options=("upstream_manifest_path", "snapshot_id", "built_at"),
    )

    def run(self, request: PipelineRunRequest) -> FinancePipelineResult:
        return run_finance_benefit_reconciliation_from_bronze(
            request.input_path,
            request.output_dir,
            upstream_manifest_path=request.options.get("upstream_manifest_path"),
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
        )


def run_finance_benefit_reconciliation_from_bronze(
    bronze_path: str | Path,
    output_dir: str | Path,
    *,
    upstream_manifest_path: str | Path | None = None,
    snapshot_id: str | None = None,
    built_at: str | None = None,
) -> FinancePipelineResult:
    source_path = Path(bronze_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    resolved_snapshot_id = snapshot_id or f"finance-benefit-{_compact_timestamp(build_time)}"
    upstream_manifest = load_manifest(upstream_manifest_path) if upstream_manifest_path else None

    bronze_rows = read_jsonl(source_path)
    silver_rows = build_silver_rows(bronze_rows)
    gold_rows = build_gold_rows(
        silver_rows,
        snapshot_id=resolved_snapshot_id,
        built_at=build_time,
    )

    bronze_snapshot = LayerSnapshot(
        name="bronze.events_benefit_settled",
        path=source_path,
        row_count=len(bronze_rows),
        content_hash=hash_file(source_path),
        quality_passed=not validate_bronze_rows(bronze_rows),
        quality_errors=validate_bronze_rows(bronze_rows),
    )
    silver_snapshot = write_layer_snapshot(
        "silver.finance_benefit_transactions",
        target_dir / "silver" / "finance_benefit_transactions.jsonl",
        silver_rows,
        quality_errors=validate_silver_rows(silver_rows),
    )
    gold_snapshot = write_layer_snapshot(
        "gold.finance_benefit_reconciliation",
        target_dir / "gold" / "finance_benefit_reconciliation.jsonl",
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
    manifest_path = target_dir / "manifests" / f"finance_benefit_reconciliation.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return FinancePipelineResult(
        snapshot_id=resolved_snapshot_id,
        bronze_path=source_path,
        silver_path=silver_snapshot.path,
        gold_path=gold_snapshot.path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def build_silver_rows(bronze_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bronze in bronze_rows:
        rows.append(
            {
                "transaction_id": stable_id(
                    "finance-benefit-transaction",
                    bronze.get("event_id"),
                    bronze.get("benefit_transaction_id"),
                    bronze.get("payment_id"),
                ),
                "product_id": bronze.get("product_id"),
                "source_product_id": bronze.get("source_product_id") or bronze.get("product_id"),
                "org_id": bronze.get("org_id"),
                "order_id": bronze.get("order_id"),
                "payment_id": bronze.get("payment_id"),
                "entitlement_id": bronze.get("entitlement_id"),
                "beneficiary_id_hash": bronze.get("beneficiary_id_hash"),
                "item_id": bronze.get("item_id"),
                "currency": bronze.get("currency"),
                "benefit_transaction_id": bronze.get("benefit_transaction_id"),
                "reconciliation_key": bronze.get("reconciliation_key"),
                "benefit_type": bronze.get("benefit_type"),
                "expected_amount_cents": _int_value(bronze.get("expected_amount_cents")),
                "actual_amount_cents": _int_value(bronze.get("actual_amount_cents")),
                "expected_points": _int_value(bronze.get("expected_points")),
                "actual_points": _int_value(bronze.get("actual_points")),
                "list_price_cents": _int_value(bronze.get("list_price_cents")),
                "final_amount_cents": _int_value(bronze.get("final_amount_cents")),
                "paid_amount_cents": _int_value(bronze.get("paid_amount_cents")),
                "committed_discount_cents": _int_value(bronze.get("committed_discount_cents")),
                "loyalty_points_earned": _int_value(bronze.get("loyalty_points_earned")),
                "loyalty_points_burned": _int_value(bronze.get("loyalty_points_burned")),
                "reward_amount_cents": _int_value(bronze.get("reward_amount_cents")),
                "refund_amount_cents": _int_value(bronze.get("refund_amount_cents")),
                "settlement_status": bronze.get("settlement_status"),
                "benefit_status": bronze.get("benefit_status"),
                "settled_at": bronze.get("settled_at"),
                "accounting_date": bronze.get("accounting_date"),
                "reason_code": bronze.get("reason_code"),
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
        expected_amount = _int_value(silver.get("expected_amount_cents"))
        actual_amount = _int_value(silver.get("actual_amount_cents"))
        expected_points = _int_value(silver.get("expected_points"))
        actual_points = _int_value(silver.get("actual_points"))
        status, reason_code = reconciliation_status(
            silver,
            variance_amount_cents=actual_amount - expected_amount,
            variance_points=actual_points - expected_points,
        )
        rows.append(
            {
                "product_id": silver.get("product_id"),
                "source_product_id": silver.get("source_product_id"),
                "dataset_snapshot_id": snapshot_id,
                "reconciliation_id": stable_id("finance-benefit-reconciliation", snapshot_id, silver.get("reconciliation_key")),
                "org_id": silver.get("org_id"),
                "order_id": silver.get("order_id"),
                "payment_id": silver.get("payment_id"),
                "benefit_transaction_id": silver.get("benefit_transaction_id"),
                "reconciliation_key": silver.get("reconciliation_key"),
                "benefit_type": silver.get("benefit_type"),
                "entitlement_id": silver.get("entitlement_id"),
                "beneficiary_id_hash": silver.get("beneficiary_id_hash"),
                "item_id": silver.get("item_id"),
                "currency": silver.get("currency"),
                "expected_amount_cents": expected_amount,
                "actual_amount_cents": actual_amount,
                "variance_amount_cents": actual_amount - expected_amount,
                "expected_points": expected_points,
                "actual_points": actual_points,
                "variance_points": actual_points - expected_points,
                "list_price_cents": silver.get("list_price_cents"),
                "final_amount_cents": silver.get("final_amount_cents"),
                "paid_amount_cents": silver.get("paid_amount_cents"),
                "committed_discount_cents": silver.get("committed_discount_cents"),
                "loyalty_points_earned": silver.get("loyalty_points_earned"),
                "loyalty_points_burned": silver.get("loyalty_points_burned"),
                "reward_amount_cents": silver.get("reward_amount_cents"),
                "refund_amount_cents": silver.get("refund_amount_cents"),
                "expected_net_revenue_cents": expected_amount,
                "actual_net_revenue_cents": actual_amount,
                "reconciliation_delta_cents": actual_amount - expected_amount,
                "settlement_status": silver.get("settlement_status"),
                "benefit_status": silver.get("benefit_status"),
                "reconciliation_status": status,
                "reason_code": silver.get("reason_code") or reason_code,
                "accounting_date": silver.get("accounting_date"),
                "source_event_id": silver.get("source_event_id"),
                "source_record_hash_sha256": silver.get("source_record_hash_sha256"),
                "occurred_at": silver.get("settled_at"),
                "settled_at": silver.get("settled_at"),
                "built_at": built_at,
                "quality_passed": True,
            }
        )
    return rows


def reconciliation_status(
    row: dict[str, Any],
    *,
    variance_amount_cents: int,
    variance_points: int,
) -> tuple[str, str]:
    settlement_status = row.get("settlement_status")
    benefit_status = row.get("benefit_status")
    refund_amount = _int_value(row.get("refund_amount_cents"))
    if settlement_status in {"PENDING", "FAILED"}:
        return "PENDING_SOURCE", "SETTLEMENT_NOT_FINAL"
    if benefit_status in {"PENDING", "MISSING"}:
        return "EXCEPTION", "MISSING_BENEFIT_COMMIT"
    if refund_amount > 0 and benefit_status != "REVERSED":
        return "EXCEPTION", "MISSING_REVERSE"
    if variance_amount_cents != 0:
        return "EXCEPTION", "AMOUNT_MISMATCH"
    if variance_points != 0:
        return "EXCEPTION", "POINTS_MISMATCH"
    return "MATCHED", "MATCHED"


def validate_bronze_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    _require_not_null(errors, rows, "event_id", "bronze event_id_not_null")
    _require_not_null(errors, rows, "product_id", "bronze product_id_not_null")
    _require_not_null(errors, rows, "org_id", "bronze org_id_not_null")
    _require_not_null(errors, rows, "reconciliation_key", "bronze reconciliation_key_not_null")
    _require_allowed_values(errors, rows, "event_type", {"BENEFIT_SETTLED"}, "bronze event_type_allowed")
    return tuple(errors)


def validate_silver_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("silver snapshot must contain at least one benefit transaction")
        return tuple(errors)
    _require_not_null(errors, rows, "transaction_id", "silver transaction_id_not_null")
    _require_not_null(errors, rows, "product_id", "silver product_id_not_null")
    _require_not_null(errors, rows, "source_product_id", "silver source_product_id_not_null")
    _require_not_null(errors, rows, "reconciliation_key", "silver reconciliation_key_not_null")
    _require_unique(errors, rows, ("transaction_id",), "silver transaction_id_unique")
    return tuple(errors)


def validate_gold_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("gold snapshot must contain at least one reconciliation row")
        return tuple(errors)
    for column in (
        "dataset_snapshot_id",
        "reconciliation_id",
        "org_id",
        "source_product_id",
        "reconciliation_key",
        "currency",
        "reconciliation_status",
        "reason_code",
        "built_at",
    ):
        _require_not_null(errors, rows, column, f"gold {column}_not_null")
    _require_allowed_values(
        errors,
        rows,
        "reconciliation_status",
        VALID_RECONCILIATION_STATUSES,
        "gold reconciliation_status_allowed",
    )
    _require_unique(errors, rows, ("dataset_snapshot_id", "reconciliation_key"), "gold reconciliation_key_unique")
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
    gold = layers["gold.finance_benefit_reconciliation"]
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
