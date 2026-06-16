from __future__ import annotations

import argparse
import json
from pathlib import Path

from enterprise_df.access_grants import validate_access_grant_registry, write_access_grant_evidence_report
from enterprise_df.access_governance import validate_access_persona_registry, validate_consumer_contract_registry
from enterprise_df.access_policies import validate_access_policy_registry
from enterprise_df.access_policy import write_access_policy_report
from enterprise_df.attestations import validate_evidence_trust_key_registry, verify_attestation_file
from enterprise_df.backfill import validate_backfill_request_registry, write_backfill_readiness_report
from enterprise_df.capabilities import validate_capability_registry, write_capability_maturity_report
from enterprise_df.catalog import write_catalog_bundle
from enterprise_df.catalog_publish import write_catalog_publish_manifest
from enterprise_df.change_requests import validate_change_request_registry, write_change_control_evidence_report
from enterprise_df.contracts import ValidationResult, validate_contract_tree
from enterprise_df.control_tower import write_data_product_control_tower_report
from enterprise_df.domains import validate_domain_registry
from enterprise_df.environments import validate_environment_manifests
from enterprise_df.ingestion import run_bronze_ingestion
from enterprise_df.observability import write_observability_artifacts
from enterprise_df.openlineage import write_openlineage_events
from enterprise_df.orchestration import run_recommendation_slice, run_use_case
from enterprise_df.offset_ledger import write_offset_ledger_report
from enterprise_df.pipeline_registry_manifest import validate_pipeline_registry_manifest
from enterprise_df.pipelines import PipelineRunRequest, default_pipeline_registry, run_recommendation_pipeline_from_bronze
from enterprise_df.portfolio import write_enterprise_portfolio_readiness_report
from enterprise_df.products import scaffold_product_onboarding, validate_product_onboarding_tree
from enterprise_df.promotion import write_release_activation_manifest, write_release_promotion_manifest
from enterprise_df.quality_profiles import validate_quality_profile_registry
from enterprise_df.retention import validate_retention_policy_registry, write_retention_evidence_report
from enterprise_df.release_profiles import validate_release_profile_registry
from enterprise_df.runtime import (
    validate_runtime_topology,
    write_runtime_evidence_pack,
    write_runtime_iac_evidence_pack,
    write_runtime_readiness_report,
)
from enterprise_df.schema_registry import write_schema_registry_report
from enterprise_df.source_activation_ledger import (
    write_source_activation_ops_report,
    validate_source_activation_registry,
    write_source_activation_manifest_from_bundle,
    write_source_revocation_manifest,
)
from enterprise_df.source_bridge import run_source_bridge_preflight
from enterprise_df.source_readiness_bundle import run_source_readiness_bundle
from enterprise_df.scope_guardrails import validate_scope_guardrails
from enterprise_df.semantic_metrics import validate_semantic_metric_registry
from enterprise_df.semantic_views import write_semantic_view_manifest
from enterprise_df.snapshot_evidence import write_snapshot_evidence_report
from enterprise_df.source_registry import validate_source_registry, write_source_readiness_report
from enterprise_df.structure import validate_project_structure
from enterprise_df.usecases import validate_use_case_registry


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="enterprise-df",
        description="Validate and run local enterprise data platform tooling.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate contracts under df/.")
    validate_parser.add_argument(
        "--root",
        default=".",
        help="Data platform root directory. Use repository df/ path when running outside df.",
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
    openlineage_parser.add_argument("--namespace", default="enterprise-df://local", help="OpenLineage job and dataset namespace.")
    openlineage_parser.add_argument(
        "--producer",
        default="https://enterprise-df.local/openlineage-export",
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
    semantic_views_parser = subparsers.add_parser(
        "semantic-views-export",
        help="Export deployable Trino/Dremio semantic view SQL manifest from semantic metric definitions.",
    )
    semantic_views_parser.add_argument("--root", default=".", help="Data platform root directory.")
    semantic_views_parser.add_argument("--output", required=True, help="Output semantic views manifest JSON path.")
    semantic_views_parser.add_argument("--engine", choices=("all", "trino", "dremio"), default="all", help="Target serving engine.")
    semantic_views_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
    capability_parser = subparsers.add_parser(
        "capability-maturity-report",
        help="Write enterprise data foundation capability maturity and production-readiness report.",
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
    control_tower_parser.add_argument(
        "--release-evidence",
        action="append",
        default=[],
        help="Optional release evidence JSON artifact. Can be passed multiple times.",
    )
    control_tower_parser.add_argument("--capability-maturity-report", default=None, help="Optional capability maturity report JSON artifact.")
    control_tower_parser.add_argument("--environment", default="local", choices=("local", "staging", "prod"), help="Control Tower target environment.")
    control_tower_parser.add_argument("--generated-at", default=None, help="UTC generated_at override.")
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
    runtime_pack_parser.add_argument("--issuer-tool", default="enterprise-df-runtime-evidence-pack", help="Evidence issuer tool name.")
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
        result.extend(validate_pipeline_registry_manifest(root))
        result.extend(validate_semantic_metric_registry(root))
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
            release_evidence_paths=args.release_evidence,
            capability_maturity_report_path=args.capability_maturity_report,
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
        )
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0 if result["passed"] else 1
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
    payload = {
        "runner_id": runner_id,
        "snapshot_id": getattr(result, "snapshot_id"),
        "manifest_path": getattr(result, "manifest_path").as_posix(),
        "row_count": manifest["row_count"],
        "quality_passed": manifest["quality_passed"],
    }
    for attribute in ("bronze_path", "silver_path", "gold_path"):
        value = getattr(result, attribute, None)
        if value is not None:
            payload[attribute] = value.as_posix()
    if isinstance(manifest.get("layers"), dict):
        payload["output_paths"] = {
            name: layer.get("path")
            for name, layer in manifest["layers"].items()
            if isinstance(layer, dict) and layer.get("path")
        }
    if "upstream_quality_passed" in manifest:
        payload["upstream_quality_passed"] = manifest["upstream_quality_passed"]
    print(json.dumps(payload, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
