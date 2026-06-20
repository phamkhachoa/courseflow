from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.access_grants import build_access_grant_ops_report, evaluate_access_grants
from enterprise_dp.access_governance import evaluate_consumer_contract_reference
from enterprise_dp.access_policies import evaluate_access_policy_contract
from enterprise_dp.capabilities import build_capability_maturity_report
from enterprise_dp.catalog import build_catalog_bundle, canonical_json, hash_file, load_json
from enterprise_dp.catalog_lineage_ops import build_catalog_lineage_ops_report
from enterprise_dp.catalog_runtime_ops import strict_catalog_runtime_ops_release_gate_passed
from enterprise_dp.contracts import ValidationResult, load_yaml, validate_data_product_contract
from enterprise_dp.ingestion_runtime import build_ingestion_runtime_ops_report
from enterprise_dp.lakehouse_ops import build_bronze_lakehouse_ops_report
from enterprise_dp.orchestration_runtime_ops import strict_orchestration_runtime_ops_release_gate_passed
from enterprise_dp.publication_ops import build_silver_gold_publication_ops_report
from enterprise_dp.quality_profiles import list_quality_profiles
from enterprise_dp.quality_slo_ops import build_quality_slo_ops_report
from enterprise_dp.runtime import build_runtime_readiness_report
from enterprise_dp.schema_registry import build_schema_registry_ops_report
from enterprise_dp.semantic_serving_ops import build_semantic_metric_serving_ops_report
from enterprise_dp.source_activation_ledger import (
    SOURCE_ACTIVATION_CRITICAL_RISK_STATES,
    build_source_activation_ops_report,
)


REPORT_VERSION = 1
P0 = "P0"
P1 = "P1"


@dataclass(frozen=True)
class ControlTowerReportResult:
    output_path: Path
    report: dict[str, Any]


