from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.model_serving import ModelServingMetricsSnapshot
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

METRIC_COUNTERS = (
    "auditFailure",
    "auditRecord",
    "error",
    "fallback",
    "humanReview",
    "ok",
    "request",
)


@dataclass(frozen=True, slots=True)
class ModelServingMetricsExportReport:
    generated_at: str
    source_adapter: str
    export_status: str
    metrics: ModelServingMetricsSnapshot

    def to_dict(self) -> dict[str, Any]:
        return {
            "exportStatus": self.export_status,
            "generatedAt": self.generated_at,
            "metrics": self.metrics.to_dict(),
            "sourceAdapter": self.source_adapter,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "model-serving-metrics-export-v1",
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "source_adapter": self.source_adapter,
            "summary": {
                "export_status": self.export_status,
                "request_count": self.metrics.request_count,
                "success_count": self.metrics.success_count,
                "fallback_count": self.metrics.fallback_count,
                "error_count": self.metrics.error_count,
                "human_review_count": self.metrics.human_review_count,
                "audit_record_count": self.metrics.audit_record_count,
                "audit_failure_count": self.metrics.audit_failure_count,
                "model_count": len(self.metrics.by_model),
            },
            "by_model": self.metrics.by_model,
        }


def load_model_serving_metrics_export(
    ai_root: Path | str,
) -> ModelServingMetricsExportReport | None:
    path = default_snapshot_path(Path(ai_root))
    if not path.exists():
        return None
    return model_serving_metrics_export_from_snapshot(load_yaml(path), path)


def build_model_serving_metrics_export_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    metrics: ModelServingMetricsSnapshot | None = None,
    source_adapter: str = "hosted-model-serving-adapter",
) -> dict[str, Any]:
    root = Path(ai_root)
    if metrics is None:
        loaded = load_model_serving_metrics_export(root)
        metrics = loaded.metrics if loaded is not None else empty_metrics_snapshot()
        source_adapter = loaded.source_adapter if loaded is not None else source_adapter
    report_date = generated_at or date.today().isoformat()
    return ModelServingMetricsExportReport(
        generated_at=report_date,
        source_adapter=source_adapter,
        export_status=derive_export_status(metrics),
        metrics=metrics,
    ).to_snapshot_dict()


def write_model_serving_metrics_export_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
    metrics: ModelServingMetricsSnapshot | None = None,
    source_adapter: str = "hosted-model-serving-adapter",
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    payload = build_model_serving_metrics_export_snapshot(
        root,
        generated_at=generated_at,
        metrics=metrics,
        source_adapter=source_adapter,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
    return target


def model_serving_metrics_export_from_snapshot(
    row: dict[str, Any],
    path: Path,
) -> ModelServingMetricsExportReport:
    summary = row.get("summary")
    if not isinstance(summary, dict):
        raise RegistryValidationError(f"{path} must define mapping field summary")
    by_model = row.get("by_model")
    if not isinstance(by_model, dict):
        raise RegistryValidationError(f"{path} must define mapping field by_model")
    metrics = ModelServingMetricsSnapshot(
        request_count=require_non_negative_int(summary, "request_count", path),
        success_count=require_non_negative_int(summary, "success_count", path),
        fallback_count=require_non_negative_int(summary, "fallback_count", path),
        error_count=require_non_negative_int(summary, "error_count", path),
        human_review_count=require_non_negative_int(summary, "human_review_count", path),
        audit_record_count=require_non_negative_int(summary, "audit_record_count", path),
        audit_failure_count=require_non_negative_int(summary, "audit_failure_count", path),
        by_model=parse_by_model(by_model, path),
    )
    validate_metric_totals(metrics, path)
    export_status = require_str(summary, "export_status", f"{path} summary")
    if export_status != derive_export_status(metrics):
        raise RegistryValidationError(
            f"{path} summary export_status must match metric totals"
        )
    return ModelServingMetricsExportReport(
        generated_at=require_str(row, "generated_at", str(path)),
        source_adapter=require_str(row, "source_adapter", str(path)),
        export_status=export_status,
        metrics=metrics,
    )


def parse_by_model(row: dict[object, object], path: Path) -> dict[str, dict[str, int]]:
    parsed: dict[str, dict[str, int]] = {}
    for model_id, raw_counters in row.items():
        if not isinstance(model_id, str) or not model_id.strip():
            raise RegistryValidationError(f"{path} by_model keys must be model IDs")
        if not isinstance(raw_counters, dict):
            raise RegistryValidationError(f"{path} by_model {model_id} must be a mapping")
        counters: dict[str, int] = {}
        for counter in METRIC_COUNTERS:
            counters[counter] = require_non_negative_int(raw_counters, counter, path)
        parsed[model_id.strip()] = counters
    return dict(sorted(parsed.items()))


def validate_metric_totals(metrics: ModelServingMetricsSnapshot, path: Path) -> None:
    total_request = sum(row["request"] for row in metrics.by_model.values())
    total_ok = sum(row["ok"] for row in metrics.by_model.values())
    total_fallback = sum(row["fallback"] for row in metrics.by_model.values())
    total_error = sum(row["error"] for row in metrics.by_model.values())
    total_human_review = sum(row["humanReview"] for row in metrics.by_model.values())
    total_audit_record = sum(row["auditRecord"] for row in metrics.by_model.values())
    total_audit_failure = sum(row["auditFailure"] for row in metrics.by_model.values())
    expected = {
        "audit_failure_count": (metrics.audit_failure_count, total_audit_failure),
        "audit_record_count": (metrics.audit_record_count, total_audit_record),
        "error_count": (metrics.error_count, total_error),
        "fallback_count": (metrics.fallback_count, total_fallback),
        "human_review_count": (metrics.human_review_count, total_human_review),
        "request_count": (metrics.request_count, total_request),
        "success_count": (metrics.success_count, total_ok),
    }
    for field, (actual, derived) in expected.items():
        if actual != derived:
            raise RegistryValidationError(
                f"{path} summary {field} must equal by_model total {derived}"
            )


def derive_export_status(metrics: ModelServingMetricsSnapshot) -> str:
    if metrics.request_count == 0:
        return "connected_no_traffic"
    if metrics.audit_failure_count:
        return "connected_with_audit_failures"
    if metrics.error_count:
        return "connected_with_errors"
    if metrics.audit_record_count < metrics.request_count:
        return "connected_with_audit_gap"
    return "connected"


def require_non_negative_int(row: dict[object, object], key: str, path: Path) -> int:
    value = row.get(key)
    if not isinstance(value, int) or value < 0:
        raise RegistryValidationError(f"{path} must define non-negative integer {key}")
    return value


def empty_metrics_snapshot() -> ModelServingMetricsSnapshot:
    return ModelServingMetricsSnapshot(
        request_count=0,
        success_count=0,
        fallback_count=0,
        error_count=0,
        human_review_count=0,
        audit_record_count=0,
        audit_failure_count=0,
        by_model={},
    )


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "operations" / "reports" / "model-serving-metrics-export-v1.yaml"
