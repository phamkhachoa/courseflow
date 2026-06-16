from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_df.pipelines.base import PipelineRunRequest, PipelineSpec


BILLING_TOPIC = "finance.billing_transaction.settled.v1"
PIPELINE_FROM_BRONZE_NAME = "billing.revenue_daily.from_approved_bronze.v1"
PRODUCT_ID = "billing-platform"

VALID_TRANSACTION_STATUSES = {"SETTLED", "PENDING", "FAILED", "REFUNDED", "CHARGEBACK", "REVERSED"}
VALID_RECOGNITION_STATUSES = {"RECOGNIZED", "DEFERRED", "PARTIAL", "REVERSED", "PENDING"}
VALID_REVENUE_STATUSES = {"CLOSED", "PENDING_SOURCE", "EXCEPTION"}
REVERSAL_STATUSES = {"REFUNDED", "CHARGEBACK", "REVERSED"}


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
class BillingPipelineResult:
    snapshot_id: str
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class BillingRevenueDailyRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_FROM_BRONZE_NAME,
        name="Billing revenue daily from approved Bronze",
        product=PRODUCT_ID,
        domain="finance",
        use_cases=("enterprise-revenue-intelligence",),
        input_kind="approved_bronze_jsonl",
        output_data_products=(
            "silver.finance_billing_transactions",
            "gold.finance_revenue_daily",
        ),
        description="Build Silver finance billing transactions and Gold daily revenue aggregates from approved Bronze billing events.",
        input_topics=(BILLING_TOPIC,),
        input_data_products=("bronze.events_billing_transaction_settled",),
        primary_output="gold.finance_revenue_daily",
        evidence_capabilities=(
            "schema_registry",
            "access_policy",
            "catalog_lineage",
            "release_gates",
        ),
        optional_options=("upstream_manifest_path", "snapshot_id", "built_at"),
    )

    def run(self, request: PipelineRunRequest) -> BillingPipelineResult:
        return run_billing_revenue_daily_from_bronze(
            request.input_path,
            request.output_dir,
            upstream_manifest_path=request.options.get("upstream_manifest_path"),
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
        )


