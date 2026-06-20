from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from enterprise_dp.access_grants import validate_access_grant_registry
from enterprise_dp.access_governance import validate_access_persona_registry, validate_consumer_contract_registry
from enterprise_dp.access_policies import validate_access_policy_registry
from enterprise_dp.attestations import validate_evidence_trust_key_registry, verify_external_evidence_attestation
from enterprise_dp.catalog import hash_file, load_json
from enterprise_dp.contracts import load_yaml, validate_contract_tree
from enterprise_dp.domains import validate_domain_registry
from enterprise_dp.ingestion import read_jsonl
from enterprise_dp.products import validate_product_onboarding_tree
from enterprise_dp.quality_profiles import (
    evaluate_quality_profile,
    hash_quality_profile_registry,
    validate_quality_profile_registry,
)
from enterprise_dp.retention import validate_retention_policy_registry
from enterprise_dp.release_profiles import (
    evaluate_release_profile,
    hash_release_profile_registry,
    validate_release_profile_registry,
)
from enterprise_dp.structure import validate_project_structure
from enterprise_dp.usecases import validate_use_case_registry


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    passed: bool
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "passed": self.passed,
            "details": self.details,
        }


def build_recommendation_release_evidence(
    root: str | Path,
    *,
    release_id: str,
    environment: str,
    ingestion_manifest_path: str | Path,
    medallion_manifest_path: str | Path,
    catalog_bundle_path: str | Path,
    approved_bronze_path: str | Path,
    output_path: str | Path,
    generated_at: str | None = None,
    code_commit_sha: str | None = None,
    schema_registry_report_uri: str | None = None,
    schema_registry_report_hash: str | None = None,
    validator_output_uri: str | None = None,
    access_policy_check_id: str | None = None,
    access_policy_report_uri: str | None = None,
    access_policy_report_hash: str | None = None,
    access_grant_evidence_uri: str | None = None,
    access_grant_evidence_hash: str | None = None,
    retention_evidence_uri: str | None = None,
    retention_evidence_hash: str | None = None,
    snapshot_evidence_uri: str | None = None,
    snapshot_evidence_hash: str | None = None,
    approver: str | None = None,
) -> dict[str, Any]:
    evidence = evaluate_recommendation_release_gates(
        root,
        release_id=release_id,
        environment=environment,
        ingestion_manifest_path=ingestion_manifest_path,
        medallion_manifest_path=medallion_manifest_path,
        catalog_bundle_path=catalog_bundle_path,
        approved_bronze_path=approved_bronze_path,
        generated_at=generated_at,
        code_commit_sha=code_commit_sha,
        schema_registry_report_uri=schema_registry_report_uri,
        schema_registry_report_hash=schema_registry_report_hash,
        validator_output_uri=validator_output_uri,
        access_policy_check_id=access_policy_check_id,
        access_policy_report_uri=access_policy_report_uri,
        access_policy_report_hash=access_policy_report_hash,
        access_grant_evidence_uri=access_grant_evidence_uri,
        access_grant_evidence_hash=access_grant_evidence_hash,
        retention_evidence_uri=retention_evidence_uri,
        retention_evidence_hash=retention_evidence_hash,
        snapshot_evidence_uri=snapshot_evidence_uri,
        snapshot_evidence_hash=snapshot_evidence_hash,
        approver=approver,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(evidence)}\n", encoding="utf-8")
    return evidence


def build_pipeline_release_evidence(
    root: str | Path,
    *,
    release_id: str,
    environment: str,
    use_case_id: str,
    runner_id: str,
    runner_input_kind: str | None = None,
    pipeline_manifest_path: str | Path,
    catalog_bundle_path: str | Path,
    primary_output: str,
    output_path: str | Path,
    input_topics: list[str] | tuple[str, ...] | None = None,
    input_data_products: list[str] | tuple[str, ...] | None = None,
    output_data_products: list[str] | tuple[str, ...] | None = None,
    quality_profile_id: str | None = None,
    release_profile_id: str | None = None,
    ingestion_manifest_path: str | Path | None = None,
    generated_at: str | None = None,
    code_commit_sha: str | None = None,
    schema_registry_report_uri: str | None = None,
    schema_registry_report_hash: str | None = None,
    validator_output_uri: str | None = None,
    access_policy_check_id: str | None = None,
    access_policy_report_uri: str | None = None,
    access_policy_report_hash: str | None = None,
    access_grant_evidence_uri: str | None = None,
    access_grant_evidence_hash: str | None = None,
    retention_evidence_uri: str | None = None,
    retention_evidence_hash: str | None = None,
    snapshot_evidence_uri: str | None = None,
    snapshot_evidence_hash: str | None = None,
    approver: str | None = None,
) -> dict[str, Any]:
    evidence = evaluate_pipeline_release_gates(
        root,
        release_id=release_id,
        environment=environment,
        use_case_id=use_case_id,
        runner_id=runner_id,
        runner_input_kind=runner_input_kind,
        pipeline_manifest_path=pipeline_manifest_path,
        catalog_bundle_path=catalog_bundle_path,
        primary_output=primary_output,
        input_topics=input_topics,
        input_data_products=input_data_products,
        output_data_products=output_data_products,
        quality_profile_id=quality_profile_id,
        release_profile_id=release_profile_id,
        ingestion_manifest_path=ingestion_manifest_path,
        generated_at=generated_at,
        code_commit_sha=code_commit_sha,
        schema_registry_report_uri=schema_registry_report_uri,
        schema_registry_report_hash=schema_registry_report_hash,
        validator_output_uri=validator_output_uri,
        access_policy_check_id=access_policy_check_id,
        access_policy_report_uri=access_policy_report_uri,
        access_policy_report_hash=access_policy_report_hash,
        access_grant_evidence_uri=access_grant_evidence_uri,
        access_grant_evidence_hash=access_grant_evidence_hash,
        retention_evidence_uri=retention_evidence_uri,
        retention_evidence_hash=retention_evidence_hash,
        snapshot_evidence_uri=snapshot_evidence_uri,
        snapshot_evidence_hash=snapshot_evidence_hash,
        approver=approver,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(evidence)}\n", encoding="utf-8")
    return evidence


