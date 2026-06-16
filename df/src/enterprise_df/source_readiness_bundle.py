from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from enterprise_df.catalog import canonical_json, write_catalog_bundle
from enterprise_df.change_requests import write_change_control_evidence_report
from enterprise_df.ingestion import BronzeIngestionResult, run_bronze_ingestion
from enterprise_df.offset_ledger import write_offset_ledger_report
from enterprise_df.openlineage import write_openlineage_events
from enterprise_df.schema_registry import write_schema_registry_report
from enterprise_df.source_bridge import SourceBridgeResult, run_source_bridge_preflight
from enterprise_df.source_registry import find_source_entry, write_source_readiness_report


REPORT_VERSION = 1
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}


@dataclass(frozen=True)
class SourceReadinessBundleResult:
    source_id: str
    environment: str
    output_dir: Path
    summary_path: Path
    summary: dict[str, Any]
    bridge: SourceBridgeResult | None
    ingestion: BronzeIngestionResult
    replay: BronzeIngestionResult
    readiness_path: Path
    readiness: dict[str, Any]


def run_source_readiness_bundle(
    root: str | Path,
    source_id: str,
    input_path: str | Path,
    output_dir: str | Path,
    *,
    environment: str = "local",
    bundle_id: str | None = None,
    generated_at: str | None = None,
    ingested_at: str | None = None,
    replayed_at: str | None = None,
    schema_registry_uri: str | None = None,
    change_request_id: str | None = None,
    target_snapshot_id: str | None = None,
    table_metadata_uri: str | None = None,
    table_metadata_hash: str | None = None,
    openlineage_namespace: str | None = None,
    openlineage_producer: str | None = None,
) -> SourceReadinessBundleResult:
    platform_root = Path(root)
    source_entry = find_source_entry(platform_root, source_id)
    if source_entry is None:
        raise KeyError(f"source is not registered: {source_id}")
    source = mapping(source_entry, "source")
    canonical = mapping(source_entry, "canonical")
    bridge_config = mapping(source_entry, "bridge")
    topic = required_string(canonical, "topic", source_id)
    bronze_target = required_string(canonical, "bronzeTarget", source_id)
    target_dir = Path(output_dir)
    generated = generated_at or utc_now()
    resolved_bundle_id = bundle_id or f"{source_id}-{compact_timestamp(generated)}"

    bridge_result: SourceBridgeResult | None = None
    bronze_input_path = Path(input_path)
    if bridge_config.get("required") is True:
        bridge_result = run_source_bridge_preflight(
            platform_root,
            source_id,
            input_path,
            target_dir / "source-bridge",
            normalized_at=generated,
            bridge_run_id=f"{resolved_bundle_id}-bridge",
        )
        bronze_input_path = bridge_result.normalized_path

    first_ingested_at = ingested_at or generated
    replay_ingested_at = replayed_at or generated
    ingestion = run_bronze_ingestion(
        platform_root,
        topic,
        bronze_input_path,
        target_dir / "bronze",
        ingested_at=first_ingested_at,
        ingest_run_id=f"{resolved_bundle_id}-first",
        schema_id=schema_id(topic, environment),
    )
    replay = run_bronze_ingestion(
        platform_root,
        topic,
        bronze_input_path,
        target_dir / "bronze",
        ingested_at=replay_ingested_at,
        ingest_run_id=f"{resolved_bundle_id}-replay",
        schema_id=schema_id(topic, environment),
    )

    schema = write_schema_registry_report(
        platform_root,
        target_dir / "schema" / f"{source_id}.schema-registry.json",
        topic_name=topic,
        registry_uri=schema_registry_uri,
        generated_at=generated,
    )
    change_control = None
    if change_request_id:
        change_control = write_change_control_evidence_report(
            platform_root,
            target_dir / "change-control" / f"{source_id}.change-control.json",
            request_id=change_request_id,
            environment=environment,
            generated_at=generated,
        )

    offset_ledger = write_offset_ledger_report(
        platform_root,
        target_dir / "offset-ledger" / f"{source_id}.offset-ledger.json",
        source_id=source_id,
        environment=environment,
        ingestion_manifest_path=ingestion.manifest_path,
        replay_manifest_path=replay.manifest_path,
        target_snapshot_id=target_snapshot_id,
        table_metadata_uri=table_metadata_uri,
        table_metadata_hash=table_metadata_hash,
        committed_at=first_ingested_at,
        generated_at=generated,
    )
    catalog_path = target_dir / "catalog" / "catalog-bundle.json"
    write_catalog_bundle(
        platform_root,
        catalog_path,
        manifest_paths=[ingestion.manifest_path],
        generated_at=generated,
    )
    openlineage = write_openlineage_events(
        catalog_path,
        target_dir / "lineage" / "openlineage.jsonl",
        namespace=openlineage_namespace or f"enterprise-df://{environment}",
        producer=openlineage_producer or f"https://enterprise-df.{environment}.local/openlineage-export",
    )
    readiness = write_source_readiness_report(
        platform_root,
        target_dir / "readiness" / f"{source_id}.source-readiness.json",
        source_id=source_id,
        environment=environment,
        ingestion_manifest_path=ingestion.manifest_path,
        bridge_manifest_path=bridge_result.manifest_path if bridge_result else None,
        replay_manifest_path=replay.manifest_path,
        offset_ledger_path=offset_ledger.output_path,
        schema_registry_report_path=schema.output_path,
        change_control_evidence_path=change_control.output_path if change_control else None,
        catalog_bundle_path=catalog_path,
        openlineage_events_path=openlineage["output_path"],
        generated_at=generated,
    )
    summary = build_bundle_summary(
        source_id=source_id,
        source=source,
        canonical=canonical,
        environment=environment,
        bundle_id=resolved_bundle_id,
        generated_at=generated,
        input_path=Path(input_path),
        bridge_result=bridge_result,
        ingestion=ingestion,
        replay=replay,
        schema_path=schema.output_path,
        change_control_path=change_control.output_path if change_control else None,
        offset_ledger_path=offset_ledger.output_path,
        catalog_path=catalog_path,
        openlineage_path=openlineage["output_path"],
        readiness=readiness.report,
        readiness_path=readiness.output_path,
        bronze_target=bronze_target,
    )
    summary_path = target_dir / "summary" / f"{source_id}.source-readiness-bundle.json"
    write_json(summary_path, summary)
    return SourceReadinessBundleResult(
        source_id=source_id,
        environment=environment,
        output_dir=target_dir,
        summary_path=summary_path,
        summary=summary,
        bridge=bridge_result,
        ingestion=ingestion,
        replay=replay,
        readiness_path=readiness.output_path,
        readiness=readiness.report,
    )


