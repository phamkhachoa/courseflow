from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from enterprise_dp.access_grants import write_access_grant_ops_report
from enterprise_dp.catalog_lineage_ops import write_catalog_lineage_ops_report
from enterprise_dp.catalog_runtime_ops import write_catalog_runtime_ops_report
from enterprise_dp.contract_impact import write_contract_impact_report
from enterprise_dp.control_tower import (
    build_data_product_control_tower_report,
    validate_data_product_control_tower_report,
    write_data_product_control_tower_report,
)
from enterprise_dp.data_plane_smoke import write_data_plane_smoke_report
from enterprise_dp.ingestion_runtime import write_ingestion_runtime_ops_report
from enterprise_dp.lakehouse_ops import write_bronze_lakehouse_ops_report
from enterprise_dp.orchestration import run_use_case
from enterprise_dp.orchestration_runtime_ops import write_orchestration_runtime_ops_report
from enterprise_dp.pipelines.control_tower import run_control_tower_gold_materialization
from enterprise_dp.publication_ops import write_silver_gold_publication_ops_report
from enterprise_dp.quality_slo_ops import write_quality_slo_ops_report
from enterprise_dp.runtime import write_runtime_readiness_report
from enterprise_dp.schema_registry import write_schema_registry_ops_report
from enterprise_dp.semantic_serving_ops import write_semantic_metric_serving_ops_report
from enterprise_dp.source_activation_ledger import write_source_activation_ops_report


ROOT = Path(__file__).resolve().parents[1]
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"
BILLING_TOPIC = "finance.billing_transaction.settled.v1"


def test_control_tower_report_aggregates_enterprise_data_product_evidence() -> None:
    report = build_data_product_control_tower_report(
        ROOT,
        generated_at="2026-06-16T11:00:00Z",
    )

    assert report["artifact_type"] == "data_product_control_tower_report.v1"
    assert report["readiness_state"] == "not_ready"
    assert report["p0_ready"] is False
    assert report["passed"] is False
    assert report["summary"]["data_product_count"] >= 13
    assert report["summary"]["capability_blocker_count"] >= 1
    assert report["summary"]["gold_release_coverage"]["gold_count"] >= 6
    assert "data-product-control-tower" in report["scope"]["use_cases"]
    assert "enterprise-data-platform" in report["scope"]["products"]
    assert report["inputs"]["catalog_bundle"]["source"] == "generated_from_root"
    assert report["inputs"]["catalog_lineage_ops_report"]["source"] == "generated_from_root"
    assert report["inputs"]["quality_slo_ops_report"]["source"] == "generated_from_root"
    assert report["inputs"]["semantic_metric_serving_ops_report"]["source"] == "generated_from_root"
    assert report["inputs"]["schema_registry_ops_report"]["source"] == "generated_from_root"
    assert report["inputs"]["data_plane_smoke_report"]["source"] == "not_attached"
    assert report["inputs"]["capability_maturity_report"]["readiness_state"] == "not_ready"
    assert report["inputs"]["access_grant_ops_report"]["source"] == "generated_from_root"
    assert report["inputs"]["ingestion_runtime_report"]["source"] == "generated_from_root"
    assert report["inputs"]["bronze_lakehouse_ops_report"]["source"] == "generated_from_root"
    assert report["inputs"]["silver_gold_publication_ops_report"]["source"] == "generated_from_root"
    assert report["inputs"]["runtime_readiness_report"]["source"] == "generated_from_root"
    assert report["summary"]["ingestion_runtime"]["environment"] == "local"
    assert report["summary"]["catalog_lineage_ops"]["environment"] == "local"
    assert report["summary"]["catalog_lineage_ops"]["passed"] is True
    assert report["summary"]["catalog_lineage_ops_blocker_count"] == 0
    assert report["summary"]["quality_slo_ops"]["environment"] == "local"
    assert report["summary"]["quality_slo_ops"]["passed"] is True
    assert report["summary"]["quality_slo_ops_blocker_count"] == 0
    assert report["summary"]["semantic_metric_serving_ops"]["environment"] == "local"
    assert report["summary"]["semantic_metric_serving_ops"]["passed"] is True
    assert report["summary"]["semantic_metric_serving_ops_blocker_count"] == 0
    assert report["summary"]["schema_registry_ops"]["environment"] == "local"
    assert report["summary"]["schema_registry_ops"]["passed"] is True
    assert report["summary"]["schema_registry_ops_blocker_count"] == 0
    assert report["summary"]["data_plane_smoke"]["attached"] is False
    assert report["summary"]["data_plane_smoke_blocker_count"] == 0
    assert report["summary"]["ingestion_runtime"]["passed"] is True
    assert report["summary"]["ingestion_runtime_blocker_count"] == 0
    assert report["summary"]["bronze_lakehouse_ops"]["environment"] == "local"
    assert report["summary"]["bronze_lakehouse_ops"]["passed"] is True
    assert report["summary"]["bronze_lakehouse_ops_blocker_count"] == 0
    assert report["summary"]["silver_gold_publication_ops"]["environment"] == "local"
    assert report["summary"]["silver_gold_publication_ops"]["passed"] is True
    assert report["summary"]["silver_gold_publication_ops_blocker_count"] == 0
    assert report["summary"]["runtime_readiness"]["environment"] == "local"
    assert report["summary"]["runtime_readiness"]["passed"] is True
    assert report["summary"]["access_grant_ops"]["active_grant_count"] > 0
    assert report["summary"]["access_grant_ops"]["p0_issue_count"] == 0
    assert report["summary"]["access_grant_ops"]["review_overdue_count"] > 0
    assert any(row["gate"] == "contract_active" for row in report["gate_matrix"])
    assert any(row["gate"] == "access_grant_ops_p0_clear" for row in report["gate_matrix"])
    assert any(blocker["scope"] == "platform_capability" for blocker in report["blockers"])

    inventory = data_product(report, "gold.data_product_inventory")
    assert inventory["product"] == "enterprise-data-platform"
    assert inventory["domain"] == "enterprise-reporting"
    assert inventory["quality"]["quality_profiles"][0]["id"] == "p0-data-product-control-tower"
    assert inventory["readiness_state"] == "blocked"
    recsys = data_product(report, "gold.recsys_interactions")
    assert recsys["access"]["grant_ops"]["p0_issue_count"] == 0
    assert recsys["access"]["grant_ops"]["p1_issue_count"] > 0

    validation = validate_data_product_control_tower_report(report)
    assert validation.errors == []


