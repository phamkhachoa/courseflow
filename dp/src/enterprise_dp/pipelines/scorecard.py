from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, load_json
from enterprise_dp.pipelines.base import PipelineRunRequest, PipelineSpec


PIPELINE_NAME = "enterprise_reporting.executive_scorecard.from_semantic_snapshot.v1"
PRODUCT_ID = "enterprise-data-platform"
DOMAIN = "enterprise-reporting"
OUTPUT_DATA_PRODUCTS = ("gold.enterprise_kpi_daily", "gold.executive_scorecard_daily")
ALLOWED_THRESHOLD_STATUS = {"GREEN", "AMBER", "RED", "UNKNOWN"}
ALLOWED_TRENDS = {"UP", "DOWN", "FLAT", "UNKNOWN"}
ALLOWED_CERTIFICATION_STATUS = {"CERTIFIED", "PROVISIONAL", "EXPLORATORY"}
ALLOWED_METRIC_STATUS = {"ACTIVE", "DEGRADED", "MISSING"}
DIRECT_IDENTIFIER_FIELDS = {
    "customer_id_hash",
    "subject_id_hash",
    "learner_id_hash",
    "user_id",
    "email",
    "phone",
    "full_name",
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
class ExecutiveScorecardPipelineResult:
    snapshot_id: str
    input_path: Path
    enterprise_kpi_path: Path
    executive_scorecard_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


class ExecutiveScorecardRunner:
    spec = PipelineSpec(
        runner_id=PIPELINE_NAME,
        name="Executive scorecard from semantic metric snapshot",
        product=PRODUCT_ID,
        domain=DOMAIN,
        use_cases=("enterprise-kpi-scorecard",),
        input_kind="semantic_metric_snapshot",
        input_data_products=(
            "gold.finance_revenue_daily",
            "gold.finance_benefit_reconciliation",
            "gold.customer_360_profile",
            "gold.access_risk_daily",
            "gold.support_sla_daily",
            "gold.recsys_interactions",
            "gold.data_product_inventory",
            "gold.contract_compliance_daily",
            "gold.quality_sla_daily",
            "gold.lineage_coverage_daily",
        ),
        output_data_products=OUTPUT_DATA_PRODUCTS,
        description=(
            "Materialize governed non-PII executive KPI and scorecard Gold outputs "
            "from a certified semantic metric snapshot."
        ),
        primary_output="gold.executive_scorecard_daily",
        evidence_capabilities=(
            "semantic_metrics",
            "catalog_lineage",
            "quality_slo",
            "access_privacy",
            "release_gates",
        ),
        optional_options=("snapshot_id", "built_at"),
    )

    def run(self, request: PipelineRunRequest) -> ExecutiveScorecardPipelineResult:
        return run_executive_scorecard_from_semantic_snapshot(
            request.input_path,
            request.output_dir,
            snapshot_id=request.options.get("snapshot_id"),
            built_at=request.options.get("built_at"),
        )


def run_executive_scorecard_from_semantic_snapshot(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    snapshot_id: str | None = None,
    built_at: str | None = None,
) -> ExecutiveScorecardPipelineResult:
    source_path = Path(input_path)
    target_dir = Path(output_dir)
    build_time = built_at or _utc_now()
    snapshot = load_json(source_path)
    validate_semantic_snapshot_input(source_path, snapshot)
    resolved_snapshot_id = snapshot_id or str(snapshot.get("snapshot_id") or f"executive-scorecard-{_compact_timestamp(build_time)}")
    source_hash = hash_file(source_path)

    kpi_rows = build_enterprise_kpi_rows(
        snapshot,
        snapshot_id=resolved_snapshot_id,
        source_metric_snapshot_hash=source_hash,
        built_at=build_time,
    )
    scorecard_rows = build_executive_scorecard_rows(kpi_rows)

    kpi_snapshot = write_layer_snapshot(
        "gold.enterprise_kpi_daily",
        target_dir / "gold" / "enterprise_kpi_daily.jsonl",
        kpi_rows,
        quality_errors=validate_enterprise_kpi_rows(kpi_rows),
    )
    scorecard_snapshot = write_layer_snapshot(
        "gold.executive_scorecard_daily",
        target_dir / "gold" / "executive_scorecard_daily.jsonl",
        scorecard_rows,
        quality_errors=validate_executive_scorecard_rows(scorecard_rows),
    )

    layer_snapshots = (kpi_snapshot, scorecard_snapshot)
    manifest = build_manifest(
        snapshot_id=resolved_snapshot_id,
        generated_at=build_time,
        input_path=source_path,
        source_metric_snapshot=snapshot,
        source_metric_snapshot_hash=source_hash,
        output_dir=target_dir,
        layer_snapshots=layer_snapshots,
        kpi_rows=kpi_rows,
    )
    manifest_path = target_dir / "manifests" / f"executive_scorecard.{resolved_snapshot_id}.json"
    write_manifest(manifest_path, manifest)

    return ExecutiveScorecardPipelineResult(
        snapshot_id=resolved_snapshot_id,
        input_path=source_path,
        enterprise_kpi_path=kpi_snapshot.path,
        executive_scorecard_path=scorecard_snapshot.path,
        manifest_path=manifest_path,
        manifest=manifest,
    )


def build_enterprise_kpi_rows(
    snapshot: dict[str, Any],
    *,
    snapshot_id: str,
    source_metric_snapshot_hash: str,
    built_at: str,
) -> list[dict[str, Any]]:
    report_date = str(snapshot.get("report_date"))
    source_metric_snapshot_id = str(snapshot.get("snapshot_id") or snapshot_id)
    semantic_registry_hash = str(snapshot.get("semantic_registry_hash") or source_metric_snapshot_hash)
    rows: list[dict[str, Any]] = []
    for metric in semantic_metrics(snapshot):
        metric_id = str(metric.get("metric_id"))
        org_id = str(metric.get("org_id"))
        metric_report_date = str(metric.get("report_date") or report_date)
        source_data_product = str(metric.get("source_data_product"))
        source_product_id = str(metric.get("source_product_id") or metric.get("product_id") or PRODUCT_ID)
        dimension_scope = dict_value(metric.get("dimension_scope"))
        dimension_hash = str(metric.get("dimension_hash") or stable_hash(dimension_scope))
        value = float_value(metric.get("metric_value"))
        prior_value = optional_float(metric.get("prior_value"))
        delta_value = optional_float(metric.get("delta_value"))
        if delta_value is None and prior_value is not None:
            delta_value = value - prior_value
        status = normalized(metric.get("threshold_status"), allowed=ALLOWED_THRESHOLD_STATUS, default="UNKNOWN")
        quality_passed = bool(metric.get("quality_passed"))
        rows.append(
            {
                "product_id": PRODUCT_ID,
                "dataset_snapshot_id": snapshot_id,
                "kpi_daily_id": stable_id(
                    "enterprise-kpi",
                    snapshot_id,
                    org_id,
                    metric_report_date,
                    metric_id,
                    source_data_product,
                    dimension_hash,
                ),
                "org_id": org_id,
                "report_date": metric_report_date,
                "metric_id": metric_id,
                "metric_name": str(metric.get("metric_name") or metric_id),
                "metric_domain": str(metric.get("metric_domain") or metric.get("domain") or "enterprise"),
                "metric_owner": str(metric.get("metric_owner") or metric.get("owner") or "enterprise-reporting-po"),
                "metric_status": "ACTIVE" if quality_passed else "DEGRADED",
                "certification_status": normalized(
                    metric.get("certification_status"),
                    allowed=ALLOWED_CERTIFICATION_STATUS,
                    default="CERTIFIED",
                ),
                "source_data_product": source_data_product,
                "source_product_id": source_product_id,
                "source_snapshot_id": str(metric.get("source_snapshot_id") or source_metric_snapshot_id),
                "source_content_hash": str(metric.get("source_content_hash") or source_metric_snapshot_hash),
                "semantic_view": str(metric.get("semantic_view") or f"semantic.enterprise_metrics.{metric_id}"),
                "dimension_hash": dimension_hash,
                "dimension_scope": dimension_scope,
                "metric_value": value,
                "target_value": optional_float(metric.get("target_value")),
                "prior_value": prior_value,
                "delta_value": delta_value,
                "metric_unit": str(metric.get("metric_unit") or metric.get("unit") or "count"),
                "currency": metric.get("currency"),
                "threshold_status": status,
                "trend": normalized(metric.get("trend"), allowed=ALLOWED_TRENDS, default=derive_trend(delta_value)),
                "freshness_slo_minutes": int_value(metric.get("freshness_slo_minutes"), default=240),
                "freshness_age_minutes": int_value(metric.get("freshness_age_minutes"), default=0),
                "quality_passed": quality_passed,
                "source_metric_snapshot_id": source_metric_snapshot_id,
                "source_metric_snapshot_hash": source_metric_snapshot_hash,
                "semantic_registry_hash": semantic_registry_hash,
                "blocker_count": int_value(metric.get("blocker_count"), default=0),
                "top_blocker_gate": metric.get("top_blocker_gate"),
                "built_at": built_at,
            }
        )
    return rows


def build_executive_scorecard_rows(kpi_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kpi in kpi_rows:
        rows.append(
            {
                "product_id": PRODUCT_ID,
                "dataset_snapshot_id": kpi["dataset_snapshot_id"],
                "scorecard_id": stable_id(
                    "executive-scorecard",
                    kpi["dataset_snapshot_id"],
                    kpi["org_id"],
                    kpi["report_date"],
                    kpi["metric_id"],
                    kpi["source_data_product"],
                    kpi["dimension_hash"],
                ),
                "scorecard_name": "Enterprise Executive KPI Scorecard",
                "org_id": kpi["org_id"],
                "report_date": kpi["report_date"],
                "section": section_for_metric(kpi["metric_domain"], kpi["metric_id"]),
                "metric_id": kpi["metric_id"],
                "metric_name": kpi["metric_name"],
                "actual_value": kpi["metric_value"],
                "target_value": kpi["target_value"],
                "prior_value": kpi["prior_value"],
                "delta_value": kpi["delta_value"],
                "metric_unit": kpi["metric_unit"],
                "currency": kpi["currency"],
                "status": kpi["threshold_status"],
                "trend": kpi["trend"],
                "blocker_count": kpi["blocker_count"],
                "top_blocker_gate": kpi["top_blocker_gate"],
                "certification_status": kpi["certification_status"],
                "source_data_product": kpi["source_data_product"],
                "source_snapshot_id": kpi["source_snapshot_id"],
                "source_metric_snapshot_id": kpi["source_metric_snapshot_id"],
                "source_metric_snapshot_hash": kpi["source_metric_snapshot_hash"],
                "semantic_registry_hash": kpi["semantic_registry_hash"],
                "built_at": kpi["built_at"],
                "quality_passed": kpi["quality_passed"],
            }
        )
    return rows


def build_manifest(
    *,
    snapshot_id: str,
    generated_at: str,
    input_path: Path,
    source_metric_snapshot: dict[str, Any],
    source_metric_snapshot_hash: str,
    output_dir: Path,
    layer_snapshots: tuple[LayerSnapshot, ...],
    kpi_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    layers = {snapshot.name: snapshot.as_manifest_entry(output_dir) for snapshot in layer_snapshots}
    quality_passed = all(snapshot.quality_passed for snapshot in layer_snapshots)
    primary_layer = layers["gold.executive_scorecard_daily"]
    source_products = sorted({str(row["source_data_product"]) for row in kpi_rows})
    return {
        "pipeline": PIPELINE_NAME,
        "product_id": PRODUCT_ID,
        "snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "input": {
            "path": input_path.as_posix(),
            "content_hash": source_metric_snapshot_hash,
            "artifact_type": source_metric_snapshot.get("artifact_type"),
            "snapshot_id": source_metric_snapshot.get("snapshot_id"),
            "semantic_registry_hash": source_metric_snapshot.get("semantic_registry_hash"),
            "semantic_views_manifest_hash": source_metric_snapshot.get("semantic_views_manifest_hash"),
            "metric_count": len(semantic_metrics(source_metric_snapshot)),
        },
        "layers": layers,
        "lineage_edges": scorecard_lineage_edges(source_products),
        "source_positions": [],
        "upstream_quality_passed": bool(source_metric_snapshot.get("upstream_quality_passed", quality_passed)),
        "row_count": primary_layer["row_count"],
        "content_hash": combined_layer_hash(layer_snapshots),
        "quality_passed": quality_passed,
        "metric_count": len(kpi_rows),
        "source_data_products": source_products,
    }


def scorecard_lineage_edges(source_data_products: list[str]) -> list[dict[str, str]]:
    edges = [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": source_data_product,
            "target": "gold.enterprise_kpi_daily",
        }
        for source_data_product in source_data_products
    ]
    edges.append(
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.enterprise_kpi_daily",
            "target": "gold.executive_scorecard_daily",
        }
    )
    return edges