def run_billing_revenue_daily_from_bronze(
    bronze_path: str | Path,
    output_dir: str | Path,
    *,
    upstream_manifest_path: str | Path | None = None,
    snapshot_id: str | None = None,
    built_at: str | None = None,
) -> BillingPipelineResult:
    source_path = Path(bronze_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    resolved_snapshot_id = snapshot_id or f"billing-revenue-{_compact_timestamp(build_time)}"
    upstream_manifest = load_manifest(upstream_manifest_path) if upstream_manifest_path else None

    bronze_rows = read_jsonl(source_path)
    silver_rows = build_silver_rows(bronze_rows)
    gold_rows = build_gold_rows(
        silver_rows,
        snapshot_id=resolved_snapshot_id,
        built_at=build_time,
    )

    bronze_errors = validate_bronze_rows(bronze_rows)
    bronze_snapshot = LayerSnapshot(
        name="bronze.events_billing_transaction_settled",
        path=source_path,
        row_count=len(bronze_rows),
        content_hash=hash_file(source_path),
        quality_passed=not bronze_errors,
        quality_errors=bronze_errors,
    )
    silver_snapshot = write_layer_snapshot(
        "silver.finance_billing_transactions",
        target_dir / "silver" / "finance_billing_transactions.jsonl",
        silver_rows,
        quality_errors=validate_silver_rows(silver_rows),
    )
    gold_snapshot = write_layer_snapshot(
        "gold.finance_revenue_daily",
        target_dir / "gold" / "finance_revenue_daily.jsonl",
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
    manifest_path = target_dir / "manifests" / f"billing_revenue_daily.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return BillingPipelineResult(
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
                    "finance-billing-transaction",
                    bronze.get("event_id"),
                    bronze.get("billing_transaction_id"),
                    bronze.get("invoice_id"),
                    bronze.get("payment_id"),
                ),
                "product_id": bronze.get("product_id"),
                "source_product_id": bronze.get("source_product_id") or bronze.get("product_id"),
                "org_id": bronze.get("org_id"),
                "account_id": bronze.get("account_id"),
                "customer_id_hash": bronze.get("customer_id_hash"),
                "billing_transaction_id": bronze.get("billing_transaction_id"),
                "invoice_id": bronze.get("invoice_id"),
                "payment_id": bronze.get("payment_id"),
                "subscription_id": bronze.get("subscription_id"),
                "contract_id": bronze.get("contract_id"),
                "order_id": bronze.get("order_id"),
                "product_line": bronze.get("product_line"),
                "offering_id": bronze.get("offering_id"),
                "sku_id": bronze.get("sku_id"),
                "currency": bronze.get("currency"),
                "gross_amount_cents": _int_value(bronze.get("gross_amount_cents")),
                "discount_amount_cents": _int_value(bronze.get("discount_amount_cents")),
                "tax_amount_cents": _int_value(bronze.get("tax_amount_cents")),
                "refund_amount_cents": _int_value(bronze.get("refund_amount_cents")),
                "net_revenue_cents": _int_value(bronze.get("net_revenue_cents")),
                "recognized_revenue_cents": _int_value(bronze.get("recognized_revenue_cents")),
                "deferred_revenue_cents": _int_value(bronze.get("deferred_revenue_cents")),
                "transaction_status": bronze.get("transaction_status"),
                "revenue_recognition_status": bronze.get("revenue_recognition_status"),
                "billing_period_start": bronze.get("billing_period_start"),
                "billing_period_end": bronze.get("billing_period_end"),
                "accounting_date": bronze.get("accounting_date"),
                "settled_at": bronze.get("settled_at"),
                "source_system_record_id_hash": bronze.get("source_system_record_id_hash"),
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
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in silver_rows:
        key = (
            row.get("accounting_date"),
            row.get("product_id"),
            row.get("org_id"),
            row.get("source_product_id"),
            row.get("product_line"),
            row.get("currency"),
        )
        grouped.setdefault(key, []).append(row)

    rows: list[dict[str, Any]] = []
    for key in sorted(grouped, key=lambda item: tuple("" if value is None else str(value) for value in item)):
        accounting_date, product_id, org_id, source_product_id, product_line, currency = key
        records = grouped[key]
        pending_count = sum(1 for record in records if record.get("transaction_status") == "PENDING")
        failed_count = sum(1 for record in records if record.get("transaction_status") == "FAILED")
        reversed_count = sum(1 for record in records if record.get("transaction_status") in REVERSAL_STATUSES)
        revenue_status = aggregate_revenue_status(
            pending_count=pending_count,
            failed_count=failed_count,
            records=records,
        )
        source_hashes = sorted(str(record.get("source_record_hash_sha256")) for record in records)
        rows.append(
            {
                "product_id": product_id,
                "source_product_id": source_product_id,
                "dataset_snapshot_id": snapshot_id,
                "revenue_daily_id": stable_id(
                    "finance-revenue-daily",
                    snapshot_id,
                    accounting_date,
                    product_id,
                    org_id,
                    source_product_id,
                    product_line,
                    currency,
                ),
                "org_id": org_id,
                "report_date": accounting_date,
                "accounting_date": accounting_date,
                "product_line": product_line,
                "currency": currency,
                "transaction_count": len(records),
                "invoice_count": len({record.get("invoice_id") for record in records if record.get("invoice_id")}),
                "gross_amount_cents": sum(_int_value(record.get("gross_amount_cents")) for record in records),
                "discount_amount_cents": sum(_int_value(record.get("discount_amount_cents")) for record in records),
                "tax_amount_cents": sum(_int_value(record.get("tax_amount_cents")) for record in records),
                "refund_amount_cents": sum(_int_value(record.get("refund_amount_cents")) for record in records),
                "net_revenue_cents": sum(_int_value(record.get("net_revenue_cents")) for record in records),
                "recognized_revenue_cents": sum(_int_value(record.get("recognized_revenue_cents")) for record in records),
                "deferred_revenue_cents": sum(_int_value(record.get("deferred_revenue_cents")) for record in records),
                "pending_transaction_count": pending_count,
                "failed_transaction_count": failed_count,
                "reversed_transaction_count": reversed_count,
                "revenue_status": revenue_status,
                "source_record_hash_sha256": content_hash(canonical_json(source_hashes)),
                "built_at": built_at,
                "quality_passed": True,
            }
        )
    return rows


def aggregate_revenue_status(
    *,
    pending_count: int,
    failed_count: int,
    records: list[dict[str, Any]],
) -> str:
    if pending_count or failed_count:
        return "PENDING_SOURCE"
    for record in records:
        net_revenue = _int_value(record.get("net_revenue_cents"))
        expected_net = (
            _int_value(record.get("gross_amount_cents"))
            - _int_value(record.get("discount_amount_cents"))
            - _int_value(record.get("refund_amount_cents"))
        )
        if net_revenue != expected_net:
            return "EXCEPTION"
    return "CLOSED"


def validate_bronze_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    _require_not_null(errors, rows, "event_id", "bronze event_id_not_null")
    _require_not_null(errors, rows, "product_id", "bronze product_id_not_null")
    _require_not_null(errors, rows, "org_id", "bronze org_id_not_null")
    _require_not_null(errors, rows, "customer_id_hash", "bronze customer_id_hash_not_null")
    _require_not_null(errors, rows, "billing_transaction_id", "bronze billing_transaction_id_not_null")
    _require_allowed_values(errors, rows, "event_type", {"BILLING_TRANSACTION_SETTLED"}, "bronze event_type_allowed")
    return tuple(errors)


def validate_silver_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("silver snapshot must contain at least one billing transaction")
        return tuple(errors)
    for column in (
        "transaction_id",
        "product_id",
        "source_product_id",
        "org_id",
        "customer_id_hash",
        "billing_transaction_id",
        "invoice_id",
        "currency",
        "accounting_date",
    ):
        _require_not_null(errors, rows, column, f"silver {column}_not_null")
    _require_allowed_values(
        errors,
        rows,
        "transaction_status",
        VALID_TRANSACTION_STATUSES,
        "silver transaction_status_allowed",
    )
    _require_allowed_values(
        errors,
        rows,
        "revenue_recognition_status",
        VALID_RECOGNITION_STATUSES,
        "silver revenue_recognition_status_allowed",
    )
    _require_unique(errors, rows, ("transaction_id",), "silver transaction_id_unique")
    return tuple(errors)


def validate_gold_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("gold snapshot must contain at least one revenue aggregate")
        return tuple(errors)
    for column in (
        "dataset_snapshot_id",
        "revenue_daily_id",
        "org_id",
        "report_date",
        "accounting_date",
        "source_product_id",
        "product_line",
        "currency",
        "net_revenue_cents",
        "recognized_revenue_cents",
        "revenue_status",
        "source_record_hash_sha256",
        "built_at",
    ):
        _require_not_null(errors, rows, column, f"gold {column}_not_null")
    _require_allowed_values(
        errors,
        rows,
        "revenue_status",
        VALID_REVENUE_STATUSES,
        "gold revenue_status_allowed",
    )
    _require_unique(
        errors,
        rows,
        ("dataset_snapshot_id", "revenue_daily_id"),
        "gold revenue_daily_id_unique",
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
    gold = layers["gold.finance_revenue_daily"]
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
