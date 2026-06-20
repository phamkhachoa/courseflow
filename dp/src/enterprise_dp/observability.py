from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.contracts import ValidationResult


FORBIDDEN_METRIC_LABELS = {"release_id", "snapshot_id", "dataset_snapshot_id", "content_hash", "manifest_hash"}
METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
LABEL_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


@dataclass(frozen=True)
class Metric:
    name: str
    value: float | int
    labels: dict[str, str]
    help: str
    type: str = "gauge"

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "help": self.help,
            "type": self.type,
        }


def build_observability_snapshot(
    catalog_bundle: dict[str, Any],
    *,
    release_evidences: list[dict[str, Any]] | None = None,
    environment: str = "local",
    generated_at: str | None = None,
) -> dict[str, Any]:
    releases = release_evidences or []
    product_domain_by_dataset = data_product_index(catalog_bundle)
    metrics: list[Metric] = []
    metrics.extend(catalog_metrics(catalog_bundle, environment=environment))
    metrics.extend(run_metrics(catalog_bundle, environment=environment, product_domain_by_dataset=product_domain_by_dataset))
    metrics.extend(release_metrics(releases, environment=environment, product_domain_by_dataset=product_domain_by_dataset))
    metrics.extend(cost_metrics(catalog_bundle, environment=environment, product_domain_by_dataset=product_domain_by_dataset))
    summary = {
        "artifact_type": "enterprise_dp_observability_snapshot.v1",
        "generated_at": generated_at or _utc_now(),
        "environment": environment,
        "catalog": {
            "summary": catalog_bundle.get("summary", {}),
            "bundle_hash": None,
        },
        "release_evidence": [
            release_summary(release)
            for release in releases
        ],
        "cost_attribution": cost_attribution(catalog_bundle, product_domain_by_dataset=product_domain_by_dataset),
        "metrics_count": len(metrics),
        "high_cardinality_omitted_from_metric_labels": sorted(FORBIDDEN_METRIC_LABELS),
        "metrics": [metric.as_dict() for metric in metrics],
    }
    return summary


def write_observability_artifacts(
    catalog_bundle_path: str | Path,
    *,
    metrics_output_path: str | Path,
    summary_output_path: str | Path,
    release_evidence_paths: list[str | Path] | None = None,
    environment: str = "local",
    generated_at: str | None = None,
) -> dict[str, Any]:
    catalog_path = Path(catalog_bundle_path)
    catalog_bundle = load_json(catalog_path)
    releases = [load_json(Path(path)) for path in release_evidence_paths or []]
    snapshot = build_observability_snapshot(
        catalog_bundle,
        release_evidences=releases,
        environment=environment,
        generated_at=generated_at,
    )
    snapshot["catalog"]["bundle_hash"] = hash_file(catalog_path)
    snapshot["release_evidence"] = [
        {
            **summary,
            "evidence_hash": hash_file(path),
        }
        for summary, path in zip(snapshot["release_evidence"], [Path(path) for path in release_evidence_paths or []])
    ]

    result = validate_observability_snapshot(snapshot)
    if not result.ok:
        raise ValueError("; ".join(result.errors))

    metrics_target = Path(metrics_output_path)
    metrics_target.parent.mkdir(parents=True, exist_ok=True)
    metrics_target.write_text(render_prometheus_metrics(metrics_from_snapshot(snapshot)), encoding="utf-8")

    summary_target = Path(summary_output_path)
    summary_target.parent.mkdir(parents=True, exist_ok=True)
    summary_target.write_text(f"{canonical_json(summary_without_metric_objects(snapshot))}\n", encoding="utf-8")

    return {
        "metrics_output_path": metrics_target,
        "summary_output_path": summary_target,
        "metrics_hash": hash_file(metrics_target),
        "summary_hash": hash_file(summary_target),
        "metrics_count": snapshot["metrics_count"],
        "environment": environment,
    }