def validate_semantic_snapshot_input(path: Path, snapshot: dict[str, Any]) -> None:
    if snapshot.get("artifact_type") != "semantic_metric_snapshot.v1":
        raise ValueError(f"{path}: expected artifact_type=semantic_metric_snapshot.v1")
    if snapshot.get("use_case_id") != "enterprise-kpi-scorecard":
        raise ValueError(f"{path}: expected use_case_id=enterprise-kpi-scorecard")
    if not snapshot.get("snapshot_id"):
        raise ValueError(f"{path}: snapshot_id is required")
    if not snapshot.get("report_date"):
        raise ValueError(f"{path}: report_date is required")
    if not snapshot.get("semantic_registry_hash"):
        raise ValueError(f"{path}: semantic_registry_hash is required")
    metrics = snapshot.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        raise ValueError(f"{path}: metrics must be a non-empty list")
    for index, metric in enumerate(metrics):
        if not isinstance(metric, dict):
            raise ValueError(f"{path}: metrics[{index}] must be an object")
        missing = [
            key
            for key in ("metric_id", "org_id", "metric_value", "source_data_product", "quality_passed")
            if key not in metric or metric.get(key) in {None, ""}
        ]
        if missing:
            raise ValueError(f"{path}: metrics[{index}] missing required fields: {missing}")
        forbidden = sorted(set(metric) & DIRECT_IDENTIFIER_FIELDS)
        dimension_scope = dict_value(metric.get("dimension_scope"))
        forbidden.extend(sorted(set(dimension_scope) & DIRECT_IDENTIFIER_FIELDS))
        if forbidden:
            raise ValueError(f"{path}: metrics[{index}] contains direct identifier fields: {forbidden}")


