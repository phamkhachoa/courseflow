from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from enterprise_dp.attestations import verify_attestation_file
from enterprise_dp.capabilities import write_capability_maturity_report
from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.catalog_runtime_ops import (
    catalog_runtime_ops_closes_gap,
    strict_catalog_runtime_ops_release_gate_passed,
)
from enterprise_dp.control_tower import write_data_product_control_tower_report
from enterprise_dp.data_plane_smoke import DEFAULT_RELEASE_ID, DEFAULT_USE_CASE_ID, write_data_plane_smoke_report
from enterprise_dp.orchestration_runtime_ops import (
    orchestration_runtime_ops_closes_gap,
    strict_orchestration_runtime_ops_release_gate_passed,
)
from enterprise_dp.runtime import write_runtime_readiness_report


REPORT_VERSION = 1
DEFAULT_REVIEW_GENERATED_AT = "2026-06-16T12:05:00Z"
DEFAULT_SMOKE_GENERATED_AT = "2026-01-15T09:15:20Z"
DEFAULT_SMOKE_INGESTED_AT = "2026-01-15T09:15:05Z"
DEFAULT_SMOKE_BUILT_AT = "2026-01-15T09:15:10Z"
DEFAULT_SMOKE_EVALUATION_TIME = "2026-01-15T09:15:15Z"
DEFAULT_FINANCE_SCHEMA_ID = "registry:finance.benefit_settled.v1:1"
DEFAULT_FINANCE_SNAPSHOT_ID = "finance-benefit-local-data-plane-smoke"


@dataclass(frozen=True)
class ProductionReviewPackResult:
    output_dir: Path
    manifest_path: Path
    manifest: dict[str, Any]


