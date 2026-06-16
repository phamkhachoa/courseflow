from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import uuid
from typing import Any

from enterprise_df.catalog import canonical_json, hash_file, load_json
from enterprise_df.contracts import ValidationResult


OPENLINEAGE_SCHEMA_URL = "https://openlineage.io/spec/OpenLineage.json#/definitions/RunEvent"
DEFAULT_NAMESPACE = "enterprise-df://local"
DEFAULT_PRODUCER = "https://enterprise-df.local/openlineage-export"
ENTERPRISE_DF_FACET_SCHEMA_BASE = "https://enterprise-df.local/schemas/openlineage"


def build_openlineage_events(
    catalog_bundle: dict[str, Any],
    *,
    namespace: str = DEFAULT_NAMESPACE,
    producer: str = DEFAULT_PRODUCER,
) -> list[dict[str, Any]]:
    data_products = {
        data_product.get("name"): data_product
        for data_product in catalog_bundle.get("data_products", [])
        if isinstance(data_product, dict) and isinstance(data_product.get("name"), str)
    }
    topics = {
        topic.get("name"): topic
        for topic in catalog_bundle.get("topics", [])
        if isinstance(topic, dict) and isinstance(topic.get("name"), str)
    }
    events = [
        openlineage_event(
            run,
            data_products=data_products,
            topics=topics,
            namespace=namespace,
            producer=producer,
        )
        for run in catalog_bundle.get("run_evidence", [])
        if isinstance(run, dict)
    ]
    return sorted(events, key=lambda event: (event["job"]["name"], event["run"]["runId"]))


def write_openlineage_events(
    catalog_bundle_path: str | Path,
    output_path: str | Path,
    *,
    namespace: str = DEFAULT_NAMESPACE,
    producer: str = DEFAULT_PRODUCER,
) -> dict[str, Any]:
    bundle_path = Path(catalog_bundle_path)
    catalog_bundle = load_json(bundle_path)
    events = build_openlineage_events(catalog_bundle, namespace=namespace, producer=producer)
    result = validate_openlineage_events(events)
    if not result.ok:
        raise ValueError("; ".join(result.errors))

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(f"{canonical_json(event)}\n" for event in events), encoding="utf-8")
    return {
        "output_path": target,
        "event_count": len(events),
        "content_hash": hash_file(target),
        "catalog_bundle_hash": hash_file(bundle_path),
        "namespace": namespace,
        "producer": producer,
    }


def openlineage_event(
    run: dict[str, Any],
    *,
    data_products: dict[str, dict[str, Any]],
    topics: dict[str, dict[str, Any]],
    namespace: str,
    producer: str,
) -> dict[str, Any]:
    run_urn = str(run.get("urn"))
    inputs, outputs = run_datasets(run)
    return {
        "eventType": "COMPLETE" if run.get("quality_passed") is True else "FAIL",
        "eventTime": event_time(run),
        "producer": producer,
        "schemaURL": OPENLINEAGE_SCHEMA_URL,
        "run": {
            "runId": stable_run_id(run_urn),
            "facets": {
                "enterpriseDf_run": enterprise_run_facet(run, producer),
            },
        },
        "job": {
            "namespace": namespace,
            "name": str(run.get("pipeline") or "unknown_pipeline"),
            "facets": {
                "enterpriseDf_job": enterprise_job_facet(run, producer),
            },
        },
        "inputs": [
            dataset_entry(name, kind, data_products=data_products, topics=topics, namespace=namespace, producer=producer)
            for kind, name in inputs
        ],
        "outputs": [
            dataset_entry(name, kind, data_products=data_products, topics=topics, namespace=namespace, producer=producer)
            for kind, name in outputs
        ],
    }


