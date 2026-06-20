from __future__ import annotations

import argparse
import json
from pathlib import Path

from enterprise_dp.access_grants import (
    validate_access_grant_registry,
    write_access_grant_evidence_report,
    write_access_grant_ops_report,
)
from enterprise_dp.access_governance import validate_access_persona_registry, validate_consumer_contract_registry
from enterprise_dp.access_policies import validate_access_policy_registry
from enterprise_dp.access_policy import write_access_policy_report
from enterprise_dp.attestations import (
    validate_evidence_trust_key_registry,
    verify_attestation_file,
    write_schema_registry_publication_attestation,
)
from enterprise_dp.backfill import validate_backfill_request_registry, write_backfill_readiness_report
from enterprise_dp.broker_acl_smoke import write_broker_acl_smoke_report
from enterprise_dp.capabilities import validate_capability_registry, write_capability_maturity_report
from enterprise_dp.catalog import write_catalog_bundle
from enterprise_dp.catalog_compatibility_smoke import write_catalog_compatibility_smoke_report
from enterprise_dp.catalog_lineage_ops import write_catalog_lineage_ops_report
from enterprise_dp.catalog_publish import write_catalog_publish_manifest
from enterprise_dp.catalog_runtime_ops import write_catalog_runtime_ops_report
from enterprise_dp.change_requests import validate_change_request_registry, write_change_control_evidence_report
from enterprise_dp.contract_impact import write_contract_impact_report
from enterprise_dp.contracts import ValidationResult, validate_contract_tree
from enterprise_dp.control_tower import write_data_product_control_tower_report
from enterprise_dp.data_plane_smoke import DEFAULT_RELEASE_ID, DEFAULT_USE_CASE_ID, write_data_plane_smoke_report
from enterprise_dp.dagster_day2_smoke import write_dagster_day2_smoke_report
from enterprise_dp.dagster_orchestration_smoke import write_dagster_orchestration_smoke_report
from enterprise_dp.domains import validate_domain_registry
from enterprise_dp.environments import validate_environment_manifests
from enterprise_dp.event_backbone_smoke import write_event_backbone_smoke_report
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.ingestion_runtime import write_ingestion_runtime_evidence_artifact, write_ingestion_runtime_ops_report
from enterprise_dp.iceberg_catalog_smoke import write_iceberg_catalog_smoke_report
from enterprise_dp.incidents import validate_incident_registry, write_incident_report
from enterprise_dp.lakehouse_ops import write_bronze_lakehouse_ops_report
from enterprise_dp.live_lakehouse_smoke import write_live_lakehouse_smoke_report
from enterprise_dp.live_bronze_ingestion_smoke import write_live_bronze_ingestion_smoke_report
from enterprise_dp.live_quality_slo_smoke import write_live_quality_slo_smoke_report
from enterprise_dp.observability import write_observability_artifacts
from enterprise_dp.object_store_smoke import write_object_store_commit_smoke_report
from enterprise_dp.oidc_auth_smoke import write_oidc_auth_smoke_report
from enterprise_dp.openlineage import write_openlineage_events
from enterprise_dp.orchestrated_publication_smoke import write_orchestrated_publication_smoke_report
from enterprise_dp.orchestration import run_recommendation_slice, run_use_case
from enterprise_dp.orchestration_runtime_ops import write_orchestration_runtime_ops_report
from enterprise_dp.offset_ledger import write_offset_ledger_report
from enterprise_dp.pipeline_registry_manifest import validate_pipeline_registry_manifest
from enterprise_dp.pipelines import PipelineRunRequest, default_pipeline_registry, run_recommendation_pipeline_from_bronze
from enterprise_dp.pipelines.lms_recommendation import run_lms_recommendation_training_from_bronze
from enterprise_dp.portfolio import write_enterprise_portfolio_readiness_report
from enterprise_dp.portfolio_release_smoke import write_portfolio_release_smoke_report
from enterprise_dp.production_review_gate import write_production_review_gate_report
from enterprise_dp.policy_decision_smoke import write_policy_decision_smoke_report
from enterprise_dp.production_review_pack import write_production_review_pack
from enterprise_dp.publication_ops import write_silver_gold_publication_ops_report
from enterprise_dp.products import scaffold_product_onboarding, validate_product_onboarding_tree
from enterprise_dp.promotion import write_release_activation_manifest, write_release_promotion_manifest
from enterprise_dp.quality_slo_ops import write_quality_slo_ops_report
from enterprise_dp.quality_profiles import validate_quality_profile_registry
from enterprise_dp.retention import validate_retention_policy_registry, write_retention_evidence_report
from enterprise_dp.release_profiles import validate_release_profile_registry
from enterprise_dp.runtime import (
    validate_runtime_topology,
    write_runtime_evidence_pack,
    write_runtime_iac_evidence_pack,
    write_runtime_readiness_report,
)
from enterprise_dp.schema_registry import write_schema_registry_ops_report, write_schema_registry_report
from enterprise_dp.schema_registry_auth_smoke import write_schema_registry_auth_smoke_report
from enterprise_dp.schema_registry_runtime_smoke import write_schema_registry_runtime_smoke_report
from enterprise_dp.schema_registry_storage_smoke import write_schema_registry_storage_smoke_report
from enterprise_dp.secret_rotation_ops import write_secret_rotation_ops_report
from enterprise_dp.secret_rotation_smoke import write_secret_rotation_smoke_report
from enterprise_dp.semantic_metric_certification import (
    validate_semantic_metric_certification_registry,
    write_semantic_metric_certification_report,
)
from enterprise_dp.semantic_serving_ops import write_semantic_metric_serving_ops_report
from enterprise_dp.source_activation_ledger import (
    write_source_activation_ops_report,
    validate_source_activation_registry,
    write_source_activation_manifest_from_bundle,
    write_source_revocation_manifest,
)
from enterprise_dp.source_bridge import run_source_bridge_preflight
from enterprise_dp.source_readiness_bundle import run_source_readiness_bundle
from enterprise_dp.scope_guardrails import validate_scope_guardrails
from enterprise_dp.semantic_metrics import validate_semantic_metric_registry
from enterprise_dp.semantic_views import write_semantic_view_manifest
from enterprise_dp.snapshot_evidence import write_snapshot_evidence_report
from enterprise_dp.source_registry import validate_source_registry, write_source_readiness_report
from enterprise_dp.structure import validate_project_structure
from enterprise_dp.transactional_outbox_smoke import write_transactional_outbox_smoke_report
from enterprise_dp.trino_sql_smoke import write_trino_sql_runtime_smoke_report
from enterprise_dp.trino_iceberg_minio_smoke import write_trino_iceberg_minio_smoke_report
from enterprise_dp.trino_runtime_security_smoke import write_trino_runtime_security_smoke_report
from enterprise_dp.usecases import validate_use_case_registry


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="enterprise-dp",
        description="Validate and run local enterprise data platform tooling.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate contracts under dp/.")
    validate_parser.add_argument(
        "--root",
        default=".",
        help="Data platform root directory. Use repository dp/ path when running outside dp.",
    )
    product_scaffold_parser = subparsers.add_parser(
        "product-scaffold",
        help="Create a planned product onboarding pack for a new enterprise product.",
    )
    product_scaffold_parser.add_argument("--root", default=".", help="Data platform root directory.")
    product_scaffold_parser.add_argument("--product-code", required=True, help="Kebab-case product code.")
    product_scaffold_parser.add_argument("--name", required=True, help="Human-readable product name.")
    product_scaffold_parser.add_argument("--domain", action="append", required=True, help="Enterprise/source domain. Repeatable.")
    product_scaffold_parser.add_argument("--business-sponsor", required=True, help="Business sponsor id or team.")
    product_scaffold_parser.add_argument("--product-owner", required=True, help="Product owner id or team.")
    product_scaffold_parser.add_argument("--technical-owner", required=True, help="Technical owner id or team.")
    product_scaffold_parser.add_argument("--data-steward", default="enterprise-data-steward", help="Data steward id or team.")
    product_scaffold_parser.add_argument("--status", default="draft", choices=("draft", "pilot", "active", "deprecated"))
    product_scaffold_parser.add_argument("--source-service", action="append", default=[], help="Source service. Repeatable.")
    product_scaffold_parser.add_argument(
        "--publication-mode",
        action="append",
        default=[],
        help="Publication mode such as transactional_outbox, cdc, saas_connector or batch_connector. Repeatable.",
    )
    product_scaffold_parser.add_argument("--consumer", action="append", default=[], help="Consumer channel/persona label. Repeatable.")
    product_scaffold_parser.add_argument("--classification", default="CONFIDENTIAL", help="Default product data classification.")
    product_scaffold_parser.add_argument(
        "--contains-pii",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Whether the product first slice may contain PII.",
    )
    product_scaffold_parser.add_argument("--tenant-isolation", default="REQUIRED", help="Default tenant isolation stance.")
    product_scaffold_parser.add_argument("--retention-policy", default="standard_personal_data_3y", help="Default retention policy id.")
    product_scaffold_parser.add_argument(
        "--access-persona",
        action="append",
        default=[],
        help="Default access persona id. Repeatable.",
    )
    product_scaffold_parser.add_argument(
        "--consumer-contract",
        default="catalog_registered_access_request_required",
        help="Default consumer contract id.",
    )
    product_scaffold_parser.add_argument(
        "--release-evidence-profile",
        default="local-medallion-release.v1",
        help="Default release evidence profile id.",
    )
    product_scaffold_parser.add_argument("--overwrite", action="store_true", help="Replace existing onboarding.yaml if present.")
    ingest_parser = subparsers.add_parser(
        "ingest-bronze",
        help="Run local contract-checked JSONL ingestion into approved Bronze/quarantine outputs.",
    )
    ingest_parser.add_argument("--root", default=".", help="Data platform root directory.")
    ingest_parser.add_argument("--topic", required=True, help="Topic contract name, for example recommendation.tracking.v1.")
    ingest_parser.add_argument("--input", required=True, help="Input JSONL file containing enterprise event envelopes.")
    ingest_parser.add_argument("--output-dir", required=True, help="Output directory for Bronze, quarantine and manifest files.")
    ingest_parser.add_argument("--ingested-at", default=None, help="UTC ingestion timestamp override.")
    ingest_parser.add_argument("--ingest-run-id", default=None, help="Stable run id for replay/evidence.")
    ingest_parser.add_argument("--schema-id", default=None, help="Schema registry id or local compatibility id.")
    recommendation_parser = subparsers.add_parser(
        "build-recommendation",
        help="Build local Silver/Gold recommendation outputs from approved Bronze JSONL.",
    )
    recommendation_parser.add_argument("--bronze", required=True, help="Approved Bronze JSONL path.")
    recommendation_parser.add_argument("--output-dir", required=True, help="Output directory for Silver, Gold and manifest.")
    recommendation_parser.add_argument("--upstream-manifest", default=None, help="Bronze ingestion manifest path.")
    recommendation_parser.add_argument("--snapshot-id", default=None, help="Gold dataset snapshot id.")
    recommendation_parser.add_argument("--built-at", default=None, help="UTC build timestamp override.")
    lms_recommendation_parser = subparsers.add_parser(
        "build-lms-recommendation-training",
        help="Build LMS course catalog and recommendation training feature snapshots from approved Bronze.",
    )
    lms_recommendation_parser.add_argument("--course-bronze", required=True, help="Approved course.published Bronze JSONL path.")
    lms_recommendation_parser.add_argument("--enrollment-bronze", required=True, help="Approved enrollment.completed Bronze JSONL path.")
    lms_recommendation_parser.add_argument("--output-dir", required=True, help="Output directory for Gold feature snapshots and manifest.")
    lms_recommendation_parser.add_argument(
        "--upstream-manifest",
        action="append",
        default=[],
        help="Upstream Bronze/source manifest path. Can be passed multiple times.",
    )
    lms_recommendation_parser.add_argument("--snapshot-id", default=None, help="Gold dataset snapshot id.")
    lms_recommendation_parser.add_argument("--built-at", default=None, help="UTC build timestamp override.")
    catalog_parser = subparsers.add_parser(
        "catalog-export",
        help="Export catalog and lineage metadata bundle from contracts and run manifests.",
    )
    catalog_parser.add_argument("--root", default=".", help="Data platform root directory.")
    catalog_parser.add_argument("--output", required=True, help="Output JSON bundle path.")
    catalog_parser.add_argument(
        "--manifest",
        action="append",
        default=[],
        help="Pipeline or ingestion manifest path. Can be passed multiple times.",
    )
    catalog_parser.add_argument("--generated-at", default=None, help="UTC generated_at override for deterministic exports.")
    openlineage_parser = subparsers.add_parser(
        "openlineage-export",
        help="Export OpenLineage-style runtime events from a catalog bundle.",
    )
    openlineage_parser.add_argument("--catalog", required=True, help="Catalog bundle JSON path.")
    openlineage_parser.add_argument("--output", required=True, help="Output JSONL path for OpenLineage events.")
    openlineage_parser.add_argument("--namespace", default="enterprise-dp://local", help="OpenLineage job and dataset namespace.")
    openlineage_parser.add_argument(
        "--producer",
        default="https://enterprise-dp.local/openlineage-export",
        help="OpenLineage producer URI.",
    )
    catalog_publish_parser = subparsers.add_parser(
        "catalog-publish-manifest",
        help="Create an auditable publish manifest for DataHub/OpenMetadata catalog publication.",
    )
    catalog_publish_parser.add_argument("--catalog", required=True, help="Catalog bundle JSON path.")
    catalog_publish_parser.add_argument("--output", required=True, help="Output catalog publish manifest path.")
    catalog_publish_parser.add_argument("--target-system", required=True, choices=("datahub", "openmetadata"), help="Catalog backend target.")
    catalog_publish_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Target environment.")
    catalog_publish_parser.add_argument("--endpoint", default=None, help="Catalog endpoint URI for staging/prod publish.")
    catalog_publish_parser.add_argument("--openlineage-events", default=None, help="Optional OpenLineage JSONL artifact path.")
    catalog_publish_parser.add_argument("--semantic-views", default=None, help="Optional semantic views manifest path.")
    catalog_publish_parser.add_argument("--requested-by", default=None, help="Requester identity for production-like audit.")
    catalog_publish_parser.add_argument("--change-ticket", default=None, help="Change ticket for production-like audit.")
    catalog_publish_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    catalog_lineage_ops_parser = subparsers.add_parser(
        "catalog-lineage-ops-report",
        help="Write catalog and lineage operations report from catalog, publish, OpenLineage and publish receipt evidence.",
    )
    catalog_lineage_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    catalog_lineage_ops_parser.add_argument("--output", required=True, help="Output catalog_lineage_ops_report.v1 JSON path.")
    catalog_lineage_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    catalog_lineage_ops_parser.add_argument("--catalog", default=None, help="Optional catalog bundle JSON path. If omitted, generated from root.")
    catalog_lineage_ops_parser.add_argument("--catalog-publish-manifest", default=None, help="Optional catalog_publish_manifest.v1 JSON artifact.")
    catalog_lineage_ops_parser.add_argument("--openlineage-events", default=None, help="Optional OpenLineage JSONL artifact.")
    catalog_lineage_ops_parser.add_argument("--publish-receipt", default=None, help="Optional catalog_publish_receipt.v1 JSON artifact from DataHub/OpenMetadata publish job.")
    catalog_lineage_ops_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    catalog_runtime_ops_parser = subparsers.add_parser(
        "catalog-runtime-ops-report",
        help="Write production-like Iceberg catalog runtime HA, failover, backup and concurrency evidence.",
    )
    catalog_runtime_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    catalog_runtime_ops_parser.add_argument("--output", required=True, help="Output catalog_runtime_ops_report.v1 JSON path.")
    catalog_runtime_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"))
    catalog_runtime_ops_parser.add_argument("--evidence", default=None, help="Optional managed_catalog_runtime_evidence.v1 JSON artifact.")
    catalog_runtime_ops_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    orchestration_runtime_ops_parser = subparsers.add_parser(
        "orchestration-runtime-ops-report",
        help="Write production-like orchestration runtime HA, distributed launcher, run storage and day-2 evidence.",
    )
    orchestration_runtime_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    orchestration_runtime_ops_parser.add_argument("--output", required=True, help="Output orchestration_runtime_ops_report.v1 JSON path.")
    orchestration_runtime_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"))
    orchestration_runtime_ops_parser.add_argument("--evidence", default=None, help="Optional managed_orchestration_runtime_evidence.v1 JSON artifact.")
    orchestration_runtime_ops_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    observability_parser = subparsers.add_parser(
        "observability-export",
        help="Export Prometheus metrics and an operations summary from catalog and release evidence.",
    )
    observability_parser.add_argument("--catalog", required=True, help="Catalog bundle JSON path.")
    observability_parser.add_argument("--output-metrics", required=True, help="Prometheus text metrics output path.")
    observability_parser.add_argument("--output-summary", required=True, help="JSON operations summary output path.")
    observability_parser.add_argument(
        "--release-evidence",
        action="append",
        default=[],
        help="Release evidence JSON path. Can be passed multiple times.",
    )
    observability_parser.add_argument("--environment", default="local", help="Environment label.")
    observability_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    quality_slo_ops_parser = subparsers.add_parser(
        "quality-slo-release-gates-ops-report",
        help="Write quality and SLO operations report from release, runtime quality, alert and incident evidence.",
    )
    quality_slo_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    quality_slo_ops_parser.add_argument("--output", required=True, help="Output quality_slo_release_gates_ops_report.v1 JSON path.")
    quality_slo_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    quality_slo_ops_parser.add_argument("--catalog", default=None, help="Optional catalog bundle JSON path. If omitted, generated from root.")
    quality_slo_ops_parser.add_argument("--release-evidence", action="append", default=[], help="Release evidence JSON artifact. Repeatable.")
    quality_slo_ops_parser.add_argument("--quality-runtime-evidence", default=None, help="Optional quality_runtime_evidence.v1 JSON artifact.")
    quality_slo_ops_parser.add_argument("--alert-evidence", default=None, help="Optional slo_alert_evidence.v1 JSON artifact.")
    quality_slo_ops_parser.add_argument("--incident-report", default=None, help="Optional incident_slo_report.v1 JSON artifact.")
    quality_slo_ops_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    semantic_views_parser = subparsers.add_parser(
        "semantic-views-export",
        help="Export deployable Trino/Dremio semantic view SQL manifest from semantic metric definitions.",
    )
    semantic_views_parser.add_argument("--root", default=".", help="Data platform root directory.")
    semantic_views_parser.add_argument("--output", required=True, help="Output semantic views manifest JSON path.")
    semantic_views_parser.add_argument("--engine", choices=("all", "trino", "dremio"), default="all", help="Target serving engine.")
    semantic_views_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    semantic_certification_parser = subparsers.add_parser(
        "semantic-metric-certification-report",
        help="Write semantic metric certification evidence with maker-checker, diff and impact checks.",
    )
    semantic_certification_parser.add_argument("--root", default=".", help="Data platform root directory.")
    semantic_certification_parser.add_argument("--output", required=True, help="Output semantic_metric_certification_report.v1 JSON path.")
    semantic_certification_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    semantic_certification_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    semantic_serving_ops_parser = subparsers.add_parser(
        "semantic-metric-serving-ops-report",
        help="Write semantic metric serving operations report from registry, view manifest, deployment and usage evidence.",
    )
    semantic_serving_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    semantic_serving_ops_parser.add_argument("--output", required=True, help="Output semantic_metric_serving_ops_report.v1 JSON path.")
    semantic_serving_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    semantic_serving_ops_parser.add_argument("--semantic-view-manifest", default=None, help="Optional semantic_views_manifest.v1 JSON artifact.")
    semantic_serving_ops_parser.add_argument("--metric-certification-report", default=None, help="Optional semantic_metric_certification_report.v1 JSON artifact.")
    semantic_serving_ops_parser.add_argument("--serving-deployment-evidence", default=None, help="Optional semantic_serving_deployment_evidence.v1 JSON artifact.")
    semantic_serving_ops_parser.add_argument("--usage-evidence", default=None, help="Optional semantic_metric_usage_evidence.v1 JSON artifact.")
    semantic_serving_ops_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    capability_parser = subparsers.add_parser(
        "capability-maturity-report",
        help="Write enterprise data platform capability maturity and production-readiness report.",
    )
    capability_parser.add_argument("--root", default=".", help="Data platform root directory.")
    capability_parser.add_argument("--output", required=True, help="Output capability maturity report JSON path.")
    capability_parser.add_argument("--phase", choices=("P0", "P1", "P2", "P3"), default=None, help="Optional phase filter.")
    capability_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    control_tower_parser = subparsers.add_parser(
        "control-tower-report",
        help="Write the enterprise Data Product Control Tower readiness report.",
    )
    control_tower_parser.add_argument("--root", default=".", help="Data platform root directory.")
    control_tower_parser.add_argument("--output", required=True, help="Output control tower report JSON path.")
    control_tower_parser.add_argument("--catalog", default=None, help="Optional catalog bundle JSON artifact.")
    control_tower_parser.add_argument("--catalog-lineage-ops-report", default=None, help="Optional catalog_lineage_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--quality-slo-release-gates-ops-report", default=None, help="Optional quality_slo_release_gates_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--semantic-metric-serving-ops-report", default=None, help="Optional semantic_metric_serving_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--schema-registry-ops-report", default=None, help="Optional schema_registry_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--catalog-runtime-ops-report", default=None, help="Optional catalog_runtime_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--orchestration-runtime-ops-report", default=None, help="Optional orchestration_runtime_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--data-plane-smoke-report", default=None, help="Optional data_plane_smoke_report.v1 JSON artifact from enterprise-dp data-plane-smoke.")
    control_tower_parser.add_argument(
        "--release-evidence",
        action="append",
        default=[],
        help="Optional release evidence JSON artifact. Can be passed multiple times.",
    )
    control_tower_parser.add_argument("--capability-maturity-report", default=None, help="Optional capability maturity report JSON artifact.")
    control_tower_parser.add_argument("--access-grant-ops-report", default=None, help="Optional access_grant_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--source-activation-ops-report", default=None, help="Optional source_activation_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--ingestion-runtime-report", default=None, help="Optional event_cdc_ingestion_runtime_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--bronze-lakehouse-ops-report", default=None, help="Optional bronze_lakehouse_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--silver-gold-publication-ops-report", default=None, help="Optional silver_gold_publication_ops_report.v1 JSON artifact.")
    control_tower_parser.add_argument("--runtime-readiness-report", default=None, help="Optional runtime_readiness_report.v1 JSON artifact.")
    control_tower_parser.add_argument(
        "--contract-impact-report",
        action="append",
        default=[],
        help="Optional contract_impact_report.v1 JSON artifact. Can be passed multiple times.",
    )
    control_tower_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Control Tower target environment.")
    control_tower_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    incident_parser = subparsers.add_parser(
        "incident-report",
        help="Create an operational incident/SLO report from a Data Product Control Tower report.",
    )
    incident_parser.add_argument("--control-tower-report", required=True, help="Input data_product_control_tower_report.v1 JSON path.")
    incident_parser.add_argument("--output", required=True, help="Output incident_slo_report.v1 JSON path.")
    incident_parser.add_argument("--incident-registry", default=None, help="Optional governance/incidents.yaml state registry.")
    incident_parser.add_argument("--environment", default=None, choices=("local", "staging", "prod"), help="Override environment label.")
    incident_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    portfolio_parser = subparsers.add_parser(
        "portfolio-readiness-report",
        help="Write the group-wide product and use-case portfolio readiness decision report.",
    )
    portfolio_parser.add_argument("--root", default=".", help="Data platform root directory.")
    portfolio_parser.add_argument("--output", required=True, help="Output portfolio readiness report JSON path.")
    portfolio_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Portfolio target environment.")
    portfolio_parser.add_argument(
        "--source-activation-ledger",
        default=None,
        help="Optional governance/source-activations.yaml overlay for effective source readiness.",
    )
    portfolio_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    runtime_parser = subparsers.add_parser(
        "runtime-readiness-check",
        aliases=("runtime-iac-readiness-check",),
        help="Write Platform Runtime/IaC readiness evidence from topology, environment and IaC metadata.",
    )
    runtime_parser.add_argument("--root", default=".", help="Data platform root directory.")
    runtime_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Target runtime environment.")
    runtime_parser.add_argument("--output", required=True, help="Output runtime readiness report path.")
    runtime_parser.add_argument("--iac-plan", default=None, help="runtime_iac_plan_evidence.v1 JSON artifact.")
    runtime_parser.add_argument("--iac-apply", default=None, help="runtime_iac_apply_evidence.v1 JSON artifact.")
    runtime_parser.add_argument("--drift-report", default=None, help="runtime_iac_drift_report.v1 JSON artifact.")
    runtime_parser.add_argument("--backup-report", default=None, help="runtime_backup_evidence.v1 JSON artifact.")
    runtime_parser.add_argument("--dr-report", default=None, help="runtime_dr_evidence.v1 JSON artifact.")
    runtime_parser.add_argument("--health-report", default=None, help="runtime_service_health_evidence.v1 JSON artifact.")
    runtime_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    runtime_pack_parser = subparsers.add_parser(
        "runtime-evidence-pack",
        help="Create a normalized runtime evidence artifact pack for CI/CD, SRE checks or local contract fixtures.",
    )
    runtime_pack_parser.add_argument("--root", default=".", help="Data platform root directory.")
    runtime_pack_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Target runtime environment.")
    runtime_pack_parser.add_argument("--output-dir", required=True, help="Directory to write runtime evidence artifacts.")
    runtime_pack_parser.add_argument(
        "--source-kind",
        default="synthetic_fixture",
        choices=("synthetic_fixture", "ci_tool_output", "external_attestation"),
        help="Evidence origin. synthetic_fixture is never accepted for staging/prod readiness.",
    )
    runtime_pack_parser.add_argument("--git-sha", required=True, help="Source commit SHA for the runtime evidence.")
    runtime_pack_parser.add_argument("--ci-run-id", required=True, help="CI/CD or SRE run id that produced the evidence.")
    runtime_pack_parser.add_argument("--artifact-base-uri", required=True, help="Durable base URI for evidence artifacts.")
    runtime_pack_parser.add_argument("--issuer-tool", default="enterprise-dp-runtime-evidence-pack", help="Evidence issuer tool name.")
    runtime_pack_parser.add_argument("--issuer-tool-version", default="0.1.0", help="Evidence issuer tool version.")
    runtime_pack_parser.add_argument("--change-request-id", default=None, help="Required for production readiness evidence.")
    runtime_pack_parser.add_argument("--include-dr", action="store_true", help="Include DR evidence; prod includes it by default.")
    runtime_pack_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    runtime_pack_parser.add_argument("--valid-until", default=None, help="UTC expiry timestamp for generated evidence.")
    runtime_pack_parser.add_argument("--destructive-change-count", type=int, default=0, help="Plan destructive change count.")
    runtime_pack_parser.add_argument("--drifted-resource-count", type=int, default=0, help="Drifted resource count.")
    runtime_iac_parser = subparsers.add_parser(
        "runtime-evidence-normalize-iac",
        help="Normalize OpenTofu/Terraform machine JSON and SRE check JSON into runtime evidence artifacts.",
    )
    runtime_iac_parser.add_argument("--root", default=".", help="Data platform root directory.")
    runtime_iac_parser.add_argument("--environment", required=True, choices=("staging", "prod"), help="Target runtime environment.")
    runtime_iac_parser.add_argument("--output-dir", required=True, help="Directory to write normalized runtime evidence artifacts.")
    runtime_iac_parser.add_argument("--plan-json", required=True, help="JSON from tofu/terraform show -json for a plan file.")
    runtime_iac_parser.add_argument("--state-json", required=True, help="JSON from tofu/terraform show -json for state after apply.")
    runtime_iac_parser.add_argument("--health-checks", required=True, help="Machine-readable runtime service health check JSON.")
    runtime_iac_parser.add_argument("--backup-checks", required=True, help="Machine-readable backup/restore evidence JSON.")
    runtime_iac_parser.add_argument("--dr-exercise", default=None, help="Machine-readable DR exercise JSON. Required for prod readiness.")
    runtime_iac_parser.add_argument("--resource-map", default=None, help="Optional resource address prefix to runtime service map YAML/JSON.")
    runtime_iac_parser.add_argument("--source-kind", default="ci_tool_output", choices=("ci_tool_output", "external_attestation"))
    runtime_iac_parser.add_argument("--git-sha", required=True, help="Source commit SHA for the runtime evidence.")
    runtime_iac_parser.add_argument("--ci-run-id", required=True, help="CI/CD or SRE run id that produced the evidence.")
    runtime_iac_parser.add_argument("--artifact-base-uri", required=True, help="Durable base URI for normalized evidence artifacts.")
    runtime_iac_parser.add_argument("--issuer-tool", default="opentofu", help="Evidence issuer tool name.")
    runtime_iac_parser.add_argument("--issuer-tool-version", required=True, help="Evidence issuer tool version.")
    runtime_iac_parser.add_argument("--change-request-id", default=None, help="Required for production readiness evidence.")
    runtime_iac_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    runtime_iac_parser.add_argument("--valid-until", default=None, help="UTC expiry timestamp for generated evidence.")
    attestation_parser = subparsers.add_parser(
        "attestation-verify",
        help="Verify a signed external evidence attestation against the trust key registry.",
    )
    attestation_parser.add_argument("--root", default=".", help="Data platform root directory.")
    attestation_parser.add_argument("--input", required=True, help="external_evidence_attestation.v1 JSON file.")
    attestation_parser.add_argument(
        "--evidence-kind",
        required=True,
        choices=("schema_registry", "access_policy", "access_grant", "retention_erasure"),
        help="Expected evidence kind.",
    )
    attestation_parser.add_argument("--environment", required=True, help="Expected release environment.")
    attestation_parser.add_argument("--release-id", default=None, help="Optional expected release id.")
    attestation_parser.add_argument("--subject", default=None, help="Optional subject artifact path whose hash must match.")
    attestation_parser.add_argument("--subject-hash", default=None, help="Optional expected subject hash.")
    schema_attestation_parser = subparsers.add_parser(
        "schema-registry-attestation",
        help="Sign a schema_registry_publication_manifest.v1 with an Ed25519 external evidence attestation.",
    )
    schema_attestation_parser.add_argument("--root", default=".", help="Data platform root directory.")
    schema_attestation_parser.add_argument("--publication-manifest", required=True, help="schema_registry_publication_manifest.v1 path.")
    schema_attestation_parser.add_argument("--output", required=True, help="Output external_evidence_attestation.v1 JSON path.")
    schema_attestation_parser.add_argument(
        "--schema-registry-runtime-smoke-report",
        required=True,
        help="schema_registry_runtime_smoke_report.v1 used to bind the publication manifest hash.",
    )
    schema_attestation_parser.add_argument("--environment", default="staging", choices=("staging", "prod"))
    schema_attestation_parser.add_argument("--release-id", default=None, help="Attestation release id. Defaults to schema runtime release id.")
    schema_attestation_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    schema_attestation_parser.add_argument("--subject-uri", default=None, help="Durable evidence URI to place in the signed subject_uri.")
    schema_attestation_parser.add_argument("--signing-key-id", default="local-test-ed25519-2026", help="Trust registry key id.")
    schema_attestation_parser.add_argument("--producer", default="data-platform-control-plane", help="Attestation producer id.")
    schema_attestation_parser.add_argument(
        "--private-key-seed-base64",
        default=None,
        help="Base64 Ed25519 private key seed. If omitted, DP_EVIDENCE_ATTESTATION_PRIVATE_KEY_SEED_BASE64 is used; the local test key falls back to a CI fixture.",
    )
    promotion_parser = subparsers.add_parser(
        "release-promote",
        help="Create an auditable release promotion manifest from a passing release evidence pack.",
    )
    promotion_parser.add_argument("--release-evidence", required=True, help="Release evidence JSON path.")
    promotion_parser.add_argument("--output", required=True, help="Output release promotion manifest path.")
    promotion_parser.add_argument("--target-environment", required=True, help="Environment to activate the release in.")
    promotion_parser.add_argument("--requested-by", required=True, help="Requester identity for maker-checker audit.")
    promotion_parser.add_argument("--approver", required=True, help="Approver identity for maker-checker audit.")
    promotion_parser.add_argument("--change-ticket", default=None, help="Optional change or incident ticket.")
    promotion_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    activation_parser = subparsers.add_parser(
        "release-activate",
        help="Create a release activation manifest and update the active pointer when promotion is approved.",
    )
    activation_parser.add_argument("--promotion-manifest", required=True, help="Approved release promotion manifest path.")
    activation_parser.add_argument("--output", required=True, help="Output release activation manifest path.")
    activation_parser.add_argument("--active-state", required=True, help="Active pointer state JSON path.")
    activation_parser.add_argument("--activated-by", required=True, help="Activator identity for maker-checker audit.")
    activation_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    schema_parser = subparsers.add_parser(
        "schema-registry-check",
        help="Write a local schema registry compatibility report from topic contracts and JSON schemas.",
    )
    schema_parser.add_argument("--root", default=".", help="Data platform root directory.")
    schema_parser.add_argument("--output", required=True, help="Output JSON compatibility report path.")
    schema_parser.add_argument("--topic", default=None, help="Optional topic name to check.")
    schema_parser.add_argument("--registry-uri", default=None, help="Registry URI or local registry label.")
    schema_parser.add_argument("--generated-at", default=None, help="UTC generated_at override for deterministic reports.")
    schema_ops_parser = subparsers.add_parser(
        "schema-registry-ops-report",
        help="Write schema registry production governance report from compatibility and publication evidence.",
    )
    schema_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    schema_ops_parser.add_argument("--output", required=True, help="Output schema_registry_ops_report.v1 JSON path.")
    schema_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    schema_ops_parser.add_argument("--release-id", default=None, help="Optional release id bound to external attestation.")
    schema_ops_parser.add_argument("--compatibility-report", default=None, help="Optional schema_registry_compatibility_report.v1 JSON path.")
    schema_ops_parser.add_argument("--publication-evidence", default=None, help="Optional schema_registry_publication_manifest.v1 JSON path.")
    schema_ops_parser.add_argument("--attestation", default=None, help="Optional external_evidence_attestation.v1 for the publication evidence.")
    schema_ops_parser.add_argument("--generated-at", default=None, help="UTC generated_at override for deterministic reports.")
    schema_runtime_smoke_parser = subparsers.add_parser(
        "schema-registry-runtime-smoke",
        help="Publish topic JSON Schemas to local Apicurio ccompat v7 and verify read-back evidence.",
    )
    schema_runtime_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    schema_runtime_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for schema registry runtime smoke artifacts.")
    schema_runtime_smoke_parser.add_argument("--output", required=True, help="Output schema_registry_runtime_smoke_report.v1 JSON path.")
    schema_runtime_smoke_parser.add_argument("--topic-name", default=None, help="Optional single topic contract to publish. Defaults to all topics.")
    schema_runtime_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    schema_runtime_smoke_parser.add_argument("--service", default="schema-registry", help="Compose service name for Apicurio Registry.")
    schema_runtime_smoke_parser.add_argument("--registry-url", default="http://localhost:18082", help="Apicurio Registry base URL.")
    schema_runtime_smoke_parser.add_argument("--group-id", default="enterprise-dp-local-smoke", help="Apicurio registry group id.")
    schema_runtime_smoke_parser.add_argument("--release-id", default="local-schema-registry-runtime-smoke", help="Stable release/run id.")
    schema_runtime_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    schema_runtime_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    schema_runtime_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    schema_runtime_smoke_parser.add_argument("--wait-attempts", type=int, default=30)
    schema_runtime_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before registry calls.")
    schema_auth_smoke_parser = subparsers.add_parser(
        "schema-registry-auth-smoke",
        help="Run a local authn/authz gateway smoke in front of Apicurio Schema Registry.",
    )
    schema_auth_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    schema_auth_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for schema registry auth smoke artifacts.")
    schema_auth_smoke_parser.add_argument("--output", required=True, help="Output schema_registry_auth_smoke_report.v1 JSON path.")
    schema_auth_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    schema_auth_smoke_parser.add_argument("--service", default="schema-registry", help="Compose service name for Apicurio Registry.")
    schema_auth_smoke_parser.add_argument("--registry-url", default="http://localhost:18082", help="Apicurio Registry base URL.")
    schema_auth_smoke_parser.add_argument("--gateway-host", default="127.0.0.1", help="Local auth gateway host.")
    schema_auth_smoke_parser.add_argument("--gateway-port", type=int, default=18083, help="Local auth gateway port.")
    schema_auth_smoke_parser.add_argument("--group-id", default="enterprise-dp-auth-smoke", help="Apicurio registry group id.")
    schema_auth_smoke_parser.add_argument("--subject", default="dp.local.schema_registry_auth_smoke-value", help="Probe schema subject.")
    schema_auth_smoke_parser.add_argument("--release-id", default="local-schema-registry-auth-smoke", help="Stable release/run id.")
    schema_auth_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    schema_auth_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    schema_auth_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    schema_auth_smoke_parser.add_argument("--wait-attempts", type=int, default=30)
    schema_auth_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before registry calls.")
    schema_storage_smoke_parser = subparsers.add_parser(
        "schema-registry-storage-smoke",
        help="Run a local SQL-backed two-replica Apicurio Schema Registry storage smoke.",
    )
    schema_storage_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    schema_storage_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for schema registry storage smoke artifacts.")
    schema_storage_smoke_parser.add_argument("--output", required=True, help="Output schema_registry_storage_smoke_report.v1 JSON path.")
    schema_storage_smoke_parser.add_argument("--sql-image", default="apicurio/apicurio-registry-sql:2.6.5.Final")
    schema_storage_smoke_parser.add_argument("--postgres-image", default="postgres:16-alpine")
    schema_storage_smoke_parser.add_argument("--network", default="enterprise-dp-schema-registry-storage-smoke")
    schema_storage_smoke_parser.add_argument("--registry-a-port", type=int, default=18084)
    schema_storage_smoke_parser.add_argument("--registry-b-port", type=int, default=18085)
    schema_storage_smoke_parser.add_argument("--group-id", default="enterprise-dp-storage-smoke")
    schema_storage_smoke_parser.add_argument("--subject", default="dp.local.schema_registry_storage_smoke-value")
    schema_storage_smoke_parser.add_argument("--release-id", default="local-schema-registry-storage-smoke", help="Stable release/run id.")
    schema_storage_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    schema_storage_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    schema_storage_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=600)
    schema_storage_smoke_parser.add_argument("--wait-attempts", type=int, default=45)
    schema_storage_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Use already-running registry A/B URLs.")
    schema_storage_smoke_parser.add_argument("--no-cleanup-runtime", action="store_true", help="Leave local Docker containers running.")
    schema_storage_smoke_parser.add_argument("--registry-a-url", default=None, help="Registry A URL when --no-start-runtime is used.")
    schema_storage_smoke_parser.add_argument("--registry-b-url", default=None, help="Registry B URL when --no-start-runtime is used.")
    contract_impact_parser = subparsers.add_parser(
        "contract-impact-report",
        help="Write downstream impact and release decision for a topic contract/schema change.",
    )
    contract_impact_parser.add_argument("--root", default=".", help="Data platform root directory.")
    contract_impact_parser.add_argument("--topic", required=True, help="Topic name to evaluate, for example finance.billing_transaction.settled.v1.")
    contract_impact_parser.add_argument("--output", required=True, help="Output contract_impact_report.v1 JSON path.")
    contract_impact_parser.add_argument("--schema-registry-report", default=None, help="Optional schema_registry_compatibility_report.v1 JSON path.")
    contract_impact_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    source_bridge_parser = subparsers.add_parser(
        "source-bridge-normalize",
        help="Normalize raw registered source JSONL into canonical enterprise event envelopes.",
    )
    source_bridge_parser.add_argument("--root", default=".", help="Data platform root directory.")
    source_bridge_parser.add_argument("--source-id", required=True, help="Source id from platform/ingestion/source-registry.yaml.")
    source_bridge_parser.add_argument("--input", required=True, help="Raw source JSONL input path.")
    source_bridge_parser.add_argument("--output-dir", required=True, help="Output directory for normalized JSONL, quarantine and manifest.")
    source_bridge_parser.add_argument("--normalized-at", default=None, help="UTC normalization timestamp override.")
    source_bridge_parser.add_argument("--bridge-run-id", default=None, help="Stable bridge run id for replay/evidence.")
    source_bundle_parser = subparsers.add_parser(
        "source-readiness-bundle",
        help="Run source bridge if needed, Bronze ingestion, replay, ledger, catalog, lineage and readiness evidence.",
    )
    source_bundle_parser.add_argument("--root", default=".", help="Data platform root directory.")
    source_bundle_parser.add_argument("--source-id", required=True, help="Source id from platform/ingestion/source-registry.yaml.")
    source_bundle_parser.add_argument("--input", required=True, help="Canonical or raw source JSONL input path.")
    source_bundle_parser.add_argument("--output-dir", required=True, help="Output directory for all source readiness artifacts.")
    source_bundle_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Target readiness environment.")
    source_bundle_parser.add_argument("--bundle-id", default=None, help="Stable bundle id used in run ids.")
    source_bundle_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    source_bundle_parser.add_argument("--ingested-at", default=None, help="UTC first ingestion timestamp override.")
    source_bundle_parser.add_argument("--replayed-at", default=None, help="UTC replay ingestion timestamp override.")
    source_bundle_parser.add_argument("--schema-registry-uri", default=None, help="Production-like schema registry URI.")
    source_bundle_parser.add_argument("--change-request-id", default=None, help="Approved source_onboarding change request id.")
    source_bundle_parser.add_argument("--target-snapshot-id", default=None, help="Iceberg target snapshot id after Bronze commit.")
    source_bundle_parser.add_argument("--table-metadata-uri", default=None, help="Iceberg table metadata URI after Bronze commit.")
    source_bundle_parser.add_argument("--table-metadata-hash", default=None, help="SHA-256 hash of Iceberg table metadata.")
    source_bundle_parser.add_argument("--openlineage-namespace", default=None, help="OpenLineage namespace override.")
    source_bundle_parser.add_argument("--openlineage-producer", default=None, help="OpenLineage producer URI override.")
    source_activate_parser = subparsers.add_parser(
        "source-activate",
        help="Create an evidence-backed source activation manifest, append the activation ledger and update the active pointer.",
    )
    source_activate_parser.add_argument("--root", default=".", help="Data platform root directory.")
    source_activate_parser.add_argument("--bundle", required=True, help="source_readiness_bundle.v1 summary JSON path.")
    source_activate_parser.add_argument("--output", required=True, help="Output source_activation_manifest.v1 JSON path.")
    source_activate_parser.add_argument("--requested-by", required=True, help="Requester identity for maker-checker audit.")
    source_activate_parser.add_argument("--approved-by", required=True, help="Approver identity for maker-checker audit.")
    source_activate_parser.add_argument("--change-request-id", required=True, help="Approved source_onboarding change request id.")
    source_activate_parser.add_argument("--ledger", default=None, help="Activation ledger path. Defaults to governance/source-activations.yaml.")
    source_activate_parser.add_argument("--active-state", default=None, help="Active pointer JSON path. Defaults to per-source/per-env governance pointer.")
    source_activate_parser.add_argument("--expires-at", default=None, help="UTC expiry timestamp for the activation.")
    source_activate_parser.add_argument("--generated-at", default=None, help="UTC activation timestamp override.")
    source_activate_parser.add_argument("--impacted-use-case", action="append", default=[], help="Impacted use case id. Repeatable.")
    source_activate_parser.add_argument("--reason", default=None, help="Activation reason or approval note.")
    source_activate_parser.add_argument("--runtime-readiness-report", default=None, help="Required for staging/prod source activation.")
    source_revoke_parser = subparsers.add_parser(
        "source-revoke",
        help="Append a source activation revocation event and write a revoked active pointer tombstone.",
    )
    source_revoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    source_revoke_parser.add_argument("--source-id", required=True, help="Source id from platform/ingestion/source-registry.yaml.")
    source_revoke_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Activation environment to revoke.")
    source_revoke_parser.add_argument("--output", required=True, help="Output source_revocation_manifest.v1 JSON path.")
    source_revoke_parser.add_argument("--requested-by", required=True, help="Requester identity for maker-checker audit.")
    source_revoke_parser.add_argument("--approved-by", required=True, help="Approver identity for maker-checker audit.")
    source_revoke_parser.add_argument("--change-request-id", required=True, help="Approved source_activation_revoke change request id.")
    source_revoke_parser.add_argument("--ledger", default=None, help="Activation ledger path. Defaults to governance/source-activations.yaml.")
    source_revoke_parser.add_argument("--active-state", default=None, help="Active pointer JSON path. Defaults to per-source/per-env governance pointer.")
    source_revoke_parser.add_argument("--generated-at", default=None, help="UTC revocation timestamp override.")
    source_revoke_parser.add_argument("--reason", required=True, help="Business and technical reason for revocation.")
    source_revoke_parser.add_argument("--evidence-uri", required=True, help="Evidence URI for the revocation decision.")
    source_revoke_parser.add_argument("--impacted-use-case", action="append", default=[], help="Impacted use case id. Repeatable.")
    source_revoke_parser.add_argument(
        "--allow-missing-active-pointer",
        action="store_true",
        help="Break-glass revocation for a latest active ledger record whose active pointer is already missing.",
    )
    source_activation_ops_parser = subparsers.add_parser(
        "source-activation-ops-report",
        help="Write the group-wide source activation operations report for ledger, pointer, expiry and drift health.",
    )
    source_activation_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    source_activation_ops_parser.add_argument("--output", required=True, help="Output source_activation_ops_report.v1 JSON path.")
    source_activation_ops_parser.add_argument("--environment", default="staging", choices=("local", "staging", "prod"), help="Environment view.")
    source_activation_ops_parser.add_argument("--ledger", default=None, help="Activation ledger path. Defaults to governance/source-activations.yaml.")
    source_activation_ops_parser.add_argument("--active-pointer-dir", default=None, help="Directory containing source active pointer JSON files.")
    source_activation_ops_parser.add_argument("--as-of", default=None, help="UTC report timestamp override.")
    source_activation_ops_parser.add_argument("--expiring-within-days", type=int, default=30, help="Warn when active source activation expires within N days.")
    ingestion_runtime_ops_parser = subparsers.add_parser(
        "ingestion-runtime-check",
        help="Write event/CDC ingestion runtime production readiness report from connector evidence.",
    )
    ingestion_runtime_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    ingestion_runtime_ops_parser.add_argument("--output", required=True, help="Output event_cdc_ingestion_runtime_report.v1 JSON path.")
    ingestion_runtime_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Environment view.")
    ingestion_runtime_ops_parser.add_argument("--evidence", default=None, help="Optional ingestion_runtime_evidence.v1 JSON artifact.")
    ingestion_runtime_ops_parser.add_argument("--lag-slo-records", type=int, default=1000, help="Maximum allowed connector lag in records.")
    ingestion_runtime_ops_parser.add_argument("--lag-slo-seconds", type=int, default=300, help="Maximum allowed connector lag age in seconds.")
    ingestion_runtime_ops_parser.add_argument("--dlt-unresolved-slo", type=int, default=0, help="Maximum unresolved DLT record count.")
    ingestion_runtime_ops_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    ingestion_runtime_evidence_parser = subparsers.add_parser(
        "ingestion-runtime-evidence-normalize",
        help="Normalize Kafka Connect, lag, DLT, backpressure, broker and offset-ledger exports into ingestion_runtime_evidence.v1.",
    )
    ingestion_runtime_evidence_parser.add_argument("--root", default=".", help="Data platform root directory.")
    ingestion_runtime_evidence_parser.add_argument("--output", required=True, help="Output ingestion_runtime_evidence.v1 JSON path.")
    ingestion_runtime_evidence_parser.add_argument("--environment", required=True, choices=("staging", "prod"), help="Target runtime environment.")
    ingestion_runtime_evidence_parser.add_argument("--source-kind", required=True, choices=("ci_tool_output", "external_attestation", "synthetic_fixture"))
    ingestion_runtime_evidence_parser.add_argument("--kafka-connect-status", required=True, help="Kafka Connect/Debezium connector status JSON.")
    ingestion_runtime_evidence_parser.add_argument("--lag-metrics", required=True, help="Consumer/source lag metrics JSON.")
    ingestion_runtime_evidence_parser.add_argument("--dlt-report", required=True, help="DLT operations JSON.")
    ingestion_runtime_evidence_parser.add_argument("--backpressure-report", required=True, help="Backpressure probe JSON.")
    ingestion_runtime_evidence_parser.add_argument("--offset-ledgers", required=True, help="Source offset ledger reference JSON.")
    ingestion_runtime_evidence_parser.add_argument("--broker-checks", default=None, help="Optional topic and ACL check JSON.")
    ingestion_runtime_evidence_parser.add_argument("--ci-run-id", default=None, help="CI/CD or SRE run id.")
    ingestion_runtime_evidence_parser.add_argument("--issuer-tool", default=None, help="Tool that produced the normalized evidence.")
    ingestion_runtime_evidence_parser.add_argument("--issuer-tool-version", default=None, help="Tool version that produced the normalized evidence.")
    ingestion_runtime_evidence_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    ingestion_runtime_evidence_parser.add_argument("--valid-until", required=True, help="UTC validity deadline for the evidence.")
    source_readiness_parser = subparsers.add_parser(
        "source-readiness-check",
        help="Write Source-to-Bronze production readiness evidence for one registered source.",
    )
    source_readiness_parser.add_argument("--root", default=".", help="Data platform root directory.")
    source_readiness_parser.add_argument("--source-id", required=True, help="Source id from platform/ingestion/source-registry.yaml.")
    source_readiness_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Target readiness environment.")
    source_readiness_parser.add_argument("--ingestion-manifest", required=True, help="First Bronze ingestion manifest path.")
    source_readiness_parser.add_argument("--bridge-manifest", default=None, help="Source bridge normalizer manifest path for bridge-required sources.")
    source_readiness_parser.add_argument("--replay-manifest", default=None, help="Replay Bronze ingestion manifest path.")
    source_readiness_parser.add_argument("--offset-ledger", default=None, help="Source offset ledger evidence path.")
    source_readiness_parser.add_argument("--schema-registry-report", default=None, help="Schema registry compatibility report path.")
    source_readiness_parser.add_argument("--change-control-evidence", default=None, help="Change-control evidence report path.")
    source_readiness_parser.add_argument("--catalog-bundle", default=None, help="Catalog bundle JSON path.")
    source_readiness_parser.add_argument("--openlineage-events", default=None, help="OpenLineage JSONL event artifact path.")
    source_readiness_parser.add_argument("--output", required=True, help="Output JSON source readiness report path.")
    source_readiness_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    offset_ledger_parser = subparsers.add_parser(
        "offset-ledger-record",
        help="Write durable source offset ledger evidence from a Bronze ingestion manifest.",
    )
    offset_ledger_parser.add_argument("--root", default=".", help="Data platform root directory.")
    offset_ledger_parser.add_argument("--source-id", required=True, help="Source id from platform/ingestion/source-registry.yaml.")
    offset_ledger_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Target environment.")
    offset_ledger_parser.add_argument("--ingestion-manifest", required=True, help="Bronze ingestion manifest path.")
    offset_ledger_parser.add_argument("--replay-manifest", default=None, help="Optional replay Bronze ingestion manifest path.")
    offset_ledger_parser.add_argument("--table-format", default="iceberg", choices=("iceberg",), help="Lakehouse table format.")
    offset_ledger_parser.add_argument("--target-snapshot-id", default=None, help="Iceberg target snapshot id after commit.")
    offset_ledger_parser.add_argument("--table-metadata-uri", default=None, help="Iceberg table metadata file URI after commit.")
    offset_ledger_parser.add_argument("--table-metadata-hash", default=None, help="SHA-256 hash of the Iceberg table metadata file.")
    offset_ledger_parser.add_argument("--commit-status", default="committed", choices=("started", "committed", "failed", "rolled_back"), help="Commit status.")
    offset_ledger_parser.add_argument("--committed-at", default=None, help="UTC commit timestamp.")
    offset_ledger_parser.add_argument("--output", required=True, help="Output source offset ledger report path.")
    offset_ledger_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    snapshot_evidence_parser = subparsers.add_parser(
        "snapshot-evidence-record",
        help="Write Silver/Gold lakehouse snapshot evidence from a pipeline manifest and Iceberg metadata.",
    )
    snapshot_evidence_parser.add_argument("--root", default=".", help="Data platform root directory.")
    snapshot_evidence_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Target environment.")
    snapshot_evidence_parser.add_argument("--pipeline-manifest", required=True, help="Silver/Gold pipeline manifest path.")
    snapshot_evidence_parser.add_argument("--snapshot-metadata", required=True, help="JSON file with Iceberg snapshot metadata for each output data product.")
    snapshot_evidence_parser.add_argument("--primary-output", required=True, help="Primary output data product, for example gold.recsys_interactions.")
    snapshot_evidence_parser.add_argument("--source-offset-ledger", default=None, help="Optional Source-to-Bronze offset ledger evidence path.")
    snapshot_evidence_parser.add_argument("--release-id", default=None, help="Release id bound to this snapshot evidence.")
    snapshot_evidence_parser.add_argument("--use-case-id", default=None, help="Use-case id bound to this snapshot evidence.")
    snapshot_evidence_parser.add_argument("--runner-id", default=None, help="Pipeline runner id bound to this snapshot evidence.")
    snapshot_evidence_parser.add_argument("--code-commit-sha", default=None, help="Source commit SHA that produced the pipeline output.")
    snapshot_evidence_parser.add_argument("--release-evidence-profile-id", default=None, help="Release evidence profile id.")
    snapshot_evidence_parser.add_argument("--release-evidence-profile-hash", default=None, help="Release evidence profile registry hash.")
    snapshot_evidence_parser.add_argument("--output", required=True, help="Output lakehouse snapshot evidence report path.")
    snapshot_evidence_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    bronze_lakehouse_ops_parser = subparsers.add_parser(
        "bronze-lakehouse-ops-report",
        help="Write Bronze lakehouse operations report from source offset ledgers and table maintenance evidence.",
    )
    bronze_lakehouse_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    bronze_lakehouse_ops_parser.add_argument("--output", required=True, help="Output bronze_lakehouse_ops_report.v1 JSON path.")
    bronze_lakehouse_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    bronze_lakehouse_ops_parser.add_argument(
        "--offset-ledger",
        action="append",
        default=[],
        help="source_offset_ledger.v1 JSON artifact. Can be passed multiple times.",
    )
    bronze_lakehouse_ops_parser.add_argument("--maintenance-evidence", default=None, help="Optional bronze_lakehouse_maintenance_evidence.v1 JSON artifact.")
    bronze_lakehouse_ops_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    publication_ops_parser = subparsers.add_parser(
        "silver-gold-publication-ops-report",
        help="Write Silver/Gold publication operations report from release, promotion, activation and active pointer evidence.",
    )
    publication_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    publication_ops_parser.add_argument("--output", required=True, help="Output silver_gold_publication_ops_report.v1 JSON path.")
    publication_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    publication_ops_parser.add_argument("--release-evidence", action="append", default=[], help="Release evidence JSON artifact. Repeatable.")
    publication_ops_parser.add_argument("--promotion-manifest", action="append", default=[], help="release_promotion_manifest.v1 JSON artifact. Repeatable.")
    publication_ops_parser.add_argument("--activation-manifest", action="append", default=[], help="release_activation_manifest.v1 JSON artifact. Repeatable.")
    publication_ops_parser.add_argument("--active-pointer", action="append", default=[], help="release_active_pointer.v1 JSON artifact. Repeatable.")
    publication_ops_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    access_parser = subparsers.add_parser(
        "access-policy-check",
        help="Write an access-policy evidence report for a data product contract and optional snapshot.",
    )
    access_parser.add_argument("--root", default=".", help="Data platform root directory.")
    access_parser.add_argument("--data-product", required=True, help="Data product name, for example gold.recsys_interactions.")
    access_parser.add_argument("--output", required=True, help="Output JSON access-policy report path.")
    access_parser.add_argument("--environment", default="local", help="Environment label.")
    access_parser.add_argument("--release-id", default=None, help="Release id for evidence correlation.")
    access_parser.add_argument("--dataset-snapshot-id", default=None, help="Dataset snapshot id.")
    access_parser.add_argument("--table-version", default=None, help="Table version or content version.")
    access_parser.add_argument("--content-hash", default=None, help="Published dataset content hash.")
    access_parser.add_argument("--row-count", type=int, default=None, help="Published dataset row count.")
    access_parser.add_argument("--generated-at", default=None, help="UTC generated_at override for deterministic reports.")
    grant_parser = subparsers.add_parser(
        "access-grant-check",
        help="Write an access-grant evidence report for approved grants, approvals and runtime access decisions.",
    )
    grant_parser.add_argument("--root", default=".", help="Data platform root directory.")
    grant_parser.add_argument("--data-product", required=True, help="Data product name, for example gold.recsys_interactions.")
    grant_parser.add_argument("--output", required=True, help="Output JSON access-grant evidence report path.")
    grant_parser.add_argument("--environment", default="local", help="Environment label.")
    grant_parser.add_argument("--release-id", default=None, help="Release id for evidence correlation.")
    grant_parser.add_argument("--dataset-snapshot-id", default=None, help="Dataset snapshot id.")
    grant_parser.add_argument("--table-version", default=None, help="Table version or content version.")
    grant_parser.add_argument("--content-hash", default=None, help="Published dataset content hash.")
    grant_parser.add_argument("--generated-at", default=None, help="UTC generated_at override for deterministic reports.")
    grant_ops_parser = subparsers.add_parser(
        "access-grant-ops-report",
        help="Write an operations decision report for enterprise data access grants.",
    )
    grant_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    grant_ops_parser.add_argument("--output", required=True, help="Output JSON access grant ops report path.")
    grant_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    grant_ops_parser.add_argument("--generated-at", default=None, help="UTC generated_at override for deterministic reports.")
    grant_ops_parser.add_argument("--expiring-within-days", type=int, default=30, help="Warn when active grants expire within this many days.")
    change_control_parser = subparsers.add_parser(
        "change-control-check",
        help="Write enterprise data change-control evidence for approved or in-review platform changes.",
    )
    change_control_parser.add_argument("--root", default=".", help="Data platform root directory.")
    change_control_parser.add_argument("--output", required=True, help="Output JSON change-control evidence report path.")
    change_control_parser.add_argument("--request-id", default=None, help="Optional governance/change-requests.yaml request id.")
    change_control_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Target environment.")
    change_control_parser.add_argument("--generated-at", default=None, help="UTC generated_at override for deterministic reports.")
    backfill_parser = subparsers.add_parser(
        "backfill-readiness-check",
        help="Write governed backfill/replay readiness evidence for a registered backfill request.",
    )
    backfill_parser.add_argument("--root", default=".", help="Data platform root directory.")
    backfill_parser.add_argument("--request-id", required=True, help="Request id from governance/backfill-requests.yaml.")
    backfill_parser.add_argument("--environment", required=True, choices=("local", "staging", "prod"), help="Target environment.")
    backfill_parser.add_argument("--dry-run-report", default=None, help="Optional local dry-run report JSON path.")
    backfill_parser.add_argument("--quality-report", default=None, help="Optional local quality report JSON path.")
    backfill_parser.add_argument("--data-diff-report", default=None, help="Optional local data-diff report JSON path.")
    backfill_parser.add_argument("--source-offset-ledger", default=None, help="Optional local source offset ledger evidence path.")
    backfill_parser.add_argument("--snapshot-evidence", default=None, help="Optional local lakehouse snapshot evidence path.")
    backfill_parser.add_argument("--release-evidence", default=None, help="Optional local release evidence path.")
    backfill_parser.add_argument("--change-control-evidence", default=None, help="Optional local change-control evidence path.")
    backfill_parser.add_argument("--backfill-plan", default=None, help="Optional local backfill plan JSON path.")
    backfill_parser.add_argument("--active-state", default=None, help="Optional local active pointer state JSON path.")
    backfill_parser.add_argument("--output", required=True, help="Output backfill readiness report path.")
    backfill_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    retention_parser = subparsers.add_parser(
        "retention-check",
        help="Write retention and erasure evidence for a data product contract and optional snapshot.",
    )
    retention_parser.add_argument("--root", default=".", help="Data platform root directory.")
    retention_parser.add_argument("--data-product", required=True, help="Data product name, for example gold.recsys_interactions.")
    retention_parser.add_argument("--output", required=True, help="Output JSON retention evidence report path.")
    retention_parser.add_argument("--environment", default="local", help="Environment label.")
    retention_parser.add_argument("--release-id", default=None, help="Release id for evidence correlation.")
    retention_parser.add_argument("--dataset-snapshot-id", default=None, help="Dataset snapshot id.")
    retention_parser.add_argument("--table-version", default=None, help="Table version or content version.")
    retention_parser.add_argument("--content-hash", default=None, help="Published dataset content hash.")
    retention_parser.add_argument("--row-count", type=int, default=None, help="Published dataset row count.")
    retention_parser.add_argument("--evidence-input", default=None, help="Retention job evidence input JSON path.")
    retention_parser.add_argument("--generated-at", default=None, help="UTC generated_at override for deterministic reports.")
    pipeline_list_parser = subparsers.add_parser(
        "pipeline-list",
        help="List registered local pipeline runners.",
    )
    pipeline_list_parser.add_argument("--format", choices=("json", "text"), default="json", help="Output format.")
    pipeline_list_parser.add_argument("--product", default=None, help="Filter by product code.")
    pipeline_list_parser.add_argument("--domain", default=None, help="Filter by enterprise domain.")
    pipeline_list_parser.add_argument("--use-case", default=None, help="Filter by use-case id.")
    pipeline_list_parser.add_argument("--output-data-product", default=None, help="Filter by output data product.")
    pipeline_describe_parser = subparsers.add_parser(
        "pipeline-describe",
        help="Describe one registered pipeline runner.",
    )
    pipeline_describe_parser.add_argument("--runner-id", required=True, help="Pipeline runner id.")
    pipeline_parser = subparsers.add_parser(
        "run-pipeline",
        help="Run a registered local pipeline runner by runner id.",
    )
    pipeline_parser.add_argument("--runner-id", required=True, help="Pipeline runner id from pipeline-list.")
    pipeline_parser.add_argument("--input", required=True, help="Input file path for the runner.")
    pipeline_parser.add_argument("--output-dir", required=True, help="Output directory for the runner artifacts.")
    pipeline_parser.add_argument("--upstream-manifest", default=None, help="Optional upstream manifest path.")
    pipeline_parser.add_argument(
        "--enrollment-bronze",
        default=None,
        help="Optional second approved enrollment.completed Bronze JSONL path for LMS recommendation training.",
    )
    pipeline_parser.add_argument("--snapshot-id", default=None, help="Optional snapshot id.")
    pipeline_parser.add_argument("--built-at", default=None, help="Optional UTC build timestamp.")
    pipeline_parser.add_argument("--ingested-at", default=None, help="Optional UTC ingestion timestamp for raw local runners.")
    use_case_parser = subparsers.add_parser(
        "run-use-case",
        help="Run a registered use-case implementation with catalog and release-gate evidence.",
    )
    use_case_parser.add_argument("--root", default=".", help="Data platform root directory.")
    use_case_parser.add_argument("--use-case-id", "--use-case", required=True, dest="use_case_id", help="Use-case id from use-cases/registry.yaml.")
    use_case_parser.add_argument("--runner-id", default=None, help="Optional runner id; required when the use case has multiple implementations.")
    use_case_parser.add_argument("--topic", default=None, help="Optional input topic override when the use case has multiple topics.")
    use_case_parser.add_argument("--primary-output", default=None, help="Optional primary output data product override.")
    use_case_parser.add_argument("--input", required=True, help="Use-case input file. Event-backed runners accept raw topic JSONL here.")
    use_case_parser.add_argument("--output-dir", required=True, help="Output directory for all use-case artifacts.")
    use_case_parser.add_argument("--release-id", required=True, help="Stable release or run id.")
    use_case_parser.add_argument("--environment", default="local", help="Environment label for evidence.")
    use_case_parser.add_argument("--ingested-at", default=None, help="UTC ingestion timestamp override.")
    use_case_parser.add_argument("--built-at", default=None, help="UTC pipeline build timestamp override.")
    use_case_parser.add_argument("--evaluation-time", default=None, help="UTC release-gate evaluation timestamp override.")
    use_case_parser.add_argument("--schema-id", default=None, help="Schema registry id or local compatibility id.")
    use_case_parser.add_argument("--snapshot-id", default=None, help="Optional dataset snapshot id.")
    use_case_parser.add_argument("--code-commit-sha", default=None, help="Source commit SHA recorded in release evidence.")
    use_case_parser.add_argument("--schema-registry-report-uri", default=None, help="Schema registry compatibility report URI.")
    use_case_parser.add_argument("--schema-registry-report-hash", default=None, help="SHA-256 hash of the schema registry report.")
    use_case_parser.add_argument("--validator-output-uri", default=None, help="Contract/data-quality validator output URI.")
    use_case_parser.add_argument("--access-policy-check-id", default=None, help="Access policy check id recorded in release evidence.")
    use_case_parser.add_argument("--access-policy-report-uri", default=None, help="Access policy evidence report URI.")
    use_case_parser.add_argument("--access-policy-report-hash", default=None, help="SHA-256 hash of the access policy evidence report.")
    use_case_parser.add_argument("--access-grant-evidence-uri", default=None, help="Access grant evidence report URI.")
    use_case_parser.add_argument("--access-grant-evidence-hash", default=None, help="SHA-256 hash of the access grant evidence report.")
    use_case_parser.add_argument("--retention-evidence-uri", default=None, help="Retention and erasure evidence report URI.")
    use_case_parser.add_argument("--retention-evidence-hash", default=None, help="SHA-256 hash of the retention and erasure evidence report.")
    use_case_parser.add_argument("--retention-evidence-input", default=None, help="Retention job evidence input JSON used to generate a release evidence report.")
    use_case_parser.add_argument("--snapshot-evidence-uri", default=None, help="Lakehouse snapshot evidence report URI.")
    use_case_parser.add_argument("--snapshot-evidence-hash", default=None, help="SHA-256 hash of the lakehouse snapshot evidence report.")
    use_case_parser.add_argument("--approver", default=None, help="Approver identity recorded in release evidence.")
    data_plane_smoke_parser = subparsers.add_parser(
        "data-plane-smoke",
        help="Run a local CI data-plane smoke: source events -> Bronze -> Silver/Gold -> catalog -> release evidence -> query check.",
    )
    data_plane_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    data_plane_smoke_parser.add_argument(
        "--use-case-id",
        "--use-case",
        dest="use_case_id",
        default=DEFAULT_USE_CASE_ID,
        help="Use-case id from use-cases/registry.yaml.",
    )
    data_plane_smoke_parser.add_argument("--runner-id", default=None, help="Optional runner id override.")
    data_plane_smoke_parser.add_argument("--topic", default=None, help="Optional input topic override.")
    data_plane_smoke_parser.add_argument("--primary-output", default=None, help="Optional primary output override.")
    data_plane_smoke_parser.add_argument(
        "--input",
        default=None,
        help="Use-case input JSONL. If omitted, a built-in smoke sample is selected for supported use cases.",
    )
    data_plane_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for use-case artifacts.")
    data_plane_smoke_parser.add_argument("--output", required=True, help="Output data_plane_smoke_report.v1 JSON path.")
    data_plane_smoke_parser.add_argument("--release-id", default=DEFAULT_RELEASE_ID, help="Stable release or run id.")
    data_plane_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    data_plane_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    data_plane_smoke_parser.add_argument("--ingested-at", default=None, help="UTC ingestion timestamp override.")
    data_plane_smoke_parser.add_argument("--built-at", default=None, help="UTC pipeline build timestamp override.")
    data_plane_smoke_parser.add_argument("--evaluation-time", default=None, help="UTC release-gate evaluation timestamp override.")
    data_plane_smoke_parser.add_argument("--schema-id", default=None, help="Schema registry id or local compatibility id.")
    data_plane_smoke_parser.add_argument("--snapshot-id", default=None, help="Optional dataset snapshot id.")
    live_lakehouse_smoke_parser = subparsers.add_parser(
        "live-lakehouse-smoke",
        help="Run finance slice through local Parquet table commits and DuckDB SQL query probe.",
    )
    live_lakehouse_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    live_lakehouse_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for live lakehouse smoke artifacts.")
    live_lakehouse_smoke_parser.add_argument("--output", required=True, help="Output live_lakehouse_smoke_report.v1 JSON path.")
    live_lakehouse_smoke_parser.add_argument("--input", default=None, help="Optional input JSONL. Defaults to finance benefit sample.")
    live_lakehouse_smoke_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    live_lakehouse_smoke_parser.add_argument("--release-id", default="local-live-lakehouse-smoke", help="Stable release/run id.")
    live_lakehouse_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    live_lakehouse_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    live_lakehouse_smoke_parser.add_argument("--ingested-at", default=None, help="UTC ingestion timestamp override.")
    live_lakehouse_smoke_parser.add_argument("--built-at", default=None, help="UTC pipeline build timestamp override.")
    live_lakehouse_smoke_parser.add_argument("--evaluation-time", default=None, help="UTC release-gate evaluation timestamp override.")
    live_lakehouse_smoke_parser.add_argument("--schema-id", default=None, help="Schema registry id or local compatibility id.")
    live_lakehouse_smoke_parser.add_argument("--snapshot-id", default=None, help="Optional dataset snapshot id.")
    object_store_smoke_parser = subparsers.add_parser(
        "object-store-commit-smoke",
        help="Upload finance Parquet commits to S3-compatible object store and verify read-back evidence.",
    )
    object_store_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    object_store_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for object-store smoke artifacts.")
    object_store_smoke_parser.add_argument("--output", required=True, help="Output object_store_commit_smoke_report.v1 JSON path.")
    object_store_smoke_parser.add_argument("--live-lakehouse-smoke-report", default=None, help="Optional live_lakehouse_smoke_report.v1 input.")
    object_store_smoke_parser.add_argument("--bucket", default="enterprise-dp-local-lakehouse", help="S3 bucket for smoke uploads.")
    object_store_smoke_parser.add_argument("--endpoint-url", default="http://localhost:19000", help="S3-compatible endpoint URL.")
    object_store_smoke_parser.add_argument("--access-key", default="enterprise_dp_local", help="S3 access key.")
    object_store_smoke_parser.add_argument("--secret-key", default="enterprise_dp_local_only_change_me", help="S3 secret key.")
    object_store_smoke_parser.add_argument("--region-name", default="us-east-1", help="S3 region name.")
    object_store_smoke_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    object_store_smoke_parser.add_argument("--release-id", default="local-object-store-commit-smoke", help="Stable release/run id.")
    object_store_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    object_store_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    trino_sql_smoke_parser = subparsers.add_parser(
        "trino-sql-runtime-smoke",
        help="Load finance Gold rows into local Trino memory catalog and verify a SQL aggregate probe.",
    )
    trino_sql_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    trino_sql_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for Trino smoke artifacts.")
    trino_sql_smoke_parser.add_argument("--output", required=True, help="Output trino_sql_runtime_smoke_report.v1 JSON path.")
    trino_sql_smoke_parser.add_argument("--live-lakehouse-smoke-report", default=None, help="Optional live_lakehouse_smoke_report.v1 input.")
    trino_sql_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    trino_sql_smoke_parser.add_argument("--service", default="trino", help="Compose service name for Trino.")
    trino_sql_smoke_parser.add_argument("--schema", default="enterprise_dp_smoke", help="Trino memory schema for smoke table.")
    trino_sql_smoke_parser.add_argument("--table", default="finance_benefit_reconciliation", help="Trino memory table for smoke rows.")
    trino_sql_smoke_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    trino_sql_smoke_parser.add_argument("--release-id", default="local-trino-sql-runtime-smoke", help="Stable release/run id.")
    trino_sql_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    trino_sql_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    trino_sql_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    trino_sql_smoke_parser.add_argument("--wait-attempts", type=int, default=12)
    trino_sql_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before Trino commands.")
    trino_iceberg_minio_smoke_parser = subparsers.add_parser(
        "trino-iceberg-minio-smoke",
        help="Create and query a Trino Iceberg table on MinIO through the local JDBC catalog.",
    )
    trino_iceberg_minio_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    trino_iceberg_minio_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for Trino Iceberg/MinIO smoke artifacts.")
    trino_iceberg_minio_smoke_parser.add_argument("--output", required=True, help="Output trino_iceberg_minio_smoke_report.v1 JSON path.")
    trino_iceberg_minio_smoke_parser.add_argument("--live-lakehouse-smoke-report", default=None, help="Optional live_lakehouse_smoke_report.v1 input.")
    trino_iceberg_minio_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    trino_iceberg_minio_smoke_parser.add_argument("--service", default="trino", help="Compose service name for Trino.")
    trino_iceberg_minio_smoke_parser.add_argument("--postgres-service", default="iceberg-postgres", help="Compose service name for the Iceberg JDBC catalog database.")
    trino_iceberg_minio_smoke_parser.add_argument("--bucket", default="enterprise-dp-local-iceberg", help="MinIO/S3 bucket for Iceberg warehouse data.")
    trino_iceberg_minio_smoke_parser.add_argument("--endpoint-url", default="http://localhost:19000", help="S3-compatible endpoint URL reachable from the host.")
    trino_iceberg_minio_smoke_parser.add_argument("--access-key", default="enterprise_dp_local", help="S3 access key.")
    trino_iceberg_minio_smoke_parser.add_argument("--secret-key", default="enterprise_dp_local_only_change_me", help="S3 secret key.")
    trino_iceberg_minio_smoke_parser.add_argument("--region-name", default="us-east-1", help="S3 region name.")
    trino_iceberg_minio_smoke_parser.add_argument("--catalog", default="iceberg", help="Trino Iceberg catalog name.")
    trino_iceberg_minio_smoke_parser.add_argument("--schema", default="finance_iceberg_smoke", help="Trino Iceberg schema for the smoke table.")
    trino_iceberg_minio_smoke_parser.add_argument("--table", default="finance_benefit_reconciliation", help="Trino Iceberg table for smoke rows.")
    trino_iceberg_minio_smoke_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    trino_iceberg_minio_smoke_parser.add_argument("--release-id", default="local-trino-iceberg-minio-smoke", help="Stable release/run id.")
    trino_iceberg_minio_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    trino_iceberg_minio_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    trino_iceberg_minio_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    trino_iceberg_minio_smoke_parser.add_argument("--wait-attempts", type=int, default=12)
    trino_iceberg_minio_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before Trino commands.")
    catalog_cross_engine_smoke_parser = subparsers.add_parser(
        "catalog-cross-engine-smoke",
        help="Verify Trino and PyIceberg can share the local JDBC Iceberg catalog and reject stale commits.",
    )
    catalog_cross_engine_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    catalog_cross_engine_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for catalog cross-engine smoke artifacts.")
    catalog_cross_engine_smoke_parser.add_argument("--output", required=True, help="Output catalog_cross_engine_smoke_report.v1 JSON path.")
    catalog_cross_engine_smoke_parser.add_argument(
        "--trino-iceberg-minio-smoke-report",
        default=None,
        help="Optional trino_iceberg_minio_smoke_report.v1 input.",
    )
    catalog_cross_engine_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    catalog_cross_engine_smoke_parser.add_argument("--service", default="trino", help="Compose service name for Trino.")
    catalog_cross_engine_smoke_parser.add_argument("--postgres-service", default="iceberg-postgres", help="Compose service name for the Iceberg JDBC catalog database.")
    catalog_cross_engine_smoke_parser.add_argument("--minio-service", default="minio", help="Compose service name for MinIO.")
    catalog_cross_engine_smoke_parser.add_argument("--bucket", default="enterprise-dp-local-iceberg", help="MinIO/S3 bucket for Iceberg warehouse data.")
    catalog_cross_engine_smoke_parser.add_argument("--endpoint-url", default="http://localhost:19000", help="S3-compatible endpoint URL reachable from the host.")
    catalog_cross_engine_smoke_parser.add_argument("--access-key", default="enterprise_dp_local", help="S3 access key.")
    catalog_cross_engine_smoke_parser.add_argument("--secret-key", default="enterprise_dp_local_only_change_me", help="S3 secret key.")
    catalog_cross_engine_smoke_parser.add_argument("--region-name", default="us-east-1", help="S3 region name.")
    catalog_cross_engine_smoke_parser.add_argument("--catalog", default="iceberg", help="Trino Iceberg catalog name.")
    catalog_cross_engine_smoke_parser.add_argument("--catalog-name", default="local_finance_iceberg", help="Iceberg JDBC catalog name.")
    catalog_cross_engine_smoke_parser.add_argument("--schema", default="finance_iceberg_smoke", help="Shared Iceberg schema for probe tables.")
    catalog_cross_engine_smoke_parser.add_argument("--cross-engine-table", default="catalog_cross_engine_probe", help="Probe table for Trino/PyIceberg commit compatibility.")
    catalog_cross_engine_smoke_parser.add_argument("--concurrency-table", default="catalog_lock_probe", help="Probe table for stale commit rejection.")
    catalog_cross_engine_smoke_parser.add_argument("--catalog-uri", default="postgresql+psycopg://iceberg:iceberg_local_only_change_me@localhost:15432/iceberg", help="PyIceberg SQL catalog URI reachable from the host.")
    catalog_cross_engine_smoke_parser.add_argument("--release-id", default="local-catalog-cross-engine-smoke", help="Stable release/run id.")
    catalog_cross_engine_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    catalog_cross_engine_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    catalog_cross_engine_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    catalog_cross_engine_smoke_parser.add_argument("--wait-attempts", type=int, default=12)
    catalog_cross_engine_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before Trino commands.")
    trino_runtime_security_smoke_parser = subparsers.add_parser(
        "trino-runtime-security-smoke",
        help="Verify local Trino file-based access control with allow, write-deny and default-deny probes.",
    )
    trino_runtime_security_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    trino_runtime_security_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for Trino security smoke artifacts.")
    trino_runtime_security_smoke_parser.add_argument("--output", required=True, help="Output trino_runtime_security_smoke_report.v1 JSON path.")
    trino_runtime_security_smoke_parser.add_argument(
        "--trino-iceberg-minio-smoke-report",
        default=None,
        help="Optional trino_iceberg_minio_smoke_report.v1 input.",
    )
    trino_runtime_security_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    trino_runtime_security_smoke_parser.add_argument("--service", default="trino", help="Compose service name for Trino.")
    trino_runtime_security_smoke_parser.add_argument("--postgres-service", default="iceberg-postgres", help="Compose service name for the Iceberg JDBC catalog database.")
    trino_runtime_security_smoke_parser.add_argument("--catalog", default="iceberg", help="Trino Iceberg catalog name.")
    trino_runtime_security_smoke_parser.add_argument("--schema", default="finance_iceberg_smoke", help="Trino Iceberg schema for the smoke table.")
    trino_runtime_security_smoke_parser.add_argument("--table", default="finance_benefit_reconciliation", help="Trino Iceberg table for smoke rows.")
    trino_runtime_security_smoke_parser.add_argument("--security-probe-table", default="finance_benefit_security_probe", help="Trino Iceberg table created for row-filter and column-mask probes.")
    trino_runtime_security_smoke_parser.add_argument("--allowed-user", default="dp_allowed", help="User expected to read the governed table.")
    trino_runtime_security_smoke_parser.add_argument("--denied-user", default="dp_denied", help="User expected to be denied on the governed table.")
    trino_runtime_security_smoke_parser.add_argument("--unknown-user", default="dp_unknown", help="Unknown user expected to hit default deny.")
    trino_runtime_security_smoke_parser.add_argument("--row-filter-user", default="dp_row_filter", help="User expected to see only filtered rows on the security probe table.")
    trino_runtime_security_smoke_parser.add_argument("--masked-user", default="dp_masked", help="User expected to see masked PII columns on the security probe table.")
    trino_runtime_security_smoke_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    trino_runtime_security_smoke_parser.add_argument("--release-id", default="local-trino-runtime-security-smoke", help="Stable release/run id.")
    trino_runtime_security_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    trino_runtime_security_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    trino_runtime_security_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    trino_runtime_security_smoke_parser.add_argument("--wait-attempts", type=int, default=12)
    trino_runtime_security_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before Trino commands.")
    policy_decision_smoke_parser = subparsers.add_parser(
        "policy-decision-smoke",
        help="Run a local OPA policy decision point smoke for access decisions and maker-checker policy admin.",
    )
    policy_decision_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    policy_decision_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for OPA PDP smoke artifacts.")
    policy_decision_smoke_parser.add_argument("--output", required=True, help="Output policy_decision_smoke_report.v1 JSON path.")
    policy_decision_smoke_parser.add_argument("--opa-image", default="openpolicyagent/opa:0.70.0")
    policy_decision_smoke_parser.add_argument("--container-name", default="enterprise-dp-opa-policy-decision-smoke")
    policy_decision_smoke_parser.add_argument("--port", type=int, default=18186)
    policy_decision_smoke_parser.add_argument("--release-id", default="local-policy-decision-smoke", help="Stable release/run id.")
    policy_decision_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    policy_decision_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    policy_decision_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    policy_decision_smoke_parser.add_argument("--wait-attempts", type=int, default=30)
    policy_decision_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Use an already-running OPA PDP URL.")
    policy_decision_smoke_parser.add_argument("--no-cleanup-runtime", action="store_true", help="Leave the local OPA container running.")
    policy_decision_smoke_parser.add_argument("--pdp-url", default=None, help="OPA PDP base URL when --no-start-runtime is used.")
    oidc_auth_smoke_parser = subparsers.add_parser(
        "oidc-auth-smoke",
        help="Verify local OIDC RS256/JWKS token validation, claim authorization and redacted audit evidence.",
    )
    oidc_auth_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    oidc_auth_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for OIDC auth smoke artifacts.")
    oidc_auth_smoke_parser.add_argument("--output", required=True, help="Output oidc_auth_smoke_report.v1 JSON path.")
    oidc_auth_smoke_parser.add_argument("--issuer", default="https://identity.local/realms/enterprise-dp")
    oidc_auth_smoke_parser.add_argument("--audience", default="enterprise-dp-runtime")
    oidc_auth_smoke_parser.add_argument("--required-role", default="data-platform-runtime-reader")
    oidc_auth_smoke_parser.add_argument("--key-id", default="enterprise-dp-local-rs256-2026-01")
    oidc_auth_smoke_parser.add_argument("--release-id", default="local-oidc-auth-smoke", help="Stable release/run id.")
    oidc_auth_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    oidc_auth_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    secret_rotation_smoke_parser = subparsers.add_parser(
        "secret-rotation-smoke",
        help="Verify local encrypted secret rotation and Dagster service-identity secret injection evidence.",
    )
    secret_rotation_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    secret_rotation_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for secret rotation smoke artifacts.")
    secret_rotation_smoke_parser.add_argument("--output", required=True, help="Output secret_rotation_smoke_report.v1 JSON path.")
    secret_rotation_smoke_parser.add_argument("--release-id", default="local-secret-rotation-smoke", help="Stable release/run id.")
    secret_rotation_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    secret_rotation_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    secret_rotation_ops_parser = subparsers.add_parser(
        "secret-rotation-ops-report",
        help="Write production-like managed secret/KMS rotation operations evidence.",
    )
    secret_rotation_ops_parser.add_argument("--root", default=".", help="Data platform root directory.")
    secret_rotation_ops_parser.add_argument("--output", required=True, help="Output secret_rotation_ops_report.v1 JSON path.")
    secret_rotation_ops_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"))
    secret_rotation_ops_parser.add_argument("--evidence", default=None, help="Optional managed_secret_rotation_evidence.v1 JSON artifact.")
    secret_rotation_ops_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    iceberg_catalog_smoke_parser = subparsers.add_parser(
        "iceberg-catalog-smoke",
        help="Commit finance Bronze/Silver/Gold tables into a local PyIceberg SQL catalog and verify snapshots.",
    )
    iceberg_catalog_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    iceberg_catalog_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for Iceberg smoke artifacts.")
    iceberg_catalog_smoke_parser.add_argument("--output", required=True, help="Output iceberg_catalog_smoke_report.v1 JSON path.")
    iceberg_catalog_smoke_parser.add_argument("--live-lakehouse-smoke-report", default=None, help="Optional live_lakehouse_smoke_report.v1 input.")
    iceberg_catalog_smoke_parser.add_argument("--catalog-name", default="local_finance_iceberg", help="PyIceberg catalog name.")
    iceberg_catalog_smoke_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    iceberg_catalog_smoke_parser.add_argument("--release-id", default="local-iceberg-catalog-smoke", help="Stable release/run id.")
    iceberg_catalog_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    iceberg_catalog_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    dagster_orchestration_smoke_parser = subparsers.add_parser(
        "dagster-orchestration-smoke",
        help="Run a local Dagster job over finance live evidence and read back Dagster run history.",
    )
    dagster_orchestration_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    dagster_orchestration_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for Dagster smoke artifacts.")
    dagster_orchestration_smoke_parser.add_argument("--output", required=True, help="Output dagster_orchestration_smoke_report.v1 JSON path.")
    dagster_orchestration_smoke_parser.add_argument("--live-lakehouse-smoke-report", default=None, help="Optional live_lakehouse_smoke_report.v1 input.")
    dagster_orchestration_smoke_parser.add_argument("--object-store-smoke-report", default=None, help="Optional object_store_commit_smoke_report.v1 input.")
    dagster_orchestration_smoke_parser.add_argument("--trino-sql-smoke-report", default=None, help="Optional trino_sql_runtime_smoke_report.v1 input.")
    dagster_orchestration_smoke_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    dagster_orchestration_smoke_parser.add_argument("--release-id", default="local-dagster-orchestration-smoke", help="Stable release/run id.")
    dagster_orchestration_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    dagster_orchestration_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    dagster_day2_smoke_parser = subparsers.add_parser(
        "dagster-day2-smoke",
        help="Run a local Dagster day-2 smoke for retry policy, schedule tick ledger and backfill materialization history.",
    )
    dagster_day2_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    dagster_day2_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for Dagster day-2 smoke artifacts.")
    dagster_day2_smoke_parser.add_argument("--output", required=True, help="Output dagster_day2_smoke_report.v1 JSON path.")
    dagster_day2_smoke_parser.add_argument("--release-id", default="local-dagster-day2-smoke", help="Stable release/run id.")
    dagster_day2_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    dagster_day2_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    event_backbone_smoke_parser = subparsers.add_parser(
        "event-backbone-smoke",
        help="Run an optional local Redpanda/rpk round-trip smoke and feed consumed records into the data-plane smoke.",
    )
    event_backbone_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    event_backbone_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for smoke artifacts.")
    event_backbone_smoke_parser.add_argument("--output", required=True, help="Output event_backbone_smoke_report.v1 JSON path.")
    event_backbone_smoke_parser.add_argument("--input", default=None, help="Input JSONL. Defaults to the finance benefit sample.")
    event_backbone_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    event_backbone_smoke_parser.add_argument("--service", default="redpanda", help="Compose service name for Redpanda.")
    event_backbone_smoke_parser.add_argument("--topic", default=None, help="Optional runtime topic. Defaults to a unique local smoke topic.")
    event_backbone_smoke_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    event_backbone_smoke_parser.add_argument("--release-id", default="local-data-plane-smoke", help="Stable release or run id.")
    event_backbone_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    event_backbone_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    event_backbone_smoke_parser.add_argument("--ingested-at", default=None, help="UTC ingestion timestamp override.")
    event_backbone_smoke_parser.add_argument("--built-at", default=None, help="UTC pipeline build timestamp override.")
    event_backbone_smoke_parser.add_argument("--evaluation-time", default=None, help="UTC release-gate evaluation timestamp override.")
    event_backbone_smoke_parser.add_argument("--schema-id", default=None, help="Schema registry id or local compatibility id.")
    event_backbone_smoke_parser.add_argument("--snapshot-id", default=None, help="Optional dataset snapshot id.")
    event_backbone_smoke_parser.add_argument(
        "--schema-registry-runtime-smoke-report",
        default=None,
        help="Optional schema_registry_runtime_smoke_report.v1 used to enforce producer schema ids before publish.",
    )
    event_backbone_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=90)
    event_backbone_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before rpk commands.")
    broker_acl_smoke_parser = subparsers.add_parser(
        "broker-acl-smoke",
        help="Run an isolated local Redpanda SASL/SCRAM ACL smoke and prove broker authorization denial.",
    )
    broker_acl_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    broker_acl_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for broker ACL smoke artifacts.")
    broker_acl_smoke_parser.add_argument("--output", required=True, help="Output broker_acl_smoke_report.v1 JSON path.")
    broker_acl_smoke_parser.add_argument("--image", default="redpandadata/redpanda:v24.2.8", help="Redpanda image to run.")
    broker_acl_smoke_parser.add_argument(
        "--container-name",
        default="enterprise-dp-local-broker-acl-smoke",
        help="Temporary Redpanda container name.",
    )
    broker_acl_smoke_parser.add_argument("--topic", default="dp.local.broker.acl.smoke", help="Topic used for ACL probes.")
    broker_acl_smoke_parser.add_argument("--group", default="dp.local.broker.acl.smoke.group", help="Consumer group used for ACL probes.")
    broker_acl_smoke_parser.add_argument("--release-id", default="local-broker-acl-smoke", help="Stable release/run id.")
    broker_acl_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    broker_acl_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    broker_acl_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    broker_acl_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not start the temporary Redpanda container.")
    broker_acl_smoke_parser.add_argument("--no-cleanup-runtime", action="store_true", help="Leave the temporary Redpanda container running.")
    transactional_outbox_smoke_parser = subparsers.add_parser(
        "transactional-outbox-smoke",
        help="Run a local Postgres transactional outbox to Redpanda to Bronze ingestion smoke.",
    )
    transactional_outbox_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    transactional_outbox_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for transactional outbox smoke artifacts.")
    transactional_outbox_smoke_parser.add_argument("--output", required=True, help="Output transactional_outbox_smoke_report.v1 JSON path.")
    transactional_outbox_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    transactional_outbox_smoke_parser.add_argument("--postgres-service", default="iceberg-postgres", help="Compose service name for Postgres.")
    transactional_outbox_smoke_parser.add_argument("--redpanda-service", default="redpanda", help="Compose service name for Redpanda.")
    transactional_outbox_smoke_parser.add_argument("--source-id", default="enterprise-commerce-benefit-settled-outbox", help="Source registry id to seed into the local transactional outbox.")
    transactional_outbox_smoke_parser.add_argument("--release-id", default="local-transactional-outbox-smoke", help="Stable release/run id.")
    transactional_outbox_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    transactional_outbox_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    transactional_outbox_smoke_parser.add_argument("--ingested-at", default=None, help="UTC Bronze ingestion timestamp override.")
    transactional_outbox_smoke_parser.add_argument("--schema-id", default=None, help="Optional schema id passed to Bronze ingestion.")
    transactional_outbox_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    transactional_outbox_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before Postgres/Redpanda commands.")
    live_bronze_ingestion_smoke_parser = subparsers.add_parser(
        "live-bronze-ingestion-smoke",
        help="Run source Postgres outbox to Redpanda to Bronze Iceberg ingestion runtime smoke.",
    )
    live_bronze_ingestion_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    live_bronze_ingestion_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for live Bronze ingestion artifacts.")
    live_bronze_ingestion_smoke_parser.add_argument("--output", required=True, help="Output live_bronze_ingestion_runtime_report.v1 JSON path.")
    live_bronze_ingestion_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    live_bronze_ingestion_smoke_parser.add_argument("--source-postgres-service", default="source-postgres", help="Compose service name for source outbox Postgres.")
    live_bronze_ingestion_smoke_parser.add_argument("--redpanda-service", default="redpanda", help="Compose service name for Redpanda.")
    live_bronze_ingestion_smoke_parser.add_argument("--trino-service", default="trino", help="Compose service name for Trino.")
    live_bronze_ingestion_smoke_parser.add_argument("--iceberg-postgres-service", default="iceberg-postgres", help="Compose service name for Iceberg JDBC catalog Postgres.")
    live_bronze_ingestion_smoke_parser.add_argument("--minio-service", default="minio", help="Compose service name for MinIO.")
    live_bronze_ingestion_smoke_parser.add_argument("--bucket", default="enterprise-dp-local-iceberg", help="MinIO/S3 bucket for Iceberg warehouse data.")
    live_bronze_ingestion_smoke_parser.add_argument("--endpoint-url", default="http://localhost:19000", help="S3-compatible endpoint URL reachable from the host.")
    live_bronze_ingestion_smoke_parser.add_argument("--access-key", default="enterprise_dp_local", help="S3 access key.")
    live_bronze_ingestion_smoke_parser.add_argument("--secret-key", default="enterprise_dp_local_only_change_me", help="S3 secret key.")
    live_bronze_ingestion_smoke_parser.add_argument("--region-name", default="us-east-1", help="S3 region name.")
    live_bronze_ingestion_smoke_parser.add_argument("--catalog", default="iceberg", help="Trino Iceberg catalog name.")
    live_bronze_ingestion_smoke_parser.add_argument("--catalog-name", default="local_finance_iceberg", help="Iceberg JDBC catalog name.")
    live_bronze_ingestion_smoke_parser.add_argument("--catalog-uri", default="postgresql+psycopg://iceberg:iceberg_local_only_change_me@localhost:15432/iceberg", help="PyIceberg SQL catalog URI reachable from the host.")
    live_bronze_ingestion_smoke_parser.add_argument("--schema", default="bronze_runtime_smoke", help="Shared Iceberg schema for Bronze probe table.")
    live_bronze_ingestion_smoke_parser.add_argument("--table", default="events_benefit_settled", help="Bronze Iceberg probe table.")
    live_bronze_ingestion_smoke_parser.add_argument("--source-id", default="enterprise-commerce-benefit-settled-outbox", help="Source registry id to seed into the local source outbox.")
    live_bronze_ingestion_smoke_parser.add_argument("--release-id", default="local-live-bronze-ingestion-smoke", help="Stable release/run id.")
    live_bronze_ingestion_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    live_bronze_ingestion_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    live_bronze_ingestion_smoke_parser.add_argument("--ingested-at", default=None, help="UTC Bronze ingestion timestamp override.")
    live_bronze_ingestion_smoke_parser.add_argument("--schema-id", default=None, help="Optional schema id recorded on Bronze rows.")
    live_bronze_ingestion_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    live_bronze_ingestion_smoke_parser.add_argument("--wait-attempts", type=int, default=12)
    live_bronze_ingestion_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before runtime commands.")
    orchestrated_publication_smoke_parser = subparsers.add_parser(
        "orchestrated-publication-smoke",
        help="Run Bronze Iceberg to Silver/Gold Iceberg publication through local Dagster and Trino.",
    )
    orchestrated_publication_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    orchestrated_publication_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for orchestrated publication artifacts.")
    orchestrated_publication_smoke_parser.add_argument("--output", required=True, help="Output orchestrated_live_publication_report.v1 JSON path.")
    orchestrated_publication_smoke_parser.add_argument("--live-bronze-ingestion-smoke-report", default=None, help="Optional live_bronze_ingestion_runtime_report.v1 input.")
    orchestrated_publication_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    orchestrated_publication_smoke_parser.add_argument("--trino-service", default="trino", help="Compose service name for Trino.")
    orchestrated_publication_smoke_parser.add_argument("--iceberg-postgres-service", default="iceberg-postgres", help="Compose service name for Iceberg JDBC catalog Postgres.")
    orchestrated_publication_smoke_parser.add_argument("--minio-service", default="minio", help="Compose service name for MinIO.")
    orchestrated_publication_smoke_parser.add_argument("--bucket", default="enterprise-dp-local-iceberg", help="MinIO/S3 bucket for Iceberg warehouse data.")
    orchestrated_publication_smoke_parser.add_argument("--endpoint-url", default="http://localhost:19000", help="S3-compatible endpoint URL reachable from the host.")
    orchestrated_publication_smoke_parser.add_argument("--access-key", default="enterprise_dp_local", help="S3 access key.")
    orchestrated_publication_smoke_parser.add_argument("--secret-key", default="enterprise_dp_local_only_change_me", help="S3 secret key.")
    orchestrated_publication_smoke_parser.add_argument("--region-name", default="us-east-1", help="S3 region name.")
    orchestrated_publication_smoke_parser.add_argument("--catalog", default="iceberg", help="Trino Iceberg catalog name.")
    orchestrated_publication_smoke_parser.add_argument("--catalog-name", default="local_finance_iceberg", help="Iceberg JDBC catalog name.")
    orchestrated_publication_smoke_parser.add_argument("--catalog-uri", default="postgresql+psycopg://iceberg:iceberg_local_only_change_me@localhost:15432/iceberg", help="PyIceberg SQL catalog URI reachable from the host.")
    orchestrated_publication_smoke_parser.add_argument("--bronze-schema", default="bronze_runtime_smoke", help="Bronze Iceberg schema to read.")
    orchestrated_publication_smoke_parser.add_argument("--bronze-table", default="events_benefit_settled", help="Bronze Iceberg table to read.")
    orchestrated_publication_smoke_parser.add_argument("--publication-schema", default="publication_runtime_smoke", help="Silver/Gold Iceberg publication schema.")
    orchestrated_publication_smoke_parser.add_argument("--silver-table", default="finance_benefit_transactions", help="Silver Iceberg table name.")
    orchestrated_publication_smoke_parser.add_argument("--gold-table", default="finance_benefit_reconciliation", help="Gold Iceberg table name.")
    orchestrated_publication_smoke_parser.add_argument("--release-id", default="local-orchestrated-live-publication-smoke", help="Stable release/run id.")
    orchestrated_publication_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    orchestrated_publication_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    orchestrated_publication_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    orchestrated_publication_smoke_parser.add_argument("--wait-attempts", type=int, default=12)
    orchestrated_publication_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before runtime commands.")
    live_quality_slo_smoke_parser = subparsers.add_parser(
        "live-quality-slo-smoke",
        help="Run live Trino quality/SLO checks over published Gold Iceberg and emit quality gate evidence.",
    )
    live_quality_slo_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    live_quality_slo_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for live quality/SLO artifacts.")
    live_quality_slo_smoke_parser.add_argument("--output", required=True, help="Output live_quality_slo_smoke_report.v1 JSON path.")
    live_quality_slo_smoke_parser.add_argument("--orchestrated-publication-smoke-report", default=None, help="Optional orchestrated_live_publication_report.v1 input.")
    live_quality_slo_smoke_parser.add_argument("--compose-file", default=None, help="Docker Compose file. Defaults to platform/runtime/local/docker-compose.yaml.")
    live_quality_slo_smoke_parser.add_argument("--trino-service", default="trino", help="Compose service name for Trino.")
    live_quality_slo_smoke_parser.add_argument("--iceberg-postgres-service", default="iceberg-postgres", help="Compose service name for Iceberg JDBC catalog Postgres.")
    live_quality_slo_smoke_parser.add_argument("--release-id", default="local-live-quality-slo-smoke", help="Stable release/run id.")
    live_quality_slo_smoke_parser.add_argument("--environment", default="local", choices=("local", "dev", "staging", "prod"))
    live_quality_slo_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    live_quality_slo_smoke_parser.add_argument("--data-product", default="gold.finance_benefit_reconciliation", help="Gold data product to validate.")
    live_quality_slo_smoke_parser.add_argument("--freshness-slo-seconds", type=int, default=900, help="Freshness SLO threshold for the Gold runtime check.")
    live_quality_slo_smoke_parser.add_argument("--command-timeout-seconds", type=int, default=180)
    live_quality_slo_smoke_parser.add_argument("--wait-attempts", type=int, default=12)
    live_quality_slo_smoke_parser.add_argument("--no-start-runtime", action="store_true", help="Do not run docker compose up before runtime commands.")
    portfolio_release_smoke_parser = subparsers.add_parser(
        "portfolio-release-smoke",
        help="Run local multi-use-case release evidence smoke and generate consolidated Control Tower evidence.",
    )
    portfolio_release_smoke_parser.add_argument("--root", default=".", help="Data platform root directory.")
    portfolio_release_smoke_parser.add_argument("--output-dir", required=True, help="Output directory for portfolio release artifacts.")
    portfolio_release_smoke_parser.add_argument("--output", required=True, help="Output portfolio_release_smoke_report.v1 JSON path.")
    portfolio_release_smoke_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"))
    portfolio_release_smoke_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    production_review_parser = subparsers.add_parser(
        "production-review-pack",
        help="Generate a partner-review artifact pack with data-plane smoke, runtime readiness, capability and Control Tower evidence.",
    )
    production_review_parser.add_argument("--root", default=".", help="Data platform root directory.")
    production_review_parser.add_argument("--output-dir", required=True, help="Output directory for the review pack.")
    production_review_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Review target environment.")
    production_review_parser.add_argument("--generated-at", default=None, help="UTC review pack timestamp override.")
    production_review_parser.add_argument("--use-case-id", "--use-case", dest="use_case_id", default="finance-benefit-reconciliation")
    production_review_parser.add_argument("--release-id", default="local-data-plane-smoke", help="Stable release/run id for the smoke slice.")
    production_review_parser.add_argument("--smoke-generated-at", default=None, help="UTC smoke report timestamp override.")
    production_review_parser.add_argument("--ingested-at", default=None, help="UTC ingestion timestamp override.")
    production_review_parser.add_argument("--built-at", default=None, help="UTC pipeline build timestamp override.")
    production_review_parser.add_argument("--evaluation-time", default=None, help="UTC release-gate evaluation timestamp override.")
    production_review_parser.add_argument("--schema-id", default=None, help="Schema registry id or local compatibility id.")
    production_review_parser.add_argument("--snapshot-id", default=None, help="Optional dataset snapshot id.")
    production_review_parser.add_argument(
        "--event-backbone-smoke-report",
        default=None,
        help="Optional event_backbone_smoke_report.v1 JSON artifact from enterprise-dp event-backbone-smoke.",
    )
    production_review_parser.add_argument(
        "--ingestion-runtime-report",
        default=None,
        help="Optional event_cdc_ingestion_runtime_report.v1 JSON artifact from enterprise-dp ingestion-runtime-check or event-backbone-smoke.",
    )
    production_review_parser.add_argument(
        "--catalog-lineage-ops-report",
        default=None,
        help="Optional production-like catalog_lineage_ops_report.v1 JSON artifact.",
    )
    production_review_parser.add_argument(
        "--semantic-metric-serving-ops-report",
        default=None,
        help="Optional production-like semantic_metric_serving_ops_report.v1 JSON artifact.",
    )
    production_review_parser.add_argument(
        "--source-activation-ops-report",
        default=None,
        help="Optional production-like source_activation_ops_report.v1 JSON artifact.",
    )
    production_review_parser.add_argument(
        "--backfill-readiness-report",
        default=None,
        help="Optional production-like backfill_readiness_report.v1 JSON artifact.",
    )
    production_review_parser.add_argument(
        "--runtime-readiness-report",
        default=None,
        help="Optional runtime_readiness_report.v1 JSON artifact from enterprise-dp runtime-readiness-check.",
    )
    production_review_parser.add_argument(
        "--runtime-iac-plan",
        default=None,
        help="Optional runtime_iac_plan_evidence.v1 JSON artifact used to build runtime readiness inside the review pack.",
    )
    production_review_parser.add_argument(
        "--runtime-iac-apply",
        default=None,
        help="Optional runtime_iac_apply_evidence.v1 JSON artifact used to build runtime readiness inside the review pack.",
    )
    production_review_parser.add_argument(
        "--runtime-drift-report",
        default=None,
        help="Optional runtime_iac_drift_report.v1 JSON artifact used to build runtime readiness inside the review pack.",
    )
    production_review_parser.add_argument(
        "--runtime-backup-report",
        default=None,
        help="Optional runtime_backup_evidence.v1 JSON artifact used to build runtime readiness inside the review pack.",
    )
    production_review_parser.add_argument(
        "--runtime-dr-report",
        default=None,
        help="Optional runtime_dr_evidence.v1 JSON artifact required for production runtime readiness.",
    )
    production_review_parser.add_argument(
        "--runtime-health-report",
        default=None,
        help="Optional runtime_service_health_evidence.v1 JSON artifact used to build runtime readiness inside the review pack.",
    )
    production_review_parser.add_argument(
        "--workload-benchmark-report",
        default=None,
        help="Optional workload_benchmark_report.v1 artifact from managed staging/prod scale testing.",
    )
    production_review_parser.add_argument(
        "--schema-registry-runtime-smoke-report",
        default=None,
        help="Optional schema_registry_runtime_smoke_report.v1 JSON artifact from enterprise-dp schema-registry-runtime-smoke.",
    )
    production_review_parser.add_argument(
        "--schema-registry-attestation-report",
        default=None,
        help="Optional external_evidence_attestation.v1 for schema_registry_publication_manifest.v1.",
    )
    production_review_parser.add_argument(
        "--schema-registry-ops-report",
        default=None,
        help="Optional production-like schema_registry_ops_report.v1 JSON artifact.",
    )
    production_review_parser.add_argument(
        "--schema-registry-auth-smoke-report",
        default=None,
        help="Optional schema_registry_auth_smoke_report.v1 JSON artifact from enterprise-dp schema-registry-auth-smoke.",
    )
    production_review_parser.add_argument(
        "--schema-registry-storage-smoke-report",
        default=None,
        help="Optional schema_registry_storage_smoke_report.v1 JSON artifact from enterprise-dp schema-registry-storage-smoke.",
    )
    production_review_parser.add_argument(
        "--broker-acl-smoke-report",
        default=None,
        help="Optional broker_acl_smoke_report.v1 JSON artifact from enterprise-dp broker-acl-smoke.",
    )
    production_review_parser.add_argument(
        "--transactional-outbox-smoke-report",
        default=None,
        help="Optional transactional_outbox_smoke_report.v1 JSON artifact from enterprise-dp transactional-outbox-smoke.",
    )
    production_review_parser.add_argument(
        "--live-bronze-ingestion-smoke-report",
        default=None,
        help="Optional live_bronze_ingestion_runtime_report.v1 JSON artifact from enterprise-dp live-bronze-ingestion-smoke.",
    )
    production_review_parser.add_argument(
        "--orchestrated-publication-smoke-report",
        default=None,
        help="Optional orchestrated_live_publication_report.v1 JSON artifact from enterprise-dp orchestrated-publication-smoke.",
    )
    production_review_parser.add_argument(
        "--live-quality-slo-smoke-report",
        default=None,
        help="Optional live_quality_slo_smoke_report.v1 JSON artifact from enterprise-dp live-quality-slo-smoke.",
    )
    production_review_parser.add_argument(
        "--live-lakehouse-smoke-report",
        default=None,
        help="Optional live_lakehouse_smoke_report.v1 JSON artifact from enterprise-dp live-lakehouse-smoke.",
    )
    production_review_parser.add_argument(
        "--iceberg-catalog-smoke-report",
        default=None,
        help="Optional iceberg_catalog_smoke_report.v1 JSON artifact from enterprise-dp iceberg-catalog-smoke.",
    )
    production_review_parser.add_argument(
        "--object-store-smoke-report",
        default=None,
        help="Optional object_store_commit_smoke_report.v1 JSON artifact from enterprise-dp object-store-commit-smoke.",
    )
    production_review_parser.add_argument(
        "--trino-sql-smoke-report",
        default=None,
        help="Optional trino_sql_runtime_smoke_report.v1 JSON artifact from enterprise-dp trino-sql-runtime-smoke.",
    )
    production_review_parser.add_argument(
        "--trino-iceberg-minio-smoke-report",
        default=None,
        help="Optional trino_iceberg_minio_smoke_report.v1 JSON artifact from enterprise-dp trino-iceberg-minio-smoke.",
    )
    production_review_parser.add_argument(
        "--catalog-cross-engine-smoke-report",
        default=None,
        help="Optional catalog_cross_engine_smoke_report.v1 JSON artifact from enterprise-dp catalog-cross-engine-smoke.",
    )
    production_review_parser.add_argument(
        "--catalog-runtime-ops-report",
        default=None,
        help="Optional production-like catalog_runtime_ops_report.v1 JSON artifact.",
    )
    production_review_parser.add_argument(
        "--orchestration-runtime-ops-report",
        default=None,
        help="Optional production-like orchestration_runtime_ops_report.v1 JSON artifact.",
    )
    production_review_parser.add_argument(
        "--trino-runtime-security-smoke-report",
        default=None,
        help="Optional trino_runtime_security_smoke_report.v1 JSON artifact from enterprise-dp trino-runtime-security-smoke.",
    )
    production_review_parser.add_argument(
        "--policy-decision-smoke-report",
        default=None,
        help="Optional policy_decision_smoke_report.v1 JSON artifact from enterprise-dp policy-decision-smoke.",
    )
    production_review_parser.add_argument(
        "--oidc-auth-smoke-report",
        default=None,
        help="Optional oidc_auth_smoke_report.v1 JSON artifact from enterprise-dp oidc-auth-smoke.",
    )
    production_review_parser.add_argument(
        "--secret-rotation-smoke-report",
        default=None,
        help="Optional secret_rotation_smoke_report.v1 JSON artifact from enterprise-dp secret-rotation-smoke.",
    )
    production_review_parser.add_argument(
        "--secret-rotation-ops-report",
        default=None,
        help="Optional production-like secret_rotation_ops_report.v1 JSON artifact.",
    )
    production_review_parser.add_argument(
        "--dagster-orchestration-smoke-report",
        default=None,
        help="Optional dagster_orchestration_smoke_report.v1 JSON artifact from enterprise-dp dagster-orchestration-smoke.",
    )
    production_review_parser.add_argument(
        "--dagster-day2-smoke-report",
        default=None,
        help="Optional dagster_day2_smoke_report.v1 JSON artifact from enterprise-dp dagster-day2-smoke.",
    )
    production_review_parser.add_argument(
        "--portfolio-release-smoke-report",
        default=None,
        help="Optional portfolio_release_smoke_report.v1 JSON artifact from enterprise-dp portfolio-release-smoke.",
    )
    production_review_gate_parser = subparsers.add_parser(
        "production-review-gate",
        help="Fail-closed gate over an existing production_review_pack.v1 manifest.",
    )
    production_review_gate_parser.add_argument(
        "--manifest",
        default="build/production-review-pack/production-review-pack.json",
        help="Path to production-review-pack.json.",
    )
    production_review_gate_parser.add_argument(
        "--profile",
        default="code-control-plane",
        choices=("partner-review", "code-control-plane", "source-onboarding", "production-ready"),
        help="Gate profile to enforce.",
    )
    production_review_gate_parser.add_argument(
        "--environment",
        default=None,
        choices=("local", "staging", "prod"),
        help="Optional expected manifest environment.",
    )
    production_review_gate_parser.add_argument(
        "--output",
        default=None,
        help="Optional output production_review_gate_report.v1 JSON path.",
    )
    production_review_gate_parser.add_argument("--generated-at", default=None, help="UTC report timestamp override.")
    slice_parser = subparsers.add_parser(
        "run-recommendation-slice",
        help="Run local Bronze -> Silver/Gold -> catalog -> release-gate evidence for recommendation.",
    )
    slice_parser.add_argument("--root", default=".", help="Data platform root directory.")
    slice_parser.add_argument("--input", required=True, help="Input JSONL recommendation tracking events.")
    slice_parser.add_argument("--output-dir", required=True, help="Output directory for all slice artifacts.")
    slice_parser.add_argument("--release-id", required=True, help="Stable release or run id.")
    slice_parser.add_argument("--environment", default="local", help="Environment label for evidence.")
    slice_parser.add_argument("--ingested-at", default=None, help="UTC ingestion timestamp override.")
    slice_parser.add_argument("--built-at", default=None, help="UTC medallion build timestamp override.")
    slice_parser.add_argument("--evaluation-time", default=None, help="UTC release-gate evaluation timestamp override.")
    slice_parser.add_argument("--schema-id", default=None, help="Schema registry id or local compatibility id.")
    slice_parser.add_argument("--code-commit-sha", default=None, help="Source commit SHA recorded in release evidence.")
    slice_parser.add_argument("--schema-registry-report-uri", default=None, help="Schema registry compatibility report URI.")
    slice_parser.add_argument("--schema-registry-report-hash", default=None, help="SHA-256 hash of the schema registry report.")
    slice_parser.add_argument("--validator-output-uri", default=None, help="Contract/data-quality validator output URI.")
    slice_parser.add_argument("--access-policy-check-id", default=None, help="Access policy check id recorded in release evidence.")
    slice_parser.add_argument("--access-policy-report-uri", default=None, help="Access policy evidence report URI.")
    slice_parser.add_argument("--access-policy-report-hash", default=None, help="SHA-256 hash of the access policy evidence report.")
    slice_parser.add_argument("--access-grant-evidence-uri", default=None, help="Access grant evidence report URI.")
    slice_parser.add_argument("--access-grant-evidence-hash", default=None, help="SHA-256 hash of the access grant evidence report.")
    slice_parser.add_argument("--retention-evidence-uri", default=None, help="Retention and erasure evidence report URI.")
    slice_parser.add_argument("--retention-evidence-hash", default=None, help="SHA-256 hash of the retention and erasure evidence report.")
    slice_parser.add_argument("--retention-evidence-input", default=None, help="Retention job evidence input JSON used to generate a release evidence report.")
    slice_parser.add_argument("--snapshot-evidence-uri", default=None, help="Lakehouse snapshot evidence report URI.")
    slice_parser.add_argument("--snapshot-evidence-hash", default=None, help="SHA-256 hash of the lakehouse snapshot evidence report.")
    slice_parser.add_argument("--approver", default=None, help="Approver identity recorded in release evidence.")

    args = parser.parse_args()
    if args.command == "validate":
        root = Path(args.root)
        result = validate_project_structure(root)
        result.extend(validate_contract_tree(root))
        result.extend(validate_product_onboarding_tree(root))
        result.extend(validate_domain_registry(root))
        result.extend(validate_access_persona_registry(root))
        result.extend(validate_consumer_contract_registry(root))
        result.extend(validate_access_grant_registry(root))
        result.extend(validate_change_request_registry(root))
        result.extend(validate_backfill_request_registry(root))
        result.extend(validate_access_policy_registry(root))
        result.extend(validate_evidence_trust_key_registry(root))
        result.extend(validate_retention_policy_registry(root))
        result.extend(validate_quality_profile_registry(root))
        result.extend(validate_release_profile_registry(root))
        result.extend(validate_use_case_registry(root))
        result.extend(validate_scope_guardrails(root))
        result.extend(validate_environment_manifests(root))
        result.extend(validate_runtime_topology(root))
        result.extend(validate_source_registry(root))
        result.extend(validate_source_activation_registry(root))
        result.extend(validate_incident_registry(root))
        result.extend(validate_pipeline_registry_manifest(root))
        result.extend(validate_semantic_metric_registry(root))
        result.extend(validate_semantic_metric_certification_registry(root))
        result.extend(validate_capability_registry(root))
        print_validation_result(result)
        return 0 if result.ok else 1
    if args.command == "product-scaffold":
        result = scaffold_product_onboarding(
            args.root,
            product_code=args.product_code,
            name=args.name,
            domains=args.domain,
            business_sponsor=args.business_sponsor,
            product_owner=args.product_owner,
            technical_owner=args.technical_owner,
            data_steward=args.data_steward,
            status=args.status,
            source_services=args.source_service or None,
            publication_modes=args.publication_mode or None,
            consumers=args.consumer or None,
            classification=args.classification,
            contains_pii=args.contains_pii,
            tenant_isolation=args.tenant_isolation,
            default_retention_policy=args.retention_policy,
            default_access_personas=args.access_persona or None,
            consumer_contract=args.consumer_contract,
            release_evidence_profile=args.release_evidence_profile,
            overwrite=args.overwrite,
        )
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0
    if args.command == "ingest-bronze":
        result = run_bronze_ingestion(
            args.root,
            args.topic,
            args.input,
            args.output_dir,
            ingested_at=args.ingested_at,
            ingest_run_id=args.ingest_run_id,
            schema_id=args.schema_id,
        )
        print(
            json.dumps(
                {
                    "topic": result.topic,
                    "approved_path": result.approved_path.as_posix(),
                    "quarantine_path": result.quarantine_path.as_posix(),
                    "manifest_path": result.manifest_path.as_posix(),
                    "approved_rows": result.manifest["approved"]["row_count"],
                    "quarantine_rows": result.manifest["quarantine"]["row_count"],
                    "quality_passed": result.manifest["quality_passed"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["quality_passed"] else 1
    if args.command == "catalog-export":
        bundle = write_catalog_bundle(
            args.root,
            args.output,
            manifest_paths=args.manifest,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "data_products": bundle["summary"]["data_product_count"],
                    "topics": bundle["summary"]["topic_count"],
                    "domains": bundle["summary"]["domain_count"],
                    "quality_profiles": bundle["summary"]["quality_profile_count"],
                    "access_policies": bundle["summary"]["access_policy_count"],
                    "access_personas": bundle["summary"]["access_persona_count"],
                    "consumer_contracts": bundle["summary"]["consumer_contract_count"],
                    "access_grants": bundle["summary"]["access_grant_count"],
                    "change_requests": bundle["summary"]["change_request_count"],
                    "release_evidence_profiles": bundle["summary"]["release_evidence_profile_count"],
                    "retention_policies": bundle["summary"]["retention_policy_count"],
                    "use_cases": bundle["summary"]["use_case_count"],
                    "products": bundle["summary"]["product_count"],
                    "lineage_edges": bundle["summary"]["lineage_edge_count"],
                    "run_evidence": bundle["summary"]["run_evidence_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "openlineage-export":
        result = write_openlineage_events(
            args.catalog,
            args.output,
            namespace=args.namespace,
            producer=args.producer,
        )
        print(
            json.dumps(
                {
                    "output": result["output_path"].as_posix(),
                    "event_count": result["event_count"],
                    "content_hash": result["content_hash"],
                    "catalog_bundle_hash": result["catalog_bundle_hash"],
                    "namespace": result["namespace"],
                    "producer": result["producer"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "catalog-publish-manifest":
        result = write_catalog_publish_manifest(
            args.catalog,
            args.output,
            target_system=args.target_system,
            environment=args.environment,
            endpoint=args.endpoint,
            openlineage_events_path=args.openlineage_events,
            semantic_views_manifest_path=args.semantic_views,
            requested_by=args.requested_by,
            change_ticket=args.change_ticket,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "publish_state": result.manifest["publish_state"],
                    "target_system": result.manifest["target"]["system"],
                    "environment": result.manifest["target"]["environment"],
                    "passed": result.manifest["passed"],
                    "failure_count": len(result.manifest["failures"]),
                    "data_products": result.manifest["publish_payload"]["data_products"],
                    "lineage_edges": result.manifest["publish_payload"]["lineage_edges"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["passed"] else 1
    if args.command == "catalog-lineage-ops-report":
        result = write_catalog_lineage_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            catalog_bundle_path=args.catalog,
            catalog_publish_manifest_path=args.catalog_publish_manifest,
            openlineage_events_path=args.openlineage_events,
            publish_receipt_path=args.publish_receipt,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "readiness_state": result.report["readiness_state"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "quality-slo-release-gates-ops-report":
        result = write_quality_slo_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            catalog_bundle_path=args.catalog,
            release_evidence_paths=args.release_evidence,
            quality_runtime_evidence_path=args.quality_runtime_evidence,
            alert_evidence_path=args.alert_evidence,
            incident_report_path=args.incident_report,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "readiness_state": result.report["readiness_state"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "observability-export":
        result = write_observability_artifacts(
            args.catalog,
            metrics_output_path=args.output_metrics,
            summary_output_path=args.output_summary,
            release_evidence_paths=args.release_evidence,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "metrics_output": result["metrics_output_path"].as_posix(),
                    "summary_output": result["summary_output_path"].as_posix(),
                    "metrics_hash": result["metrics_hash"],
                    "summary_hash": result["summary_hash"],
                    "metrics_count": result["metrics_count"],
                    "environment": result["environment"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "semantic-views-export":
        manifest = write_semantic_view_manifest(
            args.root,
            args.output,
            engine=args.engine,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": str(args.output),
                    "registry_hash": manifest["registry_hash"],
                    "engine": manifest["engine"],
                    "metric_count": manifest["summary"]["metric_count"],
                    "view_count": manifest["summary"]["view_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "semantic-metric-certification-report":
        result = write_semantic_metric_certification_report(
            args.root,
            args.output,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "readiness_state": result.report["readiness_state"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "semantic-metric-serving-ops-report":
        result = write_semantic_metric_serving_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            semantic_view_manifest_path=args.semantic_view_manifest,
            metric_certification_report_path=args.metric_certification_report,
            serving_deployment_evidence_path=args.serving_deployment_evidence,
            usage_evidence_path=args.usage_evidence,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "readiness_state": result.report["readiness_state"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "capability-maturity-report":
        result = write_capability_maturity_report(
            args.root,
            args.output,
            phase=args.phase,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "readiness_state": result.report["readiness_state"],
                    "p0_ready": result.report["p0_ready"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "blocker_count": len(result.report["blockers"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "control-tower-report":
        result = write_data_product_control_tower_report(
            args.root,
            args.output,
            catalog_bundle_path=args.catalog,
            catalog_lineage_ops_report_path=args.catalog_lineage_ops_report,
            quality_slo_ops_report_path=args.quality_slo_release_gates_ops_report,
            semantic_metric_serving_ops_report_path=args.semantic_metric_serving_ops_report,
            schema_registry_ops_report_path=args.schema_registry_ops_report,
            catalog_runtime_ops_report_path=args.catalog_runtime_ops_report,
            orchestration_runtime_ops_report_path=args.orchestration_runtime_ops_report,
            data_plane_smoke_report_path=args.data_plane_smoke_report,
            release_evidence_paths=args.release_evidence,
            capability_maturity_report_path=args.capability_maturity_report,
            access_grant_ops_report_path=args.access_grant_ops_report,
            source_activation_ops_report_path=args.source_activation_ops_report,
            ingestion_runtime_report_path=args.ingestion_runtime_report,
            bronze_lakehouse_ops_report_path=args.bronze_lakehouse_ops_report,
            silver_gold_publication_ops_report_path=args.silver_gold_publication_ops_report,
            contract_impact_report_paths=args.contract_impact_report,
            runtime_readiness_report_path=args.runtime_readiness_report,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "readiness_state": result.report["readiness_state"],
                    "p0_ready": result.report["p0_ready"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "blocker_count": len(result.report["blockers"]),
                    "data_product_count": result.report["summary"]["data_product_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "incident-report":
        result = write_incident_report(
            args.control_tower_report,
            args.output,
            incident_registry_path=args.incident_registry,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "readiness_state": result.report["readiness_state"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "portfolio-readiness-report":
        result = write_enterprise_portfolio_readiness_report(
            args.root,
            args.output,
            environment=args.environment,
            generated_at=args.generated_at,
            source_activation_ledger_path=args.source_activation_ledger,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "readiness_state": result.report["readiness_state"],
                    "p0_ready": result.report["p0_ready"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "blocker_count": len(result.report["blockers"]),
                    "blocked_p0_use_cases": result.report["decision_board"]["blocked_p0_use_cases"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command in {"runtime-readiness-check", "runtime-iac-readiness-check"}:
        result = write_runtime_readiness_report(
            args.root,
            args.output,
            environment=args.environment,
            iac_plan_path=args.iac_plan,
            iac_apply_path=args.iac_apply,
            drift_report_path=args.drift_report,
            backup_report_path=args.backup_report,
            dr_report_path=args.dr_report,
            health_report_path=args.health_report,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "readiness_id": result.report["report_id"],
                    "readiness_state": result.report["readiness_state"],
                    "environment": result.report["environment"],
                    "passed": result.report["passed"],
                    "failure_count": len(result.report["failures"]),
                    "required_service_count": result.report["summary"]["required_p0_service_count"],
                    "deployed_service_count": result.report["summary"]["deployed_service_count"],
                    "healthy_service_count": result.report["summary"]["healthy_service_count"],
                    "topology_service_count": result.report["summary"]["topology_service_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "runtime-evidence-pack":
        result = write_runtime_evidence_pack(
            args.root,
            args.output_dir,
            environment=args.environment,
            source_kind=args.source_kind,
            generated_at=args.generated_at,
            valid_until=args.valid_until,
            git_sha=args.git_sha,
            ci_run_id=args.ci_run_id,
            issuer_tool=args.issuer_tool,
            issuer_tool_version=args.issuer_tool_version,
            artifact_base_uri=args.artifact_base_uri,
            change_request_id=args.change_request_id,
            include_dr=args.include_dr or None,
            destructive_change_count=args.destructive_change_count,
            drifted_resource_count=args.drifted_resource_count,
        )
        print(
            json.dumps(
                {
                    "output_dir": result.output_dir.as_posix(),
                    "manifest_path": result.manifest_path.as_posix(),
                    "evidence_pack_id": result.manifest["manifest_id"],
                    "environment": result.manifest["environment"],
                    "profile_id": result.manifest["profile_id"],
                    "source_kind": result.manifest["source_kind"],
                    "passed": result.manifest["passed"],
                    "artifact_count": len(result.manifest["artifacts"]),
                    "blocker_count": len(result.manifest["blockers"]),
                    "production_signoff_allowed": result.manifest["production_signoff_allowed"],
                    "readiness_args": result.manifest["readiness_args"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["passed"] else 1
    if args.command == "runtime-evidence-normalize-iac":
        try:
            result = write_runtime_iac_evidence_pack(
                args.root,
                args.output_dir,
                environment=args.environment,
                plan_json_path=args.plan_json,
                state_json_path=args.state_json,
                health_checks_path=args.health_checks,
                backup_checks_path=args.backup_checks,
                dr_exercise_path=args.dr_exercise,
                resource_map_path=args.resource_map,
                source_kind=args.source_kind,
                generated_at=args.generated_at,
                valid_until=args.valid_until,
                git_sha=args.git_sha,
                ci_run_id=args.ci_run_id,
                issuer_tool=args.issuer_tool,
                issuer_tool_version=args.issuer_tool_version,
                artifact_base_uri=args.artifact_base_uri,
                change_request_id=args.change_request_id,
            )
        except ValueError as exc:
            print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=True, sort_keys=True))
            return 1
        print(
            json.dumps(
                {
                    "output_dir": result.output_dir.as_posix(),
                    "manifest_path": result.manifest_path.as_posix(),
                    "evidence_pack_id": result.manifest["manifest_id"],
                    "environment": result.manifest["environment"],
                    "profile_id": result.manifest["profile_id"],
                    "source_kind": result.manifest["source_kind"],
                    "passed": result.manifest["passed"],
                    "artifact_count": len(result.manifest["artifacts"]),
                    "change_count": result.manifest["plan_summary"]["change_count"],
                    "destructive_change_count": result.manifest["plan_summary"]["destructive_change_count"],
                    "replacement_count": result.manifest["plan_summary"]["replacement_count"],
                    "deployed_service_count": len(result.manifest["deployed_services"]),
                    "production_signoff_allowed": result.manifest["production_signoff_allowed"],
                    "readiness_args": result.manifest["readiness_args"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "attestation-verify":
        result = verify_attestation_file(
            args.root,
            args.input,
            evidence_kind=args.evidence_kind,
            environment=args.environment,
            release_id=args.release_id,
            subject_path=args.subject,
            subject_hash=args.subject_hash,
        )
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0 if result["passed"] else 1
    if args.command == "schema-registry-attestation":
        try:
            result = write_schema_registry_publication_attestation(
                args.root,
                args.output,
                publication_manifest_path=args.publication_manifest,
                schema_registry_runtime_smoke_report_path=args.schema_registry_runtime_smoke_report,
                environment=args.environment,
                release_id=args.release_id,
                generated_at=args.generated_at,
                subject_uri=args.subject_uri,
                signing_key_id=args.signing_key_id,
                producer=args.producer,
                private_key_seed_base64=args.private_key_seed_base64,
            )
        except ValueError as exc:
            print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=True, sort_keys=True))
            return 1
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.verification["passed"],
                    "environment": result.report["environment"],
                    "release_id": result.report["release_id"],
                    "subject_uri": result.report["subject_uri"],
                    "subject_hash": result.report["subject_hash"],
                    "signing_key_id": result.report["signing_key_id"],
                    "signing_key_material_source": result.report["signing_key_material_source"],
                    "signature_verified": result.verification["required"]["signature_verified"],
                    "subject_hash_matches": result.verification["required"]["subject_hash_matches"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.verification["passed"] else 1
    if args.command == "release-promote":
        result = write_release_promotion_manifest(
            args.release_evidence,
            args.output,
            target_environment=args.target_environment,
            requested_by=args.requested_by,
            approver=args.approver,
            change_ticket=args.change_ticket,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "promotion_id": result.manifest["promotion_id"],
                    "promotion_state": result.manifest["promotion_state"],
                    "release_id": result.manifest["release_id"],
                    "target_environment": result.manifest["target_environment"],
                    "passed": result.manifest["passed"],
                    "failure_count": len(result.manifest["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["passed"] else 1
    if args.command == "release-activate":
        result = write_release_activation_manifest(
            args.promotion_manifest,
            args.output,
            active_state_path=args.active_state,
            activated_by=args.activated_by,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "active_state": result.active_state_path.as_posix(),
                    "activation_id": result.manifest["activation_id"],
                    "activation_state": result.manifest["activation_state"],
                    "promotion_id": result.manifest["promotion_id"],
                    "release_id": result.manifest["release_id"],
                    "target_environment": result.manifest["target_environment"],
                    "passed": result.manifest["passed"],
                    "failure_count": len(result.manifest["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["passed"] else 1
    if args.command == "schema-registry-check":
        result = write_schema_registry_report(
            args.root,
            args.output,
            topic_name=args.topic,
            registry_uri=args.registry_uri,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "compatibility_passed": result.report["compatibility_passed"],
                    "subject_count": result.report["subject_count"],
                    "failed_subjects": result.report["summary"]["failed_subjects"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["compatibility_passed"] else 1
    if args.command == "schema-registry-ops-report":
        result = write_schema_registry_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            release_id=args.release_id,
            compatibility_report_path=args.compatibility_report,
            publication_evidence_path=args.publication_evidence,
            attestation_path=args.attestation,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "mode": result.report["mode"],
                    "passed": result.report["passed"],
                    "subject_count": result.report["summary"]["subject_count"],
                    "failed_subject_count": result.report["summary"]["failed_subject_count"],
                    "p0_failed_subject_count": result.report["summary"]["p0_failed_subject_count"],
                    "global_failed_check_count": result.report["summary"]["global_failed_check_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "schema-registry-runtime-smoke":
        result = write_schema_registry_runtime_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            topic_name=args.topic_name,
            compose_file=args.compose_file,
            service=args.service,
            registry_url=args.registry_url,
            group_id=args.group_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "registry_uri": result.report["summary"]["registry_uri"],
                    "registry_api": result.report["summary"]["registry_api"],
                    "subject_count": result.report["summary"]["subject_count"],
                    "published_subject_count": result.report["summary"]["published_subject_count"],
                    "readback_passed_count": result.report["summary"]["readback_passed_count"],
                    "hash_match_count": result.report["summary"]["hash_match_count"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "schema-registry-auth-smoke":
        result = write_schema_registry_auth_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            compose_file=args.compose_file,
            service=args.service,
            registry_url=args.registry_url,
            gateway_host=args.gateway_host,
            gateway_port=args.gateway_port,
            group_id=args.group_id,
            subject=args.subject,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "registry_uri": result.report["summary"]["registry_uri"],
                    "gateway_uri": result.report["summary"]["gateway_uri"],
                    "auth_gateway_enforced": result.report["summary"]["auth_gateway_enforced"],
                    "missing_token_denied": result.report["summary"]["missing_token_denied"],
                    "unknown_token_denied": result.report["summary"]["unknown_token_denied"],
                    "denied_token_blocked": result.report["summary"]["denied_token_blocked"],
                    "reader_write_denied": result.report["summary"]["reader_write_denied"],
                    "publisher_publish_allowed": result.report["summary"]["publisher_publish_allowed"],
                    "reader_read_allowed": result.report["summary"]["reader_read_allowed"],
                    "authorization_audit_event_count": result.report["summary"]["authorization_audit_event_count"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "schema-registry-storage-smoke":
        result = write_schema_registry_storage_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            sql_image=args.sql_image,
            postgres_image=args.postgres_image,
            network=args.network,
            registry_a_port=args.registry_a_port,
            registry_b_port=args.registry_b_port,
            group_id=args.group_id,
            subject=args.subject,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
            cleanup_runtime=not args.no_cleanup_runtime,
            registry_a_url=args.registry_a_url,
            registry_b_url=args.registry_b_url,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "registry_a_uri": result.report["summary"]["registry_a_uri"],
                    "registry_b_uri": result.report["summary"]["registry_b_uri"],
                    "storage_backend": result.report["summary"]["storage_backend"],
                    "registry_replica_count": result.report["summary"]["registry_replica_count"],
                    "shared_sql_storage_configured": result.report["summary"]["shared_sql_storage_configured"],
                    "cross_replica_read_after_write_passed": result.report["summary"][
                        "cross_replica_read_after_write_passed"
                    ],
                    "replica_restart_durable_readback_passed": result.report["summary"][
                        "replica_restart_durable_readback_passed"
                    ],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "contract-impact-report":
        result = write_contract_impact_report(
            args.root,
            args.output,
            topic_name=args.topic,
            schema_registry_report_path=args.schema_registry_report,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "topic": result.report["topic"]["name"],
                    "passed": result.report["passed"],
                    "release_decision": result.report["impact"]["release_decision"],
                    "risk_level": result.report["impact"]["risk_level"],
                    "breaking_change_count": result.report["compatibility"]["breaking_change_count"],
                    "affected_data_product_count": result.report["impact"]["affected_data_product_count"],
                    "affected_use_case_count": result.report["impact"]["affected_use_case_count"],
                    "affected_p0_use_case_count": result.report["impact"]["affected_p0_use_case_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "source-bridge-normalize":
        result = run_source_bridge_preflight(
            args.root,
            args.source_id,
            args.input,
            args.output_dir,
            normalized_at=args.normalized_at,
            bridge_run_id=args.bridge_run_id,
        )
        print(
            json.dumps(
                {
                    "source_id": result.source_id,
                    "canonical_topic": result.canonical_topic,
                    "normalized_path": result.normalized_path.as_posix(),
                    "quarantine_path": result.quarantine_path.as_posix(),
                    "manifest_path": result.manifest_path.as_posix(),
                    "quality_passed": result.manifest["quality_passed"],
                    "normalized_rows": result.manifest["normalized"]["row_count"],
                    "quarantine_rows": result.manifest["quarantine"]["row_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["quality_passed"] else 1
    if args.command == "source-readiness-bundle":
        result = run_source_readiness_bundle(
            args.root,
            args.source_id,
            args.input,
            args.output_dir,
            environment=args.environment,
            bundle_id=args.bundle_id,
            generated_at=args.generated_at,
            ingested_at=args.ingested_at,
            replayed_at=args.replayed_at,
            schema_registry_uri=args.schema_registry_uri,
            change_request_id=args.change_request_id,
            target_snapshot_id=args.target_snapshot_id,
            table_metadata_uri=args.table_metadata_uri,
            table_metadata_hash=args.table_metadata_hash,
            openlineage_namespace=args.openlineage_namespace,
            openlineage_producer=args.openlineage_producer,
        )
        print(
            json.dumps(
                {
                    "output": result.summary_path.as_posix(),
                    "source_id": result.source_id,
                    "environment": result.environment,
                    "readiness_report": result.readiness_path.as_posix(),
                    "readiness_id": result.readiness["readiness_id"],
                    "readiness_state": result.readiness["readiness_state"],
                    "passed": result.summary["passed"],
                    "failure_count": result.summary["quality"]["failure_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.summary["passed"] else 1
    if args.command == "source-activate":
        result = write_source_activation_manifest_from_bundle(
            args.root,
            args.bundle,
            args.output,
            requested_by=args.requested_by,
            approved_by=args.approved_by,
            change_request_id=args.change_request_id,
            ledger_path=args.ledger,
            active_state_path=args.active_state,
            expires_at=args.expires_at,
            generated_at=args.generated_at,
            impacted_use_cases=args.impacted_use_case or None,
            reason=args.reason,
            runtime_readiness_report_path=args.runtime_readiness_report,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "activation_id": result.manifest["activation_id"],
                    "activation_state": result.manifest["activation_state"],
                    "source_id": result.manifest["source_id"],
                    "environment": result.manifest["environment"],
                    "ledger": result.ledger_path.as_posix(),
                    "active_state": result.active_state_path.as_posix(),
                    "passed": result.manifest["passed"],
                    "failure_count": len(result.manifest["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["passed"] else 1
    if args.command == "source-revoke":
        result = write_source_revocation_manifest(
            args.root,
            args.output,
            source_id=args.source_id,
            environment=args.environment,
            requested_by=args.requested_by,
            approved_by=args.approved_by,
            change_request_id=args.change_request_id,
            ledger_path=args.ledger,
            active_state_path=args.active_state,
            generated_at=args.generated_at,
            reason=args.reason,
            evidence_uri=args.evidence_uri,
            impacted_use_cases=args.impacted_use_case or None,
            allow_missing_active_pointer=args.allow_missing_active_pointer,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "revocation_id": result.manifest["revocation_id"],
                    "revocation_state": result.manifest["revocation_state"],
                    "source_id": result.manifest["source_id"],
                    "environment": result.manifest["environment"],
                    "ledger": result.ledger_path.as_posix(),
                    "active_state": result.active_state_path.as_posix(),
                    "passed": result.manifest["passed"],
                    "failure_count": len(result.manifest["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["passed"] else 1
    if args.command == "source-activation-ops-report":
        result = write_source_activation_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            ledger_path=args.ledger,
            active_pointer_dir=args.active_pointer_dir,
            generated_at=args.as_of,
            expiry_warning_days=args.expiring_within_days,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "critical_sources": result.report["decision_board"]["critical_sources"],
                    "expiring_sources": result.report["decision_board"]["expiring_sources"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "ingestion-runtime-check":
        result = write_ingestion_runtime_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            evidence_path=args.evidence,
            generated_at=args.generated_at,
            lag_slo_records=args.lag_slo_records,
            lag_slo_seconds=args.lag_slo_seconds,
            dlt_unresolved_slo=args.dlt_unresolved_slo,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "readiness_state": result.report["readiness_state"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "ingestion-runtime-evidence-normalize":
        result = write_ingestion_runtime_evidence_artifact(
            args.root,
            args.output,
            environment=args.environment,
            source_kind=args.source_kind,
            kafka_connect_status_path=args.kafka_connect_status,
            lag_metrics_path=args.lag_metrics,
            dlt_report_path=args.dlt_report,
            backpressure_report_path=args.backpressure_report,
            offset_ledgers_path=args.offset_ledgers,
            broker_checks_path=args.broker_checks,
            generated_at=args.generated_at,
            valid_until=args.valid_until,
            ci_run_id=args.ci_run_id,
            issuer_tool=args.issuer_tool,
            issuer_tool_version=args.issuer_tool_version,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "manifest": result.manifest_path.as_posix(),
                    "environment": result.evidence["environment"],
                    "source_kind": result.evidence["source_kind"],
                    "connector_count": len(result.evidence["connectors"]),
                    "p0_connector_count": result.evidence["summary"]["p0_connector_count"],
                    "evidence_id": result.evidence["evidence_id"],
                    "readiness_args": result.manifest["readiness_args"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "source-readiness-check":
        result = write_source_readiness_report(
            args.root,
            args.output,
            source_id=args.source_id,
            environment=args.environment,
            ingestion_manifest_path=args.ingestion_manifest,
            bridge_manifest_path=args.bridge_manifest,
            replay_manifest_path=args.replay_manifest,
            offset_ledger_path=args.offset_ledger,
            schema_registry_report_path=args.schema_registry_report,
            change_control_evidence_path=args.change_control_evidence,
            catalog_bundle_path=args.catalog_bundle,
            openlineage_events_path=args.openlineage_events,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "readiness_id": result.report["readiness_id"],
                    "readiness_state": result.report["readiness_state"],
                    "source_id": result.report["source_id"],
                    "environment": result.report["environment"],
                    "passed": result.report["passed"],
                    "failure_count": len(result.report["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "offset-ledger-record":
        result = write_offset_ledger_report(
            args.root,
            args.output,
            source_id=args.source_id,
            environment=args.environment,
            ingestion_manifest_path=args.ingestion_manifest,
            replay_manifest_path=args.replay_manifest,
            table_format=args.table_format,
            target_snapshot_id=args.target_snapshot_id,
            table_metadata_uri=args.table_metadata_uri,
            table_metadata_hash=args.table_metadata_hash,
            commit_status=args.commit_status,
            committed_at=args.committed_at,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "ledger_id": result.report["ledger_id"],
                    "source_id": result.report["source_id"],
                    "environment": result.report["environment"],
                    "target_table": result.report["target"]["target_table"],
                    "target_snapshot_id": result.report["target"]["target_snapshot_id"],
                    "passed": result.report["passed"],
                    "failure_count": len(result.report["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "snapshot-evidence-record":
        result = write_snapshot_evidence_report(
            args.root,
            args.output,
            environment=args.environment,
            pipeline_manifest_path=args.pipeline_manifest,
            snapshot_metadata_path=args.snapshot_metadata,
            primary_output=args.primary_output,
            source_offset_ledger_path=args.source_offset_ledger,
            release_id=args.release_id,
            use_case_id=args.use_case_id,
            runner_id=args.runner_id,
            code_commit_sha=args.code_commit_sha,
            release_evidence_profile_id=args.release_evidence_profile_id,
            release_evidence_profile_hash=args.release_evidence_profile_hash,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "evidence_id": result.report["evidence_id"],
                    "environment": result.report["environment"],
                    "primary_output": result.report["primary_output"],
                    "primary_snapshot_id": (result.report.get("primary_snapshot") or {}).get("snapshot_id"),
                    "passed": result.report["passed"],
                    "failure_count": len(result.report["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "bronze-lakehouse-ops-report":
        result = write_bronze_lakehouse_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            offset_ledger_paths=args.offset_ledger,
            maintenance_evidence_path=args.maintenance_evidence,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "readiness_state": result.report["readiness_state"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "silver-gold-publication-ops-report":
        result = write_silver_gold_publication_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            release_evidence_paths=args.release_evidence,
            promotion_manifest_paths=args.promotion_manifest,
            activation_manifest_paths=args.activation_manifest,
            active_pointer_paths=args.active_pointer,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "environment": result.report["environment"],
                    "readiness_state": result.report["readiness_state"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "access-policy-check":
        result = write_access_policy_report(
            args.root,
            args.output,
            data_product_name=args.data_product,
            environment=args.environment,
            release_id=args.release_id,
            dataset_snapshot_id=args.dataset_snapshot_id,
            table_version=args.table_version,
            content_hash=args.content_hash,
            row_count=args.row_count,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "check_id": result.report["check_id"],
                    "passed": result.report["passed"],
                    "data_product": result.report["data_product"],
                    "failure_count": len(result.report["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "access-grant-check":
        result = write_access_grant_evidence_report(
            args.root,
            args.output,
            data_product_name=args.data_product,
            environment=args.environment,
            release_id=args.release_id,
            dataset_snapshot_id=args.dataset_snapshot_id,
            table_version=args.table_version,
            content_hash=args.content_hash,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "evidence_id": result.report["evidence_id"],
                    "passed": result.report["passed"],
                    "data_product": result.report["data_product"],
                    "active_grant_count": result.report["active_grant_count"],
                    "failure_count": len(result.report["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "access-grant-ops-report":
        result = write_access_grant_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            generated_at=args.generated_at,
            expiring_within_days=args.expiring_within_days,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "report_id": result.report["report_id"],
                    "environment": result.report["environment"],
                    "passed": result.report["passed"],
                    "summary": result.report["summary"],
                    "page_now": result.report["decision_board"]["page_now"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "change-control-check":
        result = write_change_control_evidence_report(
            args.root,
            args.output,
            request_id=args.request_id,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "evidence_id": result.report["evidence_id"],
                    "passed": result.report["passed"],
                    "environment": result.report["environment"],
                    "request_id": result.report["request_id"],
                    "request_count": result.report["summary"]["request_count"],
                    "failed_count": result.report["summary"]["failed_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "backfill-readiness-check":
        result = write_backfill_readiness_report(
            args.root,
            args.output,
            request_id=args.request_id,
            environment=args.environment,
            dry_run_report_path=args.dry_run_report,
            quality_report_path=args.quality_report,
            data_diff_report_path=args.data_diff_report,
            source_offset_ledger_path=args.source_offset_ledger,
            snapshot_evidence_path=args.snapshot_evidence,
            release_evidence_path=args.release_evidence,
            change_control_evidence_path=args.change_control_evidence,
            backfill_plan_path=args.backfill_plan,
            active_state_path=args.active_state,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "readiness_id": result.report["readiness_id"],
                    "readiness_state": result.report["readiness_state"],
                    "request_id": result.report["request_id"],
                    "environment": result.report["environment"],
                    "passed": result.report["passed"],
                    "failure_count": len(result.report["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "retention-check":
        result = write_retention_evidence_report(
            args.root,
            args.output,
            data_product_name=args.data_product,
            environment=args.environment,
            release_id=args.release_id,
            dataset_snapshot_id=args.dataset_snapshot_id,
            table_version=args.table_version,
            content_hash=args.content_hash,
            row_count=args.row_count,
            generated_at=args.generated_at,
            evidence_input_path=args.evidence_input,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "evidence_id": result.report["evidence_id"],
                    "passed": result.report["passed"],
                    "data_product": result.report["data_product"],
                    "policy_id": result.report["policy"]["policy_id"],
                    "failure_count": len(result.report["failures"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "pipeline-list":
        specs = [
            spec.as_dict()
            for spec in default_pipeline_registry().list_specs(
                product=args.product,
                domain=args.domain,
                use_case=args.use_case,
                output_data_product=args.output_data_product,
            )
        ]
        if args.format == "text":
            for spec in specs:
                print(f"{spec['runner_id']}\t{spec['product']}\t{spec['domain']}\t{spec['input_kind']}")
        else:
            print(json.dumps({"pipelines": specs}, ensure_ascii=True, sort_keys=True))
        return 0
    if args.command == "pipeline-describe":
        spec = default_pipeline_registry().get(args.runner_id).spec.as_dict()
        print(json.dumps(spec, ensure_ascii=True, sort_keys=True))
        return 0
    if args.command == "run-pipeline":
        options = {
            "upstream_manifest_path": args.upstream_manifest,
            "enrollment_bronze_path": args.enrollment_bronze,
            "snapshot_id": args.snapshot_id,
            "built_at": args.built_at,
            "ingested_at": args.ingested_at,
        }
        result = default_pipeline_registry().run(
            args.runner_id,
            PipelineRunRequest(
                input_path=Path(args.input),
                output_dir=Path(args.output_dir),
                options={key: value for key, value in options.items() if value is not None},
            ),
        )
        print_pipeline_result(args.runner_id, result)
        return 0 if result.manifest["quality_passed"] else 1
    if args.command == "run-use-case":
        result = run_use_case(
            args.root,
            args.input,
            args.output_dir,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            runner_id=args.runner_id,
            topic=args.topic,
            primary_output=args.primary_output,
            environment=args.environment,
            ingested_at=args.ingested_at,
            built_at=args.built_at,
            evaluation_time=args.evaluation_time,
            schema_id=args.schema_id,
            snapshot_id=args.snapshot_id,
            code_commit_sha=args.code_commit_sha,
            schema_registry_report_uri=args.schema_registry_report_uri,
            schema_registry_report_hash=args.schema_registry_report_hash,
            validator_output_uri=args.validator_output_uri,
            access_policy_check_id=args.access_policy_check_id,
            access_policy_report_uri=args.access_policy_report_uri,
            access_policy_report_hash=args.access_policy_report_hash,
            access_grant_evidence_uri=args.access_grant_evidence_uri,
            access_grant_evidence_hash=args.access_grant_evidence_hash,
            retention_evidence_uri=args.retention_evidence_uri,
            retention_evidence_hash=args.retention_evidence_hash,
            retention_evidence_input_path=args.retention_evidence_input,
            snapshot_evidence_uri=args.snapshot_evidence_uri,
            snapshot_evidence_hash=args.snapshot_evidence_hash,
            approver=args.approver,
        )
        print(
            json.dumps(
                {
                    "release_id": result.release_id,
                    "use_case_id": result.use_case_id,
                    "runner_id": result.runner_id,
                    "topic": result.topic,
                    "primary_output": result.primary_output,
                    "release_passed": result.evidence["release_passed"],
                    "ingestion_manifest_path": result.ingestion.manifest_path.as_posix() if result.ingestion else None,
                    "pipeline_manifest_path": result.pipeline.manifest_path.as_posix(),
                    "catalog_bundle_path": result.catalog_bundle_path.as_posix(),
                    "evidence_path": result.evidence_path.as_posix(),
                    "gates": {
                        gate["gate_id"]: gate["passed"]
                        for gate in result.evidence["gates"]
                    },
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.evidence["release_passed"] else 1
    if args.command == "data-plane-smoke":
        result = write_data_plane_smoke_report(
            args.root,
            args.output,
            input_path=args.input,
            output_dir=args.output_dir,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            runner_id=args.runner_id,
            topic=args.topic,
            primary_output=args.primary_output,
            environment=args.environment,
            generated_at=args.generated_at,
            ingested_at=args.ingested_at,
            built_at=args.built_at,
            evaluation_time=args.evaluation_time,
            schema_id=args.schema_id,
            snapshot_id=args.snapshot_id,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "release_id": result.report["release_id"],
                    "use_case_id": result.report["use_case_id"],
                    "primary_output": result.report["primary_output"],
                    "query_name": result.report["query_smoke"].get("query_name"),
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                    "layers": {
                        layer["name"]: layer["passed"]
                        for layer in result.report["layers"]
                    },
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "live-lakehouse-smoke":
        result = write_live_lakehouse_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            input_path=args.input,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            ingested_at=args.ingested_at,
            built_at=args.built_at,
            evaluation_time=args.evaluation_time,
            schema_id=args.schema_id,
            snapshot_id=args.snapshot_id,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "use_case_id": result.report["use_case_id"],
                    "primary_output": result.report["primary_output"],
                    "runtime_mode": result.report["runtime_scope"]["mode"],
                    "table_count": result.report["summary"]["table_count"],
                    "query_engine": result.report["summary"]["query_engine"],
                    "query_passed": result.report["summary"]["query_passed"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "object-store-commit-smoke":
        result = write_object_store_commit_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            live_lakehouse_smoke_report_path=args.live_lakehouse_smoke_report,
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            access_key=args.access_key,
            secret_key=args.secret_key,
            region_name=args.region_name,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "use_case_id": result.report["use_case_id"],
                    "bucket": result.report["object_store"]["bucket"],
                    "object_count": result.report["summary"]["object_count"],
                    "uploaded_object_count": result.report["summary"]["uploaded_object_count"],
                    "readback_passed_count": result.report["summary"]["readback_passed_count"],
                    "encrypted_object_count": result.report["summary"]["encrypted_object_count"],
                    "encryption_policy_enforced": result.report["summary"]["encryption_policy_enforced"],
                    "unencrypted_put_denied": result.report["summary"]["unencrypted_put_denied"],
                    "encrypted_put_allowed": result.report["summary"]["encrypted_put_allowed"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "trino-sql-runtime-smoke":
        result = write_trino_sql_runtime_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            live_lakehouse_smoke_report_path=args.live_lakehouse_smoke_report,
            compose_file=args.compose_file,
            service=args.service,
            schema=args.schema,
            table=args.table,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "use_case_id": result.report["use_case_id"],
                    "query_engine": result.report["summary"]["query_engine"],
                    "query_mode": result.report["summary"]["query_mode"],
                    "row_count": result.report["summary"]["row_count"],
                    "query_passed": result.report["summary"]["query_passed"],
                    "result_row_count": result.report["summary"]["result_row_count"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "trino-iceberg-minio-smoke":
        result = write_trino_iceberg_minio_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            live_lakehouse_smoke_report_path=args.live_lakehouse_smoke_report,
            compose_file=args.compose_file,
            service=args.service,
            postgres_service=args.postgres_service,
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            access_key=args.access_key,
            secret_key=args.secret_key,
            region_name=args.region_name,
            catalog=args.catalog,
            schema=args.schema,
            table=args.table,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "use_case_id": result.report["use_case_id"],
                    "catalog": result.report["trino"]["catalog"],
                    "query_mode": result.report["summary"]["query_mode"],
                    "row_count": result.report["summary"]["row_count"],
                    "query_passed": result.report["summary"]["query_passed"],
                    "snapshot_count": result.report["summary"]["snapshot_count"],
                    "iceberg_file_count": result.report["summary"]["iceberg_file_count"],
                    "minio_object_count": result.report["summary"]["minio_object_count"],
                    "minio_encrypted_object_count": result.report["summary"]["minio_encrypted_object_count"],
                    "object_store_encryption_policy_enforced": result.report["summary"][
                        "object_store_encryption_policy_enforced"
                    ],
                    "trino_iceberg_objects_encrypted": result.report["summary"]["trino_iceberg_objects_encrypted"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "catalog-cross-engine-smoke":
        result = write_catalog_compatibility_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            trino_iceberg_minio_smoke_report_path=args.trino_iceberg_minio_smoke_report,
            compose_file=args.compose_file,
            service=args.service,
            postgres_service=args.postgres_service,
            minio_service=args.minio_service,
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            access_key=args.access_key,
            secret_key=args.secret_key,
            region_name=args.region_name,
            catalog=args.catalog,
            catalog_name=args.catalog_name,
            schema=args.schema,
            cross_engine_table=args.cross_engine_table,
            concurrency_table=args.concurrency_table,
            catalog_uri=args.catalog_uri,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "catalog": result.report["summary"]["catalog"],
                    "catalog_backend": result.report["summary"]["catalog_backend"],
                    "cross_engine_commit_compatibility_passed": result.report["summary"][
                        "cross_engine_commit_compatibility_passed"
                    ],
                    "catalog_concurrency_locking_passed": result.report["summary"][
                        "catalog_concurrency_locking_passed"
                    ],
                    "stale_commit_rejected": result.report["summary"]["stale_commit_rejected"],
                    "trino_initial_row_count": result.report["summary"]["trino_initial_row_count"],
                    "pyiceberg_readback_row_count": result.report["summary"]["pyiceberg_readback_row_count"],
                    "snapshot_count_after_pyiceberg": result.report["summary"]["snapshot_count_after_pyiceberg"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "trino-runtime-security-smoke":
        result = write_trino_runtime_security_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            trino_iceberg_minio_smoke_report_path=args.trino_iceberg_minio_smoke_report,
            compose_file=args.compose_file,
            service=args.service,
            postgres_service=args.postgres_service,
            catalog=args.catalog,
            schema=args.schema,
            table=args.table,
            security_probe_table=args.security_probe_table,
            allowed_user=args.allowed_user,
            denied_user=args.denied_user,
            unknown_user=args.unknown_user,
            row_filter_user=args.row_filter_user,
            masked_user=args.masked_user,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "use_case_id": result.report["use_case_id"],
                    "query_mode": result.report["summary"]["query_mode"],
                    "source_row_count": result.report["summary"]["source_row_count"],
                    "allowed_user": result.report["summary"]["allowed_user"],
                    "allowed_query_passed": result.report["summary"]["allowed_query_passed"],
                    "allowed_write_blocked": result.report["summary"]["allowed_write_blocked"],
                    "denied_user": result.report["summary"]["denied_user"],
                    "denied_query_blocked": result.report["summary"]["denied_query_blocked"],
                    "unknown_user": result.report["summary"]["unknown_user"],
                    "unknown_user_blocked": result.report["summary"]["unknown_user_blocked"],
                    "row_filter_user": result.report["summary"]["row_filter_user"],
                    "row_level_filter_enforced": result.report["summary"]["row_level_filter_enforced"],
                    "masked_user": result.report["summary"]["masked_user"],
                    "column_masking_enforced": result.report["summary"]["column_masking_enforced"],
                    "centralized_audit_sink_passed": result.report["summary"]["centralized_audit_sink_passed"],
                    "runtime_security_audit_event_count": result.report["summary"]["runtime_security_audit_event_count"],
                    "access_denied_verified": result.report["summary"]["access_denied_verified"],
                    "all_access_denied_errors_verified": result.report["summary"]["all_access_denied_errors_verified"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "policy-decision-smoke":
        result = write_policy_decision_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            opa_image=args.opa_image,
            container_name=args.container_name,
            port=args.port,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
            cleanup_runtime=not args.no_cleanup_runtime,
            pdp_url=args.pdp_url,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "pdp": result.report["summary"]["pdp"],
                    "decision_api_reachable": result.report["summary"]["decision_api_reachable"],
                    "finance_reader_allowed": result.report["summary"]["finance_reader_allowed"],
                    "unauthorized_default_denied": result.report["summary"]["unauthorized_default_denied"],
                    "row_filter_decision_present": result.report["summary"]["row_filter_decision_present"],
                    "column_mask_decision_present": result.report["summary"]["column_mask_decision_present"],
                    "policy_admin_approval_passed": result.report["summary"]["policy_admin_approval_passed"],
                    "policy_admin_self_approval_denied": result.report["summary"][
                        "policy_admin_self_approval_denied"
                    ],
                    "policy_admin_missing_evidence_denied": result.report["summary"][
                        "policy_admin_missing_evidence_denied"
                    ],
                    "audit_sink_passed": result.report["summary"]["audit_sink_passed"],
                    "audit_event_count": result.report["summary"]["audit_event_count"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "oidc-auth-smoke":
        result = write_oidc_auth_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            issuer=args.issuer,
            audience=args.audience,
            required_role=args.required_role,
            key_id=args.key_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "issuer": result.report["summary"]["issuer"],
                    "audience": result.report["summary"]["audience"],
                    "jwks_key_published": result.report["summary"]["jwks_key_published"],
                    "rs256_signature_validation_passed": result.report["summary"][
                        "rs256_signature_validation_passed"
                    ],
                    "issuer_validation_passed": result.report["summary"]["issuer_validation_passed"],
                    "audience_validation_passed": result.report["summary"]["audience_validation_passed"],
                    "expiry_validation_passed": result.report["summary"]["expiry_validation_passed"],
                    "required_role_denied": result.report["summary"]["required_role_denied"],
                    "unknown_kid_denied": result.report["summary"]["unknown_kid_denied"],
                    "missing_token_denied": result.report["summary"]["missing_token_denied"],
                    "audit_sink_passed": result.report["summary"]["audit_sink_passed"],
                    "raw_access_tokens_persisted": result.report["summary"]["raw_access_tokens_persisted"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "secret-rotation-smoke":
        result = write_secret_rotation_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "secret_manager_mode": result.report["summary"]["secret_manager_mode"],
                    "service_identity_count": result.report["summary"]["service_identity_count"],
                    "rotated_secret_count": result.report["summary"]["rotated_secret_count"],
                    "active_version_advanced": result.report["summary"]["active_version_advanced"],
                    "old_versions_revoked": result.report["summary"]["old_versions_revoked"],
                    "new_versions_readable": result.report["summary"]["new_versions_readable"],
                    "unauthorized_identity_denied": result.report["summary"]["unauthorized_identity_denied"],
                    "missing_secret_denied": result.report["summary"]["missing_secret_denied"],
                    "orchestrator_secret_injection_passed": result.report["summary"][
                        "orchestrator_secret_injection_passed"
                    ],
                    "orchestrator_injection_manifest_redacted": result.report["summary"][
                        "orchestrator_injection_manifest_redacted"
                    ],
                    "plaintext_secret_material_persisted": result.report["summary"][
                        "plaintext_secret_material_persisted"
                    ],
                    "audit_sink_passed": result.report["summary"]["audit_sink_passed"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "secret-rotation-ops-report":
        result = write_secret_rotation_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            evidence_path=args.evidence,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "environment": result.report["environment"],
                    "mode": result.report["mode"],
                    "readiness_state": result.report["readiness_state"],
                    "p0_service_count": result.report["summary"]["p0_service_count"],
                    "covered_service_count": result.report["summary"]["covered_service_count"],
                    "failed_service_count": result.report["summary"]["failed_service_count"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "catalog-runtime-ops-report":
        result = write_catalog_runtime_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            evidence_path=args.evidence,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "environment": result.report["environment"],
                    "mode": result.report["mode"],
                    "readiness_state": result.report["readiness_state"],
                    "replica_count": result.report["summary"]["replica_count"],
                    "availability_zones": result.report["summary"]["availability_zones"],
                    "failover_passed": result.report["summary"]["failover_passed"],
                    "stale_commit_rejected": result.report["summary"]["stale_commit_rejected"],
                    "backup_enabled": result.report["summary"]["backup_enabled"],
                    "pitr_enabled": result.report["summary"]["pitr_enabled"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "orchestration-runtime-ops-report":
        result = write_orchestration_runtime_ops_report(
            args.root,
            args.output,
            environment=args.environment,
            evidence_path=args.evidence,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "environment": result.report["environment"],
                    "mode": result.report["mode"],
                    "readiness_state": result.report["readiness_state"],
                    "replica_count": result.report["summary"]["replica_count"],
                    "availability_zones": result.report["summary"]["availability_zones"],
                    "distributed_executor_enabled": result.report["summary"]["distributed_executor_enabled"],
                    "kubernetes_run_launcher_enabled": result.report["summary"]["kubernetes_run_launcher_enabled"],
                    "managed_run_storage": result.report["summary"]["managed_run_storage"],
                    "schedule_tick_history_passed": result.report["summary"]["schedule_tick_history_passed"],
                    "backfill_materialization_history_passed": result.report["summary"][
                        "backfill_materialization_history_passed"
                    ],
                    "secret_injection_verified": result.report["summary"]["secret_injection_verified"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "iceberg-catalog-smoke":
        result = write_iceberg_catalog_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            live_lakehouse_smoke_report_path=args.live_lakehouse_smoke_report,
            catalog_name=args.catalog_name,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "use_case_id": result.report["use_case_id"],
                    "catalog_type": result.report["iceberg"]["catalog_type"],
                    "table_count": result.report["summary"]["table_count"],
                    "snapshot_commit_count": result.report["summary"]["snapshot_commit_count"],
                    "readback_passed_count": result.report["summary"]["readback_passed_count"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "dagster-orchestration-smoke":
        result = write_dagster_orchestration_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            live_lakehouse_smoke_report_path=args.live_lakehouse_smoke_report,
            object_store_smoke_report_path=args.object_store_smoke_report,
            trino_sql_smoke_report_path=args.trino_sql_smoke_report,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "use_case_id": result.report["use_case_id"],
                    "job_name": result.report["summary"]["job_name"],
                    "run_id": result.report["summary"]["run_id"],
                    "run_status": result.report["summary"]["run_status"],
                    "event_count": result.report["summary"]["event_count"],
                    "op_success_count": result.report["summary"]["op_success_count"],
                    "validated_report_count": result.report["summary"]["validated_report_count"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "event-backbone-smoke":
        result = write_event_backbone_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            input_path=args.input,
            compose_file=args.compose_file,
            service=args.service,
            topic=args.topic,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            ingested_at=args.ingested_at,
            built_at=args.built_at,
            evaluation_time=args.evaluation_time,
            schema_id=args.schema_id,
            snapshot_id=args.snapshot_id,
            schema_registry_runtime_report_path=args.schema_registry_runtime_smoke_report,
            command_timeout_seconds=args.command_timeout_seconds,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "topic": result.report["topic"],
                    "source_record_count": result.report["summary"]["source_record_count"],
                    "consumed_record_count": result.report["summary"]["consumed_record_count"],
                    "data_plane_smoke_passed": result.report["summary"]["data_plane_smoke_passed"],
                    "sink_schema_validation_passed": result.report["summary"]["sink_schema_validation_passed"],
                    "sink_schema_validated_source_count": result.report["summary"]["sink_schema_validated_source_count"],
                    "producer_schema_id_guard_passed": result.report["summary"]["producer_schema_id_guard_passed"],
                    "producer_schema_id_guarded_source_count": result.report["summary"]["producer_schema_id_guarded_source_count"],
                    "multi_partition_rebalance_passed": result.report["summary"]["multi_partition_rebalance_passed"],
                    "multi_partition_topic_partition_count": result.report["summary"]["multi_partition_topic_partition_count"],
                    "multi_partition_group_total_lag": result.report["summary"]["multi_partition_group_total_lag"],
                    "ingestion_runtime_report_passed": result.report["summary"]["ingestion_runtime_report_passed"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "broker-acl-smoke":
        result = write_broker_acl_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            image=args.image,
            container_name=args.container_name,
            topic=args.topic,
            group=args.group,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            start_runtime=not args.no_start_runtime,
            cleanup_runtime=not args.no_cleanup_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "topic": result.report["redpanda"]["topic"],
                    "group": result.report["redpanda"]["group"],
                    "broker_acl_enforced": result.report["summary"]["broker_acl_enforced"],
                    "allowed_user_can_produce": result.report["summary"]["allowed_user_can_produce"],
                    "denied_user_blocked": result.report["summary"]["denied_user_blocked"],
                    "authorization_denied_verified": result.report["summary"]["authorization_denied_verified"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "transactional-outbox-smoke":
        result = write_transactional_outbox_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            compose_file=args.compose_file,
            postgres_service=args.postgres_service,
            redpanda_service=args.redpanda_service,
            source_id=args.source_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            ingested_at=args.ingested_at,
            schema_id=args.schema_id,
            command_timeout_seconds=args.command_timeout_seconds,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "source_id": result.report["source"]["source_id"],
                    "topic": result.report["source"]["topic"],
                    "bronze_target": result.report["source"]["bronze_target"],
                    "outbox_row_count": result.report["summary"]["outbox_row_count"],
                    "connector_record_count": result.report["summary"]["connector_record_count"],
                    "consumed_record_count": result.report["summary"]["consumed_record_count"],
                    "bronze_approved_new_row_count": result.report["summary"]["bronze_approved_new_row_count"],
                    "bronze_quarantine_row_count": result.report["summary"]["bronze_quarantine_row_count"],
                    "transactional_outbox_to_bronze_passed": result.report["summary"][
                        "transactional_outbox_to_bronze_passed"
                    ],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "live-bronze-ingestion-smoke":
        result = write_live_bronze_ingestion_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            compose_file=args.compose_file,
            source_postgres_service=args.source_postgres_service,
            redpanda_service=args.redpanda_service,
            trino_service=args.trino_service,
            iceberg_postgres_service=args.iceberg_postgres_service,
            minio_service=args.minio_service,
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            access_key=args.access_key,
            secret_key=args.secret_key,
            region_name=args.region_name,
            catalog=args.catalog,
            catalog_name=args.catalog_name,
            catalog_uri=args.catalog_uri,
            schema=args.schema,
            table=args.table,
            source_id=args.source_id,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            ingested_at=args.ingested_at,
            schema_id=args.schema_id,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "source_id": result.report["summary"]["source_id"],
                    "runtime_topic": result.report["summary"]["runtime_topic"],
                    "bronze_target": result.report["summary"]["bronze_target"],
                    "iceberg_table": result.report["summary"]["iceberg_table"],
                    "source_record_count": result.report["summary"]["source_record_count"],
                    "consumed_record_count": result.report["summary"]["consumed_record_count"],
                    "approved_row_count": result.report["summary"]["approved_row_count"],
                    "duplicate_skipped_count": result.report["summary"]["duplicate_skipped_count"],
                    "quarantine_row_count": result.report["summary"]["quarantine_row_count"],
                    "trino_row_count": result.report["summary"]["trino_row_count"],
                    "snapshot_count_after": result.report["summary"]["snapshot_count_after"],
                    "restart_resume_passed": result.report["summary"]["restart_resume_passed"],
                    "dlt_quarantine_passed": result.report["summary"]["dlt_quarantine_passed"],
                    "live_bronze_iceberg_sink_passed": result.report["summary"]["live_bronze_iceberg_sink_passed"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "orchestrated-publication-smoke":
        result = write_orchestrated_publication_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            live_bronze_ingestion_smoke_report_path=args.live_bronze_ingestion_smoke_report,
            compose_file=args.compose_file,
            trino_service=args.trino_service,
            iceberg_postgres_service=args.iceberg_postgres_service,
            minio_service=args.minio_service,
            bucket=args.bucket,
            endpoint_url=args.endpoint_url,
            access_key=args.access_key,
            secret_key=args.secret_key,
            region_name=args.region_name,
            catalog=args.catalog,
            catalog_name=args.catalog_name,
            catalog_uri=args.catalog_uri,
            bronze_schema=args.bronze_schema,
            bronze_table=args.bronze_table,
            publication_schema=args.publication_schema,
            silver_table=args.silver_table,
            gold_table=args.gold_table,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "bronze_row_count": result.report["summary"]["bronze_row_count"],
                    "silver_row_count": result.report["summary"]["silver_row_count"],
                    "gold_row_count": result.report["summary"]["gold_row_count"],
                    "trino_silver_row_count": result.report["summary"]["trino_silver_row_count"],
                    "trino_gold_row_count": result.report["summary"]["trino_gold_row_count"],
                    "promotion_passed": result.report["summary"]["promotion_passed"],
                    "activation_passed": result.report["summary"]["activation_passed"],
                    "publication_ops_passed": result.report["summary"]["publication_ops_passed"],
                    "active_pointer_drift_negative_test_passed": result.report["summary"][
                        "active_pointer_drift_negative_test_passed"
                    ],
                    "dagster_retry_event_count": result.report["summary"]["dagster_retry_event_count"],
                    "asset_materialization_count": result.report["summary"]["asset_materialization_count"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "live-quality-slo-smoke":
        result = write_live_quality_slo_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            orchestrated_publication_smoke_report_path=args.orchestrated_publication_smoke_report,
            compose_file=args.compose_file,
            trino_service=args.trino_service,
            iceberg_postgres_service=args.iceberg_postgres_service,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
            data_product=args.data_product,
            freshness_slo_seconds=args.freshness_slo_seconds,
            command_timeout_seconds=args.command_timeout_seconds,
            wait_attempts=args.wait_attempts,
            start_runtime=not args.no_start_runtime,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "target_data_product": result.report["summary"]["target_data_product"],
                    "gold_row_count": result.report["summary"]["gold_row_count"],
                    "quality_runtime_passed": result.report["summary"]["quality_runtime_passed"],
                    "slo_alert_passed": result.report["summary"]["slo_alert_passed"],
                    "quality_slo_ops_passed": result.report["summary"]["quality_slo_ops_passed"],
                    "corrupt_gold_null_negative_test_passed": result.report["summary"][
                        "corrupt_gold_null_negative_test_passed"
                    ],
                    "stale_freshness_negative_test_passed": result.report["summary"][
                        "stale_freshness_negative_test_passed"
                    ],
                    "red_alert_negative_test_passed": result.report["summary"]["red_alert_negative_test_passed"],
                    "environment_mismatch_negative_test_passed": result.report["summary"][
                        "environment_mismatch_negative_test_passed"
                    ],
                    "missing_alert_production_like_negative_test_passed": result.report["summary"][
                        "missing_alert_production_like_negative_test_passed"
                    ],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "portfolio-release-smoke":
        result = write_portfolio_release_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "release_evidence_count": result.report["summary"]["release_evidence_count"],
                    "passed_release_count": result.report["summary"]["passed_release_count"],
                    "source_bridge_preflight_count": result.report["summary"]["source_bridge_preflight_count"],
                    "source_bridge_preflight_passed_count": result.report["summary"]["source_bridge_preflight_passed_count"],
                    "source_bridge_bronze_ingestion_passed_count": result.report["summary"]["source_bridge_bronze_ingestion_passed_count"],
                    "source_activation_count": result.report["summary"]["source_activation_count"],
                    "source_activation_passed_count": result.report["summary"]["source_activation_passed_count"],
                    "source_activation_ops_passed": result.report["summary"]["source_activation_ops_passed"],
                    "covered_gold_count": result.report["summary"]["covered_gold_count"],
                    "gold_count": result.report["summary"]["gold_count"],
                    "missing_gold_outputs": result.report["summary"]["missing_gold_outputs"],
                    "final_control_tower_blocker_count": result.report["summary"]["final_control_tower_blocker_count"],
                    "final_gold_release_blocker_count": result.report["summary"]["final_gold_release_blocker_count"],
                    "final_runtime_lineage_blocker_count": result.report["summary"]["final_runtime_lineage_blocker_count"],
                    "final_source_activation_blocker_count": result.report["summary"]["final_source_activation_blocker_count"],
                    "final_contract_active_blocker_count": result.report["summary"]["final_contract_active_blocker_count"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "dagster-day2-smoke":
        result = write_dagster_day2_smoke_report(
            args.root,
            args.output,
            output_dir=args.output_dir,
            release_id=args.release_id,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "output": result.output_path.as_posix(),
                    "passed": result.report["passed"],
                    "run_id": result.report["summary"]["run_id"],
                    "run_status": result.report["summary"]["run_status"],
                    "schedule_tick_count": result.report["summary"]["schedule_tick_count"],
                    "schedule_tick_history_passed": result.report["summary"]["schedule_tick_history_passed"],
                    "retry_event_count": result.report["summary"]["retry_event_count"],
                    "retry_restart_count": result.report["summary"]["retry_restart_count"],
                    "retry_policy_verified": result.report["summary"]["retry_policy_verified"],
                    "backfill_partition_count": result.report["summary"]["backfill_partition_count"],
                    "asset_materialization_event_count": result.report["summary"][
                        "asset_materialization_event_count"
                    ],
                    "backfill_materialization_history_passed": result.report["summary"][
                        "backfill_materialization_history_passed"
                    ],
                    "distributed_executor_verified": result.report["summary"]["distributed_executor_verified"],
                    "failed_check_count": result.report["summary"]["failed_check_count"],
                    "failed_checks": result.report["summary"]["failed_checks"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "production-review-pack":
        result = write_production_review_pack(
            args.root,
            args.output_dir,
            environment=args.environment,
            generated_at=args.generated_at,
            use_case_id=args.use_case_id,
            release_id=args.release_id,
            smoke_generated_at=args.smoke_generated_at,
            ingested_at=args.ingested_at,
            built_at=args.built_at,
            evaluation_time=args.evaluation_time,
            schema_id=args.schema_id,
            snapshot_id=args.snapshot_id,
            event_backbone_smoke_report_path=args.event_backbone_smoke_report,
            ingestion_runtime_report_path=args.ingestion_runtime_report,
            catalog_lineage_ops_report_path=args.catalog_lineage_ops_report,
            semantic_metric_serving_ops_report_path=args.semantic_metric_serving_ops_report,
            source_activation_ops_report_path=args.source_activation_ops_report,
            backfill_readiness_report_path=args.backfill_readiness_report,
            runtime_readiness_report_path=args.runtime_readiness_report,
            runtime_iac_plan_path=args.runtime_iac_plan,
            runtime_iac_apply_path=args.runtime_iac_apply,
            runtime_drift_report_path=args.runtime_drift_report,
            runtime_backup_report_path=args.runtime_backup_report,
            runtime_dr_report_path=args.runtime_dr_report,
            runtime_health_report_path=args.runtime_health_report,
            workload_benchmark_report_path=args.workload_benchmark_report,
            schema_registry_runtime_smoke_report_path=args.schema_registry_runtime_smoke_report,
            schema_registry_attestation_report_path=args.schema_registry_attestation_report,
            schema_registry_ops_report_path=args.schema_registry_ops_report,
            schema_registry_auth_smoke_report_path=args.schema_registry_auth_smoke_report,
            schema_registry_storage_smoke_report_path=args.schema_registry_storage_smoke_report,
            live_lakehouse_smoke_report_path=args.live_lakehouse_smoke_report,
            iceberg_catalog_smoke_report_path=args.iceberg_catalog_smoke_report,
            object_store_smoke_report_path=args.object_store_smoke_report,
            trino_sql_smoke_report_path=args.trino_sql_smoke_report,
            trino_iceberg_minio_smoke_report_path=args.trino_iceberg_minio_smoke_report,
            catalog_cross_engine_smoke_report_path=args.catalog_cross_engine_smoke_report,
            catalog_runtime_ops_report_path=args.catalog_runtime_ops_report,
            orchestration_runtime_ops_report_path=args.orchestration_runtime_ops_report,
            trino_runtime_security_smoke_report_path=args.trino_runtime_security_smoke_report,
            policy_decision_smoke_report_path=args.policy_decision_smoke_report,
            oidc_auth_smoke_report_path=args.oidc_auth_smoke_report,
            secret_rotation_smoke_report_path=args.secret_rotation_smoke_report,
            secret_rotation_ops_report_path=args.secret_rotation_ops_report,
            broker_acl_smoke_report_path=args.broker_acl_smoke_report,
            transactional_outbox_smoke_report_path=args.transactional_outbox_smoke_report,
            live_bronze_ingestion_smoke_report_path=args.live_bronze_ingestion_smoke_report,
            orchestrated_publication_smoke_report_path=args.orchestrated_publication_smoke_report,
            live_quality_slo_smoke_report_path=args.live_quality_slo_smoke_report,
            dagster_orchestration_smoke_report_path=args.dagster_orchestration_smoke_report,
            dagster_day2_smoke_report_path=args.dagster_day2_smoke_report,
            portfolio_release_smoke_report_path=args.portfolio_release_smoke_report,
        )
        print(
            json.dumps(
                {
                    "output": result.manifest_path.as_posix(),
                    "partner_review_ready": result.manifest["verdict"]["partner_review_ready"],
                    "production_ready": result.manifest["verdict"]["production_ready"],
                    "readiness_state": result.manifest["verdict"]["readiness_state"],
                    "control_tower_blocker_count": result.manifest["summary"]["control_tower_blocker_count"],
                    "data_plane_smoke_passed": result.manifest["summary"]["data_plane_smoke_passed"],
                    "data_plane_smoke_blocker_count": result.manifest["summary"]["data_plane_smoke_blocker_count"],
                    "event_backbone_smoke_attached": result.manifest["summary"]["event_backbone_smoke_attached"],
                    "event_backbone_smoke_passed": result.manifest["summary"]["event_backbone_smoke_passed"],
                    "ingestion_runtime_attached": result.manifest["summary"]["ingestion_runtime_attached"],
                    "ingestion_runtime_passed": result.manifest["summary"]["ingestion_runtime_passed"],
                    "catalog_lineage_ops_attached": result.manifest["summary"]["catalog_lineage_ops_attached"],
                    "catalog_lineage_ops_passed": result.manifest["summary"]["catalog_lineage_ops_passed"],
                    "catalog_lineage_release_gate_passed": result.manifest["summary"][
                        "catalog_lineage_release_gate_passed"
                    ],
                    "semantic_metric_serving_ops_attached": result.manifest["summary"][
                        "semantic_metric_serving_ops_attached"
                    ],
                    "semantic_metric_serving_ops_passed": result.manifest["summary"][
                        "semantic_metric_serving_ops_passed"
                    ],
                    "semantic_metric_serving_release_gate_passed": result.manifest["summary"][
                        "semantic_metric_serving_release_gate_passed"
                    ],
                    "source_activation_ops_attached": result.manifest["summary"]["source_activation_ops_attached"],
                    "source_activation_ops_passed": result.manifest["summary"]["source_activation_ops_passed"],
                    "source_onboarding_release_gate_passed": result.manifest["summary"][
                        "source_onboarding_release_gate_passed"
                    ],
                    "backfill_readiness_attached": result.manifest["summary"]["backfill_readiness_attached"],
                    "backfill_readiness_passed": result.manifest["summary"]["backfill_readiness_passed"],
                    "backfill_change_governance_release_gate_passed": result.manifest["summary"][
                        "backfill_change_governance_release_gate_passed"
                    ],
                    "runtime_readiness_external_attached": result.manifest["summary"][
                        "runtime_readiness_external_attached"
                    ],
                    "runtime_iac_release_gate_passed": result.manifest["summary"]["runtime_iac_release_gate_passed"],
                    "schema_registry_runtime_smoke_attached": result.manifest["summary"]["schema_registry_runtime_smoke_attached"],
                    "schema_registry_runtime_smoke_passed": result.manifest["summary"]["schema_registry_runtime_smoke_passed"],
                    "schema_registry_attestation_attached": result.manifest["summary"]["schema_registry_attestation_attached"],
                    "schema_registry_attestation_passed": result.manifest["summary"]["schema_registry_attestation_passed"],
                    "schema_registry_ops_attached": result.manifest["summary"]["schema_registry_ops_attached"],
                    "schema_registry_ops_passed": result.manifest["summary"]["schema_registry_ops_passed"],
                    "schema_registry_release_gate_passed": result.manifest["summary"][
                        "schema_registry_release_gate_passed"
                    ],
                    "schema_registry_auth_smoke_attached": result.manifest["summary"]["schema_registry_auth_smoke_attached"],
                    "schema_registry_auth_smoke_passed": result.manifest["summary"]["schema_registry_auth_smoke_passed"],
                    "schema_registry_storage_smoke_attached": result.manifest["summary"][
                        "schema_registry_storage_smoke_attached"
                    ],
                    "schema_registry_storage_smoke_passed": result.manifest["summary"][
                        "schema_registry_storage_smoke_passed"
                    ],
                    "broker_acl_smoke_attached": result.manifest["summary"]["broker_acl_smoke_attached"],
                    "broker_acl_smoke_passed": result.manifest["summary"]["broker_acl_smoke_passed"],
                    "transactional_outbox_smoke_attached": result.manifest["summary"][
                        "transactional_outbox_smoke_attached"
                    ],
                    "transactional_outbox_smoke_passed": result.manifest["summary"]["transactional_outbox_smoke_passed"],
                    "live_bronze_ingestion_smoke_attached": result.manifest["summary"][
                        "live_bronze_ingestion_smoke_attached"
                    ],
                    "live_bronze_ingestion_smoke_passed": result.manifest["summary"][
                        "live_bronze_ingestion_smoke_passed"
                    ],
                    "orchestrated_publication_smoke_attached": result.manifest["summary"][
                        "orchestrated_publication_smoke_attached"
                    ],
                    "orchestrated_publication_smoke_passed": result.manifest["summary"][
                        "orchestrated_publication_smoke_passed"
                    ],
                    "live_quality_slo_smoke_attached": result.manifest["summary"][
                        "live_quality_slo_smoke_attached"
                    ],
                    "live_quality_slo_smoke_passed": result.manifest["summary"]["live_quality_slo_smoke_passed"],
                    "live_lakehouse_smoke_attached": result.manifest["summary"]["live_lakehouse_smoke_attached"],
                    "live_lakehouse_smoke_passed": result.manifest["summary"]["live_lakehouse_smoke_passed"],
                    "iceberg_catalog_smoke_attached": result.manifest["summary"]["iceberg_catalog_smoke_attached"],
                    "iceberg_catalog_smoke_passed": result.manifest["summary"]["iceberg_catalog_smoke_passed"],
                    "object_store_smoke_attached": result.manifest["summary"]["object_store_smoke_attached"],
                    "object_store_smoke_passed": result.manifest["summary"]["object_store_smoke_passed"],
                    "trino_sql_smoke_attached": result.manifest["summary"]["trino_sql_smoke_attached"],
                    "trino_sql_smoke_passed": result.manifest["summary"]["trino_sql_smoke_passed"],
                    "trino_iceberg_minio_smoke_attached": result.manifest["summary"]["trino_iceberg_minio_smoke_attached"],
                    "trino_iceberg_minio_smoke_passed": result.manifest["summary"]["trino_iceberg_minio_smoke_passed"],
                    "catalog_cross_engine_smoke_attached": result.manifest["summary"][
                        "catalog_cross_engine_smoke_attached"
                    ],
                    "catalog_cross_engine_smoke_passed": result.manifest["summary"][
                        "catalog_cross_engine_smoke_passed"
                    ],
                    "catalog_runtime_ops_attached": result.manifest["summary"]["catalog_runtime_ops_attached"],
                    "catalog_runtime_ops_passed": result.manifest["summary"]["catalog_runtime_ops_passed"],
                    "catalog_runtime_release_gate_passed": result.manifest["summary"][
                        "catalog_runtime_release_gate_passed"
                    ],
                    "orchestration_runtime_ops_attached": result.manifest["summary"][
                        "orchestration_runtime_ops_attached"
                    ],
                    "orchestration_runtime_ops_passed": result.manifest["summary"][
                        "orchestration_runtime_ops_passed"
                    ],
                    "orchestration_runtime_release_gate_passed": result.manifest["summary"][
                        "orchestration_runtime_release_gate_passed"
                    ],
                    "trino_runtime_security_smoke_attached": result.manifest["summary"]["trino_runtime_security_smoke_attached"],
                    "trino_runtime_security_smoke_passed": result.manifest["summary"]["trino_runtime_security_smoke_passed"],
                    "policy_decision_smoke_attached": result.manifest["summary"]["policy_decision_smoke_attached"],
                    "policy_decision_smoke_passed": result.manifest["summary"]["policy_decision_smoke_passed"],
                    "oidc_auth_smoke_attached": result.manifest["summary"]["oidc_auth_smoke_attached"],
                    "oidc_auth_smoke_passed": result.manifest["summary"]["oidc_auth_smoke_passed"],
                    "access_privacy_release_gate_passed": result.manifest["summary"][
                        "access_privacy_release_gate_passed"
                    ],
                    "secret_rotation_smoke_attached": result.manifest["summary"][
                        "secret_rotation_smoke_attached"
                    ],
                    "secret_rotation_smoke_passed": result.manifest["summary"]["secret_rotation_smoke_passed"],
                    "secret_rotation_ops_attached": result.manifest["summary"]["secret_rotation_ops_attached"],
                    "secret_rotation_ops_passed": result.manifest["summary"]["secret_rotation_ops_passed"],
                    "secret_rotation_ops_release_gate_passed": result.manifest["summary"][
                        "secret_rotation_ops_release_gate_passed"
                    ],
                    "dagster_orchestration_smoke_attached": result.manifest["summary"]["dagster_orchestration_smoke_attached"],
                    "dagster_orchestration_smoke_passed": result.manifest["summary"]["dagster_orchestration_smoke_passed"],
                    "dagster_day2_smoke_attached": result.manifest["summary"]["dagster_day2_smoke_attached"],
                    "dagster_day2_smoke_passed": result.manifest["summary"]["dagster_day2_smoke_passed"],
                    "dagster_day2_release_gate_passed": result.manifest["summary"][
                        "dagster_day2_release_gate_passed"
                    ],
                    "portfolio_release_smoke_attached": result.manifest["summary"]["portfolio_release_smoke_attached"],
                    "portfolio_release_smoke_passed": result.manifest["summary"]["portfolio_release_smoke_passed"],
                    "portfolio_release_smoke_covered_gold_count": result.manifest["summary"]["portfolio_release_smoke_covered_gold_count"],
                    "portfolio_release_smoke_gold_count": result.manifest["summary"]["portfolio_release_smoke_gold_count"],
                    "p0_gap_count": len(result.manifest["p0_gap_backlog"]),
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "production-review-gate":
        result = write_production_review_gate_report(
            args.manifest,
            args.output,
            profile=args.profile,
            environment=args.environment,
            generated_at=args.generated_at,
        )
        print(
            json.dumps(
                {
                    "manifest": result.report["manifest"]["path"],
                    "profile": result.report["profile"],
                    "environment": result.report["environment"],
                    "passed": result.report["passed"],
                    "failed_check_count": result.report["failed_check_count"],
                    "failed_checks": result.report["failed_checks"],
                    "verdict": result.report["verdict"],
                    "summary": result.report["summary"],
                    "output": result.output_path.as_posix() if result.output_path else None,
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.report["passed"] else 1
    if args.command == "build-recommendation":
        result = run_recommendation_pipeline_from_bronze(
            args.bronze,
            args.output_dir,
            upstream_manifest_path=args.upstream_manifest,
            snapshot_id=args.snapshot_id,
            built_at=args.built_at,
        )
        print(
            json.dumps(
                {
                    "snapshot_id": result.snapshot_id,
                    "silver_path": result.silver_path.as_posix(),
                    "gold_path": result.gold_path.as_posix(),
                    "manifest_path": result.manifest_path.as_posix(),
                    "row_count": result.manifest["row_count"],
                    "quality_passed": result.manifest["quality_passed"],
                    "upstream_quality_passed": result.manifest["upstream_quality_passed"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["quality_passed"] else 1
    if args.command == "build-lms-recommendation-training":
        result = run_lms_recommendation_training_from_bronze(
            args.course_bronze,
            args.enrollment_bronze,
            args.output_dir,
            upstream_manifest_paths=args.upstream_manifest,
            snapshot_id=args.snapshot_id,
            built_at=args.built_at,
        )
        print(
            json.dumps(
                {
                    "snapshot_id": result.snapshot_id,
                    "course_catalog_path": result.course_catalog_path.as_posix(),
                    "training_path": result.training_path.as_posix(),
                    "manifest_path": result.manifest_path.as_posix(),
                    "quality_passed": result.manifest["quality_passed"],
                    "metrics": result.manifest["metrics"],
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.manifest["quality_passed"] else 1
    if args.command == "run-recommendation-slice":
        result = run_recommendation_slice(
            args.root,
            args.input,
            args.output_dir,
            release_id=args.release_id,
            environment=args.environment,
            ingested_at=args.ingested_at,
            built_at=args.built_at,
            evaluation_time=args.evaluation_time,
            schema_id=args.schema_id,
            code_commit_sha=args.code_commit_sha,
            schema_registry_report_uri=args.schema_registry_report_uri,
            schema_registry_report_hash=args.schema_registry_report_hash,
            validator_output_uri=args.validator_output_uri,
            access_policy_check_id=args.access_policy_check_id,
            access_policy_report_uri=args.access_policy_report_uri,
            access_policy_report_hash=args.access_policy_report_hash,
            access_grant_evidence_uri=args.access_grant_evidence_uri,
            access_grant_evidence_hash=args.access_grant_evidence_hash,
            retention_evidence_uri=args.retention_evidence_uri,
            retention_evidence_hash=args.retention_evidence_hash,
            retention_evidence_input_path=args.retention_evidence_input,
            snapshot_evidence_uri=args.snapshot_evidence_uri,
            snapshot_evidence_hash=args.snapshot_evidence_hash,
            approver=args.approver,
        )
        print(
            json.dumps(
                {
                    "release_id": result.release_id,
                    "release_passed": result.evidence["release_passed"],
                    "ingestion_manifest_path": result.ingestion.manifest_path.as_posix(),
                    "medallion_manifest_path": result.medallion.manifest_path.as_posix(),
                    "catalog_bundle_path": result.catalog_bundle_path.as_posix(),
                    "evidence_path": result.evidence_path.as_posix(),
                    "gates": {
                        gate["gate_id"]: gate["passed"]
                        for gate in result.evidence["gates"]
                    },
                },
                ensure_ascii=True,
                sort_keys=True,
            )
        )
        return 0 if result.evidence["release_passed"] else 1
    parser.error(f"Unknown command {args.command}")
    return 2


def print_validation_result(result: ValidationResult) -> None:
    for warning in result.warnings:
        print(f"WARN {warning}")
    if result.ok:
        print(f"OK validated {result.checked_count} data platform artifact(s)")
        return
    for error in result.errors:
        print(f"ERROR {error}")


def print_pipeline_result(runner_id: str, result: object) -> None:
    manifest = getattr(result, "manifest")
    layers = manifest.get("layers") if isinstance(manifest.get("layers"), dict) else {}
    primary_output = manifest.get("primary_output")
    primary_layer = layers.get(primary_output) if primary_output else None
    row_count = manifest.get("row_count")
    if row_count is None and isinstance(primary_layer, dict):
        row_count = primary_layer.get("row_count")
    payload = {
        "runner_id": runner_id,
        "snapshot_id": getattr(result, "snapshot_id"),
        "manifest_path": getattr(result, "manifest_path").as_posix(),
        "row_count": row_count,
        "quality_passed": manifest["quality_passed"],
    }
    for attribute in ("bronze_path", "silver_path", "gold_path"):
        value = getattr(result, attribute, None)
        if value is not None:
            payload[attribute] = value.as_posix()
    if layers:
        payload["output_paths"] = {
            name: layer.get("path")
            for name, layer in layers.items()
            if isinstance(layer, dict) and layer.get("path")
        }
    if "upstream_quality_passed" in manifest:
        payload["upstream_quality_passed"] = manifest["upstream_quality_passed"]
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