def evaluate_pipeline_release_gates(
    root: str | Path,
    *,
    release_id: str,
    environment: str,
    use_case_id: str,
    runner_id: str,
    runner_input_kind: str | None = None,
    pipeline_manifest_path: str | Path,
    catalog_bundle_path: str | Path,
    primary_output: str,
    input_topics: list[str] | tuple[str, ...] | None = None,
    input_data_products: list[str] | tuple[str, ...] | None = None,
    output_data_products: list[str] | tuple[str, ...] | None = None,
    quality_profile_id: str | None = None,
    release_profile_id: str | None = None,
    ingestion_manifest_path: str | Path | None = None,
    generated_at: str | None = None,
    code_commit_sha: str | None = None,
    schema_registry_report_uri: str | None = None,
    schema_registry_report_hash: str | None = None,
    validator_output_uri: str | None = None,
    access_policy_check_id: str | None = None,
    access_policy_report_uri: str | None = None,
    access_policy_report_hash: str | None = None,
    access_grant_evidence_uri: str | None = None,
    access_grant_evidence_hash: str | None = None,
    retention_evidence_uri: str | None = None,
    retention_evidence_hash: str | None = None,
    snapshot_evidence_uri: str | None = None,
    snapshot_evidence_hash: str | None = None,
    approver: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or _utc_now()
    pipeline_manifest = load_json(Path(pipeline_manifest_path))
    catalog_bundle = load_json(Path(catalog_bundle_path))
    ingestion_manifest = load_json(Path(ingestion_manifest_path)) if ingestion_manifest_path else None
    approved_rows, approved_rows_error = _approved_rows_from_ingestion_manifest(
        Path(ingestion_manifest_path),
        ingestion_manifest,
    ) if ingestion_manifest and ingestion_manifest_path else ([], None)
    resolved_output_products = list(output_data_products or pipeline_manifest.get("layers", {}).keys())
    resolved_input_topics = list(input_topics or [])
    resolved_input_data_products = list(input_data_products or [])
    freshness_report = _pipeline_freshness_report(
        platform_root,
        ingestion_manifest=ingestion_manifest,
        pipeline_manifest=pipeline_manifest,
        generated_at=generated,
        approved_rows=approved_rows,
        approved_rows_error=approved_rows_error,
    )
    primary_layer = pipeline_manifest.get("layers", {}).get(primary_output, {})
    primary_content_hash = primary_layer.get("content_hash") or pipeline_manifest.get("content_hash")
    gates = [
        _contract_gate(platform_root),
        _schema_registry_gate(schema_registry_report_uri, schema_registry_report_hash, root=platform_root, environment=environment, release_id=release_id),
        _access_policy_gate(access_policy_report_uri, access_policy_report_hash, root=platform_root, environment=environment, release_id=release_id),
        _access_grant_evidence_gate(access_grant_evidence_uri, access_grant_evidence_hash, root=platform_root, environment=environment, release_id=release_id),
        _retention_evidence_gate(
            retention_evidence_uri,
            retention_evidence_hash,
            root=platform_root,
            environment=environment,
            release_id=release_id,
            data_product=primary_output,
            dataset_snapshot_id=pipeline_manifest.get("snapshot_id"),
            content_hash=primary_content_hash,
        ),
        _production_evidence_gate(
            environment=environment,
            code_commit_sha=code_commit_sha,
            schema_registry_report_uri=schema_registry_report_uri,
            schema_registry_report_hash=schema_registry_report_hash,
            validator_output_uri=validator_output_uri,
            access_policy_check_id=access_policy_check_id,
            access_policy_report_uri=access_policy_report_uri,
            access_policy_report_hash=access_policy_report_hash,
            access_grant_evidence_uri=access_grant_evidence_uri,
            access_grant_evidence_hash=access_grant_evidence_hash,
            retention_evidence_uri=retention_evidence_uri,
            retention_evidence_hash=retention_evidence_hash,
            snapshot_evidence_uri=snapshot_evidence_uri,
            snapshot_evidence_hash=snapshot_evidence_hash,
            approver=approver,
        ),
        _pipeline_ingestion_lag_gate(
            platform_root,
            ingestion_manifest=ingestion_manifest,
            approved_rows=approved_rows,
            approved_rows_error=approved_rows_error,
        ),
        _pipeline_freshness_gate(freshness_report),
        _pipeline_quality_gate(ingestion_manifest, pipeline_manifest),
        _quality_profile_gate(
            platform_root,
            quality_profile_id=quality_profile_id,
            use_case_id=use_case_id,
            primary_output=primary_output,
            output_data_products=resolved_output_products,
            ingestion_manifest=ingestion_manifest,
            pipeline_manifest=pipeline_manifest,
        ),
        _pipeline_output_evidence_gate(
            pipeline_manifest,
            primary_output=primary_output,
            output_data_products=resolved_output_products,
        ),
        _lakehouse_snapshot_evidence_gate(
            snapshot_evidence_uri,
            snapshot_evidence_hash,
            root=platform_root,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            runner_id=runner_id,
            pipeline_manifest_path=pipeline_manifest_path,
            pipeline_manifest=pipeline_manifest,
            primary_output=primary_output,
            primary_content_hash=primary_content_hash,
        ),
        _pipeline_catalog_lineage_gate(
            catalog_bundle,
            pipeline_manifest,
            ingestion_manifest,
            use_case_id=use_case_id,
            primary_output=primary_output,
            output_data_products=resolved_output_products,
            input_topics=resolved_input_topics,
        ),
    ]
    evidence = {
        "release_id": release_id,
        "environment": environment,
        "generated_at": generated,
        "use_case_id": use_case_id,
        "runner_id": runner_id,
        "runner_input_kind": runner_input_kind,
        "primary_output": primary_output,
        "input_topics": resolved_input_topics,
        "input_data_products": resolved_input_data_products,
        "output_data_products": resolved_output_products,
        "quality_profile_id": quality_profile_id,
        "quality_profile_hash": hash_quality_profile_registry(platform_root) if quality_profile_id else None,
        "release_evidence_profile_id": release_profile_id,
        "release_evidence_profile_hash": hash_release_profile_registry(platform_root) if release_profile_id else None,
        "code_commit_sha": code_commit_sha,
        "contract_versions": _contract_versions(platform_root),
        "schema_registry_report_uri": schema_registry_report_uri
        or ("local-json-schema-preflight" if environment in {"local", "dev"} else None),
        "schema_registry_report_hash": _schema_registry_hash(schema_registry_report_uri, schema_registry_report_hash),
        "validator_output_uri": validator_output_uri,
        "pipeline_run_id": pipeline_manifest.get("snapshot_id"),
        "topic_offset_ranges": _source_positions(ingestion_manifest, pipeline_manifest),
        "freshness_report": freshness_report,
        "quality_report": _pipeline_quality_report(ingestion_manifest, pipeline_manifest, primary_output, quality_profile_id),
        "lineage_catalog": {
            "bundle_path": Path(catalog_bundle_path).as_posix(),
            "bundle_hash": hash_file(catalog_bundle_path),
            "lineage_edge_count": catalog_bundle.get("summary", {}).get("lineage_edge_count"),
            "run_evidence_count": catalog_bundle.get("summary", {}).get("run_evidence_count"),
        },
        "access_policy_check_id": access_policy_check_id
        or ("local-contract-access-policy-check" if environment in {"local", "dev"} else None),
        "access_policy_report_uri": access_policy_report_uri,
        "access_policy_report_hash": _local_or_provided_hash(access_policy_report_uri, access_policy_report_hash),
        "access_grant_evidence_uri": access_grant_evidence_uri,
        "access_grant_evidence_hash": _local_or_provided_hash(access_grant_evidence_uri, access_grant_evidence_hash),
        "retention_evidence_uri": retention_evidence_uri,
        "retention_evidence_hash": _local_or_provided_hash(retention_evidence_uri, retention_evidence_hash),
        "snapshot_evidence_uri": snapshot_evidence_uri,
        "snapshot_evidence_hash": _local_or_provided_hash(snapshot_evidence_uri, snapshot_evidence_hash),
        "approver": approver,
        "artifacts": _pipeline_artifacts(
            ingestion_manifest_path=ingestion_manifest_path,
            pipeline_manifest_path=pipeline_manifest_path,
            catalog_bundle_path=catalog_bundle_path,
            snapshot_evidence_uri=snapshot_evidence_uri,
        ),
        "gates": [gate.as_dict() for gate in gates],
    }
    release_profile_gate = _release_profile_gate(
        platform_root,
        release_profile_id=release_profile_id,
        use_case_id=use_case_id,
        runner_input_kind=runner_input_kind,
        environment=environment,
        evidence=evidence,
    )
    gates.append(release_profile_gate)
    evidence["gates"] = [gate.as_dict() for gate in gates]
    evidence["release_passed"] = all(gate.passed for gate in gates)
    return evidence


def evaluate_recommendation_release_gates(
    root: str | Path,
    *,
    release_id: str,
    environment: str,
    ingestion_manifest_path: str | Path,
    medallion_manifest_path: str | Path,
    catalog_bundle_path: str | Path,
    approved_bronze_path: str | Path,
    generated_at: str | None = None,
    code_commit_sha: str | None = None,
    schema_registry_report_uri: str | None = None,
    schema_registry_report_hash: str | None = None,
    validator_output_uri: str | None = None,
    access_policy_check_id: str | None = None,
    access_policy_report_uri: str | None = None,
    access_policy_report_hash: str | None = None,
    access_grant_evidence_uri: str | None = None,
    access_grant_evidence_hash: str | None = None,
    retention_evidence_uri: str | None = None,
    retention_evidence_hash: str | None = None,
    snapshot_evidence_uri: str | None = None,
    snapshot_evidence_hash: str | None = None,
    approver: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or _utc_now()
    ingestion_manifest = load_json(Path(ingestion_manifest_path))
    medallion_manifest = load_json(Path(medallion_manifest_path))
    catalog_bundle = load_json(Path(catalog_bundle_path))
    approved_rows = read_jsonl(approved_bronze_path)

    contract_versions = _contract_versions(platform_root)
    freshness_report = _freshness_report(platform_root, approved_rows, medallion_manifest, generated)
    gold_layer = medallion_manifest.get("layers", {}).get("gold.recsys_interactions", {})
    gold_content_hash = gold_layer.get("content_hash") or medallion_manifest.get("content_hash")
    gates = [
        _contract_gate(platform_root),
        _schema_registry_gate(schema_registry_report_uri, schema_registry_report_hash, root=platform_root, environment=environment, release_id=release_id),
        _access_policy_gate(access_policy_report_uri, access_policy_report_hash, root=platform_root, environment=environment, release_id=release_id),
        _access_grant_evidence_gate(access_grant_evidence_uri, access_grant_evidence_hash, root=platform_root, environment=environment, release_id=release_id),
        _retention_evidence_gate(
            retention_evidence_uri,
            retention_evidence_hash,
            root=platform_root,
            environment=environment,
            release_id=release_id,
            data_product="gold.recsys_interactions",
            dataset_snapshot_id=medallion_manifest.get("snapshot_id"),
            content_hash=gold_content_hash,
        ),
        _production_evidence_gate(
            environment=environment,
            code_commit_sha=code_commit_sha,
            schema_registry_report_uri=schema_registry_report_uri,
            schema_registry_report_hash=schema_registry_report_hash,
            validator_output_uri=validator_output_uri,
            access_policy_check_id=access_policy_check_id,
            access_policy_report_uri=access_policy_report_uri,
            access_policy_report_hash=access_policy_report_hash,
            access_grant_evidence_uri=access_grant_evidence_uri,
            access_grant_evidence_hash=access_grant_evidence_hash,
            retention_evidence_uri=retention_evidence_uri,
            retention_evidence_hash=retention_evidence_hash,
            snapshot_evidence_uri=snapshot_evidence_uri,
            snapshot_evidence_hash=snapshot_evidence_hash,
            approver=approver,
        ),
        _ingestion_lag_gate(platform_root, approved_rows),
        _freshness_gate(freshness_report),
        _quality_gate(ingestion_manifest, medallion_manifest),
        _gold_evidence_gate(ingestion_manifest, medallion_manifest, catalog_bundle),
        _lakehouse_snapshot_evidence_gate(
            snapshot_evidence_uri,
            snapshot_evidence_hash,
            root=platform_root,
            environment=environment,
            release_id=release_id,
            use_case_id=None,
            runner_id=None,
            pipeline_manifest_path=medallion_manifest_path,
            pipeline_manifest=medallion_manifest,
            primary_output="gold.recsys_interactions",
            primary_content_hash=gold_content_hash,
        ),
        _catalog_lineage_gate(catalog_bundle, medallion_manifest),
    ]
    release_passed = all(gate.passed for gate in gates)
    return {
        "release_id": release_id,
        "environment": environment,
        "generated_at": generated,
        "release_passed": release_passed,
        "code_commit_sha": code_commit_sha,
        "contract_versions": contract_versions,
        "schema_registry_report_uri": schema_registry_report_uri
        or ("local-json-schema-preflight" if environment in {"local", "dev"} else None),
        "schema_registry_report_hash": _schema_registry_hash(schema_registry_report_uri, schema_registry_report_hash),
        "validator_output_uri": validator_output_uri,
        "pipeline_run_id": medallion_manifest.get("snapshot_id"),
        "topic_offset_ranges": ingestion_manifest.get("source_positions", []),
        "bronze_table_version": ingestion_manifest.get("approved", {}).get("content_hash"),
        "silver_table_version": medallion_manifest.get("layers", {}).get("silver.learner_activity", {}).get("content_hash"),
        "gold_dataset_snapshot_id": medallion_manifest.get("snapshot_id"),
        "quality_report": {
            "ingestion_quality_passed": ingestion_manifest.get("quality_passed"),
            "medallion_quality_passed": medallion_manifest.get("quality_passed"),
            "approved_rows": ingestion_manifest.get("approved", {}).get("row_count"),
            "quarantine_rows": ingestion_manifest.get("quarantine", {}).get("row_count"),
            "gold_rows": medallion_manifest.get("row_count"),
        },
        "freshness_report": freshness_report,
        "lineage_catalog": {
            "bundle_path": Path(catalog_bundle_path).as_posix(),
            "bundle_hash": hash_file(catalog_bundle_path),
            "lineage_edge_count": catalog_bundle.get("summary", {}).get("lineage_edge_count"),
            "run_evidence_count": catalog_bundle.get("summary", {}).get("run_evidence_count"),
        },
        "access_policy_check_id": access_policy_check_id
        or ("local-contract-access-policy-check" if environment in {"local", "dev"} else None),
        "access_policy_report_uri": access_policy_report_uri,
        "access_policy_report_hash": _local_or_provided_hash(access_policy_report_uri, access_policy_report_hash),
        "access_grant_evidence_uri": access_grant_evidence_uri,
        "access_grant_evidence_hash": _local_or_provided_hash(access_grant_evidence_uri, access_grant_evidence_hash),
        "retention_evidence_uri": retention_evidence_uri,
        "retention_evidence_hash": _local_or_provided_hash(retention_evidence_uri, retention_evidence_hash),
        "snapshot_evidence_uri": snapshot_evidence_uri,
        "snapshot_evidence_hash": _local_or_provided_hash(snapshot_evidence_uri, snapshot_evidence_hash),
        "approver": approver,
        "artifacts": {
            "ingestion_manifest_path": Path(ingestion_manifest_path).as_posix(),
            "ingestion_manifest_hash": hash_file(ingestion_manifest_path),
            "medallion_manifest_path": Path(medallion_manifest_path).as_posix(),
            "medallion_manifest_hash": hash_file(medallion_manifest_path),
            "approved_bronze_path": Path(approved_bronze_path).as_posix(),
            "approved_bronze_hash": hash_file(approved_bronze_path),
            "catalog_bundle_path": Path(catalog_bundle_path).as_posix(),
            "catalog_bundle_hash": hash_file(catalog_bundle_path),
        },
        "gates": [gate.as_dict() for gate in gates],
    }


def _source_positions(
    ingestion_manifest: dict[str, Any] | None,
    pipeline_manifest: dict[str, Any],
) -> list[Any]:
    if ingestion_manifest:
        positions = ingestion_manifest.get("source_positions", [])
        return positions if isinstance(positions, list) else []
    positions = pipeline_manifest.get("source_positions", [])
    return positions if isinstance(positions, list) else []


def _pipeline_quality_report(
    ingestion_manifest: dict[str, Any] | None,
    pipeline_manifest: dict[str, Any],
    primary_output: str,
    quality_profile_id: str | None,
) -> dict[str, Any]:
    primary_layer = pipeline_manifest.get("layers", {}).get(primary_output, {})
    report = {
        "quality_profile_id": quality_profile_id,
        "pipeline_quality_passed": pipeline_manifest.get("quality_passed"),
        "upstream_quality_passed": pipeline_manifest.get("upstream_quality_passed"),
        "primary_output_rows": primary_layer.get("row_count"),
        "primary_output_hash": primary_layer.get("content_hash"),
        "pipeline_rows": pipeline_manifest.get("row_count"),
    }
    if ingestion_manifest:
        report.update(
            {
                "ingestion_quality_passed": ingestion_manifest.get("quality_passed"),
                "approved_rows": ingestion_manifest.get("approved", {}).get("row_count"),
                "quarantine_rows": ingestion_manifest.get("quarantine", {}).get("row_count"),
            }
        )
    return report


def _quality_profile_gate(
    root: Path,
    *,
    quality_profile_id: str | None,
    use_case_id: str,
    primary_output: str,
    output_data_products: list[str],
    ingestion_manifest: dict[str, Any] | None,
    pipeline_manifest: dict[str, Any],
) -> GateResult:
    try:
        evaluation = evaluate_quality_profile(
            root,
            profile_id=quality_profile_id,
            use_case_id=use_case_id,
            primary_output=primary_output,
            output_data_products=output_data_products,
            ingestion_manifest=ingestion_manifest,
            pipeline_manifest=pipeline_manifest,
        )
    except KeyError as exc:
        evaluation = {
            "profile_id": quality_profile_id,
            "passed": False,
            "checks": [
                {
                    "name": "profile_registered",
                    "passed": False,
                    "details": {"reason": str(exc)},
                }
            ],
        }
    return GateResult(
        gate_id="P0-QUALITY-PROFILE",
        passed=evaluation.get("passed") is True,
        details=evaluation,
    )


def _release_profile_gate(
    root: Path,
    *,
    release_profile_id: str | None,
    use_case_id: str,
    runner_input_kind: str | None,
    environment: str,
    evidence: dict[str, Any],
) -> GateResult:
    try:
        evaluation = evaluate_release_profile(
            root,
            profile_id=release_profile_id,
            use_case_id=use_case_id,
            runner_input_kind=runner_input_kind,
            environment=environment,
            evidence=evidence,
        )
    except KeyError as exc:
        evaluation = {
            "profile_id": release_profile_id,
            "passed": False,
            "checks": [
                {
                    "name": "profile_registered",
                    "passed": False,
                    "details": {"reason": str(exc)},
                }
            ],
        }
    return GateResult(
        gate_id="P0-RELEASE-EVIDENCE-PROFILE",
        passed=evaluation.get("passed") is True,
        details=evaluation,
    )


def _pipeline_artifacts(
    *,
    ingestion_manifest_path: str | Path | None,
    pipeline_manifest_path: str | Path,
    catalog_bundle_path: str | Path,
    snapshot_evidence_uri: str | None = None,
) -> dict[str, Any]:
    artifacts: dict[str, Any] = {
        "pipeline_manifest_path": Path(pipeline_manifest_path).as_posix(),
        "pipeline_manifest_hash": hash_file(pipeline_manifest_path),
        "catalog_bundle_path": Path(catalog_bundle_path).as_posix(),
        "catalog_bundle_hash": hash_file(catalog_bundle_path),
    }
    if ingestion_manifest_path:
        artifacts.update(
            {
                "ingestion_manifest_path": Path(ingestion_manifest_path).as_posix(),
                "ingestion_manifest_hash": hash_file(ingestion_manifest_path),
            }
        )
    if snapshot_evidence_uri:
        artifacts.update(
            {
                "snapshot_evidence_uri": snapshot_evidence_uri,
                "snapshot_evidence_hash": _local_or_provided_hash(snapshot_evidence_uri, None),
            }
        )
    return artifacts


def _pipeline_quality_gate(
    ingestion_manifest: dict[str, Any] | None,
    pipeline_manifest: dict[str, Any],
) -> GateResult:
    quarantine_rows = ingestion_manifest.get("quarantine", {}).get("row_count") if ingestion_manifest else 0
    required = {
        "pipeline_quality_passed": pipeline_manifest.get("quality_passed") is True,
        "upstream_quality_passed": pipeline_manifest.get("upstream_quality_passed") is not False,
        "ingestion_quality_passed": ingestion_manifest is None or ingestion_manifest.get("quality_passed") is True,
        "quarantine_empty": quarantine_rows == 0,
    }
    return GateResult(
        gate_id="P0-PIPELINE-QUALITY",
        passed=all(required.values()),
        details={
            **required,
            "quarantine_rows": quarantine_rows,
            "pipeline_rows": pipeline_manifest.get("row_count"),
        },
    )


def _pipeline_output_evidence_gate(
    pipeline_manifest: dict[str, Any],
    *,
    primary_output: str,
    output_data_products: list[str],
) -> GateResult:
    layers = pipeline_manifest.get("layers", {})
    primary_layer = layers.get(primary_output)
    missing_outputs = [
        data_product_name
        for data_product_name in output_data_products
        if data_product_name not in layers
    ]
    required = {
        "snapshot_id": bool(pipeline_manifest.get("snapshot_id")),
        "primary_output_in_manifest": isinstance(primary_layer, dict),
        "primary_output_content_hash": isinstance(primary_layer, dict) and bool(primary_layer.get("content_hash")),
        "primary_output_row_count": isinstance(primary_layer, dict) and primary_layer.get("row_count") is not None,
        "declared_outputs_in_manifest": not missing_outputs,
    }
    return GateResult(
        gate_id="P0-OUTPUT-EVIDENCE",
        passed=all(required.values()),
        details={
            **required,
            "primary_output": primary_output,
            "missing_outputs": missing_outputs,
            "manifest_outputs": sorted(str(name) for name in layers.keys()),
        },
    )


def _lakehouse_snapshot_evidence_gate(
    snapshot_evidence_uri: str | None,
    snapshot_evidence_hash: str | None,
    *,
    root: Path,
    environment: str,
    release_id: str,
    use_case_id: str | None,
    runner_id: str | None,
    pipeline_manifest_path: str | Path,
    pipeline_manifest: dict[str, Any],
    primary_output: str,
    primary_content_hash: str | None,
) -> GateResult:
    del root
    production_like = environment not in {"local", "dev"}
    if not snapshot_evidence_uri:
        return GateResult(
            gate_id="P0-LAKEHOUSE-SNAPSHOT-EVIDENCE",
            passed=not production_like,
            details={
                "reason": "snapshot_evidence_uri_missing",
                "environment": environment,
                "production_like": production_like,
            },
        )
    evidence_path = Path(snapshot_evidence_uri)
    if not evidence_path.is_file():
        return GateResult(
            gate_id="P0-LAKEHOUSE-SNAPSHOT-EVIDENCE",
            passed=False,
            details={
                "snapshot_evidence_uri": snapshot_evidence_uri,
                "snapshot_evidence_hash": snapshot_evidence_hash,
                "reason": "external_reference_unverified",
                "required": "local_lakehouse_snapshot_evidence.v1",
            },
        )
    evidence_hash = hash_file(evidence_path)
    if snapshot_evidence_hash and snapshot_evidence_hash != evidence_hash:
        return GateResult(
            gate_id="P0-LAKEHOUSE-SNAPSHOT-EVIDENCE",
            passed=False,
            details={
                "snapshot_evidence_uri": snapshot_evidence_uri,
                "expected_hash": snapshot_evidence_hash,
                "actual_hash": evidence_hash,
                "reason": "snapshot_evidence_hash_mismatch",
            },
        )
    report = load_json(evidence_path)
    report_pipeline = _dict(report.get("pipeline"))
    report_layers = _dict(report.get("layers"))
    primary_binding = _dict(report_layers.get(primary_output))
    primary_snapshot = _dict(report.get("primary_snapshot")) or _dict(primary_binding.get("snapshot"))
    primary_layer = _dict(primary_binding.get("manifest_layer"))
    source_offset_ledger = report.get("source_offset_ledger")
    release_id_matches = (
        report.get("release_id") == release_id
        if production_like
        else report.get("release_id") in {None, release_id}
    )
    use_case_id_matches = (
        (use_case_id is None or report.get("use_case_id") == use_case_id)
        if production_like
        else report.get("use_case_id") in {None, use_case_id}
    )
    runner_id_matches = (
        (runner_id is None or report.get("runner_id") == runner_id)
        if production_like
        else report.get("runner_id") in {None, runner_id}
    )
    structural_checks = {
        "artifact_type_valid": report.get("artifact_type") == "lakehouse_snapshot_evidence.v1",
        "report_passed": report.get("passed") is True,
        "environment_matches": report.get("environment") == environment,
        "release_id_matches": release_id_matches,
        "use_case_id_matches": use_case_id_matches,
        "runner_id_matches": runner_id_matches,
        "primary_output_matches": report.get("primary_output") == primary_output,
        "pipeline_manifest_hash_matches": report_pipeline.get("manifest_hash") == hash_file(pipeline_manifest_path),
        "pipeline_snapshot_id_matches": report_pipeline.get("snapshot_id") == pipeline_manifest.get("snapshot_id"),
        "primary_snapshot_id_present": bool(primary_snapshot.get("snapshot_id")),
        "primary_layer_content_hash_matches": primary_layer.get("content_hash") == primary_content_hash,
        "primary_snapshot_content_hash_matches": primary_snapshot.get("content_hash") == primary_content_hash,
        "source_offset_ledger_attached": not production_like or isinstance(source_offset_ledger, dict),
    }
    return GateResult(
        gate_id="P0-LAKEHOUSE-SNAPSHOT-EVIDENCE",
        passed=all(structural_checks.values()),
        details={
            "snapshot_evidence_uri": snapshot_evidence_uri,
            "snapshot_evidence_hash": evidence_hash,
            "evidence_id": report.get("evidence_id"),
            "environment": environment,
            "report_environment": report.get("environment"),
            "release_id": release_id,
            "report_release_id": report.get("release_id"),
            "use_case_id": use_case_id,
            "report_use_case_id": report.get("use_case_id"),
            "runner_id": runner_id,
            "report_runner_id": report.get("runner_id"),
            "primary_output": primary_output,
            "pipeline_snapshot_id": pipeline_manifest.get("snapshot_id"),
            "primary_snapshot_id": primary_snapshot.get("snapshot_id"),
            "primary_content_hash": primary_content_hash,
            "failure_count": len(report.get("failures", [])),
            **structural_checks,
        },
    )


def _pipeline_ingestion_lag_gate(
    root: Path,
    *,
    ingestion_manifest: dict[str, Any] | None,
    approved_rows: list[dict[str, Any]],
    approved_rows_error: str | None,
) -> GateResult:
    if ingestion_manifest is None:
        return GateResult(
            gate_id="P0-INGESTION-LAG",
            passed=True,
            details={"not_applicable": True, "reason": "no_ingestion_manifest"},
        )
    if approved_rows_error:
        return GateResult(
            gate_id="P0-INGESTION-LAG",
            passed=False,
            details={"reason": approved_rows_error},
        )
    topic_name = ingestion_manifest.get("topic")
    slo_seconds = _topic_slo(root, topic_name) if isinstance(topic_name, str) else None
    lags = []
    missing = 0
    for row in approved_rows:
        published_at = _parse_time(row.get("published_at"))
        ingested_at = _parse_time(row.get("ingested_at"))
        if not published_at or not ingested_at:
            missing += 1
            continue
        lags.append((ingested_at - published_at).total_seconds())
    max_lag = max(lags) if lags else None
    passed = bool(lags) and missing == 0 and slo_seconds is not None and max_lag is not None and max_lag <= slo_seconds
    return GateResult(
        gate_id="P0-INGESTION-LAG",
        passed=passed,
        details={
            "topic": topic_name,
            "slo_seconds": slo_seconds,
            "max_lag_seconds": max_lag,
            "missing_timestamp_rows": missing,
            "row_count": len(approved_rows),
        },
    )


def _pipeline_freshness_gate(freshness_report: dict[str, Any]) -> GateResult:
    layer_reports = [
        report for key, report in freshness_report.items()
        if key != "_meta" and isinstance(report, dict)
    ]
    return GateResult(
        gate_id="P0-FRESHNESS",
        passed=bool(layer_reports) and all(report.get("passed") is True for report in layer_reports),
        details=freshness_report,
    )


def _pipeline_freshness_report(
    root: Path,
    *,
    ingestion_manifest: dict[str, Any] | None,
    pipeline_manifest: dict[str, Any],
    generated_at: str,
    approved_rows: list[dict[str, Any]],
    approved_rows_error: str | None,
) -> dict[str, Any]:
    evaluation_time = _parse_time(generated_at)
    if not evaluation_time:
        return {
            "_meta": {
                "passed": False,
                "reason": "generated_at_invalid",
                "generated_at": generated_at,
            }
        }
    pipeline_time = _parse_time(pipeline_manifest.get("generated_at"))
    latest_bronze_ingested = _latest_time(row.get("ingested_at") for row in approved_rows)
    if not latest_bronze_ingested and ingestion_manifest is not None:
        latest_bronze_ingested = _parse_time(ingestion_manifest.get("ingested_at"))

    report: dict[str, Any] = {
        "_meta": {
            "generated_at": generated_at,
            "approved_rows_error": approved_rows_error,
        }
    }
    for layer_name in ordered_layer_names(pipeline_manifest.get("layers", {})):
        try:
            slo_seconds = _data_product_slo(root, layer_name)
        except FileNotFoundError as exc:
            report[layer_name] = {
                "passed": False,
                "reason": str(exc),
            }
            continue
        latest_time = latest_bronze_ingested if layer_name.startswith("bronze.") else pipeline_time
        entry = _freshness_entry(evaluation_time, latest_time, slo_seconds)
        entry["latest_time_source"] = "approved_bronze_ingested_at" if layer_name.startswith("bronze.") else "pipeline_generated_at"
        if approved_rows_error and layer_name.startswith("bronze."):
            entry["passed"] = False
            entry["reason"] = approved_rows_error
        report[layer_name] = entry
    return report


def _pipeline_catalog_lineage_gate(
    catalog_bundle: dict[str, Any],
    pipeline_manifest: dict[str, Any],
    ingestion_manifest: dict[str, Any] | None,
    *,
    use_case_id: str,
    primary_output: str,
    output_data_products: list[str],
    input_topics: list[str],
) -> GateResult:
    runs = [
        run for run in catalog_bundle.get("run_evidence", [])
        if isinstance(run, dict)
    ]
    edges = [
        edge for edge in catalog_bundle.get("lineage_edges", [])
        if isinstance(edge, dict)
    ]
    edge_types = {edge.get("type") for edge in edges}
    pipeline_run_registered = any(
        run.get("pipeline") == pipeline_manifest.get("pipeline")
        and run.get("snapshot_id") == pipeline_manifest.get("snapshot_id")
        for run in runs
    )
    ingestion_run_registered = ingestion_manifest is None or any(
        run.get("ingest_run_id") == ingestion_manifest.get("ingest_run_id")
        for run in runs
    )
    primary_output_registered = any(
        primary_output in (run.get("layers", {}) or {})
        for run in runs
    )
    use_case_output_lineage = any(
        edge.get("type") == "USE_CASE_DATA_PRODUCT"
        and edge.get("source") == f"urn:enterprise-dp:use-case:{use_case_id}"
        and edge.get("target") == f"urn:enterprise-dp:data-product:{primary_output}"
        for edge in edges
    )
    expected_transform_edges = expected_pipeline_transform_edges(pipeline_manifest)
    expected_topic_edges = expected_topic_to_bronze_edges(ingestion_manifest, pipeline_manifest, input_topics)
    run_urn = pipeline_run_urn(pipeline_manifest)
    missing_transform_edges = [
        edge for edge in expected_transform_edges
        if not any(
            catalog_edge.get("type") == "RUN_LAYER_TRANSFORM"
            and catalog_edge.get("source") == f"urn:enterprise-dp:data-product:{edge['source']}"
            and catalog_edge.get("target") == f"urn:enterprise-dp:data-product:{edge['target']}"
            and (run_urn is None or catalog_edge.get("run") == run_urn)
            for catalog_edge in edges
        )
    ]
    missing_topic_edges = [
        edge for edge in expected_topic_edges
        if not any(
            catalog_edge.get("type") in {"TOPIC_TO_BRONZE", "RUN_TOPIC_TO_BRONZE"}
            and catalog_edge.get("source") == f"urn:enterprise-dp:topic:{edge['source']}"
            and catalog_edge.get("target") == f"urn:enterprise-dp:data-product:{edge['target']}"
            for catalog_edge in edges
        )
    ]
    required = {
        "pipeline_run_registered": pipeline_run_registered,
        "ingestion_run_registered": ingestion_run_registered,
        "primary_output_registered": primary_output_registered,
        "use_case_output_lineage": use_case_output_lineage,
        "run_transform_lineage": not expected_transform_edges or not missing_transform_edges,
        "topic_lineage": not expected_topic_edges or not missing_topic_edges,
    }
    return GateResult(
        gate_id="P0-CATALOG-LINEAGE",
        passed=all(required.values()),
        details={
            **required,
            "expected_transform_edges": expected_transform_edges,
            "missing_transform_edges": missing_transform_edges,
            "expected_topic_edges": expected_topic_edges,
            "missing_topic_edges": missing_topic_edges,
            "edge_types": sorted(str(edge_type) for edge_type in edge_types),
            "lineage_edge_count": len(edges),
            "run_evidence_count": catalog_bundle.get("summary", {}).get("run_evidence_count"),
        },
    )


def expected_pipeline_transform_edges(pipeline_manifest: dict[str, Any]) -> list[dict[str, str]]:
    explicit_edges = pipeline_manifest.get("lineage_edges")
    if isinstance(explicit_edges, list):
        parsed = [
            {
                "source": edge["source"],
                "target": edge["target"],
            }
            for edge in explicit_edges
            if isinstance(edge, dict)
            and edge.get("type", "RUN_LAYER_TRANSFORM") == "RUN_LAYER_TRANSFORM"
            and isinstance(edge.get("source"), str)
            and isinstance(edge.get("target"), str)
        ]
        if parsed:
            return parsed
    layer_names = ordered_layer_names(pipeline_manifest.get("layers", {}))
    return [
        {
            "source": source_layer,
            "target": target_layer,
        }
        for source_layer, target_layer in zip(layer_names, layer_names[1:])
    ]


def expected_topic_to_bronze_edges(
    ingestion_manifest: dict[str, Any] | None,
    pipeline_manifest: dict[str, Any],
    input_topics: list[str],
) -> list[dict[str, str]]:
    if ingestion_manifest:
        topic = ingestion_manifest.get("topic")
        bronze_target = ingestion_manifest.get("bronze_target")
        if isinstance(topic, str) and isinstance(bronze_target, str):
            return [{"source": topic, "target": bronze_target}]
    bronze_layers = [
        layer_name for layer_name in ordered_layer_names(pipeline_manifest.get("layers", {}))
        if layer_name.startswith("bronze.")
    ]
    if len(input_topics) == 1 and bronze_layers:
        return [{"source": input_topics[0], "target": bronze_layers[0]}]
    return []


def pipeline_run_urn(pipeline_manifest: dict[str, Any]) -> str | None:
    pipeline = pipeline_manifest.get("pipeline")
    snapshot_id = pipeline_manifest.get("snapshot_id")
    if isinstance(pipeline, str) and isinstance(snapshot_id, str):
        return f"urn:enterprise-dp:run:{pipeline}:{snapshot_id}"
    return None


def _contract_gate(root: Path) -> GateResult:
    result = validate_project_structure(root)
    result.extend(validate_contract_tree(root))
    result.extend(validate_product_onboarding_tree(root))
    result.extend(validate_domain_registry(root))
    result.extend(validate_access_persona_registry(root))
    result.extend(validate_consumer_contract_registry(root))
    result.extend(validate_access_grant_registry(root))
    result.extend(validate_access_policy_registry(root))
    result.extend(validate_evidence_trust_key_registry(root))
    result.extend(validate_retention_policy_registry(root))
    result.extend(validate_quality_profile_registry(root))
    result.extend(validate_release_profile_registry(root))
    result.extend(validate_use_case_registry(root))
    return GateResult(
        gate_id="P0-CONTRACT-COMPATIBILITY",
        passed=result.ok,
        details={
            "checked_count": result.checked_count,
            "errors": result.errors,
            "warnings": result.warnings,
        },
    )


def _schema_registry_gate(schema_registry_report_uri: str | None, schema_registry_report_hash: str | None, *, root: Path, environment: str, release_id: str | None = None) -> GateResult:
    if not schema_registry_report_uri:
        return GateResult(
            gate_id="P0-SCHEMA-REGISTRY-COMPATIBILITY",
            passed=False,
            details={"reason": "schema_registry_report_uri_missing"},
        )
    report_path = Path(schema_registry_report_uri)
    if not report_path.is_file():
        return GateResult(
            gate_id="P0-SCHEMA-REGISTRY-COMPATIBILITY",
            passed=False,
            details={
                "schema_registry_report_uri": schema_registry_report_uri,
                "schema_registry_report_hash": schema_registry_report_hash,
                "reason": "external_reference_unverified",
                "required": "local_report_or_external_evidence_attestation.v1",
            },
        )
    report_hash = hash_file(report_path)
    if schema_registry_report_hash and schema_registry_report_hash != report_hash:
        return GateResult(
            gate_id="P0-SCHEMA-REGISTRY-COMPATIBILITY",
            passed=False,
            details={
                "schema_registry_report_uri": schema_registry_report_uri,
                "expected_hash": schema_registry_report_hash,
                "actual_hash": report_hash,
                "reason": "schema_registry_report_hash_mismatch",
            },
        )
    report = load_json(report_path)
    attestation = _external_evidence_attestation_gate(
        gate_id="P0-SCHEMA-REGISTRY-COMPATIBILITY",
        evidence_kind="schema_registry",
        uri_field="schema_registry_report_uri",
        uri=schema_registry_report_uri,
        evidence_hash=report_hash,
        report=report,
        root=root,
        environment=environment,
        release_id=release_id,
    )
    if attestation is not None:
        return attestation
    return GateResult(
        gate_id="P0-SCHEMA-REGISTRY-COMPATIBILITY",
        passed=report.get("compatibility_passed") is True,
        details={
            "schema_registry_report_uri": schema_registry_report_uri,
            "schema_registry_report_hash": report_hash,
            "subject_count": report.get("subject_count"),
            "failed_subjects": report.get("summary", {}).get("failed_subjects"),
            "registry_uri": report.get("registry_uri"),
        },
    )


def _access_policy_gate(access_policy_report_uri: str | None, access_policy_report_hash: str | None, *, root: Path, environment: str, release_id: str | None = None) -> GateResult:
    if not access_policy_report_uri:
        return GateResult(
            gate_id="P0-ACCESS-POLICY",
            passed=False,
            details={"reason": "access_policy_report_uri_missing"},
        )
    report_path = Path(access_policy_report_uri)
    if not report_path.is_file():
        return GateResult(
            gate_id="P0-ACCESS-POLICY",
            passed=False,
            details={
                "access_policy_report_uri": access_policy_report_uri,
                "access_policy_report_hash": access_policy_report_hash,
                "reason": "external_reference_unverified",
                "required": "local_report_or_external_evidence_attestation.v1",
            },
        )
    report_hash = hash_file(report_path)
    if access_policy_report_hash and access_policy_report_hash != report_hash:
        return GateResult(
            gate_id="P0-ACCESS-POLICY",
            passed=False,
            details={
                "access_policy_report_uri": access_policy_report_uri,
                "expected_hash": access_policy_report_hash,
                "actual_hash": report_hash,
                "reason": "access_policy_report_hash_mismatch",
            },
        )
    report = load_json(report_path)
    attestation = _external_evidence_attestation_gate(
        gate_id="P0-ACCESS-POLICY",
        evidence_kind="access_policy",
        uri_field="access_policy_report_uri",
        uri=access_policy_report_uri,
        evidence_hash=report_hash,
        report=report,
        root=root,
        environment=environment,
        release_id=release_id,
    )
    if attestation is not None:
        return attestation
    return GateResult(
        gate_id="P0-ACCESS-POLICY",
        passed=report.get("passed") is True,
        details={
            "access_policy_report_uri": access_policy_report_uri,
            "access_policy_report_hash": report_hash,
            "check_id": report.get("check_id"),
            "data_product": report.get("data_product"),
            "failure_count": len(report.get("failures", [])),
        },
    )


def _access_grant_evidence_gate(access_grant_evidence_uri: str | None, access_grant_evidence_hash: str | None, *, root: Path, environment: str, release_id: str | None = None) -> GateResult:
    if not access_grant_evidence_uri:
        return GateResult(
            gate_id="P0-ACCESS-GRANT-EVIDENCE",
            passed=False,
            details={"reason": "access_grant_evidence_uri_missing"},
        )
    evidence_path = Path(access_grant_evidence_uri)
    if not evidence_path.is_file():
        return GateResult(
            gate_id="P0-ACCESS-GRANT-EVIDENCE",
            passed=False,
            details={
                "access_grant_evidence_uri": access_grant_evidence_uri,
                "access_grant_evidence_hash": access_grant_evidence_hash,
                "reason": "external_reference_unverified",
                "required": "local_report_or_external_evidence_attestation.v1",
            },
        )
    evidence_hash = hash_file(evidence_path)
    if access_grant_evidence_hash and access_grant_evidence_hash != evidence_hash:
        return GateResult(
            gate_id="P0-ACCESS-GRANT-EVIDENCE",
            passed=False,
            details={
                "access_grant_evidence_uri": access_grant_evidence_uri,
                "expected_hash": access_grant_evidence_hash,
                "actual_hash": evidence_hash,
                "reason": "access_grant_evidence_hash_mismatch",
            },
        )
    report = load_json(evidence_path)
    attestation = _external_evidence_attestation_gate(
        gate_id="P0-ACCESS-GRANT-EVIDENCE",
        evidence_kind="access_grant",
        uri_field="access_grant_evidence_uri",
        uri=access_grant_evidence_uri,
        evidence_hash=evidence_hash,
        report=report,
        root=root,
        environment=environment,
        release_id=release_id,
    )
    if attestation is not None:
        return attestation
    return GateResult(
        gate_id="P0-ACCESS-GRANT-EVIDENCE",
        passed=report.get("passed") is True,
        details={
            "access_grant_evidence_uri": access_grant_evidence_uri,
            "access_grant_evidence_hash": evidence_hash,
            "evidence_id": report.get("evidence_id"),
            "data_product": report.get("data_product"),
            "active_grant_count": report.get("active_grant_count"),
            "failure_count": len(report.get("failures", [])),
        },
    )


def _retention_evidence_gate(
    retention_evidence_uri: str | None,
    retention_evidence_hash: str | None,
    *,
    root: Path | None = None,
    environment: str,
    release_id: str | None = None,
    data_product: str | None = None,
    dataset_snapshot_id: str | None = None,
    content_hash: str | None = None,
) -> GateResult:
    if not retention_evidence_uri:
        return GateResult(
            gate_id="P0-RETENTION-ERASURE",
            passed=False,
            details={"reason": "retention_evidence_uri_missing"},
        )
    evidence_path = Path(retention_evidence_uri)
    if not evidence_path.is_file():
        return GateResult(
            gate_id="P0-RETENTION-ERASURE",
            passed=False,
            details={
                "retention_evidence_uri": retention_evidence_uri,
                "retention_evidence_hash": retention_evidence_hash,
                "reason": "external_reference_unverified",
                "required": "local_report_or_external_evidence_attestation.v1",
            },
        )
    evidence_hash = hash_file(evidence_path)
    if retention_evidence_hash and retention_evidence_hash != evidence_hash:
        return GateResult(
            gate_id="P0-RETENTION-ERASURE",
            passed=False,
            details={
                "retention_evidence_uri": retention_evidence_uri,
                "expected_hash": retention_evidence_hash,
                "actual_hash": evidence_hash,
                "reason": "retention_evidence_hash_mismatch",
            },
        )
    report = load_json(evidence_path)
    attestation = _external_evidence_attestation_gate(
        gate_id="P0-RETENTION-ERASURE",
        evidence_kind="retention_erasure",
        uri_field="retention_evidence_uri",
        uri=retention_evidence_uri,
        evidence_hash=evidence_hash,
        report=report,
        root=root or Path("."),
        environment=environment,
        release_id=release_id,
        data_product=data_product,
        dataset_snapshot_id=dataset_snapshot_id,
        content_hash=content_hash,
    )
    if attestation is not None:
        return attestation
    evidence_source = report.get("evidence_source") if isinstance(report.get("evidence_source"), dict) else {}
    report_environment = report.get("environment")
    production_like = environment not in {"local", "dev"}
    structural_checks = {
        "artifact_type_valid": report.get("artifact_type") == "retention_erasure_evidence.v1",
        "environment_matches_release": report_environment == environment,
        "release_id_matches": release_id is None or report.get("release_id") == release_id,
        "data_product_matches": data_product is None or report.get("data_product") == data_product,
        "dataset_snapshot_id_matches": dataset_snapshot_id is None or report.get("dataset_snapshot_id") == dataset_snapshot_id,
        "content_hash_matches": content_hash is None or report.get("content_hash") == content_hash,
        "table_version_matches_content_hash": content_hash is None or report.get("table_version") == content_hash,
        "evidence_source_verified": evidence_source.get("verified") is True,
        "production_uses_external_input": not production_like or evidence_source.get("type") == "external_input",
    }
    return GateResult(
        gate_id="P0-RETENTION-ERASURE",
        passed=report.get("passed") is True and all(structural_checks.values()),
        details={
            "retention_evidence_uri": retention_evidence_uri,
            "retention_evidence_hash": evidence_hash,
            "evidence_id": report.get("evidence_id"),
            "data_product": report.get("data_product"),
            "policy_id": report.get("policy", {}).get("policy_id"),
            "report_environment": report_environment,
            "evidence_source_type": evidence_source.get("type"),
            "expected_release_id": release_id,
            "report_release_id": report.get("release_id"),
            "expected_data_product": data_product,
            "expected_dataset_snapshot_id": dataset_snapshot_id,
            "report_dataset_snapshot_id": report.get("dataset_snapshot_id"),
            "expected_content_hash": content_hash,
            "report_content_hash": report.get("content_hash"),
            **structural_checks,
            "failure_count": len(report.get("failures", [])),
        },
    )


def _external_evidence_attestation_gate(
    *,
    gate_id: str,
    evidence_kind: str,
    uri_field: str,
    uri: str,
    evidence_hash: str,
    report: dict[str, Any],
    root: Path,
    environment: str,
    release_id: str | None = None,
    data_product: str | None = None,
    dataset_snapshot_id: str | None = None,
    content_hash: str | None = None,
) -> GateResult | None:
    if report.get("artifact_type") != "external_evidence_attestation.v1":
        return None
    subject_uri = report.get("subject_uri")
    subject_hash = report.get("subject_hash")
    verification = verify_external_evidence_attestation(
        root,
        report,
        evidence_kind=evidence_kind,
        environment=environment,
    )
    required = {
        "artifact_type": True,
        "evidence_kind": report.get("evidence_kind") == evidence_kind,
        "subject_uri": isinstance(subject_uri, str) and bool(subject_uri.strip()),
        "subject_hash": isinstance(subject_hash, str) and subject_hash.startswith("sha256:"),
        "environment": report.get("environment") == environment,
        "release_id": release_id is None or report.get("release_id") == release_id,
        "data_product": data_product is None or report.get("data_product") == data_product,
        "dataset_snapshot_id": dataset_snapshot_id is None or report.get("dataset_snapshot_id") == dataset_snapshot_id,
        "content_hash": content_hash is None or report.get("content_hash") == content_hash,
        "producer": isinstance(report.get("producer"), str) and bool(str(report.get("producer")).strip()),
        "generated_at": _parse_time(report.get("generated_at")) is not None,
        "passed": report.get("passed") is True,
        **verification.required,
    }
    return GateResult(
        gate_id=gate_id,
        passed=all(required.values()),
        details={
            uri_field: uri,
            f"{uri_field}_hash": evidence_hash,
            "checked": "external_evidence_attestation.v1",
            "subject_uri": subject_uri,
            "subject_hash": subject_hash,
            "evidence_kind": report.get("evidence_kind"),
            "environment": report.get("environment"),
            "expected_environment": environment,
            "release_id": report.get("release_id"),
            "expected_release_id": release_id,
            "data_product": report.get("data_product"),
            "expected_data_product": data_product,
            "dataset_snapshot_id": report.get("dataset_snapshot_id"),
            "expected_dataset_snapshot_id": dataset_snapshot_id,
            "content_hash": report.get("content_hash"),
            "expected_content_hash": content_hash,
            "producer": report.get("producer"),
            "generated_at": report.get("generated_at"),
            **verification.details,
            "required": required,
        },
    )


def _production_evidence_gate(
    *,
    environment: str,
    code_commit_sha: str | None,
    schema_registry_report_uri: str | None,
    schema_registry_report_hash: str | None,
    validator_output_uri: str | None,
    access_policy_check_id: str | None,
    access_policy_report_uri: str | None,
    access_policy_report_hash: str | None,
    access_grant_evidence_uri: str | None,
    access_grant_evidence_hash: str | None,
    retention_evidence_uri: str | None,
    retention_evidence_hash: str | None,
    snapshot_evidence_uri: str | None,
    snapshot_evidence_hash: str | None,
    approver: str | None,
) -> GateResult:
    required = {
        "code_commit_sha": bool(code_commit_sha),
        "schema_registry_report_uri": bool(schema_registry_report_uri),
        "schema_registry_report_hash": bool(schema_registry_report_hash) or _is_local_file(schema_registry_report_uri),
        "validator_output_uri": bool(validator_output_uri),
        "access_policy_check_id": bool(access_policy_check_id),
        "access_policy_report_uri": bool(access_policy_report_uri),
        "access_policy_report_hash": bool(access_policy_report_hash) or _is_local_file(access_policy_report_uri),
        "access_grant_evidence_uri": bool(access_grant_evidence_uri),
        "access_grant_evidence_hash": bool(access_grant_evidence_hash) or _is_local_file(access_grant_evidence_uri),
        "retention_evidence_uri": bool(retention_evidence_uri),
        "retention_evidence_hash": bool(retention_evidence_hash) or _is_local_file(retention_evidence_uri),
        "snapshot_evidence_uri": bool(snapshot_evidence_uri),
        "snapshot_evidence_hash": bool(snapshot_evidence_hash) or _is_local_file(snapshot_evidence_uri),
        "approver": bool(approver),
    }
    is_production_like = environment not in {"local", "dev"}
    return GateResult(
        gate_id="P0-PRODUCTION-EVIDENCE",
        passed=not is_production_like or all(required.values()),
        details={
            "environment": environment,
            "production_like": is_production_like,
            "required": required,
        },
    )


def _schema_registry_hash(schema_registry_report_uri: str | None, schema_registry_report_hash: str | None) -> str | None:
    return _local_or_provided_hash(schema_registry_report_uri, schema_registry_report_hash)


def _local_or_provided_hash(report_uri: str | None, report_hash: str | None) -> str | None:
    if report_hash:
        return report_hash
    if _is_local_file(report_uri):
        return hash_file(report_uri)
    return None


def _is_local_file(value: str | None) -> bool:
    return bool(value) and Path(str(value)).is_file()


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ingestion_lag_gate(root: Path, approved_rows: list[dict[str, Any]]) -> GateResult:
    topic_contract = load_yaml(root / "contracts" / "topics" / "recommendation.tracking.v1.yaml")
    slo_seconds = int(topic_contract.get("quality", {}).get("freshnessSloMinutes", 15)) * 60
    lags = []
    missing = 0
    for row in approved_rows:
        published_at = _parse_time(row.get("published_at"))
        ingested_at = _parse_time(row.get("ingested_at"))
        if not published_at or not ingested_at:
            missing += 1
            continue
        lags.append((ingested_at - published_at).total_seconds())
    max_lag = max(lags) if lags else None
    passed = bool(lags) and missing == 0 and max_lag is not None and max_lag <= slo_seconds
    return GateResult(
        gate_id="P0-INGESTION-LAG",
        passed=passed,
        details={
            "slo_seconds": slo_seconds,
            "max_lag_seconds": max_lag,
            "missing_timestamp_rows": missing,
            "row_count": len(approved_rows),
        },
    )


def _freshness_report(root: Path, approved_rows: list[dict[str, Any]], medallion_manifest: dict[str, Any], generated_at: str) -> dict[str, Any]:
    evaluation_time = _parse_time(generated_at)
    if not evaluation_time:
        raise ValueError(f"generated_at is not an ISO timestamp: {generated_at}")
    bronze_slo = _data_product_slo(root, "bronze.events_recommendation_tracking")
    silver_slo = _data_product_slo(root, "silver.learner_activity")
    gold_slo = _data_product_slo(root, "gold.recsys_interactions")
    latest_bronze_ingested = _latest_time(row.get("ingested_at") for row in approved_rows)
    medallion_time = _parse_time(medallion_manifest.get("generated_at"))
    return {
        "bronze.events_recommendation_tracking": _freshness_entry(evaluation_time, latest_bronze_ingested, bronze_slo),
        "silver.learner_activity": _freshness_entry(evaluation_time, medallion_time, silver_slo),
        "gold.recsys_interactions": _freshness_entry(evaluation_time, medallion_time, gold_slo),
    }


def _freshness_gate(freshness_report: dict[str, Any]) -> GateResult:
    return GateResult(
        gate_id="P0-FRESHNESS",
        passed=all(item.get("passed") is True for item in freshness_report.values()),
        details=freshness_report,
    )


def _quality_gate(ingestion_manifest: dict[str, Any], medallion_manifest: dict[str, Any]) -> GateResult:
    quarantine_rows = ingestion_manifest.get("quarantine", {}).get("row_count")
    passed = (
        ingestion_manifest.get("quality_passed") is True
        and medallion_manifest.get("quality_passed") is True
        and quarantine_rows == 0
    )
    return GateResult(
        gate_id="P0-QUALITY",
        passed=passed,
        details={
            "ingestion_quality_passed": ingestion_manifest.get("quality_passed"),
            "medallion_quality_passed": medallion_manifest.get("quality_passed"),
            "quarantine_rows": quarantine_rows,
            "gold_rows": medallion_manifest.get("row_count"),
        },
    )


def _gold_evidence_gate(
    ingestion_manifest: dict[str, Any],
    medallion_manifest: dict[str, Any],
    catalog_bundle: dict[str, Any],
) -> GateResult:
    source_positions = ingestion_manifest.get("source_positions")
    layers = medallion_manifest.get("layers", {})
    run_evidence_count = catalog_bundle.get("summary", {}).get("run_evidence_count", 0)
    required = {
        "snapshot_id": bool(medallion_manifest.get("snapshot_id")),
        "source_positions": bool(source_positions),
        "upstream_manifest_hash": bool(medallion_manifest.get("input", {}).get("upstream_manifest_hash")),
        "gold_content_hash": bool(medallion_manifest.get("content_hash")),
        "silver_layer_hash": bool(layers.get("silver.learner_activity", {}).get("content_hash")),
        "gold_layer_hash": bool(layers.get("gold.recsys_interactions", {}).get("content_hash")),
        "catalog_run_evidence": run_evidence_count >= 2,
    }
    return GateResult(
        gate_id="P0-GOLD-EVIDENCE",
        passed=all(required.values()),
        details=required,
    )


def _catalog_lineage_gate(catalog_bundle: dict[str, Any], medallion_manifest: dict[str, Any]) -> GateResult:
    edges = catalog_bundle.get("lineage_edges", [])
    edge_types = {edge.get("type") for edge in edges if isinstance(edge, dict)}
    passed = (
        "TOPIC_TO_BRONZE" in edge_types
        and "DATA_PRODUCT_UPSTREAM" in edge_types
        and "RUN_LAYER_TRANSFORM" in edge_types
        and catalog_bundle.get("summary", {}).get("run_evidence_count", 0) >= 2
        and any(
            run.get("snapshot_id") == medallion_manifest.get("snapshot_id")
            for run in catalog_bundle.get("run_evidence", [])
            if isinstance(run, dict)
        )
    )
    return GateResult(
        gate_id="P0-CATALOG-LINEAGE",
        passed=passed,
        details={
            "edge_types": sorted(str(edge_type) for edge_type in edge_types),
            "lineage_edge_count": len(edges),
            "run_evidence_count": catalog_bundle.get("summary", {}).get("run_evidence_count"),
        },
    )


def _contract_versions(root: Path) -> dict[str, int]:
    versions: dict[str, int] = {}
    for path in sorted((root / "contracts" / "topics").glob("*.yaml")):
        contract = load_yaml(path)
        name = contract.get("topic", {}).get("name")
        if isinstance(name, str):
            versions[f"topic:{name}"] = int(contract.get("contractVersion", 0))
    for path in sorted((root / "contracts" / "data-products").glob("*.yaml")):
        contract = load_yaml(path)
        name = contract.get("dataProduct", {}).get("name")
        if isinstance(name, str):
            versions[f"data-product:{name}"] = int(contract.get("contractVersion", 0))
    return versions


def _data_product_slo(root: Path, data_product_name: str) -> int:
    candidates = sorted((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))
    if not candidates:
        raise FileNotFoundError(f"data product contract does not exist: {data_product_name}")
    contract = load_yaml(max(candidates, key=lambda path: int(load_yaml(path).get("contractVersion", 0))))
    return int(contract.get("quality", {}).get("freshnessSloMinutes", 1)) * 60


def _topic_slo(root: Path, topic_name: str | None) -> int | None:
    if not topic_name:
        return None
    topic_path = root / "contracts" / "topics" / f"{topic_name}.yaml"
    if not topic_path.is_file():
        return None
    contract = load_yaml(topic_path)
    return int(contract.get("quality", {}).get("freshnessSloMinutes", 1)) * 60


def _approved_rows_from_ingestion_manifest(
    ingestion_manifest_path: Path,
    ingestion_manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], str | None]:
    approved = ingestion_manifest.get("approved")
    if not isinstance(approved, dict):
        return [], "approved_manifest_section_missing"
    approved_path_value = approved.get("path")
    if not isinstance(approved_path_value, str) or not approved_path_value:
        return [], "approved_manifest_path_missing"
    approved_path = Path(approved_path_value)
    if not approved_path.is_absolute():
        approved_path = ingestion_manifest_path.parent.parent / approved_path
    if not approved_path.is_file():
        return [], f"approved_bronze_file_missing:{approved_path.as_posix()}"
    try:
        return read_jsonl(approved_path), None
    except ValueError as exc:
        return [], f"approved_bronze_file_invalid:{exc}"


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


def _freshness_entry(evaluation_time: datetime, latest_time: datetime | None, slo_seconds: int) -> dict[str, Any]:
    age_seconds = (evaluation_time - latest_time).total_seconds() if latest_time else None
    return {
        "slo_seconds": slo_seconds,
        "age_seconds": age_seconds,
        "latest_time": latest_time.isoformat().replace("+00:00", "Z") if latest_time else None,
        "passed": age_seconds is not None and age_seconds <= slo_seconds,
    }


def _latest_time(values: Any) -> datetime | None:
    parsed = [_parse_time(value) for value in values]
    valid = [value for value in parsed if value is not None]
    return max(valid) if valid else None


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed


def canonical_json(record: Any) -> str:
    return json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
