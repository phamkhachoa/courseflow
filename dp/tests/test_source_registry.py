from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_dp.catalog import write_catalog_bundle
from enterprise_dp.change_requests import write_change_control_evidence_report
from enterprise_dp.contracts import ValidationResult
from enterprise_dp.ingestion import run_bronze_ingestion
from enterprise_dp.offset_ledger import write_offset_ledger_report
from enterprise_dp.openlineage import write_openlineage_events
from enterprise_dp.schema_registry import write_schema_registry_report
from enterprise_dp.source_registry import (
    build_source_readiness_report,
    validate_source_entry,
    validate_source_registry,
    validation_context,
    write_source_readiness_report,
)


ROOT = Path(__file__).resolve().parents[1]
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"


def test_repository_source_registry_is_valid() -> None:
    result = validate_source_registry(ROOT)

    assert result.errors == []
    assert result.checked_count >= 6


def test_support_platform_source_is_registered_as_customer_saas_connector() -> None:
    _, source = load_source("support-platform-support-case-changed-connector")

    assert source["priority"] == "P1"
    assert source["status"] == "pilot"
    assert source["product"] == "support-platform"
    assert source["domain"] == "customer"
    assert source["source"]["type"] == "saas_connector"
    assert source["canonical"]["topic"] == "customer.support_case.changed.v1"
    assert source["canonical"]["bronzeTarget"] == "bronze.events_support_case_changed"
    assert source["bridge"]["mode"] == "direct_canonical"
    assert source["privacy"]["piiHandling"] == "tokenized_before_bronze"


def test_billing_platform_source_is_registered_as_finance_outbox() -> None:
    _, source = load_source("billing-platform-billing-transaction-settled-outbox")

    assert source["priority"] == "P0"
    assert source["status"] == "pilot"
    assert source["product"] == "billing-platform"
    assert source["domain"] == "finance"
    assert source["source"]["type"] == "transactional_outbox"
    assert source["canonical"]["topic"] == "finance.billing_transaction.settled.v1"
    assert source["canonical"]["bronzeTarget"] == "bronze.events_billing_transaction_settled"
    assert source["bridge"]["mode"] == "direct_canonical"
    assert source["privacy"]["piiHandling"] == "tokenized_before_bronze"


def test_source_registry_rejects_unknown_canonical_topic() -> None:
    path, entry = load_first_source()
    entry["canonical"]["topic"] = "finance.unknown_event.v1"
    entry["canonical"]["schemaSubject"] = "finance.unknown_event.v1-value"
    result = ValidationResult()

    validate_source_entry(ROOT, path, entry, 0, set(), validation_context(ROOT), result)

    assert any("canonical.topic contract does not exist" in error for error in result.errors)


def test_source_registry_requires_p0_production_evidence() -> None:
    path, entry = load_first_source()
    entry["evidence"]["productionAttestationRequired"] = False
    result = ValidationResult()

    validate_source_entry(ROOT, path, entry, 0, set(), validation_context(ROOT), result)

    assert any("productionAttestationRequired must be true for P0 sources" in error for error in result.errors)


def test_source_registry_requires_normalizer_when_bridge_is_required() -> None:
    path, entry = load_source("lms-courseflow-enrollment-completed-outbox")
    entry["bridge"]["normalizerId"] = "none"
    result = ValidationResult()

    validate_source_entry(ROOT, path, entry, 0, set(), validation_context(ROOT), result)

    assert any("normalizerId must name the approved normalizer" in error for error in result.errors)


def test_source_registry_aligns_bronze_target_with_topic_contract() -> None:
    path, entry = load_first_source()
    entry["canonical"]["bronzeTarget"] = "bronze.events_wrong_target"
    result = ValidationResult()

    validate_source_entry(ROOT, path, entry, 0, set(), validation_context(ROOT), result)

    assert any("canonical.bronzeTarget must match topic ingestion.bronzeTarget" in error for error in result.errors)


def test_source_readiness_report_passes_for_enterprise_commerce_source(tmp_path: Path) -> None:
    artifacts = build_source_readiness_artifacts(tmp_path)

    report = build_source_readiness_report(
        ROOT,
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=artifacts["ingestion_manifest"],
        replay_manifest_path=artifacts["replay_manifest"],
        offset_ledger_path=artifacts["offset_ledger"],
        schema_registry_report_path=artifacts["schema_report"],
        change_control_evidence_path=artifacts["change_control"],
        catalog_bundle_path=artifacts["catalog_bundle"],
        openlineage_events_path=artifacts["openlineage"],
        generated_at="2026-01-17T12:00:00Z",
    )

    assert report["artifact_type"] == "source_readiness_report.v1"
    assert report["passed"] is True
    assert report["readiness_state"] == "production_ready"
    assert report["source"]["product"] == "enterprise-commerce"
    assert report["source"]["canonical_topic"] == "finance.benefit_settled.v1"
    assert all(check["passed"] is True for check in report["checks"])


def test_source_readiness_blocks_missing_replay_proof(tmp_path: Path) -> None:
    artifacts = build_source_readiness_artifacts(tmp_path)

    report = build_source_readiness_report(
        ROOT,
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=artifacts["ingestion_manifest"],
        offset_ledger_path=artifacts["offset_ledger"],
        schema_registry_report_path=artifacts["schema_report"],
        change_control_evidence_path=artifacts["change_control"],
        catalog_bundle_path=artifacts["catalog_bundle"],
        openlineage_events_path=artifacts["openlineage"],
        generated_at="2026-01-17T12:00:00Z",
    )

    assert report["passed"] is False
    failed_checks = {failure["check"] for failure in report["failures"]}
    assert "replay_manifest_attached" in failed_checks