def test_control_tower_blocks_failed_catalog_lineage_ops_report(tmp_path: Path) -> None:
    ops_path = write_catalog_lineage_ops_payload(tmp_path, environment="local", passed=False)

    report = build_data_product_control_tower_report(
        ROOT,
        catalog_lineage_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "catalog_lineage_ops_passed"]
    assert report["inputs"]["catalog_lineage_ops_report"]["source"] == "artifact"
    assert report["summary"]["catalog_lineage_ops"]["passed"] is False
    assert report["summary"]["catalog_lineage_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "catalog-lineage-control-plane"
    assert any(
        gate["gate_id"] == "catalog_lineage_ops_report_passed"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_catalog_lineage_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_catalog_lineage_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        catalog_lineage_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "catalog_lineage_ops_passed"]
    assert report["summary"]["catalog_lineage_ops"]["passed"] is True
    assert report["summary"]["catalog_lineage_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "catalog_lineage_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "catalog_lineage_ops_state_valid_for_environment"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_catalog_lineage_catalog_hash_mismatch(tmp_path: Path) -> None:
    ops = write_catalog_lineage_ops_report(
        ROOT,
        tmp_path / "catalog-lineage" / "local.json",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
    )
    payload = json.loads(ops.output_path.read_text(encoding="utf-8"))
    payload["summary"]["catalog_hash"] = "sha256:9999999999999999999999999999999999999999999999999999999999999999"
    bad_path = tmp_path / "catalog-lineage" / "bad-hash.json"
    bad_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = build_data_product_control_tower_report(
        ROOT,
        catalog_lineage_ops_report_path=bad_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "catalog_lineage_ops_passed"]
    assert report["summary"]["catalog_lineage_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "catalog_lineage_ops_catalog_hash_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_failed_quality_slo_ops_report(tmp_path: Path) -> None:
    ops_path = write_quality_slo_ops_payload(tmp_path, environment="local", passed=False)

    report = build_data_product_control_tower_report(
        ROOT,
        quality_slo_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "quality_slo_release_gates_ops_passed"]
    assert report["inputs"]["quality_slo_ops_report"]["source"] == "artifact"
    assert report["summary"]["quality_slo_ops"]["passed"] is False
    assert report["summary"]["quality_slo_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "quality-slo-release-gates"
    assert any(
        gate["gate_id"] == "quality_slo_release_gates_ops_report_passed"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_quality_slo_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_quality_slo_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        quality_slo_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "quality_slo_release_gates_ops_passed"]
    assert report["summary"]["quality_slo_ops"]["passed"] is True
    assert report["summary"]["quality_slo_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "quality_slo_release_gates_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "quality_slo_release_gates_ops_state_valid_for_environment"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_failed_semantic_metric_serving_ops_report(tmp_path: Path) -> None:
    ops_path = write_semantic_metric_serving_ops_payload(tmp_path, environment="local", passed=False)

    report = build_data_product_control_tower_report(
        ROOT,
        semantic_metric_serving_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "semantic_metric_serving_ops_passed"]
    assert report["inputs"]["semantic_metric_serving_ops_report"]["source"] == "artifact"
    assert report["summary"]["semantic_metric_serving_ops"]["passed"] is False
    assert report["summary"]["semantic_metric_serving_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "semantic-metric-serving"
    assert any(
        gate["gate_id"] == "semantic_metric_serving_ops_report_passed"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_semantic_metric_serving_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_semantic_metric_serving_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        semantic_metric_serving_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "semantic_metric_serving_ops_passed"]
    assert report["summary"]["semantic_metric_serving_ops"]["passed"] is True
    assert report["summary"]["semantic_metric_serving_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "semantic_metric_serving_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "semantic_metric_serving_ops_state_valid_for_environment"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_failed_schema_registry_ops_report(tmp_path: Path) -> None:
    ops_path = write_schema_registry_ops_payload(tmp_path, environment="local", passed=False)

    report = build_data_product_control_tower_report(
        ROOT,
        schema_registry_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "schema_registry_ops_passed"]
    assert report["inputs"]["schema_registry_ops_report"]["source"] == "artifact"
    assert report["summary"]["schema_registry_ops"]["passed"] is False
    assert report["summary"]["schema_registry_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "schema-registry-compatibility"
    assert any(
        gate["gate_id"] == "schema_registry_ops_report_passed"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_schema_registry_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_schema_registry_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        schema_registry_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "schema_registry_ops_passed"]
    assert report["summary"]["schema_registry_ops"]["passed"] is True
    assert report["summary"]["schema_registry_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "schema_registry_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "schema_registry_ops_state_valid_for_environment"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_invalid_schema_registry_ops_artifact_type(tmp_path: Path) -> None:
    ops_path = write_schema_registry_ops_payload(
        tmp_path,
        environment="local",
        passed=True,
        artifact_type="wrong.v1",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        schema_registry_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "schema_registry_ops_passed"]
    assert report["summary"]["schema_registry_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "schema_registry_ops_artifact_type_valid"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_summarizes_catalog_runtime_ops_without_overclaim(tmp_path: Path) -> None:
    ops_path = write_catalog_runtime_ops_payload(tmp_path, environment="staging")

    report = build_data_product_control_tower_report(
        ROOT,
        catalog_runtime_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "catalog_runtime_ops_passed"]
    summary = report["summary"]["catalog_runtime_ops"]
    assert report["inputs"]["catalog_runtime_ops_report"]["source"] == "artifact"
    assert summary["attached"] is True
    assert summary["environment"] == "staging"
    assert summary["readiness_state"] == "production_like_ready"
    assert summary["failover_passed"] is True
    assert summary["stale_commit_rejected"] is True
    assert report["summary"]["catalog_runtime_ops_blocker_count"] == 0
    assert blockers == []


def test_control_tower_blocks_catalog_runtime_ops_environment_mismatch(tmp_path: Path) -> None:
    ops_path = write_catalog_runtime_ops_payload(tmp_path, environment="staging")

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        catalog_runtime_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "catalog_runtime_ops_passed"]
    assert report["summary"]["catalog_runtime_ops"]["passed"] is True
    assert report["summary"]["catalog_runtime_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "production-catalog-runtime"
    assert any(
        gate["gate_id"] == "catalog_runtime_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_summarizes_orchestration_runtime_ops_without_overclaim(tmp_path: Path) -> None:
    ops_path = write_orchestration_runtime_ops_payload(tmp_path, environment="staging")

    report = build_data_product_control_tower_report(
        ROOT,
        orchestration_runtime_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "orchestration_runtime_ops_passed"]
    summary = report["summary"]["orchestration_runtime_ops"]
    assert report["inputs"]["orchestration_runtime_ops_report"]["source"] == "artifact"
    assert summary["attached"] is True
    assert summary["environment"] == "staging"
    assert summary["readiness_state"] == "production_like_ready"
    assert summary["kubernetes_run_launcher_enabled"] is True
    assert summary["managed_run_storage"] is True
    assert summary["secret_injection_verified"] is True
    assert report["summary"]["orchestration_runtime_ops_blocker_count"] == 0
    assert blockers == []


def test_control_tower_blocks_orchestration_runtime_ops_environment_mismatch(tmp_path: Path) -> None:
    ops_path = write_orchestration_runtime_ops_payload(tmp_path, environment="staging")

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        orchestration_runtime_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "orchestration_runtime_ops_passed"]
    assert report["summary"]["orchestration_runtime_ops"]["passed"] is True
    assert report["summary"]["orchestration_runtime_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "production-orchestration-runtime"
    assert any(
        gate["gate_id"] == "orchestration_runtime_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_prod_schema_registry_without_publication_and_attestation() -> None:
    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "schema_registry_ops_passed"]
    assert report["summary"]["schema_registry_ops"]["passed"] is False
    assert report["summary"]["schema_registry_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "publication_evidence_attached"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "external_attestation_verified"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_prod_schema_registry_thin_subject_evidence_even_if_payload_passes(
    tmp_path: Path,
) -> None:
    ops_path = tmp_path / "schema-registry-ops" / "thin-prod.json"
    ops_path.parent.mkdir(parents=True, exist_ok=True)
    ops_path.write_text(
        json.dumps(
            {
                "artifact_type": "schema_registry_ops_report.v1",
                "generated_at": "2026-01-15T10:05:00Z",
                "environment": "prod",
                "release_id": "schema-prod-release",
                "capability_id": "schema-registry-compatibility",
                "readiness_state": "production_like_ready",
                "mode": "external_registry_evidence",
                "registry_uri": "https://schema-registry.prod.example",
                "passed": True,
                "publication_evidence": {
                    "attached": True,
                    "artifact_type": "schema_registry_publication_manifest.v1",
                    "environment": "prod",
                    "registry_uri": "https://schema-registry.prod.example",
                    "hash": "sha256:" + ("7" * 64),
                },
                "attestation": {
                    "attached": True,
                    "passed": True,
                    "subject_hash": "sha256:" + ("7" * 64),
                    "required": {
                        "signature_verified": True,
                        "subject_hash_matches": True,
                    },
                },
                "checks": [
                    {"check": "compatibility_report_type_valid", "passed": True},
                    {"check": "compatibility_report_passed", "passed": True},
                    {"check": "publication_evidence_attached", "passed": True},
                    {"check": "publication_evidence_type_valid", "passed": True},
                    {"check": "publication_environment_matches", "passed": True},
                    {"check": "production_registry_uri_declared", "passed": True},
                    {"check": "external_attestation_verified", "passed": True},
                    {"check": "attestation_subject_hash_matches_publication", "passed": True},
                ],
                "subjects": [
                    {
                        "subject": "finance.benefit_settled.v1-value",
                        "passed": True,
                        "publication": {
                            "registered": True,
                            "schema_id": "schema-1",
                            "compatibility": "BACKWARD_TRANSITIVE",
                            "producer_enforced": True,
                            "broker_validation": True,
                        },
                    }
                ],
                "summary": {
                    "subject_count": 1,
                    "passed_subject_count": 1,
                    "failed_subject_count": 0,
                    "p0_subject_count": 1,
                    "p0_failed_subject_count": 0,
                    "global_failed_check_count": 0,
                    "publication_evidence_attached": True,
                    "producer_enforcement_gap_count": 0,
                    "broker_validation_gap_count": 0,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        schema_registry_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "schema_registry_ops_passed"]
    assert report["summary"]["schema_registry_ops"]["passed"] is True
    assert report["summary"]["schema_registry_ops_blocker_count"] == 1
    assert len(blockers) == 1
    failed_gate_ids = {gate["gate_id"] for gate in blockers[0]["details"]["failed_gates"]}
    assert "schema_registry_ops_p0_subject_coverage" in failed_gate_ids
    assert "schema_registry_ops_subject_runtime_evidence_strict" in failed_gate_ids


def test_control_tower_blocks_access_grant_ops_p0_from_attached_report(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "contracts", tmp_path / "contracts")
    shutil.copytree(ROOT / "governance", tmp_path / "governance")
    registry_path = tmp_path / "governance" / "access-grants.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registry["grants"][0]["approver"] = registry["grants"][0]["requester"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    ops_result = write_access_grant_ops_report(
        tmp_path,
        tmp_path / "build" / "access-grant-ops.json",
        environment="prod",
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        access_grant_ops_report_path=ops_result.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    recsys = data_product(report, "gold.recsys_interactions")
    assert report["inputs"]["access_grant_ops_report"]["source"] == "artifact"
    assert report["summary"]["access_grant_ops"]["p0_issue_count"] == 1
    assert recsys["access"]["grant_ops"]["issue_ids"] == ["access_review_overdue", "maker_checker_conflict"]
    assert any(blocker["gate"] == "access_grant_ops_p0_clear" for blocker in recsys["blockers"])
    assert any(
        blocker["data_product"] == "gold.recsys_interactions" and blocker["gate"] == "access_grant_ops_p0_clear"
        for blocker in report["blockers"]
    )


def test_control_tower_summarizes_contract_impact_review_queue(tmp_path: Path) -> None:
    impact = write_contract_impact_report(
        ROOT,
        tmp_path / "impact" / "billing-impact.json",
        topic_name=BILLING_TOPIC,
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        contract_impact_report_paths=[impact.output_path],
        generated_at="2026-06-16T12:05:00Z",
    )

    assert report["inputs"]["contract_impact_reports"]["report_count"] == 1
    assert report["inputs"]["contract_impact_reports"]["review_required_count"] == 1
    assert report["summary"]["contract_impact"]["review_required_topics"] == [BILLING_TOPIC]
    assert report["summary"]["contract_impact"]["affected_p0_use_case_count"] >= 2
    assert not any(blocker["gate"] == "contract_impact_release_not_blocked" for blocker in report["blockers"])


def test_control_tower_blocks_contract_impact_p0_breaking_change(tmp_path: Path) -> None:
    schema_report = tmp_path / "schema-registry" / "billing-breaking.json"
    schema_report.parent.mkdir(parents=True)
    schema_report.write_text(
        json.dumps(
            {
                "artifact_type": "schema_registry_compatibility_report.v1",
                "report_version": 1,
                "compatibility_passed": False,
                "subject_count": 1,
                "summary": {"passed_subjects": 0, "failed_subjects": 1},
                "subjects": [
                    {
                        "subject": f"{BILLING_TOPIC}-value",
                        "topic": BILLING_TOPIC,
                        "contract_path": "contracts/topics/finance.billing_transaction.settled.v1.yaml",
                        "contract_hash": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "contract_version": 2,
                        "product": "billing-platform",
                        "domain": "finance",
                        "compatibility": "BACKWARD_TRANSITIVE",
                        "prior_versions_checked": ["finance.billing_transaction.settled.v1"],
                        "compatibility_passed": False,
                        "checks": [
                            {
                                "check": "backward_transitive_local",
                                "passed": False,
                                "details": {"violations": ["$: new required fields added: ['settlementBatchId']"]},
                            }
                        ],
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    impact = write_contract_impact_report(
        ROOT,
        tmp_path / "impact" / "billing-impact-blocked.json",
        topic_name=BILLING_TOPIC,
        schema_registry_report_path=schema_report,
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        contract_impact_report_paths=[impact.output_path],
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "contract_impact_release_not_blocked"]
    assert report["summary"]["contract_impact"]["blocked_topics"] == [BILLING_TOPIC]
    assert report["summary"]["contract_impact_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["details"]["affected_p0_use_case_count"] >= 2


def test_control_tower_blocks_failed_runtime_readiness_report(tmp_path: Path) -> None:
    runtime = write_runtime_readiness_report(
        ROOT,
        tmp_path / "runtime" / "prod-readiness.json",
        environment="prod",
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        runtime_readiness_report_path=runtime.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "runtime_readiness_passed"]
    assert report["inputs"]["runtime_readiness_report"]["source"] == "artifact"
    assert report["summary"]["runtime_readiness"]["readiness_state"] == "production_like_not_ready"
    assert report["summary"]["runtime_readiness_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["details"]["failed_gate_count"] >= 1
    assert any(gate["gate_id"] == "runtime_iac_deployed" for gate in blockers[0]["details"]["failed_gates"])


def test_control_tower_blocks_runtime_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    runtime = write_runtime_readiness_report(
        ROOT,
        tmp_path / "runtime" / "local-readiness.json",
        environment="local",
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        runtime_readiness_report_path=runtime.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "runtime_readiness_passed"]
    assert report["summary"]["runtime_readiness"]["passed"] is True
    assert report["summary"]["runtime_readiness_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "runtime_readiness_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "runtime_readiness_state_valid_for_environment"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_wrong_runtime_artifact_type_even_if_payload_passes(tmp_path: Path) -> None:
    runtime = write_runtime_readiness_report(
        ROOT,
        tmp_path / "runtime" / "local-readiness.json",
        environment="local",
        generated_at="2026-06-16T12:00:00Z",
    )
    payload = json.loads(runtime.output_path.read_text(encoding="utf-8"))
    payload["artifact_type"] = "not_runtime_readiness_report.v1"
    bad_report_path = tmp_path / "runtime" / "bad-runtime-artifact.json"
    bad_report_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = build_data_product_control_tower_report(
        ROOT,
        runtime_readiness_report_path=bad_report_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "runtime_readiness_passed"]
    assert report["summary"]["runtime_readiness"]["passed"] is True
    assert report["summary"]["runtime_readiness_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "runtime_readiness_artifact_type_valid"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_accepts_passing_source_activation_ops_artifact(tmp_path: Path) -> None:
    ops_path = write_source_activation_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        source_activation_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    assert report["inputs"]["source_activation_ops_report"]["source"] == "artifact"
    assert report["summary"]["source_activation_ops"]["passed"] is True
    assert report["summary"]["source_activation_ops_blocker_count"] == 0
    assert not any(blocker["gate"] == "source_activation_ops_p0_clear" for blocker in report["blockers"])


def test_control_tower_blocks_failed_source_activation_ops_report(tmp_path: Path) -> None:
    ops = write_source_activation_ops_report(
        ROOT,
        tmp_path / "source-activation-ops" / "staging.json",
        environment="staging",
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        environment="staging",
        source_activation_ops_report_path=ops.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "source_activation_ops_p0_clear"]
    assert report["summary"]["source_activation_ops"]["passed"] is False
    assert report["summary"]["source_activation_ops"]["critical_issue_count"] > 0
    assert report["summary"]["source_activation_ops"]["p0_next_action_count"] > 0
    assert report["summary"]["source_activation_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["details"]["critical_sources"][0]["source_id"] == "billing-platform-billing-transaction-settled-outbox"
    assert any(
        row["risk_state"] == "p0_source_unactivated"
        for row in blockers[0]["details"]["critical_source_rows"]
    )
    assert any(gate["gate_id"] == "source_activation_ops_passed" for gate in blockers[0]["details"]["failed_gates"])


def test_control_tower_consumes_fail_closed_source_ops_for_p0_unactivated_sources(tmp_path: Path) -> None:
    ops = write_source_activation_ops_report(
        ROOT,
        tmp_path / "source-activation-ops" / "prod.json",
        environment="prod",
        generated_at="2026-06-16T12:00:00Z",
    )
    assert ops.report["passed"] is False

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        source_activation_ops_report_path=ops.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "source_activation_ops_p0_clear"]
    assert report["summary"]["source_activation_ops"]["passed"] is False
    assert report["summary"]["source_activation_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        row["risk_state"] == "p0_source_unactivated"
        for row in blockers[0]["details"]["critical_source_rows"]
    )
    assert any(
        gate["gate_id"] == "source_activation_ops_passed"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "source_activation_critical_risk_clear"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_runtime_readiness_gap_even_if_source_ops_payload_passes(tmp_path: Path) -> None:
    ops_path = write_source_activation_ops_payload(tmp_path, environment="local", passed=True)
    payload = json.loads(ops_path.read_text(encoding="utf-8"))
    payload["summary"]["critical_issue_count"] = 1
    payload["summary"]["runtime_readiness_issue_count"] = 1
    payload["sources"] = [
        {
            "source_id": "billing-platform-billing-transaction-settled-outbox",
            "risk_state": "runtime_readiness_evidence_missing",
            "issues": ["runtime_readiness_evidence_missing"],
            "runtime_readiness": {"required": True, "attached": False},
        }
    ]
    ops_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = build_data_product_control_tower_report(
        ROOT,
        source_activation_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "source_activation_ops_p0_clear"]
    assert report["summary"]["source_activation_ops"]["passed"] is True
    assert report["summary"]["source_activation_ops"]["runtime_readiness_issue_count"] == 1
    assert report["summary"]["source_activation_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        row["risk_state"] == "runtime_readiness_evidence_missing"
        for row in blockers[0]["details"]["critical_source_rows"]
    )
    assert any(
        gate["gate_id"] == "source_activation_critical_risk_clear"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_source_activation_ops_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_source_activation_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        source_activation_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "source_activation_ops_p0_clear"]
    assert report["summary"]["source_activation_ops"]["passed"] is True
    assert report["summary"]["source_activation_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "source_activation_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_wrong_source_activation_ops_artifact_type_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_source_activation_ops_payload(
        tmp_path,
        environment="local",
        passed=True,
        artifact_type="not_source_activation_ops_report.v1",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        source_activation_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "source_activation_ops_p0_clear"]
    assert report["summary"]["source_activation_ops"]["passed"] is True
    assert report["summary"]["source_activation_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "source_activation_ops_artifact_type_valid"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_failed_ingestion_runtime_report(tmp_path: Path) -> None:
    runtime = write_ingestion_runtime_ops_report(
        ROOT,
        tmp_path / "ingestion-runtime" / "prod.json",
        environment="prod",
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        ingestion_runtime_report_path=runtime.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "ingestion_runtime_passed"]
    assert report["inputs"]["ingestion_runtime_report"]["source"] == "artifact"
    assert report["summary"]["ingestion_runtime"]["readiness_state"] == "not_ready"
    assert report["summary"]["ingestion_runtime"]["passed"] is False
    assert report["summary"]["ingestion_runtime"]["p0_failed_source_count"] >= 1
    assert report["summary"]["ingestion_runtime_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "event-cdc-ingestion-runtime"
    assert any(
        gate["gate_id"] == "ingestion_runtime_p0_sources_clear"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_ingestion_runtime_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    runtime_path = write_ingestion_runtime_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        ingestion_runtime_report_path=runtime_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "ingestion_runtime_passed"]
    assert report["summary"]["ingestion_runtime"]["passed"] is True
    assert report["summary"]["ingestion_runtime_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "ingestion_runtime_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "ingestion_runtime_state_valid_for_environment"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_wrong_ingestion_runtime_artifact_type_even_if_payload_passes(tmp_path: Path) -> None:
    runtime_path = write_ingestion_runtime_ops_payload(
        tmp_path,
        environment="local",
        passed=True,
        artifact_type="not_event_cdc_ingestion_runtime_report.v1",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        ingestion_runtime_report_path=runtime_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "ingestion_runtime_passed"]
    assert report["summary"]["ingestion_runtime"]["passed"] is True
    assert report["summary"]["ingestion_runtime_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "ingestion_runtime_artifact_type_valid"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_failed_bronze_lakehouse_ops_report(tmp_path: Path) -> None:
    ops = write_bronze_lakehouse_ops_report(
        ROOT,
        tmp_path / "bronze-lakehouse" / "prod.json",
        environment="prod",
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        bronze_lakehouse_ops_report_path=ops.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "bronze_lakehouse_ops_passed"]
    assert report["inputs"]["bronze_lakehouse_ops_report"]["source"] == "artifact"
    assert report["summary"]["bronze_lakehouse_ops"]["readiness_state"] == "not_ready"
    assert report["summary"]["bronze_lakehouse_ops"]["passed"] is False
    assert report["summary"]["bronze_lakehouse_ops"]["p0_failed_table_count"] >= 1
    assert report["summary"]["bronze_lakehouse_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "bronze-lakehouse-evidence"
    assert any(
        gate["gate_id"] == "bronze_lakehouse_p0_tables_clear"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_bronze_lakehouse_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_bronze_lakehouse_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        bronze_lakehouse_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "bronze_lakehouse_ops_passed"]
    assert report["summary"]["bronze_lakehouse_ops"]["passed"] is True
    assert report["summary"]["bronze_lakehouse_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "bronze_lakehouse_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "bronze_lakehouse_ops_state_valid_for_environment"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_wrong_bronze_lakehouse_artifact_type_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_bronze_lakehouse_ops_payload(
        tmp_path,
        environment="local",
        passed=True,
        artifact_type="not_bronze_lakehouse_ops_report.v1",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        bronze_lakehouse_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "bronze_lakehouse_ops_passed"]
    assert report["summary"]["bronze_lakehouse_ops"]["passed"] is True
    assert report["summary"]["bronze_lakehouse_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "bronze_lakehouse_ops_artifact_type_valid"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_failed_silver_gold_publication_ops_report(tmp_path: Path) -> None:
    ops = write_silver_gold_publication_ops_report(
        ROOT,
        tmp_path / "publication" / "prod.json",
        environment="prod",
        generated_at="2026-06-16T12:00:00Z",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        silver_gold_publication_ops_report_path=ops.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "silver_gold_publication_ops_passed"]
    assert report["inputs"]["silver_gold_publication_ops_report"]["source"] == "artifact"
    assert report["summary"]["silver_gold_publication_ops"]["readiness_state"] == "not_ready"
    assert report["summary"]["silver_gold_publication_ops"]["passed"] is False
    assert report["summary"]["silver_gold_publication_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "silver-gold-publication"
    assert any(
        gate["gate_id"] == "silver_gold_publication_ops_report_passed"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_silver_gold_publication_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_silver_gold_publication_ops_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        silver_gold_publication_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "silver_gold_publication_ops_passed"]
    assert report["summary"]["silver_gold_publication_ops"]["passed"] is True
    assert report["summary"]["silver_gold_publication_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "silver_gold_publication_ops_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )
    assert any(
        gate["gate_id"] == "silver_gold_publication_ops_state_valid_for_environment"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_wrong_silver_gold_publication_artifact_type_even_if_payload_passes(tmp_path: Path) -> None:
    ops_path = write_silver_gold_publication_ops_payload(
        tmp_path,
        environment="local",
        passed=True,
        artifact_type="not_silver_gold_publication_ops_report.v1",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        silver_gold_publication_ops_report_path=ops_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "silver_gold_publication_ops_passed"]
    assert report["summary"]["silver_gold_publication_ops"]["passed"] is True
    assert report["summary"]["silver_gold_publication_ops_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "silver_gold_publication_ops_artifact_type_valid"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_cli_accepts_source_activation_ops_report(tmp_path: Path) -> None:
    ops_path = write_source_activation_ops_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-source-ops.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--source-activation-ops-report",
            str(ops_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["source_activation_ops"]["passed"] is False
    assert summary["summary"]["source_activation_ops_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_cli_accepts_catalog_lineage_ops_report(tmp_path: Path) -> None:
    ops_path = write_catalog_lineage_ops_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-catalog-lineage.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--catalog-lineage-ops-report",
            str(ops_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["catalog_lineage_ops"]["passed"] is False
    assert summary["summary"]["catalog_lineage_ops_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_cli_accepts_quality_slo_ops_report(tmp_path: Path) -> None:
    ops_path = write_quality_slo_ops_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-quality-slo.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--quality-slo-release-gates-ops-report",
            str(ops_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["quality_slo_ops"]["passed"] is False
    assert summary["summary"]["quality_slo_ops_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_cli_accepts_semantic_metric_serving_ops_report(tmp_path: Path) -> None:
    ops_path = write_semantic_metric_serving_ops_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-semantic-serving.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--semantic-metric-serving-ops-report",
            str(ops_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["semantic_metric_serving_ops"]["passed"] is False
    assert summary["summary"]["semantic_metric_serving_ops_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_cli_accepts_schema_registry_ops_report(tmp_path: Path) -> None:
    ops_path = write_schema_registry_ops_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-schema-registry.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--schema-registry-ops-report",
            str(ops_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["schema_registry_ops"]["passed"] is False
    assert summary["summary"]["schema_registry_ops_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_accepts_passing_data_plane_smoke_report(tmp_path: Path) -> None:
    smoke = write_data_plane_smoke_report(
        ROOT,
        tmp_path / "data-plane-smoke" / "report.json",
        output_dir=tmp_path / "data-plane-smoke" / "run",
        release_id="ct-finance-data-plane-smoke",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
        schema_id="registry:finance.benefit_settled.v1:1",
        snapshot_id="ct-finance-benefit-smoke",
    )

    report = build_data_product_control_tower_report(
        ROOT,
        data_plane_smoke_report_path=smoke.output_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    assert report["inputs"]["data_plane_smoke_report"]["source"] == "artifact"
    assert report["inputs"]["data_plane_smoke_report"]["passed"] is True
    assert report["summary"]["data_plane_smoke"]["attached"] is True
    assert report["summary"]["data_plane_smoke"]["passed"] is True
    assert report["summary"]["data_plane_smoke"]["use_case_id"] == "finance-benefit-reconciliation"
    assert report["summary"]["data_plane_smoke"]["primary_output"] == "gold.finance_benefit_reconciliation"
    assert report["summary"]["data_plane_smoke"]["query_name"] == "finance_reconciliation_by_status"
    assert report["summary"]["data_plane_smoke_blocker_count"] == 0
    assert not [blocker for blocker in report["blockers"] if blocker["gate"] == "data_plane_smoke_passed"]


def test_control_tower_blocks_failed_data_plane_smoke_report(tmp_path: Path) -> None:
    smoke_path = write_data_plane_smoke_payload(tmp_path, environment="local", passed=False)

    report = build_data_product_control_tower_report(
        ROOT,
        data_plane_smoke_report_path=smoke_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "data_plane_smoke_passed"]
    assert report["summary"]["data_plane_smoke"]["passed"] is False
    assert report["summary"]["data_plane_smoke_blocker_count"] == 1
    assert len(blockers) == 1
    assert blockers[0]["capability_id"] == "platform-runtime-iac"
    assert blockers[0]["data_product"] == "gold.finance_benefit_reconciliation"
    assert any(
        gate["gate_id"] == "data_plane_smoke_report_passed"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_blocks_data_plane_smoke_environment_mismatch_even_if_payload_passes(tmp_path: Path) -> None:
    smoke_path = write_data_plane_smoke_payload(tmp_path, environment="local", passed=True)

    report = build_data_product_control_tower_report(
        ROOT,
        environment="prod",
        data_plane_smoke_report_path=smoke_path,
        generated_at="2026-06-16T12:05:00Z",
    )

    blockers = [blocker for blocker in report["blockers"] if blocker["gate"] == "data_plane_smoke_passed"]
    assert report["summary"]["data_plane_smoke"]["passed"] is True
    assert report["summary"]["data_plane_smoke_blocker_count"] == 1
    assert len(blockers) == 1
    assert any(
        gate["gate_id"] == "data_plane_smoke_environment_matches_control_tower"
        for gate in blockers[0]["details"]["failed_gates"]
    )


def test_control_tower_cli_accepts_data_plane_smoke_report(tmp_path: Path) -> None:
    smoke_path = write_data_plane_smoke_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-data-plane-smoke.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--data-plane-smoke-report",
            str(smoke_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["data_plane_smoke"]["passed"] is False
    assert summary["summary"]["data_plane_smoke_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_cli_accepts_ingestion_runtime_report(tmp_path: Path) -> None:
    runtime_path = write_ingestion_runtime_ops_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-ingestion-runtime.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--ingestion-runtime-report",
            str(runtime_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["ingestion_runtime"]["passed"] is False
    assert summary["summary"]["ingestion_runtime_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_cli_accepts_bronze_lakehouse_ops_report(tmp_path: Path) -> None:
    ops_path = write_bronze_lakehouse_ops_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-bronze-lakehouse.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--bronze-lakehouse-ops-report",
            str(ops_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["bronze_lakehouse_ops"]["passed"] is False
    assert summary["summary"]["bronze_lakehouse_ops_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_cli_accepts_silver_gold_publication_ops_report(tmp_path: Path) -> None:
    ops_path = write_silver_gold_publication_ops_payload(tmp_path, environment="local", passed=False)
    output_path = tmp_path / "control-tower" / "cli-publication.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(output_path),
            "--silver-gold-publication-ops-report",
            str(ops_path),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["summary"]["silver_gold_publication_ops"]["passed"] is False
    assert summary["summary"]["silver_gold_publication_ops_blocker_count"] == 1
    assert output_path.is_file()


def test_control_tower_report_uses_release_evidence_when_attached(tmp_path: Path) -> None:
    run = run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        tmp_path / "finance-run",
        use_case_id="finance-benefit-reconciliation",
        release_id="control-tower-finance-release",
        environment="local",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
        snapshot_id="control-tower-finance-snapshot",
    )
    report = build_data_product_control_tower_report(
        ROOT,
        catalog_bundle_path=run.catalog_bundle_path,
        release_evidence_paths=[run.evidence_path],
        generated_at="2026-06-16T11:00:00Z",
    )

    finance = data_product(report, "gold.finance_benefit_reconciliation")
    assert finance["release_evidence"]["covered"] is True
    assert finance["release_evidence"]["passed"] is True
    assert finance["release_evidence"]["release_count"] == 1
    assert report["release_evidence"]["covered_data_products"] == [
        "gold.finance_benefit_reconciliation",
        "silver.finance_benefit_transactions",
    ]


def test_control_tower_writer_and_cli_block_until_p0_ready(tmp_path: Path) -> None:
    output_path = tmp_path / "control-tower" / "report.json"
    result = write_data_product_control_tower_report(
        ROOT,
        output_path,
        generated_at="2026-06-16T11:00:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "control-tower" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "control-tower-report",
            "--root",
            str(ROOT),
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-06-16T11:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["readiness_state"] == "not_ready"
    assert summary["p0_ready"] is False
    assert summary["passed"] is False
    assert summary["blocker_count"] >= 1
    assert cli_output.is_file()


def test_control_tower_materializes_four_operational_gold_outputs(tmp_path: Path) -> None:
    report_path = tmp_path / "control-tower" / "report.json"
    write_data_product_control_tower_report(
        ROOT,
        report_path,
        generated_at="2026-06-16T11:00:00Z",
    )

    result = run_control_tower_gold_materialization(
        report_path,
        tmp_path / "pipeline",
        snapshot_id="control-tower-snapshot",
        built_at="2026-06-16T11:05:00Z",
    )

    assert result.manifest["pipeline"] == "control_tower.materialize_gold.from_report.v1"
    assert result.manifest["quality_passed"] is True
    assert result.manifest["input"]["artifact_type"] == "data_product_control_tower_report.v1"
    assert set(result.manifest["layers"]) == {
        "gold.data_product_inventory",
        "gold.contract_compliance_daily",
        "gold.quality_sla_daily",
        "gold.lineage_coverage_daily",
    }
    assert result.manifest["lineage_edges"] == [
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.contract_compliance_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.quality_sla_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.contract_compliance_daily",
            "target": "gold.quality_sla_daily",
        },
        {
            "type": "RUN_LAYER_TRANSFORM",
            "source": "gold.data_product_inventory",
            "target": "gold.lineage_coverage_daily",
        },
    ]

    inventory = read_jsonl(result.inventory_path)
    contract = read_jsonl(result.contract_compliance_path)
    quality = read_jsonl(result.quality_sla_path)
    lineage = read_jsonl(result.lineage_coverage_path)
    assert len(inventory) == len(contract) == len(quality) == len(lineage) >= 13

    inventory_row = next(row for row in inventory if row["data_product_name"] == "gold.data_product_inventory")
    assert inventory_row["environment"] == "local"
    assert inventory_row["business_owner"] == "enterprise-data-platform-po"
    assert inventory_row["technical_owner"] == "senior-data-platform"
    assert inventory_row["quality_profile_id"] == "p0-data-product-control-tower"
    assert inventory_row["active_snapshot_id"] == "control-tower-snapshot"
    assert inventory_row["lifecycle_state"] == "ACTIVE"

    contract_row = next(row for row in contract if row["data_product_name"] == "gold.data_product_inventory")
    assert contract_row["compatibility_status"] == "NOT_ATTACHED"
    assert contract_row["breaking_change_risk"] == "LOW"
    assert contract_row["privacy_policy_passed"] is True
    assert contract_row["highest_severity"] in {"P0", "NONE"}

    quality_row = next(row for row in quality if row["data_product_name"] == "gold.data_product_inventory")
    assert quality_row["release_gate_status"] == "MISSING"
    assert quality_row["sla_status"] in {"RED", "UNKNOWN", "GREEN"}
    assert "assignee" in quality_row

    lineage_row = next(row for row in lineage if row["data_product_name"] == "gold.data_product_inventory")
    assert lineage_row["catalog_publish_status"] == "NOT_ATTACHED"
    assert "missing_lineage_reason" in lineage_row
    assert "owner_action_required" in lineage_row


def test_control_tower_materialized_lineage_uses_catalog_lineage_ops(tmp_path: Path) -> None:
    ops = write_catalog_lineage_ops_report(
        ROOT,
        tmp_path / "catalog-lineage" / "ops.json",
        environment="local",
        generated_at="2026-06-16T11:00:00Z",
    )
    payload = json.loads(ops.output_path.read_text(encoding="utf-8"))
    payload["summary"]["catalog_publish_status"] = "READY"
    payload["summary"]["openlineage_event_count"] = 7
    for row in payload["data_products"]:
        if row["data_product"] == "gold.data_product_inventory":
            row["catalog_publish_status"] = "READY"
            row["runtime_event_count"] = 7
            row["last_runtime_run_id"] = "catalog-lineage-run"
            row["last_runtime_run_at"] = "2026-06-16T10:59:00Z"
    ops.output_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    report_path = tmp_path / "control-tower" / "report.json"
    write_data_product_control_tower_report(
        ROOT,
        report_path,
        catalog_lineage_ops_report_path=ops.output_path,
        generated_at="2026-06-16T11:00:00Z",
    )

    result = run_control_tower_gold_materialization(
        report_path,
        tmp_path / "pipeline",
        snapshot_id="control-tower-snapshot",
        built_at="2026-06-16T11:05:00Z",
    )

    lineage = read_jsonl(result.lineage_coverage_path)
    lineage_row = next(row for row in lineage if row["data_product_name"] == "gold.data_product_inventory")
    assert lineage_row["catalog_publish_status"] == "READY"
    assert lineage_row["openlineage_event_count"] == 7
    assert lineage_row["last_runtime_run_id"] == "catalog-lineage-run"


def test_control_tower_materialized_quality_uses_quality_slo_ops(tmp_path: Path) -> None:
    ops = write_quality_slo_ops_report(
        ROOT,
        tmp_path / "quality-slo" / "ops.json",
        environment="local",
        generated_at="2026-06-16T11:00:00Z",
    )
    payload = json.loads(ops.output_path.read_text(encoding="utf-8"))
    for row in payload["data_products"]:
        if row["data_product"] == "gold.data_product_inventory":
            row["runtime_quality"] = {
                "attached": True,
                "quality_tool": "great_expectations",
                "validation_passed": True,
                "failed_check_count": 0,
                "freshness_status": "GREEN",
                "age_seconds": 180,
                "slo_seconds": 900,
                "quarantine_row_count": 0,
            }
            row["release"] = {
                "attached": True,
                "release_id": "quality-slo-release",
                "release_passed": True,
            }
            row["passed"] = True
            row["risk_state"] = "ok"
    ops.output_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    report_path = tmp_path / "control-tower" / "report.json"
    write_data_product_control_tower_report(
        ROOT,
        report_path,
        quality_slo_ops_report_path=ops.output_path,
        generated_at="2026-06-16T11:00:00Z",
    )

    result = run_control_tower_gold_materialization(
        report_path,
        tmp_path / "pipeline",
        snapshot_id="control-tower-snapshot",
        built_at="2026-06-16T11:05:00Z",
    )

    quality = read_jsonl(result.quality_sla_path)
    quality_row = next(row for row in quality if row["data_product_name"] == "gold.data_product_inventory")
    assert quality_row["freshness_status"] == "GREEN"
    assert quality_row["observed_age_minutes"] == 3
    assert quality_row["quarantine_row_count"] == 0
    assert quality_row["release_gate_status"] == "PASSED"


def test_control_tower_materialization_rejects_wrong_artifact_type(tmp_path: Path) -> None:
    bad_input = tmp_path / "bad.json"
    bad_input.write_text(json.dumps({"artifact_type": "other.v1", "data_products": []}), encoding="utf-8")

    try:
        run_control_tower_gold_materialization(bad_input, tmp_path / "pipeline")
    except ValueError as exc:
        assert "data_product_control_tower_report.v1" in str(exc)
    else:
        raise AssertionError("wrong artifact_type was accepted")


def test_control_tower_use_case_materialization_passes_local_release_gates(tmp_path: Path) -> None:
    report_path = tmp_path / "control-tower" / "report.json"
    write_data_product_control_tower_report(
        ROOT,
        report_path,
        generated_at="2026-06-16T11:00:00Z",
    )
    result = run_use_case(
        ROOT,
        report_path,
        tmp_path / "run",
        use_case_id="data-product-control-tower",
        release_id="control-tower-release",
        environment="local",
        built_at="2026-06-16T11:05:00Z",
        evaluation_time="2026-06-16T11:06:00Z",
        snapshot_id="control-tower-release-snapshot",
    )
    gates = {gate["gate_id"]: gate["passed"] for gate in result.evidence["gates"]}

    assert result.runner_id == "control_tower.materialize_gold.from_report.v1"
    assert result.primary_output == "gold.data_product_inventory"
    assert result.evidence["release_passed"] is True
    assert gates["P0-OUTPUT-EVIDENCE"] is True
    assert gates["P0-QUALITY-PROFILE"] is True
    assert gates["P0-CATALOG-LINEAGE"] is True
    assert result.pipeline.inventory_path.is_file()


def data_product(report: dict[str, object], name: str) -> dict[str, object]:
    return next(item for item in report["data_products"] if item["name"] == name)


def write_catalog_lineage_ops_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "catalog_lineage_ops_report.v1",
) -> Path:
    path = tmp_path / "catalog-lineage-ops" / f"{environment}.json"
    result = write_catalog_lineage_ops_report(
        ROOT,
        path,
        environment=environment,
        generated_at="2026-06-16T12:05:00Z",
    )
    payload = result.report
    payload["artifact_type"] = artifact_type
    payload["passed"] = passed
    payload["readiness_state"] = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    if not passed:
        payload["checks"] = payload["checks"] + [
            {
                "name": "catalog_publish_manifest_passed",
                "passed": False,
                "details": {"passed": False},
            }
        ]
        payload["summary"]["global_failed_check_count"] = int(payload["summary"].get("global_failed_check_count", 0)) + 1
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def write_quality_slo_ops_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "quality_slo_release_gates_ops_report.v1",
) -> Path:
    path = tmp_path / "quality-slo-ops" / f"{environment}.json"
    result = write_quality_slo_ops_report(
        ROOT,
        path,
        environment=environment,
        generated_at="2026-06-16T12:05:00Z",
    )
    payload = result.report
    payload["artifact_type"] = artifact_type
    payload["passed"] = passed
    payload["readiness_state"] = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    if not passed:
        payload["checks"] = payload["checks"] + [
            {
                "name": "release_evidence_attached_for_production_like",
                "passed": False,
                "details": {"release_count": 0},
            }
        ]
        payload["summary"]["global_failed_check_count"] = int(payload["summary"].get("global_failed_check_count", 0)) + 1
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def write_semantic_metric_serving_ops_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "semantic_metric_serving_ops_report.v1",
) -> Path:
    path = tmp_path / "semantic-serving-ops" / f"{environment}.json"
    result = write_semantic_metric_serving_ops_report(
        ROOT,
        path,
        environment=environment,
        generated_at="2026-06-16T12:05:00Z",
    )
    payload = result.report
    payload["artifact_type"] = artifact_type
    payload["passed"] = passed
    payload["readiness_state"] = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    if not passed:
        payload["checks"] = payload["checks"] + [
            {
                "name": "semantic_view_manifest_valid",
                "passed": False,
                "details": {"errors": ["forced failure"]},
            }
        ]
        payload["summary"]["global_failed_check_count"] = int(payload["summary"].get("global_failed_check_count", 0)) + 1
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def write_schema_registry_ops_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "schema_registry_ops_report.v1",
) -> Path:
    path = tmp_path / "schema-registry-ops" / f"{environment}.json"
    result = write_schema_registry_ops_report(
        ROOT,
        path,
        environment=environment,
        generated_at="2026-06-16T12:05:00Z",
    )
    payload = result.report
    payload["artifact_type"] = artifact_type
    payload["passed"] = passed
    payload["readiness_state"] = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    if not passed:
        payload["checks"] = payload["checks"] + [
            {
                "check": "compatibility_report_passed",
                "passed": False,
                "details": {"compatibility_passed": False},
            }
        ]
        payload["summary"]["global_failed_check_count"] = int(payload["summary"].get("global_failed_check_count", 0)) + 1
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def write_catalog_runtime_ops_payload(tmp_path: Path, *, environment: str) -> Path:
    evidence_path = tmp_path / "catalog-runtime-ops" / f"{environment}-evidence.json"
    release_id = f"{environment}-catalog-runtime-release"
    change_ticket = "CHG-DP-CATALOG-20260616"
    warehouse_uri = f"s3://enterprise-dp-{environment}/warehouse"
    service_identity = f"svc-dp-{environment}-table-format"
    upstream_hash = fake_sha256(f"{environment}:trino-iceberg-minio-smoke")
    evidence = {
        "artifact_type": "managed_catalog_runtime_evidence.v1",
        "environment": environment,
        "generated_at": "2026-06-16T12:00:00Z",
        "valid_until": "2026-06-17T12:00:00Z",
        "passed": True,
        "evidence_source": "external_attestation",
        "production_evidence": True,
        "sample": False,
        "redacted": True,
        "release_id": release_id,
        "change_ticket": change_ticket,
        "catalog": {
            "provider": "iceberg-rest",
            "catalog_id": f"dp-{environment}-iceberg-rest",
            "service_id": "table_format",
            "service_identity": service_identity,
            "endpoint_uri": f"https://iceberg-rest.{environment}.dp.example",
            "warehouse_uri": warehouse_uri,
            "metadata_store": "postgresql-ha",
            "catalog_hash": fake_sha256(f"{environment}:catalog-state"),
        },
        "deployment": {
            "replica_count": 3,
            "availability_zones": 3,
            "multi_az": True,
            "health_check_passed": True,
            "managed_service": True,
            "ha_mode": "managed_ha",
        },
        "failover": {
            "failover_tested": True,
            "failover_passed": True,
            "failover_seconds": 45,
            "read_after_failover_passed": True,
            "write_after_failover_passed": True,
        },
        "concurrency": {
            "optimistic_locking": True,
            "concurrent_commit_probe_passed": True,
            "stale_commit_rejected": True,
            "lost_update_prevented": True,
            "latest_snapshot_preserved": True,
            "cross_engine_read_after_conflict_passed": True,
            "conflict_count": 1,
        },
        "backup_restore": {
            "backup_enabled": True,
            "pitr_enabled": True,
            "restore_tested": True,
            "restore_test_passed": True,
            "rpo_minutes": 5,
            "rto_minutes": 30,
        },
        "audit_sink": {
            "sink_uri": f"siem://enterprise/{environment}/catalog-runtime",
            "events_hash": fake_sha256("catalog-runtime-audit-events"),
            "event_count": 19,
            "failed_event_count": 0,
        },
        "attestation": {
            "attached": True,
            "signature_verified": True,
            "subject_hash_matches": True,
            "subject_hash": fake_sha256("catalog-runtime-attestation-subject"),
        },
        "upstream_evidence": [
            {
                "name": "trino_iceberg_minio_smoke",
                "artifact_type": "trino_iceberg_minio_smoke_report.v1",
                "artifact_hash": upstream_hash,
                "passed": True,
            }
        ],
        "binding": {
            "release_id_hash": fake_sha256(release_id),
            "change_ticket_hash": fake_sha256(change_ticket),
            "warehouse_uri_hash": fake_sha256(warehouse_uri),
            "catalog_service_identity_hash": fake_sha256(service_identity),
            "upstream_evidence_hashes": [upstream_hash],
        },
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, sort_keys=True), encoding="utf-8")
    result = write_catalog_runtime_ops_report(
        ROOT,
        tmp_path / "catalog-runtime-ops" / f"{environment}.json",
        environment=environment,
        evidence_path=evidence_path,
        generated_at="2026-06-16T12:05:00Z",
    )
    return result.output_path


def write_orchestration_runtime_ops_payload(tmp_path: Path, *, environment: str) -> Path:
    evidence_path = tmp_path / "orchestration-runtime-ops" / f"{environment}-evidence.json"
    release_id = f"{environment}-orchestration-runtime-release"
    change_ticket = "CHG-DP-ORCH-20260616"
    deployment_id = f"dagster-{environment}-workspace"
    service_identity = f"svc-dp-{environment}-orchestration"
    run_storage_uri = f"postgresql://dagster-run-storage.{environment}.dp.internal/dagster"
    upstream_hash = fake_sha256(f"{environment}:dagster-day2-smoke")
    evidence = {
        "artifact_type": "managed_orchestration_runtime_evidence.v1",
        "environment": environment,
        "generated_at": "2026-06-16T12:00:00Z",
        "valid_until": "2026-06-17T12:00:00Z",
        "passed": True,
        "evidence_source": "external_attestation",
        "production_evidence": True,
        "sample": False,
        "redacted": True,
        "release_id": release_id,
        "change_ticket": change_ticket,
        "source_version": {
            "git_sha": "0123456789abcdef0123456789abcdef01234567",
            "image_digest": fake_sha256(f"{environment}:dagster-image"),
        },
        "orchestrator": {
            "provider": "dagster",
            "service_id": "orchestration",
            "deployment_id": deployment_id,
            "service_identity": service_identity,
            "endpoint_uri": f"https://dagster.{environment}.dp.example",
            "run_history_hash": fake_sha256(f"{environment}:run-history"),
        },
        "deployment": {
            "replica_count": 3,
            "daemon_replica_count": 2,
            "scheduler_replica_count": 2,
            "worker_replica_count": 4,
            "availability_zones": 3,
            "multi_az": True,
            "health_check_passed": True,
            "managed_service": True,
            "ha_mode": "managed_ha",
        },
        "run_launcher": {
            "distributed_executor_enabled": True,
            "kubernetes_run_launcher_enabled": True,
            "isolated_run_workers": True,
            "run_queue_enabled": True,
        },
        "run_storage": {
            "storage_uri": run_storage_uri,
            "managed_run_storage": True,
            "persistent": True,
            "ha_enabled": True,
            "backup_enabled": True,
            "run_history_readback_passed": True,
            "asset_state_readback_passed": True,
        },
        "day2": {
            "schedule_tick_history_passed": True,
            "retry_policy_verified": True,
            "retry_backoff_seconds": 30,
            "backfill_materialization_history_passed": True,
            "production_backfill_scheduler": True,
            "backfill_partition_count": 5,
            "materialization_event_count": 5,
            "worker_restart_recovered": True,
            "failed_run_recovered": True,
        },
        "security": {
            "service_identity_authorized": True,
            "secret_injection_verified": True,
            "raw_secret_material_persisted": False,
            "network_private": True,
        },
        "metrics": {
            "metrics_exported": True,
            "run_failure_alert_configured": True,
            "scheduler_lag_metric_exported": True,
        },
        "audit_sink": {
            "sink_uri": f"siem://enterprise/{environment}/orchestration-runtime",
            "events_hash": fake_sha256("orchestration-runtime-audit-events"),
            "event_count": 37,
            "failed_event_count": 0,
        },
        "attestation": {
            "attached": True,
            "signature_verified": True,
            "subject_hash_matches": True,
            "subject_hash": fake_sha256("orchestration-runtime-attestation-subject"),
        },
        "upstream_evidence": [
            {
                "name": "dagster_day2_smoke",
                "artifact_type": "dagster_day2_smoke_report.v1",
                "artifact_hash": upstream_hash,
                "passed": True,
            }
        ],
        "binding": {
            "release_id_hash": fake_sha256(release_id),
            "change_ticket_hash": fake_sha256(change_ticket),
            "orchestrator_deployment_id_hash": fake_sha256(deployment_id),
            "orchestrator_service_identity_hash": fake_sha256(service_identity),
            "run_storage_uri_hash": fake_sha256(run_storage_uri),
            "upstream_evidence_hashes": [upstream_hash],
        },
    }
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, sort_keys=True), encoding="utf-8")
    result = write_orchestration_runtime_ops_report(
        ROOT,
        tmp_path / "orchestration-runtime-ops" / f"{environment}.json",
        environment=environment,
        evidence_path=evidence_path,
        generated_at="2026-06-16T12:05:00Z",
    )
    return result.output_path


def fake_sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def write_data_plane_smoke_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "data_plane_smoke_report.v1",
) -> Path:
    failed_checks = [] if passed else [{"check": "release_gates", "failed_gates": ["P0-PIPELINE-QUALITY"]}]
    payload = {
        "artifact_type": artifact_type,
        "report_version": 1,
        "capability_id": "local-data-plane-runtime-smoke",
        "report_id": f"data-plane-smoke:{environment}:finance-benefit-reconciliation:test",
        "generated_at": "2026-01-15T09:15:20Z",
        "environment": environment,
        "release_id": "ct-data-plane-smoke-payload",
        "use_case_id": "finance-benefit-reconciliation",
        "runner_id": "finance.benefit_reconciliation.from_approved_bronze.v1",
        "topic": "finance.benefit_settled.v1",
        "primary_output": "gold.finance_benefit_reconciliation",
        "runtime_scope": {
            "mode": "local_ci_jsonl_medallion",
            "covered": ["bronze_approved_quarantine_outputs", "silver_gold_pipeline_outputs", "gold_query_smoke"],
            "not_covered": ["live_kafka_redpanda_broker_flow", "iceberg_table_commit", "trino_or_dremio_sql_runtime_query"],
        },
        "input": {
            "path": "samples/finance/benefit_settled.jsonl",
            "content_hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
            "row_count": 4,
        },
        "output_dir": "build/data-plane-smoke/run",
        "layers": [
            {
                "name": "bronze.events_benefit_settled",
                "path": "build/data-plane-smoke/run/ingestion/bronze/events_benefit_settled.jsonl",
                "exists": passed,
                "manifest_row_count": 4,
                "actual_row_count": 4 if passed else 0,
                "row_count_matches": passed,
                "manifest_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
                "actual_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
                "hash_matches": passed,
                "quality_passed": passed,
                "quality_errors": [] if passed else ["forced failure"],
                "passed": passed,
            }
        ],
        "artifacts": [],
        "release_gates": {"P0-PIPELINE-QUALITY": passed},
        "query_smoke": {
            "passed": passed,
            "query_name": "finance_reconciliation_by_status",
            "row_count": 4 if passed else 0,
            "result_row_count": 2 if passed else 0,
            "result": [] if not passed else [{"reconciliation_status": "MATCHED", "row_count": 1}],
        },
        "summary": {
            "layer_count": 1,
            "artifact_count": 4,
            "release_passed": passed,
            "all_layers_materialized": passed,
            "query_passed": passed,
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
        "passed": passed,
    }
    path = tmp_path / "data-plane-smoke" / f"{environment}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def write_source_activation_ops_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "source_activation_ops_report.v1",
) -> Path:
    payload = {
        "artifact_type": artifact_type,
        "report_version": 1,
        "report_id": f"source-activation-ops-{environment}",
        "generated_at": "2026-06-16T12:00:00Z",
        "environment": environment,
        "ledger": {
            "path": "governance/source-activations.yaml",
            "exists": True,
            "hash": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
            "validation_passed": True,
            "validation_errors": [],
        },
        "source_registry": {
            "current_hash": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
        },
        "active_pointer_dir": "governance/source-active-pointers",
        "summary": {
            "source_count": 1,
            "active_count": 1,
            "revoked_count": 0,
            "unactivated_count": 0,
            "expired_count": 0,
            "expiring_soon_count": 0,
            "critical_issue_count": 0 if passed else 1,
            "pointer_issue_count": 0 if passed else 1,
            "registry_drift_count": 0,
        },
        "decision_board": {
            "critical_sources": [],
            "expiring_sources": [],
            "revoked_sources": [],
            "next_actions": [],
        },
        "sources": [],
        "passed": passed,
    }
    path = tmp_path / "source-activation-ops" / f"{environment}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def write_ingestion_runtime_ops_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "event_cdc_ingestion_runtime_report.v1",
) -> Path:
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    payload = {
        "artifact_type": artifact_type,
        "report_version": 1,
        "report_id": f"ingestion-runtime-{environment}",
        "generated_at": "2026-06-16T12:00:00Z",
        "environment": environment,
        "capability_id": "event-cdc-ingestion-runtime",
        "readiness_state": readiness_state,
        "mode": "local_preflight" if environment == "local" else "runtime_evidence",
        "slo": {
            "lag_slo_records": 1000,
            "lag_slo_seconds": 300,
            "dlt_unresolved_slo": 0,
        },
        "evidence": {
            "attached": environment != "local",
            "uri": None,
            "hash": None,
            "artifact_type": None,
            "generated_at": None,
            "valid_until": None,
            "environment": None,
            "source_kind": None,
        },
        "checks": [] if passed else [{"name": "evidence_attached_for_production_like", "passed": False, "message": "Evidence missing."}],
        "sources": [],
        "decision_board": {
            "p0_failed_sources": [],
            "warning_sources": [],
            "page_now": [],
        },
        "summary": {
            "source_count": 1,
            "p0_source_count": 1,
            "running_connector_count": 1 if passed else 0,
            "p0_failed_source_count": 0,
            "warning_source_count": 0,
            "global_failed_check_count": 0 if passed else 1,
            "by_priority": {"P0": 1},
            "by_risk_state": {"ok": 1} if passed else {"runtime_evidence_missing": 1},
        },
        "passed": passed,
    }
    path = tmp_path / "ingestion-runtime" / f"{environment}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def write_bronze_lakehouse_ops_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "bronze_lakehouse_ops_report.v1",
) -> Path:
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    payload = {
        "artifact_type": artifact_type,
        "report_version": 1,
        "report_id": f"bronze-lakehouse-{environment}",
        "generated_at": "2026-06-16T12:00:00Z",
        "environment": environment,
        "capability_id": "bronze-lakehouse-evidence",
        "readiness_state": readiness_state,
        "mode": "local_preflight" if environment == "local" else "runtime_evidence",
        "inputs": {
            "offset_ledgers": [],
            "maintenance_evidence": {"attached": False},
        },
        "checks": [] if passed else [{"name": "maintenance_evidence_attached_for_production_like", "passed": False}],
        "tables": [],
        "decision_board": {
            "p0_failed_tables": [],
            "warning_tables": [],
            "page_now": [],
        },
        "summary": {
            "source_count": 1,
            "p0_source_count": 1,
            "ledger_attached_count": 1 if passed else 0,
            "maintenance_attached_count": 1 if passed else 0,
            "p0_failed_table_count": 0,
            "warning_table_count": 0,
            "global_failed_check_count": 0 if passed else 1,
            "by_priority": {"P0": 1},
            "by_risk_state": {"ok": 1} if passed else {"maintenance_evidence_missing": 1},
        },
        "passed": passed,
    }
    path = tmp_path / "bronze-lakehouse-ops" / f"{environment}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def write_silver_gold_publication_ops_payload(
    tmp_path: Path,
    *,
    environment: str,
    passed: bool,
    artifact_type: str = "silver_gold_publication_ops_report.v1",
) -> Path:
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    payload = {
        "artifact_type": artifact_type,
        "report_version": 1,
        "report_id": f"publication-{environment}",
        "generated_at": "2026-06-16T12:00:00Z",
        "environment": environment,
        "capability_id": "silver-gold-publication",
        "readiness_state": readiness_state,
        "mode": "local_preflight" if environment == "local" else "runtime_evidence",
        "inputs": {
            "release_evidence": [],
            "promotion_manifests": [],
            "activation_manifests": [],
            "active_pointers": [],
        },
        "checks": [] if passed else [{"name": "release_evidence_attached_for_production_like", "passed": False}],
        "data_products": [],
        "decision_board": {
            "failed_products": [],
            "page_now": [],
        },
        "summary": {
            "data_product_count": 1,
            "failed_product_count": 0,
            "global_failed_check_count": 0 if passed else 1,
            "release_attached_count": 1 if passed else 0,
            "promotion_attached_count": 1 if passed else 0,
            "activation_attached_count": 1 if passed else 0,
            "active_pointer_attached_count": 1 if passed else 0,
            "by_risk_state": {"ok": 1} if passed else {"release_evidence_missing": 1},
        },
        "passed": passed,
    }
    path = tmp_path / "publication-ops" / f"{environment}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