def catalog_metrics(catalog_bundle: dict[str, Any], *, environment: str) -> list[Metric]:
    metrics: list[Metric] = []
    data_product_counts: dict[tuple[str, str, str], int] = {}
    for data_product in catalog_bundle.get("data_products", []):
        if not isinstance(data_product, dict):
            continue
        key = (
            str(data_product.get("product") or "unknown"),
            str(data_product.get("domain") or "unknown"),
            str(data_product.get("layer") or "UNKNOWN"),
        )
        data_product_counts[key] = data_product_counts.get(key, 0) + 1
    for (product, domain, layer), count in sorted(data_product_counts.items()):
        metrics.append(
            Metric(
                name="enterprise_dp_catalog_data_products_total",
                value=count,
                labels={"environment": environment, "product": product, "domain": domain, "layer": layer},
                help="Number of cataloged enterprise data products by stable ownership labels.",
            )
        )

    topic_counts: dict[tuple[str, str], int] = {}
    for topic in catalog_bundle.get("topics", []):
        if not isinstance(topic, dict):
            continue
        key = (str(topic.get("product") or "unknown"), str(topic.get("domain") or "unknown"))
        topic_counts[key] = topic_counts.get(key, 0) + 1
    for (product, domain), count in sorted(topic_counts.items()):
        metrics.append(
            Metric(
                name="enterprise_dp_catalog_topics_total",
                value=count,
                labels={"environment": environment, "product": product, "domain": domain},
                help="Number of cataloged enterprise topics by stable ownership labels.",
            )
        )

    use_case_counts: dict[tuple[str, str, str], int] = {}
    for use_case in catalog_bundle.get("use_cases", []):
        if not isinstance(use_case, dict):
            continue
        key = (
            str(use_case.get("domain") or "unknown"),
            str(use_case.get("priority") or "unknown"),
            str(use_case.get("status") or "unknown"),
        )
        use_case_counts[key] = use_case_counts.get(key, 0) + 1
    for (domain, priority, status), count in sorted(use_case_counts.items()):
        metrics.append(
            Metric(
                name="enterprise_dp_catalog_use_cases_total",
                value=count,
                labels={"environment": environment, "domain": domain, "priority": priority, "status": status},
                help="Number of registered enterprise data platform use cases.",
            )
        )
    return metrics


def run_metrics(
    catalog_bundle: dict[str, Any],
    *,
    environment: str,
    product_domain_by_dataset: dict[str, dict[str, str]],
) -> list[Metric]:
    metrics: list[Metric] = []
    for run in catalog_bundle.get("run_evidence", []):
        if not isinstance(run, dict):
            continue
        pipeline = str(run.get("pipeline") or "unknown")
        product = str(run.get("product") or "unknown")
        domain = run_domain(run, product_domain_by_dataset)
        labels = {"environment": environment, "product": product, "domain": domain, "pipeline": pipeline}
        metrics.append(
            Metric(
                name="enterprise_dp_run_quality_status",
                value=1 if run.get("quality_passed") is True else 0,
                labels=labels,
                help="Pipeline run quality status from saved run evidence.",
            )
        )
        row_count = run.get("row_count")
        if isinstance(row_count, int | float):
            metrics.append(
                Metric(
                    name="enterprise_dp_run_rows_total",
                    value=row_count,
                    labels=labels,
                    help="Rows produced or approved by saved run evidence.",
                )
            )
    return metrics