def build_bundle_summary(
    *,
    source_id: str,
    source: dict[str, Any],
    canonical: dict[str, Any],
    environment: str,
    bundle_id: str,
    generated_at: str,
    input_path: Path,
    bridge_result: SourceBridgeResult | None,
    ingestion: BronzeIngestionResult,
    replay: BronzeIngestionResult,
    schema_path: Path,
    change_control_path: Path | None,
    offset_ledger_path: Path,
    catalog_path: Path,
    openlineage_path: Path,
    readiness: dict[str, Any],
    readiness_path: Path,
    bronze_target: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "source_readiness_bundle.v1",
        "report_version": REPORT_VERSION,
        "bundle_id": bundle_id,
        "generated_at": generated_at,
        "environment": environment,
        "source_id": source_id,
        "source": {
            "raw_topic": source.get("rawTopic"),
            "canonical_topic": canonical.get("topic"),
            "bronze_target": bronze_target,
            "schema_subject": canonical.get("schemaSubject"),
        },
        "input": {
            "uri": input_path.as_posix(),
            "mode": "bridge_normalized" if bridge_result else "direct_canonical",
        },
        "artifacts": {
            "bridge_manifest": bridge_result.manifest_path.as_posix() if bridge_result else None,
            "ingestion_manifest": ingestion.manifest_path.as_posix(),
            "replay_manifest": replay.manifest_path.as_posix(),
            "schema_registry_report": schema_path.as_posix(),
            "change_control_evidence": change_control_path.as_posix() if change_control_path else None,
            "offset_ledger": offset_ledger_path.as_posix(),
            "catalog_bundle": catalog_path.as_posix(),
            "openlineage_events": openlineage_path.as_posix(),
            "source_readiness_report": readiness_path.as_posix(),
        },
        "quality": {
            "bridge_passed": bridge_result.manifest["quality_passed"] if bridge_result else None,
            "ingestion_passed": ingestion.manifest["quality_passed"],
            "replay_passed": replay.manifest["quality_passed"],
            "readiness_passed": readiness.get("passed"),
            "failure_count": len(readiness.get("failures", [])),
        },
        "readiness_id": readiness.get("readiness_id"),
        "readiness_state": readiness.get("readiness_state"),
        "passed": readiness.get("passed") is True,
    }


def schema_id(topic: str, environment: str) -> str:
    if environment in PRODUCTION_LIKE_ENVIRONMENTS:
        return f"registry:{topic}:1"
    return f"local:{topic}:1"


def mapping(value: dict[str, Any], key: str) -> dict[str, Any]:
    item = value.get(key)
    return item if isinstance(item, dict) else {}


def required_string(value: dict[str, Any], key: str, source_id: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"{source_id}: {key} is required")
    return item


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compact_timestamp(value: str) -> str:
    return "".join(char for char in value if char.isdigit())[:14]
