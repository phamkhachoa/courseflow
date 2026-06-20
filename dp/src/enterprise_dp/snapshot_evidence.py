from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import hash_file, load_json
from enterprise_dp.contracts import load_yaml


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
VALID_ARTIFACT_TYPE = "lakehouse_snapshot_evidence.v1"
VALID_TABLE_FORMATS = {"iceberg"}


@dataclass(frozen=True)
class SnapshotEvidenceResult:
    output_path: Path
    report: dict[str, Any]


def write_snapshot_evidence_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str,
    pipeline_manifest_path: str | Path,
    snapshot_metadata_path: str | Path,
    primary_output: str,
    source_offset_ledger_path: str | Path | None = None,
    release_id: str | None = None,
    use_case_id: str | None = None,
    runner_id: str | None = None,
    code_commit_sha: str | None = None,
    release_evidence_profile_id: str | None = None,
    release_evidence_profile_hash: str | None = None,
    generated_at: str | None = None,
) -> SnapshotEvidenceResult:
    report = build_snapshot_evidence_report(
        root,
        environment=environment,
        pipeline_manifest_path=pipeline_manifest_path,
        snapshot_metadata_path=snapshot_metadata_path,
        primary_output=primary_output,
        source_offset_ledger_path=source_offset_ledger_path,
        release_id=release_id,
        use_case_id=use_case_id,
        runner_id=runner_id,
        code_commit_sha=code_commit_sha,
        release_evidence_profile_id=release_evidence_profile_id,
        release_evidence_profile_hash=release_evidence_profile_hash,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SnapshotEvidenceResult(output_path=target, report=report)


def build_snapshot_evidence_report(
    root: str | Path,
    *,
    environment: str,
    pipeline_manifest_path: str | Path,
    snapshot_metadata_path: str | Path,
    primary_output: str,
    source_offset_ledger_path: str | Path | None = None,
    release_id: str | None = None,
    use_case_id: str | None = None,
    runner_id: str | None = None,
    code_commit_sha: str | None = None,
    release_evidence_profile_id: str | None = None,
    release_evidence_profile_hash: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    pipeline_path = Path(pipeline_manifest_path)
    metadata_path = Path(snapshot_metadata_path)
    ledger_path = Path(source_offset_ledger_path) if source_offset_ledger_path else None
    pipeline_manifest = load_json(pipeline_path)
    snapshot_metadata = load_json(metadata_path)
    source_offset_ledger = load_json(ledger_path) if ledger_path else None
    layers = build_layer_bindings(
        platform_root,
        pipeline_manifest,
        snapshot_metadata,
        primary_output=primary_output,
    )
    checks = snapshot_evidence_checks(
        environment=environment,
        pipeline_manifest=pipeline_manifest,
        pipeline_manifest_path=pipeline_path,
        snapshot_metadata=snapshot_metadata,
        snapshot_metadata_path=metadata_path,
        source_offset_ledger=source_offset_ledger,
        source_offset_ledger_path=ledger_path,
        primary_output=primary_output,
        layers=layers,
        release_id=release_id,
        use_case_id=use_case_id,
        runner_id=runner_id,
        code_commit_sha=code_commit_sha,
        release_evidence_profile_id=release_evidence_profile_id,
        release_evidence_profile_hash=release_evidence_profile_hash,
    )
    passed = all(item["passed"] is True for item in checks)
    pipeline_hash = hash_file(pipeline_path)
    metadata_hash = hash_file(metadata_path)
    ledger_hash = hash_file(ledger_path) if ledger_path else None
    primary_layer = layers.get(primary_output, {})
    return {
        "artifact_type": VALID_ARTIFACT_TYPE,
        "evidence_version": REPORT_VERSION,
        "evidence_id": stable_id(
            "lakehouse-snapshot-evidence",
            environment,
            pipeline_hash,
            metadata_hash,
            ledger_hash,
            primary_output,
            release_id,
        ),
        "generated_at": generated_at or utc_now(),
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "runner_id": runner_id,
        "code_commit_sha": code_commit_sha,
        "release_evidence_profile_id": release_evidence_profile_id,
        "release_evidence_profile_hash": release_evidence_profile_hash,
        "primary_output": primary_output,
        "pipeline": {
            "manifest_uri": pipeline_path.as_posix(),
            "manifest_hash": pipeline_hash,
            "pipeline": pipeline_manifest.get("pipeline"),
            "product_id": pipeline_manifest.get("product_id"),
            "snapshot_id": pipeline_manifest.get("snapshot_id"),
            "generated_at": pipeline_manifest.get("generated_at"),
            "quality_passed": pipeline_manifest.get("quality_passed"),
            "row_count": pipeline_manifest.get("row_count"),
            "content_hash": pipeline_manifest.get("content_hash"),
            "source_positions": pipeline_manifest.get("source_positions", []),
            "input": pipeline_manifest.get("input", {}),
        },
        "snapshot_metadata": {
            "uri": metadata_path.as_posix(),
            "hash": metadata_hash,
            "format": snapshot_metadata.get("format"),
            "snapshot_count": len(snapshot_entries(snapshot_metadata)),
        },
        "source_offset_ledger": source_offset_ledger_summary(ledger_path, source_offset_ledger, ledger_hash),
        "layers": layers,
        "primary_snapshot": primary_layer.get("snapshot"),
        "checks": checks,
        "failures": [
            {"check": item["name"], "details": item.get("details", {})}
            for item in checks
            if item.get("passed") is not True
        ],
        "passed": passed,
    }


def build_layer_bindings(
    root: Path,
    pipeline_manifest: dict[str, Any],
    snapshot_metadata: dict[str, Any],
    *,
    primary_output: str,
) -> dict[str, Any]:
    manifest_layers = mapping(pipeline_manifest, "layers")
    snapshots_by_product = {
        str(snapshot.get("data_product")): snapshot
        for snapshot in snapshot_entries(snapshot_metadata)
        if isinstance(snapshot.get("data_product"), str)
    }
    bindings: dict[str, Any] = {}
    for name in sorted(manifest_layers.keys()):
        if str(name).startswith("bronze."):
            continue
        layer = manifest_layers.get(name)
        if not isinstance(layer, dict):
            continue
        contract = data_product_contract(root, str(name))
        bindings[str(name)] = {
            "data_product": name,
            "primary": name == primary_output,
            "contract": contract,
            "manifest_layer": {
                "path": layer.get("path"),
                "row_count": layer.get("row_count"),
                "content_hash": layer.get("content_hash"),
                "quality_passed": layer.get("quality_passed"),
                "quality_errors": layer.get("quality_errors", []),
            },
            "snapshot": normalize_snapshot(snapshots_by_product.get(str(name))),
        }
    for name, snapshot in snapshots_by_product.items():
        if name not in bindings:
            contract = data_product_contract(root, str(name))
            bindings[name] = {
                "data_product": name,
                "primary": name == primary_output,
                "contract": contract,
                "manifest_layer": None,
                "snapshot": normalize_snapshot(snapshot),
            }
    return bindings


def snapshot_evidence_checks(
    *,
    environment: str,
    pipeline_manifest: dict[str, Any],
    pipeline_manifest_path: Path,
    snapshot_metadata: dict[str, Any],
    snapshot_metadata_path: Path,
    source_offset_ledger: dict[str, Any] | None,
    source_offset_ledger_path: Path | None,
    primary_output: str,
    layers: dict[str, Any],
    release_id: str | None,
    use_case_id: str | None,
    runner_id: str | None,
    code_commit_sha: str | None,
    release_evidence_profile_id: str | None,
    release_evidence_profile_hash: str | None,
) -> list[dict[str, Any]]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    metadata_snapshots = snapshot_entries(snapshot_metadata)
    metadata_products = {
        str(snapshot.get("data_product"))
        for snapshot in metadata_snapshots
        if isinstance(snapshot.get("data_product"), str)
    }
    expected_products = {str(name) for name in layers.keys()}
    missing_snapshots = sorted(expected_products - metadata_products)
    undeclared_snapshots = sorted(metadata_products - expected_products)
    failed_layers = layer_failures(layers, production_like=production_like)
    ledger_checks = source_offset_ledger_checks(
        pipeline_manifest,
        source_offset_ledger,
        source_offset_ledger_path,
        production_like=production_like,
    )
    primary_binding = layers.get(primary_output, {})
    primary_snapshot = mapping(primary_binding, "snapshot")
    checks = [
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check("release_id_present", not production_like or non_empty(release_id), {"release_id": release_id}),
        check("use_case_id_present", not production_like or non_empty(use_case_id), {"use_case_id": use_case_id}),
        check("runner_id_present", not production_like or non_empty(runner_id), {"runner_id": runner_id}),
        check("code_commit_sha_present", not production_like or non_empty(code_commit_sha), {"code_commit_sha": code_commit_sha}),
        check("release_evidence_profile_id_present", not production_like or non_empty(release_evidence_profile_id), {"release_evidence_profile_id": release_evidence_profile_id}),
        check("release_evidence_profile_hash_present", not production_like or is_hash(release_evidence_profile_hash), {"release_evidence_profile_hash": release_evidence_profile_hash}),
        check("pipeline_manifest_present", pipeline_manifest_path.is_file(), {"pipeline_manifest_uri": pipeline_manifest_path.as_posix()}),
        check("snapshot_metadata_present", snapshot_metadata_path.is_file(), {"snapshot_metadata_uri": snapshot_metadata_path.as_posix()}),
        check("snapshot_metadata_format_supported", snapshot_metadata.get("format") in VALID_TABLE_FORMATS, {"format": snapshot_metadata.get("format")}),
        check("pipeline_snapshot_id_present", non_empty(pipeline_manifest.get("snapshot_id")), {"snapshot_id": pipeline_manifest.get("snapshot_id")}),
        check("pipeline_quality_passed", pipeline_manifest.get("quality_passed") is True, {"quality_passed": pipeline_manifest.get("quality_passed")}),
        check("primary_output_in_manifest", primary_output in layers, {"primary_output": primary_output}),
        check("primary_output_has_snapshot", non_empty(primary_snapshot.get("snapshot_id")), {"primary_output": primary_output, "snapshot": primary_snapshot}),
        check("declared_layers_have_snapshots", not missing_snapshots, {"missing_snapshots": missing_snapshots}),
        check("snapshot_products_declared", not undeclared_snapshots, {"undeclared_snapshots": undeclared_snapshots}),
        check("layer_snapshot_bindings_valid", not failed_layers, {"failed_layers": failed_layers}),
        *ledger_checks,
    ]
    return checks


def layer_failures(layers: dict[str, Any], *, production_like: bool) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for data_product, binding in layers.items():
        layer = binding.get("manifest_layer") if isinstance(binding, dict) else None
        snapshot = binding.get("snapshot") if isinstance(binding, dict) else None
        if not isinstance(layer, dict) or not isinstance(snapshot, dict):
            failures.append({"data_product": data_product, "reason": "manifest_layer_or_snapshot_missing"})
            continue
        contract = binding.get("contract") if isinstance(binding, dict) else None
        contract = contract if isinstance(contract, dict) else {}
        expected_row_count = layer.get("row_count")
        expected_content_hash = layer.get("content_hash")
        layer_checks = {
            "contract_registered": contract.get("registered") is True,
            "contract_hash_present": is_hash(contract.get("contract_hash")),
            "contract_version_present": isinstance(contract.get("contract_version"), int),
            "layer_quality_passed": layer.get("quality_passed") is True,
            "layer_row_count_present": isinstance(expected_row_count, int) and expected_row_count >= 0,
            "layer_content_hash_present": is_hash(expected_content_hash),
            "iceberg_table_identifier_present": not production_like or non_empty(snapshot.get("iceberg_table_identifier")),
            "snapshot_id_present": non_empty(snapshot.get("snapshot_id")),
            "metadata_uri_present": non_empty(snapshot.get("metadata_uri")),
            "metadata_hash_present": is_hash(snapshot.get("metadata_hash")),
            "manifest_list_uri_present": not production_like or non_empty(snapshot.get("manifest_list_uri")),
            "manifest_list_hash_present": not production_like or is_hash(snapshot.get("manifest_list_hash")),
            "schema_id_present": not production_like or non_empty(snapshot.get("schema_id")),
            "schema_hash_present": not production_like or is_hash(snapshot.get("schema_hash")),
            "schema_hash_matches_contract": not production_like or snapshot.get("schema_hash") == contract.get("schema_hash"),
            "partition_spec_id_present": not production_like or non_empty(snapshot.get("partition_spec_id")),
            "partition_spec_hash_present": not production_like or is_hash(snapshot.get("partition_spec_hash")),
            "snapshot_row_count_matches": snapshot.get("row_count") == expected_row_count,
            "snapshot_content_hash_matches": snapshot.get("content_hash") == expected_content_hash,
        }
        if not all(layer_checks.values()):
            failures.append(
                {
                    "data_product": data_product,
                    "checks": layer_checks,
                    "expected": {
                        "row_count": expected_row_count,
                        "content_hash": expected_content_hash,
                        "schema_hash": contract.get("schema_hash"),
                    },
                    "contract": contract,
                    "snapshot": snapshot,
                }
            )
    return failures


def source_offset_ledger_checks(
    pipeline_manifest: dict[str, Any],
    source_offset_ledger: dict[str, Any] | None,
    source_offset_ledger_path: Path | None,
    *,
    production_like: bool,
) -> list[dict[str, Any]]:
    input_manifest = mapping(pipeline_manifest, "input")
    upstream_manifest_hash = input_manifest.get("upstream_manifest_hash")
    source_positions = pipeline_manifest.get("source_positions")
    checks = [
        check(
            "source_offset_ledger_attached",
            source_offset_ledger is not None or not production_like,
            {"source_offset_ledger_uri": source_offset_ledger_path.as_posix() if source_offset_ledger_path else None},
        )
    ]
    if source_offset_ledger is None:
        return checks
    ledger_ingestion = mapping(source_offset_ledger, "ingestion")
    ledger_watermarks = source_offset_ledger.get("watermarks")
    checks.extend(
        [
            check("source_offset_ledger_artifact_type", source_offset_ledger.get("artifact_type") == "source_offset_ledger.v1", {"artifact_type": source_offset_ledger.get("artifact_type")}),
            check("source_offset_ledger_passed", source_offset_ledger.get("passed") is True, {"passed": source_offset_ledger.get("passed")}),
            check(
                "ledger_matches_pipeline_upstream_manifest",
                not upstream_manifest_hash or ledger_ingestion.get("manifest_hash") == upstream_manifest_hash,
                {"pipeline_upstream_manifest_hash": upstream_manifest_hash, "ledger_ingestion_manifest_hash": ledger_ingestion.get("manifest_hash")},
            ),
            check(
                "ledger_watermarks_match_pipeline_positions",
                not isinstance(source_positions, list) or watermark_positions(ledger_watermarks) == source_position_ranges(source_positions),
                {"pipeline_source_positions": source_position_ranges(source_positions), "ledger_watermarks": watermark_positions(ledger_watermarks)},
            ),
        ]
    )
    return checks


def source_offset_ledger_summary(
    path: Path | None,
    ledger: dict[str, Any] | None,
    ledger_hash: str | None,
) -> dict[str, Any] | None:
    if path is None or ledger is None:
        return None
    return {
        "uri": path.as_posix(),
        "hash": ledger_hash,
        "ledger_id": ledger.get("ledger_id"),
        "source_id": ledger.get("source_id"),
        "environment": ledger.get("environment"),
        "passed": ledger.get("passed"),
        "ingestion_manifest_hash": mapping(ledger, "ingestion").get("manifest_hash"),
        "target": ledger.get("target", {}),
        "watermarks": ledger.get("watermarks", []),
    }


def snapshot_entries(snapshot_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    value = snapshot_metadata.get("snapshots")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def normalize_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    if snapshot is None:
        return {}
    return {
        "data_product": snapshot.get("data_product"),
        "layer": snapshot.get("layer"),
        "iceberg_table_identifier": snapshot.get("iceberg_table_identifier"),
        "snapshot_id": snapshot.get("snapshot_id"),
        "parent_snapshot_id": snapshot.get("parent_snapshot_id"),
        "sequence_number": snapshot.get("sequence_number"),
        "operation": snapshot.get("operation"),
        "committed_at": snapshot.get("committed_at"),
        "metadata_uri": snapshot.get("metadata_uri"),
        "metadata_hash": snapshot.get("metadata_hash"),
        "manifest_list_uri": snapshot.get("manifest_list_uri"),
        "manifest_list_hash": snapshot.get("manifest_list_hash"),
        "schema_id": snapshot.get("schema_id"),
        "schema_hash": snapshot.get("schema_hash"),
        "partition_spec_id": snapshot.get("partition_spec_id"),
        "partition_spec_hash": snapshot.get("partition_spec_hash"),
        "min_event_time": snapshot.get("min_event_time"),
        "max_event_time": snapshot.get("max_event_time"),
        "freshness_timestamp": snapshot.get("freshness_timestamp"),
        "upstream_snapshot_ids": snapshot.get("upstream_snapshot_ids", []),
        "row_count": snapshot.get("row_count"),
        "content_hash": snapshot.get("content_hash"),
    }


def data_product_contract(root: Path, data_product_name: str) -> dict[str, Any]:
    path = data_product_contract_path(root, data_product_name)
    if path is None:
        return {
            "registered": False,
            "data_product": data_product_name,
            "contract_path": None,
            "contract_hash": None,
            "contract_version": None,
            "layer": None,
            "schema_hash": None,
        }
    contract = load_yaml(path)
    data_product = mapping(contract, "dataProduct")
    schema = mapping(contract, "schema")
    source = mapping(contract, "source")
    return {
        "registered": True,
        "data_product": data_product_name,
        "contract_path": path.as_posix(),
        "contract_hash": hash_file(path),
        "contract_version": contract.get("contractVersion"),
        "layer": data_product.get("layer"),
        "product": data_product.get("product"),
        "domain": data_product.get("domain"),
        "event_time_column": source.get("eventTimeColumn"),
        "schema_hash": content_hash(canonical_json(schema)),
        "schema_column_count": len(schema.get("columns", [])) if isinstance(schema.get("columns"), list) else 0,
    }


def data_product_contract_path(root: Path, data_product_name: str) -> Path | None:
    exact = root / "contracts" / "data-products" / f"{data_product_name}.v1.yaml"
    if exact.is_file():
        return exact
    matches = sorted((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))
    return matches[-1] if matches else None


def watermark_positions(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    positions = []
    for item in value:
        if not isinstance(item, dict):
            continue
        positions.append(
            {
                "source_topic": item.get("source_topic"),
                "source_partition": item.get("source_partition"),
                "min_offset": item.get("min_offset"),
                "max_offset": item.get("max_offset"),
                "row_count": item.get("row_count"),
            }
        )
    return sorted(positions, key=lambda item: canonical_json(item))


def source_position_ranges(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    positions = []
    for item in value:
        if not isinstance(item, dict):
            continue
        positions.append(
            {
                "source_topic": item.get("source_topic"),
                "source_partition": item.get("source_partition"),
                "min_offset": item.get("min_offset"),
                "max_offset": item.get("max_offset"),
                "row_count": item.get("row_count"),
            }
        )
    return sorted(positions, key=lambda item: canonical_json(item))


def mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_hash(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:")


def content_hash(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