def release_metrics(
    releases: list[dict[str, Any]],
    *,
    environment: str,
    product_domain_by_dataset: dict[str, dict[str, str]],
) -> list[Metric]:
    metrics: list[Metric] = []
    for release in releases:
        use_case = str(release.get("use_case_id") or "unknown")
        primary_output = str(release.get("primary_output") or "")
        owner = product_domain_by_dataset.get(primary_output, {})
        base_labels = {
            "environment": environment,
            "use_case": use_case,
            "product": owner.get("product", "unknown"),
            "domain": owner.get("domain", "unknown"),
        }
        metrics.append(
            Metric(
                name="enterprise_dp_release_passed_status",
                value=1 if release.get("release_passed") is True else 0,
                labels=base_labels,
                help="Release evidence pass status without high-cardinality release identifiers.",
            )
        )
        for gate in release.get("gates", []):
            if not isinstance(gate, dict):
                continue
            gate_id = str(gate.get("gate_id") or "unknown")
            metrics.append(
                Metric(
                    name="enterprise_dp_release_gate_status",
                    value=1 if gate.get("passed") is True else 0,
                    labels={**base_labels, "gate_id": gate_id},
                    help="Release gate status by stable use-case and gate labels.",
                )
            )
        freshness = release.get("freshness_report")
        if isinstance(freshness, dict):
            for data_product_name, report in freshness.items():
                if data_product_name == "_meta" or not isinstance(report, dict):
                    continue
                age_seconds = report.get("age_seconds")
                if not isinstance(age_seconds, int | float):
                    continue
                metadata = product_domain_by_dataset.get(data_product_name, {})
                metrics.append(
                    Metric(
                        name="enterprise_dp_data_product_freshness_seconds",
                        value=age_seconds,
                        labels={
                            "environment": environment,
                            "product": metadata.get("product", "unknown"),
                            "domain": metadata.get("domain", "unknown"),
                            "layer": metadata.get("layer", layer_of(data_product_name)),
                            "data_product": data_product_name,
                        },
                        help="Freshness age in seconds from release evidence.",
                    )
                )
        quality = release.get("quality_report")
        if isinstance(quality, dict):
            quarantine_rows = quality.get("quarantine_rows")
            if isinstance(quarantine_rows, int | float):
                metrics.append(
                    Metric(
                        name="enterprise_dp_quarantine_rows",
                        value=quarantine_rows,
                        labels=base_labels,
                        help="Quarantine rows linked to release quality evidence.",
                    )
                )
        ingestion_gate = gate_by_id(release, "P0-INGESTION-LAG")
        details = ingestion_gate.get("details") if isinstance(ingestion_gate, dict) else None
        if isinstance(details, dict) and isinstance(details.get("max_lag_seconds"), int | float):
            topic = str(details.get("topic") or "unknown")
            metrics.append(
                Metric(
                    name="enterprise_dp_ingestion_lag_seconds",
                    value=details["max_lag_seconds"],
                    labels={**base_labels, "topic": topic},
                    help="Maximum source publish to Bronze landing lag from release evidence.",
                )
            )
    return metrics


def cost_metrics(
    catalog_bundle: dict[str, Any],
    *,
    environment: str,
    product_domain_by_dataset: dict[str, dict[str, str]],
) -> list[Metric]:
    return [
        Metric(
            name="enterprise_dp_cost_attribution_rows_total",
            value=entry["row_count"],
            labels={
                "environment": environment,
                "product": entry["product"],
                "domain": entry["domain"],
                "pipeline": entry["pipeline"],
            },
            help="Rows attributed to product/domain/pipeline as a proxy for platform processing cost.",
        )
        for entry in cost_attribution(catalog_bundle, product_domain_by_dataset=product_domain_by_dataset)
    ]