def write_production_review_pack(
    root: str | Path,
    output_dir: str | Path,
    *,
    environment: str = "local",
    generated_at: str | None = None,
    use_case_id: str = DEFAULT_USE_CASE_ID,
    release_id: str = DEFAULT_RELEASE_ID,
    smoke_generated_at: str | None = None,
    ingested_at: str | None = None,
    built_at: str | None = None,
    evaluation_time: str | None = None,
    schema_id: str | None = None,
    snapshot_id: str | None = None,
    event_backbone_smoke_report_path: str | Path | None = None,
    ingestion_runtime_report_path: str | Path | None = None,
    catalog_lineage_ops_report_path: str | Path | None = None,
    semantic_metric_serving_ops_report_path: str | Path | None = None,
    source_activation_ops_report_path: str | Path | None = None,
    backfill_readiness_report_path: str | Path | None = None,
    runtime_readiness_report_path: str | Path | None = None,
    runtime_iac_plan_path: str | Path | None = None,
    runtime_iac_apply_path: str | Path | None = None,
    runtime_drift_report_path: str | Path | None = None,
    runtime_backup_report_path: str | Path | None = None,
    runtime_dr_report_path: str | Path | None = None,
    runtime_health_report_path: str | Path | None = None,
    schema_registry_runtime_smoke_report_path: str | Path | None = None,
    schema_registry_attestation_report_path: str | Path | None = None,
    schema_registry_ops_report_path: str | Path | None = None,
    schema_registry_auth_smoke_report_path: str | Path | None = None,
    schema_registry_storage_smoke_report_path: str | Path | None = None,
    broker_acl_smoke_report_path: str | Path | None = None,
    transactional_outbox_smoke_report_path: str | Path | None = None,
    live_bronze_ingestion_smoke_report_path: str | Path | None = None,
    orchestrated_publication_smoke_report_path: str | Path | None = None,
    live_quality_slo_smoke_report_path: str | Path | None = None,
    live_lakehouse_smoke_report_path: str | Path | None = None,
    iceberg_catalog_smoke_report_path: str | Path | None = None,
    object_store_smoke_report_path: str | Path | None = None,
    trino_sql_smoke_report_path: str | Path | None = None,
    trino_iceberg_minio_smoke_report_path: str | Path | None = None,
    catalog_cross_engine_smoke_report_path: str | Path | None = None,
    catalog_runtime_ops_report_path: str | Path | None = None,
    orchestration_runtime_ops_report_path: str | Path | None = None,
    trino_runtime_security_smoke_report_path: str | Path | None = None,
    policy_decision_smoke_report_path: str | Path | None = None,
    oidc_auth_smoke_report_path: str | Path | None = None,
    secret_rotation_smoke_report_path: str | Path | None = None,
    secret_rotation_ops_report_path: str | Path | None = None,
    dagster_orchestration_smoke_report_path: str | Path | None = None,
    dagster_day2_smoke_report_path: str | Path | None = None,
    portfolio_release_smoke_report_path: str | Path | None = None,
    workload_benchmark_report_path: str | Path | None = None,
) -> ProductionReviewPackResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    run_dir = target_dir / "run"
    evidence_dir = target_dir / "evidence"
    manifest_path = target_dir / "production-review-pack.json"
    review_time = generated_at or DEFAULT_REVIEW_GENERATED_AT
    smoke_time = smoke_generated_at or DEFAULT_SMOKE_GENERATED_AT

    smoke_result = write_data_plane_smoke_report(
        platform_root,
        evidence_dir / "data-plane-smoke-report.json",
        output_dir=run_dir / "data-plane-smoke",
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=smoke_time,
        ingested_at=ingested_at or DEFAULT_SMOKE_INGESTED_AT,
        built_at=built_at or DEFAULT_SMOKE_BUILT_AT,
        evaluation_time=evaluation_time or DEFAULT_SMOKE_EVALUATION_TIME,
        schema_id=schema_id or DEFAULT_FINANCE_SCHEMA_ID,
        snapshot_id=snapshot_id or DEFAULT_FINANCE_SNAPSHOT_ID,
    )
    generated_runtime_result = write_runtime_readiness_report(
        platform_root,
        evidence_dir / "runtime-readiness.json",
        environment=environment,
        iac_plan_path=runtime_iac_plan_path,
        iac_apply_path=runtime_iac_apply_path,
        drift_report_path=runtime_drift_report_path,
        backup_report_path=runtime_backup_report_path,
        dr_report_path=runtime_dr_report_path,
        health_report_path=runtime_health_report_path,
        generated_at=review_time,
    )
    capability_result = write_capability_maturity_report(
        platform_root,
        evidence_dir / "capability-maturity-p0.json",
        phase="P0",
        generated_at=review_time,
    )
    portfolio_report, portfolio_path = resolve_optional_artifact(portfolio_release_smoke_report_path)
    ingestion_runtime_report, ingestion_runtime_path = resolve_optional_artifact(ingestion_runtime_report_path)
    runtime_report, runtime_path = resolve_optional_artifact(runtime_readiness_report_path)
    runtime_external_attached = runtime_report is not None or any(
        path is not None
        for path in (
            runtime_iac_plan_path,
            runtime_iac_apply_path,
            runtime_drift_report_path,
            runtime_backup_report_path,
            runtime_dr_report_path,
            runtime_health_report_path,
        )
    )
    if runtime_report is None or runtime_path is None:
        runtime_report = generated_runtime_result.report
        runtime_path = generated_runtime_result.output_path
    portfolio_inputs = portfolio_control_tower_inputs(portfolio_report)
    catalog_lineage_ops_input_path = (
        catalog_lineage_ops_report_path or portfolio_inputs.get("catalog_lineage_ops_report_path")
    )
    catalog_lineage_ops_report, catalog_lineage_ops_path = resolve_optional_artifact(catalog_lineage_ops_input_path)
    semantic_metric_serving_ops_input_path = (
        semantic_metric_serving_ops_report_path
        or portfolio_inputs.get("semantic_metric_serving_ops_report_path")
    )
    semantic_metric_serving_ops_report, semantic_metric_serving_ops_path = resolve_optional_artifact(
        semantic_metric_serving_ops_input_path
    )
    source_activation_ops_input_path = (
        source_activation_ops_report_path or portfolio_inputs.get("source_activation_ops_report_path")
    )
    source_activation_ops_report, source_activation_ops_path = resolve_optional_artifact(source_activation_ops_input_path)
    backfill_readiness_report, backfill_readiness_path = resolve_optional_artifact(backfill_readiness_report_path)
    catalog_runtime_ops_report, catalog_runtime_ops_path = resolve_optional_artifact(catalog_runtime_ops_report_path)
    orchestration_runtime_ops_report, orchestration_runtime_ops_path = resolve_optional_artifact(
        orchestration_runtime_ops_report_path
    )
    control_tower_result = write_data_product_control_tower_report(
        platform_root,
        evidence_dir / "control-tower-with-smoke.json",
        catalog_bundle_path=portfolio_inputs.get("catalog_bundle_path"),
        catalog_lineage_ops_report_path=catalog_lineage_ops_path,
        quality_slo_ops_report_path=portfolio_inputs.get("quality_slo_ops_report_path"),
        semantic_metric_serving_ops_report_path=semantic_metric_serving_ops_path,
        source_activation_ops_report_path=source_activation_ops_path,
        catalog_runtime_ops_report_path=catalog_runtime_ops_path,
        orchestration_runtime_ops_report_path=orchestration_runtime_ops_path,
        release_evidence_paths=portfolio_inputs.get("release_evidence_paths"),
        data_plane_smoke_report_path=smoke_result.output_path,
        ingestion_runtime_report_path=ingestion_runtime_path,
        runtime_readiness_report_path=runtime_path,
        capability_maturity_report_path=capability_result.output_path,
        environment=environment,
        generated_at=review_time,
    )
    event_backbone_report, event_backbone_path = resolve_optional_artifact(event_backbone_smoke_report_path)
    schema_registry_runtime_report, schema_registry_runtime_path = resolve_optional_artifact(
        schema_registry_runtime_smoke_report_path
    )
    schema_registry_attestation_report, schema_registry_attestation_path = resolve_optional_artifact(
        schema_registry_attestation_report_path
    )
    schema_registry_ops_report, schema_registry_ops_path = resolve_optional_artifact(schema_registry_ops_report_path)
    schema_registry_auth_report, schema_registry_auth_path = resolve_optional_artifact(schema_registry_auth_smoke_report_path)
    schema_registry_storage_report, schema_registry_storage_path = resolve_optional_artifact(
        schema_registry_storage_smoke_report_path
    )
    broker_acl_report, broker_acl_path = resolve_optional_artifact(broker_acl_smoke_report_path)
    transactional_outbox_report, transactional_outbox_path = resolve_optional_artifact(transactional_outbox_smoke_report_path)
    live_bronze_ingestion_report, live_bronze_ingestion_path = resolve_optional_artifact(
        live_bronze_ingestion_smoke_report_path
    )
    orchestrated_publication_report, orchestrated_publication_path = resolve_optional_artifact(
        orchestrated_publication_smoke_report_path
    )
    live_quality_slo_report, live_quality_slo_path = resolve_optional_artifact(live_quality_slo_smoke_report_path)
    live_lakehouse_report, live_lakehouse_path = resolve_optional_artifact(live_lakehouse_smoke_report_path)
    iceberg_catalog_report, iceberg_catalog_path = resolve_optional_artifact(iceberg_catalog_smoke_report_path)
    object_store_report, object_store_path = resolve_optional_artifact(object_store_smoke_report_path)
    trino_sql_report, trino_sql_path = resolve_optional_artifact(trino_sql_smoke_report_path)
    trino_iceberg_minio_report, trino_iceberg_minio_path = resolve_optional_artifact(trino_iceberg_minio_smoke_report_path)
    catalog_cross_engine_report, catalog_cross_engine_path = resolve_optional_artifact(
        catalog_cross_engine_smoke_report_path
    )
    trino_runtime_security_report, trino_runtime_security_path = resolve_optional_artifact(
        trino_runtime_security_smoke_report_path
    )
    policy_decision_report, policy_decision_path = resolve_optional_artifact(policy_decision_smoke_report_path)
    oidc_auth_report, oidc_auth_path = resolve_optional_artifact(oidc_auth_smoke_report_path)
    secret_rotation_report, secret_rotation_path = resolve_optional_artifact(secret_rotation_smoke_report_path)
    secret_rotation_ops_report, secret_rotation_ops_path = resolve_optional_artifact(secret_rotation_ops_report_path)
    dagster_orchestration_report, dagster_orchestration_path = resolve_optional_artifact(dagster_orchestration_smoke_report_path)
    dagster_day2_report, dagster_day2_path = resolve_optional_artifact(dagster_day2_smoke_report_path)
    workload_benchmark_report, workload_benchmark_path = resolve_optional_artifact(workload_benchmark_report_path)

    manifest = build_production_review_pack_manifest(
        platform_root=platform_root,
        output_dir=target_dir,
        generated_at=review_time,
        environment=environment,
        smoke_report=smoke_result.report,
        smoke_path=smoke_result.output_path,
        runtime_report=runtime_report,
        runtime_path=runtime_path,
        runtime_external_attached=runtime_external_attached,
        capability_report=capability_result.report,
        capability_path=capability_result.output_path,
        control_tower_report=control_tower_result.report,
        control_tower_path=control_tower_result.output_path,
        event_backbone_report=event_backbone_report,
        event_backbone_path=event_backbone_path,
        ingestion_runtime_report=ingestion_runtime_report,
        ingestion_runtime_path=ingestion_runtime_path,
        catalog_lineage_ops_report=catalog_lineage_ops_report,
        catalog_lineage_ops_path=catalog_lineage_ops_path,
        semantic_metric_serving_ops_report=semantic_metric_serving_ops_report,
        semantic_metric_serving_ops_path=semantic_metric_serving_ops_path,
        source_activation_ops_report=source_activation_ops_report,
        source_activation_ops_path=source_activation_ops_path,
        backfill_readiness_report=backfill_readiness_report,
        backfill_readiness_path=backfill_readiness_path,
        schema_registry_runtime_report=schema_registry_runtime_report,
        schema_registry_runtime_path=schema_registry_runtime_path,
        schema_registry_attestation_report=schema_registry_attestation_report,
        schema_registry_attestation_path=schema_registry_attestation_path,
        schema_registry_ops_report=schema_registry_ops_report,
        schema_registry_ops_path=schema_registry_ops_path,
        schema_registry_auth_report=schema_registry_auth_report,
        schema_registry_auth_path=schema_registry_auth_path,
        schema_registry_storage_report=schema_registry_storage_report,
        schema_registry_storage_path=schema_registry_storage_path,
        broker_acl_report=broker_acl_report,
        broker_acl_path=broker_acl_path,
        transactional_outbox_report=transactional_outbox_report,
        transactional_outbox_path=transactional_outbox_path,
        live_bronze_ingestion_report=live_bronze_ingestion_report,
        live_bronze_ingestion_path=live_bronze_ingestion_path,
        orchestrated_publication_report=orchestrated_publication_report,
        orchestrated_publication_path=orchestrated_publication_path,
        live_quality_slo_report=live_quality_slo_report,
        live_quality_slo_path=live_quality_slo_path,
        live_lakehouse_report=live_lakehouse_report,
        live_lakehouse_path=live_lakehouse_path,
        iceberg_catalog_report=iceberg_catalog_report,
        iceberg_catalog_path=iceberg_catalog_path,
        object_store_report=object_store_report,
        object_store_path=object_store_path,
        trino_sql_report=trino_sql_report,
        trino_sql_path=trino_sql_path,
        trino_iceberg_minio_report=trino_iceberg_minio_report,
        trino_iceberg_minio_path=trino_iceberg_minio_path,
        catalog_cross_engine_report=catalog_cross_engine_report,
        catalog_cross_engine_path=catalog_cross_engine_path,
        catalog_runtime_ops_report=catalog_runtime_ops_report,
        catalog_runtime_ops_path=catalog_runtime_ops_path,
        orchestration_runtime_ops_report=orchestration_runtime_ops_report,
        orchestration_runtime_ops_path=orchestration_runtime_ops_path,
        trino_runtime_security_report=trino_runtime_security_report,
        trino_runtime_security_path=trino_runtime_security_path,
        policy_decision_report=policy_decision_report,
        policy_decision_path=policy_decision_path,
        oidc_auth_report=oidc_auth_report,
        oidc_auth_path=oidc_auth_path,
        secret_rotation_report=secret_rotation_report,
        secret_rotation_path=secret_rotation_path,
        secret_rotation_ops_report=secret_rotation_ops_report,
        secret_rotation_ops_path=secret_rotation_ops_path,
        dagster_orchestration_report=dagster_orchestration_report,
        dagster_orchestration_path=dagster_orchestration_path,
        dagster_day2_report=dagster_day2_report,
        dagster_day2_path=dagster_day2_path,
        portfolio_report=portfolio_report,
        portfolio_path=portfolio_path,
        workload_benchmark_report=workload_benchmark_report,
        workload_benchmark_path=workload_benchmark_path,
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return ProductionReviewPackResult(output_dir=target_dir, manifest_path=manifest_path, manifest=manifest)


def build_production_review_pack_manifest(
    *,
    platform_root: Path,
    output_dir: Path,
    generated_at: str,
    environment: str,
    smoke_report: dict[str, Any],
    smoke_path: Path,
    runtime_report: dict[str, Any],
    runtime_path: Path,
    runtime_external_attached: bool,
    capability_report: dict[str, Any],
    capability_path: Path,
    control_tower_report: dict[str, Any],
    control_tower_path: Path,
    event_backbone_report: dict[str, Any] | None = None,
    event_backbone_path: Path | None = None,
    ingestion_runtime_report: dict[str, Any] | None = None,
    ingestion_runtime_path: Path | None = None,
    catalog_lineage_ops_report: dict[str, Any] | None = None,
    catalog_lineage_ops_path: Path | None = None,
    semantic_metric_serving_ops_report: dict[str, Any] | None = None,
    semantic_metric_serving_ops_path: Path | None = None,
    source_activation_ops_report: dict[str, Any] | None = None,
    source_activation_ops_path: Path | None = None,
    backfill_readiness_report: dict[str, Any] | None = None,
    backfill_readiness_path: Path | None = None,
    schema_registry_runtime_report: dict[str, Any] | None = None,
    schema_registry_runtime_path: Path | None = None,
    schema_registry_attestation_report: dict[str, Any] | None = None,
    schema_registry_attestation_path: Path | None = None,
    schema_registry_ops_report: dict[str, Any] | None = None,
    schema_registry_ops_path: Path | None = None,
    schema_registry_auth_report: dict[str, Any] | None = None,
    schema_registry_auth_path: Path | None = None,
    schema_registry_storage_report: dict[str, Any] | None = None,
    schema_registry_storage_path: Path | None = None,
    broker_acl_report: dict[str, Any] | None = None,
    broker_acl_path: Path | None = None,
    transactional_outbox_report: dict[str, Any] | None = None,
    transactional_outbox_path: Path | None = None,
    live_bronze_ingestion_report: dict[str, Any] | None = None,
    live_bronze_ingestion_path: Path | None = None,
    orchestrated_publication_report: dict[str, Any] | None = None,
    orchestrated_publication_path: Path | None = None,
    live_quality_slo_report: dict[str, Any] | None = None,
    live_quality_slo_path: Path | None = None,
    live_lakehouse_report: dict[str, Any] | None = None,
    live_lakehouse_path: Path | None = None,
    iceberg_catalog_report: dict[str, Any] | None = None,
    iceberg_catalog_path: Path | None = None,
    object_store_report: dict[str, Any] | None = None,
    object_store_path: Path | None = None,
    trino_sql_report: dict[str, Any] | None = None,
    trino_sql_path: Path | None = None,
    trino_iceberg_minio_report: dict[str, Any] | None = None,
    trino_iceberg_minio_path: Path | None = None,
    catalog_cross_engine_report: dict[str, Any] | None = None,
    catalog_cross_engine_path: Path | None = None,
    catalog_runtime_ops_report: dict[str, Any] | None = None,
    catalog_runtime_ops_path: Path | None = None,
    orchestration_runtime_ops_report: dict[str, Any] | None = None,
    orchestration_runtime_ops_path: Path | None = None,
    trino_runtime_security_report: dict[str, Any] | None = None,
    trino_runtime_security_path: Path | None = None,
    policy_decision_report: dict[str, Any] | None = None,
    policy_decision_path: Path | None = None,
    oidc_auth_report: dict[str, Any] | None = None,
    oidc_auth_path: Path | None = None,
    secret_rotation_report: dict[str, Any] | None = None,
    secret_rotation_path: Path | None = None,
    secret_rotation_ops_report: dict[str, Any] | None = None,
    secret_rotation_ops_path: Path | None = None,
    dagster_orchestration_report: dict[str, Any] | None = None,
    dagster_orchestration_path: Path | None = None,
    dagster_day2_report: dict[str, Any] | None = None,
    dagster_day2_path: Path | None = None,
    portfolio_report: dict[str, Any] | None = None,
    portfolio_path: Path | None = None,
    workload_benchmark_report: dict[str, Any] | None = None,
    workload_benchmark_path: Path | None = None,
) -> dict[str, Any]:
    control_summary = control_tower_report.get("summary") if isinstance(control_tower_report.get("summary"), dict) else {}
    smoke_summary = smoke_report.get("summary") if isinstance(smoke_report.get("summary"), dict) else {}
    smoke_scope = smoke_report.get("runtime_scope") if isinstance(smoke_report.get("runtime_scope"), dict) else {}
    runtime_summary = runtime_report.get("summary") if isinstance(runtime_report.get("summary"), dict) else {}
    runtime_inputs = runtime_report.get("inputs") if isinstance(runtime_report.get("inputs"), dict) else {}
    capability_summary = capability_report.get("summary") if isinstance(capability_report.get("summary"), dict) else {}
    event_summary = (
        event_backbone_report.get("summary")
        if isinstance(event_backbone_report, dict) and isinstance(event_backbone_report.get("summary"), dict)
        else {}
    )
    event_scope = (
        event_backbone_report.get("runtime_scope")
        if isinstance(event_backbone_report, dict) and isinstance(event_backbone_report.get("runtime_scope"), dict)
        else {}
    )
    ingestion_runtime_summary = (
        ingestion_runtime_report.get("summary")
        if isinstance(ingestion_runtime_report, dict) and isinstance(ingestion_runtime_report.get("summary"), dict)
        else {}
    )
    ingestion_runtime_evidence = (
        ingestion_runtime_report.get("evidence")
        if isinstance(ingestion_runtime_report, dict) and isinstance(ingestion_runtime_report.get("evidence"), dict)
        else {}
    )
    catalog_lineage_ops_summary = (
        catalog_lineage_ops_report.get("summary")
        if isinstance(catalog_lineage_ops_report, dict)
        and isinstance(catalog_lineage_ops_report.get("summary"), dict)
        else {}
    )
    catalog_lineage_release_gate_passed = strict_catalog_lineage_release_gate_passed(
        catalog_lineage_ops_report,
        target_environment=environment,
    )
    semantic_metric_serving_ops_summary = (
        semantic_metric_serving_ops_report.get("summary")
        if isinstance(semantic_metric_serving_ops_report, dict)
        and isinstance(semantic_metric_serving_ops_report.get("summary"), dict)
        else {}
    )
    semantic_metric_serving_release_gate_passed = strict_semantic_metric_serving_release_gate_passed(
        semantic_metric_serving_ops_report,
        target_environment=environment,
    )
    source_activation_ops_summary = (
        source_activation_ops_report.get("summary")
        if isinstance(source_activation_ops_report, dict)
        and isinstance(source_activation_ops_report.get("summary"), dict)
        else {}
    )
    source_onboarding_release_gate_passed = strict_source_onboarding_release_gate_passed(
        source_activation_ops_report,
        target_environment=environment,
    )
    backfill_readiness_summary = (
        backfill_readiness_report.get("summary")
        if isinstance(backfill_readiness_report, dict)
        and isinstance(backfill_readiness_report.get("summary"), dict)
        else {}
    )
    backfill_change_governance_release_gate_passed = strict_backfill_readiness_release_gate_passed(
        backfill_readiness_report,
        target_environment=environment,
    )
    schema_registry_runtime_summary = (
        schema_registry_runtime_report.get("summary")
        if isinstance(schema_registry_runtime_report, dict)
        and isinstance(schema_registry_runtime_report.get("summary"), dict)
        else {}
    )
    schema_registry_runtime_scope = (
        schema_registry_runtime_report.get("runtime_scope")
        if isinstance(schema_registry_runtime_report, dict)
        and isinstance(schema_registry_runtime_report.get("runtime_scope"), dict)
        else {}
    )
    schema_registry_attestation_verification = verify_schema_registry_attestation_for_review(
        platform_root,
        schema_registry_attestation_report,
        schema_registry_attestation_path,
        schema_registry_runtime_report=schema_registry_runtime_report,
    )
    schema_registry_ops_summary = (
        schema_registry_ops_report.get("summary")
        if isinstance(schema_registry_ops_report, dict) and isinstance(schema_registry_ops_report.get("summary"), dict)
        else {}
    )
    schema_registry_release_gate_passed = strict_schema_registry_release_gate_passed(schema_registry_ops_report)
    catalog_runtime_release_gate_passed = strict_catalog_runtime_ops_release_gate_passed(
        catalog_runtime_ops_report,
        target_environment=environment,
    )
    orchestration_runtime_ops_summary = (
        orchestration_runtime_ops_report.get("summary")
        if isinstance(orchestration_runtime_ops_report, dict)
        and isinstance(orchestration_runtime_ops_report.get("summary"), dict)
        else {}
    )
    orchestration_runtime_release_gate_passed = strict_orchestration_runtime_ops_release_gate_passed(
        orchestration_runtime_ops_report,
        target_environment=environment,
    )
    schema_registry_auth_summary = (
        schema_registry_auth_report.get("summary")
        if isinstance(schema_registry_auth_report, dict) and isinstance(schema_registry_auth_report.get("summary"), dict)
        else {}
    )
    schema_registry_auth_scope = (
        schema_registry_auth_report.get("runtime_scope")
        if isinstance(schema_registry_auth_report, dict)
        and isinstance(schema_registry_auth_report.get("runtime_scope"), dict)
        else {}
    )
    schema_registry_storage_summary = (
        schema_registry_storage_report.get("summary")
        if isinstance(schema_registry_storage_report, dict)
        and isinstance(schema_registry_storage_report.get("summary"), dict)
        else {}
    )
    schema_registry_storage_scope = (
        schema_registry_storage_report.get("runtime_scope")
        if isinstance(schema_registry_storage_report, dict)
        and isinstance(schema_registry_storage_report.get("runtime_scope"), dict)
        else {}
    )
    broker_acl_summary = (
        broker_acl_report.get("summary")
        if isinstance(broker_acl_report, dict) and isinstance(broker_acl_report.get("summary"), dict)
        else {}
    )
    broker_acl_scope = (
        broker_acl_report.get("runtime_scope")
        if isinstance(broker_acl_report, dict) and isinstance(broker_acl_report.get("runtime_scope"), dict)
        else {}
    )
    transactional_outbox_summary = (
        transactional_outbox_report.get("summary")
        if isinstance(transactional_outbox_report, dict)
        and isinstance(transactional_outbox_report.get("summary"), dict)
        else {}
    )
    transactional_outbox_scope = (
        transactional_outbox_report.get("runtime_scope")
        if isinstance(transactional_outbox_report, dict)
        and isinstance(transactional_outbox_report.get("runtime_scope"), dict)
        else {}
    )
    live_bronze_ingestion_summary = (
        live_bronze_ingestion_report.get("summary")
        if isinstance(live_bronze_ingestion_report, dict)
        and isinstance(live_bronze_ingestion_report.get("summary"), dict)
        else {}
    )
    live_bronze_ingestion_scope = (
        live_bronze_ingestion_report.get("runtime_scope")
        if isinstance(live_bronze_ingestion_report, dict)
        and isinstance(live_bronze_ingestion_report.get("runtime_scope"), dict)
        else {}
    )
    orchestrated_publication_summary = (
        orchestrated_publication_report.get("summary")
        if isinstance(orchestrated_publication_report, dict)
        and isinstance(orchestrated_publication_report.get("summary"), dict)
        else {}
    )
    orchestrated_publication_scope = (
        orchestrated_publication_report.get("runtime_scope")
        if isinstance(orchestrated_publication_report, dict)
        and isinstance(orchestrated_publication_report.get("runtime_scope"), dict)
        else {}
    )
    live_quality_slo_summary = (
        live_quality_slo_report.get("summary")
        if isinstance(live_quality_slo_report, dict)
        and isinstance(live_quality_slo_report.get("summary"), dict)
        else {}
    )
    live_quality_slo_scope = (
        live_quality_slo_report.get("runtime_scope")
        if isinstance(live_quality_slo_report, dict)
        and isinstance(live_quality_slo_report.get("runtime_scope"), dict)
        else {}
    )
    live_lakehouse_summary = (
        live_lakehouse_report.get("summary")
        if isinstance(live_lakehouse_report, dict) and isinstance(live_lakehouse_report.get("summary"), dict)
        else {}
    )
    live_lakehouse_scope = (
        live_lakehouse_report.get("runtime_scope")
        if isinstance(live_lakehouse_report, dict) and isinstance(live_lakehouse_report.get("runtime_scope"), dict)
        else {}
    )
    iceberg_catalog_summary = (
        iceberg_catalog_report.get("summary")
        if isinstance(iceberg_catalog_report, dict) and isinstance(iceberg_catalog_report.get("summary"), dict)
        else {}
    )
    iceberg_catalog_scope = (
        iceberg_catalog_report.get("runtime_scope")
        if isinstance(iceberg_catalog_report, dict) and isinstance(iceberg_catalog_report.get("runtime_scope"), dict)
        else {}
    )
    object_store_summary = (
        object_store_report.get("summary")
        if isinstance(object_store_report, dict) and isinstance(object_store_report.get("summary"), dict)
        else {}
    )
    object_store_scope = (
        object_store_report.get("runtime_scope")
        if isinstance(object_store_report, dict) and isinstance(object_store_report.get("runtime_scope"), dict)
        else {}
    )
    trino_sql_summary = (
        trino_sql_report.get("summary")
        if isinstance(trino_sql_report, dict) and isinstance(trino_sql_report.get("summary"), dict)
        else {}
    )
    trino_sql_scope = (
        trino_sql_report.get("runtime_scope")
        if isinstance(trino_sql_report, dict) and isinstance(trino_sql_report.get("runtime_scope"), dict)
        else {}
    )
    trino_iceberg_minio_summary = (
        trino_iceberg_minio_report.get("summary")
        if isinstance(trino_iceberg_minio_report, dict)
        and isinstance(trino_iceberg_minio_report.get("summary"), dict)
        else {}
    )
    trino_iceberg_minio_scope = (
        trino_iceberg_minio_report.get("runtime_scope")
        if isinstance(trino_iceberg_minio_report, dict)
        and isinstance(trino_iceberg_minio_report.get("runtime_scope"), dict)
        else {}
    )
    catalog_cross_engine_summary = (
        catalog_cross_engine_report.get("summary")
        if isinstance(catalog_cross_engine_report, dict)
        and isinstance(catalog_cross_engine_report.get("summary"), dict)
        else {}
    )
    catalog_cross_engine_scope = (
        catalog_cross_engine_report.get("runtime_scope")
        if isinstance(catalog_cross_engine_report, dict)
        and isinstance(catalog_cross_engine_report.get("runtime_scope"), dict)
        else {}
    )
    catalog_runtime_ops_summary = (
        catalog_runtime_ops_report.get("summary")
        if isinstance(catalog_runtime_ops_report, dict)
        and isinstance(catalog_runtime_ops_report.get("summary"), dict)
        else {}
    )
    trino_runtime_security_summary = (
        trino_runtime_security_report.get("summary")
        if isinstance(trino_runtime_security_report, dict)
        and isinstance(trino_runtime_security_report.get("summary"), dict)
        else {}
    )
    trino_runtime_security_scope = (
        trino_runtime_security_report.get("runtime_scope")
        if isinstance(trino_runtime_security_report, dict)
        and isinstance(trino_runtime_security_report.get("runtime_scope"), dict)
        else {}
    )
    policy_decision_summary = (
        policy_decision_report.get("summary")
        if isinstance(policy_decision_report, dict) and isinstance(policy_decision_report.get("summary"), dict)
        else {}
    )
    policy_decision_scope = (
        policy_decision_report.get("runtime_scope")
        if isinstance(policy_decision_report, dict) and isinstance(policy_decision_report.get("runtime_scope"), dict)
        else {}
    )
    oidc_auth_summary = (
        oidc_auth_report.get("summary")
        if isinstance(oidc_auth_report, dict) and isinstance(oidc_auth_report.get("summary"), dict)
        else {}
    )
    oidc_auth_scope = (
        oidc_auth_report.get("runtime_scope")
        if isinstance(oidc_auth_report, dict) and isinstance(oidc_auth_report.get("runtime_scope"), dict)
        else {}
    )
    access_privacy_release_gate_passed = strict_access_privacy_release_gate_passed(
        trino_runtime_security_report=trino_runtime_security_report,
        policy_decision_report=policy_decision_report,
        oidc_auth_report=oidc_auth_report,
    )
    secret_rotation_summary = (
        secret_rotation_report.get("summary")
        if isinstance(secret_rotation_report, dict) and isinstance(secret_rotation_report.get("summary"), dict)
        else {}
    )
    secret_rotation_scope = (
        secret_rotation_report.get("runtime_scope")
        if isinstance(secret_rotation_report, dict)
        and isinstance(secret_rotation_report.get("runtime_scope"), dict)
        else {}
    )
    secret_rotation_ops_summary = (
        secret_rotation_ops_report.get("summary")
        if isinstance(secret_rotation_ops_report, dict)
        and isinstance(secret_rotation_ops_report.get("summary"), dict)
        else {}
    )
    secret_rotation_ops_release_gate_passed = strict_secret_rotation_ops_release_gate_passed(
        secret_rotation_ops_report,
        target_environment=environment,
    )
    dagster_orchestration_summary = (
        dagster_orchestration_report.get("summary")
        if isinstance(dagster_orchestration_report, dict) and isinstance(dagster_orchestration_report.get("summary"), dict)
        else {}
    )
    dagster_orchestration_scope = (
        dagster_orchestration_report.get("runtime_scope")
        if isinstance(dagster_orchestration_report, dict)
        and isinstance(dagster_orchestration_report.get("runtime_scope"), dict)
        else {}
    )
    dagster_day2_summary = (
        dagster_day2_report.get("summary")
        if isinstance(dagster_day2_report, dict) and isinstance(dagster_day2_report.get("summary"), dict)
        else {}
    )
    dagster_day2_scope = (
        dagster_day2_report.get("runtime_scope")
        if isinstance(dagster_day2_report, dict) and isinstance(dagster_day2_report.get("runtime_scope"), dict)
        else {}
    )
    dagster_day2_release_gate_passed = strict_dagster_day2_release_gate_passed(dagster_day2_report)
    runtime_iac_release_gate_passed = strict_runtime_iac_release_gate_passed(
        runtime_report,
        target_environment=environment,
    )
    portfolio_summary = (
        portfolio_report.get("summary")
        if isinstance(portfolio_report, dict) and isinstance(portfolio_report.get("summary"), dict)
        else {}
    )
    portfolio_scope = (
        portfolio_report.get("runtime_scope")
        if isinstance(portfolio_report, dict) and isinstance(portfolio_report.get("runtime_scope"), dict)
        else {}
    )
    workload_benchmark_summary = (
        workload_benchmark_report.get("summary")
        if isinstance(workload_benchmark_report, dict)
        and isinstance(workload_benchmark_report.get("summary"), dict)
        else {}
    )
    workload_benchmark_release_gate_passed = strict_workload_benchmark_release_gate_passed(
        workload_benchmark_report,
        target_environment=environment,
    )
    production_ready = (
        bool(control_tower_report.get("p0_ready"))
        and bool(control_tower_report.get("passed"))
        and workload_benchmark_release_gate_passed
    )
    non_infra_blockers = non_infra_control_tower_blockers(control_tower_report)
    code_control_plane_ready = (
        not non_infra_blockers
        and smoke_report.get("passed") is True
        and portfolio_report is not None
        and portfolio_report.get("passed") is True
    )
    manifest = {
        "artifact_type": "production_review_pack.v1",
        "report_version": REPORT_VERSION,
        "generated_at": generated_at,
        "environment": environment,
        "output_dir": output_dir.as_posix(),
        "verdict": {
            "partner_review_ready": True,
            "production_ready": production_ready,
            "code_control_plane_ready_excluding_live_infra": code_control_plane_ready,
            "readiness_state": control_tower_report.get("readiness_state"),
            "message": "Generated review evidence pack. Production readiness remains false while Control Tower P0 blockers exist."
            if not production_ready
            else "Generated review evidence pack. Control Tower reports P0 production readiness.",
        },
        "artifacts": {
            "event_backbone_smoke": optional_artifact_ref(event_backbone_path, event_backbone_report),
            "ingestion_runtime": optional_artifact_ref(ingestion_runtime_path, ingestion_runtime_report),
            "catalog_lineage_ops": optional_artifact_ref(catalog_lineage_ops_path, catalog_lineage_ops_report),
            "semantic_metric_serving_ops": optional_artifact_ref(
                semantic_metric_serving_ops_path,
                semantic_metric_serving_ops_report,
            ),
            "source_activation_ops": optional_artifact_ref(source_activation_ops_path, source_activation_ops_report),
            "backfill_readiness": optional_artifact_ref(backfill_readiness_path, backfill_readiness_report),
            "schema_registry_runtime_smoke": optional_artifact_ref(schema_registry_runtime_path, schema_registry_runtime_report),
            "schema_registry_attestation": optional_artifact_ref(
                schema_registry_attestation_path,
                schema_registry_attestation_report,
            ),
            "schema_registry_ops": optional_artifact_ref(schema_registry_ops_path, schema_registry_ops_report),
            "schema_registry_auth_smoke": optional_artifact_ref(schema_registry_auth_path, schema_registry_auth_report),
            "schema_registry_storage_smoke": optional_artifact_ref(
                schema_registry_storage_path,
                schema_registry_storage_report,
            ),
            "broker_acl_smoke": optional_artifact_ref(broker_acl_path, broker_acl_report),
            "transactional_outbox_smoke": optional_artifact_ref(
                transactional_outbox_path,
                transactional_outbox_report,
            ),
            "live_bronze_ingestion_smoke": optional_artifact_ref(
                live_bronze_ingestion_path,
                live_bronze_ingestion_report,
            ),
            "orchestrated_publication_smoke": optional_artifact_ref(
                orchestrated_publication_path,
                orchestrated_publication_report,
            ),
            "live_quality_slo_smoke": optional_artifact_ref(live_quality_slo_path, live_quality_slo_report),
            "live_lakehouse_smoke": optional_artifact_ref(live_lakehouse_path, live_lakehouse_report),
            "iceberg_catalog_smoke": optional_artifact_ref(iceberg_catalog_path, iceberg_catalog_report),
            "object_store_commit_smoke": optional_artifact_ref(object_store_path, object_store_report),
            "trino_sql_runtime_smoke": optional_artifact_ref(trino_sql_path, trino_sql_report),
            "trino_iceberg_minio_smoke": optional_artifact_ref(trino_iceberg_minio_path, trino_iceberg_minio_report),
            "catalog_cross_engine_smoke": optional_artifact_ref(
                catalog_cross_engine_path,
                catalog_cross_engine_report,
            ),
            "catalog_runtime_ops": optional_artifact_ref(catalog_runtime_ops_path, catalog_runtime_ops_report),
            "orchestration_runtime_ops": optional_artifact_ref(
                orchestration_runtime_ops_path,
                orchestration_runtime_ops_report,
            ),
            "trino_runtime_security_smoke": optional_artifact_ref(trino_runtime_security_path, trino_runtime_security_report),
            "policy_decision_smoke": optional_artifact_ref(policy_decision_path, policy_decision_report),
            "oidc_auth_smoke": optional_artifact_ref(oidc_auth_path, oidc_auth_report),
            "secret_rotation_smoke": optional_artifact_ref(secret_rotation_path, secret_rotation_report),
            "secret_rotation_ops": optional_artifact_ref(secret_rotation_ops_path, secret_rotation_ops_report),
            "dagster_orchestration_smoke": optional_artifact_ref(dagster_orchestration_path, dagster_orchestration_report),
            "dagster_day2_smoke": optional_artifact_ref(dagster_day2_path, dagster_day2_report),
            "portfolio_release_smoke": optional_artifact_ref(portfolio_path, portfolio_report),
            "workload_benchmark": optional_artifact_ref(workload_benchmark_path, workload_benchmark_report),
            "data_plane_smoke": artifact_ref(smoke_path, smoke_report),
            "runtime_readiness": artifact_ref(runtime_path, runtime_report),
            "capability_maturity": artifact_ref(capability_path, capability_report),
            "control_tower": artifact_ref(control_tower_path, control_tower_report),
        },
        "summary": {
            "data_plane_smoke_passed": smoke_report.get("passed"),
            "data_plane_smoke_use_case": smoke_report.get("use_case_id"),
            "data_plane_smoke_primary_output": smoke_report.get("primary_output"),
            "data_plane_smoke_failed_check_count": smoke_summary.get("failed_check_count", 0),
            "data_plane_smoke_not_covered": smoke_scope.get("not_covered", []),
            "event_backbone_smoke_attached": event_backbone_report is not None,
            "event_backbone_smoke_passed": event_backbone_report.get("passed") if event_backbone_report else None,
            "event_backbone_smoke_failed_check_count": event_summary.get("failed_check_count", 0),
            "event_backbone_smoke_source_record_count": event_summary.get("source_record_count", 0),
            "event_backbone_smoke_consumed_record_count": event_summary.get("consumed_record_count", 0),
            "event_backbone_smoke_multi_partition_rebalance_passed": event_summary.get(
                "multi_partition_rebalance_passed"
            ),
            "event_backbone_smoke_multi_partition_topic_partition_count": event_summary.get(
                "multi_partition_topic_partition_count"
            ),
            "event_backbone_smoke_multi_partition_group_total_lag": event_summary.get(
                "multi_partition_group_total_lag"
            ),
            "event_backbone_smoke_not_covered": event_scope.get("not_covered", []),
            "ingestion_runtime_attached": ingestion_runtime_report is not None,
            "ingestion_runtime_passed": ingestion_runtime_report.get("passed") if ingestion_runtime_report else None,
            "ingestion_runtime_readiness_state": ingestion_runtime_report.get("readiness_state") if ingestion_runtime_report else None,
            "ingestion_runtime_mode": ingestion_runtime_report.get("mode") if ingestion_runtime_report else None,
            "ingestion_runtime_source_kind": ingestion_runtime_evidence.get("source_kind"),
            "ingestion_runtime_p0_source_count": ingestion_runtime_summary.get("p0_source_count", 0),
            "ingestion_runtime_p0_failed_source_count": ingestion_runtime_summary.get("p0_failed_source_count", 0),
            "ingestion_runtime_running_connector_count": ingestion_runtime_summary.get("running_connector_count", 0),
            "ingestion_runtime_global_failed_check_count": ingestion_runtime_summary.get("global_failed_check_count", 0),
            "catalog_lineage_ops_attached": catalog_lineage_ops_report is not None,
            "catalog_lineage_ops_passed": catalog_lineage_ops_report.get("passed")
            if catalog_lineage_ops_report
            else None,
            "catalog_lineage_ops_environment": catalog_lineage_ops_report.get("environment")
            if catalog_lineage_ops_report
            else None,
            "catalog_lineage_ops_readiness_state": catalog_lineage_ops_report.get("readiness_state")
            if catalog_lineage_ops_report
            else None,
            "catalog_lineage_ops_mode": catalog_lineage_ops_report.get("mode")
            if catalog_lineage_ops_report
            else None,
            "catalog_lineage_ops_data_product_count": catalog_lineage_ops_summary.get("data_product_count", 0),
            "catalog_lineage_ops_failed_product_count": catalog_lineage_ops_summary.get("failed_product_count", 0),
            "catalog_lineage_ops_global_failed_check_count": catalog_lineage_ops_summary.get(
                "global_failed_check_count",
                0,
            ),
            "catalog_lineage_ops_publish_status": catalog_lineage_ops_summary.get("catalog_publish_status"),
            "catalog_lineage_ops_openlineage_event_count": catalog_lineage_ops_summary.get(
                "openlineage_event_count",
                0,
            ),
            "catalog_lineage_release_gate_passed": catalog_lineage_release_gate_passed,
            "semantic_metric_serving_ops_attached": semantic_metric_serving_ops_report is not None,
            "semantic_metric_serving_ops_passed": semantic_metric_serving_ops_report.get("passed")
            if semantic_metric_serving_ops_report
            else None,
            "semantic_metric_serving_ops_environment": semantic_metric_serving_ops_report.get("environment")
            if semantic_metric_serving_ops_report
            else None,
            "semantic_metric_serving_ops_readiness_state": semantic_metric_serving_ops_report.get("readiness_state")
            if semantic_metric_serving_ops_report
            else None,
            "semantic_metric_serving_ops_mode": semantic_metric_serving_ops_report.get("mode")
            if semantic_metric_serving_ops_report
            else None,
            "semantic_metric_serving_ops_metric_count": semantic_metric_serving_ops_summary.get("metric_count", 0),
            "semantic_metric_serving_ops_failed_metric_count": semantic_metric_serving_ops_summary.get(
                "failed_metric_count",
                0,
            ),
            "semantic_metric_serving_ops_global_failed_check_count": semantic_metric_serving_ops_summary.get(
                "global_failed_check_count",
                0,
            ),
            "semantic_metric_serving_ops_certification_attached": semantic_metric_serving_ops_summary.get(
                "certification_evidence_attached"
            ),
            "semantic_metric_serving_ops_deployment_attached": semantic_metric_serving_ops_summary.get(
                "deployment_evidence_attached"
            ),
            "semantic_metric_serving_ops_usage_attached": semantic_metric_serving_ops_summary.get(
                "usage_evidence_attached"
            ),
            "semantic_metric_serving_ops_usage_tracking_gap_count": semantic_metric_serving_ops_summary.get(
                "usage_tracking_gap_count",
                0,
            ),
            "semantic_metric_serving_release_gate_passed": semantic_metric_serving_release_gate_passed,
            "source_activation_ops_attached": source_activation_ops_report is not None,
            "source_activation_ops_passed": source_activation_ops_report.get("passed")
            if source_activation_ops_report
            else None,
            "source_activation_ops_environment": source_activation_ops_report.get("environment")
            if source_activation_ops_report
            else None,
            "source_activation_ops_readiness_state": source_activation_ops_report.get("readiness_state")
            if source_activation_ops_report
            else None,
            "source_activation_ops_mode": source_activation_ops_report.get("mode")
            if source_activation_ops_report
            else None,
            "source_activation_ops_source_count": source_activation_ops_summary.get("source_count", 0),
            "source_activation_ops_p0_source_count": source_activation_ops_summary.get("p0_source_count", 0),
            "source_activation_ops_active_count": source_activation_ops_summary.get("active_count", 0),
            "source_activation_ops_p0_active_count": source_activation_ops_summary.get("p0_active_count", 0),
            "source_activation_ops_p0_unactivated_count": source_activation_ops_summary.get(
                "p0_unactivated_count",
                0,
            ),
            "source_activation_ops_p0_activation_gap_count": source_activation_ops_summary.get(
                "p0_activation_gap_count",
                0,
            ),
            "source_activation_ops_production_ready_count": source_activation_ops_summary.get(
                "production_ready_count",
                0,
            ),
            "source_activation_ops_critical_issue_count": source_activation_ops_summary.get(
                "critical_issue_count",
                0,
            ),
            "source_activation_ops_p0_critical_issue_count": source_activation_ops_summary.get(
                "p0_critical_issue_count",
                0,
            ),
            "source_activation_ops_expired_count": source_activation_ops_summary.get("expired_count", 0),
            "source_activation_ops_revoked_count": source_activation_ops_summary.get("revoked_count", 0),
            "source_activation_ops_registry_drift_count": source_activation_ops_summary.get(
                "registry_drift_count",
                0,
            ),
            "source_activation_ops_pointer_issue_count": source_activation_ops_summary.get(
                "pointer_issue_count",
                0,
            ),
            "source_activation_ops_runtime_readiness_issue_count": source_activation_ops_summary.get(
                "runtime_readiness_issue_count",
                0,
            ),
            "source_activation_ops_p0_runtime_readiness_issue_count": source_activation_ops_summary.get(
                "p0_runtime_readiness_issue_count",
                0,
            ),
            "source_activation_ops_evidence_integrity_issue_count": source_activation_ops_summary.get(
                "evidence_integrity_issue_count",
                0,
            ),
            "source_activation_ops_p0_evidence_integrity_issue_count": source_activation_ops_summary.get(
                "p0_evidence_integrity_issue_count",
                0,
            ),
            "source_onboarding_release_gate_passed": source_onboarding_release_gate_passed,
            "backfill_readiness_attached": backfill_readiness_report is not None,
            "backfill_readiness_passed": backfill_readiness_report.get("passed")
            if backfill_readiness_report
            else None,
            "backfill_readiness_environment": backfill_readiness_report.get("environment")
            if backfill_readiness_report
            else None,
            "backfill_readiness_mode": backfill_readiness_report.get("mode")
            if backfill_readiness_report
            else None,
            "backfill_readiness_state": backfill_readiness_report.get("readiness_state")
            if backfill_readiness_report
            else None,
            "backfill_readiness_failed_check_count": backfill_readiness_summary.get("failed_check_count", 0),
            "backfill_readiness_attached_evidence_count": backfill_readiness_summary.get(
                "attached_evidence_count",
                0,
            ),
            "backfill_readiness_required_evidence_count": len(required_backfill_readiness_evidence_keys()),
            "backfill_change_governance_release_gate_passed": backfill_change_governance_release_gate_passed,
            "schema_registry_runtime_smoke_attached": schema_registry_runtime_report is not None,
            "schema_registry_runtime_smoke_passed": schema_registry_runtime_report.get("passed")
            if schema_registry_runtime_report
            else None,
            "schema_registry_runtime_smoke_failed_check_count": schema_registry_runtime_summary.get("failed_check_count", 0),
            "schema_registry_runtime_smoke_registry_api": schema_registry_runtime_summary.get("registry_api"),
            "schema_registry_runtime_smoke_subject_count": schema_registry_runtime_summary.get("subject_count", 0),
            "schema_registry_runtime_smoke_published_subject_count": schema_registry_runtime_summary.get("published_subject_count", 0),
            "schema_registry_runtime_smoke_readback_passed_count": schema_registry_runtime_summary.get("readback_passed_count", 0),
            "schema_registry_runtime_smoke_hash_match_count": schema_registry_runtime_summary.get("hash_match_count", 0),
            "schema_registry_runtime_smoke_not_covered": schema_registry_runtime_scope.get("not_covered", []),
            "schema_registry_attestation_attached": schema_registry_attestation_report is not None,
            "schema_registry_attestation_passed": schema_registry_attestation_verification.get("passed")
            if schema_registry_attestation_verification
            else None,
            "schema_registry_attestation_environment": schema_registry_attestation_report.get("environment")
            if schema_registry_attestation_report
            else None,
            "schema_registry_attestation_subject_hash": schema_registry_attestation_report.get("subject_hash")
            if schema_registry_attestation_report
            else None,
            "schema_registry_attestation_subject_hash_expected": schema_registry_attestation_verification.get(
                "subject_hash_expected"
            )
            if schema_registry_attestation_verification
            else None,
            "schema_registry_attestation_signature_verified": (
                schema_registry_attestation_verification.get("required", {}).get("signature_verified")
                if schema_registry_attestation_verification
                else None
            ),
            "schema_registry_attestation_subject_hash_matches": (
                schema_registry_attestation_verification.get("required", {}).get("subject_hash_matches")
                if schema_registry_attestation_verification
                else None
            ),
            "schema_registry_ops_attached": schema_registry_ops_report is not None,
            "schema_registry_ops_passed": schema_registry_ops_report.get("passed")
            if schema_registry_ops_report
            else None,
            "schema_registry_ops_environment": schema_registry_ops_report.get("environment")
            if schema_registry_ops_report
            else None,
            "schema_registry_ops_readiness_state": schema_registry_ops_report.get("readiness_state")
            if schema_registry_ops_report
            else None,
            "schema_registry_ops_subject_count": schema_registry_ops_summary.get("subject_count", 0),
            "schema_registry_ops_p0_failed_subject_count": schema_registry_ops_summary.get(
                "p0_failed_subject_count",
                0,
            ),
            "schema_registry_ops_failed_subject_count": schema_registry_ops_summary.get("failed_subject_count", 0),
            "schema_registry_ops_global_failed_check_count": schema_registry_ops_summary.get(
                "global_failed_check_count",
                0,
            ),
            "schema_registry_ops_publication_evidence_attached": schema_registry_ops_summary.get(
                "publication_evidence_attached"
            ),
            "schema_registry_ops_producer_enforcement_gap_count": schema_registry_ops_summary.get(
                "producer_enforcement_gap_count",
                0,
            ),
            "schema_registry_ops_broker_validation_gap_count": schema_registry_ops_summary.get(
                "broker_validation_gap_count",
                0,
            ),
            "schema_registry_release_gate_passed": schema_registry_release_gate_passed,
            "schema_registry_auth_smoke_attached": schema_registry_auth_report is not None,
            "schema_registry_auth_smoke_passed": schema_registry_auth_report.get("passed")
            if schema_registry_auth_report
            else None,
            "schema_registry_auth_smoke_auth_gateway_enforced": schema_registry_auth_summary.get(
                "auth_gateway_enforced"
            ),
            "schema_registry_auth_smoke_missing_token_denied": schema_registry_auth_summary.get("missing_token_denied"),
            "schema_registry_auth_smoke_unknown_token_denied": schema_registry_auth_summary.get("unknown_token_denied"),
            "schema_registry_auth_smoke_denied_token_blocked": schema_registry_auth_summary.get("denied_token_blocked"),
            "schema_registry_auth_smoke_reader_write_denied": schema_registry_auth_summary.get("reader_write_denied"),
            "schema_registry_auth_smoke_publisher_publish_allowed": schema_registry_auth_summary.get(
                "publisher_publish_allowed"
            ),
            "schema_registry_auth_smoke_reader_read_allowed": schema_registry_auth_summary.get("reader_read_allowed"),
            "schema_registry_auth_smoke_authorization_audit_event_count": schema_registry_auth_summary.get(
                "authorization_audit_event_count",
                0,
            ),
            "schema_registry_auth_smoke_failed_check_count": schema_registry_auth_summary.get("failed_check_count", 0),
            "schema_registry_auth_smoke_not_covered": schema_registry_auth_scope.get("not_covered", []),
            "schema_registry_storage_smoke_attached": schema_registry_storage_report is not None,
            "schema_registry_storage_smoke_passed": schema_registry_storage_report.get("passed")
            if schema_registry_storage_report
            else None,
            "schema_registry_storage_smoke_backend": schema_registry_storage_summary.get("storage_backend"),
            "schema_registry_storage_smoke_replica_count": schema_registry_storage_summary.get(
                "registry_replica_count",
                0,
            ),
            "schema_registry_storage_smoke_shared_sql_storage_configured": schema_registry_storage_summary.get(
                "shared_sql_storage_configured"
            ),
            "schema_registry_storage_smoke_secret_env_files_persisted": schema_registry_storage_summary.get(
                "secret_env_files_persisted"
            ),
            "schema_registry_storage_smoke_cross_replica_read_after_write_passed": schema_registry_storage_summary.get(
                "cross_replica_read_after_write_passed"
            ),
            "schema_registry_storage_smoke_replica_restart_durable_readback_passed": schema_registry_storage_summary.get(
                "replica_restart_durable_readback_passed"
            ),
            "schema_registry_storage_smoke_failed_check_count": schema_registry_storage_summary.get("failed_check_count", 0),
            "schema_registry_storage_smoke_not_covered": schema_registry_storage_scope.get("not_covered", []),
            "broker_acl_smoke_attached": broker_acl_report is not None,
            "broker_acl_smoke_passed": broker_acl_report.get("passed") if broker_acl_report else None,
            "broker_acl_smoke_broker_acl_enforced": broker_acl_summary.get("broker_acl_enforced"),
            "broker_acl_smoke_allowed_user_can_produce": broker_acl_summary.get("allowed_user_can_produce"),
            "broker_acl_smoke_denied_user_blocked": broker_acl_summary.get("denied_user_blocked"),
            "broker_acl_smoke_authorization_denied_verified": broker_acl_summary.get("authorization_denied_verified"),
            "broker_acl_smoke_failed_check_count": broker_acl_summary.get("failed_check_count", 0),
            "broker_acl_smoke_not_covered": broker_acl_scope.get("not_covered", []),
            "transactional_outbox_smoke_attached": transactional_outbox_report is not None,
            "transactional_outbox_smoke_passed": transactional_outbox_report.get("passed")
            if transactional_outbox_report
            else None,
            "transactional_outbox_smoke_to_bronze_passed": transactional_outbox_summary.get(
                "transactional_outbox_to_bronze_passed"
            ),
            "transactional_outbox_smoke_source_type": transactional_outbox_summary.get("source_type"),
            "transactional_outbox_smoke_connector_record_count": transactional_outbox_summary.get(
                "connector_record_count",
                0,
            ),
            "transactional_outbox_smoke_consumed_record_count": transactional_outbox_summary.get(
                "consumed_record_count",
                0,
            ),
            "transactional_outbox_smoke_bronze_approved_new_row_count": transactional_outbox_summary.get(
                "bronze_approved_new_row_count"
            ),
            "transactional_outbox_smoke_bronze_quarantine_row_count": transactional_outbox_summary.get(
                "bronze_quarantine_row_count"
            ),
            "transactional_outbox_smoke_failed_check_count": transactional_outbox_summary.get("failed_check_count", 0),
            "transactional_outbox_smoke_not_covered": transactional_outbox_scope.get("not_covered", []),
            "live_bronze_ingestion_smoke_attached": live_bronze_ingestion_report is not None,
            "live_bronze_ingestion_smoke_passed": live_bronze_ingestion_report.get("passed")
            if live_bronze_ingestion_report
            else None,
            "live_bronze_ingestion_smoke_source_id": live_bronze_ingestion_summary.get("source_id"),
            "live_bronze_ingestion_smoke_bronze_target": live_bronze_ingestion_summary.get("bronze_target"),
            "live_bronze_ingestion_smoke_iceberg_table": live_bronze_ingestion_summary.get("iceberg_table"),
            "live_bronze_ingestion_smoke_consumed_record_count": live_bronze_ingestion_summary.get(
                "consumed_record_count",
                0,
            ),
            "live_bronze_ingestion_smoke_approved_row_count": live_bronze_ingestion_summary.get("approved_row_count", 0),
            "live_bronze_ingestion_smoke_duplicate_skipped_count": live_bronze_ingestion_summary.get(
                "duplicate_skipped_count",
                0,
            ),
            "live_bronze_ingestion_smoke_quarantine_row_count": live_bronze_ingestion_summary.get(
                "quarantine_row_count",
                0,
            ),
            "live_bronze_ingestion_smoke_snapshot_count_after": live_bronze_ingestion_summary.get(
                "snapshot_count_after",
                0,
            ),
            "live_bronze_ingestion_smoke_restart_resume_passed": live_bronze_ingestion_summary.get(
                "restart_resume_passed"
            ),
            "live_bronze_ingestion_smoke_dlt_quarantine_passed": live_bronze_ingestion_summary.get(
                "dlt_quarantine_passed"
            ),
            "live_bronze_ingestion_smoke_failed_check_count": live_bronze_ingestion_summary.get(
                "failed_check_count",
                0,
            ),
            "live_bronze_ingestion_smoke_not_covered": live_bronze_ingestion_scope.get("not_covered", []),
            "orchestrated_publication_smoke_attached": orchestrated_publication_report is not None,
            "orchestrated_publication_smoke_passed": orchestrated_publication_report.get("passed")
            if orchestrated_publication_report
            else None,
            "orchestrated_publication_smoke_bronze_row_count": orchestrated_publication_summary.get(
                "bronze_row_count",
                0,
            ),
            "orchestrated_publication_smoke_silver_row_count": orchestrated_publication_summary.get(
                "silver_row_count",
                0,
            ),
            "orchestrated_publication_smoke_gold_row_count": orchestrated_publication_summary.get(
                "gold_row_count",
                0,
            ),
            "orchestrated_publication_smoke_trino_silver_row_count": orchestrated_publication_summary.get(
                "trino_silver_row_count",
                0,
            ),
            "orchestrated_publication_smoke_trino_gold_row_count": orchestrated_publication_summary.get(
                "trino_gold_row_count",
                0,
            ),
            "orchestrated_publication_smoke_promotion_passed": orchestrated_publication_summary.get(
                "promotion_passed"
            ),
            "orchestrated_publication_smoke_activation_passed": orchestrated_publication_summary.get(
                "activation_passed"
            ),
            "orchestrated_publication_smoke_publication_ops_passed": orchestrated_publication_summary.get(
                "publication_ops_passed"
            ),
            "orchestrated_publication_smoke_active_pointer_drift_negative_test_passed": orchestrated_publication_summary.get(
                "active_pointer_drift_negative_test_passed"
            ),
            "orchestrated_publication_smoke_dagster_retry_event_count": orchestrated_publication_summary.get(
                "dagster_retry_event_count",
                0,
            ),
            "orchestrated_publication_smoke_asset_materialization_count": orchestrated_publication_summary.get(
                "asset_materialization_count",
                0,
            ),
            "orchestrated_publication_smoke_failed_check_count": orchestrated_publication_summary.get(
                "failed_check_count",
                0,
            ),
            "orchestrated_publication_smoke_not_covered": orchestrated_publication_scope.get("not_covered", []),
            "live_quality_slo_smoke_attached": live_quality_slo_report is not None,
            "live_quality_slo_smoke_passed": live_quality_slo_report.get("passed") if live_quality_slo_report else None,
            "live_quality_slo_smoke_target_data_product": live_quality_slo_summary.get("target_data_product"),
            "live_quality_slo_smoke_gold_row_count": live_quality_slo_summary.get("gold_row_count", 0),
            "live_quality_slo_smoke_quality_runtime_passed": live_quality_slo_summary.get(
                "quality_runtime_passed"
            ),
            "live_quality_slo_smoke_slo_alert_passed": live_quality_slo_summary.get("slo_alert_passed"),
            "live_quality_slo_smoke_quality_slo_ops_passed": live_quality_slo_summary.get(
                "quality_slo_ops_passed"
            ),
            "live_quality_slo_smoke_corrupt_gold_null_negative_test_passed": live_quality_slo_summary.get(
                "corrupt_gold_null_negative_test_passed"
            ),
            "live_quality_slo_smoke_stale_freshness_negative_test_passed": live_quality_slo_summary.get(
                "stale_freshness_negative_test_passed"
            ),
            "live_quality_slo_smoke_red_alert_negative_test_passed": live_quality_slo_summary.get(
                "red_alert_negative_test_passed"
            ),
            "live_quality_slo_smoke_environment_mismatch_negative_test_passed": live_quality_slo_summary.get(
                "environment_mismatch_negative_test_passed"
            ),
            "live_quality_slo_smoke_missing_alert_production_like_negative_test_passed": live_quality_slo_summary.get(
                "missing_alert_production_like_negative_test_passed"
            ),
            "live_quality_slo_smoke_failed_check_count": live_quality_slo_summary.get("failed_check_count", 0),
            "live_quality_slo_smoke_not_covered": live_quality_slo_scope.get("not_covered", []),
            "live_lakehouse_smoke_attached": live_lakehouse_report is not None,
            "live_lakehouse_smoke_passed": live_lakehouse_report.get("passed") if live_lakehouse_report else None,
            "live_lakehouse_smoke_failed_check_count": live_lakehouse_summary.get("failed_check_count", 0),
            "live_lakehouse_smoke_table_count": live_lakehouse_summary.get("table_count", 0),
            "live_lakehouse_smoke_parquet_commit_passed_count": live_lakehouse_summary.get("parquet_commit_passed_count", 0),
            "live_lakehouse_smoke_query_engine": live_lakehouse_summary.get("query_engine"),
            "live_lakehouse_smoke_query_passed": live_lakehouse_summary.get("query_passed"),
            "live_lakehouse_smoke_not_covered": live_lakehouse_scope.get("not_covered", []),
            "iceberg_catalog_smoke_attached": iceberg_catalog_report is not None,
            "iceberg_catalog_smoke_passed": iceberg_catalog_report.get("passed") if iceberg_catalog_report else None,
            "iceberg_catalog_smoke_failed_check_count": iceberg_catalog_summary.get("failed_check_count", 0),
            "iceberg_catalog_smoke_table_count": iceberg_catalog_summary.get("table_count", 0),
            "iceberg_catalog_smoke_table_passed_count": iceberg_catalog_summary.get("iceberg_table_passed_count", 0),
            "iceberg_catalog_smoke_snapshot_commit_count": iceberg_catalog_summary.get("snapshot_commit_count", 0),
            "iceberg_catalog_smoke_readback_passed_count": iceberg_catalog_summary.get("readback_passed_count", 0),
            "iceberg_catalog_smoke_not_covered": iceberg_catalog_scope.get("not_covered", []),
            "object_store_smoke_attached": object_store_report is not None,
            "object_store_smoke_passed": object_store_report.get("passed") if object_store_report else None,
            "object_store_smoke_failed_check_count": object_store_summary.get("failed_check_count", 0),
            "object_store_smoke_object_count": object_store_summary.get("object_count", 0),
            "object_store_smoke_uploaded_object_count": object_store_summary.get("uploaded_object_count", 0),
            "object_store_smoke_readback_passed_count": object_store_summary.get("readback_passed_count", 0),
            "object_store_smoke_encrypted_object_count": object_store_summary.get("encrypted_object_count", 0),
            "object_store_smoke_encryption_policy_enforced": object_store_summary.get(
                "encryption_policy_enforced"
            ),
            "object_store_smoke_unencrypted_put_denied": object_store_summary.get("unencrypted_put_denied"),
            "object_store_smoke_encrypted_put_allowed": object_store_summary.get("encrypted_put_allowed"),
            "object_store_smoke_not_covered": object_store_scope.get("not_covered", []),
            "trino_sql_smoke_attached": trino_sql_report is not None,
            "trino_sql_smoke_passed": trino_sql_report.get("passed") if trino_sql_report else None,
            "trino_sql_smoke_failed_check_count": trino_sql_summary.get("failed_check_count", 0),
            "trino_sql_smoke_row_count": trino_sql_summary.get("row_count", 0),
            "trino_sql_smoke_result_row_count": trino_sql_summary.get("result_row_count", 0),
            "trino_sql_smoke_query_engine": trino_sql_summary.get("query_engine"),
            "trino_sql_smoke_query_mode": trino_sql_summary.get("query_mode"),
            "trino_sql_smoke_query_passed": trino_sql_summary.get("query_passed"),
            "trino_sql_smoke_not_covered": trino_sql_scope.get("not_covered", []),
            "trino_iceberg_minio_smoke_attached": trino_iceberg_minio_report is not None,
            "trino_iceberg_minio_smoke_passed": trino_iceberg_minio_report.get("passed")
            if trino_iceberg_minio_report
            else None,
            "trino_iceberg_minio_smoke_failed_check_count": trino_iceberg_minio_summary.get("failed_check_count", 0),
            "trino_iceberg_minio_smoke_row_count": trino_iceberg_minio_summary.get("row_count", 0),
            "trino_iceberg_minio_smoke_query_mode": trino_iceberg_minio_summary.get("query_mode"),
            "trino_iceberg_minio_smoke_query_passed": trino_iceberg_minio_summary.get("query_passed"),
            "trino_iceberg_minio_smoke_snapshot_count": trino_iceberg_minio_summary.get("snapshot_count", 0),
            "trino_iceberg_minio_smoke_iceberg_file_count": trino_iceberg_minio_summary.get("iceberg_file_count", 0),
            "trino_iceberg_minio_smoke_minio_object_count": trino_iceberg_minio_summary.get("minio_object_count", 0),
            "trino_iceberg_minio_smoke_minio_encrypted_object_count": trino_iceberg_minio_summary.get(
                "minio_encrypted_object_count",
                0,
            ),
            "trino_iceberg_minio_smoke_object_store_encryption_policy_enforced": trino_iceberg_minio_summary.get(
                "object_store_encryption_policy_enforced"
            ),
            "trino_iceberg_minio_smoke_objects_encrypted": trino_iceberg_minio_summary.get(
                "trino_iceberg_objects_encrypted"
            ),
            "trino_iceberg_minio_smoke_not_covered": trino_iceberg_minio_scope.get("not_covered", []),
            "catalog_cross_engine_smoke_attached": catalog_cross_engine_report is not None,
            "catalog_cross_engine_smoke_passed": catalog_cross_engine_report.get("passed")
            if catalog_cross_engine_report
            else None,
            "catalog_cross_engine_smoke_failed_check_count": catalog_cross_engine_summary.get("failed_check_count", 0),
            "catalog_cross_engine_smoke_catalog_backend": catalog_cross_engine_summary.get("catalog_backend"),
            "catalog_cross_engine_smoke_cross_engine_commit_compatibility_passed": catalog_cross_engine_summary.get(
                "cross_engine_commit_compatibility_passed"
            ),
            "catalog_cross_engine_smoke_catalog_concurrency_locking_passed": catalog_cross_engine_summary.get(
                "catalog_concurrency_locking_passed"
            ),
            "catalog_cross_engine_smoke_stale_commit_rejected": catalog_cross_engine_summary.get(
                "stale_commit_rejected"
            ),
            "catalog_cross_engine_smoke_pyiceberg_readback_row_count": catalog_cross_engine_summary.get(
                "pyiceberg_readback_row_count",
                0,
            ),
            "catalog_cross_engine_smoke_snapshot_count_after_pyiceberg": catalog_cross_engine_summary.get(
                "snapshot_count_after_pyiceberg",
                0,
            ),
            "catalog_cross_engine_smoke_not_covered": catalog_cross_engine_scope.get("not_covered", []),
            "catalog_runtime_ops_attached": catalog_runtime_ops_report is not None,
            "catalog_runtime_ops_passed": catalog_runtime_ops_report.get("passed")
            if catalog_runtime_ops_report
            else None,
            "catalog_runtime_ops_environment": catalog_runtime_ops_report.get("environment")
            if catalog_runtime_ops_report
            else None,
            "catalog_runtime_ops_readiness_state": catalog_runtime_ops_report.get("readiness_state")
            if catalog_runtime_ops_report
            else None,
            "catalog_runtime_ops_mode": catalog_runtime_ops_report.get("mode")
            if catalog_runtime_ops_report
            else None,
            "catalog_runtime_ops_failed_check_count": catalog_runtime_ops_summary.get("failed_check_count", 0),
            "catalog_runtime_ops_catalog_provider": catalog_runtime_ops_summary.get("catalog_provider"),
            "catalog_runtime_ops_replica_count": catalog_runtime_ops_summary.get("replica_count", 0),
            "catalog_runtime_ops_availability_zones": catalog_runtime_ops_summary.get("availability_zones", 0),
            "catalog_runtime_ops_multi_az": catalog_runtime_ops_summary.get("multi_az"),
            "catalog_runtime_ops_failover_passed": catalog_runtime_ops_summary.get("failover_passed"),
            "catalog_runtime_ops_stale_commit_rejected": catalog_runtime_ops_summary.get("stale_commit_rejected"),
            "catalog_runtime_ops_backup_enabled": catalog_runtime_ops_summary.get("backup_enabled"),
            "catalog_runtime_ops_pitr_enabled": catalog_runtime_ops_summary.get("pitr_enabled"),
            "catalog_runtime_ops_restore_test_passed": catalog_runtime_ops_summary.get("restore_test_passed"),
            "catalog_runtime_ops_audit_event_count": catalog_runtime_ops_summary.get("audit_event_count", 0),
            "catalog_runtime_ops_audit_failed_event_count": catalog_runtime_ops_summary.get(
                "audit_failed_event_count",
                0,
            ),
            "catalog_runtime_release_gate_passed": catalog_runtime_release_gate_passed,
            "orchestration_runtime_ops_attached": orchestration_runtime_ops_report is not None,
            "orchestration_runtime_ops_passed": orchestration_runtime_ops_report.get("passed")
            if orchestration_runtime_ops_report
            else None,
            "orchestration_runtime_ops_environment": orchestration_runtime_ops_report.get("environment")
            if orchestration_runtime_ops_report
            else None,
            "orchestration_runtime_ops_readiness_state": orchestration_runtime_ops_report.get("readiness_state")
            if orchestration_runtime_ops_report
            else None,
            "orchestration_runtime_ops_mode": orchestration_runtime_ops_report.get("mode")
            if orchestration_runtime_ops_report
            else None,
            "orchestration_runtime_ops_failed_check_count": orchestration_runtime_ops_summary.get("failed_check_count", 0),
            "orchestration_runtime_ops_orchestrator_provider": orchestration_runtime_ops_summary.get("orchestrator_provider"),
            "orchestration_runtime_ops_replica_count": orchestration_runtime_ops_summary.get("replica_count", 0),
            "orchestration_runtime_ops_availability_zones": orchestration_runtime_ops_summary.get("availability_zones", 0),
            "orchestration_runtime_ops_multi_az": orchestration_runtime_ops_summary.get("multi_az"),
            "orchestration_runtime_ops_distributed_executor_enabled": orchestration_runtime_ops_summary.get(
                "distributed_executor_enabled"
            ),
            "orchestration_runtime_ops_kubernetes_run_launcher_enabled": orchestration_runtime_ops_summary.get(
                "kubernetes_run_launcher_enabled"
            ),
            "orchestration_runtime_ops_managed_run_storage": orchestration_runtime_ops_summary.get(
                "managed_run_storage"
            ),
            "orchestration_runtime_ops_schedule_tick_history_passed": orchestration_runtime_ops_summary.get(
                "schedule_tick_history_passed"
            ),
            "orchestration_runtime_ops_retry_policy_verified": orchestration_runtime_ops_summary.get(
                "retry_policy_verified"
            ),
            "orchestration_runtime_ops_backfill_materialization_history_passed": orchestration_runtime_ops_summary.get(
                "backfill_materialization_history_passed"
            ),
            "orchestration_runtime_ops_secret_injection_verified": orchestration_runtime_ops_summary.get(
                "secret_injection_verified"
            ),
            "orchestration_runtime_ops_metrics_exported": orchestration_runtime_ops_summary.get("metrics_exported"),
            "orchestration_runtime_release_gate_passed": orchestration_runtime_release_gate_passed,
            "trino_runtime_security_smoke_attached": trino_runtime_security_report is not None,
            "trino_runtime_security_smoke_passed": trino_runtime_security_report.get("passed")
            if trino_runtime_security_report
            else None,
            "trino_runtime_security_smoke_failed_check_count": trino_runtime_security_summary.get("failed_check_count", 0),
            "trino_runtime_security_smoke_query_mode": trino_runtime_security_summary.get("query_mode"),
            "trino_runtime_security_smoke_source_row_count": trino_runtime_security_summary.get("source_row_count", 0),
            "trino_runtime_security_smoke_allowed_user": trino_runtime_security_summary.get("allowed_user"),
            "trino_runtime_security_smoke_allowed_query_passed": trino_runtime_security_summary.get("allowed_query_passed"),
            "trino_runtime_security_smoke_allowed_write_blocked": trino_runtime_security_summary.get("allowed_write_blocked"),
            "trino_runtime_security_smoke_denied_user": trino_runtime_security_summary.get("denied_user"),
            "trino_runtime_security_smoke_denied_query_blocked": trino_runtime_security_summary.get("denied_query_blocked"),
            "trino_runtime_security_smoke_unknown_user_blocked": trino_runtime_security_summary.get("unknown_user_blocked"),
            "trino_runtime_security_smoke_security_probe_admin_unfiltered": trino_runtime_security_summary.get(
                "security_probe_admin_unfiltered"
            ),
            "trino_runtime_security_smoke_row_level_filter_enforced": trino_runtime_security_summary.get(
                "row_level_filter_enforced"
            ),
            "trino_runtime_security_smoke_column_masking_enforced": trino_runtime_security_summary.get(
                "column_masking_enforced"
            ),
            "trino_runtime_security_smoke_centralized_audit_sink_passed": trino_runtime_security_summary.get(
                "centralized_audit_sink_passed"
            ),
            "trino_runtime_security_smoke_audit_event_count": trino_runtime_security_summary.get(
                "runtime_security_audit_event_count", 0
            ),
            "trino_runtime_security_smoke_audit_failed_event_count": trino_runtime_security_summary.get(
                "runtime_security_audit_failed_event_count", 0
            ),
            "trino_runtime_security_smoke_all_access_denied_errors_verified": trino_runtime_security_summary.get(
                "all_access_denied_errors_verified"
            ),
            "trino_runtime_security_smoke_not_covered": trino_runtime_security_scope.get("not_covered", []),
            "policy_decision_smoke_attached": policy_decision_report is not None,
            "policy_decision_smoke_passed": policy_decision_report.get("passed") if policy_decision_report else None,
            "policy_decision_smoke_pdp": policy_decision_summary.get("pdp"),
            "policy_decision_smoke_decision_api_reachable": policy_decision_summary.get("decision_api_reachable"),
            "policy_decision_smoke_finance_reader_allowed": policy_decision_summary.get("finance_reader_allowed"),
            "policy_decision_smoke_unauthorized_default_denied": policy_decision_summary.get(
                "unauthorized_default_denied"
            ),
            "policy_decision_smoke_row_filter_decision_present": policy_decision_summary.get(
                "row_filter_decision_present"
            ),
            "policy_decision_smoke_column_mask_decision_present": policy_decision_summary.get(
                "column_mask_decision_present"
            ),
            "policy_decision_smoke_policy_admin_approval_passed": policy_decision_summary.get(
                "policy_admin_approval_passed"
            ),
            "policy_decision_smoke_policy_admin_self_approval_denied": policy_decision_summary.get(
                "policy_admin_self_approval_denied"
            ),
            "policy_decision_smoke_policy_admin_missing_evidence_denied": policy_decision_summary.get(
                "policy_admin_missing_evidence_denied"
            ),
            "policy_decision_smoke_audit_sink_passed": policy_decision_summary.get("audit_sink_passed"),
            "policy_decision_smoke_audit_event_count": policy_decision_summary.get("audit_event_count", 0),
            "policy_decision_smoke_failed_check_count": policy_decision_summary.get("failed_check_count", 0),
            "policy_decision_smoke_not_covered": policy_decision_scope.get("not_covered", []),
            "oidc_auth_smoke_attached": oidc_auth_report is not None,
            "oidc_auth_smoke_passed": oidc_auth_report.get("passed") if oidc_auth_report else None,
            "oidc_auth_smoke_issuer": oidc_auth_summary.get("issuer"),
            "oidc_auth_smoke_audience": oidc_auth_summary.get("audience"),
            "oidc_auth_smoke_required_role": oidc_auth_summary.get("required_role"),
            "oidc_auth_smoke_jwks_key_published": oidc_auth_summary.get("jwks_key_published"),
            "oidc_auth_smoke_rs256_signature_validation_passed": oidc_auth_summary.get(
                "rs256_signature_validation_passed"
            ),
            "oidc_auth_smoke_issuer_validation_passed": oidc_auth_summary.get("issuer_validation_passed"),
            "oidc_auth_smoke_audience_validation_passed": oidc_auth_summary.get("audience_validation_passed"),
            "oidc_auth_smoke_expiry_validation_passed": oidc_auth_summary.get("expiry_validation_passed"),
            "oidc_auth_smoke_required_role_denied": oidc_auth_summary.get("required_role_denied"),
            "oidc_auth_smoke_unknown_kid_denied": oidc_auth_summary.get("unknown_kid_denied"),
            "oidc_auth_smoke_missing_token_denied": oidc_auth_summary.get("missing_token_denied"),
            "oidc_auth_smoke_audit_sink_passed": oidc_auth_summary.get("audit_sink_passed"),
            "oidc_auth_smoke_audit_event_count": oidc_auth_summary.get("audit_event_count", 0),
            "oidc_auth_smoke_raw_access_tokens_persisted": oidc_auth_summary.get("raw_access_tokens_persisted"),
            "oidc_auth_smoke_failed_check_count": oidc_auth_summary.get("failed_check_count", 0),
            "oidc_auth_smoke_not_covered": oidc_auth_scope.get("not_covered", []),
            "access_privacy_release_gate_passed": access_privacy_release_gate_passed,
            "secret_rotation_smoke_attached": secret_rotation_report is not None,
            "secret_rotation_smoke_passed": secret_rotation_report.get("passed")
            if secret_rotation_report
            else None,
            "secret_rotation_smoke_secret_manager_mode": secret_rotation_summary.get("secret_manager_mode"),
            "secret_rotation_smoke_service_identity_count": secret_rotation_summary.get(
                "service_identity_count",
                0,
            ),
            "secret_rotation_smoke_rotated_secret_count": secret_rotation_summary.get("rotated_secret_count", 0),
            "secret_rotation_smoke_active_version_advanced": secret_rotation_summary.get("active_version_advanced"),
            "secret_rotation_smoke_old_versions_revoked": secret_rotation_summary.get("old_versions_revoked"),
            "secret_rotation_smoke_new_versions_readable": secret_rotation_summary.get("new_versions_readable"),
            "secret_rotation_smoke_unauthorized_identity_denied": secret_rotation_summary.get(
                "unauthorized_identity_denied"
            ),
            "secret_rotation_smoke_missing_secret_denied": secret_rotation_summary.get("missing_secret_denied"),
            "secret_rotation_smoke_orchestrator_service_identity_used": secret_rotation_summary.get(
                "orchestrator_service_identity_used"
            ),
            "secret_rotation_smoke_orchestrator_run_id_present": secret_rotation_summary.get(
                "orchestrator_run_id_present"
            ),
            "secret_rotation_smoke_orchestrator_secret_injection_passed": secret_rotation_summary.get(
                "orchestrator_secret_injection_passed"
            ),
            "secret_rotation_smoke_orchestrator_injection_manifest_redacted": secret_rotation_summary.get(
                "orchestrator_injection_manifest_redacted"
            ),
            "secret_rotation_smoke_plaintext_secret_material_persisted": secret_rotation_summary.get(
                "plaintext_secret_material_persisted"
            ),
            "secret_rotation_smoke_audit_sink_passed": secret_rotation_summary.get("audit_sink_passed"),
            "secret_rotation_smoke_audit_event_count": secret_rotation_summary.get("audit_event_count", 0),
            "secret_rotation_smoke_failed_check_count": secret_rotation_summary.get("failed_check_count", 0),
            "secret_rotation_smoke_not_covered": secret_rotation_scope.get("not_covered", []),
            "secret_rotation_ops_attached": secret_rotation_ops_report is not None,
            "secret_rotation_ops_passed": secret_rotation_ops_report.get("passed")
            if secret_rotation_ops_report
            else None,
            "secret_rotation_ops_environment": secret_rotation_ops_report.get("environment")
            if secret_rotation_ops_report
            else None,
            "secret_rotation_ops_readiness_state": secret_rotation_ops_report.get("readiness_state")
            if secret_rotation_ops_report
            else None,
            "secret_rotation_ops_mode": secret_rotation_ops_report.get("mode")
            if secret_rotation_ops_report
            else None,
            "secret_rotation_ops_p0_service_count": secret_rotation_ops_summary.get("p0_service_count", 0),
            "secret_rotation_ops_covered_service_count": secret_rotation_ops_summary.get("covered_service_count", 0),
            "secret_rotation_ops_failed_service_count": secret_rotation_ops_summary.get("failed_service_count", 0),
            "secret_rotation_ops_failed_check_count": secret_rotation_ops_summary.get("failed_check_count", 0),
            "secret_rotation_ops_managed_secret_manager_ha": secret_rotation_ops_summary.get(
                "managed_secret_manager_ha"
            ),
            "secret_rotation_ops_kms_hsm_custody": secret_rotation_ops_summary.get("kms_hsm_custody"),
            "secret_rotation_ops_audit_sink_siem_exported": secret_rotation_ops_summary.get(
                "audit_sink_siem_exported"
            ),
            "secret_rotation_ops_release_gate_passed": secret_rotation_ops_release_gate_passed,
            "dagster_orchestration_smoke_attached": dagster_orchestration_report is not None,
            "dagster_orchestration_smoke_passed": dagster_orchestration_report.get("passed")
            if dagster_orchestration_report
            else None,
            "dagster_orchestration_smoke_failed_check_count": dagster_orchestration_summary.get("failed_check_count", 0),
            "dagster_orchestration_smoke_job_name": dagster_orchestration_summary.get("job_name"),
            "dagster_orchestration_smoke_run_id": dagster_orchestration_summary.get("run_id"),
            "dagster_orchestration_smoke_run_status": dagster_orchestration_summary.get("run_status"),
            "dagster_orchestration_smoke_event_count": dagster_orchestration_summary.get("event_count", 0),
            "dagster_orchestration_smoke_op_success_count": dagster_orchestration_summary.get("op_success_count", 0),
            "dagster_orchestration_smoke_validated_report_count": dagster_orchestration_summary.get("validated_report_count", 0),
            "dagster_orchestration_smoke_not_covered": dagster_orchestration_scope.get("not_covered", []),
            "dagster_day2_smoke_attached": dagster_day2_report is not None,
            "dagster_day2_smoke_passed": dagster_day2_report.get("passed") if dagster_day2_report else None,
            "dagster_day2_smoke_failed_check_count": dagster_day2_summary.get("failed_check_count", 0),
            "dagster_day2_smoke_job_name": dagster_day2_summary.get("job_name"),
            "dagster_day2_smoke_run_id": dagster_day2_summary.get("run_id"),
            "dagster_day2_smoke_run_status": dagster_day2_summary.get("run_status"),
            "dagster_day2_smoke_schedule_tick_count": dagster_day2_summary.get("schedule_tick_count", 0),
            "dagster_day2_smoke_schedule_tick_history_passed": dagster_day2_summary.get(
                "schedule_tick_history_passed"
            ),
            "dagster_day2_smoke_retry_event_count": dagster_day2_summary.get("retry_event_count", 0),
            "dagster_day2_smoke_retry_restart_count": dagster_day2_summary.get("retry_restart_count", 0),
            "dagster_day2_smoke_retry_policy_max_retries": dagster_day2_summary.get(
                "retry_policy_max_retries",
                0,
            ),
            "dagster_day2_smoke_retry_policy_backoff_seconds": dagster_day2_summary.get(
                "retry_policy_backoff_seconds",
                0,
            ),
            "dagster_day2_smoke_retry_policy_verified": dagster_day2_summary.get("retry_policy_verified"),
            "dagster_day2_smoke_backfill_partition_count": dagster_day2_summary.get("backfill_partition_count", 0),
            "dagster_day2_smoke_asset_materialization_event_count": dagster_day2_summary.get(
                "asset_materialization_event_count",
                0,
            ),
            "dagster_day2_smoke_backfill_materialization_history_passed": dagster_day2_summary.get(
                "backfill_materialization_history_passed"
            ),
            "dagster_day2_smoke_distributed_executor_verified": dagster_day2_summary.get(
                "distributed_executor_verified"
            ),
            "dagster_day2_smoke_not_covered": dagster_day2_scope.get("not_covered", []),
            "dagster_day2_release_gate_passed": dagster_day2_release_gate_passed,
            "portfolio_release_smoke_attached": portfolio_report is not None,
            "portfolio_release_smoke_passed": portfolio_report.get("passed") if portfolio_report else None,
            "portfolio_release_smoke_release_evidence_count": portfolio_summary.get("release_evidence_count", 0),
            "portfolio_release_smoke_passed_release_count": portfolio_summary.get("passed_release_count", 0),
            "portfolio_release_smoke_covered_gold_count": portfolio_summary.get("covered_gold_count", 0),
            "portfolio_release_smoke_gold_count": portfolio_summary.get("gold_count", 0),
            "portfolio_release_smoke_missing_gold_outputs": portfolio_summary.get("missing_gold_outputs", []),
            "portfolio_release_smoke_final_control_tower_blocker_count": portfolio_summary.get("final_control_tower_blocker_count", 0),
            "portfolio_release_smoke_final_gold_release_blocker_count": portfolio_summary.get("final_gold_release_blocker_count", 0),
            "portfolio_release_smoke_final_runtime_lineage_blocker_count": portfolio_summary.get("final_runtime_lineage_blocker_count", 0),
            "portfolio_release_smoke_final_source_activation_blocker_count": portfolio_summary.get("final_source_activation_blocker_count", 0),
            "portfolio_release_smoke_source_activation_count": portfolio_summary.get("source_activation_count", 0),
            "portfolio_release_smoke_source_activation_passed_count": portfolio_summary.get("source_activation_passed_count", 0),
            "portfolio_release_smoke_source_activation_ops_passed": portfolio_summary.get("source_activation_ops_passed"),
            "portfolio_release_smoke_not_covered": portfolio_scope.get("not_covered", []),
            "workload_benchmark_attached": workload_benchmark_report is not None,
            "workload_benchmark_passed": workload_benchmark_report.get("passed")
            if workload_benchmark_report
            else None,
            "workload_benchmark_environment": workload_benchmark_report.get("environment")
            if workload_benchmark_report
            else None,
            "workload_benchmark_release_gate_passed": workload_benchmark_release_gate_passed,
            "workload_benchmark_scale_profile": workload_benchmark_summary.get("scale_profile"),
            "workload_benchmark_input_record_count": workload_benchmark_summary.get("input_record_count", 0),
            "workload_benchmark_duration_minutes": workload_benchmark_summary.get("duration_minutes", 0),
            "workload_benchmark_throughput_records_per_second": workload_benchmark_summary.get(
                "throughput_records_per_second",
                0,
            ),
            "workload_benchmark_query_concurrency": workload_benchmark_summary.get("query_concurrency", 0),
            "workload_benchmark_p95_query_latency_ms": workload_benchmark_summary.get("p95_query_latency_ms", 0),
            "workload_benchmark_max_consumer_lag_records": workload_benchmark_summary.get(
                "max_consumer_lag_records",
                0,
            ),
            "workload_benchmark_error_rate": workload_benchmark_summary.get("error_rate", 1),
            "control_tower_passed": control_tower_report.get("passed"),
            "control_tower_blocker_count": control_summary.get("blocker_count", 0),
            "non_infra_control_tower_blocker_count": len(non_infra_blockers),
            "live_infra_or_capability_blocker_count": max(
                int_value(control_summary.get("blocker_count", 0)) - len(non_infra_blockers),
                0,
            ),
            "data_plane_smoke_blocker_count": control_summary.get("data_plane_smoke_blocker_count", 0),
            "capability_blocker_count": control_summary.get("capability_blocker_count", 0),
            "data_product_blocker_count": control_summary.get("data_product_blocker_count", 0),
            "runtime_readiness_passed": runtime_report.get("passed"),
            "runtime_readiness_external_attached": runtime_external_attached,
            "runtime_readiness_environment": runtime_report.get("environment"),
            "runtime_readiness_state": runtime_report.get("readiness_state"),
            "runtime_readiness_failed_gate_count": runtime_summary.get("failed_gate_count", 0),
            "runtime_readiness_failure_count": len(runtime_report.get("failures", []))
            if isinstance(runtime_report.get("failures"), list)
            else 0,
            "runtime_readiness_input_count": len(runtime_inputs),
            "runtime_iac_release_gate_passed": runtime_iac_release_gate_passed,
            "runtime_deployed_service_count": runtime_summary.get("deployed_service_count", 0),
            "runtime_required_p0_service_count": runtime_summary.get("required_p0_service_count", 0),
            "capability_p0_ready": capability_report.get("p0_ready"),
            "capability_summary": capability_summary,
        },
        "p0_gap_backlog": p0_gap_backlog(
            control_tower_report=control_tower_report,
            runtime_report=runtime_report,
            smoke_not_covered=smoke_scope.get("not_covered", []),
            event_backbone_report=event_backbone_report,
            ingestion_runtime_report=ingestion_runtime_report,
            catalog_lineage_ops_report=catalog_lineage_ops_report,
            semantic_metric_serving_ops_report=semantic_metric_serving_ops_report,
            source_activation_ops_report=source_activation_ops_report,
            backfill_readiness_report=backfill_readiness_report,
            schema_registry_runtime_report=schema_registry_runtime_report,
            schema_registry_attestation_verification=schema_registry_attestation_verification,
            schema_registry_ops_report=schema_registry_ops_report,
            schema_registry_auth_report=schema_registry_auth_report,
            schema_registry_storage_report=schema_registry_storage_report,
            broker_acl_report=broker_acl_report,
            transactional_outbox_report=transactional_outbox_report,
            live_bronze_ingestion_report=live_bronze_ingestion_report,
            orchestrated_publication_report=orchestrated_publication_report,
            live_quality_slo_report=live_quality_slo_report,
            live_lakehouse_report=live_lakehouse_report,
            iceberg_catalog_report=iceberg_catalog_report,
            object_store_report=object_store_report,
            trino_sql_report=trino_sql_report,
            trino_iceberg_minio_report=trino_iceberg_minio_report,
            catalog_cross_engine_report=catalog_cross_engine_report,
            catalog_runtime_ops_report=catalog_runtime_ops_report,
            orchestration_runtime_ops_report=orchestration_runtime_ops_report,
            trino_runtime_security_report=trino_runtime_security_report,
            policy_decision_report=policy_decision_report,
            oidc_auth_report=oidc_auth_report,
            secret_rotation_report=secret_rotation_report,
            secret_rotation_ops_report=secret_rotation_ops_report,
            dagster_orchestration_report=dagster_orchestration_report,
            dagster_day2_report=dagster_day2_report,
            portfolio_report=portfolio_report,
            workload_benchmark_report=workload_benchmark_report,
        ),
    }
    manifest["pack_id"] = stable_id(
        "production-review-pack",
        environment,
        generated_at,
        manifest["artifacts"],
        manifest["summary"],
    )
    return manifest


def non_infra_control_tower_blockers(control_tower_report: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = control_tower_report.get("blockers")
    if not isinstance(blockers, list):
        return []
    return [
        blocker
        for blocker in blockers
        if isinstance(blocker, dict) and blocker.get("gate") != "p0_capability_target_met"
    ]


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def numeric_value(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def strict_workload_benchmark_release_gate_passed(
    report: dict[str, Any] | None,
    *,
    target_environment: str,
) -> bool:
    if not isinstance(report, dict):
        return False
    summary = report.get("summary")
    evidence = report.get("evidence")
    if not isinstance(summary, dict) or not isinstance(evidence, dict):
        return False
    source_hash = evidence.get("source_artifact_hash")
    return (
        report.get("artifact_type") == "workload_benchmark_report.v1"
        and report.get("environment") == target_environment
        and target_environment in {"staging", "prod"}
        and report.get("passed") is True
        and report.get("source_kind") in {"ci_tool_output", "external_attestation"}
        and isinstance(evidence.get("source_artifact_uri"), str)
        and bool(str(evidence.get("source_artifact_uri")).strip())
        and isinstance(source_hash, str)
        and source_hash.startswith("sha256:")
        and len(source_hash.removeprefix("sha256:")) == 64
        and summary.get("scale_profile") in {"managed_staging", "production_like", "production"}
        and isinstance(summary.get("target_use_case"), str)
        and bool(str(summary.get("target_use_case")).strip())
        and int_value(summary.get("input_record_count", 0)) >= 1_000_000
        and numeric_value(summary.get("duration_minutes", 0)) >= 10
        and numeric_value(summary.get("throughput_records_per_second", 0)) >= 1_000
        and int_value(summary.get("query_concurrency", 0)) >= 25
        and numeric_value(summary.get("p95_query_latency_ms", 9_999_999)) <= 3_000
        and int_value(summary.get("max_consumer_lag_records", 9_999_999)) <= 1_000
        and numeric_value(summary.get("error_rate", 1.0)) <= 0.001
        and summary.get("freshness_slo_passed") is True
        and summary.get("zero_data_loss_verified") is True
    )


def secret_rotation_ops_closes_gap(gap: str, release_gate_passed: bool) -> bool:
    return release_gate_passed and gap in {
        "production_secret_rotation",
        "production_connector_secret_rotation",
        "production_cloud_kms_key_rotation",
        "cloud_kms_or_hsm_key_custody",
        "managed_secret_manager_ha",
        "workload_identity_federation_to_cloud",
        "automatic_rotation_scheduler",
        "cross_region_secret_replication",
        "siem_audit_export",
    }


def strict_access_privacy_release_gate_passed(
    *,
    trino_runtime_security_report: dict[str, Any] | None,
    policy_decision_report: dict[str, Any] | None,
    oidc_auth_report: dict[str, Any] | None,
) -> bool:
    trino_summary = (
        trino_runtime_security_report.get("summary")
        if isinstance(trino_runtime_security_report, dict)
        and isinstance(trino_runtime_security_report.get("summary"), dict)
        else {}
    )
    policy_summary = (
        policy_decision_report.get("summary")
        if isinstance(policy_decision_report, dict) and isinstance(policy_decision_report.get("summary"), dict)
        else {}
    )
    oidc_summary = (
        oidc_auth_report.get("summary")
        if isinstance(oidc_auth_report, dict) and isinstance(oidc_auth_report.get("summary"), dict)
        else {}
    )
    trino_passed = (
        trino_runtime_security_report is not None
        and trino_runtime_security_report.get("artifact_type") == "trino_runtime_security_smoke_report.v1"
        and trino_runtime_security_report.get("passed") is True
        and int_value(trino_summary.get("source_row_count", 0)) > 0
        and trino_summary.get("allowed_query_passed") is True
        and trino_summary.get("allowed_write_blocked") is True
        and trino_summary.get("denied_query_blocked") is True
        and trino_summary.get("unknown_user_blocked") is True
        and trino_summary.get("security_probe_admin_unfiltered") is True
        and trino_summary.get("row_level_filter_enforced") is True
        and trino_summary.get("column_masking_enforced") is True
        and trino_summary.get("centralized_audit_sink_passed") is True
        and trino_summary.get("all_access_denied_errors_verified") is True
        and int_value(trino_summary.get("runtime_security_audit_event_count", 0)) >= 8
        and int_value(trino_summary.get("runtime_security_audit_failed_event_count", 0)) == 0
        and int_value(trino_summary.get("failed_check_count", 0)) == 0
    )
    policy_passed = (
        policy_decision_report is not None
        and policy_decision_report.get("artifact_type") == "policy_decision_smoke_report.v1"
        and policy_decision_report.get("passed") is True
        and policy_summary.get("pdp") == "opa"
        and policy_summary.get("decision_api_reachable") is True
        and policy_summary.get("finance_reader_allowed") is True
        and policy_summary.get("unauthorized_default_denied") is True
        and policy_summary.get("row_filter_decision_present") is True
        and policy_summary.get("column_mask_decision_present") is True
        and policy_summary.get("policy_admin_approval_passed") is True
        and policy_summary.get("policy_admin_self_approval_denied") is True
        and policy_summary.get("policy_admin_missing_evidence_denied") is True
        and policy_summary.get("audit_sink_passed") is True
        and int_value(policy_summary.get("audit_event_count", 0)) >= 6
        and int_value(policy_summary.get("failed_check_count", 0)) == 0
    )
    oidc_passed = (
        oidc_auth_report is not None
        and oidc_auth_report.get("artifact_type") == "oidc_auth_smoke_report.v1"
        and oidc_auth_report.get("passed") is True
        and oidc_summary.get("jwks_key_published") is True
        and oidc_summary.get("rs256_signature_validation_passed") is True
        and oidc_summary.get("issuer_validation_passed") is True
        and oidc_summary.get("audience_validation_passed") is True
        and oidc_summary.get("expiry_validation_passed") is True
        and oidc_summary.get("required_role_denied") is True
        and oidc_summary.get("unknown_kid_denied") is True
        and oidc_summary.get("missing_token_denied") is True
        and oidc_summary.get("audit_sink_passed") is True
        and oidc_summary.get("raw_access_tokens_persisted") is False
        and int_value(oidc_summary.get("failed_check_count", 0)) == 0
    )
    return trino_passed and policy_passed and oidc_passed


def strict_dagster_day2_release_gate_passed(dagster_day2_report: dict[str, Any] | None) -> bool:
    summary = (
        dagster_day2_report.get("summary")
        if isinstance(dagster_day2_report, dict) and isinstance(dagster_day2_report.get("summary"), dict)
        else {}
    )
    backfill_partition_count = int_value(summary.get("backfill_partition_count", 0))
    materialization_event_count = int_value(summary.get("asset_materialization_event_count", 0))
    return (
        dagster_day2_report is not None
        and dagster_day2_report.get("artifact_type") == "dagster_day2_smoke_report.v1"
        and dagster_day2_report.get("passed") is True
        and summary.get("run_status") == "SUCCESS"
        and int_value(summary.get("schedule_tick_count", 0)) >= 1
        and summary.get("schedule_tick_history_passed") is True
        and int_value(summary.get("retry_policy_max_retries", 0)) >= 2
        and int_value(summary.get("retry_policy_backoff_seconds", 0)) > 0
        and int_value(summary.get("retry_event_count", 0)) >= 1
        and int_value(summary.get("retry_restart_count", 0)) >= 1
        and summary.get("retry_policy_verified") is True
        and backfill_partition_count >= 3
        and materialization_event_count >= backfill_partition_count
        and summary.get("backfill_materialization_history_passed") is True
        and summary.get("distributed_executor_verified") is False
        and int_value(summary.get("failed_check_count", 0)) == 0
    )


def strict_schema_registry_release_gate_passed(schema_registry_ops_report: dict[str, Any] | None) -> bool:
    if not isinstance(schema_registry_ops_report, dict):
        return False
    summary = (
        schema_registry_ops_report.get("summary")
        if isinstance(schema_registry_ops_report.get("summary"), dict)
        else {}
    )
    publication_evidence = (
        schema_registry_ops_report.get("publication_evidence")
        if isinstance(schema_registry_ops_report.get("publication_evidence"), dict)
        else {}
    )
    attestation = (
        schema_registry_ops_report.get("attestation")
        if isinstance(schema_registry_ops_report.get("attestation"), dict)
        else {}
    )
    attestation_required = attestation.get("required") if isinstance(attestation.get("required"), dict) else {}
    checks = schema_registry_ops_report.get("checks") if isinstance(schema_registry_ops_report.get("checks"), list) else []
    subjects = (
        schema_registry_ops_report.get("subjects")
        if isinstance(schema_registry_ops_report.get("subjects"), list)
        else []
    )
    subject_count = int_value(summary.get("subject_count", 0))
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
    all_checks_passed = (
        bool(checks)
        and all(isinstance(check, dict) and check.get("passed") is True for check in checks)
        and required_checks.issubset(passed_check_names)
    )
    p0_subject_count = int_value(summary.get("p0_subject_count", 0))
    p0_subject_rows = [
        subject
        for subject in subjects
        if isinstance(subject, dict) and schema_registry_subject_has_p0_source(subject)
    ]
    all_subjects_passed = bool(subjects) and all(
        schema_registry_subject_row_release_ready(subject)
        for subject in subjects
        if isinstance(subject, dict)
    )
    return (
        schema_registry_ops_report.get("artifact_type") == "schema_registry_ops_report.v1"
        and schema_registry_ops_report.get("capability_id") == "schema-registry-compatibility"
        and schema_registry_ops_report.get("environment") in {"staging", "prod"}
        and isinstance(schema_registry_ops_report.get("release_id"), str)
        and bool(str(schema_registry_ops_report.get("release_id")).strip())
        and schema_registry_ops_report.get("readiness_state") == "production_like_ready"
        and schema_registry_ops_report.get("mode") == "external_registry_evidence"
        and schema_registry_ops_report.get("passed") is True
        and subject_count > 0
        and len(subjects) == subject_count
        and int_value(summary.get("passed_subject_count", 0)) == subject_count
        and int_value(summary.get("failed_subject_count", 0)) == 0
        and p0_subject_count > 0
        and len(p0_subject_rows) == p0_subject_count
        and int_value(summary.get("p0_failed_subject_count", 0)) == 0
        and int_value(summary.get("global_failed_check_count", 0)) == 0
        and summary.get("publication_evidence_attached") is True
        and int_value(summary.get("producer_enforcement_gap_count", 0)) == 0
        and int_value(summary.get("broker_validation_gap_count", 0)) == 0
        and publication_evidence.get("attached") is True
        and publication_evidence.get("artifact_type") == "schema_registry_publication_manifest.v1"
        and publication_evidence.get("environment") == schema_registry_ops_report.get("environment")
        and sha256_value_valid(publication_evidence.get("hash"))
        and isinstance(publication_evidence.get("registry_uri"), str)
        and publication_evidence.get("registry_uri", "").startswith("https://")
        and attestation.get("attached") is True
        and attestation.get("passed") is True
        and attestation.get("subject_hash") == publication_evidence.get("hash")
        and attestation_required.get("signature_verified") is True
        and attestation_required.get("subject_hash_matches") is True
        and all_checks_passed
        and all_subjects_passed
    )


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


def strict_catalog_lineage_release_gate_passed(
    catalog_lineage_ops_report: dict[str, Any] | None,
    *,
    target_environment: str,
) -> bool:
    if not isinstance(catalog_lineage_ops_report, dict):
        return False
    summary = (
        catalog_lineage_ops_report.get("summary")
        if isinstance(catalog_lineage_ops_report.get("summary"), dict)
        else {}
    )
    inputs = (
        catalog_lineage_ops_report.get("inputs")
        if isinstance(catalog_lineage_ops_report.get("inputs"), dict)
        else {}
    )
    catalog_input = inputs.get("catalog_bundle") if isinstance(inputs.get("catalog_bundle"), dict) else {}
    publish_input = inputs.get("catalog_publish_manifest") if isinstance(inputs.get("catalog_publish_manifest"), dict) else {}
    lineage_input = inputs.get("openlineage_events") if isinstance(inputs.get("openlineage_events"), dict) else {}
    receipt_input = inputs.get("publish_receipt") if isinstance(inputs.get("publish_receipt"), dict) else {}
    checks = catalog_lineage_ops_report.get("checks") if isinstance(catalog_lineage_ops_report.get("checks"), list) else []
    data_products = (
        catalog_lineage_ops_report.get("data_products")
        if isinstance(catalog_lineage_ops_report.get("data_products"), list)
        else []
    )
    data_product_count = int_value(summary.get("data_product_count", 0))
    all_checks_passed = bool(checks) and all(
        isinstance(check, dict) and check.get("passed") is True
        for check in checks
    )
    passed_check_names = {
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is True
    }
    required_check_names = {
        "catalog_publish_manifest_attached_for_production_like",
        "catalog_publish_manifest_artifact_type_valid",
        "catalog_publish_manifest_passed",
        "catalog_publish_manifest_validation_passed",
        "catalog_hash_matches_publish_manifest",
        "catalog_publish_environment_matches",
        "production_publish_endpoint_declared",
        "production_requested_by_declared",
        "production_change_ticket_declared",
        "openlineage_attached_for_production_like",
        "openlineage_jsonl_parse_passed",
        "openlineage_events_valid",
        "openlineage_events_non_empty_for_production_like",
        "openlineage_hash_matches_publish_manifest",
        "production_openlineage_namespace_not_local",
        "production_openlineage_producer_not_local",
        "publish_receipt_attached_for_production_like",
        "publish_receipt_artifact_type_valid",
        "publish_receipt_environment_matches",
        "publish_receipt_status_succeeded",
        "publish_receipt_catalog_hash_matches",
        "publish_receipt_manifest_hash_matches",
        "publish_receipt_openlineage_hash_matches",
        "publish_receipt_target_matches",
    }
    all_products_passed = bool(data_products) and all(
        isinstance(row, dict) and row.get("passed") is True
        for row in data_products
    )
    return (
        catalog_lineage_ops_report.get("artifact_type") == "catalog_lineage_ops_report.v1"
        and catalog_lineage_ops_report.get("capability_id") == "catalog-lineage-control-plane"
        and catalog_lineage_ops_report.get("environment") in {"staging", "prod"}
        and catalog_lineage_ops_report.get("environment") == target_environment
        and catalog_lineage_ops_report.get("readiness_state") == "production_like_ready"
        and catalog_lineage_ops_report.get("mode") == "runtime_attested"
        and catalog_lineage_ops_report.get("passed") is True
        and data_product_count > 0
        and int_value(summary.get("failed_product_count", 0)) == 0
        and int_value(summary.get("global_failed_check_count", 0)) == 0
        and summary.get("catalog_publish_status") == "READY"
        and summary.get("catalog_publish_manifest_attached") is True
        and summary.get("openlineage_attached") is True
        and int_value(summary.get("openlineage_event_count", 0)) > 0
        and summary.get("publish_receipt_attached") is True
        and int_value(summary.get("owner_steward_gap_count", 0)) == 0
        and int_value(summary.get("static_lineage_gap_count", 0)) == 0
        and int_value(summary.get("runtime_lineage_gap_count", 0)) == 0
        and catalog_input.get("attached") is True
        and publish_input.get("attached") is True
        and publish_input.get("environment") == catalog_lineage_ops_report.get("environment")
        and lineage_input.get("attached") is True
        and int_value(lineage_input.get("event_count", 0)) > 0
        and not lineage_input.get("parse_errors")
        and receipt_input.get("attached") is True
        and receipt_input.get("environment") == catalog_lineage_ops_report.get("environment")
        and receipt_input.get("passed") is not False
        and all_checks_passed
        and required_check_names.issubset(passed_check_names)
        and all_products_passed
    )


def strict_semantic_metric_serving_release_gate_passed(
    semantic_metric_serving_ops_report: dict[str, Any] | None,
    *,
    target_environment: str,
) -> bool:
    if not isinstance(semantic_metric_serving_ops_report, dict):
        return False
    summary = (
        semantic_metric_serving_ops_report.get("summary")
        if isinstance(semantic_metric_serving_ops_report.get("summary"), dict)
        else {}
    )
    inputs = (
        semantic_metric_serving_ops_report.get("inputs")
        if isinstance(semantic_metric_serving_ops_report.get("inputs"), dict)
        else {}
    )
    registry_input = inputs.get("semantic_metric_registry") if isinstance(inputs.get("semantic_metric_registry"), dict) else {}
    manifest_input = inputs.get("semantic_view_manifest") if isinstance(inputs.get("semantic_view_manifest"), dict) else {}
    certification_input = (
        inputs.get("metric_certification_report")
        if isinstance(inputs.get("metric_certification_report"), dict)
        else {}
    )
    deployment_input = (
        inputs.get("serving_deployment_evidence")
        if isinstance(inputs.get("serving_deployment_evidence"), dict)
        else {}
    )
    usage_input = inputs.get("usage_evidence") if isinstance(inputs.get("usage_evidence"), dict) else {}
    checks = (
        semantic_metric_serving_ops_report.get("checks")
        if isinstance(semantic_metric_serving_ops_report.get("checks"), list)
        else []
    )
    metrics = (
        semantic_metric_serving_ops_report.get("metrics")
        if isinstance(semantic_metric_serving_ops_report.get("metrics"), list)
        else []
    )
    metric_count = int_value(summary.get("metric_count", 0))
    all_checks_passed = bool(checks) and all(
        isinstance(check, dict) and check.get("passed") is True
        for check in checks
    )
    passed_check_names = {
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("passed") is True
    }
    required_check_names = {
        "environment_supported",
        "semantic_metric_registry_attached",
        "semantic_metric_registry_valid",
        "semantic_view_manifest_attached_for_production_like",
        "semantic_view_manifest_artifact_type_valid",
        "semantic_view_manifest_valid",
        "semantic_view_manifest_registry_hash_matches",
        "metric_certification_report_attached_for_production_like",
        "metric_certification_artifact_type_valid",
        "metric_certification_environment_matches",
        "metric_certification_registry_hash_matches",
        "metric_certification_report_passed",
        "serving_deployment_evidence_attached_for_production_like",
        "serving_deployment_artifact_type_valid",
        "serving_deployment_environment_matches",
        "serving_deployment_manifest_hash_matches",
        "serving_deployment_passed",
        "usage_evidence_attached_for_production_like",
        "usage_evidence_artifact_type_valid",
        "usage_evidence_environment_matches",
        "usage_tracking_enabled",
    }
    all_metrics_passed = bool(metrics) and all(
        isinstance(metric, dict)
        and metric.get("passed") is True
        and metric.get("status") == "certified"
        and isinstance(metric.get("certification"), dict)
        and metric["certification"].get("attached") is True
        and metric["certification"].get("status") == "approved"
        and int_value(metric.get("view_count", 0)) > 0
        and int_value(metric.get("deployment_view_count", 0)) >= int_value(metric.get("view_count", 0))
        and isinstance(metric.get("usage"), dict)
        and metric["usage"].get("attached") is True
        and metric["usage"].get("usage_tracking_enabled") is True
        for metric in metrics
    )
    deployment_summary = (
        deployment_input.get("summary")
        if isinstance(deployment_input.get("summary"), dict)
        else {}
    )
    usage_summary = usage_input.get("summary") if isinstance(usage_input.get("summary"), dict) else {}
    return (
        semantic_metric_serving_ops_report.get("artifact_type") == "semantic_metric_serving_ops_report.v1"
        and semantic_metric_serving_ops_report.get("capability_id") == "semantic-metric-serving"
        and semantic_metric_serving_ops_report.get("environment") in {"staging", "prod"}
        and semantic_metric_serving_ops_report.get("environment") == target_environment
        and semantic_metric_serving_ops_report.get("readiness_state") == "production_like_ready"
        and semantic_metric_serving_ops_report.get("mode") == "runtime_attested"
        and semantic_metric_serving_ops_report.get("passed") is True
        and metric_count > 0
        and len(metrics) == metric_count
        and int_value(summary.get("failed_metric_count", 0)) == 0
        and int_value(summary.get("global_failed_check_count", 0)) == 0
        and int_value(summary.get("certified_metric_count", 0)) == metric_count
        and int_value(summary.get("certification_approved_metric_count", 0)) == metric_count
        and int_value(summary.get("metric_certification_gap_count", 0)) == 0
        and int_value(summary.get("serving_deployment_failed_count", 0)) == 0
        and int_value(summary.get("usage_tracking_gap_count", 0)) == 0
        and summary.get("certification_evidence_attached") is True
        and summary.get("deployment_evidence_attached") is True
        and summary.get("usage_evidence_attached") is True
        and registry_input.get("attached") is True
        and manifest_input.get("attached") is True
        and manifest_input.get("source") == "artifact"
        and manifest_input.get("artifact_type") == "semantic_views_manifest.v1"
        and int_value(manifest_input.get("metric_count", 0)) == metric_count
        and int_value(manifest_input.get("view_count", 0)) >= metric_count
        and certification_input.get("attached") is True
        and certification_input.get("source") == "artifact"
        and certification_input.get("artifact_type") == "semantic_metric_certification_report.v1"
        and certification_input.get("environment") == semantic_metric_serving_ops_report.get("environment")
        and certification_input.get("readiness_state") in {"certification_ready", "production_like_ready"}
        and certification_input.get("passed") is True
        and certification_input.get("metric_registry_hash") == registry_input.get("hash")
        and deployment_input.get("attached") is True
        and deployment_input.get("artifact_type") == "semantic_serving_deployment_evidence.v1"
        and deployment_input.get("environment") == semantic_metric_serving_ops_report.get("environment")
        and deployment_input.get("passed") is True
        and int_value(deployment_summary.get("failed_view_count", 0)) == 0
        and usage_input.get("attached") is True
        and usage_input.get("artifact_type") == "semantic_metric_usage_evidence.v1"
        and usage_input.get("environment") == semantic_metric_serving_ops_report.get("environment")
        and usage_input.get("passed") is True
        and int_value(usage_summary.get("usage_tracking_disabled_count", 0)) == 0
        and all_checks_passed
        and required_check_names.issubset(passed_check_names)
        and all_metrics_passed
    )


def strict_source_onboarding_release_gate_passed(
    source_activation_ops_report: dict[str, Any] | None,
    *,
    target_environment: str,
) -> bool:
    if not isinstance(source_activation_ops_report, dict):
        return False
    summary = (
        source_activation_ops_report.get("summary")
        if isinstance(source_activation_ops_report.get("summary"), dict)
        else {}
    )
    decision_board = (
        source_activation_ops_report.get("decision_board")
        if isinstance(source_activation_ops_report.get("decision_board"), dict)
        else {}
    )
    ledger = (
        source_activation_ops_report.get("ledger")
        if isinstance(source_activation_ops_report.get("ledger"), dict)
        else {}
    )
    source_registry = (
        source_activation_ops_report.get("source_registry")
        if isinstance(source_activation_ops_report.get("source_registry"), dict)
        else {}
    )
    sources = (
        source_activation_ops_report.get("sources")
        if isinstance(source_activation_ops_report.get("sources"), list)
        else []
    )
    p0_sources = [row for row in sources if isinstance(row, dict) and row.get("priority") == "P0"]
    source_count = int_value(summary.get("source_count", 0))
    p0_source_count = int_value(summary.get("p0_source_count", 0))
    decision_actions = (
        decision_board.get("next_actions")
        if isinstance(decision_board.get("next_actions"), list)
        else []
    )
    p0_next_actions = [
        action
        for action in decision_actions
        if isinstance(action, dict)
        and action.get("priority") == "P0"
        and action.get("action") != "no_action"
    ]
    current_registry_hash = source_registry.get("current_hash")
    all_p0_sources_ready = bool(p0_sources) and all(
        source_activation_p0_row_release_ready(row, current_registry_hash=current_registry_hash)
        for row in p0_sources
    )
    return (
        source_activation_ops_report.get("artifact_type") == "source_activation_ops_report.v1"
        and source_activation_ops_report.get("capability_id") == "source-onboarding"
        and source_activation_ops_report.get("environment") in {"staging", "prod"}
        and source_activation_ops_report.get("environment") == target_environment
        and source_activation_ops_report.get("mode") == "runtime_attested"
        and source_activation_ops_report.get("readiness_state") == "production_like_ready"
        and source_activation_ops_report.get("passed") is True
        and source_count > 0
        and p0_source_count > 0
        and len(p0_sources) == p0_source_count
        and int_value(summary.get("p0_active_count", 0)) == p0_source_count
        and int_value(summary.get("p0_unactivated_count", 0)) == 0
        and int_value(summary.get("p0_activation_gap_count", 0)) == 0
        and int_value(summary.get("p0_production_ready_count", 0)) == p0_source_count
        and int_value(summary.get("p0_runtime_readiness_attached_count", 0)) == p0_source_count
        and int_value(summary.get("p0_critical_issue_count", 0)) == 0
        and int_value(summary.get("critical_issue_count", 0)) == 0
        and int_value(summary.get("expired_count", 0)) == 0
        and int_value(summary.get("revoked_count", 0)) == 0
        and int_value(summary.get("pending_count", 0)) == 0
        and int_value(summary.get("failed_count", 0)) == 0
        and int_value(summary.get("stale_count", 0)) == 0
        and int_value(summary.get("registry_drift_count", 0)) == 0
        and int_value(summary.get("pointer_issue_count", 0)) == 0
        and int_value(summary.get("runtime_readiness_issue_count", 0)) == 0
        and int_value(summary.get("evidence_integrity_issue_count", 0)) == 0
        and int_value(summary.get("p0_evidence_integrity_issue_count", 0)) == 0
        and int_value(summary.get("p0_next_action_count", 0)) == 0
        and ledger.get("exists") is True
        and ledger.get("validation_passed") is True
        and sha256_value_valid(ledger.get("hash"))
        and sha256_value_valid(current_registry_hash)
        and not decision_board.get("critical_sources")
        and not p0_next_actions
        and all_p0_sources_ready
    )


def required_backfill_readiness_evidence_keys() -> tuple[str, ...]:
    return (
        "backfill_plan",
        "active_pointer",
        "dry_run",
        "quality",
        "data_diff",
        "source_offset_ledger",
        "snapshot",
        "release",
        "change_control",
    )


def strict_backfill_readiness_release_gate_passed(
    backfill_readiness_report: dict[str, Any] | None,
    *,
    target_environment: str,
) -> bool:
    if not isinstance(backfill_readiness_report, dict):
        return False
    summary = (
        backfill_readiness_report.get("summary")
        if isinstance(backfill_readiness_report.get("summary"), dict)
        else {}
    )
    evidence = (
        backfill_readiness_report.get("evidence")
        if isinstance(backfill_readiness_report.get("evidence"), dict)
        else {}
    )
    required_evidence_keys = required_backfill_readiness_evidence_keys()
    return (
        backfill_readiness_report.get("artifact_type") == "backfill_readiness_report.v1"
        and backfill_readiness_report.get("capability_id") == "backfill-change-governance"
        and backfill_readiness_report.get("environment") in {"staging", "prod"}
        and backfill_readiness_report.get("environment") == target_environment
        and backfill_readiness_report.get("mode") == "runtime_attested"
        and backfill_readiness_report.get("readiness_state") == "ready"
        and backfill_readiness_report.get("passed") is True
        and int_value(summary.get("failed_check_count", 0)) == 0
        and int_value(summary.get("attached_evidence_count", 0)) >= len(required_evidence_keys)
        and all(backfill_evidence_ref_release_ready(evidence.get(key)) for key in required_evidence_keys)
    )


def backfill_evidence_ref_release_ready(value: object) -> bool:
    return (
        isinstance(value, dict)
        and value.get("local") is True
        and isinstance(value.get("uri"), str)
        and bool(value.get("uri"))
        and sha256_value_valid(value.get("hash"))
    )


def strict_secret_rotation_ops_release_gate_passed(
    secret_rotation_ops_report: dict[str, Any] | None,
    *,
    target_environment: str,
) -> bool:
    if not isinstance(secret_rotation_ops_report, dict):
        return False
    summary = (
        secret_rotation_ops_report.get("summary")
        if isinstance(secret_rotation_ops_report.get("summary"), dict)
        else {}
    )
    evidence = (
        secret_rotation_ops_report.get("evidence")
        if isinstance(secret_rotation_ops_report.get("evidence"), dict)
        else {}
    )
    checks = (
        secret_rotation_ops_report.get("checks")
        if isinstance(secret_rotation_ops_report.get("checks"), list)
        else []
    )
    services = (
        secret_rotation_ops_report.get("services")
        if isinstance(secret_rotation_ops_report.get("services"), list)
        else []
    )
    p0_service_count = int_value(summary.get("p0_service_count", 0))
    all_checks_passed = bool(checks) and all(
        isinstance(check, dict) and check.get("passed") is True
        for check in checks
    )
    all_services_passed = bool(services) and all(
        secret_rotation_service_row_release_ready(row)
        for row in services
        if isinstance(row, dict)
    )
    return (
        secret_rotation_ops_report.get("artifact_type") == "secret_rotation_ops_report.v1"
        and secret_rotation_ops_report.get("capability_id") == "production-secret-rotation"
        and secret_rotation_ops_report.get("environment") in {"staging", "prod"}
        and secret_rotation_ops_report.get("environment") == target_environment
        and secret_rotation_ops_report.get("mode") == "managed_secret_manager_evidence"
        and secret_rotation_ops_report.get("readiness_state") == "production_like_ready"
        and secret_rotation_ops_report.get("passed") is True
        and evidence.get("attached") is True
        and evidence.get("artifact_type") == "managed_secret_rotation_evidence.v1"
        and evidence.get("environment") == secret_rotation_ops_report.get("environment")
        and sha256_value_valid(evidence.get("hash"))
        and p0_service_count > 0
        and len(services) == p0_service_count
        and int_value(summary.get("covered_service_count", 0)) == p0_service_count
        and int_value(summary.get("passed_service_count", 0)) == p0_service_count
        and int_value(summary.get("failed_service_count", 0)) == 0
        and int_value(summary.get("failed_check_count", 0)) == 0
        and summary.get("managed_secret_manager_ha") is True
        and summary.get("workload_identity_federation") is True
        and summary.get("kms_hsm_custody") is True
        and summary.get("rotation_policy_enforced") is True
        and summary.get("old_versions_denied") is True
        and summary.get("unauthorized_identity_denied") is True
        and summary.get("missing_secret_denied") is True
        and summary.get("orchestrator_injection_redacted") is True
        and summary.get("plaintext_secret_material_persisted") is False
        and summary.get("audit_sink_siem_exported") is True
        and int_value(summary.get("audit_event_count", 0)) > 0
        and int_value(summary.get("audit_failed_event_count", 0)) == 0
        and all_checks_passed
        and all_services_passed
    )


def secret_rotation_service_row_release_ready(row: dict[str, Any]) -> bool:
    return (
        row.get("passed") is True
        and row.get("evidence_attached") is True
        and row.get("secrets_mode") == "external_secret_reference"
        and row.get("identity_mode")
        in {"service_account_oidc", "workload_identity", "enterprise_sso_and_service_account"}
        and isinstance(row.get("secret_handle"), str)
        and bool(row.get("secret_handle"))
        and isinstance(row.get("service_identity"), str)
        and bool(row.get("service_identity"))
        and isinstance(row.get("active_version"), str)
        and bool(row.get("active_version"))
        and isinstance(row.get("kms_key_id"), str)
        and bool(row.get("kms_key_id"))
        and sha256_value_valid(row.get("key_hash"))
        and isinstance(row.get("rotation_policy_id"), str)
        and bool(row.get("rotation_policy_id"))
        and not row.get("issues")
    )


def source_activation_p0_row_release_ready(row: dict[str, Any], *, current_registry_hash: object) -> bool:
    evidence = row.get("evidence_integrity") if isinstance(row.get("evidence_integrity"), dict) else {}
    runtime = row.get("runtime_readiness") if isinstance(row.get("runtime_readiness"), dict) else {}
    pointer = row.get("pointer") if isinstance(row.get("pointer"), dict) else {}
    next_actions = row.get("next_actions") if isinstance(row.get("next_actions"), list) else []
    issues = row.get("issues") if isinstance(row.get("issues"), list) else []
    p0_next_actions = [
        action
        for action in next_actions
        if isinstance(action, dict)
        and action.get("priority") == "P0"
        and action.get("action") != "no_action"
    ]
    return (
        row.get("activation_state") == "active"
        and row.get("effective_status") == "production_ready"
        and row.get("risk_state") == "ok"
        and not issues
        and not p0_next_actions
        and row.get("source_registry_hash") == current_registry_hash
        and row.get("current_source_registry_hash") == current_registry_hash
        and sha256_value_valid(row.get("source_registry_hash"))
        and evidence.get("required") is True
        and evidence.get("passed") is True
        and runtime.get("required") is True
        and runtime.get("attached") is True
        and runtime.get("hash_valid") is True
        and runtime.get("artifact_verifiable") is True
        and runtime.get("hash_matches_artifact") is True
        and sha256_value_valid(runtime.get("report_hash"))
        and bool(runtime.get("runtime_readiness_id"))
        and pointer.get("exists") is True
        and pointer.get("matches_latest_record") is True
        and pointer.get("consistency_state") == "consistent"
        and sha256_value_valid(pointer.get("hash"))
    )


def sha256_value_valid(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
        and all(char in "0123456789abcdef" for char in value.removeprefix("sha256:"))
    )


def strict_runtime_iac_release_gate_passed(
    runtime_report: dict[str, Any] | None,
    *,
    target_environment: str,
) -> bool:
    if not isinstance(runtime_report, dict):
        return False
    environment = runtime_report.get("environment")
    if environment not in {"staging", "prod"} or environment != target_environment:
        return False
    summary = runtime_report.get("summary") if isinstance(runtime_report.get("summary"), dict) else {}
    inputs = runtime_report.get("inputs") if isinstance(runtime_report.get("inputs"), dict) else {}
    gates = runtime_report.get("gates") if isinstance(runtime_report.get("gates"), list) else []
    service_matrix = runtime_report.get("service_matrix") if isinstance(runtime_report.get("service_matrix"), list) else []
    failures = runtime_report.get("failures") if isinstance(runtime_report.get("failures"), list) else []
    blockers = runtime_report.get("blockers") if isinstance(runtime_report.get("blockers"), list) else []
    required_inputs = ["iac_plan", "iac_apply", "drift_report", "backup_report", "health_report"]
    if environment == "prod":
        required_inputs.append("dr_report")

    required_service_count = int_value(summary.get("required_p0_service_count", 0))
    stateful_service_count = int_value(summary.get("stateful_p0_service_count", 0))
    all_required_inputs_passed = all(runtime_input_passed(inputs.get(kind)) for kind in required_inputs)
    all_gates_passed = bool(gates) and all(
        isinstance(gate, dict) and gate.get("status") == "passed"
        for gate in gates
    )
    service_matrix_passed = (
        len(service_matrix) >= required_service_count > 0
        and all(runtime_service_entry_passed(item) for item in service_matrix)
    )
    prod_plan_safe = True
    if environment == "prod":
        plan_payload = (
            inputs.get("iac_plan", {}).get("payload")
            if isinstance(inputs.get("iac_plan"), dict) and isinstance(inputs.get("iac_plan", {}).get("payload"), dict)
            else {}
        )
        plan = plan_payload.get("plan") if isinstance(plan_payload.get("plan"), dict) else {}
        prod_plan_safe = int_value(plan.get("destructive_change_count", 0)) == 0

    return (
        runtime_report.get("artifact_type") == "runtime_readiness_report.v1"
        and runtime_report.get("passed") is True
        and runtime_report.get("readiness_state") == "production_like_ready"
        and int_value(summary.get("failed_gate_count", 0)) == 0
        and int_value(summary.get("deployed_service_count", 0)) == required_service_count
        and int_value(summary.get("healthy_service_count", 0)) == required_service_count
        and stateful_service_count >= 0
        and not failures
        and not blockers
        and all_required_inputs_passed
        and all_gates_passed
        and service_matrix_passed
        and prod_plan_safe
    )


def runtime_input_passed(input_entry: object) -> bool:
    if not isinstance(input_entry, dict):
        return False
    payload = input_entry.get("payload") if isinstance(input_entry.get("payload"), dict) else {}
    return (
        input_entry.get("provided") is True
        and input_entry.get("passed") is True
        and payload.get("source_kind") in {"ci_tool_output", "external_attestation"}
        and payload.get("production_evidence") is True
        and payload.get("sample") is False
        and payload.get("status") == "passed"
        and payload.get("redacted") is True
    )


def runtime_service_entry_passed(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    return (
        item.get("plan_covered") is True
        and item.get("apply_covered") is True
        and item.get("health_passed") is True
        and item.get("backup_passed") is True
    )


def artifact_ref(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "passed": payload.get("passed"),
    }


def optional_artifact_ref(path: Path | None, payload: dict[str, Any] | None) -> dict[str, Any]:
    if path is None or payload is None:
        return {
            "attached": False,
            "uri": None,
            "hash": None,
            "artifact_type": None,
            "generated_at": None,
            "passed": None,
        }
    return {
        "attached": True,
        **artifact_ref(path, payload),
    }


def verify_schema_registry_attestation_for_review(
    platform_root: Path,
    attestation_report: dict[str, Any] | None,
    attestation_path: Path | None,
    *,
    schema_registry_runtime_report: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if attestation_report is None or attestation_path is None:
        return None
    runtime_publication = (
        schema_registry_runtime_report.get("publication_manifest")
        if isinstance(schema_registry_runtime_report, dict)
        and isinstance(schema_registry_runtime_report.get("publication_manifest"), dict)
        else {}
    )
    expected_subject_hash = runtime_publication.get("hash") if isinstance(runtime_publication.get("hash"), str) else None
    environment = attestation_report.get("environment") if isinstance(attestation_report.get("environment"), str) else ""
    release_id = attestation_report.get("release_id") if isinstance(attestation_report.get("release_id"), str) else None
    verification = verify_attestation_file(
        platform_root,
        attestation_path,
        evidence_kind="schema_registry",
        environment=environment,
        release_id=release_id,
        subject_hash=expected_subject_hash,
    )
    runtime_release_id = (
        schema_registry_runtime_report.get("release_id")
        if isinstance(schema_registry_runtime_report, dict)
        and isinstance(schema_registry_runtime_report.get("release_id"), str)
        else None
    )
    subject_artifact = (
        attestation_report.get("subject_artifact") if isinstance(attestation_report.get("subject_artifact"), dict) else {}
    )
    verification["required"]["schema_runtime_report_attached"] = schema_registry_runtime_report is not None
    verification["required"]["schema_runtime_report_passed"] = (
        isinstance(schema_registry_runtime_report, dict) and schema_registry_runtime_report.get("passed") is True
    )
    verification["required"]["runtime_release_id_matches"] = runtime_release_id is None or release_id == runtime_release_id
    verification["required"]["subject_artifact_type"] = (
        subject_artifact.get("artifact_type") == "schema_registry_publication_manifest.v1"
    )
    verification["passed"] = all(verification["required"].values())
    return verification


def resolve_optional_artifact(path_value: str | Path | None) -> tuple[dict[str, Any] | None, Path | None]:
    if path_value is None:
        return None, None
    path = Path(path_value)
    return load_json(path), path


def portfolio_control_tower_inputs(portfolio_report: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(portfolio_report, dict):
        return {}
    final = portfolio_report.get("artifacts", {}).get("final") if isinstance(portfolio_report.get("artifacts"), dict) else {}
    if not isinstance(final, dict):
        final = {}
    releases = portfolio_report.get("release_evidence")
    release_paths = [
        Path(item["uri"])
        for item in (releases if isinstance(releases, list) else [])
        if isinstance(item, dict) and isinstance(item.get("uri"), str)
    ]
    inputs: dict[str, Any] = {"release_evidence_paths": release_paths}
    artifact_map = {
        "catalog_bundle_path": "catalog_bundle",
        "catalog_lineage_ops_report_path": "catalog_lineage_ops",
        "quality_slo_ops_report_path": "quality_slo_ops",
        "semantic_metric_serving_ops_report_path": "semantic_metric_serving_ops",
        "source_activation_ops_report_path": "source_activation_ops",
    }
    for target_key, artifact_key in artifact_map.items():
        artifact = final.get(artifact_key) if isinstance(final.get(artifact_key), dict) else {}
        uri = artifact.get("uri")
        if isinstance(uri, str):
            inputs[target_key] = Path(uri)
    return inputs


def p0_gap_backlog(
    *,
    control_tower_report: dict[str, Any],
    runtime_report: dict[str, Any],
    smoke_not_covered: list[Any],
    event_backbone_report: dict[str, Any] | None,
    ingestion_runtime_report: dict[str, Any] | None,
    catalog_lineage_ops_report: dict[str, Any] | None,
    semantic_metric_serving_ops_report: dict[str, Any] | None,
    source_activation_ops_report: dict[str, Any] | None,
    backfill_readiness_report: dict[str, Any] | None,
    schema_registry_runtime_report: dict[str, Any] | None,
    schema_registry_attestation_verification: dict[str, Any] | None,
    schema_registry_ops_report: dict[str, Any] | None,
    schema_registry_auth_report: dict[str, Any] | None,
    schema_registry_storage_report: dict[str, Any] | None,
    broker_acl_report: dict[str, Any] | None,
    transactional_outbox_report: dict[str, Any] | None,
    live_bronze_ingestion_report: dict[str, Any] | None,
    orchestrated_publication_report: dict[str, Any] | None,
    live_quality_slo_report: dict[str, Any] | None,
    live_lakehouse_report: dict[str, Any] | None,
    iceberg_catalog_report: dict[str, Any] | None,
    object_store_report: dict[str, Any] | None,
    trino_sql_report: dict[str, Any] | None,
    trino_iceberg_minio_report: dict[str, Any] | None,
    catalog_cross_engine_report: dict[str, Any] | None,
    catalog_runtime_ops_report: dict[str, Any] | None,
    orchestration_runtime_ops_report: dict[str, Any] | None,
    trino_runtime_security_report: dict[str, Any] | None,
    policy_decision_report: dict[str, Any] | None,
    oidc_auth_report: dict[str, Any] | None,
    secret_rotation_report: dict[str, Any] | None,
    secret_rotation_ops_report: dict[str, Any] | None,
    dagster_orchestration_report: dict[str, Any] | None,
    dagster_day2_report: dict[str, Any] | None,
    portfolio_report: dict[str, Any] | None,
    workload_benchmark_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    backlog: list[dict[str, Any]] = []
    target_environment = str(control_tower_report.get("environment", ""))
    schema_registry_release_gate_passed = strict_schema_registry_release_gate_passed(schema_registry_ops_report)
    catalog_runtime_release_gate_passed = strict_catalog_runtime_ops_release_gate_passed(
        catalog_runtime_ops_report,
        target_environment=target_environment,
    )
    orchestration_runtime_release_gate_passed = strict_orchestration_runtime_ops_release_gate_passed(
        orchestration_runtime_ops_report,
        target_environment=target_environment,
    )
    catalog_lineage_release_gate_passed = strict_catalog_lineage_release_gate_passed(
        catalog_lineage_ops_report,
        target_environment=target_environment,
    )
    semantic_metric_serving_release_gate_passed = strict_semantic_metric_serving_release_gate_passed(
        semantic_metric_serving_ops_report,
        target_environment=target_environment,
    )
    source_onboarding_release_gate_passed = strict_source_onboarding_release_gate_passed(
        source_activation_ops_report,
        target_environment=target_environment,
    )
    backfill_change_governance_release_gate_passed = strict_backfill_readiness_release_gate_passed(
        backfill_readiness_report,
        target_environment=target_environment,
    )
    runtime_iac_release_gate_passed = strict_runtime_iac_release_gate_passed(
        runtime_report,
        target_environment=target_environment,
    )
    secret_rotation_ops_release_gate_passed = strict_secret_rotation_ops_release_gate_passed(
        secret_rotation_ops_report,
        target_environment=target_environment,
    )
    workload_benchmark_release_gate_passed = strict_workload_benchmark_release_gate_passed(
        workload_benchmark_report,
        target_environment=target_environment,
    )
    if workload_benchmark_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "production_review_pack",
                "gap": "workload_benchmark_report_not_attached",
                "capability_id": "runtime-scale-benchmark",
                "owner_team": "data-platform-sre",
                "domain": "platform-runtime",
                "message": "Attach workload_benchmark_report.v1 from managed staging/prod to prove production-like throughput, lag, query latency, error-rate and freshness SLOs at scale.",
            }
        )
    elif not workload_benchmark_release_gate_passed:
        summary = (
            workload_benchmark_report.get("summary")
            if isinstance(workload_benchmark_report.get("summary"), dict)
            else {}
        )
        backlog.append(
            {
                "priority": "P0",
                "source": "production_review_pack",
                "gap": "workload_benchmark_release_gate_failed",
                "capability_id": "runtime-scale-benchmark",
                "owner_team": "data-platform-sre",
                "domain": "platform-runtime",
                "message": "Workload benchmark evidence is attached but does not satisfy production-like scale SLO requirements.",
                "benchmark_summary": {
                    "environment": workload_benchmark_report.get("environment"),
                    "source_kind": workload_benchmark_report.get("source_kind"),
                    "scale_profile": summary.get("scale_profile"),
                    "input_record_count": summary.get("input_record_count", 0),
                    "duration_minutes": summary.get("duration_minutes", 0),
                    "throughput_records_per_second": summary.get("throughput_records_per_second", 0),
                    "query_concurrency": summary.get("query_concurrency", 0),
                    "p95_query_latency_ms": summary.get("p95_query_latency_ms", 0),
                    "max_consumer_lag_records": summary.get("max_consumer_lag_records", 0),
                    "error_rate": summary.get("error_rate", 1),
                },
            }
        )
    runtime_security_passed = trino_runtime_security_report is not None and trino_runtime_security_report.get("passed") is True
    runtime_row_filter_passed = (
        trino_runtime_security_report is not None
        and isinstance(trino_runtime_security_report.get("summary"), dict)
        and trino_runtime_security_report["summary"].get("row_level_filter_enforced") is True
    )
    runtime_column_mask_passed = (
        trino_runtime_security_report is not None
        and isinstance(trino_runtime_security_report.get("summary"), dict)
        and trino_runtime_security_report["summary"].get("column_masking_enforced") is True
    )
    runtime_audit_sink_passed = (
        trino_runtime_security_report is not None
        and isinstance(trino_runtime_security_report.get("summary"), dict)
        and trino_runtime_security_report["summary"].get("centralized_audit_sink_passed") is True
    )
    policy_decision_summary = (
        policy_decision_report.get("summary")
        if isinstance(policy_decision_report, dict) and isinstance(policy_decision_report.get("summary"), dict)
        else {}
    )
    policy_decision_passed = (
        policy_decision_report is not None
        and policy_decision_report.get("passed") is True
        and policy_decision_summary.get("pdp") == "opa"
        and policy_decision_summary.get("decision_api_reachable") is True
        and policy_decision_summary.get("finance_reader_allowed") is True
        and policy_decision_summary.get("unauthorized_default_denied") is True
        and policy_decision_summary.get("row_filter_decision_present") is True
        and policy_decision_summary.get("column_mask_decision_present") is True
        and policy_decision_summary.get("policy_admin_approval_passed") is True
        and policy_decision_summary.get("policy_admin_self_approval_denied") is True
        and policy_decision_summary.get("policy_admin_missing_evidence_denied") is True
        and policy_decision_summary.get("audit_sink_passed") is True
    )
    oidc_auth_summary = (
        oidc_auth_report.get("summary")
        if isinstance(oidc_auth_report, dict) and isinstance(oidc_auth_report.get("summary"), dict)
        else {}
    )
    oidc_auth_passed = (
        oidc_auth_report is not None
        and oidc_auth_report.get("passed") is True
        and oidc_auth_summary.get("jwks_key_published") is True
        and oidc_auth_summary.get("rs256_signature_validation_passed") is True
        and oidc_auth_summary.get("issuer_validation_passed") is True
        and oidc_auth_summary.get("audience_validation_passed") is True
        and oidc_auth_summary.get("expiry_validation_passed") is True
        and oidc_auth_summary.get("required_role_denied") is True
        and oidc_auth_summary.get("unknown_kid_denied") is True
        and oidc_auth_summary.get("missing_token_denied") is True
        and oidc_auth_summary.get("audit_sink_passed") is True
        and oidc_auth_summary.get("raw_access_tokens_persisted") is False
    )
    access_privacy_release_gate_passed = strict_access_privacy_release_gate_passed(
        trino_runtime_security_report=trino_runtime_security_report,
        policy_decision_report=policy_decision_report,
        oidc_auth_report=oidc_auth_report,
    )
    secret_rotation_summary = (
        secret_rotation_report.get("summary")
        if isinstance(secret_rotation_report, dict)
        and isinstance(secret_rotation_report.get("summary"), dict)
        else {}
    )
    secret_rotation_passed = (
        secret_rotation_report is not None
        and secret_rotation_report.get("passed") is True
        and secret_rotation_summary.get("secret_manager_mode") == "local_encrypted_versioned_secret_store"
        and int_value(secret_rotation_summary.get("service_identity_count", 0)) >= 4
        and int_value(secret_rotation_summary.get("rotated_secret_count", 0)) >= 4
        and secret_rotation_summary.get("active_version_advanced") is True
        and secret_rotation_summary.get("old_versions_revoked") is True
        and secret_rotation_summary.get("new_versions_readable") is True
        and secret_rotation_summary.get("unauthorized_identity_denied") is True
        and secret_rotation_summary.get("missing_secret_denied") is True
        and secret_rotation_summary.get("orchestrator_service_identity_used") is True
        and secret_rotation_summary.get("orchestrator_run_id_present") is True
        and secret_rotation_summary.get("orchestrator_secret_injection_passed") is True
        and secret_rotation_summary.get("orchestrator_injection_manifest_redacted") is True
        and secret_rotation_summary.get("plaintext_secret_material_persisted") is False
        and secret_rotation_summary.get("audit_sink_passed") is True
    )
    schema_registry_runtime_passed = (
        schema_registry_runtime_report is not None and schema_registry_runtime_report.get("passed") is True
    )
    schema_registry_attestation_passed = (
        schema_registry_attestation_verification is not None
        and schema_registry_attestation_verification.get("passed") is True
    )
    schema_registry_auth_summary = (
        schema_registry_auth_report.get("summary")
        if isinstance(schema_registry_auth_report, dict) and isinstance(schema_registry_auth_report.get("summary"), dict)
        else {}
    )
    schema_registry_auth_passed = (
        schema_registry_auth_report is not None
        and schema_registry_auth_report.get("passed") is True
        and schema_registry_auth_summary.get("auth_gateway_enforced") is True
        and schema_registry_auth_summary.get("missing_token_denied") is True
        and schema_registry_auth_summary.get("unknown_token_denied") is True
        and schema_registry_auth_summary.get("denied_token_blocked") is True
        and schema_registry_auth_summary.get("reader_write_denied") is True
        and schema_registry_auth_summary.get("publisher_publish_allowed") is True
        and schema_registry_auth_summary.get("reader_read_allowed") is True
        and int_value(schema_registry_auth_summary.get("authorization_audit_event_count", 0)) >= 7
    )
    schema_registry_storage_summary = (
        schema_registry_storage_report.get("summary")
        if isinstance(schema_registry_storage_report, dict)
        and isinstance(schema_registry_storage_report.get("summary"), dict)
        else {}
    )
    schema_registry_storage_passed = (
        schema_registry_storage_report is not None
        and schema_registry_storage_report.get("passed") is True
        and schema_registry_storage_summary.get("storage_backend") == "postgresql"
        and int_value(schema_registry_storage_summary.get("registry_replica_count", 0)) >= 2
        and schema_registry_storage_summary.get("shared_sql_storage_configured") is True
        and schema_registry_storage_summary.get("cross_replica_read_after_write_passed") is True
        and schema_registry_storage_summary.get("replica_restart_durable_readback_passed") is True
    )
    event_backbone_summary = (
        event_backbone_report.get("summary")
        if isinstance(event_backbone_report, dict) and isinstance(event_backbone_report.get("summary"), dict)
        else {}
    )
    sink_schema_validation_passed = event_backbone_summary.get("sink_schema_validation_passed") is True
    producer_schema_id_guard_passed = event_backbone_summary.get("producer_schema_id_guard_passed") is True
    multi_partition_rebalance_passed = event_backbone_summary.get("multi_partition_rebalance_passed") is True
    broker_acl_summary = (
        broker_acl_report.get("summary")
        if isinstance(broker_acl_report, dict) and isinstance(broker_acl_report.get("summary"), dict)
        else {}
    )
    broker_acl_passed = (
        broker_acl_report is not None
        and broker_acl_report.get("passed") is True
        and broker_acl_summary.get("broker_acl_enforced") is True
        and broker_acl_summary.get("allowed_user_can_produce") is True
        and broker_acl_summary.get("authorization_denied_verified") is True
    )
    transactional_outbox_summary = (
        transactional_outbox_report.get("summary")
        if isinstance(transactional_outbox_report, dict)
        and isinstance(transactional_outbox_report.get("summary"), dict)
        else {}
    )
    transactional_outbox_passed = (
        transactional_outbox_report is not None
        and transactional_outbox_report.get("passed") is True
        and transactional_outbox_summary.get("transactional_outbox_to_bronze_passed") is True
    )
    live_bronze_ingestion_summary = (
        live_bronze_ingestion_report.get("summary")
        if isinstance(live_bronze_ingestion_report, dict)
        and isinstance(live_bronze_ingestion_report.get("summary"), dict)
        else {}
    )
    live_bronze_ingestion_passed = (
        live_bronze_ingestion_report is not None
        and live_bronze_ingestion_report.get("passed") is True
        and live_bronze_ingestion_summary.get("live_bronze_iceberg_sink_passed") is True
        and live_bronze_ingestion_summary.get("restart_resume_passed") is True
        and live_bronze_ingestion_summary.get("dlt_quarantine_passed") is True
        and int_value(live_bronze_ingestion_summary.get("approved_row_count", 0)) > 0
        and int_value(live_bronze_ingestion_summary.get("duplicate_skipped_count", 0)) > 0
        and int_value(live_bronze_ingestion_summary.get("quarantine_row_count", 0)) > 0
    )
    orchestrated_publication_summary = (
        orchestrated_publication_report.get("summary")
        if isinstance(orchestrated_publication_report, dict)
        and isinstance(orchestrated_publication_report.get("summary"), dict)
        else {}
    )
    orchestrated_publication_passed = (
        orchestrated_publication_report is not None
        and orchestrated_publication_report.get("passed") is True
        and orchestrated_publication_summary.get("promotion_passed") is True
        and orchestrated_publication_summary.get("activation_passed") is True
        and orchestrated_publication_summary.get("publication_ops_passed") is True
        and orchestrated_publication_summary.get("active_pointer_drift_negative_test_passed") is True
        and int_value(orchestrated_publication_summary.get("bronze_row_count", 0)) > 0
        and int_value(orchestrated_publication_summary.get("silver_row_count", 0)) > 0
        and int_value(orchestrated_publication_summary.get("gold_row_count", 0)) > 0
        and int_value(orchestrated_publication_summary.get("trino_silver_row_count", 0)) > 0
        and int_value(orchestrated_publication_summary.get("trino_gold_row_count", 0)) > 0
        and int_value(orchestrated_publication_summary.get("dagster_retry_event_count", 0)) >= 1
        and int_value(orchestrated_publication_summary.get("asset_materialization_count", 0)) >= 2
        and int_value(orchestrated_publication_summary.get("failed_check_count", 0)) == 0
    )
    live_quality_slo_summary = (
        live_quality_slo_report.get("summary")
        if isinstance(live_quality_slo_report, dict)
        and isinstance(live_quality_slo_report.get("summary"), dict)
        else {}
    )
    live_quality_slo_passed = (
        live_quality_slo_report is not None
        and live_quality_slo_report.get("artifact_type") == "live_quality_slo_smoke_report.v1"
        and live_quality_slo_report.get("passed") is True
        and live_quality_slo_summary.get("target_data_product") == "gold.finance_benefit_reconciliation"
        and int_value(live_quality_slo_summary.get("gold_row_count", 0)) > 0
        and live_quality_slo_summary.get("quality_runtime_passed") is True
        and live_quality_slo_summary.get("slo_alert_passed") is True
        and live_quality_slo_summary.get("quality_slo_ops_passed") is True
        and live_quality_slo_summary.get("corrupt_gold_null_negative_test_passed") is True
        and live_quality_slo_summary.get("stale_freshness_negative_test_passed") is True
        and live_quality_slo_summary.get("red_alert_negative_test_passed") is True
        and live_quality_slo_summary.get("environment_mismatch_negative_test_passed") is True
        and live_quality_slo_summary.get("missing_alert_production_like_negative_test_passed") is True
        and int_value(live_quality_slo_summary.get("quality_runtime_failed_check_count", 0)) == 0
        and int_value(live_quality_slo_summary.get("freshness_breach_count", 0)) == 0
        and int_value(live_quality_slo_summary.get("quality_slo_ops_failed_product_count", 0)) == 0
        and int_value(live_quality_slo_summary.get("quality_slo_ops_global_failed_check_count", 0)) == 0
        and int_value(live_quality_slo_summary.get("failed_check_count", 0)) == 0
    )
    object_store_summary = (
        object_store_report.get("summary")
        if isinstance(object_store_report, dict) and isinstance(object_store_report.get("summary"), dict)
        else {}
    )
    trino_iceberg_minio_summary = (
        trino_iceberg_minio_report.get("summary")
        if isinstance(trino_iceberg_minio_report, dict)
        and isinstance(trino_iceberg_minio_report.get("summary"), dict)
        else {}
    )
    object_store_encryption_passed = (
        (
            object_store_report is not None
            and object_store_report.get("passed") is True
            and object_store_summary.get("encryption_policy_enforced") is True
            and object_store_summary.get("unencrypted_put_denied") is True
            and object_store_summary.get("encrypted_put_allowed") is True
        )
        or (
            trino_iceberg_minio_report is not None
            and trino_iceberg_minio_report.get("passed") is True
            and trino_iceberg_minio_summary.get("object_store_encryption_policy_enforced") is True
            and trino_iceberg_minio_summary.get("trino_iceberg_objects_encrypted") is True
        )
    )
    catalog_cross_engine_summary = (
        catalog_cross_engine_report.get("summary")
        if isinstance(catalog_cross_engine_report, dict)
        and isinstance(catalog_cross_engine_report.get("summary"), dict)
        else {}
    )
    catalog_cross_engine_passed = (
        catalog_cross_engine_report is not None
        and catalog_cross_engine_report.get("passed") is True
        and catalog_cross_engine_summary.get("cross_engine_commit_compatibility_passed") is True
    )
    dagster_day2_summary = (
        dagster_day2_report.get("summary")
        if isinstance(dagster_day2_report, dict) and isinstance(dagster_day2_report.get("summary"), dict)
        else {}
    )
    dagster_day2_release_gate_passed = strict_dagster_day2_release_gate_passed(dagster_day2_report)
    if portfolio_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "portfolio_release_smoke_boundary",
                "gap": "portfolio_release_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach portfolio_release_smoke_report.v1 from make portfolio-release-smoke to prove multi-use-case Gold release evidence coverage.",
            }
        )
    elif portfolio_report.get("passed") is not True:
        summary = portfolio_report.get("summary") if isinstance(portfolio_report.get("summary"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "portfolio_release_smoke_boundary",
                "gap": "portfolio_release_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Portfolio release smoke did not pass.",
                "missing_gold_outputs": summary.get("missing_gold_outputs", []),
                "failed_release_count": summary.get("failed_release_count", 0),
            }
        )
    if event_backbone_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "event_backbone_smoke_boundary",
                "gap": "event_backbone_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach event_backbone_smoke_report.v1 from make event-backbone-smoke to prove the local Redpanda round trip.",
            }
        )
    elif event_backbone_report.get("passed") is not True:
        summary = event_backbone_report.get("summary") if isinstance(event_backbone_report.get("summary"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "event_backbone_smoke_boundary",
                "gap": "event_backbone_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local event backbone smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    elif isinstance(event_backbone_report.get("runtime_scope"), dict):
        not_covered = event_backbone_report.get("runtime_scope", {}).get("not_covered", [])
        for gap in not_covered if isinstance(not_covered, list) else []:
            if gap == "debezium_or_transactional_outbox_source_connector" and transactional_outbox_passed:
                continue
            if gap == "production_schema_registry_subject_publication" and schema_registry_runtime_passed:
                continue
            if gap == "broker_acl_enforcement" and broker_acl_passed:
                continue
            if gap == "multi_partition_rebalance" and multi_partition_rebalance_passed:
                continue
            if secret_rotation_ops_closes_gap(str(gap), secret_rotation_ops_release_gate_passed):
                continue
            backlog.append(
                {
                    "priority": "P0",
                    "source": "event_backbone_smoke_boundary",
                    "gap": str(gap),
                    "owner_team": "data-platform-team",
                }
            )
    if broker_acl_report is not None and not broker_acl_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "broker_acl_smoke_boundary",
                "gap": "broker_acl_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local Redpanda broker ACL smoke did not prove allowed produce and denied authorization enforcement.",
                "failed_checks": broker_acl_summary.get("failed_checks", []),
            }
        )
    if transactional_outbox_report is not None and not transactional_outbox_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "transactional_outbox_smoke_boundary",
                "gap": "transactional_outbox_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local Postgres transactional outbox to Redpanda to Bronze smoke did not pass.",
                "failed_checks": transactional_outbox_summary.get("failed_checks", []),
            }
        )
    if live_bronze_ingestion_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "live_bronze_ingestion_smoke_boundary",
                "gap": "live_bronze_ingestion_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach live_bronze_ingestion_runtime_report.v1 from make live-bronze-ingestion-smoke to prove source outbox to Redpanda to Bronze Iceberg runtime ingestion.",
            }
        )
    elif not live_bronze_ingestion_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "live_bronze_ingestion_smoke_boundary",
                "gap": "live_bronze_ingestion_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Live Bronze ingestion smoke did not prove source outbox to Redpanda to Bronze Iceberg with idempotency, quarantine and offset resume evidence.",
                "failed_checks": live_bronze_ingestion_summary.get("failed_checks", []),
            }
        )
    if orchestrated_publication_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "orchestrated_publication_smoke_boundary",
                "gap": "orchestrated_publication_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach orchestrated_live_publication_report.v1 from make orchestrated-publication-smoke to prove Bronze Iceberg to Silver/Gold Iceberg publication with Trino readback and release activation.",
            }
        )
    elif not orchestrated_publication_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "orchestrated_publication_smoke_boundary",
                "gap": "orchestrated_publication_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Orchestrated publication smoke did not prove Bronze Iceberg to Silver/Gold Iceberg with Trino readback, release promotion, activation, rollback pointer and drift negative evidence.",
                "failed_checks": orchestrated_publication_summary.get("failed_checks", []),
            }
        )
    if live_quality_slo_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "live_quality_slo_smoke_boundary",
                "gap": "live_quality_slo_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach live_quality_slo_smoke_report.v1 from make live-quality-slo-smoke to prove live Gold quality/SLO runtime checks, alert evidence and negative gate controls.",
            }
        )
    elif not live_quality_slo_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "live_quality_slo_smoke_boundary",
                "gap": "live_quality_slo_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Live quality/SLO smoke did not prove Trino Gold runtime quality checks, SLO alert evidence, quality ops report and negative gate controls.",
                "failed_checks": live_quality_slo_summary.get("failed_checks", []),
            }
        )
    if ingestion_runtime_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "ingestion_runtime_boundary",
                "gap": "ingestion_runtime_report_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach event_cdc_ingestion_runtime_report.v1 from ingestion-runtime-check or event-backbone-smoke to prove runtime ingestion evidence is available to Control Tower.",
            }
        )
    elif ingestion_runtime_report.get("passed") is not True:
        summary = ingestion_runtime_report.get("summary") if isinstance(ingestion_runtime_report.get("summary"), dict) else {}
        board = ingestion_runtime_report.get("decision_board") if isinstance(ingestion_runtime_report.get("decision_board"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "ingestion_runtime_boundary",
                "gap": "ingestion_runtime_report_failed",
                "owner_team": "data-platform-team",
                "message": "Event/CDC ingestion runtime report did not pass.",
                "p0_failed_source_count": summary.get("p0_failed_source_count", 0),
                "global_failed_check_count": summary.get("global_failed_check_count", 0),
                "page_now": board.get("page_now", []),
            }
        )
    else:
        summary = ingestion_runtime_report.get("summary") if isinstance(ingestion_runtime_report.get("summary"), dict) else {}
        p0_source_count = int_value(summary.get("p0_source_count", 0))
        running_connector_count = int_value(summary.get("running_connector_count", 0))
        if p0_source_count and running_connector_count < p0_source_count:
            backlog.append(
                {
                    "priority": "P0",
                    "source": "ingestion_runtime_boundary",
                    "gap": "ingestion_runtime_p0_coverage_incomplete",
                    "owner_team": "data-platform-team",
                    "message": "Ingestion runtime evidence does not yet cover every P0 source.",
                    "p0_source_count": p0_source_count,
                    "running_connector_count": running_connector_count,
                }
            )
    if schema_registry_runtime_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "schema_registry_runtime_smoke_boundary",
                "gap": "schema_registry_runtime_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach schema_registry_runtime_smoke_report.v1 from make schema-registry-runtime-smoke to prove local Apicurio registry subject publication/read-back.",
            }
        )
    elif schema_registry_runtime_report.get("passed") is not True:
        summary = (
            schema_registry_runtime_report.get("summary")
            if isinstance(schema_registry_runtime_report.get("summary"), dict)
            else {}
        )
        backlog.append(
            {
                "priority": "P0",
                "source": "schema_registry_runtime_smoke_boundary",
                "gap": "schema_registry_runtime_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local schema registry runtime smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    elif isinstance(schema_registry_runtime_report.get("runtime_scope"), dict):
        not_covered = schema_registry_runtime_report.get("runtime_scope", {}).get("not_covered", [])
        for gap in not_covered if isinstance(not_covered, list) else []:
            if gap == "broker_or_sink_schema_validation" and sink_schema_validation_passed:
                continue
            if gap == "producer_schema_id_enforcement" and producer_schema_id_guard_passed:
                continue
            if gap == "external_attestation_for_production_registry" and schema_registry_attestation_passed:
                continue
            if gap == "production_registry_authentication_authorization" and schema_registry_auth_passed:
                continue
            if gap == "production_registry_ha_storage" and schema_registry_storage_passed:
                continue
            if secret_rotation_ops_closes_gap(str(gap), secret_rotation_ops_release_gate_passed):
                continue
            backlog.append(
                {
                    "priority": "P0",
                    "source": "schema_registry_runtime_smoke_boundary",
                    "gap": str(gap),
                    "owner_team": "data-platform-team",
                }
            )
    if live_lakehouse_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "live_lakehouse_smoke_boundary",
                "gap": "live_lakehouse_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach live_lakehouse_smoke_report.v1 from make live-lakehouse-smoke to prove Parquet table commits and a real SQL query engine over the finance slice.",
            }
        )
    elif live_lakehouse_report.get("passed") is not True:
        summary = live_lakehouse_report.get("summary") if isinstance(live_lakehouse_report.get("summary"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "live_lakehouse_smoke_boundary",
                "gap": "live_lakehouse_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local live lakehouse smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    if iceberg_catalog_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "iceberg_catalog_smoke_boundary",
                "gap": "iceberg_catalog_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach iceberg_catalog_smoke_report.v1 from make iceberg-catalog-smoke to prove local Iceberg table and catalog snapshot commits.",
            }
        )
    elif iceberg_catalog_report.get("passed") is not True:
        summary = iceberg_catalog_report.get("summary") if isinstance(iceberg_catalog_report.get("summary"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "iceberg_catalog_smoke_boundary",
                "gap": "iceberg_catalog_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local Iceberg catalog smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    elif isinstance(iceberg_catalog_report.get("runtime_scope"), dict):
        not_covered = iceberg_catalog_report.get("runtime_scope", {}).get("not_covered", [])
        for gap in not_covered if isinstance(not_covered, list) else []:
            if gap == "runtime_security_enforcement" and runtime_security_passed:
                continue
            if catalog_runtime_ops_closes_gap(str(gap), catalog_runtime_release_gate_passed):
                continue
            if gap in {
                "minio_object_store_iceberg_warehouse",
                "trino_iceberg_connector",
                "minio_federated_query",
                "hive_nessie_or_rest_catalog_service",
            } and trino_iceberg_minio_report and trino_iceberg_minio_report.get("passed") is True:
                continue
            if secret_rotation_ops_closes_gap(str(gap), secret_rotation_ops_release_gate_passed):
                continue
            backlog.append(
                {
                    "priority": "P0",
                    "source": "iceberg_catalog_smoke_boundary",
                    "gap": str(gap),
                    "owner_team": "data-platform-team",
                }
            )
    if object_store_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "object_store_smoke_boundary",
                "gap": "object_store_commit_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach object_store_commit_smoke_report.v1 from make object-store-smoke to prove Parquet commits are uploaded to S3-compatible object storage and read back successfully.",
            }
        )
    elif object_store_report.get("passed") is not True:
        summary = object_store_report.get("summary") if isinstance(object_store_report.get("summary"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "object_store_smoke_boundary",
                "gap": "object_store_commit_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local object-store commit smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    if trino_sql_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "trino_sql_runtime_smoke_boundary",
                "gap": "trino_sql_runtime_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach trino_sql_runtime_smoke_report.v1 from make trino-sql-smoke to prove a live Trino engine can load and query the finance Gold slice.",
            }
        )
    elif trino_sql_report.get("passed") is not True:
        summary = trino_sql_report.get("summary") if isinstance(trino_sql_report.get("summary"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "trino_sql_runtime_smoke_boundary",
                "gap": "trino_sql_runtime_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local Trino SQL runtime smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    elif isinstance(trino_sql_report.get("runtime_scope"), dict):
        not_covered = trino_sql_report.get("runtime_scope", {}).get("not_covered", [])
        for gap in not_covered if isinstance(not_covered, list) else []:
            if gap == "iceberg_catalog_commit" and iceberg_catalog_report and iceberg_catalog_report.get("passed") is True:
                continue
            if gap in {"minio_federated_query", "trino_iceberg_connector"} and trino_iceberg_minio_report and trino_iceberg_minio_report.get("passed") is True:
                continue
            if gap == "orchestrator_run_history" and dagster_orchestration_report and dagster_orchestration_report.get("passed") is True:
                continue
            if orchestration_runtime_ops_closes_gap(str(gap), orchestration_runtime_release_gate_passed):
                continue
            if gap == "runtime_security_enforcement" and runtime_security_passed:
                continue
            backlog.append(
                {
                    "priority": "P0",
                    "source": "trino_sql_runtime_smoke_boundary",
                    "gap": str(gap),
                    "owner_team": "data-platform-team",
                }
            )
    if trino_iceberg_minio_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "trino_iceberg_minio_smoke_boundary",
                "gap": "trino_iceberg_minio_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach trino_iceberg_minio_smoke_report.v1 from make trino-iceberg-minio-smoke to prove Trino can create and query an Iceberg table backed by MinIO.",
            }
        )
    elif trino_iceberg_minio_report.get("passed") is not True:
        summary = trino_iceberg_minio_report.get("summary") if isinstance(trino_iceberg_minio_report.get("summary"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "trino_iceberg_minio_smoke_boundary",
                "gap": "trino_iceberg_minio_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local Trino Iceberg/MinIO smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    elif isinstance(trino_iceberg_minio_report.get("runtime_scope"), dict):
        not_covered = trino_iceberg_minio_report.get("runtime_scope", {}).get("not_covered", [])
        for gap in not_covered if isinstance(not_covered, list) else []:
            if gap == "runtime_security_enforcement" and runtime_security_passed:
                continue
            if gap == "cross_engine_commit_compatibility" and catalog_cross_engine_passed:
                continue
            if gap == "production_object_store_encryption_policy" and object_store_encryption_passed:
                continue
            if gap in {
                "production_cloud_kms_key_rotation",
                "cloud_provider_bucket_policy_attestation",
                "cross_account_object_store_access_policy",
            } and object_store_encryption_passed:
                continue
            if catalog_runtime_ops_closes_gap(str(gap), catalog_runtime_release_gate_passed):
                continue
            if secret_rotation_ops_closes_gap(str(gap), secret_rotation_ops_release_gate_passed):
                continue
            backlog.append(
                {
                    "priority": "P0",
                    "source": "trino_iceberg_minio_smoke_boundary",
                    "gap": str(gap),
                    "owner_team": "data-platform-team",
                }
            )
    if catalog_cross_engine_report is not None and not catalog_cross_engine_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "catalog_cross_engine_smoke_boundary",
                "gap": "catalog_cross_engine_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local catalog cross-engine smoke did not prove Trino/PyIceberg shared catalog commit compatibility.",
                "failed_checks": catalog_cross_engine_summary.get("failed_checks", []),
            }
        )
    elif catalog_cross_engine_passed and isinstance(catalog_cross_engine_report.get("runtime_scope"), dict):
        not_covered = catalog_cross_engine_report.get("runtime_scope", {}).get("not_covered", [])
        for gap in not_covered if isinstance(not_covered, list) else []:
            if catalog_runtime_ops_closes_gap(str(gap), catalog_runtime_release_gate_passed):
                continue
            backlog.append(
                {
                    "priority": "P0",
                    "source": "catalog_cross_engine_smoke_boundary",
                    "gap": str(gap),
                    "owner_team": "data-platform-team",
                }
            )
    if catalog_runtime_ops_report is not None and not catalog_runtime_release_gate_passed:
        summary = (
            catalog_runtime_ops_report.get("summary")
            if isinstance(catalog_runtime_ops_report.get("summary"), dict)
            else {}
        )
        backlog.append(
            {
                "priority": "P0",
                "source": "catalog_runtime_ops_boundary",
                "gap": "catalog_runtime_ops_failed",
                "owner_team": "data-platform-team",
                "message": "Catalog runtime ops evidence did not prove production-like HA, failover, stale-commit rejection, backup/PITR, audit and attestation.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    if trino_runtime_security_report is None:
        backlog.append(
            {
                "priority": "P0",
                "source": "trino_runtime_security_smoke_boundary",
                "gap": "trino_runtime_security_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach trino_runtime_security_smoke_report.v1 from make trino-runtime-security-smoke to prove local Trino runtime allow/deny enforcement.",
            }
        )
    elif trino_runtime_security_report.get("passed") is not True:
        summary = (
            trino_runtime_security_report.get("summary")
            if isinstance(trino_runtime_security_report.get("summary"), dict)
            else {}
        )
        backlog.append(
            {
                "priority": "P0",
                "source": "trino_runtime_security_smoke_boundary",
                "gap": "trino_runtime_security_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local Trino runtime security smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    elif isinstance(trino_runtime_security_report.get("runtime_scope"), dict):
        not_covered = trino_runtime_security_report.get("runtime_scope", {}).get("not_covered", [])
        for gap in not_covered if isinstance(not_covered, list) else []:
            if gap == "row_level_filter_enforcement" and runtime_row_filter_passed:
                continue
            if gap == "column_masking_enforcement" and runtime_column_mask_passed:
                continue
            if gap == "centralized_audit_sink" and runtime_audit_sink_passed:
                continue
            if gap in {"ranger_or_opa_policy_decision_point", "policy_admin_maker_checker"} and policy_decision_passed:
                continue
            if gap == "keycloak_or_oidc_authentication" and oidc_auth_passed:
                continue
            if secret_rotation_ops_closes_gap(str(gap), secret_rotation_ops_release_gate_passed):
                continue
            backlog.append(
                {
                    "priority": "P0",
                    "source": "trino_runtime_security_smoke_boundary",
                    "gap": str(gap),
                    "owner_team": "data-platform-team",
                }
            )
    if policy_decision_report is not None and not policy_decision_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "policy_decision_smoke_boundary",
                "gap": "policy_decision_smoke_failed",
                "owner_team": "data-platform-security",
                "message": "Local OPA PDP smoke did not prove allow/deny, row-filter, mask, maker-checker and audit evidence.",
                "failed_checks": policy_decision_summary.get("failed_checks", []),
            }
        )
    if oidc_auth_report is not None and not oidc_auth_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "oidc_auth_smoke_boundary",
                "gap": "oidc_auth_smoke_failed",
                "owner_team": "data-platform-security",
                "message": "Local OIDC/JWKS auth smoke did not prove issuer, audience, expiry, RS256 signature, role-deny and redacted audit evidence.",
                "failed_checks": oidc_auth_summary.get("failed_checks", []),
            }
        )
    if secret_rotation_report is not None and not secret_rotation_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "secret_rotation_smoke_boundary",
                "gap": "secret_rotation_smoke_failed",
                "owner_team": "data-platform-security",
                "message": "Local secret rotation smoke did not prove version rotation, old-version revoke, service identity authorization, Dagster injection and redacted audit evidence.",
                "failed_checks": secret_rotation_summary.get("failed_checks", []),
            }
        )
    if orchestration_runtime_ops_report is not None and not orchestration_runtime_release_gate_passed:
        summary = (
            orchestration_runtime_ops_report.get("summary")
            if isinstance(orchestration_runtime_ops_report.get("summary"), dict)
            else {}
        )
        backlog.append(
            {
                "priority": "P0",
                "source": "orchestration_runtime_ops_boundary",
                "gap": "orchestration_runtime_ops_failed",
                "owner_team": "data-platform-team",
                "message": "Orchestration runtime ops evidence did not prove production-like Dagster daemon HA, distributed or Kubernetes launcher, managed run storage, day-2 execution, service identity, metrics, audit and attestation.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    if dagster_orchestration_report is None and not orchestration_runtime_release_gate_passed:
        backlog.append(
            {
                "priority": "P0",
                "source": "dagster_orchestration_smoke_boundary",
                "gap": "dagster_orchestration_smoke_not_attached",
                "owner_team": "data-platform-team",
                "message": "Attach dagster_orchestration_smoke_report.v1 from make dagster-orchestration-smoke to prove local Dagster run history over the finance runtime evidence path.",
            }
        )
    elif dagster_orchestration_report is not None and dagster_orchestration_report.get("passed") is not True and not orchestration_runtime_release_gate_passed:
        summary = dagster_orchestration_report.get("summary") if isinstance(dagster_orchestration_report.get("summary"), dict) else {}
        backlog.append(
            {
                "priority": "P0",
                "source": "dagster_orchestration_smoke_boundary",
                "gap": "dagster_orchestration_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local Dagster orchestration smoke did not pass.",
                "failed_checks": summary.get("failed_checks", []),
            }
        )
    elif isinstance(dagster_orchestration_report.get("runtime_scope"), dict):
        not_covered = dagster_orchestration_report.get("runtime_scope", {}).get("not_covered", [])
        for gap in not_covered if isinstance(not_covered, list) else []:
            if gap == "runtime_security_enforcement" and runtime_security_passed:
                continue
            if gap == "orchestrator_service_identity_and_secret_injection" and secret_rotation_passed:
                continue
            if catalog_runtime_ops_closes_gap(str(gap), catalog_runtime_release_gate_passed):
                continue
            if secret_rotation_ops_closes_gap(str(gap), secret_rotation_ops_release_gate_passed):
                continue
            if orchestration_runtime_ops_closes_gap(str(gap), orchestration_runtime_release_gate_passed):
                continue
            if (
                gap
                in {
                    "dagster_daemon_or_schedule_tick_history",
                    "production_retry_backoff_runtime_policy",
                    "production_backfill_materialization_history",
                }
                and dagster_day2_release_gate_passed
            ):
                continue
            backlog.append(
                {
                    "priority": "P0",
                    "source": "dagster_orchestration_smoke_boundary",
                    "gap": str(gap),
                    "owner_team": "data-platform-team",
                }
            )
    if (
        dagster_day2_report is not None
        and dagster_day2_report.get("passed") is not True
        and not orchestration_runtime_release_gate_passed
    ):
        backlog.append(
            {
                "priority": "P0",
                "source": "dagster_day2_smoke_boundary",
                "gap": "dagster_day2_smoke_failed",
                "owner_team": "data-platform-team",
                "message": "Local Dagster day-2 smoke did not prove retry events, schedule tick ledger and backfill materialization history.",
                "failed_checks": dagster_day2_summary.get("failed_checks", []),
            }
        )
    for gap in smoke_not_covered:
        if catalog_runtime_ops_closes_gap(str(gap), catalog_runtime_release_gate_passed):
            continue
        if secret_rotation_ops_closes_gap(str(gap), secret_rotation_ops_release_gate_passed):
            continue
        if orchestration_runtime_ops_closes_gap(str(gap), orchestration_runtime_release_gate_passed):
            continue
        if gap == "live_kafka_redpanda_broker_flow" and event_backbone_report and event_backbone_report.get("passed") is True:
            continue
        if gap == "trino_or_dremio_sql_runtime_query" and trino_sql_report and trino_sql_report.get("passed") is True:
            continue
        if gap == "dagster_or_airflow_run_history" and dagster_orchestration_report and dagster_orchestration_report.get("passed") is True:
            continue
        if gap == "iceberg_table_commit" and iceberg_catalog_report and iceberg_catalog_report.get("passed") is True:
            continue
        if gap in {"minio_object_store_iceberg_warehouse", "trino_iceberg_connector", "minio_federated_query"} and trino_iceberg_minio_report and trino_iceberg_minio_report.get("passed") is True:
            continue
        if gap == "runtime_security_enforcement" and runtime_security_passed:
            continue
        backlog.append(
            {
                "priority": "P0",
                "source": "data_plane_smoke_boundary",
                "gap": str(gap),
                "owner_team": "data-platform-team",
            }
        )
    if backfill_readiness_report is not None and not backfill_change_governance_release_gate_passed:
        summary = (
            backfill_readiness_report.get("summary")
            if isinstance(backfill_readiness_report.get("summary"), dict)
            else {}
        )
        backlog.append(
            {
                "priority": "P0",
                "source": "backfill_readiness_boundary",
                "gap": "backfill_readiness_release_gate_failed",
                "owner_team": "data-platform-team",
                "capability_id": "backfill-change-governance",
                "message": "Backfill readiness evidence did not prove a production-like, runtime-attested, hash-bound governed backfill release gate.",
                "failed_check_count": summary.get("failed_check_count", 0),
                "attached_evidence_count": summary.get("attached_evidence_count", 0),
            }
        )
    blockers = control_tower_report.get("blockers") if isinstance(control_tower_report.get("blockers"), list) else []
    for blocker in blockers[:50]:
        if not isinstance(blocker, dict) or blocker.get("severity") != "P0":
            continue
        if live_bronze_ingestion_passed and blocker.get("gate") == "p0_capability_target_met" and blocker.get(
            "capability_id"
        ) in {"event-cdc-ingestion-runtime", "bronze-lakehouse-evidence"}:
            continue
        if (
            orchestrated_publication_passed
            and blocker.get("gate") == "p0_capability_target_met"
            and blocker.get("capability_id") == "silver-gold-publication"
        ):
            continue
        if (
            live_quality_slo_passed
            and blocker.get("gate") == "p0_capability_target_met"
            and blocker.get("capability_id") == "quality-slo-release-gates"
        ):
            continue
        if (
            access_privacy_release_gate_passed
            and blocker.get("gate") == "p0_capability_target_met"
            and blocker.get("capability_id") == "access-privacy-enforcement"
        ):
            continue
        if (
            schema_registry_release_gate_passed
            and blocker.get("gate") == "p0_capability_target_met"
            and blocker.get("capability_id") == "schema-registry-compatibility"
        ):
            continue
        if (
            catalog_lineage_release_gate_passed
            and blocker.get("capability_id") == "catalog-lineage-control-plane"
            and blocker.get("gate") in {"p0_capability_target_met", "catalog_lineage_ops_passed"}
        ):
            continue
        if (
            semantic_metric_serving_release_gate_passed
            and blocker.get("capability_id") == "semantic-metric-serving"
            and blocker.get("gate") in {"p0_capability_target_met", "semantic_metric_serving_ops_passed"}
        ):
            continue
        if (
            source_onboarding_release_gate_passed
            and blocker.get("capability_id") == "source-onboarding"
            and blocker.get("gate") in {"p0_capability_target_met", "source_activation_ops_p0_clear"}
        ):
            continue
        if (
            backfill_change_governance_release_gate_passed
            and blocker.get("capability_id") == "backfill-change-governance"
            and blocker.get("gate") == "p0_capability_target_met"
        ):
            continue
        if (
            runtime_iac_release_gate_passed
            and blocker.get("capability_id") == "platform-runtime-iac"
            and blocker.get("gate") in {"p0_capability_target_met", "runtime_readiness_passed"}
        ):
            continue
        backlog.append(
            {
                "priority": "P0",
                "source": "control_tower_blocker",
                "gap": str(blocker.get("gate") or "unknown"),
                "scope": blocker.get("scope"),
                "data_product": blocker.get("data_product"),
                "capability_id": blocker.get("capability_id"),
                "owner_team": blocker.get("owner_team"),
                "domain": blocker.get("domain"),
                "message": blocker.get("message"),
            }
        )
    return backlog


def stable_id(*parts: object) -> str:
    value = "|".join(canonical_json(part) if isinstance(part, (dict, list)) else ("" if part is None else str(part)) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
