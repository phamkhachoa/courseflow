from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from botocore.exceptions import ClientError
import yaml

from enterprise_dp.attestations import write_schema_registry_publication_attestation
from enterprise_dp.catalog import hash_file, write_catalog_bundle
from enterprise_dp.catalog_lineage_ops import write_catalog_lineage_ops_report
from enterprise_dp.catalog_publish import write_catalog_publish_manifest
from enterprise_dp.catalog_runtime_ops import write_catalog_runtime_ops_report
from enterprise_dp.event_backbone_smoke import CommandResult, write_event_backbone_smoke_report
from enterprise_dp.environments import REQUIRED_P0_SERVICES
from enterprise_dp.dagster_day2_smoke import write_dagster_day2_smoke_report
from enterprise_dp.dagster_orchestration_smoke import write_dagster_orchestration_smoke_report
from enterprise_dp.iceberg_catalog_smoke import write_iceberg_catalog_smoke_report
from enterprise_dp.live_lakehouse_smoke import write_live_lakehouse_smoke_report
from enterprise_dp.object_store_smoke import write_object_store_commit_smoke_report
from enterprise_dp.oidc_auth_smoke import write_oidc_auth_smoke_report
from enterprise_dp.openlineage import write_openlineage_events
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.orchestration_runtime_ops import write_orchestration_runtime_ops_report
from enterprise_dp.pipelines import run_recommendation_pipeline_from_bronze
from enterprise_dp.portfolio_release_smoke import write_portfolio_release_smoke_report
from enterprise_dp.production_review_pack import write_production_review_pack
from enterprise_dp.runtime import write_runtime_iac_evidence_pack, write_runtime_readiness_report
from enterprise_dp.secret_rotation_smoke import write_secret_rotation_smoke_report
from enterprise_dp.semantic_metric_certification import write_semantic_metric_certification_report
from enterprise_dp.semantic_serving_ops import write_semantic_metric_serving_ops_report
from enterprise_dp.semantic_views import write_semantic_view_manifest
from enterprise_dp.trino_sql_smoke import (
    CommandResult as TrinoCommandResult,
    write_trino_sql_runtime_smoke_report,
)
from enterprise_dp.trino_iceberg_minio_smoke import write_trino_iceberg_minio_smoke_report
from enterprise_dp.trino_runtime_security_smoke import write_trino_runtime_security_smoke_report


ROOT = Path(__file__).resolve().parents[1]


def test_production_review_pack_writes_partner_review_artifacts(tmp_path: Path) -> None:
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest["artifacts"]

    assert manifest == result.manifest
    assert manifest["artifact_type"] == "production_review_pack.v1"
    assert manifest["verdict"]["partner_review_ready"] is True
    assert manifest["verdict"]["production_ready"] is False
    assert manifest["verdict"]["code_control_plane_ready_excluding_live_infra"] is False
    assert manifest["verdict"]["readiness_state"] == "not_ready"
    assert manifest["summary"]["data_plane_smoke_passed"] is True
    assert manifest["summary"]["data_plane_smoke_blocker_count"] == 0
    assert manifest["summary"]["event_backbone_smoke_attached"] is False
    assert manifest["summary"]["event_backbone_smoke_passed"] is None
    assert manifest["summary"]["ingestion_runtime_attached"] is False
    assert manifest["summary"]["ingestion_runtime_passed"] is None
    assert manifest["summary"]["catalog_lineage_ops_attached"] is False
    assert manifest["summary"]["catalog_lineage_ops_passed"] is None
    assert manifest["summary"]["catalog_lineage_release_gate_passed"] is False
    assert manifest["summary"]["semantic_metric_serving_ops_attached"] is False
    assert manifest["summary"]["semantic_metric_serving_ops_passed"] is None
    assert manifest["summary"]["semantic_metric_serving_release_gate_passed"] is False
    assert manifest["summary"]["source_activation_ops_attached"] is False
    assert manifest["summary"]["source_activation_ops_passed"] is None
    assert manifest["summary"]["source_onboarding_release_gate_passed"] is False
    assert manifest["summary"]["runtime_readiness_external_attached"] is False
    assert manifest["summary"]["runtime_iac_release_gate_passed"] is False
    assert manifest["summary"]["schema_registry_runtime_smoke_attached"] is False
    assert manifest["summary"]["schema_registry_runtime_smoke_passed"] is None
    assert manifest["summary"]["schema_registry_attestation_attached"] is False
    assert manifest["summary"]["schema_registry_attestation_passed"] is None
    assert manifest["summary"]["schema_registry_ops_attached"] is False
    assert manifest["summary"]["schema_registry_ops_passed"] is None
    assert manifest["summary"]["schema_registry_release_gate_passed"] is False
    assert manifest["summary"]["schema_registry_auth_smoke_attached"] is False
    assert manifest["summary"]["schema_registry_auth_smoke_passed"] is None
    assert manifest["summary"]["schema_registry_storage_smoke_attached"] is False
    assert manifest["summary"]["schema_registry_storage_smoke_passed"] is None
    assert manifest["summary"]["broker_acl_smoke_attached"] is False
    assert manifest["summary"]["broker_acl_smoke_passed"] is None
    assert manifest["summary"]["transactional_outbox_smoke_attached"] is False
    assert manifest["summary"]["transactional_outbox_smoke_passed"] is None
    assert manifest["summary"]["live_bronze_ingestion_smoke_attached"] is False
    assert manifest["summary"]["live_bronze_ingestion_smoke_passed"] is None
    assert manifest["summary"]["orchestrated_publication_smoke_attached"] is False
    assert manifest["summary"]["orchestrated_publication_smoke_passed"] is None
    assert manifest["summary"]["live_quality_slo_smoke_attached"] is False
    assert manifest["summary"]["live_quality_slo_smoke_passed"] is None
    assert manifest["summary"]["live_lakehouse_smoke_attached"] is False
    assert manifest["summary"]["live_lakehouse_smoke_passed"] is None
    assert manifest["summary"]["iceberg_catalog_smoke_attached"] is False
    assert manifest["summary"]["iceberg_catalog_smoke_passed"] is None
    assert manifest["summary"]["object_store_smoke_attached"] is False
    assert manifest["summary"]["object_store_smoke_passed"] is None
    assert manifest["summary"]["trino_sql_smoke_attached"] is False
    assert manifest["summary"]["trino_sql_smoke_passed"] is None
    assert manifest["summary"]["trino_iceberg_minio_smoke_attached"] is False
    assert manifest["summary"]["trino_iceberg_minio_smoke_passed"] is None
    assert manifest["summary"]["catalog_cross_engine_smoke_attached"] is False
    assert manifest["summary"]["catalog_cross_engine_smoke_passed"] is None
    assert manifest["summary"]["trino_runtime_security_smoke_attached"] is False
    assert manifest["summary"]["trino_runtime_security_smoke_passed"] is None
    assert manifest["summary"]["policy_decision_smoke_attached"] is False
    assert manifest["summary"]["policy_decision_smoke_passed"] is None
    assert manifest["summary"]["oidc_auth_smoke_attached"] is False
    assert manifest["summary"]["oidc_auth_smoke_passed"] is None
    assert manifest["summary"]["access_privacy_release_gate_passed"] is False
    assert manifest["summary"]["secret_rotation_smoke_attached"] is False
    assert manifest["summary"]["secret_rotation_smoke_passed"] is None
    assert manifest["summary"]["secret_rotation_ops_attached"] is False
    assert manifest["summary"]["secret_rotation_ops_passed"] is None
    assert manifest["summary"]["secret_rotation_ops_release_gate_passed"] is False
    assert manifest["summary"]["dagster_orchestration_smoke_attached"] is False
    assert manifest["summary"]["dagster_orchestration_smoke_passed"] is None
    assert manifest["summary"]["dagster_day2_smoke_attached"] is False
    assert manifest["summary"]["dagster_day2_smoke_passed"] is None
    assert manifest["summary"]["dagster_day2_release_gate_passed"] is False
    assert manifest["summary"]["portfolio_release_smoke_attached"] is False
    assert manifest["summary"]["portfolio_release_smoke_passed"] is None
    assert manifest["summary"]["workload_benchmark_attached"] is False
    assert manifest["summary"]["workload_benchmark_passed"] is None
    assert manifest["summary"]["workload_benchmark_release_gate_passed"] is False
    assert manifest["summary"]["control_tower_blocker_count"] > 0
    assert "live_kafka_redpanda_broker_flow" in manifest["summary"]["data_plane_smoke_not_covered"]
    assert len(manifest["p0_gap_backlog"]) > 0
    assert artifacts["event_backbone_smoke"]["attached"] is False
    assert artifacts["ingestion_runtime"]["attached"] is False
    assert artifacts["catalog_lineage_ops"]["attached"] is False
    assert artifacts["semantic_metric_serving_ops"]["attached"] is False
    assert artifacts["source_activation_ops"]["attached"] is False
    assert artifacts["schema_registry_runtime_smoke"]["attached"] is False
    assert artifacts["schema_registry_attestation"]["attached"] is False
    assert artifacts["schema_registry_auth_smoke"]["attached"] is False
    assert artifacts["schema_registry_storage_smoke"]["attached"] is False
    assert artifacts["broker_acl_smoke"]["attached"] is False
    assert artifacts["transactional_outbox_smoke"]["attached"] is False
    assert artifacts["live_bronze_ingestion_smoke"]["attached"] is False
    assert artifacts["orchestrated_publication_smoke"]["attached"] is False
    assert artifacts["live_quality_slo_smoke"]["attached"] is False
    assert artifacts["live_lakehouse_smoke"]["attached"] is False
    assert artifacts["iceberg_catalog_smoke"]["attached"] is False
    assert artifacts["object_store_commit_smoke"]["attached"] is False
    assert artifacts["trino_sql_runtime_smoke"]["attached"] is False
    assert artifacts["trino_iceberg_minio_smoke"]["attached"] is False
    assert artifacts["catalog_cross_engine_smoke"]["attached"] is False
    assert artifacts["trino_runtime_security_smoke"]["attached"] is False
    assert artifacts["policy_decision_smoke"]["attached"] is False
    assert artifacts["oidc_auth_smoke"]["attached"] is False
    assert artifacts["secret_rotation_smoke"]["attached"] is False
    assert artifacts["secret_rotation_ops"]["attached"] is False
    assert artifacts["dagster_orchestration_smoke"]["attached"] is False
    assert artifacts["dagster_day2_smoke"]["attached"] is False
    assert artifacts["portfolio_release_smoke"]["attached"] is False
    assert any(item["gap"] == "portfolio_release_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "event_backbone_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "ingestion_runtime_report_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "schema_registry_runtime_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "live_lakehouse_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "iceberg_catalog_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "object_store_commit_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "trino_sql_runtime_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "trino_iceberg_minio_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "live_bronze_ingestion_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "orchestrated_publication_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "live_quality_slo_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "trino_runtime_security_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "dagster_orchestration_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "workload_benchmark_report_not_attached" for item in manifest["p0_gap_backlog"])
    assert any(item["source"] == "control_tower_blocker" for item in manifest["p0_gap_backlog"])
    assert Path(artifacts["data_plane_smoke"]["uri"]).is_file()
    assert Path(artifacts["runtime_readiness"]["uri"]).is_file()
    assert Path(artifacts["capability_maturity"]["uri"]).is_file()
    assert Path(artifacts["control_tower"]["uri"]).is_file()


def test_production_review_pack_accepts_managed_workload_benchmark_evidence(tmp_path: Path) -> None:
    benchmark_path = write_workload_benchmark_report(tmp_path / "workload-benchmark.json", environment="staging")
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="staging",
        generated_at="2026-06-16T12:05:00Z",
        workload_benchmark_report_path=benchmark_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["artifacts"]["workload_benchmark"]["attached"] is True
    assert summary["workload_benchmark_attached"] is True
    assert summary["workload_benchmark_passed"] is True
    assert summary["workload_benchmark_release_gate_passed"] is True
    assert summary["workload_benchmark_environment"] == "staging"
    assert summary["workload_benchmark_input_record_count"] == 1_500_000
    assert "workload_benchmark_report_not_attached" not in gap_names
    assert "workload_benchmark_release_gate_failed" not in gap_names