def cost_attribution(
    catalog_bundle: dict[str, Any],
    *,
    product_domain_by_dataset: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    rows_by_key: dict[tuple[str, str, str], int] = {}
    runs_by_key: dict[tuple[str, str, str], int] = {}
    for run in catalog_bundle.get("run_evidence", []):
        if not isinstance(run, dict):
            continue
        pipeline = str(run.get("pipeline") or "unknown")
        product = str(run.get("product") or "unknown")
        domain = run_domain(run, product_domain_by_dataset)
        key = (product, domain, pipeline)
        row_count = run.get("row_count")
        rows_by_key[key] = rows_by_key.get(key, 0) + (int(row_count) if isinstance(row_count, int | float) else 0)
        runs_by_key[key] = runs_by_key.get(key, 0) + 1
    return [
        {
            "product": product,
            "domain": domain,
            "pipeline": pipeline,
            "row_count": rows_by_key[(product, domain, pipeline)],
            "run_count": runs_by_key[(product, domain, pipeline)],
        }
        for product, domain, pipeline in sorted(rows_by_key)
    ]


def validate_observability_snapshot(snapshot: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    if snapshot.get("artifact_type") != "enterprise_dp_observability_snapshot.v1":
        result.error(Path("observability"), "artifact_type must be enterprise_dp_observability_snapshot.v1")
    metrics = snapshot.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        result.error(Path("observability"), "metrics must be a non-empty list")
        return result
    for index, metric in enumerate(metrics):
        result.checked_count += 1
        validate_metric(Path(f"metrics[{index}]"), metric, result)
    return result


def validate_metric(path: Path, metric: object, result: ValidationResult) -> None:
    if not isinstance(metric, dict):
        result.error(path, "metric must be an object")
        return
    name = metric.get("name")
    if not isinstance(name, str) or not METRIC_NAME.fullmatch(name):
        result.error(path, "name must be a valid Prometheus metric name")
    value = metric.get("value")
    if not isinstance(value, int | float):
        result.error(path, "value must be numeric")
    labels = metric.get("labels")
    if not isinstance(labels, dict):
        result.error(path, "labels must be an object")
        return
    for key, value in labels.items():
        if not isinstance(key, str) or not LABEL_NAME.fullmatch(key):
            result.error(path, f"label name {key!r} is invalid")
        if key in FORBIDDEN_METRIC_LABELS:
            result.error(path, f"label {key!r} is high-cardinality and must stay out of metrics")
        if not isinstance(value, str):
            result.error(path, f"label {key!r} value must be a string")


def render_prometheus_metrics(metrics: list[Metric]) -> str:
    by_name: dict[str, Metric] = {}
    for metric in metrics:
        by_name.setdefault(metric.name, metric)
    lines: list[str] = []
    for name in sorted(by_name):
        sample = by_name[name]
        lines.append(f"# HELP {name} {sample.help}")
        lines.append(f"# TYPE {name} {sample.type}")
        for metric in sorted([item for item in metrics if item.name == name], key=lambda item: sorted(item.labels.items())):
            labels = ",".join(
                f'{key}="{escape_label_value(value)}"'
                for key, value in sorted(metric.labels.items())
            )
            lines.append(f"{metric.name}{{{labels}}} {format_metric_value(metric.value)}")
    return "\n".join(lines) + "\n"


def metrics_from_snapshot(snapshot: dict[str, Any]) -> list[Metric]:
    return [
        Metric(
            name=metric["name"],
            value=metric["value"],
            labels=metric["labels"],
            help=metric["help"],
            type=metric.get("type", "gauge"),
        )
        for metric in snapshot.get("metrics", [])
        if isinstance(metric, dict)
    ]


def summary_without_metric_objects(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in snapshot.items()
        if key != "metrics"
    }


def release_summary(release: dict[str, Any]) -> dict[str, Any]:
    return {
        "release_id": release.get("release_id"),
        "environment": release.get("environment"),
        "use_case_id": release.get("use_case_id"),
        "runner_id": release.get("runner_id"),
        "primary_output": release.get("primary_output"),
        "release_passed": release.get("release_passed"),
        "failed_gates": [
            gate.get("gate_id")
            for gate in release.get("gates", [])
            if isinstance(gate, dict) and gate.get("passed") is not True
        ],
    }


def data_product_index(catalog_bundle: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        data_product["name"]: {
            "product": str(data_product.get("product") or "unknown"),
            "domain": str(data_product.get("domain") or "unknown"),
            "layer": str(data_product.get("layer") or layer_of(str(data_product["name"]))),
        }
        for data_product in catalog_bundle.get("data_products", [])
        if isinstance(data_product, dict) and isinstance(data_product.get("name"), str)
    }


def run_domain(run: dict[str, Any], product_domain_by_dataset: dict[str, dict[str, str]]) -> str:
    layers = run.get("layers")
    if isinstance(layers, dict):
        for layer_name in sorted(layers):
            metadata = product_domain_by_dataset.get(str(layer_name))
            if metadata:
                return metadata["domain"]
    bronze_target = run.get("bronze_target")
    if isinstance(bronze_target, str) and bronze_target in product_domain_by_dataset:
        return product_domain_by_dataset[bronze_target]["domain"]
    return "unknown"


def gate_by_id(release: dict[str, Any], gate_id: str) -> dict[str, Any]:
    for gate in release.get("gates", []):
        if isinstance(gate, dict) and gate.get("gate_id") == gate_id:
            return gate
    return {}


def layer_of(data_product_name: str) -> str:
    if data_product_name.startswith("bronze."):
        return "BRONZE"
    if data_product_name.startswith("silver."):
        return "SILVER"
    if data_product_name.startswith("gold."):
        return "GOLD"
    return "UNKNOWN"


def escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def format_metric_value(value: int | float) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