def write_data_product_control_tower_report(
    root: str | Path,
    output_path: str | Path,
    *,
    catalog_bundle_path: str | Path | None = None,
    catalog_lineage_ops_report_path: str | Path | None = None,
    quality_slo_ops_report_path: str | Path | None = None,
    semantic_metric_serving_ops_report_path: str | Path | None = None,
    schema_registry_ops_report_path: str | Path | None = None,
    catalog_runtime_ops_report_path: str | Path | None = None,
    orchestration_runtime_ops_report_path: str | Path | None = None,
    data_plane_smoke_report_path: str | Path | None = None,
    release_evidence_paths: list[str | Path] | None = None,
    capability_maturity_report_path: str | Path | None = None,
    access_grant_ops_report_path: str | Path | None = None,
    source_activation_ops_report_path: str | Path | None = None,
    ingestion_runtime_report_path: str | Path | None = None,
    bronze_lakehouse_ops_report_path: str | Path | None = None,
    silver_gold_publication_ops_report_path: str | Path | None = None,
    contract_impact_report_paths: list[str | Path] | None = None,
    runtime_readiness_report_path: str | Path | None = None,
    environment: str = "local",
    generated_at: str | None = None,
) -> ControlTowerReportResult:
    report = build_data_product_control_tower_report(
        root,
        catalog_bundle_path=catalog_bundle_path,
        catalog_lineage_ops_report_path=catalog_lineage_ops_report_path,
        quality_slo_ops_report_path=quality_slo_ops_report_path,
        semantic_metric_serving_ops_report_path=semantic_metric_serving_ops_report_path,
        schema_registry_ops_report_path=schema_registry_ops_report_path,
        catalog_runtime_ops_report_path=catalog_runtime_ops_report_path,
        orchestration_runtime_ops_report_path=orchestration_runtime_ops_report_path,
        data_plane_smoke_report_path=data_plane_smoke_report_path,
        release_evidence_paths=release_evidence_paths,
        capability_maturity_report_path=capability_maturity_report_path,
        access_grant_ops_report_path=access_grant_ops_report_path,
        source_activation_ops_report_path=source_activation_ops_report_path,
        ingestion_runtime_report_path=ingestion_runtime_report_path,
        bronze_lakehouse_ops_report_path=bronze_lakehouse_ops_report_path,
        silver_gold_publication_ops_report_path=silver_gold_publication_ops_report_path,
        contract_impact_report_paths=contract_impact_report_paths,
        runtime_readiness_report_path=runtime_readiness_report_path,
        environment=environment,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return ControlTowerReportResult(output_path=target, report=report)


def build_data_product_control_tower_report(
    root: str | Path,
    *,
    catalog_bundle_path: str | Path | None = None,
    catalog_lineage_ops_report_path: str | Path | None = None,
    quality_slo_ops_report_path: str | Path | None = None,
    semantic_metric_serving_ops_report_path: str | Path | None = None,
    schema_registry_ops_report_path: str | Path | None = None,
    catalog_runtime_ops_report_path: str | Path | None = None,
    orchestration_runtime_ops_report_path: str | Path | None = None,
    data_plane_smoke_report_path: str | Path | None = None,
    release_evidence_paths: list[str | Path] | None = None,
    capability_maturity_report_path: str | Path | None = None,
    access_grant_ops_report_path: str | Path | None = None,
    source_activation_ops_report_path: str | Path | None = None,
    ingestion_runtime_report_path: str | Path | None = None,
    bronze_lakehouse_ops_report_path: str | Path | None = None,
    silver_gold_publication_ops_report_path: str | Path | None = None,
    contract_impact_report_paths: list[str | Path] | None = None,
    runtime_readiness_report_path: str | Path | None = None,
    environment: str = "local",
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    catalog_bundle, catalog_ref = resolve_catalog_bundle(
        platform_root,
        catalog_bundle_path=catalog_bundle_path,
        generated_at=generated,
    )
    catalog_lineage_ops_report, catalog_lineage_ops_ref = resolve_catalog_lineage_ops_report(
        platform_root,
        catalog_bundle_path=catalog_bundle_path,
        catalog_bundle=catalog_bundle,
        catalog_lineage_ops_report_path=catalog_lineage_ops_report_path,
        environment=environment,
        generated_at=generated,
    )
    release_evidences = [load_json(Path(path)) for path in release_evidence_paths or []]
    quality_slo_ops_report, quality_slo_ops_ref = resolve_quality_slo_ops_report(
        platform_root,
        catalog_bundle_path=catalog_bundle_path,
        catalog_bundle=catalog_bundle,
        quality_slo_ops_report_path=quality_slo_ops_report_path,
        release_evidence_paths=release_evidence_paths or [],
        environment=environment,
        generated_at=generated,
    )
    semantic_metric_serving_ops_report, semantic_metric_serving_ops_ref = resolve_semantic_metric_serving_ops_report(
        platform_root,
        semantic_metric_serving_ops_report_path=semantic_metric_serving_ops_report_path,
        environment=environment,
        generated_at=generated,
    )
    schema_registry_ops_report, schema_registry_ops_ref = resolve_schema_registry_ops_report(
        platform_root,
        schema_registry_ops_report_path=schema_registry_ops_report_path,
        environment=environment,
        generated_at=generated,
    )
    catalog_runtime_ops_report, catalog_runtime_ops_ref = resolve_catalog_runtime_ops_report(
        catalog_runtime_ops_report_path=catalog_runtime_ops_report_path,
    )
    orchestration_runtime_ops_report, orchestration_runtime_ops_ref = resolve_orchestration_runtime_ops_report(
        orchestration_runtime_ops_report_path=orchestration_runtime_ops_report_path,
    )
    data_plane_smoke_report, data_plane_smoke_ref = resolve_data_plane_smoke_report(
        data_plane_smoke_report_path=data_plane_smoke_report_path,
    )
    capability_report, capability_ref = resolve_capability_report(
        platform_root,
        capability_maturity_report_path=capability_maturity_report_path,
        generated_at=generated,
    )
    access_grant_ops_report, access_grant_ops_ref = resolve_access_grant_ops_report(
        platform_root,
        access_grant_ops_report_path=access_grant_ops_report_path,
        environment=environment,
        generated_at=generated,
    )
    source_activation_ops_report, source_activation_ops_ref = resolve_source_activation_ops_report(
        platform_root,
        source_activation_ops_report_path=source_activation_ops_report_path,
        environment=environment,
        generated_at=generated,
    )
    ingestion_runtime_report, ingestion_runtime_ref = resolve_ingestion_runtime_report(
        platform_root,
        ingestion_runtime_report_path=ingestion_runtime_report_path,
        environment=environment,
        generated_at=generated,
    )
    bronze_lakehouse_ops_report, bronze_lakehouse_ops_ref = resolve_bronze_lakehouse_ops_report(
        platform_root,
        bronze_lakehouse_ops_report_path=bronze_lakehouse_ops_report_path,
        environment=environment,
        generated_at=generated,
    )
    silver_gold_publication_ops_report, silver_gold_publication_ops_ref = resolve_silver_gold_publication_ops_report(
        platform_root,
        silver_gold_publication_ops_report_path=silver_gold_publication_ops_report_path,
        environment=environment,
        generated_at=generated,
    )
    contract_impact_reports, contract_impact_ref = resolve_contract_impact_reports(contract_impact_report_paths or [])
    runtime_readiness_report, runtime_readiness_ref = resolve_runtime_readiness_report(
        platform_root,
        runtime_readiness_report_path=runtime_readiness_report_path,
        environment=environment,
        generated_at=generated,
    )
    quality_profiles = list_quality_profiles(platform_root)
    lineage_index = build_lineage_index(catalog_bundle)
    catalog_lineage_ops_index = build_catalog_lineage_ops_index(catalog_lineage_ops_report)
    quality_slo_ops_index = build_quality_slo_ops_index(quality_slo_ops_report)
    release_index = build_release_index(release_evidences, release_evidence_paths or [])
    access_grant_ops_index = build_access_grant_ops_index(access_grant_ops_report)
    products = [
        data_product_control_entry(
            platform_root,
            data_product,
            quality_profiles=quality_profiles,
            lineage_index=lineage_index,
            catalog_lineage_ops_index=catalog_lineage_ops_index,
            quality_slo_ops_index=quality_slo_ops_index,
            release_index=release_index,
            access_grant_ops_index=access_grant_ops_index,
            generated_at=generated,
        )
        for data_product in sorted(catalog_bundle.get("data_products", []), key=lambda item: str(item.get("name")))
        if isinstance(data_product, dict)
    ]
    capability_blockers = capability_blocker_entries(capability_report)
    catalog_lineage_ops_blockers = catalog_lineage_ops_blocker_entries(
        catalog_lineage_ops_report,
        target_environment=environment,
        expected_catalog_hash=catalog_ref.get("hash"),
    )
    quality_slo_ops_blockers = quality_slo_ops_blocker_entries(
        quality_slo_ops_report,
        target_environment=environment,
    )
    semantic_metric_serving_ops_blockers = semantic_metric_serving_ops_blocker_entries(
        semantic_metric_serving_ops_report,
        target_environment=environment,
    )
    schema_registry_ops_blockers = schema_registry_ops_blocker_entries(
        schema_registry_ops_report,
        target_environment=environment,
    )
    catalog_runtime_ops_blockers = catalog_runtime_ops_blocker_entries(
        catalog_runtime_ops_report,
        target_environment=environment,
    )
    orchestration_runtime_ops_blockers = orchestration_runtime_ops_blocker_entries(
        orchestration_runtime_ops_report,
        target_environment=environment,
    )
    data_plane_smoke_blockers = data_plane_smoke_blocker_entries(
        data_plane_smoke_report,
        target_environment=environment,
    )
    access_grant_ops_blockers = access_grant_ops_blocker_entries(access_grant_ops_report)
    source_activation_ops_blockers = source_activation_ops_blocker_entries(
        source_activation_ops_report,
        target_environment=environment,
    )
    ingestion_runtime_blockers = ingestion_runtime_blocker_entries(
        ingestion_runtime_report,
        target_environment=environment,
    )
    bronze_lakehouse_ops_blockers = bronze_lakehouse_ops_blocker_entries(
        bronze_lakehouse_ops_report,
        target_environment=environment,
    )
    silver_gold_publication_ops_blockers = silver_gold_publication_ops_blocker_entries(
        silver_gold_publication_ops_report,
        target_environment=environment,
    )
    contract_impact_blockers = contract_impact_blocker_entries(contract_impact_reports)
    runtime_readiness_blockers = runtime_readiness_blocker_entries(runtime_readiness_report, target_environment=environment)
    product_blockers = [
        blocker
        for product in products
        for blocker in product["blockers"]
    ]
    p0_ready = (
        not product_blockers
        and not capability_blockers
        and not catalog_lineage_ops_blockers
        and not quality_slo_ops_blockers
        and not semantic_metric_serving_ops_blockers
        and not schema_registry_ops_blockers
        and not catalog_runtime_ops_blockers
        and not orchestration_runtime_ops_blockers
        and not data_plane_smoke_blockers
        and not access_grant_ops_blockers
        and not source_activation_ops_blockers
        and not ingestion_runtime_blockers
        and not bronze_lakehouse_ops_blockers
        and not silver_gold_publication_ops_blockers
        and not contract_impact_blockers
        and not runtime_readiness_blockers
    )
    report = {
        "artifact_type": "data_product_control_tower_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "data-product-control-tower",
            catalog_ref,
            catalog_lineage_ops_ref,
            quality_slo_ops_ref,
            semantic_metric_serving_ops_ref,
            schema_registry_ops_ref,
            catalog_runtime_ops_ref,
            orchestration_runtime_ops_ref,
            data_plane_smoke_ref,
            capability_ref,
            access_grant_ops_ref,
            source_activation_ops_ref,
            ingestion_runtime_ref,
            bronze_lakehouse_ops_ref,
            silver_gold_publication_ops_ref,
            release_index,
            generated,
        ),
        "generated_at": generated,
        "environment": environment,
        "scope": control_tower_scope(catalog_bundle),
        "readiness_state": "production_ready" if p0_ready else "not_ready",
        "p0_ready": p0_ready,
        "passed": p0_ready,
        "inputs": {
            "catalog_bundle": catalog_ref,
            "catalog_lineage_ops_report": catalog_lineage_ops_ref,
            "quality_slo_ops_report": quality_slo_ops_ref,
            "semantic_metric_serving_ops_report": semantic_metric_serving_ops_ref,
            "schema_registry_ops_report": schema_registry_ops_ref,
            "catalog_runtime_ops_report": catalog_runtime_ops_ref,
            "orchestration_runtime_ops_report": orchestration_runtime_ops_ref,
            "data_plane_smoke_report": data_plane_smoke_ref,
            "capability_maturity_report": capability_ref,
            "access_grant_ops_report": access_grant_ops_ref,
            "source_activation_ops_report": source_activation_ops_ref,
            "ingestion_runtime_report": ingestion_runtime_ref,
            "bronze_lakehouse_ops_report": bronze_lakehouse_ops_ref,
            "silver_gold_publication_ops_report": silver_gold_publication_ops_ref,
            "contract_impact_reports": contract_impact_ref,
            "runtime_readiness_report": runtime_readiness_ref,
            "release_evidence": release_evidence_summary(release_index),
        },
        "catalog": catalog_ref,
        "catalog_lineage_ops": catalog_lineage_ops_ref,
        "quality_slo_ops": quality_slo_ops_ref,
        "semantic_metric_serving_ops": semantic_metric_serving_ops_ref,
        "schema_registry_ops": schema_registry_ops_ref,
        "catalog_runtime_ops": catalog_runtime_ops_ref,
        "orchestration_runtime_ops": orchestration_runtime_ops_ref,
        "data_plane_smoke": data_plane_smoke_ref,
        "capability_maturity": capability_ref,
        "access_grant_ops": access_grant_ops_ref,
        "source_activation_ops": source_activation_ops_ref,
        "ingestion_runtime": ingestion_runtime_ref,
        "bronze_lakehouse_ops": bronze_lakehouse_ops_ref,
        "silver_gold_publication_ops": silver_gold_publication_ops_ref,
        "contract_impact": contract_impact_ref,
        "runtime_readiness": runtime_readiness_ref,
        "release_evidence": release_evidence_summary(release_index),
        "summary": control_tower_summary(
            products,
            capability_blockers,
            catalog_lineage_ops_report,
            catalog_lineage_ops_blockers,
            quality_slo_ops_report,
            quality_slo_ops_blockers,
            semantic_metric_serving_ops_report,
            semantic_metric_serving_ops_blockers,
            schema_registry_ops_report,
            schema_registry_ops_blockers,
            catalog_runtime_ops_report,
            catalog_runtime_ops_blockers,
            orchestration_runtime_ops_report,
            orchestration_runtime_ops_blockers,
            data_plane_smoke_report,
            data_plane_smoke_blockers,
            access_grant_ops_report,
            access_grant_ops_blockers,
            source_activation_ops_report,
            source_activation_ops_blockers,
            ingestion_runtime_report,
            ingestion_runtime_blockers,
            bronze_lakehouse_ops_report,
            bronze_lakehouse_ops_blockers,
            silver_gold_publication_ops_report,
            silver_gold_publication_ops_blockers,
            contract_impact_reports,
            contract_impact_blockers,
            runtime_readiness_report,
            runtime_readiness_blockers,
        ),
        "escalations": escalation_summary(
            product_blockers,
            capability_blockers,
            catalog_lineage_ops_blockers,
            quality_slo_ops_blockers,
            semantic_metric_serving_ops_blockers,
            schema_registry_ops_blockers,
            catalog_runtime_ops_blockers,
            orchestration_runtime_ops_blockers,
            data_plane_smoke_blockers,
            access_grant_ops_blockers,
            source_activation_ops_blockers,
            ingestion_runtime_blockers,
            bronze_lakehouse_ops_blockers,
            silver_gold_publication_ops_blockers,
            contract_impact_blockers,
            runtime_readiness_blockers,
        ),
        "gate_matrix": gate_matrix(products),
        "blockers": (
            product_blockers
            + capability_blockers
            + catalog_lineage_ops_blockers
            + quality_slo_ops_blockers
            + semantic_metric_serving_ops_blockers
            + schema_registry_ops_blockers
            + catalog_runtime_ops_blockers
            + orchestration_runtime_ops_blockers
            + data_plane_smoke_blockers
            + access_grant_ops_blockers
            + source_activation_ops_blockers
            + ingestion_runtime_blockers
            + bronze_lakehouse_ops_blockers
            + silver_gold_publication_ops_blockers
            + contract_impact_blockers
            + runtime_readiness_blockers
        ),
        "data_products": products,
    }
    validation = validate_data_product_control_tower_report(report)
    if not validation.ok:
        raise ValueError("; ".join(validation.errors))
    return report


def data_product_control_entry(
    root: Path,
    data_product: dict[str, Any],
    *,
    quality_profiles: list[dict[str, Any]],
    lineage_index: dict[str, dict[str, Any]],
    catalog_lineage_ops_index: dict[str, dict[str, Any]],
    quality_slo_ops_index: dict[str, dict[str, Any]],
    release_index: dict[str, list[dict[str, Any]]],
    access_grant_ops_index: dict[str, dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    name = str(data_product.get("name"))
    contract_path = root / str(data_product.get("contract_path"))
    contract = load_yaml(contract_path)
    contract_result = ValidationResult(checked_count=1)
    validate_data_product_contract(contract_path, contract, contract_result, root=root)
    contract_meta = contract.get("dataProduct", {}) if isinstance(contract.get("dataProduct"), dict) else {}
    quality = data_product.get("quality") if isinstance(data_product.get("quality"), dict) else {}
    quality_slo_ops = quality_slo_ops_index.get(name, empty_quality_slo_ops_coverage(name))
    serving = data_product.get("serving") if isinstance(data_product.get("serving"), dict) else {}
    privacy = data_product.get("privacy") if isinstance(data_product.get("privacy"), dict) else {}
    schema = contract.get("schema", {}) if isinstance(contract.get("schema"), dict) else {}
    columns = [column for column in schema.get("columns", []) if isinstance(column, dict)]
    access_policy = evaluate_safely(
        lambda: evaluate_access_policy_contract(
            root,
            data_product_name=name,
            layer=str(data_product.get("layer")),
            privacy=contract.get("privacy", {}) if isinstance(contract.get("privacy"), dict) else {},
            serving=contract.get("serving", {}) if isinstance(contract.get("serving"), dict) else {},
            columns=columns,
        ),
        fallback={"passed": False, "checks": [], "error": "access_policy_evaluation_failed"},
    )
    consumer_contract = evaluate_safely(
        lambda: evaluate_consumer_contract_reference(
            root,
            data_product_name=name,
            layer=str(data_product.get("layer")),
            privacy=contract.get("privacy", {}) if isinstance(contract.get("privacy"), dict) else {},
            serving=contract.get("serving", {}) if isinstance(contract.get("serving"), dict) else {},
        ),
        fallback={"passed": False, "checks": [], "error": "consumer_contract_evaluation_failed"},
    )
    access_grants = evaluate_safely(
        lambda: evaluate_access_grants(
            root,
            data_product_name=name,
            serving=contract.get("serving", {}) if isinstance(contract.get("serving"), dict) else {},
            evaluation_time=generated_at,
        ),
        fallback={"passed": False, "checks": [], "active_grant_count": 0, "error": "access_grant_evaluation_failed"},
    )
    profiles = quality_profiles_for_data_product(name, quality_profiles)
    lineage = lineage_index.get(name, empty_lineage_coverage(name))
    catalog_lineage_ops = catalog_lineage_ops_index.get(name, empty_catalog_lineage_ops_coverage(name))
    lineage = {
        **lineage,
        "runtime_lineage_present": lineage.get("runtime_lineage_present") is True
        or int_value(catalog_lineage_ops.get("runtime_event_count")) > 0,
        "catalog_publish_status": catalog_lineage_ops.get("catalog_publish_status"),
        "openlineage_event_count": catalog_lineage_ops.get("runtime_event_count", 0),
        "catalog_lineage_ops_passed": catalog_lineage_ops.get("passed"),
        "catalog_lineage_ops_risk_state": catalog_lineage_ops.get("risk_state"),
        "last_runtime_run_id": catalog_lineage_ops.get("last_runtime_run_id"),
        "last_runtime_run_at": catalog_lineage_ops.get("last_runtime_run_at"),
    }
    releases = release_index.get(name, [])
    grant_ops = access_grant_ops_index.get(name, empty_access_grant_ops_coverage(name))
    release_passed = any(release.get("release_passed") is True for release in releases)
    layer = str(data_product.get("layer") or "")
    checks = product_checks(
        data_product=data_product,
        contract_result=contract_result,
        quality=quality,
        serving=serving,
        privacy=privacy,
        profiles=profiles,
        lineage=lineage,
        access_policy=access_policy,
        consumer_contract=consumer_contract,
        access_grants=access_grants,
        access_grant_ops=grant_ops,
        release_count=len(releases),
        release_passed=release_passed,
    )
    blockers = [
        blocker_entry(name, data_product, check)
        for check in checks
        if check["severity"] == P0 and check["passed"] is not True
    ]
    return {
        "name": name,
        "urn": data_product.get("urn"),
        "contract_urn": data_product.get("contract_urn"),
        "contract_path": data_product.get("contract_path"),
        "contract_hash": data_product.get("contract_hash"),
        "contract": {
            "contract_version": contract.get("contractVersion"),
            "valid": not contract_result.errors,
            "validation_errors": contract_result.errors,
            "schema_column_count": len(columns),
        },
        "layer": layer,
        "product": data_product.get("product"),
        "domain": data_product.get("domain"),
        "status": data_product.get("status"),
        "owners": {
            "domain_owner": data_product.get("domain_owner"),
            "owner_team": data_product.get("owner_team"),
            "business_owner": data_product.get("business_owner"),
            "technical_owner": data_product.get("technical_owner"),
            "data_steward": data_product.get("data_steward"),
        },
        "privacy": {
            "classification": privacy.get("classification"),
            "contains_pii": privacy.get("contains_pii"),
            "tenant_isolation": privacy.get("tenant_isolation"),
            "retention_days": privacy.get("retention_days"),
        },
        "quality": {
            "freshness_slo_minutes": quality.get("freshness_slo_minutes"),
            "check_count": len(quality.get("checks", [])) if isinstance(quality.get("checks"), list) else 0,
            "quality_profiles": [profile_summary(profile) for profile in profiles],
            "quality_slo_ops": {
                "passed": quality_slo_ops.get("passed"),
                "risk_state": quality_slo_ops.get("risk_state"),
                "release": quality_slo_ops.get("release", {}),
                "runtime_quality": quality_slo_ops.get("runtime_quality", {}),
                "issues": quality_slo_ops.get("issues", []),
            },
        },
        "access": {
            "access_policy": serving.get("access_policy"),
            "access_policy_passed": access_policy.get("passed") is True,
            "consumer_contract": serving.get("consumer_contract"),
            "consumer_contract_passed": consumer_contract.get("passed") is True,
            "access_personas": serving.get("access_personas", []),
            "active_grant_count": access_grants.get("active_grant_count", 0),
            "active_personas": access_grants.get("active_personas", []),
            "grant_ops": grant_ops,
        },
        "lineage": lineage,
        "release_evidence": {
            "covered": bool(releases),
            "passed": release_passed,
            "release_count": len(releases),
            "releases": [
                {
                    "release_id": release.get("release_id"),
                    "use_case_id": release.get("use_case_id"),
                    "release_passed": release.get("release_passed"),
                    "evidence_uri": release.get("evidence_uri"),
                    "evidence_hash": release.get("evidence_hash"),
                }
                for release in releases
            ],
        },
        "checks": checks,
        "blockers": blockers,
        "readiness_state": "ready_for_production_signoff" if not blockers else "blocked",
    }


def product_checks(
    *,
    data_product: dict[str, Any],
    contract_result: ValidationResult,
    quality: dict[str, Any],
    serving: dict[str, Any],
    privacy: dict[str, Any],
    profiles: list[dict[str, Any]],
    lineage: dict[str, Any],
    access_policy: dict[str, Any],
    consumer_contract: dict[str, Any],
    access_grants: dict[str, Any],
    access_grant_ops: dict[str, Any],
    release_count: int,
    release_passed: bool,
) -> list[dict[str, Any]]:
    layer = str(data_product.get("layer") or "")
    lineage_required = bool(lineage.get("lineage_required"))
    is_gold = layer == "GOLD"
    is_serving_layer = layer in {"SILVER", "GOLD"}
    return [
        check("contract_valid", not contract_result.errors, P0, {"errors": contract_result.errors}),
        check("contract_active", data_product.get("status") == "ACTIVE", P0, {"status": data_product.get("status")}),
        check("owner_team_declared", non_empty(data_product.get("owner_team")), P0, {"owner_team": data_product.get("owner_team")}),
        check("data_steward_declared", non_empty(data_product.get("data_steward")), P0, {"data_steward": data_product.get("data_steward")}),
        check(
            "freshness_slo_declared",
            isinstance(quality.get("freshness_slo_minutes"), int) and quality.get("freshness_slo_minutes") > 0,
            P0,
            {"freshness_slo_minutes": quality.get("freshness_slo_minutes")},
        ),
        check(
            "quality_checks_declared",
            isinstance(quality.get("checks"), list) and bool(quality.get("checks")),
            P0,
            {"check_count": len(quality.get("checks", [])) if isinstance(quality.get("checks"), list) else 0},
        ),
        check(
            "gold_quality_profile_attached",
            not is_gold or bool(profiles),
            P0,
            {"profile_ids": [profile.get("id") for profile in profiles]},
        ),
        check(
            "catalog_lineage_declared",
            not lineage_required or lineage.get("static_lineage_present") is True,
            P0,
            lineage,
        ),
        check(
            "runtime_lineage_evidence_present",
            not lineage_required or lineage.get("runtime_lineage_present") is True,
            P0,
            lineage,
        ),
        check(
            "access_policy_passed",
            not is_serving_layer or access_policy.get("passed") is True,
            P0,
            {"access_policy": serving.get("access_policy"), "evaluation": compact_evaluation(access_policy)},
        ),
        check(
            "consumer_contract_passed",
            not is_serving_layer or consumer_contract.get("passed") is True,
            P0,
            {"consumer_contract": serving.get("consumer_contract"), "evaluation": compact_evaluation(consumer_contract)},
        ),
        check(
            "gold_access_grants_active",
            not is_gold or int_value(access_grants.get("active_grant_count")) > 0,
            P0,
            {
                "active_grant_count": access_grants.get("active_grant_count", 0),
                "active_personas": access_grants.get("active_personas", []),
            },
        ),
        check(
            "serving_access_grant_requirements_passed",
            not is_serving_layer or access_grants.get("passed") is True,
            P0,
            {
                "evaluation": compact_evaluation(access_grants),
                "active_grant_count": access_grants.get("active_grant_count", 0),
                "missing_personas": access_grants.get("missing_personas", []),
                "expired_grants": access_grants.get("expired_grants", []),
                "incomplete_grants": access_grants.get("incomplete_grants", []),
            },
        ),
        check(
            "access_grant_ops_p0_clear",
            not is_serving_layer or int_value(access_grant_ops.get("p0_issue_count")) == 0,
            P0,
            {
                "grant_count": access_grant_ops.get("grant_count", 0),
                "p0_issue_count": access_grant_ops.get("p0_issue_count", 0),
                "p1_issue_count": access_grant_ops.get("p1_issue_count", 0),
                "p2_issue_count": access_grant_ops.get("p2_issue_count", 0),
                "issue_ids": access_grant_ops.get("issue_ids", []),
                "grant_ids": access_grant_ops.get("grant_ids", []),
            },
        ),
        check(
            "gold_release_evidence_passed",
            not is_gold or release_passed,
            P0,
            {"release_count": release_count, "release_passed": release_passed},
        ),
        check(
            "tenant_isolation_declared",
            privacy.get("tenant_isolation") == "REQUIRED",
            P1,
            {"tenant_isolation": privacy.get("tenant_isolation")},
        ),
    ]


def resolve_catalog_bundle(
    root: Path,
    *,
    catalog_bundle_path: str | Path | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if catalog_bundle_path:
        path = Path(catalog_bundle_path)
        bundle = load_json(path)
        return bundle, {
            "source": "artifact",
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "generated_at": bundle.get("generated_at"),
            "summary": bundle.get("summary", {}),
        }
    bundle = build_catalog_bundle(root, generated_at=generated_at)
    return bundle, {
        "source": "generated_from_root",
        "uri": None,
        "hash": content_hash(bundle),
        "generated_at": bundle.get("generated_at"),
        "summary": bundle.get("summary", {}),
    }


def resolve_catalog_lineage_ops_report(
    root: Path,
    *,
    catalog_bundle_path: str | Path | None,
    catalog_bundle: dict[str, Any],
    catalog_lineage_ops_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if catalog_lineage_ops_report_path:
        path = Path(catalog_lineage_ops_report_path)
        report = load_json(path)
        return report, catalog_lineage_ops_ref(report, source="artifact", path=path)
    report = build_catalog_lineage_ops_report(
        root,
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        catalog_bundle=catalog_bundle,
        generated_at=generated_at,
    )
    return report, catalog_lineage_ops_ref(report, source="generated_from_root", path=None)


def catalog_lineage_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    inputs = report.get("inputs") if isinstance(report.get("inputs"), dict) else {}
    catalog_bundle = inputs.get("catalog_bundle") if isinstance(inputs.get("catalog_bundle"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "catalog_hash": summary.get("catalog_hash") or catalog_bundle.get("hash"),
        "catalog_publish_status": summary.get("catalog_publish_status"),
        "catalog_publish_manifest_attached": summary.get("catalog_publish_manifest_attached"),
        "openlineage_event_count": summary.get("openlineage_event_count", 0),
        "publish_receipt_attached": summary.get("publish_receipt_attached"),
        "failed_product_count": summary.get("failed_product_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
    }


def resolve_quality_slo_ops_report(
    root: Path,
    *,
    catalog_bundle_path: str | Path | None,
    catalog_bundle: dict[str, Any],
    quality_slo_ops_report_path: str | Path | None,
    release_evidence_paths: list[str | Path],
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if quality_slo_ops_report_path:
        path = Path(quality_slo_ops_report_path)
        report = load_json(path)
        return report, quality_slo_ops_ref(report, source="artifact", path=path)
    report = build_quality_slo_ops_report(
        root,
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        catalog_bundle=catalog_bundle,
        release_evidence_paths=release_evidence_paths,
        generated_at=generated_at,
    )
    return report, quality_slo_ops_ref(report, source="generated_from_root", path=None)


def quality_slo_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "release_evidence_count": summary.get("release_evidence_count", 0),
        "failed_product_count": summary.get("failed_product_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "runtime_quality_attached": summary.get("runtime_quality_attached"),
        "runtime_freshness_breach_count": summary.get("runtime_freshness_breach_count", 0),
        "alert_evidence_attached": summary.get("alert_evidence_attached"),
        "incident_report_attached": summary.get("incident_report_attached"),
    }


def resolve_semantic_metric_serving_ops_report(
    root: Path,
    *,
    semantic_metric_serving_ops_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if semantic_metric_serving_ops_report_path:
        path = Path(semantic_metric_serving_ops_report_path)
        report = load_json(path)
        return report, semantic_metric_serving_ops_ref(report, source="artifact", path=path)
    report = build_semantic_metric_serving_ops_report(
        root,
        environment=environment,
        generated_at=generated_at,
    )
    return report, semantic_metric_serving_ops_ref(report, source="generated_from_root", path=None)


def semantic_metric_serving_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "metric_count": summary.get("metric_count", 0),
        "failed_metric_count": summary.get("failed_metric_count", 0),
        "certified_metric_count": summary.get("certified_metric_count", 0),
        "deployment_evidence_attached": summary.get("deployment_evidence_attached"),
        "usage_evidence_attached": summary.get("usage_evidence_attached"),
        "usage_tracking_gap_count": summary.get("usage_tracking_gap_count", 0),
    }


def resolve_schema_registry_ops_report(
    root: Path,
    *,
    schema_registry_ops_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if schema_registry_ops_report_path:
        path = Path(schema_registry_ops_report_path)
        report = load_json(path)
        return report, schema_registry_ops_ref(report, source="artifact", path=path)
    report = build_schema_registry_ops_report(
        root,
        environment=environment,
        generated_at=generated_at,
    )
    return report, schema_registry_ops_ref(report, source="generated_from_root", path=None)


def schema_registry_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "registry_uri": report.get("registry_uri"),
        "subject_count": summary.get("subject_count", 0),
        "failed_subject_count": summary.get("failed_subject_count", 0),
        "p0_subject_count": summary.get("p0_subject_count", 0),
        "p0_failed_subject_count": summary.get("p0_failed_subject_count", 0),
        "publication_evidence_attached": summary.get("publication_evidence_attached"),
        "producer_enforcement_gap_count": summary.get("producer_enforcement_gap_count", 0),
        "broker_validation_gap_count": summary.get("broker_validation_gap_count", 0),
    }


def resolve_catalog_runtime_ops_report(
    *,
    catalog_runtime_ops_report_path: str | Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not catalog_runtime_ops_report_path:
        return {}, {
            "source": "not_attached",
            "uri": None,
            "hash": None,
            "artifact_type": None,
            "attached": False,
            "passed": None,
        }
    path = Path(catalog_runtime_ops_report_path)
    report = load_json(path)
    return report, catalog_runtime_ops_ref(report, source="artifact", path=path)


def catalog_runtime_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "attached": True,
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "replica_count": summary.get("replica_count", 0),
        "availability_zones": summary.get("availability_zones", 0),
        "failover_passed": summary.get("failover_passed"),
        "stale_commit_rejected": summary.get("stale_commit_rejected"),
        "backup_enabled": summary.get("backup_enabled"),
        "pitr_enabled": summary.get("pitr_enabled"),
        "failed_check_count": summary.get("failed_check_count", 0),
    }


def resolve_orchestration_runtime_ops_report(
    *,
    orchestration_runtime_ops_report_path: str | Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not orchestration_runtime_ops_report_path:
        return {}, {
            "source": "not_attached",
            "uri": None,
            "hash": None,
            "artifact_type": None,
            "attached": False,
            "passed": None,
        }
    path = Path(orchestration_runtime_ops_report_path)
    report = load_json(path)
    return report, orchestration_runtime_ops_ref(report, source="artifact", path=path)


def orchestration_runtime_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "attached": True,
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "orchestrator_provider": summary.get("orchestrator_provider"),
        "distributed_executor_enabled": summary.get("distributed_executor_enabled"),
        "kubernetes_run_launcher_enabled": summary.get("kubernetes_run_launcher_enabled"),
        "managed_run_storage": summary.get("managed_run_storage"),
        "failed_check_count": summary.get("failed_check_count", 0),
    }


def resolve_data_plane_smoke_report(
    *,
    data_plane_smoke_report_path: str | Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not data_plane_smoke_report_path:
        return {}, {
            "source": "not_attached",
            "uri": None,
            "hash": None,
            "artifact_type": None,
            "attached": False,
            "passed": None,
        }
    path = Path(data_plane_smoke_report_path)
    report = load_json(path)
    return report, data_plane_smoke_ref(report, source="artifact", path=path)


def data_plane_smoke_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    query = report.get("query_smoke") if isinstance(report.get("query_smoke"), dict) else {}
    runtime_scope = report.get("runtime_scope") if isinstance(report.get("runtime_scope"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "attached": True,
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "release_id": report.get("release_id"),
        "use_case_id": report.get("use_case_id"),
        "runner_id": report.get("runner_id"),
        "primary_output": report.get("primary_output"),
        "passed": report.get("passed"),
        "runtime_mode": runtime_scope.get("mode"),
        "release_passed": summary.get("release_passed"),
        "all_layers_materialized": summary.get("all_layers_materialized"),
        "query_passed": summary.get("query_passed"),
        "failed_check_count": summary.get("failed_check_count", 0),
        "layer_count": summary.get("layer_count", 0),
        "query_name": query.get("query_name"),
        "query_result_row_count": query.get("result_row_count", 0),
        "not_covered": runtime_scope.get("not_covered", []),
    }


def resolve_capability_report(
    root: Path,
    *,
    capability_maturity_report_path: str | Path | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if capability_maturity_report_path:
        path = Path(capability_maturity_report_path)
        report = load_json(path)
        return report, {
            "source": "artifact",
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "readiness_state": report.get("readiness_state"),
            "p0_ready": report.get("p0_ready"),
            "blocker_count": len(report.get("blockers", [])) if isinstance(report.get("blockers"), list) else 0,
            "summary": report.get("summary", {}),
        }
    report = build_capability_maturity_report(root, phase="P0", generated_at=generated_at)
    return report, {
        "source": "generated_from_root",
        "uri": None,
        "hash": content_hash(report),
        "readiness_state": report.get("readiness_state"),
        "p0_ready": report.get("p0_ready"),
        "blocker_count": len(report.get("blockers", [])) if isinstance(report.get("blockers"), list) else 0,
        "summary": report.get("summary", {}),
    }


def resolve_access_grant_ops_report(
    root: Path,
    *,
    access_grant_ops_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if access_grant_ops_report_path:
        path = Path(access_grant_ops_report_path)
        report = load_json(path)
        return report, {
            "source": "artifact",
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "generated_at": report.get("generated_at"),
            "environment": report.get("environment"),
            "passed": report.get("passed"),
            "summary": report.get("summary", {}),
            "page_now": (report.get("decision_board") or {}).get("page_now", []) if isinstance(report.get("decision_board"), dict) else [],
        }
    report = build_access_grant_ops_report(
        root,
        environment=environment,
        generated_at=generated_at,
    )
    return report, {
        "source": "generated_from_root",
        "uri": None,
        "hash": content_hash(report),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "passed": report.get("passed"),
        "summary": report.get("summary", {}),
        "page_now": (report.get("decision_board") or {}).get("page_now", []) if isinstance(report.get("decision_board"), dict) else [],
    }


def resolve_source_activation_ops_report(
    root: Path,
    *,
    source_activation_ops_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if source_activation_ops_report_path:
        path = Path(source_activation_ops_report_path)
        report = load_json(path)
        return report, source_activation_ops_ref(report, source="artifact", path=path)
    report = build_source_activation_ops_report(
        root,
        environment=environment,
        generated_at=generated_at,
    )
    return report, source_activation_ops_ref(report, source="generated_from_root", path=None)


def source_activation_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    board = report.get("decision_board") if isinstance(report.get("decision_board"), dict) else {}
    ledger = report.get("ledger") if isinstance(report.get("ledger"), dict) else {}
    source_registry = report.get("source_registry") if isinstance(report.get("source_registry"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "passed": report.get("passed"),
        "ledger": {
            "path": ledger.get("path"),
            "hash": ledger.get("hash"),
            "exists": ledger.get("exists"),
            "validation_passed": ledger.get("validation_passed"),
            "validation_errors": ledger.get("validation_errors", []),
        },
        "source_registry": {
            "current_hash": source_registry.get("current_hash"),
        },
        "active_pointer_dir": report.get("active_pointer_dir"),
        "source_count": summary.get("source_count", 0),
        "active_count": summary.get("active_count", 0),
        "critical_issue_count": summary.get("critical_issue_count", 0),
        "runtime_readiness_issue_count": summary.get("runtime_readiness_issue_count", 0),
        "evidence_integrity_issue_count": summary.get("evidence_integrity_issue_count", 0),
        "p0_evidence_integrity_issue_count": summary.get("p0_evidence_integrity_issue_count", 0),
        "pointer_issue_count": summary.get("pointer_issue_count", 0),
        "registry_drift_count": summary.get("registry_drift_count", 0),
        "expired_count": summary.get("expired_count", 0),
        "critical_sources": board.get("critical_sources", []) if isinstance(board.get("critical_sources"), list) else [],
        "next_actions": board.get("next_actions", []) if isinstance(board.get("next_actions"), list) else [],
        "p0_next_action_count": len(
            [
                action
                for action in board.get("next_actions", [])
                if isinstance(action, dict) and action.get("priority") == P0
            ]
        )
        if isinstance(board.get("next_actions"), list)
        else 0,
    }


def resolve_ingestion_runtime_report(
    root: Path,
    *,
    ingestion_runtime_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if ingestion_runtime_report_path:
        path = Path(ingestion_runtime_report_path)
        report = load_json(path)
        return report, ingestion_runtime_ref(report, source="artifact", path=path)
    report = build_ingestion_runtime_ops_report(
        root,
        environment=environment,
        generated_at=generated_at,
    )
    return report, ingestion_runtime_ref(report, source="generated_from_root", path=None)


def ingestion_runtime_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "source_count": summary.get("source_count", 0),
        "p0_source_count": summary.get("p0_source_count", 0),
        "p0_failed_source_count": summary.get("p0_failed_source_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "running_connector_count": summary.get("running_connector_count", 0),
    }


def resolve_bronze_lakehouse_ops_report(
    root: Path,
    *,
    bronze_lakehouse_ops_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if bronze_lakehouse_ops_report_path:
        path = Path(bronze_lakehouse_ops_report_path)
        report = load_json(path)
        return report, bronze_lakehouse_ops_ref(report, source="artifact", path=path)
    report = build_bronze_lakehouse_ops_report(
        root,
        environment=environment,
        generated_at=generated_at,
    )
    return report, bronze_lakehouse_ops_ref(report, source="generated_from_root", path=None)


def bronze_lakehouse_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "source_count": summary.get("source_count", 0),
        "p0_source_count": summary.get("p0_source_count", 0),
        "ledger_attached_count": summary.get("ledger_attached_count", 0),
        "maintenance_attached_count": summary.get("maintenance_attached_count", 0),
        "p0_failed_table_count": summary.get("p0_failed_table_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
    }


def resolve_silver_gold_publication_ops_report(
    root: Path,
    *,
    silver_gold_publication_ops_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if silver_gold_publication_ops_report_path:
        path = Path(silver_gold_publication_ops_report_path)
        report = load_json(path)
        return report, silver_gold_publication_ops_ref(report, source="artifact", path=path)
    report = build_silver_gold_publication_ops_report(
        root,
        environment=environment,
        generated_at=generated_at,
    )
    return report, silver_gold_publication_ops_ref(report, source="generated_from_root", path=None)


def silver_gold_publication_ops_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "artifact_type": report.get("artifact_type"),
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "data_product_count": summary.get("data_product_count", 0),
        "failed_product_count": summary.get("failed_product_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "active_pointer_attached_count": summary.get("active_pointer_attached_count", 0),
    }


def resolve_contract_impact_reports(paths: list[str | Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    refs: list[dict[str, Any]] = []
    for path_value in paths:
        path = Path(path_value)
        report = load_json(path)
        reports.append(report)
        impact = report.get("impact") if isinstance(report.get("impact"), dict) else {}
        topic = report.get("topic") if isinstance(report.get("topic"), dict) else {}
        refs.append(
            {
                "uri": path.as_posix(),
                "hash": hash_file(path),
                "generated_at": report.get("generated_at"),
                "topic": topic.get("name"),
                "passed": report.get("passed"),
                "release_decision": impact.get("release_decision"),
                "risk_level": impact.get("risk_level"),
                "affected_data_product_count": impact.get("affected_data_product_count", 0),
                "affected_p0_use_case_count": impact.get("affected_p0_use_case_count", 0),
            }
        )
    blocked = [ref for ref in refs if ref.get("release_decision") == "blocked" or ref.get("passed") is False]
    review_required = [ref for ref in refs if ref.get("release_decision") == "review_required"]
    return reports, {
        "source": "artifact" if refs else "not_attached",
        "report_count": len(refs),
        "blocked_count": len(blocked),
        "review_required_count": len(review_required),
        "reports": refs,
    }


def resolve_runtime_readiness_report(
    root: Path,
    *,
    runtime_readiness_report_path: str | Path | None,
    environment: str,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if runtime_readiness_report_path:
        path = Path(runtime_readiness_report_path)
        report = load_json(path)
        return report, runtime_readiness_ref(report, source="artifact", path=path)
    report = build_runtime_readiness_report(
        root,
        environment=environment,
        generated_at=generated_at,
    )
    return report, runtime_readiness_ref(report, source="generated_from_root", path=None)


def runtime_readiness_ref(report: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(report),
        "generated_at": report.get("generated_at"),
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "failure_count": len(report.get("failures", [])) if isinstance(report.get("failures"), list) else 0,
        "failed_gate_count": summary.get("failed_gate_count", 0),
        "required_p0_service_count": summary.get("required_p0_service_count", 0),
        "deployed_service_count": summary.get("deployed_service_count", 0),
        "healthy_service_count": summary.get("healthy_service_count", 0),
    }


def build_access_grant_ops_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    grants = report.get("grants")
    if not isinstance(grants, list):
        return index
    for grant in grants:
        if not isinstance(grant, dict):
            continue
        data_product = grant.get("data_product")
        if not isinstance(data_product, str) or not data_product:
            continue
        entry = index.setdefault(data_product, empty_access_grant_ops_coverage(data_product))
        entry["grant_count"] += 1
        entry["grant_ids"].append(grant.get("grant_id"))
        if grant.get("status") == "active":
            entry["active_grant_count"] += 1
        for issue in grant.get("issues", []) if isinstance(grant.get("issues"), list) else []:
            if not isinstance(issue, dict):
                continue
            issue_id = str(issue.get("id") or "unknown")
            severity = str(issue.get("severity") or "P3")
            entry["issue_ids"].append(issue_id)
            if severity == P0:
                entry["p0_issue_count"] += 1
            elif severity == P1:
                entry["p1_issue_count"] += 1
            else:
                entry["p2_issue_count"] += 1
        entry["passed"] = entry["p0_issue_count"] == 0
    for entry in index.values():
        entry["grant_ids"] = sorted(str(item) for item in entry["grant_ids"] if item)
        entry["issue_ids"] = sorted(set(str(item) for item in entry["issue_ids"] if item))
    return index


def build_catalog_lineage_ops_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    rows = report.get("data_products")
    if not isinstance(rows, list):
        return index
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("data_product")
        if isinstance(name, str) and name:
            index[name] = row
    return index


def build_quality_slo_ops_index(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    rows = report.get("data_products")
    if not isinstance(rows, list):
        return index
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("data_product")
        if isinstance(name, str) and name:
            index[name] = row
    return index


def empty_catalog_lineage_ops_coverage(name: str) -> dict[str, Any]:
    return {
        "data_product": name,
        "passed": True,
        "risk_state": "not_attached",
        "catalog_publish_status": "NOT_ATTACHED",
        "runtime_event_count": 0,
        "last_runtime_run_id": None,
        "last_runtime_run_at": None,
    }


def empty_quality_slo_ops_coverage(name: str) -> dict[str, Any]:
    return {
        "data_product": name,
        "passed": True,
        "risk_state": "not_attached",
        "runtime_quality": {"attached": False},
        "issues": [],
    }


def empty_access_grant_ops_coverage(name: str) -> dict[str, Any]:
    return {
        "data_product": name,
        "passed": True,
        "grant_count": 0,
        "active_grant_count": 0,
        "p0_issue_count": 0,
        "p1_issue_count": 0,
        "p2_issue_count": 0,
        "issue_ids": [],
        "grant_ids": [],
    }


def build_lineage_index(catalog_bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    data_products = {
        item.get("name"): item
        for item in catalog_bundle.get("data_products", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    edges = [edge for edge in catalog_bundle.get("lineage_edges", []) if isinstance(edge, dict)]
    runs = [run for run in catalog_bundle.get("run_evidence", []) if isinstance(run, dict)]
    index: dict[str, dict[str, Any]] = {}
    for name, data_product in data_products.items():
        urn = f"urn:enterprise-dp:data-product:{name}"
        static_edges = [
            edge
            for edge in edges
            if edge.get("type") != "RUN_LAYER_TRANSFORM"
            and (edge.get("source") == urn or edge.get("target") == urn)
        ]
        runtime_edges = [
            edge
            for edge in edges
            if edge.get("type", "").startswith("RUN_")
            and (edge.get("source") == urn or edge.get("target") == urn)
        ]
        runtime_runs = [
            run
            for run in runs
            if run.get("bronze_target") == name
            or name in (run.get("layers", {}) if isinstance(run.get("layers"), dict) else {})
        ]
        lineage = data_product.get("lineage") if isinstance(data_product.get("lineage"), dict) else {}
        index[name] = {
            "lineage_required": lineage.get("lineage_required") is True,
            "catalog": lineage.get("catalog"),
            "static_lineage_present": bool(static_edges),
            "runtime_lineage_present": bool(runtime_edges or runtime_runs),
            "static_edge_count": len(static_edges),
            "runtime_edge_count": len(runtime_edges),
            "runtime_run_count": len(runtime_runs),
            "upstream": lineage.get("upstream", []),
        }
    return index


def build_release_index(releases: list[dict[str, Any]], paths: list[str | Path]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = {}
    for release, path_value in zip(releases, paths):
        path = Path(path_value)
        covered = set()
        primary_output = release.get("primary_output")
        if isinstance(primary_output, str):
            covered.add(primary_output)
        outputs = release.get("output_data_products")
        if isinstance(outputs, list):
            covered.update(item for item in outputs if isinstance(item, str))
        entry = {
            "release_id": release.get("release_id"),
            "use_case_id": release.get("use_case_id"),
            "release_passed": release.get("release_passed"),
            "primary_output": primary_output,
            "output_data_products": sorted(covered),
            "evidence_uri": path.as_posix(),
            "evidence_hash": hash_file(path) if path.is_file() else None,
        }
        for data_product_name in covered:
            index.setdefault(data_product_name, []).append(entry)
    return index


def release_evidence_summary(release_index: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    releases = {
        str(release.get("release_id"))
        for entries in release_index.values()
        for release in entries
        if release.get("release_id")
    }
    return {
        "release_count": len(releases),
        "covered_data_product_count": len(release_index),
        "covered_data_products": sorted(release_index),
    }


def quality_profiles_for_data_product(name: str, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched = []
    for profile in profiles:
        applies_to = profile.get("appliesTo") if isinstance(profile.get("appliesTo"), dict) else {}
        required_columns = profile.get("requiredColumns") if isinstance(profile.get("requiredColumns"), dict) else {}
        covered = set(profile.get("requiredOutputDataProducts", []) if isinstance(profile.get("requiredOutputDataProducts"), list) else [])
        covered.update(applies_to.get("primaryOutputs", []) if isinstance(applies_to.get("primaryOutputs"), list) else [])
        covered.update(key for key in required_columns if isinstance(key, str))
        if name in covered:
            matched.append(profile)
    return matched


def capability_blocker_entries(capability_report: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = []
    for blocker in capability_report.get("blockers", []):
        if not isinstance(blocker, dict):
            continue
        blockers.append(
            {
                "scope": "platform_capability",
                "data_product": None,
                "capability_id": blocker.get("capability_id"),
                "gate": "p0_capability_target_met",
                "severity": P0 if blocker.get("phase") == P0 else str(blocker.get("phase") or "P1"),
                "owner_team": "data-platform-team",
                "domain": "platform",
                "message": f"{blocker.get('capability_id')} is {blocker.get('current_level')} below target {blocker.get('target_level')}",
                "details": {
                    "missing_level_count": blocker.get("missing_level_count"),
                    "gaps": blocker.get("gaps", []),
                    "next_milestones": blocker.get("next_milestones", []),
                },
            }
        )
    return blockers


def catalog_lineage_ops_blocker_entries(
    report: dict[str, Any],
    *,
    target_environment: str,
    expected_catalog_hash: object,
) -> list[dict[str, Any]]:
    expected_state = "local_preflight_ready" if target_environment == "local" else "production_like_ready"
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "catalog_lineage_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "catalog_lineage_ops_artifact_type_valid",
                "message": "Catalog lineage ops artifact_type must be catalog_lineage_ops_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "catalog_lineage_ops_environment_matches_control_tower",
                "message": f"Catalog lineage ops environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("readiness_state") != expected_state:
        contract_failures.append(
            {
                "gate_id": "catalog_lineage_ops_state_valid_for_environment",
                "message": f"Catalog lineage ops readiness_state must be {expected_state}.",
            }
        )
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    inputs = report.get("inputs") if isinstance(report.get("inputs"), dict) else {}
    catalog_bundle = inputs.get("catalog_bundle") if isinstance(inputs.get("catalog_bundle"), dict) else {}
    catalog_hash = summary.get("catalog_hash") or catalog_bundle.get("hash")
    if expected_catalog_hash and catalog_hash != expected_catalog_hash:
        contract_failures.append(
            {
                "gate_id": "catalog_lineage_ops_catalog_hash_matches_control_tower",
                "message": "Catalog lineage ops catalog hash must match the Control Tower catalog input.",
                "details": {"expected_catalog_hash": expected_catalog_hash, "actual_catalog_hash": catalog_hash},
            }
        )
    if report.get("passed") is True and not contract_failures:
        return []

    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    board = report.get("decision_board") if isinstance(report.get("decision_board"), dict) else {}
    failed_products = board.get("failed_products") if isinstance(board.get("failed_products"), list) else []
    page_now = board.get("page_now") if isinstance(board.get("page_now"), list) else []
    blocker_gates = contract_failures + [
        {
            "gate_id": check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if report.get("passed") is not True:
        blocker_gates.append(
            {
                "gate_id": "catalog_lineage_ops_report_passed",
                "message": "Catalog lineage operations report is not passing.",
            }
        )
    if int_value(summary.get("failed_product_count")) > 0:
        blocker_gates.append(
            {
                "gate_id": "catalog_lineage_products_clear",
                "message": "Data products have catalog ownership, static lineage or runtime lineage failures.",
            }
        )
    return [
        {
            "scope": "catalog_lineage_ops",
            "data_product": None,
            "capability_id": "catalog-lineage-control-plane",
            "gate": "catalog_lineage_ops_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "catalog_lineage",
            "message": f"{report.get('environment')} catalog lineage ops is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "catalog_hash": catalog_hash,
                "expected_catalog_hash": expected_catalog_hash,
                "catalog_publish_status": summary.get("catalog_publish_status"),
                "openlineage_event_count": summary.get("openlineage_event_count", 0),
                "publish_receipt_attached": summary.get("publish_receipt_attached"),
                "failed_product_count": summary.get("failed_product_count", 0),
                "global_failed_check_count": summary.get("global_failed_check_count", 0),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
                "failed_products": failed_products[:30],
                "page_now": page_now[:30],
            },
        }
    ]


def quality_slo_ops_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    expected_state = "local_preflight_ready" if target_environment == "local" else "production_like_ready"
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "quality_slo_release_gates_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "quality_slo_release_gates_ops_artifact_type_valid",
                "message": "Quality/SLO release gates ops artifact_type must be quality_slo_release_gates_ops_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "quality_slo_release_gates_ops_environment_matches_control_tower",
                "message": f"Quality/SLO release gates ops environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("readiness_state") != expected_state:
        contract_failures.append(
            {
                "gate_id": "quality_slo_release_gates_ops_state_valid_for_environment",
                "message": f"Quality/SLO release gates ops readiness_state must be {expected_state}.",
            }
        )
    if report.get("passed") is True and not contract_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    board = report.get("decision_board") if isinstance(report.get("decision_board"), dict) else {}
    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    blocker_gates = contract_failures + [
        {
            "gate_id": check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if report.get("passed") is not True:
        blocker_gates.append(
            {
                "gate_id": "quality_slo_release_gates_ops_report_passed",
                "message": "Quality/SLO release gates operations report is not passing.",
            }
        )
    if int_value(summary.get("failed_product_count")) > 0:
        blocker_gates.append(
            {
                "gate_id": "quality_slo_release_gates_products_clear",
                "message": "Data products have quality profile, release quality, freshness or runtime quality failures.",
            }
        )
    return [
        {
            "scope": "quality_slo_release_gates",
            "data_product": None,
            "capability_id": "quality-slo-release-gates",
            "gate": "quality_slo_release_gates_ops_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "quality",
            "message": f"{report.get('environment')} quality/SLO release gates ops is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "release_evidence_count": summary.get("release_evidence_count", 0),
                "failed_product_count": summary.get("failed_product_count", 0),
                "global_failed_check_count": summary.get("global_failed_check_count", 0),
                "runtime_quality_attached": summary.get("runtime_quality_attached"),
                "runtime_freshness_breach_count": summary.get("runtime_freshness_breach_count", 0),
                "alert_evidence_attached": summary.get("alert_evidence_attached"),
                "incident_report_attached": summary.get("incident_report_attached"),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
                "failed_products": board.get("failed_products", [])[:30]
                if isinstance(board.get("failed_products"), list)
                else [],
                "page_now": board.get("page_now", [])[:30] if isinstance(board.get("page_now"), list) else [],
            },
        }
    ]


def semantic_metric_serving_ops_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    expected_state = "local_preflight_ready" if target_environment == "local" else "production_like_ready"
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "semantic_metric_serving_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "semantic_metric_serving_ops_artifact_type_valid",
                "message": "Semantic metric serving ops artifact_type must be semantic_metric_serving_ops_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "semantic_metric_serving_ops_environment_matches_control_tower",
                "message": f"Semantic metric serving ops environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("readiness_state") != expected_state:
        contract_failures.append(
            {
                "gate_id": "semantic_metric_serving_ops_state_valid_for_environment",
                "message": f"Semantic metric serving ops readiness_state must be {expected_state}.",
            }
        )
    if report.get("passed") is True and not contract_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    blocker_gates = contract_failures + [
        {
            "gate_id": check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if report.get("passed") is not True:
        blocker_gates.append(
            {
                "gate_id": "semantic_metric_serving_ops_report_passed",
                "message": "Semantic metric serving operations report is not passing.",
            }
        )
    if int_value(summary.get("failed_metric_count")) > 0:
        blocker_gates.append(
            {
                "gate_id": "semantic_metric_serving_metrics_clear",
                "message": "Semantic metrics have lifecycle, manifest, deployment or usage tracking failures.",
            }
        )
    return [
        {
            "scope": "semantic_metric_serving",
            "data_product": None,
            "capability_id": "semantic-metric-serving",
            "gate": "semantic_metric_serving_ops_passed",
            "severity": P0,
            "owner_team": "enterprise-reporting-team",
            "domain": "enterprise-reporting",
            "message": f"{report.get('environment')} semantic metric serving ops is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "metric_count": summary.get("metric_count", 0),
                "failed_metric_count": summary.get("failed_metric_count", 0),
                "certified_metric_count": summary.get("certified_metric_count", 0),
                "deployment_evidence_attached": summary.get("deployment_evidence_attached"),
                "usage_evidence_attached": summary.get("usage_evidence_attached"),
                "failed_gates": blocker_gates,
            },
        }
    ]


def schema_registry_ops_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    expected_state = "local_preflight_ready" if target_environment == "local" else "production_like_ready"
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "schema_registry_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "schema_registry_ops_artifact_type_valid",
                "message": "Schema registry ops artifact_type must be schema_registry_ops_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "schema_registry_ops_environment_matches_control_tower",
                "message": f"Schema registry ops environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("readiness_state") != expected_state:
        contract_failures.append(
            {
                "gate_id": "schema_registry_ops_state_valid_for_environment",
                "message": f"Schema registry ops readiness_state must be {expected_state}.",
            }
        )
    production_evidence_failures = schema_registry_production_evidence_failures(report, target_environment)
    if report.get("passed") is True and not contract_failures and not production_evidence_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    board = report.get("decision_board") if isinstance(report.get("decision_board"), dict) else {}
    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    blocker_gates = contract_failures + production_evidence_failures + [
        {
            "gate_id": check.get("check") or check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if report.get("passed") is not True:
        blocker_gates.append(
            {
                "gate_id": "schema_registry_ops_report_passed",
                "message": "Schema registry operations report is not passing.",
            }
        )
    if int_value(summary.get("p0_failed_subject_count")) > 0:
        blocker_gates.append(
            {
                "gate_id": "schema_registry_p0_subjects_clear",
                "message": "P0 schema registry subjects have compatibility, publication or producer enforcement failures.",
            }
        )
    return [
        {
            "scope": "schema_registry",
            "data_product": None,
            "capability_id": "schema-registry-compatibility",
            "gate": "schema_registry_ops_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "governance",
            "message": f"{report.get('environment')} schema registry ops is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "mode": report.get("mode"),
                "registry_uri": report.get("registry_uri"),
                "subject_count": summary.get("subject_count", 0),
                "failed_subject_count": summary.get("failed_subject_count", 0),
                "p0_subject_count": summary.get("p0_subject_count", 0),
                "p0_failed_subject_count": summary.get("p0_failed_subject_count", 0),
                "publication_evidence_attached": summary.get("publication_evidence_attached"),
                "producer_enforcement_gap_count": summary.get("producer_enforcement_gap_count", 0),
                "broker_validation_gap_count": summary.get("broker_validation_gap_count", 0),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
                "failed_subjects": board.get("failed_subjects", [])[:30]
                if isinstance(board.get("failed_subjects"), list)
                else [],
                "p0_failed_subjects": board.get("p0_failed_subjects", [])[:30]
                if isinstance(board.get("p0_failed_subjects"), list)
                else [],
            },
        }
    ]


def schema_registry_production_evidence_failures(
    report: dict[str, Any],
    target_environment: str,
) -> list[dict[str, Any]]:
    if target_environment == "local":
        return []
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    publication = report.get("publication_evidence") if isinstance(report.get("publication_evidence"), dict) else {}
    attestation = report.get("attestation") if isinstance(report.get("attestation"), dict) else {}
    attestation_required = attestation.get("required") if isinstance(attestation.get("required"), dict) else {}
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    subjects = report.get("subjects") if isinstance(report.get("subjects"), list) else []
    required_checks = {
        "compatibility_report_type_valid",
        "compatibility_report_passed",
        "publication_evidence_attached",
        "publication_evidence_type_valid",
        "publication_environment_matches",
        "production_registry_uri_declared",
        "external_attestation_verified",
        "attestation_subject_hash_matches_publication",
    }
    passed_check_names = {
        check.get("check")
        for check in checks
        if isinstance(check, dict) and check.get("passed") is True
    }
    p0_subject_rows = [
        subject
        for subject in subjects
        if isinstance(subject, dict) and schema_registry_subject_has_p0_source(subject)
    ]
    failures: list[dict[str, Any]] = []
    if not required_checks.issubset(passed_check_names):
        failures.append(
            {
                "gate_id": "schema_registry_ops_required_checks_passed",
                "message": "Production schema registry ops must include and pass all required publication, URI and attestation checks.",
                "details": {"missing_checks": sorted(required_checks - passed_check_names)},
            }
        )
    if (
        publication.get("attached") is not True
        or publication.get("artifact_type") != "schema_registry_publication_manifest.v1"
        or publication.get("environment") != target_environment
        or not sha256_value_valid(publication.get("hash"))
    ):
        failures.append(
            {
                "gate_id": "schema_registry_ops_publication_evidence_strict",
                "message": "Production schema registry ops must attach hash-bound publication evidence for the target environment.",
            }
        )
    if (
        attestation.get("attached") is not True
        or attestation.get("passed") is not True
        or attestation.get("subject_hash") != publication.get("hash")
        or attestation_required.get("signature_verified") is not True
        or attestation_required.get("subject_hash_matches") is not True
    ):
        failures.append(
            {
                "gate_id": "schema_registry_ops_attestation_strict",
                "message": "Production schema registry ops must be externally attested and hash-bound to the publication manifest.",
            }
        )
    if int_value(summary.get("p0_subject_count")) <= 0 or len(p0_subject_rows) != int_value(summary.get("p0_subject_count")):
        failures.append(
            {
                "gate_id": "schema_registry_ops_p0_subject_coverage",
                "message": "Production schema registry ops must identify every P0 subject row from source registry evidence.",
                "details": {
                    "summary_p0_subject_count": summary.get("p0_subject_count"),
                    "p0_subject_row_count": len(p0_subject_rows),
                },
            }
        )
    if any(
        not schema_registry_subject_row_release_ready(subject)
        for subject in subjects
        if isinstance(subject, dict)
    ):
        failures.append(
            {
                "gate_id": "schema_registry_ops_subject_runtime_evidence_strict",
                "message": "Every schema registry subject must include contract hash, payload schema hash, schema/artifact id, compatibility, producer enforcement and broker validation evidence.",
            }
        )
    return failures


def schema_registry_subject_has_p0_source(subject: dict[str, Any]) -> bool:
    sources = subject.get("sources") if isinstance(subject.get("sources"), list) else []
    return any(isinstance(source, dict) and source.get("priority") == "P0" for source in sources)


def schema_registry_subject_row_release_ready(subject: dict[str, Any]) -> bool:
    publication = subject.get("publication") if isinstance(subject.get("publication"), dict) else {}
    expected_compatibility = subject.get("expected_compatibility")
    payload_schema_hash = subject.get("payload_schema_hash")
    schema_id = publication.get("schema_id")
    artifact_id = publication.get("artifact_id")
    return (
        subject.get("passed") is True
        and isinstance(subject.get("subject"), str)
        and bool(subject.get("subject", "").strip())
        and sha256_value_valid(subject.get("contract_hash"))
        and isinstance(expected_compatibility, str)
        and expected_compatibility in {"BACKWARD", "BACKWARD_TRANSITIVE", "FULL", "FULL_TRANSITIVE"}
        and sha256_value_valid(payload_schema_hash)
        and publication.get("registered") is True
        and (
            (isinstance(schema_id, str) and bool(schema_id.strip()))
            or (isinstance(artifact_id, str) and bool(artifact_id.strip()))
        )
        and publication.get("compatibility") == expected_compatibility
        and publication.get("payload_schema_hash") == payload_schema_hash
        and publication.get("producer_enforced") is True
        and publication.get("broker_validation") is True
        and isinstance(publication.get("registry_uri"), str)
        and publication.get("registry_uri", "").startswith("https://")
        and not subject.get("issues")
    )


def catalog_runtime_ops_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    if not report:
        return []
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "catalog_runtime_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "catalog_runtime_ops_artifact_type_valid",
                "message": "Catalog runtime ops artifact_type must be catalog_runtime_ops_report.v1.",
            }
        )
    if target_environment in {"staging", "prod"} and report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "catalog_runtime_ops_environment_matches_control_tower",
                "message": f"Catalog runtime ops environment must match Control Tower environment {target_environment}.",
            }
        )
    release_gate_passed = strict_catalog_runtime_ops_release_gate_passed(
        report,
        target_environment=target_environment,
    )
    if release_gate_passed and not contract_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    blocker_gates = contract_failures + [
        {
            "gate_id": check.get("check") or check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if not release_gate_passed:
        blocker_gates.append(
            {
                "gate_id": "catalog_runtime_ops_release_gate_passed",
                "message": "Catalog runtime operations evidence is not production-like ready.",
            }
        )
    return [
        {
            "scope": "catalog_runtime",
            "data_product": None,
            "capability_id": "production-catalog-runtime",
            "gate": "catalog_runtime_ops_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "lakehouse",
            "message": f"{report.get('environment')} catalog runtime ops is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "mode": report.get("mode"),
                "replica_count": summary.get("replica_count", 0),
                "availability_zones": summary.get("availability_zones", 0),
                "multi_az": summary.get("multi_az"),
                "failover_passed": summary.get("failover_passed"),
                "stale_commit_rejected": summary.get("stale_commit_rejected"),
                "backup_enabled": summary.get("backup_enabled"),
                "pitr_enabled": summary.get("pitr_enabled"),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
            },
        }
    ]


def orchestration_runtime_ops_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    if not report:
        return []
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "orchestration_runtime_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "orchestration_runtime_ops_artifact_type_valid",
                "message": "Orchestration runtime ops artifact_type must be orchestration_runtime_ops_report.v1.",
            }
        )
    if target_environment in {"staging", "prod"} and report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "orchestration_runtime_ops_environment_matches_control_tower",
                "message": f"Orchestration runtime ops environment must match Control Tower environment {target_environment}.",
            }
        )
    release_gate_passed = strict_orchestration_runtime_ops_release_gate_passed(
        report,
        target_environment=target_environment,
    )
    if release_gate_passed and not contract_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    blocker_gates = contract_failures + [
        {
            "gate_id": check.get("check") or check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if not release_gate_passed:
        blocker_gates.append(
            {
                "gate_id": "orchestration_runtime_ops_release_gate_passed",
                "message": "Orchestration runtime operations evidence is not production-like ready.",
            }
        )
    return [
        {
            "scope": "orchestration_runtime",
            "data_product": None,
            "capability_id": "production-orchestration-runtime",
            "gate": "orchestration_runtime_ops_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "orchestration",
            "message": f"{report.get('environment')} orchestration runtime ops is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "mode": report.get("mode"),
                "orchestrator_provider": summary.get("orchestrator_provider"),
                "replica_count": summary.get("replica_count", 0),
                "availability_zones": summary.get("availability_zones", 0),
                "distributed_executor_enabled": summary.get("distributed_executor_enabled"),
                "kubernetes_run_launcher_enabled": summary.get("kubernetes_run_launcher_enabled"),
                "managed_run_storage": summary.get("managed_run_storage"),
                "schedule_tick_history_passed": summary.get("schedule_tick_history_passed"),
                "backfill_materialization_history_passed": summary.get("backfill_materialization_history_passed"),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
            },
        }
    ]


def data_plane_smoke_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    if not report:
        return []
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "data_plane_smoke_report.v1":
        contract_failures.append(
            {
                "gate_id": "data_plane_smoke_artifact_type_valid",
                "message": "Data-plane smoke artifact_type must be data_plane_smoke_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "data_plane_smoke_environment_matches_control_tower",
                "message": f"Data-plane smoke environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("passed") is True and not contract_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    query = report.get("query_smoke") if isinstance(report.get("query_smoke"), dict) else {}
    runtime_scope = report.get("runtime_scope") if isinstance(report.get("runtime_scope"), dict) else {}
    failed_checks = summary.get("failed_checks") if isinstance(summary.get("failed_checks"), list) else []
    blocker_gates = contract_failures
    if report.get("passed") is not True:
        blocker_gates = blocker_gates + [
            {
                "gate_id": "data_plane_smoke_report_passed",
                "message": "Data-plane smoke report is not passing.",
            }
        ]
    if summary.get("release_passed") is not True:
        blocker_gates = blocker_gates + [
            {
                "gate_id": "data_plane_smoke_release_gates_passed",
                "message": "The smoke slice release evidence did not pass.",
            }
        ]
    if summary.get("all_layers_materialized") is not True:
        blocker_gates = blocker_gates + [
            {
                "gate_id": "data_plane_smoke_layers_materialized",
                "message": "The smoke slice did not materialize all declared layers with matching hashes and row counts.",
            }
        ]
    if summary.get("query_passed") is not True:
        blocker_gates = blocker_gates + [
            {
                "gate_id": "data_plane_smoke_query_passed",
                "message": "The smoke slice Gold query probe did not pass.",
            }
        ]
    return [
        {
            "scope": "data_plane_runtime_smoke",
            "data_product": report.get("primary_output"),
            "capability_id": "platform-runtime-iac",
            "gate": "data_plane_smoke_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "platform",
            "message": f"{report.get('environment')} data-plane smoke is not passing.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "release_id": report.get("release_id"),
                "use_case_id": report.get("use_case_id"),
                "runner_id": report.get("runner_id"),
                "primary_output": report.get("primary_output"),
                "runtime_mode": runtime_scope.get("mode"),
                "release_passed": summary.get("release_passed"),
                "all_layers_materialized": summary.get("all_layers_materialized"),
                "query_passed": summary.get("query_passed"),
                "failed_check_count": summary.get("failed_check_count", 0),
                "failed_checks": failed_checks[:30],
                "query_name": query.get("query_name"),
                "query_result_row_count": query.get("result_row_count", 0),
                "not_covered": runtime_scope.get("not_covered", []),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
            },
        }
    ]


def access_grant_ops_blocker_entries(report: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    registry = report.get("registry") if isinstance(report.get("registry"), dict) else {}
    if registry.get("validation_passed") is not True:
        blockers.append(
            {
                "scope": "access_grant_registry",
                "data_product": None,
                "capability_id": None,
                "gate": "access_grant_registry_valid",
                "severity": P0,
                "owner_team": "data-platform-security",
                "domain": "governance",
                "message": "Access grant registry validation failed.",
                "details": {
                    "registry_path": registry.get("path"),
                    "validation_errors": registry.get("validation_errors", []),
                },
            }
        )
    grants = report.get("grants")
    if not isinstance(grants, list):
        return blockers
    for grant in grants:
        if not isinstance(grant, dict):
            continue
        data_product_exists = grant.get("data_product_exists") is True
        p0_issues = [
            issue
            for issue in grant.get("issues", [])
            if isinstance(issue, dict) and issue.get("severity") == P0
        ] if isinstance(grant.get("issues"), list) else []
        if data_product_exists or not p0_issues:
            continue
        blockers.append(
            {
                "scope": "access_grant",
                "data_product": grant.get("data_product"),
                "capability_id": None,
                "gate": "access_grant_ops_p0_clear",
                "severity": P0,
                "owner_team": "data-platform-security",
                "domain": grant.get("domain") or "governance",
                "message": f"{grant.get('grant_id')} has P0 access grant operations issues.",
                "details": {
                    "grant_id": grant.get("grant_id"),
                    "consumer": grant.get("consumer"),
                    "persona": grant.get("persona"),
                    "issue_ids": sorted(str(issue.get("id")) for issue in p0_issues if issue.get("id")),
                    "issues": p0_issues,
                },
            }
        )
    return blockers


def source_activation_ops_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "source_activation_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "source_activation_ops_artifact_type_valid",
                "message": "Source activation ops artifact_type must be source_activation_ops_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "source_activation_ops_environment_matches_control_tower",
                "message": f"Source activation ops environment must match Control Tower environment {target_environment}.",
            }
        )
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    ledger = report.get("ledger") if isinstance(report.get("ledger"), dict) else {}
    board = report.get("decision_board") if isinstance(report.get("decision_board"), dict) else {}
    sources = report.get("sources") if isinstance(report.get("sources"), list) else []
    critical_rows = [
        source
        for source in sources
        if isinstance(source, dict) and source.get("risk_state") in SOURCE_ACTIVATION_CRITICAL_RISK_STATES
    ]
    ledger_exists = ledger.get("exists")
    ledger_valid = ledger.get("validation_passed")
    if ledger_exists is not True:
        contract_failures.append(
            {
                "gate_id": "source_activation_ledger_exists",
                "message": "Source activation ledger must exist.",
            }
        )
    if ledger_valid is not True:
        contract_failures.append(
            {
                "gate_id": "source_activation_ledger_valid",
                "message": "Source activation ledger validation must pass.",
            }
        )
    if report.get("passed") is True and not contract_failures and not critical_rows:
        return []

    critical_sources = board.get("critical_sources") if isinstance(board.get("critical_sources"), list) else []
    next_actions = board.get("next_actions") if isinstance(board.get("next_actions"), list) else []
    blocker_gates = contract_failures
    if report.get("passed") is not True:
        blocker_gates = blocker_gates + [
            {
                "gate_id": "source_activation_ops_passed",
                "message": "Source activation operations report is not passing.",
            }
        ]
    if critical_rows:
        blocker_gates = blocker_gates + [
            {
                "gate_id": "source_activation_critical_risk_clear",
                "message": "Source activation operations report has critical source readiness risks.",
            }
        ]
    return [
        {
            "scope": "source_activation_ops",
            "data_product": None,
            "capability_id": "source-onboarding",
            "gate": "source_activation_ops_p0_clear",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "ingestion",
            "message": f"{report.get('environment')} source activation operations are not production-ready.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
                "source_count": summary.get("source_count", 0),
                "active_count": summary.get("active_count", 0),
                "critical_issue_count": summary.get("critical_issue_count", 0),
                "evidence_integrity_issue_count": summary.get("evidence_integrity_issue_count", 0),
                "p0_evidence_integrity_issue_count": summary.get("p0_evidence_integrity_issue_count", 0),
                "pointer_issue_count": summary.get("pointer_issue_count", 0),
                "registry_drift_count": summary.get("registry_drift_count", 0),
                "expired_count": summary.get("expired_count", 0),
                "ledger_validation_passed": ledger.get("validation_passed"),
                "ledger_validation_errors": ledger.get("validation_errors", []),
                "critical_sources": critical_sources[:20],
                "critical_source_rows": [compact_source_activation_blocker_row(row) for row in critical_rows[:30]],
                "p0_next_actions": [
                    action
                    for action in next_actions
                    if isinstance(action, dict) and action.get("priority") == P0
                ][:30],
            },
        }
    ]


def compact_source_activation_blocker_row(row: dict[str, Any]) -> dict[str, Any]:
    pointer = row.get("pointer") if isinstance(row.get("pointer"), dict) else {}
    return {
        "source_id": row.get("source_id"),
        "product": row.get("product"),
        "domain": row.get("domain"),
        "activation_id": row.get("activation_id"),
        "activation_state": row.get("activation_state"),
        "risk_state": row.get("risk_state"),
        "block_reason": row.get("block_reason"),
        "issues": row.get("issues", []),
        "readiness_id": row.get("readiness_id"),
        "expires_at": row.get("expires_at"),
        "days_to_expiry": row.get("days_to_expiry"),
        "pointer": {
            "path": pointer.get("path"),
            "hash": pointer.get("hash"),
            "consistency_state": pointer.get("consistency_state"),
            "mismatches": pointer.get("mismatches", []),
        },
        "source_registry_hash": row.get("source_registry_hash"),
        "current_source_registry_hash": row.get("current_source_registry_hash"),
        "impacted_use_cases": row.get("impacted_use_cases", []),
        "next_actions": row.get("next_actions", []),
    }


def ingestion_runtime_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    expected_state = "local_preflight_ready" if target_environment == "local" else "production_like_ready"
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "event_cdc_ingestion_runtime_report.v1":
        contract_failures.append(
            {
                "gate_id": "ingestion_runtime_artifact_type_valid",
                "message": "Ingestion runtime artifact_type must be event_cdc_ingestion_runtime_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "ingestion_runtime_environment_matches_control_tower",
                "message": f"Ingestion runtime environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("readiness_state") != expected_state:
        contract_failures.append(
            {
                "gate_id": "ingestion_runtime_state_valid_for_environment",
                "message": f"Ingestion runtime state must be {expected_state}.",
            }
        )
    if report.get("passed") is True and not contract_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    board = report.get("decision_board") if isinstance(report.get("decision_board"), dict) else {}
    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    p0_failed_sources = board.get("p0_failed_sources") if isinstance(board.get("p0_failed_sources"), list) else []
    page_now = board.get("page_now") if isinstance(board.get("page_now"), list) else []
    blocker_gates = contract_failures + [
        {
            "gate_id": check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if report.get("passed") is not True:
        blocker_gates.append(
            {
                "gate_id": "ingestion_runtime_report_passed",
                "message": "Event/CDC ingestion runtime report is not passing.",
            }
        )
    if int_value(summary.get("p0_failed_source_count")) > 0:
        blocker_gates.append(
            {
                "gate_id": "ingestion_runtime_p0_sources_clear",
                "message": "P0 event/CDC sources have runtime readiness failures.",
            }
        )
    return [
        {
            "scope": "ingestion_runtime",
            "data_product": None,
            "capability_id": "event-cdc-ingestion-runtime",
            "gate": "ingestion_runtime_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "ingestion",
            "message": f"{report.get('environment')} event/CDC ingestion runtime is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
                "source_count": summary.get("source_count", 0),
                "p0_source_count": summary.get("p0_source_count", 0),
                "p0_failed_source_count": summary.get("p0_failed_source_count", 0),
                "global_failed_check_count": summary.get("global_failed_check_count", 0),
                "running_connector_count": summary.get("running_connector_count", 0),
                "p0_failed_sources": p0_failed_sources[:30],
                "page_now": page_now[:30],
            },
        }
    ]


def bronze_lakehouse_ops_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    expected_state = "local_preflight_ready" if target_environment == "local" else "production_like_ready"
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "bronze_lakehouse_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "bronze_lakehouse_ops_artifact_type_valid",
                "message": "Bronze lakehouse ops artifact_type must be bronze_lakehouse_ops_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "bronze_lakehouse_ops_environment_matches_control_tower",
                "message": f"Bronze lakehouse ops environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("readiness_state") != expected_state:
        contract_failures.append(
            {
                "gate_id": "bronze_lakehouse_ops_state_valid_for_environment",
                "message": f"Bronze lakehouse ops readiness_state must be {expected_state}.",
            }
        )
    if report.get("passed") is True and not contract_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    board = report.get("decision_board") if isinstance(report.get("decision_board"), dict) else {}
    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    p0_failed_tables = board.get("p0_failed_tables") if isinstance(board.get("p0_failed_tables"), list) else []
    page_now = board.get("page_now") if isinstance(board.get("page_now"), list) else []
    blocker_gates = contract_failures + [
        {
            "gate_id": check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if report.get("passed") is not True:
        blocker_gates.append(
            {
                "gate_id": "bronze_lakehouse_ops_report_passed",
                "message": "Bronze lakehouse operations report is not passing.",
            }
        )
    if int_value(summary.get("p0_failed_table_count")) > 0:
        blocker_gates.append(
            {
                "gate_id": "bronze_lakehouse_p0_tables_clear",
                "message": "P0 Bronze lakehouse tables have ledger, commit or maintenance evidence failures.",
            }
        )
    return [
        {
            "scope": "bronze_lakehouse_ops",
            "data_product": None,
            "capability_id": "bronze-lakehouse-evidence",
            "gate": "bronze_lakehouse_ops_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "lakehouse",
            "message": f"{report.get('environment')} Bronze lakehouse ops is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
                "source_count": summary.get("source_count", 0),
                "p0_source_count": summary.get("p0_source_count", 0),
                "ledger_attached_count": summary.get("ledger_attached_count", 0),
                "maintenance_attached_count": summary.get("maintenance_attached_count", 0),
                "p0_failed_table_count": summary.get("p0_failed_table_count", 0),
                "global_failed_check_count": summary.get("global_failed_check_count", 0),
                "p0_failed_tables": p0_failed_tables[:30],
                "page_now": page_now[:30],
            },
        }
    ]


def silver_gold_publication_ops_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    expected_state = "local_preflight_ready" if target_environment == "local" else "production_like_ready"
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "silver_gold_publication_ops_report.v1":
        contract_failures.append(
            {
                "gate_id": "silver_gold_publication_ops_artifact_type_valid",
                "message": "Silver/Gold publication ops artifact_type must be silver_gold_publication_ops_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "silver_gold_publication_ops_environment_matches_control_tower",
                "message": f"Silver/Gold publication ops environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("readiness_state") != expected_state:
        contract_failures.append(
            {
                "gate_id": "silver_gold_publication_ops_state_valid_for_environment",
                "message": f"Silver/Gold publication ops readiness_state must be {expected_state}.",
            }
        )
    if report.get("passed") is True and not contract_failures:
        return []

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    board = report.get("decision_board") if isinstance(report.get("decision_board"), dict) else {}
    failed_checks = (
        [
            check
            for check in report.get("checks", [])
            if isinstance(check, dict) and check.get("passed") is not True
        ]
        if isinstance(report.get("checks"), list)
        else []
    )
    failed_products = board.get("failed_products") if isinstance(board.get("failed_products"), list) else []
    page_now = board.get("page_now") if isinstance(board.get("page_now"), list) else []
    blocker_gates = contract_failures + [
        {
            "gate_id": check.get("name"),
            "message": check.get("message"),
            "details": check.get("details", {}),
        }
        for check in failed_checks
    ]
    if report.get("passed") is not True:
        blocker_gates.append(
            {
                "gate_id": "silver_gold_publication_ops_report_passed",
                "message": "Silver/Gold publication operations report is not passing.",
            }
        )
    if int_value(summary.get("failed_product_count")) > 0:
        blocker_gates.append(
            {
                "gate_id": "silver_gold_publication_products_clear",
                "message": "Silver/Gold data products have release, promotion, activation or active pointer failures.",
            }
        )
    return [
        {
            "scope": "silver_gold_publication_ops",
            "data_product": None,
            "capability_id": "silver-gold-publication",
            "gate": "silver_gold_publication_ops_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "lakehouse",
            "message": f"{report.get('environment')} Silver/Gold publication ops is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "failed_gate_count": len(blocker_gates),
                "failed_gates": blocker_gates,
                "data_product_count": summary.get("data_product_count", 0),
                "failed_product_count": summary.get("failed_product_count", 0),
                "global_failed_check_count": summary.get("global_failed_check_count", 0),
                "active_pointer_attached_count": summary.get("active_pointer_attached_count", 0),
                "failed_products": failed_products[:30],
                "page_now": page_now[:30],
            },
        }
    ]


def contract_impact_blocker_entries(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        impact = report.get("impact") if isinstance(report.get("impact"), dict) else {}
        topic = report.get("topic") if isinstance(report.get("topic"), dict) else {}
        compatibility = report.get("compatibility") if isinstance(report.get("compatibility"), dict) else {}
        release_decision = impact.get("release_decision")
        if report.get("passed") is not False and release_decision != "blocked":
            continue
        blockers.append(
            {
                "scope": "contract_impact",
                "data_product": None,
                "capability_id": None,
                "gate": "contract_impact_release_not_blocked",
                "severity": P0,
                "owner_team": topic.get("owner_team") or "data-platform-team",
                "domain": topic.get("domain") or "contracts",
                "message": f"{topic.get('name')} has blocked contract impact.",
                "details": {
                    "report_id": report.get("report_id"),
                    "topic": topic.get("name"),
                    "release_decision": release_decision,
                    "risk_level": impact.get("risk_level"),
                    "breaking_change_count": compatibility.get("breaking_change_count", 0),
                    "affected_data_product_count": impact.get("affected_data_product_count", 0),
                    "affected_p0_use_case_count": impact.get("affected_p0_use_case_count", 0),
                    "affected_data_products": [
                        product.get("name")
                        for product in report.get("affected_data_products", [])
                        if isinstance(product, dict) and product.get("name")
                    ],
                    "required_approvals": report.get("required_approvals", []),
                },
            }
        )
    return blockers


def runtime_readiness_blocker_entries(report: dict[str, Any], *, target_environment: str) -> list[dict[str, Any]]:
    expected_state = "local_preflight_ready" if target_environment == "local" else "production_like_ready"
    contract_failures: list[dict[str, Any]] = []
    if report.get("artifact_type") != "runtime_readiness_report.v1":
        contract_failures.append(
            {
                "gate_id": "runtime_readiness_artifact_type_valid",
                "message": "Runtime readiness artifact_type must be runtime_readiness_report.v1.",
            }
        )
    if report.get("environment") != target_environment:
        contract_failures.append(
            {
                "gate_id": "runtime_readiness_environment_matches_control_tower",
                "message": f"Runtime readiness environment must match Control Tower environment {target_environment}.",
            }
        )
    if report.get("readiness_state") != expected_state:
        contract_failures.append(
            {
                "gate_id": "runtime_readiness_state_valid_for_environment",
                "message": f"Runtime readiness state must be {expected_state}.",
            }
        )
    if report.get("passed") is True and not contract_failures:
        return []
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    failed_gates = (
        [
            gate
            for gate in report.get("gates", [])
            if isinstance(gate, dict) and gate.get("status") == "failed"
        ]
        if isinstance(report.get("gates"), list)
        else []
    )
    blocker_gates = contract_failures + [
        {
            "gate_id": gate.get("gate_id"),
            "message": gate.get("message"),
        }
        for gate in failed_gates
    ]
    return [
        {
            "scope": "runtime_readiness",
            "data_product": None,
            "capability_id": "platform-runtime-iac",
            "gate": "runtime_readiness_passed",
            "severity": P0,
            "owner_team": "data-platform-team",
            "domain": "platform",
            "message": f"{report.get('environment')} runtime readiness is {report.get('readiness_state')}.",
            "details": {
                "report_id": report.get("report_id"),
                "environment": report.get("environment"),
                "readiness_state": report.get("readiness_state"),
                "runtime_readiness": report.get("runtime_readiness"),
                "evidence_mode": report.get("evidence_mode"),
                "failed_gate_count": len(blocker_gates),
                "failure_count": len(report.get("failures", [])) if isinstance(report.get("failures"), list) else 0,
                "required_p0_service_count": summary.get("required_p0_service_count", 0),
                "deployed_service_count": summary.get("deployed_service_count", 0),
                "healthy_service_count": summary.get("healthy_service_count", 0),
                "failed_gates": blocker_gates,
            },
        }
    ]


def control_tower_summary(
    products: list[dict[str, Any]],
    capability_blockers: list[dict[str, Any]],
    catalog_lineage_ops_report: dict[str, Any],
    catalog_lineage_ops_blockers: list[dict[str, Any]],
    quality_slo_ops_report: dict[str, Any],
    quality_slo_ops_blockers: list[dict[str, Any]],
    semantic_metric_serving_ops_report: dict[str, Any],
    semantic_metric_serving_ops_blockers: list[dict[str, Any]],
    schema_registry_ops_report: dict[str, Any],
    schema_registry_ops_blockers: list[dict[str, Any]],
    catalog_runtime_ops_report: dict[str, Any],
    catalog_runtime_ops_blockers: list[dict[str, Any]],
    orchestration_runtime_ops_report: dict[str, Any],
    orchestration_runtime_ops_blockers: list[dict[str, Any]],
    data_plane_smoke_report: dict[str, Any],
    data_plane_smoke_blockers: list[dict[str, Any]],
    access_grant_ops_report: dict[str, Any],
    access_grant_ops_blockers: list[dict[str, Any]],
    source_activation_ops_report: dict[str, Any],
    source_activation_ops_blockers: list[dict[str, Any]],
    ingestion_runtime_report: dict[str, Any],
    ingestion_runtime_blockers: list[dict[str, Any]],
    bronze_lakehouse_ops_report: dict[str, Any],
    bronze_lakehouse_ops_blockers: list[dict[str, Any]],
    silver_gold_publication_ops_report: dict[str, Any],
    silver_gold_publication_ops_blockers: list[dict[str, Any]],
    contract_impact_reports: list[dict[str, Any]],
    contract_impact_blockers: list[dict[str, Any]],
    runtime_readiness_report: dict[str, Any],
    runtime_readiness_blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    data_product_blocker_count = sum(len(product.get("blockers", [])) for product in products)
    access_summary = access_grant_ops_report.get("summary") if isinstance(access_grant_ops_report.get("summary"), dict) else {}
    source_activation_summary = (
        source_activation_ops_report.get("summary")
        if isinstance(source_activation_ops_report.get("summary"), dict)
        else {}
    )
    source_activation_board = (
        source_activation_ops_report.get("decision_board")
        if isinstance(source_activation_ops_report.get("decision_board"), dict)
        else {}
    )
    contract_summary = contract_impact_summary(contract_impact_reports)
    return {
        "overall_state": "ready"
        if (
            data_product_blocker_count == 0
            and not capability_blockers
            and not catalog_lineage_ops_blockers
            and not quality_slo_ops_blockers
            and not semantic_metric_serving_ops_blockers
            and not schema_registry_ops_blockers
            and not catalog_runtime_ops_blockers
            and not orchestration_runtime_ops_blockers
            and not data_plane_smoke_blockers
            and not access_grant_ops_blockers
            and not source_activation_ops_blockers
            and not ingestion_runtime_blockers
            and not bronze_lakehouse_ops_blockers
            and not silver_gold_publication_ops_blockers
            and not contract_impact_blockers
            and not runtime_readiness_blockers
        )
        else "blocked",
        "data_product_count": len(products),
        "by_layer": count_by(products, "layer"),
        "by_status": count_by(products, "status"),
        "by_domain": count_by(products, "domain"),
        "by_product": count_by(products, "product"),
        "by_readiness_state": count_by(products, "readiness_state"),
        "blocker_count": (
            data_product_blocker_count
            + len(capability_blockers)
            + len(catalog_lineage_ops_blockers)
            + len(quality_slo_ops_blockers)
            + len(semantic_metric_serving_ops_blockers)
            + len(schema_registry_ops_blockers)
            + len(catalog_runtime_ops_blockers)
            + len(orchestration_runtime_ops_blockers)
            + len(data_plane_smoke_blockers)
            + len(access_grant_ops_blockers)
            + len(source_activation_ops_blockers)
            + len(ingestion_runtime_blockers)
            + len(bronze_lakehouse_ops_blockers)
            + len(silver_gold_publication_ops_blockers)
            + len(contract_impact_blockers)
            + len(runtime_readiness_blockers)
        ),
        "data_product_blocker_count": data_product_blocker_count,
        "capability_blocker_count": len(capability_blockers),
        "catalog_lineage_ops_blocker_count": len(catalog_lineage_ops_blockers),
        "quality_slo_ops_blocker_count": len(quality_slo_ops_blockers),
        "semantic_metric_serving_ops_blocker_count": len(semantic_metric_serving_ops_blockers),
        "schema_registry_ops_blocker_count": len(schema_registry_ops_blockers),
        "catalog_runtime_ops_blocker_count": len(catalog_runtime_ops_blockers),
        "orchestration_runtime_ops_blocker_count": len(orchestration_runtime_ops_blockers),
        "data_plane_smoke_blocker_count": len(data_plane_smoke_blockers),
        "access_grant_ops_blocker_count": len(access_grant_ops_blockers),
        "source_activation_ops_blocker_count": len(source_activation_ops_blockers),
        "ingestion_runtime_blocker_count": len(ingestion_runtime_blockers),
        "bronze_lakehouse_ops_blocker_count": len(bronze_lakehouse_ops_blockers),
        "silver_gold_publication_ops_blocker_count": len(silver_gold_publication_ops_blockers),
        "contract_impact_blocker_count": len(contract_impact_blockers),
        "runtime_readiness_blocker_count": len(runtime_readiness_blockers),
        "catalog_lineage_ops": catalog_lineage_ops_summary(catalog_lineage_ops_report),
        "quality_slo_ops": quality_slo_ops_summary(quality_slo_ops_report),
        "semantic_metric_serving_ops": semantic_metric_serving_ops_summary(semantic_metric_serving_ops_report),
        "schema_registry_ops": schema_registry_ops_summary(schema_registry_ops_report),
        "catalog_runtime_ops": catalog_runtime_ops_summary(catalog_runtime_ops_report),
        "orchestration_runtime_ops": orchestration_runtime_ops_summary(orchestration_runtime_ops_report),
        "data_plane_smoke": data_plane_smoke_summary(data_plane_smoke_report),
        "access_grant_ops": {
            "passed": access_grant_ops_report.get("passed"),
            "grant_count": access_summary.get("grant_count", 0),
            "active_grant_count": access_summary.get("active_grant_count", 0),
            "p0_issue_count": access_summary.get("p0_issue_count", 0),
            "p1_issue_count": access_summary.get("p1_issue_count", 0),
            "p2_issue_count": access_summary.get("p2_issue_count", 0),
            "review_overdue_count": access_summary.get("review_overdue_count", 0),
            "expiring_grant_count": len((access_grant_ops_report.get("decision_board") or {}).get("expiring_grants", []))
            if isinstance(access_grant_ops_report.get("decision_board"), dict)
            else 0,
        },
        "source_activation_ops": {
            "environment": source_activation_ops_report.get("environment"),
            "passed": source_activation_ops_report.get("passed"),
            "source_count": source_activation_summary.get("source_count", 0),
            "p0_source_count": source_activation_summary.get("p0_source_count", 0),
            "active_count": source_activation_summary.get("active_count", 0),
            "p0_active_count": source_activation_summary.get("p0_active_count", 0),
            "revoked_count": source_activation_summary.get("revoked_count", 0),
            "unactivated_count": source_activation_summary.get("unactivated_count", 0),
            "p0_unactivated_count": source_activation_summary.get("p0_unactivated_count", 0),
            "expired_count": source_activation_summary.get("expired_count", 0),
            "expiring_soon_count": source_activation_summary.get("expiring_soon_count", 0),
            "critical_issue_count": source_activation_summary.get("critical_issue_count", 0),
            "p0_critical_issue_count": source_activation_summary.get("p0_critical_issue_count", 0),
            "p0_activation_gap_count": source_activation_summary.get("p0_activation_gap_count", 0),
            "runtime_readiness_issue_count": source_activation_summary.get("runtime_readiness_issue_count", 0),
            "evidence_integrity_issue_count": source_activation_summary.get("evidence_integrity_issue_count", 0),
            "p0_evidence_integrity_issue_count": source_activation_summary.get("p0_evidence_integrity_issue_count", 0),
            "pointer_issue_count": source_activation_summary.get("pointer_issue_count", 0),
            "registry_drift_count": source_activation_summary.get("registry_drift_count", 0),
            "p0_next_action_count": len(
                [
                    action
                    for action in source_activation_board.get("next_actions", [])
                    if isinstance(action, dict) and action.get("priority") == P0
                ]
            )
            if isinstance(source_activation_board.get("next_actions"), list)
            else 0,
        },
        "ingestion_runtime": ingestion_runtime_summary(ingestion_runtime_report),
        "bronze_lakehouse_ops": bronze_lakehouse_ops_summary(bronze_lakehouse_ops_report),
        "silver_gold_publication_ops": silver_gold_publication_ops_summary(silver_gold_publication_ops_report),
        "contract_impact": contract_summary,
        "runtime_readiness": runtime_readiness_summary(runtime_readiness_report),
        "gold_release_coverage": gold_release_coverage(products),
    }


def ingestion_runtime_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "source_count": summary.get("source_count", 0),
        "p0_source_count": summary.get("p0_source_count", 0),
        "p0_failed_source_count": summary.get("p0_failed_source_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "running_connector_count": summary.get("running_connector_count", 0),
    }


def bronze_lakehouse_ops_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "source_count": summary.get("source_count", 0),
        "p0_source_count": summary.get("p0_source_count", 0),
        "ledger_attached_count": summary.get("ledger_attached_count", 0),
        "maintenance_attached_count": summary.get("maintenance_attached_count", 0),
        "p0_failed_table_count": summary.get("p0_failed_table_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
    }


def silver_gold_publication_ops_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "data_product_count": summary.get("data_product_count", 0),
        "failed_product_count": summary.get("failed_product_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "release_attached_count": summary.get("release_attached_count", 0),
        "promotion_attached_count": summary.get("promotion_attached_count", 0),
        "activation_attached_count": summary.get("activation_attached_count", 0),
        "active_pointer_attached_count": summary.get("active_pointer_attached_count", 0),
    }


def catalog_lineage_ops_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "catalog_hash": summary.get("catalog_hash"),
        "catalog_publish_status": summary.get("catalog_publish_status"),
        "catalog_publish_manifest_attached": summary.get("catalog_publish_manifest_attached"),
        "openlineage_attached": summary.get("openlineage_attached"),
        "openlineage_event_count": summary.get("openlineage_event_count", 0),
        "publish_receipt_attached": summary.get("publish_receipt_attached"),
        "failed_product_count": summary.get("failed_product_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "owner_steward_gap_count": summary.get("owner_steward_gap_count", 0),
        "static_lineage_gap_count": summary.get("static_lineage_gap_count", 0),
        "runtime_lineage_gap_count": summary.get("runtime_lineage_gap_count", 0),
    }


def quality_slo_ops_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "release_evidence_count": summary.get("release_evidence_count", 0),
        "failed_product_count": summary.get("failed_product_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "release_failed_count": summary.get("release_failed_count", 0),
        "release_quality_failed_count": summary.get("release_quality_failed_count", 0),
        "release_freshness_failed_count": summary.get("release_freshness_failed_count", 0),
        "runtime_quality_attached": summary.get("runtime_quality_attached"),
        "runtime_quality_failed_count": summary.get("runtime_quality_failed_count", 0),
        "runtime_freshness_breach_count": summary.get("runtime_freshness_breach_count", 0),
        "quality_profile_gap_count": summary.get("quality_profile_gap_count", 0),
        "alert_evidence_attached": summary.get("alert_evidence_attached"),
        "incident_report_attached": summary.get("incident_report_attached"),
    }


def semantic_metric_serving_ops_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "metric_count": summary.get("metric_count", 0),
        "failed_metric_count": summary.get("failed_metric_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "certified_metric_count": summary.get("certified_metric_count", 0),
        "provisional_metric_count": summary.get("provisional_metric_count", 0),
        "semantic_view_count": summary.get("semantic_view_count", 0),
        "deployment_evidence_attached": summary.get("deployment_evidence_attached"),
        "usage_evidence_attached": summary.get("usage_evidence_attached"),
        "serving_deployment_failed_count": summary.get("serving_deployment_failed_count", 0),
        "usage_tracking_gap_count": summary.get("usage_tracking_gap_count", 0),
    }


def schema_registry_ops_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "registry_uri": report.get("registry_uri"),
        "subject_count": summary.get("subject_count", 0),
        "failed_subject_count": summary.get("failed_subject_count", 0),
        "p0_subject_count": summary.get("p0_subject_count", 0),
        "p0_failed_subject_count": summary.get("p0_failed_subject_count", 0),
        "global_failed_check_count": summary.get("global_failed_check_count", 0),
        "publication_evidence_attached": summary.get("publication_evidence_attached"),
        "producer_enforcement_gap_count": summary.get("producer_enforcement_gap_count", 0),
        "broker_validation_gap_count": summary.get("broker_validation_gap_count", 0),
    }


def catalog_runtime_ops_summary(report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return {
            "attached": False,
            "passed": None,
            "environment": None,
            "readiness_state": None,
            "failed_check_count": 0,
        }
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "attached": True,
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "release_id": report.get("release_id"),
        "change_ticket": report.get("change_ticket"),
        "catalog_provider": summary.get("catalog_provider"),
        "replica_count": summary.get("replica_count", 0),
        "availability_zones": summary.get("availability_zones", 0),
        "multi_az": summary.get("multi_az"),
        "failover_passed": summary.get("failover_passed"),
        "stale_commit_rejected": summary.get("stale_commit_rejected"),
        "backup_enabled": summary.get("backup_enabled"),
        "pitr_enabled": summary.get("pitr_enabled"),
        "restore_test_passed": summary.get("restore_test_passed"),
        "failed_check_count": summary.get("failed_check_count", 0),
    }


def orchestration_runtime_ops_summary(report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return {
            "attached": False,
            "passed": None,
            "environment": None,
            "readiness_state": None,
            "failed_check_count": 0,
        }
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "attached": True,
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "mode": report.get("mode"),
        "release_id": report.get("release_id"),
        "change_ticket": report.get("change_ticket"),
        "orchestrator_provider": summary.get("orchestrator_provider"),
        "replica_count": summary.get("replica_count", 0),
        "daemon_replica_count": summary.get("daemon_replica_count", 0),
        "scheduler_replica_count": summary.get("scheduler_replica_count", 0),
        "worker_replica_count": summary.get("worker_replica_count", 0),
        "availability_zones": summary.get("availability_zones", 0),
        "multi_az": summary.get("multi_az"),
        "distributed_executor_enabled": summary.get("distributed_executor_enabled"),
        "kubernetes_run_launcher_enabled": summary.get("kubernetes_run_launcher_enabled"),
        "managed_run_storage": summary.get("managed_run_storage"),
        "run_storage_ha_enabled": summary.get("run_storage_ha_enabled"),
        "schedule_tick_history_passed": summary.get("schedule_tick_history_passed"),
        "retry_policy_verified": summary.get("retry_policy_verified"),
        "backfill_materialization_history_passed": summary.get("backfill_materialization_history_passed"),
        "production_backfill_scheduler": summary.get("production_backfill_scheduler"),
        "service_identity_authorized": summary.get("service_identity_authorized"),
        "secret_injection_verified": summary.get("secret_injection_verified"),
        "metrics_exported": summary.get("metrics_exported"),
        "audit_event_count": summary.get("audit_event_count", 0),
        "audit_failed_event_count": summary.get("audit_failed_event_count", 0),
        "failed_check_count": summary.get("failed_check_count", 0),
    }


def data_plane_smoke_summary(report: dict[str, Any]) -> dict[str, Any]:
    if not report:
        return {
            "attached": False,
            "passed": None,
            "environment": None,
            "use_case_id": None,
            "primary_output": None,
            "runtime_mode": None,
            "failed_check_count": 0,
        }
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    query = report.get("query_smoke") if isinstance(report.get("query_smoke"), dict) else {}
    runtime_scope = report.get("runtime_scope") if isinstance(report.get("runtime_scope"), dict) else {}
    return {
        "attached": True,
        "environment": report.get("environment"),
        "passed": report.get("passed"),
        "release_id": report.get("release_id"),
        "use_case_id": report.get("use_case_id"),
        "runner_id": report.get("runner_id"),
        "primary_output": report.get("primary_output"),
        "runtime_mode": runtime_scope.get("mode"),
        "release_passed": summary.get("release_passed"),
        "all_layers_materialized": summary.get("all_layers_materialized"),
        "query_passed": summary.get("query_passed"),
        "failed_check_count": summary.get("failed_check_count", 0),
        "layer_count": summary.get("layer_count", 0),
        "query_name": query.get("query_name"),
        "query_result_row_count": query.get("result_row_count", 0),
        "not_covered": runtime_scope.get("not_covered", []),
    }


def runtime_readiness_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    return {
        "environment": report.get("environment"),
        "readiness_state": report.get("readiness_state"),
        "passed": report.get("passed"),
        "runtime_readiness": report.get("runtime_readiness"),
        "evidence_mode": report.get("evidence_mode"),
        "required_p0_service_count": summary.get("required_p0_service_count", 0),
        "deployed_service_count": summary.get("deployed_service_count", 0),
        "healthy_service_count": summary.get("healthy_service_count", 0),
        "failed_gate_count": summary.get("failed_gate_count", 0),
        "failure_count": len(report.get("failures", [])) if isinstance(report.get("failures"), list) else 0,
    }


def contract_impact_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    topics = []
    blocked_topics = []
    review_required_topics = []
    affected_data_products: set[str] = set()
    affected_use_cases: set[str] = set()
    affected_p0_use_cases: set[str] = set()
    for report in reports:
        if not isinstance(report, dict):
            continue
        topic = report.get("topic") if isinstance(report.get("topic"), dict) else {}
        impact = report.get("impact") if isinstance(report.get("impact"), dict) else {}
        topic_name = str(topic.get("name") or "unknown")
        topics.append(topic_name)
        if impact.get("release_decision") == "blocked" or report.get("passed") is False:
            blocked_topics.append(topic_name)
        if impact.get("release_decision") == "review_required":
            review_required_topics.append(topic_name)
        for product in report.get("affected_data_products", []) if isinstance(report.get("affected_data_products"), list) else []:
            if isinstance(product, dict) and product.get("name"):
                affected_data_products.add(str(product.get("name")))
        for use_case in report.get("affected_use_cases", []) if isinstance(report.get("affected_use_cases"), list) else []:
            if isinstance(use_case, dict) and use_case.get("id"):
                affected_use_cases.add(str(use_case.get("id")))
                if use_case.get("priority") == P0:
                    affected_p0_use_cases.add(str(use_case.get("id")))
    return {
        "report_count": len(reports),
        "topic_count": len(set(topics)),
        "blocked_count": len(blocked_topics),
        "review_required_count": len(review_required_topics),
        "blocked_topics": sorted(set(blocked_topics)),
        "review_required_topics": sorted(set(review_required_topics)),
        "affected_data_product_count": len(affected_data_products),
        "affected_use_case_count": len(affected_use_cases),
        "affected_p0_use_case_count": len(affected_p0_use_cases),
    }


def gold_release_coverage(products: list[dict[str, Any]]) -> dict[str, Any]:
    gold = [product for product in products if product.get("layer") == "GOLD"]
    covered = [product for product in gold if product.get("release_evidence", {}).get("covered") is True]
    passed = [product for product in gold if product.get("release_evidence", {}).get("passed") is True]
    return {
        "gold_count": len(gold),
        "covered_count": len(covered),
        "passed_count": len(passed),
        "missing": sorted(str(product.get("name")) for product in gold if product not in covered),
    }


def escalation_summary(
    product_blockers: list[dict[str, Any]],
    capability_blockers: list[dict[str, Any]],
    catalog_lineage_ops_blockers: list[dict[str, Any]],
    quality_slo_ops_blockers: list[dict[str, Any]],
    semantic_metric_serving_ops_blockers: list[dict[str, Any]],
    schema_registry_ops_blockers: list[dict[str, Any]],
    catalog_runtime_ops_blockers: list[dict[str, Any]],
    orchestration_runtime_ops_blockers: list[dict[str, Any]],
    data_plane_smoke_blockers: list[dict[str, Any]],
    access_grant_ops_blockers: list[dict[str, Any]],
    source_activation_ops_blockers: list[dict[str, Any]],
    ingestion_runtime_blockers: list[dict[str, Any]],
    bronze_lakehouse_ops_blockers: list[dict[str, Any]],
    silver_gold_publication_ops_blockers: list[dict[str, Any]],
    contract_impact_blockers: list[dict[str, Any]],
    runtime_readiness_blockers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for blocker in (
        product_blockers
        + capability_blockers
        + catalog_lineage_ops_blockers
        + quality_slo_ops_blockers
        + semantic_metric_serving_ops_blockers
        + schema_registry_ops_blockers
        + catalog_runtime_ops_blockers
        + orchestration_runtime_ops_blockers
        + data_plane_smoke_blockers
        + access_grant_ops_blockers
        + source_activation_ops_blockers
        + ingestion_runtime_blockers
        + bronze_lakehouse_ops_blockers
        + silver_gold_publication_ops_blockers
        + contract_impact_blockers
        + runtime_readiness_blockers
    ):
        key = (str(blocker.get("owner_team") or "unknown"), str(blocker.get("domain") or "unknown"))
        item = grouped.setdefault(
            key,
            {
                "owner_team": key[0],
                "domain": key[1],
                "p0_blocker_count": 0,
                "gates": {},
                "data_products": set(),
            },
        )
        if blocker.get("severity") == P0:
            item["p0_blocker_count"] += 1
        gate = str(blocker.get("gate") or "unknown")
        item["gates"][gate] = item["gates"].get(gate, 0) + 1
        data_product = blocker.get("data_product")
        if data_product:
            item["data_products"].add(data_product)
    return [
        {
            **item,
            "gates": dict(sorted(item["gates"].items())),
            "data_products": sorted(item["data_products"]),
        }
        for item in sorted(grouped.values(), key=lambda value: (-value["p0_blocker_count"], value["owner_team"], value["domain"]))
    ]


def validate_data_product_control_tower_report(report: dict[str, Any]) -> ValidationResult:
    result = ValidationResult(checked_count=1)
    if report.get("artifact_type") != "data_product_control_tower_report.v1":
        result.error(Path("control_tower_report"), "artifact_type must be data_product_control_tower_report.v1")
    if report.get("report_version") != REPORT_VERSION:
        result.error(Path("control_tower_report"), f"report_version must be {REPORT_VERSION}")
    if not isinstance(report.get("summary"), dict):
        result.error(Path("control_tower_report"), "summary must be an object")
    if not isinstance(report.get("scope"), dict):
        result.error(Path("control_tower_report"), "scope must be an object")
    if not isinstance(report.get("inputs"), dict):
        result.error(Path("control_tower_report"), "inputs must be an object")
    if not isinstance(report.get("gate_matrix"), list):
        result.error(Path("control_tower_report"), "gate_matrix must be a list")
    if not isinstance(report.get("data_products"), list):
        result.error(Path("control_tower_report"), "data_products must be a list")
    if not isinstance(report.get("blockers"), list):
        result.error(Path("control_tower_report"), "blockers must be a list")
    if report.get("p0_ready") is True and report.get("blockers"):
        result.error(Path("control_tower_report"), "p0_ready cannot be true while blockers are present")
    return result


def blocker_entry(data_product_name: str, data_product: dict[str, Any], check_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "scope": "data_product",
        "data_product": data_product_name,
        "capability_id": None,
        "gate": check_item["name"],
        "severity": check_item["severity"],
        "owner_team": data_product.get("owner_team"),
        "domain": data_product.get("domain"),
        "message": f"{data_product_name} failed {check_item['name']}",
        "details": check_item.get("details", {}),
    }


def check(name: str, passed: bool, severity: str, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "severity": severity,
        "details": details,
    }


def compact_evaluation(evaluation: dict[str, Any]) -> dict[str, Any]:
    checks = evaluation.get("checks")
    return {
        "passed": evaluation.get("passed"),
        "failed_checks": [
            item.get("name")
            for item in checks
            if isinstance(item, dict) and item.get("passed") is not True
        ] if isinstance(checks, list) else [],
        "error": evaluation.get("error"),
    }


def control_tower_scope(catalog_bundle: dict[str, Any]) -> dict[str, Any]:
    products = sorted(
        str(product.get("code"))
        for product in catalog_bundle.get("products", [])
        if isinstance(product, dict) and product.get("code")
    )
    domains = sorted(
        str(domain.get("code"))
        for domain in catalog_bundle.get("domains", [])
        if isinstance(domain, dict) and domain.get("code")
    )
    use_cases = sorted(
        str(use_case.get("id"))
        for use_case in catalog_bundle.get("use_cases", [])
        if isinstance(use_case, dict) and use_case.get("id")
    )
    return {
        "products": products,
        "domains": domains,
        "use_cases": use_cases,
    }


def gate_matrix(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for product in products:
        for check_item in product.get("checks", []):
            if not isinstance(check_item, dict):
                continue
            rows.append(
                {
                    "data_product": product.get("name"),
                    "product": product.get("product"),
                    "domain": product.get("domain"),
                    "layer": product.get("layer"),
                    "gate": check_item.get("name"),
                    "severity": check_item.get("severity"),
                    "passed": check_item.get("passed"),
                }
            )
    return rows


def evaluate_safely(callback, *, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        value = callback()
    except (KeyError, ValueError):
        return fallback
    return value if isinstance(value, dict) else fallback


def empty_lineage_coverage(name: str) -> dict[str, Any]:
    return {
        "lineage_required": True,
        "catalog": None,
        "static_lineage_present": False,
        "runtime_lineage_present": False,
        "static_edge_count": 0,
        "runtime_edge_count": 0,
        "runtime_run_count": 0,
        "upstream": [],
        "name": name,
    }


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": profile.get("id"),
        "owner": profile.get("owner"),
        "severity": profile.get("severity"),
    }


def count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def sha256_value_valid(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value.removeprefix("sha256:"))
    )


def content_hash(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