def validate_enterprise_kpi_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("enterprise_kpi_rows_empty")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        for key in ("org_id", "report_date", "metric_id", "source_data_product", "kpi_daily_id"):
            if not row.get(key):
                errors.append(f"enterprise_kpi[{index}].{key}_missing")
        key = str(row.get("kpi_daily_id"))
        if key in seen:
            errors.append(f"enterprise_kpi[{index}].kpi_daily_id_duplicate")
        seen.add(key)
        if row.get("threshold_status") not in ALLOWED_THRESHOLD_STATUS:
            errors.append(f"enterprise_kpi[{index}].threshold_status_invalid")
        if row.get("trend") not in ALLOWED_TRENDS:
            errors.append(f"enterprise_kpi[{index}].trend_invalid")
        if row.get("certification_status") not in ALLOWED_CERTIFICATION_STATUS:
            errors.append(f"enterprise_kpi[{index}].certification_status_invalid")
        if row.get("metric_status") not in ALLOWED_METRIC_STATUS:
            errors.append(f"enterprise_kpi[{index}].metric_status_invalid")
        if row.get("quality_passed") is not True:
            errors.append(f"enterprise_kpi[{index}].quality_not_passed")
        if int_value(row.get("freshness_age_minutes"), default=0) > int_value(row.get("freshness_slo_minutes"), default=0):
            errors.append(f"enterprise_kpi[{index}].freshness_slo_breached")
    return tuple(errors)