def test_production_review_pack_rejects_synthetic_or_under_scale_benchmark(tmp_path: Path) -> None:
    benchmark_path = write_workload_benchmark_report(
        tmp_path / "workload-benchmark.json",
        environment="staging",
        source_kind="synthetic_fixture",
        input_record_count=10_000,
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="staging",
        generated_at="2026-06-16T12:05:00Z",
        workload_benchmark_report_path=benchmark_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["summary"]["workload_benchmark_attached"] is True
    assert manifest["summary"]["workload_benchmark_release_gate_passed"] is False
    assert any(item["gap"] == "workload_benchmark_release_gate_failed" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_failed_event_backbone_smoke_report(tmp_path: Path) -> None:
    def failing_runner(args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        return CommandResult(tuple(args), 1, "", "Cannot connect to the Docker daemon")

    event_result = write_event_backbone_smoke_report(
        ROOT,
        tmp_path / "event-backbone-smoke-report.json",
        output_dir=tmp_path / "event-backbone-run",
        release_id="event-backbone-smoke-fail",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=failing_runner,
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        event_backbone_smoke_report_path=event_result.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    event_artifact = manifest["artifacts"]["event_backbone_smoke"]

    assert event_artifact["attached"] is True
    assert event_artifact["artifact_type"] == "event_backbone_smoke_report.v1"
    assert event_artifact["passed"] is False
    assert manifest["summary"]["event_backbone_smoke_attached"] is True
    assert manifest["summary"]["event_backbone_smoke_passed"] is False
    assert manifest["summary"]["event_backbone_smoke_failed_check_count"] == 1
    assert manifest["summary"]["event_backbone_smoke_source_record_count"] == 4
    assert manifest["summary"]["event_backbone_smoke_consumed_record_count"] == 0
    assert manifest["summary"]["ingestion_runtime_attached"] is False
    assert manifest["summary"]["ingestion_runtime_passed"] is None
    assert any(item["gap"] == "event_backbone_smoke_failed" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "ingestion_runtime_report_not_attached" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_passing_event_backbone_smoke_report(tmp_path: Path) -> None:
    produced_by_topic: dict[str, str] = {}

    def passing_runner(args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        if args[-1] == "redpanda":
            return CommandResult(tuple(args), 0, "started", "")
        if "create" in args:
            return CommandResult(tuple(args), 0, "created", "")
        if "produce" in args:
            assert input_text is not None
            produced_by_topic[args[-1]] = input_text
            return CommandResult(tuple(args), 0, "produced", "")
        if "consume" in args:
            topic = args[args.index("consume") + 1]
            return CommandResult(tuple(args), 0, produced_by_topic[topic], "")
        if "group" in args and "describe" in args:
            group = args[-1]
            topic = group.removesuffix(".group")
            return CommandResult(tuple(args), 0, fake_event_backbone_group_describe(topic), "")
        raise AssertionError(f"unexpected command: {args}")

    event_result = write_event_backbone_smoke_report(
        ROOT,
        tmp_path / "event-backbone-smoke-report.json",
        output_dir=tmp_path / "event-backbone-run",
        release_id="event-backbone-smoke-pass",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=passing_runner,
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        event_backbone_smoke_report_path=event_result.output_path,
        ingestion_runtime_report_path=event_result.report["ingestion_runtime"]["path"],
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["summary"]["event_backbone_smoke_attached"] is True
    assert manifest["summary"]["event_backbone_smoke_passed"] is True
    assert manifest["summary"]["ingestion_runtime_attached"] is True
    assert manifest["summary"]["ingestion_runtime_passed"] is True
    assert manifest["summary"]["ingestion_runtime_mode"] == "runtime_evidence"
    assert manifest["summary"]["ingestion_runtime_p0_source_count"] == 8
    assert manifest["summary"]["ingestion_runtime_running_connector_count"] == 8
    assert manifest["summary"]["event_backbone_smoke_multi_partition_rebalance_passed"] is True
    assert manifest["summary"]["event_backbone_smoke_multi_partition_topic_partition_count"] == 3
    assert manifest["summary"]["event_backbone_smoke_multi_partition_group_total_lag"] == 0
    assert manifest["artifacts"]["ingestion_runtime"]["attached"] is True
    assert manifest["artifacts"]["ingestion_runtime"]["artifact_type"] == "event_cdc_ingestion_runtime_report.v1"
    assert not any(item["gap"] == "event_backbone_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "ingestion_runtime_report_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "live_kafka_redpanda_broker_flow" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "ingestion_runtime_p0_coverage_incomplete" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "multi_partition_rebalance" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "debezium_or_transactional_outbox_source_connector" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "broker_acl_enforcement" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_broker_acl_smoke_report(tmp_path: Path) -> None:
    event_path = write_json_artifact(
        tmp_path / "event-backbone-smoke-report.json",
        {
            "artifact_type": "event_backbone_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "debezium_or_transactional_outbox_source_connector",
                    "broker_acl_enforcement",
                    "multi_partition_rebalance",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "source_record_count": 4,
                "consumed_record_count": 4,
            },
        },
    )
    broker_path = write_json_artifact(
        tmp_path / "broker-acl-smoke-report.json",
        {
            "artifact_type": "broker_acl_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_mtls_listener",
                    "production_secret_rotation",
                    "production_broker_audit_log_export",
                ]
            },
            "summary": {
                "broker_acl_enforced": True,
                "allowed_user_can_produce": True,
                "denied_user_blocked": True,
                "authorization_denied_verified": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        event_backbone_smoke_report_path=event_path,
        broker_acl_smoke_report_path=broker_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["broker_acl_smoke"]["attached"] is True
    assert manifest["artifacts"]["broker_acl_smoke"]["artifact_type"] == "broker_acl_smoke_report.v1"
    assert summary["broker_acl_smoke_attached"] is True
    assert summary["broker_acl_smoke_passed"] is True
    assert summary["broker_acl_smoke_broker_acl_enforced"] is True
    assert summary["broker_acl_smoke_allowed_user_can_produce"] is True
    assert summary["broker_acl_smoke_denied_user_blocked"] is True
    assert summary["broker_acl_smoke_authorization_denied_verified"] is True
    assert summary["broker_acl_smoke_failed_check_count"] == 0
    assert "production_secret_rotation" in summary["broker_acl_smoke_not_covered"]
    assert not any(item["gap"] == "broker_acl_enforcement" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "debezium_or_transactional_outbox_source_connector" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_transactional_outbox_smoke_report(tmp_path: Path) -> None:
    event_path = write_json_artifact(
        tmp_path / "event-backbone-smoke-report.json",
        {
            "artifact_type": "event_backbone_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "debezium_or_transactional_outbox_source_connector",
                    "broker_acl_enforcement",
                    "multi_partition_rebalance",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "source_record_count": 4,
                "consumed_record_count": 4,
                "multi_partition_rebalance_passed": True,
            },
        },
    )
    outbox_path = write_json_artifact(
        tmp_path / "transactional-outbox-smoke-report.json",
        {
            "artifact_type": "transactional_outbox_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_debezium_connector_runtime",
                    "production_connector_ha",
                    "production_outbox_relay_deployment",
                    "production_connector_secret_rotation",
                ]
            },
            "summary": {
                "transactional_outbox_to_bronze_passed": True,
                "source_type": "transactional_outbox",
                "connector_record_count": 4,
                "consumed_record_count": 4,
                "bronze_approved_new_row_count": 4,
                "bronze_quarantine_row_count": 0,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        event_backbone_smoke_report_path=event_path,
        transactional_outbox_smoke_report_path=outbox_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["transactional_outbox_smoke"]["attached"] is True
    assert manifest["artifacts"]["transactional_outbox_smoke"]["artifact_type"] == "transactional_outbox_smoke_report.v1"
    assert summary["transactional_outbox_smoke_attached"] is True
    assert summary["transactional_outbox_smoke_passed"] is True
    assert summary["transactional_outbox_smoke_to_bronze_passed"] is True
    assert summary["transactional_outbox_smoke_source_type"] == "transactional_outbox"
    assert summary["transactional_outbox_smoke_connector_record_count"] == 4
    assert summary["transactional_outbox_smoke_consumed_record_count"] == 4
    assert summary["transactional_outbox_smoke_bronze_approved_new_row_count"] == 4
    assert summary["transactional_outbox_smoke_bronze_quarantine_row_count"] == 0
    assert summary["transactional_outbox_smoke_failed_check_count"] == 0
    assert "production_debezium_connector_runtime" in summary["transactional_outbox_smoke_not_covered"]
    assert not any(
        item["gap"] == "debezium_or_transactional_outbox_source_connector"
        for item in manifest["p0_gap_backlog"]
    )
    assert any(item["gap"] == "broker_acl_enforcement" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_uses_live_bronze_ingestion_for_runtime_capability_gaps(
    tmp_path: Path,
) -> None:
    live_bronze_path = write_json_artifact(
        tmp_path / "live-bronze-ingestion-smoke-report.json",
        {
            "artifact_type": "live_bronze_ingestion_runtime_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_kafka_connect_or_debezium_worker",
                    "production_connector_ha",
                    "production_catalog_ha",
                ]
            },
            "summary": {
                "source_id": "enterprise-commerce-benefit-settled-outbox",
                "topic": "finance.benefit_settled.v1",
                "runtime_topic": "dp.local.live.bronze.test",
                "bronze_target": "bronze.events_benefit_settled",
                "iceberg_table": "iceberg.bronze_runtime_smoke.events_benefit_settled",
                "source_record_count": 4,
                "consumed_record_count": 6,
                "approved_row_count": 4,
                "duplicate_skipped_count": 1,
                "quarantine_row_count": 1,
                "snapshot_count_after": 2,
                "restart_resume_passed": True,
                "dlt_quarantine_passed": True,
                "live_bronze_iceberg_sink_passed": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_bronze_ingestion_smoke_report_path=live_bronze_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert manifest["artifacts"]["live_bronze_ingestion_smoke"]["attached"] is True
    assert manifest["artifacts"]["live_bronze_ingestion_smoke"]["artifact_type"] == "live_bronze_ingestion_runtime_report.v1"
    assert summary["live_bronze_ingestion_smoke_attached"] is True
    assert summary["live_bronze_ingestion_smoke_passed"] is True
    assert summary["live_bronze_ingestion_smoke_approved_row_count"] == 4
    assert summary["live_bronze_ingestion_smoke_duplicate_skipped_count"] == 1
    assert summary["live_bronze_ingestion_smoke_quarantine_row_count"] == 1
    assert summary["live_bronze_ingestion_smoke_restart_resume_passed"] is True
    assert "event-cdc-ingestion-runtime" not in blocker_capabilities
    assert "bronze-lakehouse-evidence" not in blocker_capabilities
    assert "source-onboarding" in blocker_capabilities
    assert any(item["gap"] == "live_lakehouse_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "live_bronze_ingestion_smoke_failed" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_uses_orchestrated_publication_for_silver_gold_capability_gap(
    tmp_path: Path,
) -> None:
    orchestrated_publication_path = write_json_artifact(
        tmp_path / "orchestrated-publication-smoke-report.json",
        {
            "artifact_type": "orchestrated_live_publication_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "capability_ids": ["silver-gold-publication"],
            "runtime_scope": {
                "mode": "local_dagster_in_process_bronze_iceberg_to_silver_gold_publication",
                "not_covered": [
                    "dagster_daemon_or_schedule_tick_history",
                    "distributed_executor_or_kubernetes_run_launcher",
                    "production_retry_backoff_runtime_policy",
                    "production_backfill_materialization_history",
                    "production_catalog_ha",
                    "production_catalog_concurrency_locking",
                    "production_secret_rotation",
                ],
            },
            "summary": {
                "bronze_row_count": 4,
                "silver_row_count": 4,
                "gold_row_count": 4,
                "trino_silver_row_count": 4,
                "trino_gold_row_count": 4,
                "promotion_passed": True,
                "activation_passed": True,
                "publication_ops_passed": True,
                "active_pointer_drift_negative_test_passed": True,
                "dagster_retry_event_count": 1,
                "asset_materialization_count": 2,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        orchestrated_publication_smoke_report_path=orchestrated_publication_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["artifacts"]["orchestrated_publication_smoke"]["attached"] is True
    assert (
        manifest["artifacts"]["orchestrated_publication_smoke"]["artifact_type"]
        == "orchestrated_live_publication_report.v1"
    )
    assert summary["orchestrated_publication_smoke_attached"] is True
    assert summary["orchestrated_publication_smoke_passed"] is True
    assert summary["orchestrated_publication_smoke_silver_row_count"] == 4
    assert summary["orchestrated_publication_smoke_gold_row_count"] == 4
    assert summary["orchestrated_publication_smoke_publication_ops_passed"] is True
    assert summary["orchestrated_publication_smoke_active_pointer_drift_negative_test_passed"] is True
    assert "silver-gold-publication" not in blocker_capabilities
    assert "orchestrated_publication_smoke_not_attached" not in gap_names
    assert "orchestrated_publication_smoke_failed" not in gap_names
    assert "event-cdc-ingestion-runtime" in blocker_capabilities
    assert "dagster_orchestration_smoke_not_attached" in gap_names
    assert "dagster_or_airflow_run_history" in gap_names


def test_production_review_pack_uses_live_quality_slo_for_quality_gate_capability_gap(
    tmp_path: Path,
) -> None:
    live_quality_slo_path = write_json_artifact(
        tmp_path / "live-quality-slo-smoke-report.json",
        {
            "artifact_type": "live_quality_slo_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "capability_ids": ["quality-slo-release-gates"],
            "runtime_scope": {
                "mode": "local_trino_iceberg_quality_slo_gate",
                "not_covered": [
                    "managed_great_expectations_or_soda_runner",
                    "production_alertmanager_or_pagerduty_route",
                    "multi_product_runtime_quality_rollout",
                    "production_slo_burn_rate_monitoring",
                ],
            },
            "summary": {
                "target_data_product": "gold.finance_benefit_reconciliation",
                "gold_row_count": 4,
                "quality_runtime_passed": True,
                "quality_runtime_failed_check_count": 0,
                "freshness_breach_count": 0,
                "slo_alert_passed": True,
                "quality_slo_ops_passed": True,
                "quality_slo_ops_failed_product_count": 0,
                "quality_slo_ops_global_failed_check_count": 0,
                "corrupt_gold_null_negative_test_passed": True,
                "stale_freshness_negative_test_passed": True,
                "red_alert_negative_test_passed": True,
                "environment_mismatch_negative_test_passed": True,
                "missing_alert_production_like_negative_test_passed": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_quality_slo_smoke_report_path=live_quality_slo_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["artifacts"]["live_quality_slo_smoke"]["attached"] is True
    assert manifest["artifacts"]["live_quality_slo_smoke"]["artifact_type"] == "live_quality_slo_smoke_report.v1"
    assert summary["live_quality_slo_smoke_attached"] is True
    assert summary["live_quality_slo_smoke_passed"] is True
    assert summary["live_quality_slo_smoke_target_data_product"] == "gold.finance_benefit_reconciliation"
    assert summary["live_quality_slo_smoke_gold_row_count"] == 4
    assert summary["live_quality_slo_smoke_quality_runtime_passed"] is True
    assert summary["live_quality_slo_smoke_slo_alert_passed"] is True
    assert summary["live_quality_slo_smoke_quality_slo_ops_passed"] is True
    assert summary["live_quality_slo_smoke_corrupt_gold_null_negative_test_passed"] is True
    assert summary["live_quality_slo_smoke_stale_freshness_negative_test_passed"] is True
    assert summary["live_quality_slo_smoke_red_alert_negative_test_passed"] is True
    assert summary["live_quality_slo_smoke_environment_mismatch_negative_test_passed"] is True
    assert summary["live_quality_slo_smoke_missing_alert_production_like_negative_test_passed"] is True
    assert summary["live_quality_slo_smoke_failed_check_count"] == 0
    assert "production_alertmanager_or_pagerduty_route" in summary["live_quality_slo_smoke_not_covered"]
    assert "quality-slo-release-gates" not in blocker_capabilities
    assert "live_quality_slo_smoke_not_attached" not in gap_names
    assert "live_quality_slo_smoke_failed" not in gap_names
    assert "event-cdc-ingestion-runtime" in blocker_capabilities
    assert "orchestrated_publication_smoke_not_attached" in gap_names


def test_production_review_pack_attaches_portfolio_release_smoke_report(tmp_path: Path) -> None:
    portfolio = write_portfolio_release_smoke_report(
        ROOT,
        tmp_path / "portfolio-release-smoke-report.json",
        output_dir=tmp_path / "portfolio-run",
        generated_at="2026-06-16T12:10:00Z",
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        portfolio_release_smoke_report_path=portfolio.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["portfolio_release_smoke"]["attached"] is True
    assert summary["portfolio_release_smoke_attached"] is True
    assert summary["portfolio_release_smoke_passed"] is True
    assert summary["portfolio_release_smoke_release_evidence_count"] == 8
    assert summary["portfolio_release_smoke_covered_gold_count"] == 12
    assert summary["portfolio_release_smoke_gold_count"] == 12
    assert summary["portfolio_release_smoke_source_activation_count"] == 7
    assert summary["portfolio_release_smoke_source_activation_passed_count"] == 7
    assert summary["portfolio_release_smoke_source_activation_ops_passed"] is True
    assert summary["portfolio_release_smoke_final_source_activation_blocker_count"] == 0
    assert summary["control_tower_blocker_count"] == 11
    assert summary["non_infra_control_tower_blocker_count"] == 0
    assert summary["live_infra_or_capability_blocker_count"] == 11
    assert manifest["verdict"]["code_control_plane_ready_excluding_live_infra"] is True
    assert not any(item["gap"] == "portfolio_release_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(
        item["gap"] == "gold_release_evidence_passed"
        for item in manifest["p0_gap_backlog"]
        if item.get("source") == "control_tower_blocker"
    )
    assert not any(
        item["gap"] == "runtime_lineage_evidence_present"
        for item in manifest["p0_gap_backlog"]
        if item.get("source") == "control_tower_blocker"
    )
    assert not any(
        item["gap"] == "serving_access_grant_requirements_passed"
        for item in manifest["p0_gap_backlog"]
        if item.get("source") == "control_tower_blocker"
    )
    assert not any(
        item["gap"] == "source_activation_ops_p0_clear"
        for item in manifest["p0_gap_backlog"]
        if item.get("source") == "control_tower_blocker"
    )
    assert not any(
        item["gap"] == "contract_active"
        for item in manifest["p0_gap_backlog"]
        if item.get("source") == "control_tower_blocker"
    )


def test_production_review_pack_attaches_live_lakehouse_smoke_report(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live-lakehouse-run",
        release_id="live-lakehouse-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_lakehouse_smoke_report_path=live.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["live_lakehouse_smoke"]["attached"] is True
    assert manifest["artifacts"]["live_lakehouse_smoke"]["artifact_type"] == "live_lakehouse_smoke_report.v1"
    assert summary["live_lakehouse_smoke_attached"] is True
    assert summary["live_lakehouse_smoke_passed"] is True
    assert summary["live_lakehouse_smoke_table_count"] == 3
    assert summary["live_lakehouse_smoke_parquet_commit_passed_count"] == 3
    assert summary["live_lakehouse_smoke_query_engine"] == "duckdb"
    assert summary["live_lakehouse_smoke_query_passed"] is True
    assert "iceberg_catalog_commit" in summary["live_lakehouse_smoke_not_covered"]
    assert not any(item["gap"] == "live_lakehouse_smoke_not_attached" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_iceberg_catalog_smoke_report(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live-lakehouse-run",
        release_id="iceberg-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
    )
    iceberg = write_iceberg_catalog_smoke_report(
        ROOT,
        tmp_path / "iceberg-catalog-smoke-report.json",
        output_dir=tmp_path / "iceberg-run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="iceberg-review-pack",
        generated_at="2026-01-15T09:15:20Z",
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_lakehouse_smoke_report_path=live.output_path,
        iceberg_catalog_smoke_report_path=iceberg.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["iceberg_catalog_smoke"]["attached"] is True
    assert manifest["artifacts"]["iceberg_catalog_smoke"]["artifact_type"] == "iceberg_catalog_smoke_report.v1"
    assert summary["iceberg_catalog_smoke_attached"] is True
    assert summary["iceberg_catalog_smoke_passed"] is True
    assert summary["iceberg_catalog_smoke_table_count"] == 3
    assert summary["iceberg_catalog_smoke_snapshot_commit_count"] == 3
    assert summary["iceberg_catalog_smoke_readback_passed_count"] == 3
    assert "trino_iceberg_connector" in summary["iceberg_catalog_smoke_not_covered"]
    assert not any(item["gap"] == "iceberg_catalog_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "iceberg_catalog_commit" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "iceberg_table_commit" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "minio_object_store_iceberg_warehouse" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_object_store_smoke_report(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live-lakehouse-run",
        release_id="object-store-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
    )
    object_store = write_object_store_commit_smoke_report(
        ROOT,
        tmp_path / "object-store-commit-smoke-report.json",
        output_dir=tmp_path / "object-store-run",
        live_lakehouse_smoke_report_path=live.output_path,
        bucket="enterprise-dp-review-pack",
        endpoint_url="http://fake-minio.local",
        release_id="object-store-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        s3_client_override=ReviewPackFakeS3(tmp_path / "fake-s3"),
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_lakehouse_smoke_report_path=live.output_path,
        object_store_smoke_report_path=object_store.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["object_store_commit_smoke"]["attached"] is True
    assert manifest["artifacts"]["object_store_commit_smoke"]["artifact_type"] == "object_store_commit_smoke_report.v1"
    assert summary["object_store_smoke_attached"] is True
    assert summary["object_store_smoke_passed"] is True
    assert summary["object_store_smoke_object_count"] == 3
    assert summary["object_store_smoke_uploaded_object_count"] == 3
    assert summary["object_store_smoke_readback_passed_count"] == 3
    assert summary["object_store_smoke_encrypted_object_count"] == 3
    assert summary["object_store_smoke_encryption_policy_enforced"] is True
    assert summary["object_store_smoke_unencrypted_put_denied"] is True
    assert summary["object_store_smoke_encrypted_put_allowed"] is True
    assert "iceberg_catalog_commit" in summary["object_store_smoke_not_covered"]
    assert not any(item["gap"] == "object_store_commit_smoke_not_attached" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_trino_sql_smoke_report(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live-lakehouse-run",
        release_id="trino-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
    )
    trino = write_trino_sql_runtime_smoke_report(
        ROOT,
        tmp_path / "trino-sql-runtime-smoke-report.json",
        output_dir=tmp_path / "trino-run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="trino-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=ReviewPackFakeTrino(),
        wait_interval_seconds=0,
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_lakehouse_smoke_report_path=live.output_path,
        trino_sql_smoke_report_path=trino.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["trino_sql_runtime_smoke"]["attached"] is True
    assert manifest["artifacts"]["trino_sql_runtime_smoke"]["artifact_type"] == "trino_sql_runtime_smoke_report.v1"
    assert summary["trino_sql_smoke_attached"] is True
    assert summary["trino_sql_smoke_passed"] is True
    assert summary["trino_sql_smoke_row_count"] == 4
    assert summary["trino_sql_smoke_result_row_count"] == 2
    assert summary["trino_sql_smoke_query_engine"] == "trino"
    assert summary["trino_sql_smoke_query_mode"] == "memory_catalog"
    assert "trino_iceberg_connector" in summary["trino_sql_smoke_not_covered"]
    assert not any(item["gap"] == "trino_sql_runtime_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "trino_or_dremio_sql_runtime_query" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "trino_iceberg_connector" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_schema_registry_runtime_smoke_report(tmp_path: Path) -> None:
    event_path = write_json_artifact(
        tmp_path / "event-backbone-smoke-report.json",
        {
            "artifact_type": "event_backbone_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "debezium_or_transactional_outbox_source_connector",
                    "broker_acl_enforcement",
                    "multi_partition_rebalance",
                    "production_schema_registry_subject_publication",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "source_record_count": 4,
                "consumed_record_count": 4,
                "sink_schema_validation_passed": True,
                "sink_schema_validated_source_count": 8,
                "producer_schema_id_guard_passed": True,
                "producer_schema_id_guarded_source_count": 8,
            },
        },
    )
    schema_path = write_json_artifact(
        tmp_path / "schema-registry-runtime-smoke-report.json",
        {
            "artifact_type": "schema_registry_runtime_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_registry_authentication_authorization",
                    "production_registry_ha_storage",
                    "producer_schema_id_enforcement",
                    "broker_or_sink_schema_validation",
                    "external_attestation_for_production_registry",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "registry_api": "confluent_compatible_v7",
                "subject_count": 9,
                "published_subject_count": 9,
                "readback_passed_count": 9,
                "hash_match_count": 9,
            },
        },
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        event_backbone_smoke_report_path=event_path,
        schema_registry_runtime_smoke_report_path=schema_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["schema_registry_runtime_smoke"]["attached"] is True
    assert manifest["artifacts"]["schema_registry_runtime_smoke"]["artifact_type"] == "schema_registry_runtime_smoke_report.v1"
    assert summary["schema_registry_runtime_smoke_attached"] is True
    assert summary["schema_registry_runtime_smoke_passed"] is True
    assert summary["schema_registry_runtime_smoke_registry_api"] == "confluent_compatible_v7"
    assert summary["schema_registry_runtime_smoke_published_subject_count"] == 9
    assert not any(item["gap"] == "schema_registry_runtime_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "production_schema_registry_subject_publication" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "broker_or_sink_schema_validation" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "producer_schema_id_enforcement" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "external_attestation_for_production_registry" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_accepts_schema_registry_attestation(tmp_path: Path) -> None:
    publication_path = write_json_artifact(
        tmp_path / "schema-registry-publication-manifest.json",
        {
            "artifact_type": "schema_registry_publication_manifest.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "environment": "local",
            "registry_vendor": "apicurio",
            "registry_api": "confluent_compatible_v7",
            "registry_uri": "http://localhost:18082",
            "subjects": [
                {
                    "subject": "finance.benefit_settled.v1-value",
                    "registered": True,
                    "schema_id": "42",
                    "artifact_id": "finance.benefit_settled.v1-value",
                    "version": 1,
                    "compatibility": "BACKWARD_TRANSITIVE",
                    "payload_schema_hash": "sha256:" + ("1" * 64),
                    "producer_enforced": False,
                    "broker_validation": False,
                    "registry_uri": "http://localhost:18082",
                }
            ],
        },
    )
    schema_path = write_json_artifact(
        tmp_path / "schema-registry-runtime-smoke-report.json",
        {
            "artifact_type": "schema_registry_runtime_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "release_id": "local-schema-registry-runtime-smoke",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_registry_authentication_authorization",
                    "production_registry_ha_storage",
                    "external_attestation_for_production_registry",
                ]
            },
            "publication_manifest": {
                "path": publication_path.as_posix(),
                "hash": hash_file(publication_path),
                "artifact_type": "schema_registry_publication_manifest.v1",
                "subject_count": 1,
            },
            "summary": {
                "failed_check_count": 0,
                "registry_api": "confluent_compatible_v7",
                "subject_count": 1,
                "published_subject_count": 1,
                "readback_passed_count": 1,
                "hash_match_count": 1,
            },
        },
    )
    attestation = write_schema_registry_publication_attestation(
        ROOT,
        tmp_path / "schema-registry-publication-attestation.json",
        publication_manifest_path=publication_path,
        schema_registry_runtime_smoke_report_path=schema_path,
        environment="staging",
        generated_at="2026-01-15T09:15:20Z",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        schema_registry_runtime_smoke_report_path=schema_path,
        schema_registry_attestation_report_path=attestation.output_path,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["schema_registry_attestation"]["attached"] is True
    assert summary["schema_registry_attestation_attached"] is True
    assert summary["schema_registry_attestation_passed"] is True
    assert summary["schema_registry_attestation_signature_verified"] is True
    assert summary["schema_registry_attestation_subject_hash_matches"] is True
    assert not any(item["gap"] == "external_attestation_for_production_registry" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "production_registry_authentication_authorization" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "production_registry_ha_storage" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_uses_production_like_schema_registry_ops_to_close_capability_gap(
    tmp_path: Path,
) -> None:
    schema_ops = write_json_artifact(
        tmp_path / "schema-registry-ops-report.json",
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
                    "contract_hash": "sha256:" + ("8" * 64),
                    "expected_compatibility": "BACKWARD_TRANSITIVE",
                    "payload_schema_hash": "sha256:" + ("9" * 64),
                    "sources": [{"source_id": "commerce-benefit-settlement", "priority": "P0"}],
                    "issues": [],
                    "passed": True,
                    "publication": {
                        "registered": True,
                        "schema_id": "schema-1",
                        "artifact_id": "artifact-1",
                        "compatibility": "BACKWARD_TRANSITIVE",
                        "payload_schema_hash": "sha256:" + ("9" * 64),
                        "producer_enforced": True,
                        "broker_validation": True,
                        "registry_uri": "https://schema-registry.prod.example",
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
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        schema_registry_ops_report_path=schema_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert manifest["artifacts"]["schema_registry_ops"]["attached"] is True
    assert summary["schema_registry_ops_attached"] is True
    assert summary["schema_registry_ops_passed"] is True
    assert summary["schema_registry_ops_environment"] == "prod"
    assert summary["schema_registry_ops_readiness_state"] == "production_like_ready"
    assert summary["schema_registry_ops_publication_evidence_attached"] is True
    assert summary["schema_registry_ops_producer_enforcement_gap_count"] == 0
    assert summary["schema_registry_ops_broker_validation_gap_count"] == 0
    assert summary["schema_registry_release_gate_passed"] is True
    assert "schema-registry-compatibility" not in blocker_capabilities
    assert "platform-runtime-iac" in blocker_capabilities
    assert "source-onboarding" in blocker_capabilities


def test_production_review_pack_rejects_thin_schema_registry_ops_subject_evidence(
    tmp_path: Path,
) -> None:
    schema_ops = write_json_artifact(
        tmp_path / "schema-registry-ops-report.json",
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
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        schema_registry_ops_report_path=schema_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert manifest["summary"]["schema_registry_ops_passed"] is True
    assert manifest["summary"]["schema_registry_release_gate_passed"] is False
    assert "schema-registry-compatibility" in blocker_capabilities


def test_production_review_pack_keeps_schema_registry_capability_blocker_for_local_ops_report(
    tmp_path: Path,
) -> None:
    schema_ops = write_json_artifact(
        tmp_path / "schema-registry-ops-report.json",
        {
            "artifact_type": "schema_registry_ops_report.v1",
            "generated_at": "2026-01-15T10:05:00Z",
            "environment": "local",
            "capability_id": "schema-registry-compatibility",
            "readiness_state": "local_preflight_ready",
            "mode": "local_preflight",
            "registry_uri": "local-json-schema-registry-preflight",
            "passed": True,
            "publication_evidence": {"attached": False},
            "attestation": {"attached": False},
            "checks": [{"check": "compatibility_report_passed", "passed": True}],
            "subjects": [{"subject": "finance.benefit_settled.v1-value", "passed": True}],
            "summary": {
                "subject_count": 1,
                "passed_subject_count": 1,
                "failed_subject_count": 0,
                "p0_subject_count": 1,
                "p0_failed_subject_count": 0,
                "global_failed_check_count": 0,
                "publication_evidence_attached": False,
                "producer_enforcement_gap_count": 0,
                "broker_validation_gap_count": 0,
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        schema_registry_ops_report_path=schema_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["schema_registry_ops_attached"] is True
    assert summary["schema_registry_ops_passed"] is True
    assert summary["schema_registry_release_gate_passed"] is False
    assert "schema-registry-compatibility" in blocker_capabilities


def test_production_review_pack_uses_production_like_catalog_lineage_ops_to_close_capability_gap(
    tmp_path: Path,
) -> None:
    catalog_ops = write_catalog_lineage_review_ops(tmp_path / "catalog-lineage", environment="prod")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        catalog_lineage_ops_report_path=catalog_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert manifest["artifacts"]["catalog_lineage_ops"]["attached"] is True
    assert summary["catalog_lineage_ops_attached"] is True
    assert summary["catalog_lineage_ops_passed"] is True
    assert summary["catalog_lineage_ops_environment"] == "prod"
    assert summary["catalog_lineage_ops_readiness_state"] == "production_like_ready"
    assert summary["catalog_lineage_ops_mode"] == "runtime_attested"
    assert summary["catalog_lineage_ops_publish_status"] == "READY"
    assert summary["catalog_lineage_ops_openlineage_event_count"] > 0
    assert summary["catalog_lineage_release_gate_passed"] is True
    assert "catalog-lineage-control-plane" not in blocker_capabilities
    assert "source-onboarding" in blocker_capabilities


def test_production_review_pack_keeps_catalog_lineage_capability_blocker_for_local_ops_report(
    tmp_path: Path,
) -> None:
    catalog_ops = write_catalog_lineage_review_ops(tmp_path / "catalog-lineage", environment="local")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        catalog_lineage_ops_report_path=catalog_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["catalog_lineage_ops_attached"] is True
    assert summary["catalog_lineage_ops_passed"] is True
    assert summary["catalog_lineage_release_gate_passed"] is False
    assert "catalog-lineage-control-plane" in blocker_capabilities


def test_production_review_pack_keeps_catalog_lineage_capability_blocker_when_named_check_missing(
    tmp_path: Path,
) -> None:
    catalog_ops = write_catalog_lineage_review_ops(tmp_path / "catalog-lineage", environment="prod")
    payload = json.loads(catalog_ops.read_text(encoding="utf-8"))
    payload["checks"] = [
        check
        for check in payload["checks"]
        if check.get("name") != "publish_receipt_openlineage_hash_matches"
    ]
    catalog_ops.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        catalog_lineage_ops_report_path=catalog_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["catalog_lineage_ops_passed"] is True
    assert summary["catalog_lineage_release_gate_passed"] is False
    assert "catalog-lineage-control-plane" in blocker_capabilities


def test_production_review_pack_uses_production_like_semantic_metric_serving_ops_to_close_capability_gap(
    tmp_path: Path,
) -> None:
    semantic_ops = write_semantic_metric_serving_review_ops(tmp_path / "semantic-serving", environment="prod")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        semantic_metric_serving_ops_report_path=semantic_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert manifest["artifacts"]["semantic_metric_serving_ops"]["attached"] is True
    assert summary["semantic_metric_serving_ops_attached"] is True
    assert summary["semantic_metric_serving_ops_passed"] is True
    assert summary["semantic_metric_serving_ops_environment"] == "prod"
    assert summary["semantic_metric_serving_ops_readiness_state"] == "production_like_ready"
    assert summary["semantic_metric_serving_ops_mode"] == "runtime_attested"
    assert summary["semantic_metric_serving_ops_metric_count"] > 0
    assert summary["semantic_metric_serving_ops_failed_metric_count"] == 0
    assert summary["semantic_metric_serving_ops_certification_attached"] is True
    assert summary["semantic_metric_serving_ops_deployment_attached"] is True
    assert summary["semantic_metric_serving_ops_usage_attached"] is True
    assert summary["semantic_metric_serving_release_gate_passed"] is True
    assert "semantic-metric-serving" not in blocker_capabilities
    assert "source-onboarding" in blocker_capabilities


def test_production_review_pack_keeps_semantic_metric_serving_blocker_for_local_ops_report(
    tmp_path: Path,
) -> None:
    semantic_ops = write_semantic_metric_serving_review_ops(tmp_path / "semantic-serving", environment="local")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        semantic_metric_serving_ops_report_path=semantic_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["semantic_metric_serving_ops_attached"] is True
    assert summary["semantic_metric_serving_ops_passed"] is True
    assert summary["semantic_metric_serving_release_gate_passed"] is False
    assert "semantic-metric-serving" in blocker_capabilities


def test_production_review_pack_keeps_semantic_metric_serving_blocker_when_named_check_missing(
    tmp_path: Path,
) -> None:
    semantic_ops = write_semantic_metric_serving_review_ops(tmp_path / "semantic-serving", environment="prod")
    payload = json.loads(semantic_ops.read_text(encoding="utf-8"))
    payload["checks"] = [
        check
        for check in payload["checks"]
        if check.get("name") != "serving_deployment_manifest_hash_matches"
    ]
    semantic_ops.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        semantic_metric_serving_ops_report_path=semantic_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["semantic_metric_serving_ops_passed"] is True
    assert summary["semantic_metric_serving_release_gate_passed"] is False
    assert "semantic-metric-serving" in blocker_capabilities


def test_production_review_pack_uses_production_like_source_activation_ops_to_close_capability_gap(
    tmp_path: Path,
) -> None:
    source_ops = write_source_activation_review_ops(tmp_path / "source-activation", environment="prod")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        source_activation_ops_report_path=source_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["source_activation_ops"]["attached"] is True
    assert summary["source_activation_ops_attached"] is True
    assert summary["source_activation_ops_passed"] is True
    assert summary["source_activation_ops_environment"] == "prod"
    assert summary["source_activation_ops_readiness_state"] == "production_like_ready"
    assert summary["source_activation_ops_mode"] == "runtime_attested"
    assert summary["source_activation_ops_source_count"] > 0
    assert summary["source_activation_ops_p0_source_count"] > 0
    assert summary["source_activation_ops_p0_active_count"] == summary["source_activation_ops_p0_source_count"]
    assert summary["source_activation_ops_p0_unactivated_count"] == 0
    assert summary["source_activation_ops_p0_activation_gap_count"] == 0
    assert summary["source_activation_ops_critical_issue_count"] == 0
    assert summary["source_activation_ops_p0_critical_issue_count"] == 0
    assert summary["source_activation_ops_registry_drift_count"] == 0
    assert summary["source_activation_ops_pointer_issue_count"] == 0
    assert summary["source_activation_ops_runtime_readiness_issue_count"] == 0
    assert summary["source_onboarding_release_gate_passed"] is True
    assert not any(item.get("capability_id") == "source-onboarding" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_keeps_source_onboarding_blocker_for_local_ops_report(
    tmp_path: Path,
) -> None:
    source_ops = write_source_activation_review_ops(tmp_path / "source-activation", environment="local")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        source_activation_ops_report_path=source_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["source_activation_ops_attached"] is True
    assert summary["source_activation_ops_passed"] is True
    assert summary["source_activation_ops_mode"] == "local_preflight"
    assert summary["source_onboarding_release_gate_passed"] is False
    assert "source-onboarding" in blocker_capabilities


def test_production_review_pack_keeps_source_onboarding_blocker_when_p0_coverage_is_incomplete(
    tmp_path: Path,
) -> None:
    source_ops = write_source_activation_review_ops(tmp_path / "source-activation", environment="prod")
    payload = json.loads(source_ops.read_text(encoding="utf-8"))
    p0_row = next(row for row in payload["sources"] if row["priority"] == "P0")
    p0_row["activation_state"] = "pending"
    payload["summary"]["p0_active_count"] -= 1
    payload["summary"]["active_count"] -= 1
    payload["summary"]["pending_count"] += 1
    source_ops.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        source_activation_ops_report_path=source_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["source_activation_ops_passed"] is True
    assert summary["source_onboarding_release_gate_passed"] is False
    assert "source-onboarding" in blocker_capabilities


def test_production_review_pack_uses_runtime_attested_backfill_readiness_to_close_capability_gap(
    tmp_path: Path,
) -> None:
    backfill = write_backfill_readiness_review_report(tmp_path / "backfill", environment="prod", ready=True)

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        backfill_readiness_report_path=backfill,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {item.get("capability_id") for item in manifest["p0_gap_backlog"]}

    assert manifest["artifacts"]["backfill_readiness"]["attached"] is True
    assert summary["backfill_readiness_attached"] is True
    assert summary["backfill_readiness_passed"] is True
    assert summary["backfill_readiness_environment"] == "prod"
    assert summary["backfill_readiness_mode"] == "runtime_attested"
    assert summary["backfill_readiness_state"] == "ready"
    assert summary["backfill_readiness_failed_check_count"] == 0
    assert summary["backfill_readiness_attached_evidence_count"] == 9
    assert summary["backfill_change_governance_release_gate_passed"] is True
    assert "backfill-change-governance" not in blocker_capabilities


def test_production_review_pack_keeps_backfill_blocker_for_non_runtime_attested_report(
    tmp_path: Path,
) -> None:
    backfill = write_backfill_readiness_review_report(tmp_path / "backfill", environment="prod", ready=False)

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        backfill_readiness_report_path=backfill,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {item.get("capability_id") for item in manifest["p0_gap_backlog"]}
    gap_names = {item.get("gap") for item in manifest["p0_gap_backlog"]}

    assert summary["backfill_readiness_attached"] is True
    assert summary["backfill_readiness_passed"] is False
    assert summary["backfill_change_governance_release_gate_passed"] is False
    assert "backfill-change-governance" in blocker_capabilities
    assert "backfill_readiness_release_gate_failed" in gap_names


def test_production_review_pack_accepts_schema_registry_auth_smoke(tmp_path: Path) -> None:
    schema_path = write_json_artifact(
        tmp_path / "schema-registry-runtime-smoke-report.json",
        {
            "artifact_type": "schema_registry_runtime_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "release_id": "local-schema-registry-runtime-smoke",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_registry_authentication_authorization",
                    "production_registry_ha_storage",
                    "external_attestation_for_production_registry",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "registry_api": "confluent_compatible_v7",
                "subject_count": 9,
                "published_subject_count": 9,
                "readback_passed_count": 9,
                "hash_match_count": 9,
            },
        },
    )
    auth_path = write_json_artifact(
        tmp_path / "schema-registry-auth-smoke-report.json",
        {
            "artifact_type": "schema_registry_auth_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_oidc_jwks_validation",
                    "production_registry_ha_storage",
                    "production_secret_rotation",
                ]
            },
            "summary": {
                "auth_gateway_enforced": True,
                "missing_token_denied": True,
                "unknown_token_denied": True,
                "denied_token_blocked": True,
                "reader_write_denied": True,
                "publisher_publish_allowed": True,
                "publisher_config_allowed": True,
                "reader_read_allowed": True,
                "authorization_audit_event_count": 7,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        schema_registry_runtime_smoke_report_path=schema_path,
        schema_registry_auth_smoke_report_path=auth_path,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["schema_registry_auth_smoke"]["attached"] is True
    assert summary["schema_registry_auth_smoke_attached"] is True
    assert summary["schema_registry_auth_smoke_passed"] is True
    assert summary["schema_registry_auth_smoke_auth_gateway_enforced"] is True
    assert summary["schema_registry_auth_smoke_authorization_audit_event_count"] == 7
    assert not any(item["gap"] == "production_registry_authentication_authorization" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "production_registry_ha_storage" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "external_attestation_for_production_registry" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_accepts_schema_registry_storage_smoke(tmp_path: Path) -> None:
    schema_path = write_json_artifact(
        tmp_path / "schema-registry-runtime-smoke-report.json",
        {
            "artifact_type": "schema_registry_runtime_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "release_id": "local-schema-registry-runtime-smoke",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_registry_authentication_authorization",
                    "production_registry_ha_storage",
                    "external_attestation_for_production_registry",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "registry_api": "confluent_compatible_v7",
                "subject_count": 9,
                "published_subject_count": 9,
                "readback_passed_count": 9,
                "hash_match_count": 9,
            },
        },
    )
    storage_path = write_json_artifact(
        tmp_path / "schema-registry-storage-smoke-report.json",
        {
            "artifact_type": "schema_registry_storage_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "managed_ha_postgres_or_database_cluster",
                    "multi_az_registry_deployment",
                    "backup_restore_or_pitr_drill",
                ]
            },
            "summary": {
                "storage_backend": "postgresql",
                "registry_replica_count": 2,
                "shared_sql_storage_configured": True,
                "secret_env_files_persisted": False,
                "cross_replica_read_after_write_passed": True,
                "replica_restart_durable_readback_passed": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        schema_registry_runtime_smoke_report_path=schema_path,
        schema_registry_storage_smoke_report_path=storage_path,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["schema_registry_storage_smoke"]["attached"] is True
    assert summary["schema_registry_storage_smoke_attached"] is True
    assert summary["schema_registry_storage_smoke_passed"] is True
    assert summary["schema_registry_storage_smoke_backend"] == "postgresql"
    assert summary["schema_registry_storage_smoke_replica_count"] == 2
    assert summary["schema_registry_storage_smoke_secret_env_files_persisted"] is False
    assert summary["schema_registry_storage_smoke_cross_replica_read_after_write_passed"] is True
    assert not any(item["gap"] == "production_registry_ha_storage" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "production_registry_authentication_authorization" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "external_attestation_for_production_registry" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_attaches_trino_iceberg_minio_smoke_report(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live-lakehouse-run",
        release_id="trino-iceberg-minio-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
    )
    iceberg = write_iceberg_catalog_smoke_report(
        ROOT,
        tmp_path / "iceberg-catalog-smoke-report.json",
        output_dir=tmp_path / "iceberg-run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="trino-iceberg-minio-review-pack",
        generated_at="2026-01-15T09:15:20Z",
    )
    trino_iceberg = write_trino_iceberg_minio_smoke_report(
        ROOT,
        tmp_path / "trino-iceberg-minio-smoke-report.json",
        output_dir=tmp_path / "trino-iceberg-run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="trino-iceberg-minio-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=ReviewPackFakeTrinoIceberg(),
        wait_interval_seconds=0,
        s3_client_override=ReviewPackFakeIcebergS3(),
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_lakehouse_smoke_report_path=live.output_path,
        iceberg_catalog_smoke_report_path=iceberg.output_path,
        trino_iceberg_minio_smoke_report_path=trino_iceberg.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["trino_iceberg_minio_smoke"]["attached"] is True
    assert manifest["artifacts"]["trino_iceberg_minio_smoke"]["artifact_type"] == "trino_iceberg_minio_smoke_report.v1"
    assert summary["trino_iceberg_minio_smoke_attached"] is True
    assert summary["trino_iceberg_minio_smoke_passed"] is True
    assert summary["trino_iceberg_minio_smoke_query_mode"] == "iceberg_jdbc_catalog_minio_s3"
    assert summary["trino_iceberg_minio_smoke_snapshot_count"] == 2
    assert summary["trino_iceberg_minio_smoke_iceberg_file_count"] == 1
    assert summary["trino_iceberg_minio_smoke_minio_object_count"] == 3
    assert summary["trino_iceberg_minio_smoke_minio_encrypted_object_count"] == 3
    assert summary["trino_iceberg_minio_smoke_object_store_encryption_policy_enforced"] is True
    assert summary["trino_iceberg_minio_smoke_objects_encrypted"] is True
    assert not any(item["gap"] == "trino_iceberg_minio_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "minio_object_store_iceberg_warehouse" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "trino_iceberg_connector" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "minio_federated_query" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "production_object_store_encryption_policy" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "production_cloud_kms_key_rotation" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "cloud_provider_bucket_policy_attestation" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "cross_account_object_store_access_policy" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "production_catalog_ha" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "cross_engine_commit_compatibility" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_uses_catalog_cross_engine_smoke_for_commit_compatibility_only(
    tmp_path: Path,
) -> None:
    trino_iceberg = write_json_artifact(
        tmp_path / "trino-iceberg-minio-smoke-report.json",
        {
            "artifact_type": "trino_iceberg_minio_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_catalog_ha",
                    "cross_engine_commit_compatibility",
                    "production_catalog_concurrency_locking",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "row_count": 3,
                "query_mode": "iceberg_jdbc_catalog_minio_s3",
                "query_passed": True,
                "snapshot_count": 2,
                "iceberg_file_count": 1,
                "minio_object_count": 3,
                "minio_encrypted_object_count": 3,
                "object_store_encryption_policy_enforced": True,
                "trino_iceberg_objects_encrypted": True,
            },
        },
    )
    catalog_cross_engine = write_json_artifact(
        tmp_path / "catalog-cross-engine-smoke-report.json",
        {
            "artifact_type": "catalog_cross_engine_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_catalog_ha",
                    "managed_catalog_failover",
                    "production_catalog_backup_restore_pitr",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "failed_checks": [],
                "catalog_backend": "postgresql_jdbc_catalog",
                "cross_engine_commit_compatibility_passed": True,
                "catalog_concurrency_locking_passed": True,
                "stale_commit_rejected": True,
                "pyiceberg_readback_row_count": 3,
                "snapshot_count_after_pyiceberg": 3,
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        trino_iceberg_minio_smoke_report_path=trino_iceberg,
        catalog_cross_engine_smoke_report_path=catalog_cross_engine,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["artifacts"]["catalog_cross_engine_smoke"]["attached"] is True
    assert manifest["artifacts"]["catalog_cross_engine_smoke"]["artifact_type"] == "catalog_cross_engine_smoke_report.v1"
    assert summary["catalog_cross_engine_smoke_attached"] is True
    assert summary["catalog_cross_engine_smoke_passed"] is True
    assert summary["catalog_cross_engine_smoke_catalog_backend"] == "postgresql_jdbc_catalog"
    assert summary["catalog_cross_engine_smoke_cross_engine_commit_compatibility_passed"] is True
    assert summary["catalog_cross_engine_smoke_catalog_concurrency_locking_passed"] is True
    assert summary["catalog_cross_engine_smoke_stale_commit_rejected"] is True
    assert summary["catalog_cross_engine_smoke_pyiceberg_readback_row_count"] == 3
    assert summary["catalog_cross_engine_smoke_snapshot_count_after_pyiceberg"] == 3
    assert "cross_engine_commit_compatibility" not in gap_names
    assert "catalog_cross_engine_smoke_failed" not in gap_names
    assert "production_catalog_ha" in gap_names
    assert "production_catalog_concurrency_locking" in gap_names


def test_production_review_pack_uses_catalog_runtime_ops_for_catalog_runtime_gaps(
    tmp_path: Path,
) -> None:
    trino_iceberg, catalog_cross_engine = write_catalog_runtime_gap_inputs(tmp_path)
    catalog_runtime_ops = write_catalog_runtime_review_report(tmp_path / "catalog-runtime", environment="staging")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        trino_iceberg_minio_smoke_report_path=trino_iceberg,
        catalog_cross_engine_smoke_report_path=catalog_cross_engine,
        catalog_runtime_ops_report_path=catalog_runtime_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert manifest["artifacts"]["catalog_runtime_ops"]["attached"] is True
    assert summary["catalog_runtime_ops_attached"] is True
    assert summary["catalog_runtime_ops_passed"] is True
    assert summary["catalog_runtime_ops_environment"] == "staging"
    assert summary["catalog_runtime_ops_replica_count"] == 3
    assert summary["catalog_runtime_ops_availability_zones"] == 3
    assert summary["catalog_runtime_ops_failover_passed"] is True
    assert summary["catalog_runtime_ops_stale_commit_rejected"] is True
    assert summary["catalog_runtime_ops_backup_enabled"] is True
    assert summary["catalog_runtime_ops_pitr_enabled"] is True
    assert summary["catalog_runtime_release_gate_passed"] is True
    assert "production_catalog_ha" not in gap_names
    assert "production_catalog_concurrency_locking" not in gap_names
    assert "managed_catalog_failover" not in gap_names
    assert "production_catalog_backup_restore_pitr" not in gap_names
    assert "platform-runtime-iac" in blocker_capabilities
    assert "catalog-lineage-control-plane" in blocker_capabilities


def test_production_review_pack_keeps_catalog_runtime_gaps_for_local_ops_report(
    tmp_path: Path,
) -> None:
    trino_iceberg, catalog_cross_engine = write_catalog_runtime_gap_inputs(tmp_path)
    catalog_runtime_ops = write_catalog_runtime_review_report(tmp_path / "catalog-runtime", environment="local")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        trino_iceberg_minio_smoke_report_path=trino_iceberg,
        catalog_cross_engine_smoke_report_path=catalog_cross_engine,
        catalog_runtime_ops_report_path=catalog_runtime_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["summary"]["catalog_runtime_ops_passed"] is False
    assert manifest["summary"]["catalog_runtime_release_gate_passed"] is False
    assert "catalog_runtime_ops_failed" in gap_names
    assert "production_catalog_ha" in gap_names
    assert "production_catalog_concurrency_locking" in gap_names


def test_production_review_pack_rejects_catalog_runtime_environment_mismatch(
    tmp_path: Path,
) -> None:
    trino_iceberg, catalog_cross_engine = write_catalog_runtime_gap_inputs(tmp_path)
    catalog_runtime_ops = write_catalog_runtime_review_report(tmp_path / "catalog-runtime", environment="staging")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        trino_iceberg_minio_smoke_report_path=trino_iceberg,
        catalog_cross_engine_smoke_report_path=catalog_cross_engine,
        catalog_runtime_ops_report_path=catalog_runtime_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["summary"]["catalog_runtime_ops_passed"] is True
    assert manifest["summary"]["catalog_runtime_ops_environment"] == "staging"
    assert manifest["summary"]["catalog_runtime_release_gate_passed"] is False
    assert "catalog_runtime_ops_failed" in gap_names
    assert "production_catalog_ha" in gap_names
    assert "production_catalog_concurrency_locking" in gap_names


def test_production_review_pack_attaches_trino_runtime_security_smoke_report(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live-lakehouse-run",
        release_id="trino-security-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
    )
    trino_iceberg = write_trino_iceberg_minio_smoke_report(
        ROOT,
        tmp_path / "trino-iceberg-minio-smoke-report.json",
        output_dir=tmp_path / "trino-iceberg-run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="trino-security-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=ReviewPackFakeTrinoIceberg(),
        wait_interval_seconds=0,
        s3_client_override=ReviewPackFakeIcebergS3(),
    )
    trino_security = write_trino_runtime_security_smoke_report(
        ROOT,
        tmp_path / "trino-runtime-security-smoke-report.json",
        output_dir=tmp_path / "trino-security-run",
        trino_iceberg_minio_smoke_report_path=trino_iceberg.output_path,
        release_id="trino-security-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=ReviewPackFakeTrinoRuntimeSecurity(),
        wait_interval_seconds=0,
    )
    policy_decision = write_json_artifact(
        tmp_path / "policy-decision-smoke-report.json",
        {
            "artifact_type": "policy_decision_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "keycloak_or_oidc_authentication",
                    "production_opa_or_ranger_cluster_ha",
                    "production_policy_bundle_signing",
                    "production_secret_rotation",
                ]
            },
            "summary": {
                "pdp": "opa",
                "decision_api_reachable": True,
                "finance_reader_allowed": True,
                "unauthorized_default_denied": True,
                "row_filter_decision_present": True,
                "column_mask_decision_present": True,
                "policy_admin_approval_passed": True,
                "policy_admin_self_approval_denied": True,
                "policy_admin_missing_evidence_denied": True,
                "audit_sink_passed": True,
                "audit_event_count": 6,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_lakehouse_smoke_report_path=live.output_path,
        trino_iceberg_minio_smoke_report_path=trino_iceberg.output_path,
        trino_runtime_security_smoke_report_path=trino_security.output_path,
        policy_decision_smoke_report_path=policy_decision,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["trino_runtime_security_smoke"]["attached"] is True
    assert manifest["artifacts"]["trino_runtime_security_smoke"]["artifact_type"] == "trino_runtime_security_smoke_report.v1"
    assert manifest["artifacts"]["policy_decision_smoke"]["attached"] is True
    assert manifest["artifacts"]["policy_decision_smoke"]["artifact_type"] == "policy_decision_smoke_report.v1"
    assert summary["trino_runtime_security_smoke_attached"] is True
    assert summary["trino_runtime_security_smoke_passed"] is True
    assert summary["policy_decision_smoke_attached"] is True
    assert summary["policy_decision_smoke_passed"] is True
    assert summary["policy_decision_smoke_pdp"] == "opa"
    assert summary["policy_decision_smoke_policy_admin_self_approval_denied"] is True
    assert summary["trino_runtime_security_smoke_source_row_count"] == 4
    assert summary["trino_runtime_security_smoke_allowed_query_passed"] is True
    assert summary["trino_runtime_security_smoke_allowed_write_blocked"] is True
    assert summary["trino_runtime_security_smoke_denied_query_blocked"] is True
    assert summary["trino_runtime_security_smoke_unknown_user_blocked"] is True
    assert summary["trino_runtime_security_smoke_security_probe_admin_unfiltered"] is True
    assert summary["trino_runtime_security_smoke_row_level_filter_enforced"] is True
    assert summary["trino_runtime_security_smoke_column_masking_enforced"] is True
    assert summary["trino_runtime_security_smoke_centralized_audit_sink_passed"] is True
    assert summary["trino_runtime_security_smoke_audit_event_count"] == 8
    assert summary["trino_runtime_security_smoke_audit_failed_event_count"] == 0
    assert summary["trino_runtime_security_smoke_all_access_denied_errors_verified"] is True
    assert summary["access_privacy_release_gate_passed"] is False
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }
    assert not any(item["gap"] == "trino_runtime_security_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "runtime_security_enforcement" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "keycloak_or_oidc_authentication" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "production_secret_rotation" for item in manifest["p0_gap_backlog"])
    assert "access-privacy-enforcement" in blocker_capabilities
    assert not any(item["gap"] == "ranger_or_opa_policy_decision_point" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "policy_admin_maker_checker" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "row_level_filter_enforcement" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "column_masking_enforcement" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "centralized_audit_sink" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_uses_oidc_auth_smoke_to_close_oidc_gap_only(tmp_path: Path) -> None:
    trino_security = write_json_artifact(
        tmp_path / "trino-runtime-security-smoke-report.json",
        {
            "artifact_type": "trino_runtime_security_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "keycloak_or_oidc_authentication",
                    "production_secret_rotation",
                ]
            },
            "summary": {
                "query_mode": "iceberg_jdbc_catalog_minio_s3_file_access_control",
                "source_row_count": 4,
                "allowed_query_passed": True,
                "allowed_write_blocked": True,
                "denied_query_blocked": True,
                "unknown_user_blocked": True,
                "security_probe_admin_unfiltered": True,
                "row_level_filter_enforced": True,
                "column_masking_enforced": True,
                "centralized_audit_sink_passed": True,
                "runtime_security_audit_event_count": 8,
                "runtime_security_audit_failed_event_count": 0,
                "all_access_denied_errors_verified": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    oidc_auth = write_oidc_auth_smoke_report(
        ROOT,
        tmp_path / "oidc-auth-smoke-report.json",
        output_dir=tmp_path / "oidc-run",
        release_id="oidc-review-pack",
        generated_at="2026-01-15T09:15:20Z",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        trino_runtime_security_smoke_report_path=trino_security,
        oidc_auth_smoke_report_path=oidc_auth.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["oidc_auth_smoke"]["attached"] is True
    assert manifest["artifacts"]["oidc_auth_smoke"]["artifact_type"] == "oidc_auth_smoke_report.v1"
    assert summary["oidc_auth_smoke_attached"] is True
    assert summary["oidc_auth_smoke_passed"] is True
    assert summary["oidc_auth_smoke_jwks_key_published"] is True
    assert summary["oidc_auth_smoke_rs256_signature_validation_passed"] is True
    assert summary["oidc_auth_smoke_audience_validation_passed"] is True
    assert summary["oidc_auth_smoke_raw_access_tokens_persisted"] is False
    assert summary["access_privacy_release_gate_passed"] is False
    assert not any(item["gap"] == "keycloak_or_oidc_authentication" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "production_secret_rotation" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "oidc_auth_smoke_failed" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_uses_access_privacy_release_gate_when_security_policy_and_oidc_pass(
    tmp_path: Path,
) -> None:
    trino_security = write_json_artifact(
        tmp_path / "trino-runtime-security-smoke-report.json",
        {
            "artifact_type": "trino_runtime_security_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": ["production_secret_rotation"]},
            "summary": {
                "query_mode": "iceberg_jdbc_catalog_minio_s3_file_access_control",
                "source_row_count": 4,
                "allowed_query_passed": True,
                "allowed_write_blocked": True,
                "denied_query_blocked": True,
                "unknown_user_blocked": True,
                "security_probe_admin_unfiltered": True,
                "row_level_filter_enforced": True,
                "column_masking_enforced": True,
                "centralized_audit_sink_passed": True,
                "runtime_security_audit_event_count": 8,
                "runtime_security_audit_failed_event_count": 0,
                "all_access_denied_errors_verified": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    policy_decision = write_json_artifact(
        tmp_path / "policy-decision-smoke-report.json",
        {
            "artifact_type": "policy_decision_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": ["production_opa_or_ranger_cluster_ha"]},
            "summary": {
                "pdp": "opa",
                "decision_api_reachable": True,
                "finance_reader_allowed": True,
                "unauthorized_default_denied": True,
                "row_filter_decision_present": True,
                "column_mask_decision_present": True,
                "policy_admin_approval_passed": True,
                "policy_admin_self_approval_denied": True,
                "policy_admin_missing_evidence_denied": True,
                "audit_sink_passed": True,
                "audit_event_count": 6,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    oidc_auth = write_json_artifact(
        tmp_path / "oidc-auth-smoke-report.json",
        {
            "artifact_type": "oidc_auth_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": ["production_keycloak_realm_management"]},
            "summary": {
                "issuer": "https://identity.local/realms/enterprise-dp",
                "audience": "enterprise-dp-runtime",
                "required_role": "data-platform-runtime-reader",
                "jwks_key_published": True,
                "rs256_signature_validation_passed": True,
                "issuer_validation_passed": True,
                "audience_validation_passed": True,
                "expiry_validation_passed": True,
                "required_role_denied": True,
                "unknown_kid_denied": True,
                "missing_token_denied": True,
                "audit_sink_passed": True,
                "audit_event_count": 8,
                "raw_access_tokens_persisted": False,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        trino_runtime_security_smoke_report_path=trino_security,
        policy_decision_smoke_report_path=policy_decision,
        oidc_auth_smoke_report_path=oidc_auth,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["access_privacy_release_gate_passed"] is True
    assert "access-privacy-enforcement" not in blocker_capabilities
    assert "production_secret_rotation" in gap_names
    assert "platform-runtime-iac" in blocker_capabilities
    assert "semantic-metric-serving" in blocker_capabilities
    assert "trino_runtime_security_smoke_not_attached" not in gap_names
    assert "policy_decision_smoke_failed" not in gap_names
    assert "oidc_auth_smoke_failed" not in gap_names
    assert "keycloak_or_oidc_authentication" not in gap_names
    assert "ranger_or_opa_policy_decision_point" not in gap_names


def test_production_review_pack_uses_secret_rotation_smoke_for_orchestrator_injection_only(
    tmp_path: Path,
) -> None:
    trino_security = write_json_artifact(
        tmp_path / "trino-runtime-security-smoke-report.json",
        {
            "artifact_type": "trino_runtime_security_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": ["production_secret_rotation"]},
            "summary": {
                "query_mode": "iceberg_jdbc_catalog_minio_s3_file_access_control",
                "source_row_count": 4,
                "allowed_query_passed": True,
                "allowed_write_blocked": True,
                "denied_query_blocked": True,
                "unknown_user_blocked": True,
                "security_probe_admin_unfiltered": True,
                "row_level_filter_enforced": True,
                "column_masking_enforced": True,
                "centralized_audit_sink_passed": True,
                "runtime_security_audit_event_count": 8,
                "runtime_security_audit_failed_event_count": 0,
                "all_access_denied_errors_verified": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    dagster = write_json_artifact(
        tmp_path / "dagster-orchestration-smoke-report.json",
        {
            "artifact_type": "dagster_orchestration_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "dagster_daemon_or_schedule_tick_history",
                    "orchestrator_service_identity_and_secret_injection",
                    "runtime_security_enforcement",
                ]
            },
            "summary": {
                "job_name": "finance_benefit_reconciliation_runtime_smoke",
                "run_id": "dagster-run-secret-rotation",
                "run_status": "SUCCESS",
                "event_count": 29,
                "op_success_count": 4,
                "validated_report_count": 3,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    secret_rotation = write_secret_rotation_smoke_report(
        ROOT,
        tmp_path / "secret-rotation-smoke-report.json",
        output_dir=tmp_path / "secret-rotation-run",
        release_id="secret-rotation-review-pack",
        generated_at="2026-01-15T09:15:20Z",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        trino_runtime_security_smoke_report_path=trino_security,
        dagster_orchestration_smoke_report_path=dagster,
        secret_rotation_smoke_report_path=secret_rotation.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["secret_rotation_smoke"]["attached"] is True
    assert manifest["artifacts"]["secret_rotation_smoke"]["artifact_type"] == "secret_rotation_smoke_report.v1"
    assert summary["secret_rotation_smoke_attached"] is True
    assert summary["secret_rotation_smoke_passed"] is True
    assert summary["secret_rotation_smoke_service_identity_count"] == 4
    assert summary["secret_rotation_smoke_active_version_advanced"] is True
    assert summary["secret_rotation_smoke_old_versions_revoked"] is True
    assert summary["secret_rotation_smoke_orchestrator_secret_injection_passed"] is True
    assert summary["secret_rotation_smoke_plaintext_secret_material_persisted"] is False
    assert not any(
        item["gap"] == "orchestrator_service_identity_and_secret_injection"
        for item in manifest["p0_gap_backlog"]
    )
    assert any(item["gap"] == "production_secret_rotation" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "dagster_daemon_or_schedule_tick_history" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "secret_rotation_smoke_failed" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_uses_secret_rotation_ops_to_close_production_secret_gaps(
    tmp_path: Path,
) -> None:
    trino_security = write_json_artifact(
        tmp_path / "trino-runtime-security-smoke-report.json",
        {
            "artifact_type": "trino_runtime_security_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_secret_rotation",
                    "production_cloud_kms_key_rotation",
                ]
            },
            "summary": {
                "query_mode": "iceberg_jdbc_catalog_minio_s3_file_access_control",
                "source_row_count": 4,
                "allowed_query_passed": True,
                "allowed_write_blocked": True,
                "denied_query_blocked": True,
                "unknown_user_blocked": True,
                "security_probe_admin_unfiltered": True,
                "row_level_filter_enforced": True,
                "column_masking_enforced": True,
                "centralized_audit_sink_passed": True,
                "runtime_security_audit_event_count": 8,
                "runtime_security_audit_failed_event_count": 0,
                "all_access_denied_errors_verified": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    secret_ops = write_secret_rotation_ops_review_report(
        tmp_path / "secret-rotation-ops",
        environment="staging",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="staging",
        generated_at="2026-06-16T12:05:00Z",
        trino_runtime_security_smoke_report_path=trino_security,
        secret_rotation_ops_report_path=secret_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert manifest["artifacts"]["secret_rotation_ops"]["attached"] is True
    assert summary["secret_rotation_ops_attached"] is True
    assert summary["secret_rotation_ops_passed"] is True
    assert summary["secret_rotation_ops_environment"] == "staging"
    assert summary["secret_rotation_ops_readiness_state"] == "production_like_ready"
    assert summary["secret_rotation_ops_mode"] == "managed_secret_manager_evidence"
    assert summary["secret_rotation_ops_p0_service_count"] > 0
    assert summary["secret_rotation_ops_covered_service_count"] == summary["secret_rotation_ops_p0_service_count"]
    assert summary["secret_rotation_ops_failed_service_count"] == 0
    assert summary["secret_rotation_ops_managed_secret_manager_ha"] is True
    assert summary["secret_rotation_ops_kms_hsm_custody"] is True
    assert summary["secret_rotation_ops_audit_sink_siem_exported"] is True
    assert summary["secret_rotation_ops_release_gate_passed"] is True
    assert "production_secret_rotation" not in gap_names
    assert "production_cloud_kms_key_rotation" not in gap_names
    assert "platform-runtime-iac" in blocker_capabilities


def test_production_review_pack_keeps_production_secret_gap_for_local_secret_ops_report(
    tmp_path: Path,
) -> None:
    trino_security = write_json_artifact(
        tmp_path / "trino-runtime-security-smoke-report.json",
        {
            "artifact_type": "trino_runtime_security_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": ["production_secret_rotation"]},
            "summary": {
                "query_mode": "iceberg_jdbc_catalog_minio_s3_file_access_control",
                "source_row_count": 4,
                "allowed_query_passed": True,
                "allowed_write_blocked": True,
                "denied_query_blocked": True,
                "unknown_user_blocked": True,
                "security_probe_admin_unfiltered": True,
                "row_level_filter_enforced": True,
                "column_masking_enforced": True,
                "centralized_audit_sink_passed": True,
                "runtime_security_audit_event_count": 8,
                "runtime_security_audit_failed_event_count": 0,
                "all_access_denied_errors_verified": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    secret_ops = write_secret_rotation_ops_review_report(
        tmp_path / "secret-rotation-ops",
        environment="local",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        trino_runtime_security_smoke_report_path=trino_security,
        secret_rotation_ops_report_path=secret_ops,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert summary["secret_rotation_ops_attached"] is True
    assert summary["secret_rotation_ops_passed"] is False
    assert summary["secret_rotation_ops_release_gate_passed"] is False
    assert "production_secret_rotation" in gap_names


def test_production_review_pack_attaches_dagster_orchestration_smoke_report(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live-lakehouse-run",
        release_id="dagster-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        ingested_at="2026-01-15T09:15:05Z",
        built_at="2026-01-15T09:15:10Z",
        evaluation_time="2026-01-15T09:15:15Z",
    )
    object_store = write_object_store_commit_smoke_report(
        ROOT,
        tmp_path / "object-store-commit-smoke-report.json",
        output_dir=tmp_path / "object-store-run",
        live_lakehouse_smoke_report_path=live.output_path,
        bucket="enterprise-dp-review-pack",
        endpoint_url="http://fake-minio.local",
        release_id="dagster-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        s3_client_override=ReviewPackFakeS3(tmp_path / "fake-s3"),
    )
    trino = write_trino_sql_runtime_smoke_report(
        ROOT,
        tmp_path / "trino-sql-runtime-smoke-report.json",
        output_dir=tmp_path / "trino-run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="dagster-review-pack",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=ReviewPackFakeTrino(),
        wait_interval_seconds=0,
    )
    dagster_smoke = write_dagster_orchestration_smoke_report(
        ROOT,
        tmp_path / "dagster-orchestration-smoke-report.json",
        output_dir=tmp_path / "dagster-run",
        live_lakehouse_smoke_report_path=live.output_path,
        object_store_smoke_report_path=object_store.output_path,
        trino_sql_smoke_report_path=trino.output_path,
        release_id="dagster-review-pack",
        generated_at="2026-01-15T09:15:20Z",
    )
    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        live_lakehouse_smoke_report_path=live.output_path,
        object_store_smoke_report_path=object_store.output_path,
        trino_sql_smoke_report_path=trino.output_path,
        dagster_orchestration_smoke_report_path=dagster_smoke.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]

    assert manifest["artifacts"]["dagster_orchestration_smoke"]["attached"] is True
    assert manifest["artifacts"]["dagster_orchestration_smoke"]["artifact_type"] == "dagster_orchestration_smoke_report.v1"
    assert summary["dagster_orchestration_smoke_attached"] is True
    assert summary["dagster_orchestration_smoke_passed"] is True
    assert summary["dagster_orchestration_smoke_run_status"] == "SUCCESS"
    assert summary["dagster_orchestration_smoke_event_count"] > 0
    assert summary["dagster_orchestration_smoke_op_success_count"] >= 4
    assert summary["dagster_orchestration_smoke_validated_report_count"] == 3
    assert not any(item["gap"] == "dagster_orchestration_smoke_not_attached" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "dagster_or_airflow_run_history" for item in manifest["p0_gap_backlog"])
    assert not any(item["gap"] == "orchestrator_run_history" for item in manifest["p0_gap_backlog"])
    assert any(item["gap"] == "production_backfill_materialization_history" for item in manifest["p0_gap_backlog"])


def test_production_review_pack_uses_dagster_day2_release_gate_for_tick_retry_and_backfill_gaps(
    tmp_path: Path,
) -> None:
    production_orchestration_gaps = [
        "dagster_daemon_or_schedule_tick_history",
        "distributed_executor_or_kubernetes_run_launcher",
        "production_retry_backoff_runtime_policy",
        "production_backfill_materialization_history",
    ]
    dagster_orchestration = write_json_artifact(
        tmp_path / "dagster-orchestration-smoke-report.json",
        {
            "artifact_type": "dagster_orchestration_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": production_orchestration_gaps},
            "summary": {
                "job_name": "finance_benefit_reconciliation_runtime_smoke",
                "run_id": "dagster-run-day2-review",
                "run_status": "SUCCESS",
                "event_count": 29,
                "op_success_count": 4,
                "validated_report_count": 3,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    dagster_day2 = write_dagster_day2_smoke_report(
        ROOT,
        tmp_path / "dagster-day2-smoke-report.json",
        output_dir=tmp_path / "dagster-day2-run",
        release_id="dagster-day2-review-pack",
        generated_at="2026-01-15T09:15:20Z",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        dagster_orchestration_smoke_report_path=dagster_orchestration,
        dagster_day2_smoke_report_path=dagster_day2.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["artifacts"]["dagster_day2_smoke"]["attached"] is True
    assert manifest["artifacts"]["dagster_day2_smoke"]["artifact_type"] == "dagster_day2_smoke_report.v1"
    assert summary["dagster_day2_smoke_attached"] is True
    assert summary["dagster_day2_smoke_passed"] is True
    assert summary["dagster_day2_smoke_run_status"] == "SUCCESS"
    assert summary["dagster_day2_smoke_schedule_tick_history_passed"] is True
    assert summary["dagster_day2_smoke_retry_policy_verified"] is True
    assert summary["dagster_day2_smoke_retry_policy_backoff_seconds"] > 0
    assert summary["dagster_day2_smoke_backfill_materialization_history_passed"] is True
    assert summary["dagster_day2_smoke_distributed_executor_verified"] is False
    assert summary["dagster_day2_release_gate_passed"] is True
    assert summary["dagster_day2_smoke_asset_materialization_event_count"] == 3
    assert "dagster_day2_smoke_failed" not in gap_names
    assert "dagster_orchestration_smoke_not_attached" not in gap_names
    assert "dagster_daemon_or_schedule_tick_history" not in gap_names
    assert "production_retry_backoff_runtime_policy" not in gap_names
    assert "production_backfill_materialization_history" not in gap_names
    assert "distributed_executor_or_kubernetes_run_launcher" in gap_names


def test_production_review_pack_uses_orchestration_runtime_ops_for_production_runtime_gaps(
    tmp_path: Path,
) -> None:
    production_orchestration_gaps = [
        "dagster_daemon_or_schedule_tick_history",
        "distributed_executor_or_kubernetes_run_launcher",
        "production_retry_backoff_runtime_policy",
        "production_backfill_materialization_history",
        "orchestrator_service_identity_and_secret_injection",
    ]
    dagster_orchestration = write_json_artifact(
        tmp_path / "dagster-orchestration-smoke-report.json",
        {
            "artifact_type": "dagster_orchestration_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": production_orchestration_gaps},
            "summary": {
                "job_name": "finance_benefit_reconciliation_runtime_smoke",
                "run_id": "dagster-run-live-runtime-review",
                "run_status": "SUCCESS",
                "event_count": 29,
                "op_success_count": 4,
                "validated_report_count": 3,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    orchestration_runtime = write_orchestration_runtime_review_report(
        tmp_path / "orchestration-runtime",
        environment="staging",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="staging",
        generated_at="2026-06-16T12:05:00Z",
        dagster_orchestration_smoke_report_path=dagster_orchestration,
        orchestration_runtime_ops_report_path=orchestration_runtime,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("source") == "control_tower_blocker"
    }

    assert manifest["artifacts"]["orchestration_runtime_ops"]["attached"] is True
    assert summary["orchestration_runtime_ops_attached"] is True
    assert summary["orchestration_runtime_ops_passed"] is True
    assert summary["orchestration_runtime_release_gate_passed"] is True
    assert summary["orchestration_runtime_ops_kubernetes_run_launcher_enabled"] is True
    assert summary["orchestration_runtime_ops_managed_run_storage"] is True
    assert summary["orchestration_runtime_ops_secret_injection_verified"] is True
    assert summary["runtime_iac_release_gate_passed"] is False
    assert "orchestration_runtime_ops_failed" not in gap_names
    for gap in production_orchestration_gaps:
        assert gap not in gap_names
    assert "platform-runtime-iac" in blocker_capabilities


def test_production_review_pack_keeps_orchestration_runtime_gate_closed_for_local_evidence(
    tmp_path: Path,
) -> None:
    dagster_orchestration = write_json_artifact(
        tmp_path / "dagster-orchestration-smoke-report.json",
        {
            "artifact_type": "dagster_orchestration_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": ["distributed_executor_or_kubernetes_run_launcher"]},
            "summary": {"run_status": "SUCCESS", "failed_check_count": 0, "failed_checks": []},
        },
    )
    orchestration_runtime = write_orchestration_runtime_review_report(
        tmp_path / "orchestration-runtime",
        environment="local",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        dagster_orchestration_smoke_report_path=dagster_orchestration,
        orchestration_runtime_ops_report_path=orchestration_runtime,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["summary"]["orchestration_runtime_ops_passed"] is False
    assert manifest["summary"]["orchestration_runtime_release_gate_passed"] is False
    assert "orchestration_runtime_ops_failed" in gap_names
    assert "distributed_executor_or_kubernetes_run_launcher" in gap_names


def test_production_review_pack_blocks_orchestration_runtime_environment_mismatch(
    tmp_path: Path,
) -> None:
    orchestration_runtime = write_orchestration_runtime_review_report(
        tmp_path / "orchestration-runtime",
        environment="staging",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        orchestration_runtime_ops_report_path=orchestration_runtime,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert manifest["summary"]["orchestration_runtime_ops_passed"] is True
    assert manifest["summary"]["orchestration_runtime_ops_environment"] == "staging"
    assert manifest["summary"]["orchestration_runtime_release_gate_passed"] is False
    assert "orchestration_runtime_ops_failed" in gap_names


def test_production_review_pack_keeps_dagster_day2_release_gate_closed_without_backoff(
    tmp_path: Path,
) -> None:
    production_orchestration_gaps = [
        "dagster_daemon_or_schedule_tick_history",
        "distributed_executor_or_kubernetes_run_launcher",
        "production_retry_backoff_runtime_policy",
        "production_backfill_materialization_history",
    ]
    dagster_orchestration = write_json_artifact(
        tmp_path / "dagster-orchestration-smoke-report.json",
        {
            "artifact_type": "dagster_orchestration_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": production_orchestration_gaps},
            "summary": {
                "job_name": "finance_benefit_reconciliation_runtime_smoke",
                "run_id": "dagster-run-day2-review",
                "run_status": "SUCCESS",
                "event_count": 29,
                "op_success_count": 4,
                "validated_report_count": 3,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    dagster_day2 = write_json_artifact(
        tmp_path / "dagster-day2-smoke-report.json",
        {
            "artifact_type": "dagster_day2_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {"not_covered": ["distributed_executor_or_kubernetes_run_launcher"]},
            "summary": {
                "job_name": "finance_benefit_reconciliation_day2_controls",
                "run_id": "dagster-day2-no-backoff",
                "run_status": "SUCCESS",
                "schedule_tick_count": 1,
                "schedule_tick_history_passed": True,
                "retry_policy_max_retries": 2,
                "retry_policy_backoff_seconds": 0,
                "retry_event_count": 1,
                "retry_restart_count": 1,
                "retry_policy_verified": True,
                "backfill_partition_count": 3,
                "asset_materialization_event_count": 3,
                "backfill_materialization_history_passed": True,
                "distributed_executor_verified": False,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        dagster_orchestration_smoke_report_path=dagster_orchestration,
        dagster_day2_smoke_report_path=dagster_day2,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    gap_names = {item["gap"] for item in manifest["p0_gap_backlog"]}

    assert summary["dagster_day2_smoke_passed"] is True
    assert summary["dagster_day2_release_gate_passed"] is False
    for gap in production_orchestration_gaps:
        assert gap in gap_names


def test_production_review_pack_cli_returns_zero_for_generated_not_ready_pack(tmp_path: Path) -> None:
    output_dir = tmp_path / "review-pack"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "production-review-pack",
            "--root",
            str(ROOT),
            "--output-dir",
            str(output_dir),
            "--environment",
            "local",
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    manifest = json.loads((output_dir / "production-review-pack.json").read_text(encoding="utf-8"))

    assert summary["partner_review_ready"] is True
    assert summary["production_ready"] is False
    assert summary["data_plane_smoke_passed"] is True
    assert summary["event_backbone_smoke_attached"] is False
    assert summary["event_backbone_smoke_passed"] is None
    assert summary["ingestion_runtime_attached"] is False
    assert summary["ingestion_runtime_passed"] is None
    assert summary["catalog_lineage_ops_attached"] is False
    assert summary["catalog_lineage_ops_passed"] is None
    assert summary["catalog_lineage_release_gate_passed"] is False
    assert summary["semantic_metric_serving_ops_attached"] is False
    assert summary["semantic_metric_serving_ops_passed"] is None
    assert summary["semantic_metric_serving_release_gate_passed"] is False
    assert summary["source_activation_ops_attached"] is False
    assert summary["source_activation_ops_passed"] is None
    assert summary["source_onboarding_release_gate_passed"] is False
    assert summary["runtime_readiness_external_attached"] is False
    assert summary["runtime_iac_release_gate_passed"] is False
    assert summary["schema_registry_runtime_smoke_attached"] is False
    assert summary["schema_registry_runtime_smoke_passed"] is None
    assert summary["schema_registry_attestation_attached"] is False
    assert summary["schema_registry_attestation_passed"] is None
    assert summary["schema_registry_ops_attached"] is False
    assert summary["schema_registry_ops_passed"] is None
    assert summary["schema_registry_release_gate_passed"] is False
    assert summary["schema_registry_auth_smoke_attached"] is False
    assert summary["schema_registry_auth_smoke_passed"] is None
    assert summary["schema_registry_storage_smoke_attached"] is False
    assert summary["schema_registry_storage_smoke_passed"] is None
    assert summary["broker_acl_smoke_attached"] is False
    assert summary["broker_acl_smoke_passed"] is None
    assert summary["transactional_outbox_smoke_attached"] is False
    assert summary["transactional_outbox_smoke_passed"] is None
    assert summary["live_bronze_ingestion_smoke_attached"] is False
    assert summary["live_bronze_ingestion_smoke_passed"] is None
    assert summary["live_quality_slo_smoke_attached"] is False
    assert summary["live_quality_slo_smoke_passed"] is None
    assert summary["live_lakehouse_smoke_attached"] is False
    assert summary["live_lakehouse_smoke_passed"] is None
    assert summary["iceberg_catalog_smoke_attached"] is False
    assert summary["iceberg_catalog_smoke_passed"] is None
    assert summary["object_store_smoke_attached"] is False
    assert summary["object_store_smoke_passed"] is None
    assert summary["trino_sql_smoke_attached"] is False
    assert summary["trino_sql_smoke_passed"] is None
    assert summary["trino_iceberg_minio_smoke_attached"] is False
    assert summary["trino_iceberg_minio_smoke_passed"] is None
    assert summary["catalog_cross_engine_smoke_attached"] is False
    assert summary["catalog_cross_engine_smoke_passed"] is None
    assert summary["trino_runtime_security_smoke_attached"] is False
    assert summary["trino_runtime_security_smoke_passed"] is None
    assert summary["policy_decision_smoke_attached"] is False
    assert summary["policy_decision_smoke_passed"] is None
    assert summary["oidc_auth_smoke_attached"] is False
    assert summary["oidc_auth_smoke_passed"] is None
    assert summary["access_privacy_release_gate_passed"] is False
    assert summary["secret_rotation_smoke_attached"] is False
    assert summary["secret_rotation_smoke_passed"] is None
    assert summary["secret_rotation_ops_attached"] is False
    assert summary["secret_rotation_ops_passed"] is None
    assert summary["secret_rotation_ops_release_gate_passed"] is False
    assert summary["dagster_orchestration_smoke_attached"] is False
    assert summary["dagster_orchestration_smoke_passed"] is None
    assert summary["dagster_day2_smoke_attached"] is False
    assert summary["dagster_day2_smoke_passed"] is None
    assert summary["dagster_day2_release_gate_passed"] is False
    assert summary["portfolio_release_smoke_attached"] is False
    assert summary["portfolio_release_smoke_passed"] is None
    assert summary["control_tower_blocker_count"] == manifest["summary"]["control_tower_blocker_count"]


def test_production_review_pack_uses_runtime_iac_evidence_to_close_platform_runtime_iac_gap(
    tmp_path: Path,
) -> None:
    runtime_evidence = write_runtime_review_evidence_set(tmp_path / "runtime", environment="staging")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="staging",
        generated_at="2026-06-16T12:05:00Z",
        runtime_iac_plan_path=runtime_evidence["iac_plan"],
        runtime_iac_apply_path=runtime_evidence["iac_apply"],
        runtime_drift_report_path=runtime_evidence["drift_report"],
        runtime_backup_report_path=runtime_evidence["backup_report"],
        runtime_health_report_path=runtime_evidence["health_report"],
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    platform_runtime_blockers = [
        item
        for item in manifest["p0_gap_backlog"]
        if item.get("capability_id") == "platform-runtime-iac"
    ]

    assert summary["runtime_readiness_external_attached"] is True
    assert summary["runtime_readiness_passed"] is True
    assert summary["runtime_readiness_environment"] == "staging"
    assert summary["runtime_readiness_state"] == "production_like_ready"
    assert summary["runtime_readiness_failed_gate_count"] == 0
    assert summary["runtime_iac_release_gate_passed"] is True
    assert summary["runtime_deployed_service_count"] == summary["runtime_required_p0_service_count"]
    assert platform_runtime_blockers == []


def test_production_review_pack_keeps_platform_runtime_iac_for_local_readiness_report(
    tmp_path: Path,
) -> None:
    local_runtime = write_runtime_readiness_report(
        ROOT,
        tmp_path / "local-runtime-readiness.json",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
    )

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="local",
        generated_at="2026-06-16T12:05:00Z",
        runtime_readiness_report_path=local_runtime.output_path,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    blocker_capabilities = {
        item.get("capability_id")
        for item in manifest["p0_gap_backlog"]
        if item.get("gap") == "p0_capability_target_met"
    }

    assert summary["runtime_readiness_external_attached"] is True
    assert summary["runtime_readiness_passed"] is True
    assert summary["runtime_readiness_environment"] == "local"
    assert summary["runtime_iac_release_gate_passed"] is False
    assert "platform-runtime-iac" in blocker_capabilities


def test_production_review_pack_keeps_platform_runtime_iac_for_prod_missing_dr(
    tmp_path: Path,
) -> None:
    runtime_evidence = write_runtime_review_evidence_set(tmp_path / "runtime", environment="prod")

    result = write_production_review_pack(
        ROOT,
        tmp_path / "review-pack",
        environment="prod",
        generated_at="2026-06-16T12:05:00Z",
        runtime_iac_plan_path=runtime_evidence["iac_plan"],
        runtime_iac_apply_path=runtime_evidence["iac_apply"],
        runtime_drift_report_path=runtime_evidence["drift_report"],
        runtime_backup_report_path=runtime_evidence["backup_report"],
        runtime_health_report_path=runtime_evidence["health_report"],
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    summary = manifest["summary"]
    platform_runtime_blockers = [
        item
        for item in manifest["p0_gap_backlog"]
        if item.get("capability_id") == "platform-runtime-iac"
    ]

    assert summary["runtime_readiness_external_attached"] is True
    assert summary["runtime_readiness_passed"] is False
    assert summary["runtime_readiness_environment"] == "prod"
    assert summary["runtime_readiness_failed_gate_count"] > 0
    assert summary["runtime_iac_release_gate_passed"] is False
    assert platform_runtime_blockers


def test_production_review_pack_cli_accepts_event_backbone_smoke_report(tmp_path: Path) -> None:
    def failing_runner(args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        return CommandResult(tuple(args), 1, "", "Cannot connect to the Docker daemon")

    event_result = write_event_backbone_smoke_report(
        ROOT,
        tmp_path / "event-backbone-smoke-report.json",
        output_dir=tmp_path / "event-backbone-run",
        release_id="event-backbone-smoke-fail",
        generated_at="2026-01-15T09:15:20Z",
        command_runner=failing_runner,
    )
    output_dir = tmp_path / "review-pack"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "production-review-pack",
            "--root",
            str(ROOT),
            "--output-dir",
            str(output_dir),
            "--environment",
            "local",
            "--generated-at",
            "2026-06-16T12:05:00Z",
            "--event-backbone-smoke-report",
            str(event_result.output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    manifest = json.loads((output_dir / "production-review-pack.json").read_text(encoding="utf-8"))

    assert summary["event_backbone_smoke_attached"] is True
    assert summary["event_backbone_smoke_passed"] is False
    assert summary["ingestion_runtime_attached"] is False
    assert summary["ingestion_runtime_passed"] is None
    assert manifest["artifacts"]["event_backbone_smoke"]["attached"] is True
    assert any(item["gap"] == "event_backbone_smoke_failed" for item in manifest["p0_gap_backlog"])


class ReviewPackFakeS3:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.buckets: set[str] = set()
        self.metadata: dict[tuple[str, str], dict[str, str]] = {}
        self.sse: dict[tuple[str, str], str | None] = {}
        self.encryption: dict[str, dict] = {}
        self.policy_enabled: dict[str, bool] = {}

    def head_bucket(self, *, Bucket: str) -> dict:
        if Bucket not in self.buckets:
            raise Exception("NoSuchBucket")
        return {}

    def create_bucket(self, *, Bucket: str) -> dict:
        self.buckets.add(Bucket)
        (self.root / Bucket).mkdir(parents=True, exist_ok=True)
        return {}

    def put_bucket_encryption(self, *, Bucket: str, ServerSideEncryptionConfiguration: dict) -> dict:
        assert Bucket in self.buckets
        self.encryption[Bucket] = ServerSideEncryptionConfiguration
        return {}

    def get_bucket_encryption(self, *, Bucket: str) -> dict:
        assert Bucket in self.buckets
        return {"ServerSideEncryptionConfiguration": self.encryption[Bucket]}

    def put_bucket_policy(self, *, Bucket: str, Policy: str) -> dict:
        assert Bucket in self.buckets
        self.policy_enabled[Bucket] = True
        return {}

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ServerSideEncryption: str | None = None,
        Metadata: dict | None = None,
    ) -> dict:
        assert Bucket in self.buckets
        if self.policy_enabled.get(Bucket) and ServerSideEncryption != "AES256":
            raise ClientError(
                {"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
                "PutObject",
            )
        target = self.root / Bucket / Key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(Body)
        self.metadata[(Bucket, Key)] = dict(Metadata or {})
        self.sse[(Bucket, Key)] = ServerSideEncryption
        return {}

    def upload_file(self, Filename: str, Bucket: str, Key: str, ExtraArgs: dict | None = None) -> None:
        assert Bucket in self.buckets
        if self.policy_enabled.get(Bucket) and (ExtraArgs or {}).get("ServerSideEncryption") != "AES256":
            raise ClientError(
                {"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
                "PutObject",
            )
        target = self.root / Bucket / Key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Filename, target)
        self.metadata[(Bucket, Key)] = dict((ExtraArgs or {}).get("Metadata", {}))
        self.sse[(Bucket, Key)] = (ExtraArgs or {}).get("ServerSideEncryption")

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        path = self.root / Bucket / Key
        data = path.read_bytes()
        return {
            "ETag": f'"fake-{len(data)}"',
            "ContentLength": len(data),
            "Metadata": self.metadata.get((Bucket, Key), {}),
            "ServerSideEncryption": self.sse.get((Bucket, Key)),
        }

    def download_file(self, Bucket: str, Key: str, Filename: str) -> None:
        source = self.root / Bucket / Key
        target = Path(Filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def write_runtime_review_evidence_set(
    base_dir: Path,
    *,
    environment: str,
    include_dr: bool = False,
    source_kind: str = "ci_tool_output",
    destructive_change_count: int = 0,
) -> dict[str, Path]:
    service_ids = sorted(REQUIRED_P0_SERVICES)
    plan_path = base_dir / "opentofu-plan.json"
    state_path = base_dir / "opentofu-state.json"
    health_path = base_dir / "health-checks.json"
    backup_path = base_dir / "backup-checks.json"
    dr_path = base_dir / "dr-exercise.json"
    destructive_services = set(service_ids[:destructive_change_count])
    write_json_artifact(
        plan_path,
        {
            "format_version": "1.0",
            "terraform_version": "1.10.0",
            "resource_changes": [
                {
                    "address": f"module.{service_id}.terraform_data.runtime",
                    "mode": "managed",
                    "type": "terraform_data",
                    "name": "runtime",
                    "change": {"actions": ["delete"] if service_id in destructive_services else ["no-op"]},
                }
                for service_id in service_ids
            ],
            "resource_drift": [],
        },
    )
    write_json_artifact(
        state_path,
        {
            "format_version": "1.0",
            "terraform_version": "1.10.0",
            "values": {
                "root_module": {
                    "resources": [
                        {
                            "address": f"module.{service_id}.terraform_data.runtime",
                            "mode": "managed",
                            "type": "terraform_data",
                            "name": "runtime",
                            "values": {"service_id": service_id},
                            "sensitive_values": {},
                        }
                        for service_id in service_ids
                    ]
                }
            },
        },
    )
    write_json_artifact(
        health_path,
        {"checks": [{"service_id": service_id, "status": "passed"} for service_id in service_ids]},
    )
    write_json_artifact(
        backup_path,
        {"backups": [{"service_id": service_id, "status": "passed", "restore_tested": True} for service_id in service_ids]},
    )
    if include_dr:
        write_json_artifact(
            dr_path,
            {
                "exercise": {"status": "passed", "rto_minutes": 60, "rpo_minutes": 15},
                "covered_services": service_ids,
            },
        )
    pack = write_runtime_iac_evidence_pack(
        ROOT,
        base_dir / "normalized-pack",
        environment=environment,
        plan_json_path=plan_path,
        state_json_path=state_path,
        health_checks_path=health_path,
        backup_checks_path=backup_path,
        dr_exercise_path=dr_path if include_dr else None,
        source_kind=source_kind,
        generated_at="2026-06-16T00:00:00Z",
        valid_until="2026-06-17T12:05:00Z",
        git_sha="0123456789abcdef0123456789abcdef01234567",
        ci_run_id="ci-runtime-123",
        issuer_tool="opentofu",
        issuer_tool_version="1.10.0",
        artifact_base_uri=f"s3://runtime-evidence/{environment}/review-pack",
        change_request_id="CHG-RUNTIME-123" if environment == "prod" else None,
    )
    return {kind: Path(entry["path"]) for kind, entry in pack.manifest["artifacts"].items()}


def write_workload_benchmark_report(
    path: Path,
    *,
    environment: str,
    source_kind: str = "ci_tool_output",
    input_record_count: int = 1_500_000,
) -> Path:
    return write_json_artifact(
        path,
        {
            "artifact_type": "workload_benchmark_report.v1",
            "report_version": 1,
            "benchmark_id": f"{environment}-finance-scale-001",
            "environment": environment,
            "source_kind": source_kind,
            "passed": True,
            "generated_at": "2026-06-16T12:00:00Z",
            "summary": {
                "target_use_case": "finance-benefit-reconciliation",
                "scale_profile": "managed_staging",
                "input_record_count": input_record_count,
                "duration_minutes": 15,
                "throughput_records_per_second": 2_500,
                "query_concurrency": 32,
                "p95_query_latency_ms": 1_250,
                "max_consumer_lag_records": 350,
                "error_rate": 0.0001,
                "freshness_slo_passed": True,
                "zero_data_loss_verified": True,
            },
            "evidence": {
                "source_artifact_uri": f"s3://runtime-benchmarks/{environment}/finance-scale-001/results.json",
                "source_artifact_hash": "sha256:" + ("a" * 64),
                "runner": "k6-spark-trino-benchmark",
                "ci_run_id": "ci-workload-benchmark-001",
            },
        },
    )


def write_catalog_lineage_review_ops(base_dir: Path, *, environment: str) -> Path:
    catalog_path, openlineage_path, semantic_views_path = write_catalog_lineage_review_inputs(base_dir, environment)
    publish_path = None
    receipt_path = None
    if environment in {"staging", "prod"}:
        publish = write_catalog_publish_manifest(
            catalog_path,
            base_dir / "publish" / "catalog-publish.json",
            target_system="datahub",
            environment=environment,
            endpoint=f"https://datahub.{environment}.enterprise.example",
            openlineage_events_path=openlineage_path,
            semantic_views_manifest_path=semantic_views_path,
            requested_by="data-platform-release-manager",
            change_ticket="CHG-DP-CATALOG-001",
            generated_at="2026-06-16T12:05:00Z",
        )
        publish_path = publish.output_path
        receipt_path = write_catalog_lineage_review_receipt(
            base_dir / "publish" / "catalog-publish-receipt.json",
            environment=environment,
            catalog_path=catalog_path,
            publish_manifest_path=publish_path,
            openlineage_path=openlineage_path,
        )
    result = write_catalog_lineage_ops_report(
        ROOT,
        base_dir / "ops" / "catalog-lineage-ops.json",
        environment=environment,
        catalog_bundle_path=catalog_path,
        catalog_publish_manifest_path=publish_path,
        openlineage_events_path=openlineage_path,
        publish_receipt_path=receipt_path,
        generated_at="2026-06-16T12:05:00Z",
    )
    return result.output_path


def write_catalog_lineage_review_inputs(base_dir: Path, environment: str) -> tuple[Path, Path, Path]:
    catalog_path = base_dir / "catalog" / "catalog-bundle.json"
    openlineage_path = base_dir / "lineage" / "openlineage.jsonl"
    semantic_views_path = base_dir / "serving" / "semantic-views.json"
    ingestion = run_bronze_ingestion(
        ROOT,
        "recommendation.tracking.v1",
        ROOT / "samples" / "recommendation" / "tracking.jsonl",
        base_dir / "ingestion",
        ingested_at="2026-01-15T11:00:05Z",
        ingest_run_id="catalog-lineage-review-pack-ingest",
    )
    recommendation = run_recommendation_pipeline_from_bronze(
        ingestion.approved_path,
        base_dir / "medallion",
        upstream_manifest_path=ingestion.manifest_path,
        snapshot_id="catalog-lineage-review-pack-recsys-snapshot",
        built_at="2026-01-15T11:00:10Z",
    )
    write_catalog_bundle(
        ROOT,
        catalog_path,
        manifest_paths=[ingestion.manifest_path, recommendation.manifest_path],
        generated_at="2026-01-15T12:00:00Z",
    )
    namespace = "enterprise-dp://local" if environment == "local" else f"enterprise-dp://{environment}"
    producer = (
        "https://enterprise-dp.local/openlineage-export"
        if environment == "local"
        else f"https://enterprise-dp.{environment}.example/openlineage-export"
    )
    write_openlineage_events(catalog_path, openlineage_path, namespace=namespace, producer=producer)
    append_catalog_lineage_coverage_events(catalog_path, openlineage_path, namespace=namespace, producer=producer)
    write_semantic_view_manifest(
        ROOT,
        semantic_views_path,
        engine="all",
        generated_at="2026-01-15T12:15:00Z",
    )
    return catalog_path, openlineage_path, semantic_views_path


def append_catalog_lineage_coverage_events(
    catalog_path: Path,
    openlineage_path: Path,
    *,
    namespace: str,
    producer: str,
) -> None:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    existing_text = openlineage_path.read_text(encoding="utf-8") if openlineage_path.is_file() else ""
    existing_names = set()
    for line in existing_text.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        datasets = event.get("inputs", []) + event.get("outputs", [])
        existing_names.update(dataset.get("name") for dataset in datasets if isinstance(dataset, dict))
    events = []
    for product in catalog.get("data_products", []):
        if not isinstance(product, dict) or not isinstance(product.get("name"), str):
            continue
        name = product["name"]
        if name in existing_names:
            continue
        events.append(
            {
                "eventType": "COMPLETE",
                "eventTime": "2026-01-15T12:30:00Z",
                "producer": producer,
                "schemaURL": "https://openlineage.io/spec/OpenLineage.json#/definitions/RunEvent",
                "run": {"runId": f"catalog-lineage-review-{name.replace('.', '-')}"},
                "job": {"namespace": namespace, "name": f"catalog_lineage_coverage_{name.replace('.', '_')}"},
                "inputs": [],
                "outputs": [{"namespace": f"{namespace}/data_products", "name": name}],
            }
        )
    if events:
        with openlineage_path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")


def write_catalog_lineage_review_receipt(
    path: Path,
    *,
    environment: str,
    catalog_path: Path,
    publish_manifest_path: Path,
    openlineage_path: Path,
) -> Path:
    return write_json_artifact(
        path,
        {
            "artifact_type": "catalog_publish_receipt.v1",
            "environment": environment,
            "target": {"system": "datahub", "endpoint": f"https://datahub.{environment}.enterprise.example"},
            "status": "succeeded",
            "published_at": "2026-06-16T12:05:30Z",
            "catalog_bundle_hash": hash_file(catalog_path),
            "catalog_publish_manifest_hash": hash_file(publish_manifest_path),
            "openlineage_hash": hash_file(openlineage_path),
            "entity_count": 1,
            "lineage_edge_count": 1,
        },
    )


def write_semantic_metric_serving_review_ops(base_dir: Path, *, environment: str) -> Path:
    certified_root = build_certified_semantic_review_root(base_dir)
    artifact_dir = base_dir / "artifacts"
    manifest_path = artifact_dir / "semantic-views.json"
    manifest = write_semantic_view_manifest(
        certified_root,
        manifest_path,
        engine="all",
        generated_at="2026-06-16T12:05:00Z",
    )
    certification_path = artifact_dir / "metric-certification.json"
    write_semantic_metric_certification_report(
        certified_root,
        certification_path,
        environment=environment,
        generated_at="2026-06-16T12:05:00Z",
    )
    deployment = {
        "artifact_type": "semantic_serving_deployment_evidence.v1",
        "environment": environment,
        "generated_at": "2026-06-16T12:06:00Z",
        "semantic_view_manifest_hash": hash_file(manifest_path),
        "passed": True,
        "summary": {
            "view_count": len(manifest["views"]),
            "failed_view_count": 0,
        },
        "views": [
            {
                "metric_id": view["metric_id"],
                "engine": view["engine"],
                "view_name": view["view_name"],
                "deployed": True,
                "smoke_test_passed": True,
                "access_policy_checked": True,
            }
            for view in manifest["views"]
        ],
    }
    deployment_path = write_json_artifact(artifact_dir / "semantic-serving-deployment.json", deployment)
    usage = {
        "artifact_type": "semantic_metric_usage_evidence.v1",
        "environment": environment,
        "generated_at": "2026-06-16T12:06:30Z",
        "passed": True,
        "summary": {
            "metric_count": manifest["summary"]["metric_count"],
            "usage_tracking_disabled_count": 0,
        },
        "metrics": [
            {
                "metric_id": metric_id,
                "usage_tracking_enabled": True,
                "active_consumer_count": 1,
                "last_queried_at": "2026-06-16T12:06:30Z",
            }
            for metric_id in sorted({view["metric_id"] for view in manifest["views"]})
        ],
    }
    usage_path = write_json_artifact(artifact_dir / "semantic-metric-usage.json", usage)
    result = write_semantic_metric_serving_ops_report(
        certified_root,
        artifact_dir / "semantic-metric-serving-ops.json",
        environment=environment,
        semantic_view_manifest_path=manifest_path,
        metric_certification_report_path=certification_path,
        serving_deployment_evidence_path=deployment_path,
        usage_evidence_path=usage_path,
        generated_at="2026-06-16T12:07:00Z",
    )
    return result.output_path


def write_source_activation_review_ops(base_dir: Path, *, environment: str) -> Path:
    source_registry_path = ROOT / "platform" / "ingestion" / "source-registry.yaml"
    source_registry = yaml.safe_load(source_registry_path.read_text(encoding="utf-8"))
    sources = [source for source in source_registry["sources"] if isinstance(source, dict)]
    registry_hash = hash_file(source_registry_path)
    production_like = environment in {"staging", "prod"}
    rows = [
        source_activation_review_row(
            source,
            environment=environment,
            registry_hash=registry_hash,
            runtime_attached=production_like,
        )
        for source in sources
    ]
    p0_rows = [row for row in rows if row["priority"] == "P0"]
    summary = {
        "source_count": len(rows),
        "p0_source_count": len(p0_rows),
        "active_count": len(rows),
        "p0_active_count": len(p0_rows),
        "revoked_count": 0,
        "pending_count": 0,
        "failed_count": 0,
        "stale_count": 0,
        "unactivated_count": 0,
        "p0_unactivated_count": 0,
        "production_ready_count": len(rows),
        "p0_production_ready_count": len(p0_rows),
        "expiring_soon_count": 0,
        "expired_count": 0,
        "registry_drift_count": 0,
        "runtime_readiness_attached_count": len(rows) if production_like else 0,
        "p0_runtime_readiness_attached_count": len(p0_rows) if production_like else 0,
        "runtime_readiness_issue_count": 0,
        "p0_runtime_readiness_issue_count": 0,
        "evidence_integrity_issue_count": 0,
        "p0_evidence_integrity_issue_count": 0,
        "pointer_issue_count": 0,
        "p0_activation_gap_count": 0,
        "p0_critical_issue_count": 0,
        "p0_next_action_count": 0,
        "critical_issue_count": 0,
        "by_activation_state": {"active": len(rows)},
        "by_risk_state": {"ok": len(rows)},
    }
    report = {
        "artifact_type": "source_activation_ops_report.v1",
        "report_version": 1,
        "capability_id": "source-onboarding",
        "report_id": fake_sha256("source-activation-ops-report-id"),
        "generated_at": "2026-06-16T12:05:00Z",
        "environment": environment,
        "mode": "runtime_attested" if production_like else "local_preflight",
        "readiness_state": "production_like_ready" if production_like else "local_preflight_ready",
        "ledger": {
            "path": "governance/source-activations.yaml",
            "exists": True,
            "hash": fake_sha256("source-activation-ledger"),
            "record_count": len(rows),
            "validation_passed": True,
            "validation_errors": [],
        },
        "source_registry": {
            "path": source_registry_path.as_posix(),
            "current_hash": registry_hash,
        },
        "active_pointer_dir": "governance/source-active-pointers",
        "expiry_warning_days": 30,
        "summary": summary,
        "decision_board": {
            "critical_sources": [],
            "expiring_sources": [],
            "revoked_sources": [],
            "next_actions": [],
        },
        "sources": rows,
        "passed": True,
    }
    return write_json_artifact(base_dir / "source-activation-ops.json", report)


def source_activation_review_row(
    source: dict[str, object],
    *,
    environment: str,
    registry_hash: str,
    runtime_attached: bool,
) -> dict[str, object]:
    source_id = str(source["sourceId"])
    activation_id = f"activation-{source_id}-{environment}"
    return {
        "source_id": source_id,
        "product": source.get("product"),
        "domain": source.get("domain"),
        "priority": source.get("priority"),
        "static_status": source.get("status"),
        "environment": environment,
        "activation_id": activation_id,
        "activation_state": "active",
        "effective_status": "production_ready",
        "business_readiness": "production_ready_verified",
        "block_reason": None,
        "activated_at": "2026-06-16T11:00:00Z",
        "expires_at": "2026-12-16T11:00:00Z",
        "days_to_expiry": 180,
        "readiness_id": fake_sha256(f"{source_id}:readiness").removeprefix("sha256:"),
        "runtime_readiness": {
            "required": runtime_attached,
            "attached": runtime_attached,
            "report_uri": f"s3://runtime-readiness/{environment}/{source_id}.json" if runtime_attached else None,
            "report_hash": fake_sha256(f"{source_id}:runtime-readiness") if runtime_attached else None,
            "runtime_readiness_id": f"runtime-{source_id}-{environment}" if runtime_attached else None,
            "hash_valid": runtime_attached,
            "artifact_verifiable": runtime_attached,
            "hash_matches_artifact": runtime_attached,
            "integrity_issues": [],
        },
        "evidence_integrity": {
            "required": runtime_attached,
            "passed": runtime_attached,
            "issues": [],
            "readiness_report": {
                "uri": f"s3://source-readiness/{environment}/{source_id}.json" if runtime_attached else None,
                "hash": fake_sha256(f"{source_id}:readiness-report") if runtime_attached else None,
                "hash_valid": runtime_attached,
                "exists": runtime_attached,
                "hash_matches": runtime_attached,
                "verifiable": runtime_attached,
            },
            "evidence_bundle": {
                "uri": f"s3://source-readiness/{environment}/{source_id}-bundle.json" if runtime_attached else None,
                "hash": fake_sha256(f"{source_id}:readiness-bundle") if runtime_attached else None,
                "hash_valid": runtime_attached,
                "exists": runtime_attached,
                "hash_matches": runtime_attached,
                "verifiable": runtime_attached,
            },
            "runtime_readiness": {
                "uri": f"s3://runtime-readiness/{environment}/{source_id}.json" if runtime_attached else None,
                "hash": fake_sha256(f"{source_id}:runtime-readiness") if runtime_attached else None,
                "hash_valid": runtime_attached,
                "exists": runtime_attached,
                "hash_matches": runtime_attached,
                "verifiable": runtime_attached,
            },
        },
        "source_registry_hash": registry_hash,
        "current_source_registry_hash": registry_hash,
        "pointer": {
            "path": f"governance/source-active-pointers/{source_id}.{environment}.json",
            "exists": True,
            "hash": fake_sha256(f"{source_id}:pointer"),
            "activation_id": activation_id,
            "activation_state": "active",
            "readiness_id": fake_sha256(f"{source_id}:readiness").removeprefix("sha256:"),
            "expires_at": "2026-12-16T11:00:00Z",
            "ledger_uri": "governance/source-activations.yaml",
            "revoked_activation_id": None,
            "matches_latest_record": True,
            "consistency_state": "consistent",
            "mismatches": [],
        },
        "gate_badges": {
            "schema": "passed",
            "bronzeReplay": "passed",
            "offsetLedger": "passed",
            "bridge": "not_required",
            "privacyTenant": "passed",
            "catalogLineage": "passed",
            "changeControl": "passed",
            "runtimeSlo": "passed" if runtime_attached else "not_required",
        },
        "impacted_use_cases": ["finance-benefit-reconciliation"],
        "issues": [],
        "risk_state": "ok",
        "next_actions": [{"priority": "P3", "action": "no_action", "owner": source.get("product")}],
    }


def write_backfill_readiness_review_report(base_dir: Path, *, environment: str, ready: bool) -> Path:
    evidence = {
        key: {
            "uri": (base_dir / f"{key}.json").as_posix(),
            "hash": fake_sha256(f"backfill:{environment}:{key}"),
            "local": True,
            "override": True,
        }
        for key in (
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
    }
    payload = {
        "artifact_type": "backfill_readiness_report.v1",
        "report_version": 1,
        "capability_id": "backfill-change-governance",
        "readiness_id": fake_sha256(f"backfill:{environment}:readiness"),
        "generated_at": "2026-06-16T12:05:00Z",
        "environment": environment,
        "request_id": "backfill_finance_benefit_reconciliation_staging",
        "mode": "runtime_attested" if ready else "metadata_preflight",
        "readiness_state": "ready" if ready else "blocked",
        "registry_uri": "governance/backfill-requests.yaml",
        "registry_hash": fake_sha256("backfill-registry"),
        "request": {
            "status": "approved",
            "risk_level": "high",
            "operation_type": "backfill",
            "primary_output": "gold.finance_benefit_reconciliation",
        },
        "scope": {
            "primary_output": "gold.finance_benefit_reconciliation",
            "affected_data_products": [
                "silver.finance_benefit_transactions",
                "gold.finance_benefit_reconciliation",
            ],
        },
        "plan": {"concurrencyLockId": "backfill.finance-benefit-reconciliation.20260115"},
        "baseline": {"rollbackTarget": "iceberg-gold-finance-benefit-reconciliation-baseline"},
        "evidence": evidence,
        "summary": {
            "failed_check_count": 0 if ready else 1,
            "passed_check_count": 42 if ready else 41,
            "check_count": 42,
            "evidence_count": 9,
            "attached_evidence_count": 9,
            "request_status": "approved",
            "risk_level": "high",
            "operation_type": "backfill",
            "approved_role_count": 3,
            "approved_roles": ["data_steward", "domain_owner", "platform_owner"],
            "maker_checker_required": True,
            "rollback_required": True,
            "impact_assessment_required": True,
            "communication_required": True,
        },
        "checks": [
            {"name": "runtime_attested_backfill", "passed": ready, "details": {}},
        ],
        "failures": [] if ready else [{"check": "runtime_attested_backfill", "details": {}}],
        "passed": ready,
    }
    return write_json_artifact(base_dir / "backfill-readiness.json", payload)


def write_secret_rotation_ops_review_report(base_dir: Path, *, environment: str) -> Path:
    evidence = write_managed_secret_rotation_review_evidence(
        base_dir / "managed-secret-rotation-evidence.json",
        environment=environment,
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "secret-rotation-ops-report",
            "--root",
            str(ROOT),
            "--output",
            str(base_dir / "secret-rotation-ops.json"),
            "--environment",
            environment,
            "--evidence",
            str(evidence),
            "--generated-at",
            "2026-06-16T12:05:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0 if environment in {"staging", "prod"} else completed.returncode == 1
    return base_dir / "secret-rotation-ops.json"


def write_managed_secret_rotation_review_evidence(path: Path, *, environment: str) -> Path:
    services = p0_runtime_services_for_review()
    payload = {
        "artifact_type": "managed_secret_rotation_evidence.v1",
        "environment": environment,
        "generated_at": "2026-06-16T12:00:00Z",
        "valid_until": "2026-06-17T12:00:00Z",
        "passed": True,
        "secret_manager": {
            "provider": "aws-secrets-manager",
            "ha_enabled": True,
            "kms_key_id": "arn:aws:kms:ap-southeast-1:111122223333:key/dp-runtime",
            "kms_key_hash": fake_sha256("dp-runtime-kms"),
            "hsm_backed": True,
            "cross_region_replication": True,
            "backup_restore_tested": True,
        },
        "controls": {
            "managed_secret_manager_ha": True,
            "workload_identity_federation": True,
            "kms_hsm_custody": True,
            "rotation_policy_enforced": True,
            "old_versions_denied": True,
            "unauthorized_identity_denied": True,
            "missing_secret_denied": True,
            "orchestrator_injection_redacted": True,
            "plaintext_secret_material_persisted": False,
        },
        "service_secrets": [
            {
                "service_id": service["serviceId"],
                "secret_handle": f"secrets://{environment}/dp/{service['serviceId']}",
                "service_identity": f"svc-dp-{service['serviceId']}",
                "identity_mode": "workload_identity",
                "active_version": "v20260616",
                "kms_key_id": "arn:aws:kms:ap-southeast-1:111122223333:key/dp-runtime",
                "key_hash": fake_sha256(f"{service['serviceId']}:key"),
                "rotation_policy_id": "rot-90d-managed",
                "latest_rotation_at": "2026-06-16T11:30:00Z",
                "old_version_revoked": True,
                "old_version_denied": True,
                "unauthorized_identity_denied": True,
                "missing_secret_denied": True,
                "plaintext_secret_material_persisted": False,
            }
            for service in services
        ],
        "audit_sink": {
            "sink_uri": f"siem://enterprise/{environment}/secret-rotation",
            "events_hash": fake_sha256("secret-rotation-audit-events"),
            "event_count": len(services) * 6,
            "failed_event_count": 0,
            "siem_exported": True,
        },
        "attestation": {
            "attached": True,
            "signature_verified": True,
            "subject_hash_matches": True,
            "signing_key_id": "external-auditor-kms-2026",
        },
    }
    return write_json_artifact(path, payload)


def write_catalog_runtime_gap_inputs(tmp_path: Path) -> tuple[Path, Path]:
    trino_iceberg = write_json_artifact(
        tmp_path / "trino-iceberg-minio-smoke-report.json",
        {
            "artifact_type": "trino_iceberg_minio_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_catalog_ha",
                    "cross_engine_commit_compatibility",
                    "production_catalog_concurrency_locking",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "row_count": 3,
                "query_mode": "iceberg_jdbc_catalog_minio_s3",
                "query_passed": True,
                "snapshot_count": 2,
                "iceberg_file_count": 1,
                "minio_object_count": 3,
                "minio_encrypted_object_count": 3,
                "object_store_encryption_policy_enforced": True,
                "trino_iceberg_objects_encrypted": True,
            },
        },
    )
    catalog_cross_engine = write_json_artifact(
        tmp_path / "catalog-cross-engine-smoke-report.json",
        {
            "artifact_type": "catalog_cross_engine_smoke_report.v1",
            "generated_at": "2026-01-15T09:15:20Z",
            "passed": True,
            "runtime_scope": {
                "not_covered": [
                    "production_catalog_ha",
                    "managed_catalog_failover",
                    "production_catalog_backup_restore_pitr",
                ]
            },
            "summary": {
                "failed_check_count": 0,
                "failed_checks": [],
                "catalog_backend": "postgresql_jdbc_catalog",
                "cross_engine_commit_compatibility_passed": True,
                "catalog_concurrency_locking_passed": True,
                "stale_commit_rejected": True,
                "pyiceberg_readback_row_count": 3,
                "snapshot_count_after_pyiceberg": 3,
            },
        },
    )
    return trino_iceberg, catalog_cross_engine


def write_catalog_runtime_review_report(base_dir: Path, *, environment: str) -> Path:
    evidence = write_managed_catalog_runtime_review_evidence(
        base_dir / "managed-catalog-runtime-evidence.json",
        environment=environment,
    )
    result = write_catalog_runtime_ops_report(
        ROOT,
        base_dir / "catalog-runtime-ops.json",
        environment=environment,
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )
    return result.output_path


def write_managed_catalog_runtime_review_evidence(path: Path, *, environment: str) -> Path:
    release_id = f"{environment}-catalog-runtime-release"
    change_ticket = "CHG-DP-CATALOG-20260616"
    warehouse_uri = f"s3://enterprise-dp-{environment}/warehouse"
    service_identity = f"svc-dp-{environment}-table-format"
    upstream_hash = fake_sha256("trino-iceberg-minio-smoke-report")
    payload = {
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
    return write_json_artifact(path, payload)


def write_orchestration_runtime_review_report(base_dir: Path, *, environment: str) -> Path:
    evidence = write_managed_orchestration_runtime_review_evidence(
        base_dir / "managed-orchestration-runtime-evidence.json",
        environment=environment,
    )
    result = write_orchestration_runtime_ops_report(
        ROOT,
        base_dir / "orchestration-runtime-ops.json",
        environment=environment,
        evidence_path=evidence,
        generated_at="2026-06-16T12:05:00Z",
    )
    return result.output_path


def write_managed_orchestration_runtime_review_evidence(path: Path, *, environment: str) -> Path:
    release_id = f"{environment}-orchestration-runtime-release"
    change_ticket = "CHG-DP-ORCH-20260616"
    deployment_id = f"dagster-{environment}-workspace"
    service_identity = f"svc-dp-{environment}-orchestration"
    run_storage_uri = f"postgresql://dagster-run-storage.{environment}.dp.internal/dagster"
    upstream_hash = fake_sha256("dagster-day2-smoke-report")
    payload = {
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
    return write_json_artifact(path, payload)


def p0_runtime_services_for_review() -> list[dict[str, object]]:
    topology = yaml.safe_load((ROOT / "platform" / "runtime" / "topology.yaml").read_text(encoding="utf-8"))
    return [
        service
        for service in topology["runtimeServices"]
        if isinstance(service, dict) and service.get("p0Required") is True
    ]


def fake_sha256(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def build_certified_semantic_review_root(base_dir: Path) -> Path:
    root = base_dir / "certified-root"
    for directory in ("contracts", "domains", "governance", "use-cases"):
        shutil.copytree(ROOT / directory, root / directory)
    (root / "platform").mkdir(parents=True)
    shutil.copytree(ROOT / "platform" / "serving", root / "platform" / "serving")

    registry_path = root / "platform" / "serving" / "semantic-metrics.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    for metric in registry["metrics"]:
        metric["status"] = "certified"
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    return root


def runtime_review_common_evidence(
    artifact_type: str,
    evidence_kind: str,
    environment: str,
    profile_id: str,
    source_kind: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "artifact_type": artifact_type,
        "schema_version": 1,
        "evidence_id": f"{environment}-{evidence_kind}-review-pack",
        "environment": environment,
        "profile_id": profile_id,
        "evidence_kind": evidence_kind,
        "source_kind": source_kind,
        "sample": source_kind == "synthetic_fixture",
        "production_evidence": source_kind != "synthetic_fixture",
        "readiness_claim": "machine_readable_runtime_evidence",
        "status": "passed",
        "generated_at": "2026-06-16T00:00:00Z",
        "valid_until": "2026-06-17T12:05:00Z",
        "issuer": {"tool": "opentofu", "tool_version": "1.10.0", "ci_run_id": "ci-runtime-123"},
        "git_sha": "0123456789abcdef0123456789abcdef01234567",
        "artifact_uri": f"s3://runtime-evidence/{environment}/{evidence_kind}.json",
        "artifact_sha256": "sha256:runtime-evidence",
        "command": "opentofu show -json",
        "exit_code": 0,
        "redacted": True,
    }
    if environment == "prod":
        payload["change_request_id"] = "CHG-RUNTIME-123"
    return payload


def write_json_artifact(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return path


def fake_event_backbone_group_describe(topic: str) -> str:
    return f"""GROUP        fake-group
COORDINATOR  0
STATE        Empty
BALANCER
MEMBERS      0
TOTAL-LAG    0

TOPIC  PARTITION  CURRENT-OFFSET  LOG-START-OFFSET  LOG-END-OFFSET  LAG   MEMBER-ID  CLIENT-ID  HOST
{topic}  0          2               0                 2               0
{topic}  1          2               0                 2               0
{topic}  2          2               0                 2               0
"""


class ReviewPackFakeTrino:
    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> TrinoCommandResult:
        if args[-1] == "trino":
            return TrinoCommandResult(tuple(args), 0, "started", "")
        sql = args[-1]
        if sql == "SELECT 1":
            return TrinoCommandResult(tuple(args), 0, '"1"\n', "")
        if "INSERT INTO" in sql:
            return TrinoCommandResult(tuple(args), 0, "DROP TABLE\nCREATE SCHEMA\nCREATE TABLE\nINSERT: 4 rows\n", "")
        if "GROUP BY reconciliation_status" in sql:
            return TrinoCommandResult(
                tuple(args),
                0,
                '"EXCEPTION","3","17000","16500","-500","-120"\n"MATCHED","1","8000","8000","0","0"\n',
                "",
            )
        raise AssertionError(f"unexpected command: {args}")


class ReviewPackFakeTrinoIceberg:
    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> TrinoCommandResult:
        if "up" in args:
            return TrinoCommandResult(tuple(args), 0, "started", "")
        if "psql" in args:
            assert input_text and "CREATE TABLE IF NOT EXISTS iceberg_tables" in input_text
            return TrinoCommandResult(tuple(args), 0, "CREATE TABLE\nCREATE TABLE\n", "")
        sql = args[-1]
        if sql == "SELECT 1":
            return TrinoCommandResult(tuple(args), 0, '"1"\n', "")
        if sql == "SHOW CATALOGS":
            return TrinoCommandResult(tuple(args), 0, '"iceberg"\n"memory"\n', "")
        if "CREATE TABLE iceberg.finance_iceberg_smoke.finance_benefit_reconciliation" in sql:
            return TrinoCommandResult(tuple(args), 0, "DROP TABLE\nCREATE SCHEMA\nCREATE TABLE\nINSERT: 4 rows\n", "")
        if "GROUP BY reconciliation_status" in sql:
            return TrinoCommandResult(
                tuple(args),
                0,
                '"EXCEPTION","3","17000","16500","-500","-120"\n"MATCHED","1","8000","8000","0","0"\n',
                "",
            )
        if "$snapshots" in sql:
            return TrinoCommandResult(tuple(args), 0, '"2"\n', "")
        if "$files" in sql:
            return TrinoCommandResult(tuple(args), 0, '"1"\n', "")
        raise AssertionError(f"unexpected command: {args}")


class ReviewPackFakeTrinoRuntimeSecurity:
    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> TrinoCommandResult:
        if "up" in args:
            return TrinoCommandResult(tuple(args), 0, "started", "")
        sql = args[-1]
        user = args[args.index("--user") + 1] if "--user" in args else "trino"
        if sql == "SELECT 1":
            return TrinoCommandResult(tuple(args), 0, '"1"\n', "")
        if sql == "SELECT current_user" and user == "dp_allowed":
            return TrinoCommandResult(tuple(args), 0, '"dp_allowed"\n', "")
        if sql.startswith("DROP TABLE IF EXISTS") and "finance_benefit_security_probe" in sql and user == "trino":
            return TrinoCommandResult(tuple(args), 0, "DROP TABLE\nCREATE TABLE\nINSERT: 4 rows\n", "")
        if sql.startswith("SELECT COUNT(*)") and user == "dp_allowed":
            return TrinoCommandResult(tuple(args), 0, '"4"\n', "")
        if sql.startswith("INSERT INTO") and user == "dp_allowed":
            return TrinoCommandResult(tuple(args), 1, "", "Access Denied: Cannot insert into table")
        if sql.startswith("SELECT COUNT(*)") and user == "dp_denied":
            return TrinoCommandResult(tuple(args), 1, "", "Access Denied: Cannot select from table")
        if sql.startswith("SELECT COUNT(*)") and user == "dp_unknown":
            return TrinoCommandResult(tuple(args), 1, "", "Access Denied: Cannot access catalog iceberg")
        if "array_sort(array_agg(DISTINCT beneficiary_id_hash))" in sql and user == "trino":
            return TrinoCommandResult(
                tuple(args),
                0,
                '"4|beneficiary-alpha,beneficiary-beta,beneficiary-delta,beneficiary-gamma"\n',
                "",
            )
        if "array_sort(array_agg(DISTINCT org_id))" in sql and user == "dp_row_filter":
            return TrinoCommandResult(tuple(args), 0, '"2|org-allowed"\n', "")
        if "array_sort(array_agg(DISTINCT beneficiary_id_hash))" in sql and user == "dp_masked":
            return TrinoCommandResult(tuple(args), 0, '"4|MASKED"\n', "")
        raise AssertionError(f"unexpected command: {args}")


class ReviewPackFakeIcebergS3:
    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.encryption: dict[str, dict] = {}
        self.policy_enabled: dict[str, bool] = {}
        self.objects: dict[tuple[str, str], dict] = {}

    def head_bucket(self, *, Bucket: str) -> dict:
        if Bucket not in self.buckets:
            raise Exception("NoSuchBucket")
        return {}

    def create_bucket(self, *, Bucket: str) -> dict:
        self.buckets.add(Bucket)
        return {}

    def put_bucket_encryption(self, *, Bucket: str, ServerSideEncryptionConfiguration: dict) -> dict:
        assert Bucket in self.buckets
        self.encryption[Bucket] = ServerSideEncryptionConfiguration
        return {}

    def get_bucket_encryption(self, *, Bucket: str) -> dict:
        assert Bucket in self.buckets
        return {"ServerSideEncryptionConfiguration": self.encryption[Bucket]}

    def put_bucket_policy(self, *, Bucket: str, Policy: str) -> dict:
        assert Bucket in self.buckets
        self.policy_enabled[Bucket] = True
        self.objects[(Bucket, "warehouse/finance_iceberg_smoke/finance_benefit_reconciliation/data/00000.parquet")] = {
            "Size": 991,
            "ServerSideEncryption": "AES256",
        }
        self.objects[(Bucket, "warehouse/finance_iceberg_smoke/finance_benefit_reconciliation/metadata/00000.metadata.json")] = {
            "Size": 2500,
            "ServerSideEncryption": "AES256",
        }
        self.objects[(Bucket, "warehouse/finance_iceberg_smoke/finance_benefit_reconciliation/metadata/snap-1.avro")] = {
            "Size": 1200,
            "ServerSideEncryption": "AES256",
        }
        return {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ServerSideEncryption: str | None = None) -> dict:
        assert Bucket in self.buckets
        if self.policy_enabled.get(Bucket) and ServerSideEncryption != "AES256":
            raise ClientError(
                {"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
                "PutObject",
            )
        self.objects[(Bucket, Key)] = {
            "Size": len(Body),
            "ServerSideEncryption": ServerSideEncryption,
        }
        return {}

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        item = self.objects[(Bucket, Key)]
        return {
            "ContentLength": item["Size"],
            "ServerSideEncryption": item.get("ServerSideEncryption"),
        }

    def list_objects_v2(self, *, Bucket: str, Prefix: str) -> dict:
        assert Bucket in self.buckets
        contents = [
            {"Key": key, "Size": item["Size"]}
            for (object_bucket, key), item in sorted(self.objects.items())
            if object_bucket == Bucket and key.startswith(Prefix)
        ]
        return {
            "KeyCount": len(contents),
            "Contents": contents,
        }