def run_datasets(run: dict[str, Any]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    topic = run.get("topic")
    bronze_target = run.get("bronze_target")
    if isinstance(topic, str) and isinstance(bronze_target, str):
        return [("topic", topic)], [("data_product", bronze_target)]

    edges = run_transform_edges(run)
    if not edges:
        return [], []
    sources = [edge["source"] for edge in edges]
    targets = [edge["target"] for edge in edges]
    target_set = set(targets)
    input_names = [name for name in sources if name not in target_set]
    if not input_names:
        input_names = sources[:1]
    return (
        [("data_product", name) for name in unique(input_names)],
        [("data_product", name) for name in unique(targets)],
    )


def run_transform_edges(run: dict[str, Any]) -> list[dict[str, str]]:
    explicit_edges = run.get("lineage_edges")
    if isinstance(explicit_edges, list):
        parsed = [
            {"source": edge["source"], "target": edge["target"]}
            for edge in explicit_edges
            if isinstance(edge, dict)
            and edge.get("type", "RUN_LAYER_TRANSFORM") == "RUN_LAYER_TRANSFORM"
            and isinstance(edge.get("source"), str)
            and isinstance(edge.get("target"), str)
        ]
        if parsed:
            return parsed
    layer_names = ordered_layer_names(run.get("layers", {}))
    return [
        {"source": source, "target": target}
        for source, target in zip(layer_names, layer_names[1:])
    ]


def dataset_entry(
    name: str,
    kind: str,
    *,
    data_products: dict[str, dict[str, Any]],
    topics: dict[str, dict[str, Any]],
    namespace: str,
    producer: str,
) -> dict[str, Any]:
    metadata = topics.get(name) if kind == "topic" else data_products.get(name)
    facets: dict[str, Any] = {
        "enterpriseDf_dataset": enterprise_dataset_facet(name, kind, metadata or {}, producer),
    }
    schema_facet = schema_dataset_facet(metadata or {}, producer)
    if schema_facet:
        facets["schema"] = schema_facet
    return {
        "namespace": f"{namespace}/{kind}s",
        "name": name,
        "facets": facets,
    }


def enterprise_run_facet(run: dict[str, Any], producer: str) -> dict[str, Any]:
    return {
        "_producer": producer,
        "_schemaURL": f"{ENTERPRISE_DF_FACET_SCHEMA_BASE}/EnterpriseDfRunFacet.v1.json",
        "runUrn": run.get("urn"),
        "manifestPath": run.get("manifest_path"),
        "manifestHash": run.get("manifest_hash"),
        "product": run.get("product"),
        "topic": run.get("topic"),
        "bronzeTarget": run.get("bronze_target"),
        "snapshotId": run.get("snapshot_id"),
        "ingestRunId": run.get("ingest_run_id"),
        "qualityPassed": run.get("quality_passed"),
        "upstreamQualityPassed": run.get("upstream_quality_passed"),
        "rowCount": run.get("row_count"),
        "contentHash": run.get("content_hash"),
        "sourcePositions": run.get("source_positions", []),
    }


def enterprise_job_facet(run: dict[str, Any], producer: str) -> dict[str, Any]:
    return {
        "_producer": producer,
        "_schemaURL": f"{ENTERPRISE_DF_FACET_SCHEMA_BASE}/EnterpriseDfJobFacet.v1.json",
        "pipeline": run.get("pipeline"),
        "product": run.get("product"),
    }


def enterprise_dataset_facet(name: str, kind: str, metadata: dict[str, Any], producer: str) -> dict[str, Any]:
    privacy = metadata.get("privacy") if isinstance(metadata.get("privacy"), dict) else {}
    return {
        "_producer": producer,
        "_schemaURL": f"{ENTERPRISE_DF_FACET_SCHEMA_BASE}/EnterpriseDfDatasetFacet.v1.json",
        "urn": metadata.get("urn"),
        "kind": kind,
        "name": name,
        "product": metadata.get("product"),
        "domain": metadata.get("domain"),
        "layer": metadata.get("layer"),
        "classification": privacy.get("classification"),
        "containsPii": privacy.get("contains_pii"),
        "dataResidency": privacy.get("data_residency"),
        "retentionDays": privacy.get("retention_days"),
    }


def schema_dataset_facet(metadata: dict[str, Any], producer: str) -> dict[str, Any] | None:
    columns = metadata.get("columns")
    if isinstance(columns, list) and columns:
        safe_columns = [
            column for column in columns
            if isinstance(column, dict)
            and isinstance(column.get("name"), str)
            and column.get("name") not in {"raw_payload", "raw_headers"}
        ]
        return {
            "_producer": producer,
            "_schemaURL": "https://openlineage.io/spec/facets/1-1-1/SchemaDatasetFacet.json",
            "fields": [
                {
                    "name": column.get("name"),
                    "type": column.get("type"),
                    "description": column.get("description"),
                }
                for column in safe_columns
            ],
        }
    schema = metadata.get("schema")
    if isinstance(schema, dict) and schema:
        return {
            "_producer": producer,
            "_schemaURL": "https://openlineage.io/spec/facets/1-1-1/SchemaDatasetFacet.json",
            "fields": [
                {
                    "name": "payload",
                    "type": schema.get("format"),
                    "description": schema.get("payload_schema"),
                }
            ],
        }
    return None


def validate_openlineage_events(events: list[dict[str, Any]]) -> ValidationResult:
    result = ValidationResult()
    if not events:
        result.error(Path("openlineage"), "at least one OpenLineage event is required")
        return result
    for index, event in enumerate(events):
        result.checked_count += 1
        validate_openlineage_event(Path(f"openlineage[{index}]"), event, result)
    return result


def validate_openlineage_event(path: Path, event: dict[str, Any], result: ValidationResult) -> None:
    if event.get("eventType") not in {"START", "RUNNING", "COMPLETE", "FAIL", "ABORT", "OTHER"}:
        result.error(path, "eventType must be a valid OpenLineage run state")
    if not isinstance(event.get("eventTime"), str) or not parse_time(event.get("eventTime")):
        result.error(path, "eventTime must be an ISO-8601 timestamp")
    for key in ("producer", "schemaURL"):
        if not isinstance(event.get(key), str) or not event[key].strip():
            result.error(path, f"{key} must be a non-empty string")
    run = event.get("run")
    if not isinstance(run, dict) or not isinstance(run.get("runId"), str) or not run.get("runId"):
        result.error(path, "run.runId must be a non-empty string")
    job = event.get("job")
    if not isinstance(job, dict):
        result.error(path, "job must be an object")
    else:
        for key in ("namespace", "name"):
            if not isinstance(job.get(key), str) or not job[key].strip():
                result.error(path, f"job.{key} must be a non-empty string")
    for key in ("inputs", "outputs"):
        value = event.get(key)
        if not isinstance(value, list):
            result.error(path, f"{key} must be a list")
            continue
        for dataset_index, dataset in enumerate(value):
            if not isinstance(dataset, dict):
                result.error(path, f"{key}[{dataset_index}] must be an object")
                continue
            for dataset_key in ("namespace", "name"):
                if not isinstance(dataset.get(dataset_key), str) or not dataset[dataset_key].strip():
                    result.error(path, f"{key}[{dataset_index}].{dataset_key} must be a non-empty string")


def event_time(run: dict[str, Any]) -> str:
    value = run.get("generated_at") or run.get("ingested_at")
    if isinstance(value, str) and parse_time(value):
        return value
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def stable_run_id(run_urn: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, run_urn))


def ordered_layer_names(layers: object) -> list[str]:
    if not isinstance(layers, dict):
        return []
    return sorted(
        [name for name in layers if isinstance(name, str)],
        key=lambda name: (layer_rank(name), name),
    )


def layer_rank(name: str) -> int:
    if name.startswith("bronze."):
        return 0
    if name.startswith("silver."):
        return 1
    if name.startswith("gold."):
        return 2
    return 3


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