def validate_executive_scorecard_rows(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    if not rows:
        errors.append("executive_scorecard_rows_empty")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        for key in ("org_id", "report_date", "scorecard_id", "section", "metric_id", "source_data_product"):
            if not row.get(key):
                errors.append(f"executive_scorecard[{index}].{key}_missing")
        key = str(row.get("scorecard_id"))
        if key in seen:
            errors.append(f"executive_scorecard[{index}].scorecard_id_duplicate")
        seen.add(key)
        if row.get("status") not in ALLOWED_THRESHOLD_STATUS:
            errors.append(f"executive_scorecard[{index}].status_invalid")
        if row.get("trend") not in ALLOWED_TRENDS:
            errors.append(f"executive_scorecard[{index}].trend_invalid")
        if row.get("certification_status") not in ALLOWED_CERTIFICATION_STATUS:
            errors.append(f"executive_scorecard[{index}].certification_status_invalid")
        if row.get("quality_passed") is not True:
            errors.append(f"executive_scorecard[{index}].quality_not_passed")
    return tuple(errors)


def write_layer_snapshot(
    name: str,
    path: Path,
    rows: list[dict[str, Any]],
    *,
    quality_errors: tuple[str, ...],
) -> LayerSnapshot:
    write_jsonl(path, rows)
    return LayerSnapshot(
        name=name,
        path=path,
        row_count=len(rows),
        content_hash=hash_file(path),
        quality_passed=not quality_errors,
        quality_errors=quality_errors,
    )


def semantic_metrics(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in snapshot.get("metrics", []) if isinstance(item, dict)]


def section_for_metric(metric_domain: str, metric_id: str) -> str:
    domain = metric_domain.lower()
    metric = metric_id.lower()
    if domain == "finance" or "revenue" in metric or "refund" in metric:
        return "finance"
    if domain == "customer" or "customer" in metric or "support" in metric:
        return "customer"
    if domain in {"compliance", "risk-compliance"} or "risk" in metric or "access" in metric:
        return "risk"
    if domain == "enterprise-reporting" or "quality" in metric or "lineage" in metric or "contract" in metric:
        return "data_trust"
    if domain == "recommendation" or "recommendation" in metric:
        return "product"
    return "enterprise"


def normalized(value: Any, *, allowed: set[str], default: str) -> str:
    if isinstance(value, str) and value.upper() in allowed:
        return value.upper()
    return default


def derive_trend(delta_value: float | None) -> str:
    if delta_value is None:
        return "UNKNOWN"
    if delta_value > 0:
        return "UP"
    if delta_value < 0:
        return "DOWN"
    return "FLAT"


def optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float_value(value)


def float_value(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return 0.0


def int_value(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(float(value))
    return default


def dict_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items() if item is not None}
    return {}


def stable_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def stable_id(*parts: Any) -> str:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return digest[:32]


def combined_layer_hash(layer_snapshots: tuple[LayerSnapshot, ...]) -> str:
    return stable_hash(
        [
            {
                "name": snapshot.name,
                "content_hash": snapshot.content_hash,
                "row_count": snapshot.row_count,
            }
            for snapshot in layer_snapshots
        ]
    )


def hash_file(path: str | Path) -> str:
    data = Path(path).read_bytes()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(f"{canonical_json(row)}\n")


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _compact_timestamp(timestamp: str) -> str:
    return "".join(char for char in timestamp if char.isdigit())[:14]