def test_source_readiness_blocks_missing_offset_ledger_in_staging(tmp_path: Path) -> None:
    artifacts = build_source_readiness_artifacts(tmp_path)

    report = build_source_readiness_report(
        ROOT,
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=artifacts["ingestion_manifest"],
        replay_manifest_path=artifacts["replay_manifest"],
        schema_registry_report_path=artifacts["schema_report"],
        change_control_evidence_path=artifacts["change_control"],
        catalog_bundle_path=artifacts["catalog_bundle"],
        openlineage_events_path=artifacts["openlineage"],
        generated_at="2026-01-17T12:00:00Z",
    )

    assert report["passed"] is False
    failed_checks = {failure["check"] for failure in report["failures"]}
    assert "offset_ledger_attached" in failed_checks


def test_source_readiness_report_and_cli(tmp_path: Path) -> None:
    artifacts = build_source_readiness_artifacts(tmp_path)
    output_path = tmp_path / "readiness" / "source-readiness.json"
    result = write_source_readiness_report(
        ROOT,
        output_path,
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=artifacts["ingestion_manifest"],
        replay_manifest_path=artifacts["replay_manifest"],
        offset_ledger_path=artifacts["offset_ledger"],
        schema_registry_report_path=artifacts["schema_report"],
        change_control_evidence_path=artifacts["change_control"],
        catalog_bundle_path=artifacts["catalog_bundle"],
        openlineage_events_path=artifacts["openlineage"],
        generated_at="2026-01-17T12:00:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "readiness" / "source-readiness-cli.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "source-readiness-check",
            "--root",
            str(ROOT),
            "--source-id",
            "enterprise-commerce-benefit-settled-outbox",
            "--environment",
            "staging",
            "--ingestion-manifest",
            str(artifacts["ingestion_manifest"]),
            "--replay-manifest",
            str(artifacts["replay_manifest"]),
            "--offset-ledger",
            str(artifacts["offset_ledger"]),
            "--schema-registry-report",
            str(artifacts["schema_report"]),
            "--change-control-evidence",
            str(artifacts["change_control"]),
            "--catalog-bundle",
            str(artifacts["catalog_bundle"]),
            "--openlineage-events",
            str(artifacts["openlineage"]),
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-01-17T12:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["readiness_state"] == "production_ready"
    assert summary["failure_count"] == 0
    assert cli_output.is_file()


def load_first_source() -> tuple[Path, dict]:
    path = ROOT / "platform" / "ingestion" / "source-registry.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    return path, deepcopy(registry["sources"][0])


def load_source(source_id: str) -> tuple[Path, dict]:
    path = ROOT / "platform" / "ingestion" / "source-registry.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    for source in registry["sources"]:
        if source["sourceId"] == source_id:
            return path, deepcopy(source)
    raise AssertionError(f"source not found: {source_id}")


def build_source_readiness_artifacts(tmp_path: Path) -> dict[str, Path]:
    ingestion = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        FINANCE_SAMPLE_INPUT,
        tmp_path / "bronze",
        ingested_at="2026-01-17T10:00:00Z",
        ingest_run_id="finance-source-readiness-first",
        schema_id="registry:finance.benefit_settled.v1:1",
    )
    replay = run_bronze_ingestion(
        ROOT,
        "finance.benefit_settled.v1",
        FINANCE_SAMPLE_INPUT,
        tmp_path / "bronze",
        ingested_at="2026-01-17T10:05:00Z",
        ingest_run_id="finance-source-readiness-replay",
        schema_id="registry:finance.benefit_settled.v1:1",
    )
    schema = write_schema_registry_report(
        ROOT,
        tmp_path / "schema" / "schema-registry.json",
        topic_name="finance.benefit_settled.v1",
        registry_uri="https://schema-registry.staging.example",
        generated_at="2026-01-17T10:10:00Z",
    )
    change_control = write_change_control_evidence_report(
        ROOT,
        tmp_path / "change-control" / "source-onboarding.json",
        request_id="onboard_enterprise_commerce_source_readiness",
        environment="staging",
        generated_at="2026-01-17T10:15:00Z",
    )
    offset_ledger = write_offset_ledger_report(
        ROOT,
        tmp_path / "offset-ledger" / "finance-benefit-settled.json",
        source_id="enterprise-commerce-benefit-settled-outbox",
        environment="staging",
        ingestion_manifest_path=ingestion.manifest_path,
        replay_manifest_path=replay.manifest_path,
        target_snapshot_id="iceberg-snapshot-finance-benefit-settled-0001",
        table_metadata_uri="s3://dp-staging-lakehouse/warehouse/bronze/events_benefit_settled/metadata/00001.metadata.json",
        table_metadata_hash="sha256:1111111111111111111111111111111111111111111111111111111111111111",
        committed_at="2026-01-17T10:06:00Z",
        generated_at="2026-01-17T10:16:00Z",
    )
    catalog_path = tmp_path / "catalog" / "catalog-bundle.json"
    write_catalog_bundle(
        ROOT,
        catalog_path,
        manifest_paths=[ingestion.manifest_path],
        generated_at="2026-01-17T10:20:00Z",
    )
    openlineage = write_openlineage_events(
        catalog_path,
        tmp_path / "lineage" / "openlineage.jsonl",
        namespace="enterprise-dp://staging",
        producer="https://enterprise-dp.staging.example/openlineage-export",
    )
    return {
        "ingestion_manifest": ingestion.manifest_path,
        "replay_manifest": replay.manifest_path,
        "offset_ledger": offset_ledger.output_path,
        "schema_report": schema.output_path,
        "change_control": change_control.output_path,
        "catalog_bundle": catalog_path,
        "openlineage": openlineage["output_path"],
    }
