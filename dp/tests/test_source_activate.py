from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.source_activation_ledger import (
    build_source_activation_index,
    validate_source_activation_registry,
    write_source_activation_manifest_from_bundle,
)
from enterprise_dp.source_readiness_bundle import run_source_readiness_bundle


ROOT = Path(__file__).resolve().parents[1]
BILLING_SOURCE_ID = "billing-platform-billing-transaction-settled-outbox"
BILLING_SAMPLE = ROOT / "samples" / "billing" / "billing_transaction_settled.jsonl"
GENERATED_AT = "2026-01-18T10:00:00Z"
ACTIVATED_AT = "2026-01-18T11:00:00Z"
EXPIRES_AT = "2026-07-18T11:00:00Z"
INGESTED_AT = "2026-01-18T10:01:00Z"
REPLAYED_AT = "2026-01-18T10:05:00Z"
BILLING_SNAPSHOT_ID = "iceberg-snapshot-billing-transaction-settled-0001"
BILLING_METADATA_URI = "s3://dp-staging-lakehouse/warehouse/bronze/events_billing_transaction_settled/metadata/00001.metadata.json"
BILLING_METADATA_HASH = "sha256:2222222222222222222222222222222222222222222222222222222222222222"


def test_source_activate_appends_valid_ledger_and_promotes_billing(tmp_path: Path) -> None:
    bundle = passing_billing_bundle(tmp_path)
    ledger_path = tmp_path / "governance" / "source-activations.yaml"
    active_state_path = tmp_path / "governance" / "source-active-pointers" / "billing.staging.json"
    output_path = tmp_path / "activation" / "billing-source-activation.json"

    result = write_source_activation_manifest_from_bundle(
        ROOT,
        bundle.summary_path,
        output_path,
        requested_by="billing-platform-sa",
        approved_by="data-platform-lead",
        change_request_id="onboard_billing_platform_source_readiness",
        ledger_path=ledger_path,
        active_state_path=active_state_path,
        generated_at=ACTIVATED_AT,
        expires_at=EXPIRES_AT,
        reason="Activate Billing Platform source after source-to-Bronze readiness evidence passed.",
        runtime_readiness_report_path=passing_runtime_readiness(tmp_path),
    )

    assert result.manifest["passed"] is True
    assert result.manifest["activation_state"] == "activated"
    assert output_path.is_file()
    assert ledger_path.is_file()
    assert active_state_path.is_file()

    activation = result.manifest["activation_record"]
    assert activation["sourceId"] == BILLING_SOURCE_ID
    assert activation["activationState"] == "active"
    assert activation["readinessId"] == bundle.readiness["readiness_id"]
    assert activation["readinessReportHash"].startswith("sha256:")
    assert activation["evidenceBundleHash"].startswith("sha256:")
    assert activation["sourceRegistryHash"].startswith("sha256:")
    assert activation["runtimeReadinessReportHash"].startswith("sha256:")
    assert activation["gateBadges"]["runtimeSlo"] == "passed"

    validation = validate_source_activation_registry(ROOT, ledger_path)
    assert validation.errors == []

    activation_index = build_source_activation_index(ROOT, environment="staging", as_of="2026-06-16T12:00:00Z", ledger_path=ledger_path)
    assert activation_index[BILLING_SOURCE_ID]["effective_status"] == "production_ready"


def test_source_activate_blocks_staging_without_runtime_readiness_report(tmp_path: Path) -> None:
    bundle = passing_billing_bundle(tmp_path)
    ledger_path = tmp_path / "governance" / "source-activations.yaml"
    output_path = tmp_path / "activation" / "blocked-runtime.json"

    result = write_source_activation_manifest_from_bundle(
        ROOT,
        bundle.summary_path,
        output_path,
        requested_by="billing-platform-sa",
        approved_by="data-platform-lead",
        change_request_id="onboard_billing_platform_source_readiness",
        ledger_path=ledger_path,
        generated_at=ACTIVATED_AT,
        expires_at=EXPIRES_AT,
    )

    assert result.manifest["passed"] is False
    assert not ledger_path.exists()
    failed_checks = {failure["check"] for failure in result.manifest["failures"]}
    assert "runtime_readiness_report_present" in failed_checks
    assert "all_activation_gate_badges_passing" in failed_checks
    assert result.manifest["activation_record"]["gateBadges"]["runtimeSlo"] == "pending_runtime"


def test_source_activate_cli_blocks_failed_readiness_without_appending_ledger(tmp_path: Path) -> None:
    bundle = failing_billing_bundle(tmp_path)
    ledger_path = tmp_path / "governance" / "source-activations.yaml"
    output_path = tmp_path / "activation" / "blocked.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "source-activate",
            "--root",
            str(ROOT),
            "--bundle",
            str(bundle.summary_path),
            "--output",
            str(output_path),
            "--requested-by",
            "billing-platform-sa",
            "--approved-by",
            "data-platform-lead",
            "--change-request-id",
            "onboard_billing_platform_source_readiness",
            "--ledger",
            str(ledger_path),
            "--generated-at",
            ACTIVATED_AT,
            "--expires-at",
            EXPIRES_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["passed"] is False
    assert output_path.is_file()
    assert not ledger_path.exists()
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    failed_checks = {failure["check"] for failure in manifest["failures"]}
    assert "bundle_passed" in failed_checks
    assert "readiness_passed" in failed_checks


def test_source_activate_blocks_same_requester_and_approver(tmp_path: Path) -> None:
    bundle = passing_billing_bundle(tmp_path)
    ledger_path = tmp_path / "governance" / "source-activations.yaml"
    output_path = tmp_path / "activation" / "blocked-maker-checker.json"

    result = write_source_activation_manifest_from_bundle(
        ROOT,
        bundle.summary_path,
        output_path,
        requested_by="billing-platform-sa",
        approved_by="billing-platform-sa",
        change_request_id="onboard_billing_platform_source_readiness",
        ledger_path=ledger_path,
        generated_at=ACTIVATED_AT,
        expires_at=EXPIRES_AT,
    )

    assert result.manifest["passed"] is False
    assert not ledger_path.exists()
    failed_checks = {failure["check"] for failure in result.manifest["failures"]}
    assert "maker_checker_separated" in failed_checks


def test_source_revoke_cli_appends_revoked_record_and_blocks_portfolio_overlay(tmp_path: Path) -> None:
    ledger_path, active_state_path = activate_billing_source(tmp_path)
    output_path = tmp_path / "revocation" / "billing-source-revocation.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "source-revoke",
            "--root",
            str(ROOT),
            "--source-id",
            BILLING_SOURCE_ID,
            "--environment",
            "staging",
            "--output",
            str(output_path),
            "--requested-by",
            "billing-platform-sa",
            "--approved-by",
            "data-platform-lead",
            "--change-request-id",
            "revoke_billing_platform_source_activation_staging",
            "--ledger",
            str(ledger_path),
            "--active-state",
            str(active_state_path),
            "--generated-at",
            "2026-06-17T10:30:00Z",
            "--reason",
            "Readiness evidence is stale for the Billing Platform source.",
            "--evidence-uri",
            "evidence://source-activations/billing-platform/staging/revocation-analysis-2026-06-17.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["revocation_state"] == "revoked"

    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["revocation_record"]["activationState"] == "revoked"
    pointer = json.loads(active_state_path.read_text(encoding="utf-8"))
    assert pointer["activation_state"] == "revoked"
    assert pointer["revoked_activation_id"] == manifest["revoked_activation_id"]

    validation = validate_source_activation_registry(ROOT, ledger_path)
    assert validation.errors == []
    activation_index = build_source_activation_index(ROOT, environment="staging", as_of="2026-06-18T12:00:00Z", ledger_path=ledger_path)
    assert activation_index[BILLING_SOURCE_ID]["effective_status"] == "blocked"
    assert activation_index[BILLING_SOURCE_ID]["block_reason"] == "activation_not_active:revoked"


def test_source_revoke_cli_allows_break_glass_when_active_pointer_is_missing(tmp_path: Path) -> None:
    ledger_path, active_state_path = activate_billing_source(tmp_path)
    active_state_path.unlink()
    output_path = tmp_path / "revocation" / "billing-source-revocation-missing-pointer.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "source-revoke",
            "--root",
            str(ROOT),
            "--source-id",
            BILLING_SOURCE_ID,
            "--environment",
            "staging",
            "--output",
            str(output_path),
            "--requested-by",
            "billing-platform-sa",
            "--approved-by",
            "data-platform-lead",
            "--change-request-id",
            "revoke_billing_platform_source_activation_staging",
            "--ledger",
            str(ledger_path),
            "--active-state",
            str(active_state_path),
            "--generated-at",
            "2026-06-17T10:30:00Z",
            "--reason",
            "Break-glass revocation because Billing source activation evidence is unverifiable and the staging pointer is missing.",
            "--evidence-uri",
            "evidence://source-activations/billing-platform/staging/revocation-analysis-2026-06-17.json",
            "--allow-missing-active-pointer",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["passed"] is True
    assert manifest["previous_active_pointer_missing"] is True
    assert manifest["missing_active_pointer_break_glass"] is True
    assert manifest["revocation_record"]["previousActivePointerMissing"] is True
    assert manifest["revocation_record"]["missingActivePointerBreakGlass"] is True
    pointer = json.loads(active_state_path.read_text(encoding="utf-8"))
    assert pointer["activation_state"] == "revoked"
    assert pointer["previous_active_pointer_missing"] is True
    assert pointer["missing_active_pointer_break_glass"] is True

    validation = validate_source_activation_registry(ROOT, ledger_path)
    assert validation.errors == []


def test_source_revoke_cli_blocks_same_requester_without_appending(tmp_path: Path) -> None:
    ledger_path, active_state_path = activate_billing_source(tmp_path)
    output_path = tmp_path / "revocation" / "blocked-maker-checker.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "source-revoke",
            "--root",
            str(ROOT),
            "--source-id",
            BILLING_SOURCE_ID,
            "--environment",
            "staging",
            "--output",
            str(output_path),
            "--requested-by",
            "billing-platform-sa",
            "--approved-by",
            "billing-platform-sa",
            "--change-request-id",
            "revoke_billing_platform_source_activation_staging",
            "--ledger",
            str(ledger_path),
            "--active-state",
            str(active_state_path),
            "--generated-at",
            "2026-06-17T10:30:00Z",
            "--reason",
            "Readiness evidence is stale for the Billing Platform source.",
            "--evidence-uri",
            "evidence://source-activations/billing-platform/staging/revocation-analysis-2026-06-17.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    failed_checks = {failure["check"] for failure in manifest["failures"]}
    assert "maker_checker_separated" in failed_checks

    ledger = read_ledger(ledger_path)
    assert [record["activationState"] for record in ledger["activations"]] == ["active"]


def test_source_revoke_cli_blocks_without_current_active(tmp_path: Path) -> None:
    ledger_path = tmp_path / "governance" / "source-activations.yaml"
    active_state_path = tmp_path / "governance" / "source-active-pointers" / "missing.json"
    output_path = tmp_path / "revocation" / "blocked-missing-active.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "source-revoke",
            "--root",
            str(ROOT),
            "--source-id",
            BILLING_SOURCE_ID,
            "--environment",
            "staging",
            "--output",
            str(output_path),
            "--requested-by",
            "billing-platform-sa",
            "--approved-by",
            "data-platform-lead",
            "--change-request-id",
            "revoke_billing_platform_source_activation_staging",
            "--ledger",
            str(ledger_path),
            "--active-state",
            str(active_state_path),
            "--generated-at",
            "2026-06-17T10:30:00Z",
            "--reason",
            "Readiness evidence is stale for the Billing Platform source.",
            "--evidence-uri",
            "evidence://source-activations/billing-platform/staging/revocation-analysis-2026-06-17.json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert not ledger_path.exists()
    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    failed_checks = {failure["check"] for failure in manifest["failures"]}
    assert "ledger_exists" in failed_checks
    assert "active_pointer_exists" in failed_checks
    assert "active_activation_found" in failed_checks


def activate_billing_source(tmp_path: Path) -> tuple[Path, Path]:
    bundle = passing_billing_bundle(tmp_path)
    ledger_path = tmp_path / "governance" / "source-activations.yaml"
    active_state_path = tmp_path / "governance" / "source-active-pointers" / "billing.staging.json"
    result = write_source_activation_manifest_from_bundle(
        ROOT,
        bundle.summary_path,
        tmp_path / "activation" / "billing-source-activation.json",
        requested_by="billing-platform-sa",
        approved_by="data-platform-lead",
        change_request_id="onboard_billing_platform_source_readiness",
        ledger_path=ledger_path,
        active_state_path=active_state_path,
        generated_at=ACTIVATED_AT,
        expires_at=EXPIRES_AT,
        reason="Activate Billing Platform source after source-to-Bronze readiness evidence passed.",
        runtime_readiness_report_path=passing_runtime_readiness(tmp_path),
    )
    assert result.manifest["passed"] is True
    return ledger_path, active_state_path


def read_ledger(path: Path) -> dict[str, object]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def passing_runtime_readiness(tmp_path: Path) -> Path:
    path = tmp_path / "runtime" / "staging-readiness.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "artifact_type": "runtime_readiness_report.v1",
                "report_version": 1,
                "report_id": "runtime-staging-ready",
                "generated_at": "2026-01-18T10:30:00Z",
                "environment": "staging",
                "readiness_state": "production_like_ready",
                "passed": True,
                "summary": {"failed_gate_count": 0},
                "gates": [{"gate_id": "service_health_passed", "status": "passed"}],
                "failures": [],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def passing_billing_bundle(tmp_path: Path):
    return run_source_readiness_bundle(
        ROOT,
        BILLING_SOURCE_ID,
        BILLING_SAMPLE,
        tmp_path / "passing-bundle",
        environment="staging",
        bundle_id="billing-source-activate-passing",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        replayed_at=REPLAYED_AT,
        schema_registry_uri="https://schema-registry.staging.example",
        change_request_id="onboard_billing_platform_source_readiness",
        target_snapshot_id=BILLING_SNAPSHOT_ID,
        table_metadata_uri=BILLING_METADATA_URI,
        table_metadata_hash=BILLING_METADATA_HASH,
        openlineage_namespace="enterprise-dp://staging",
        openlineage_producer="https://enterprise-dp.staging.example/openlineage-export",
    )


def failing_billing_bundle(tmp_path: Path):
    return run_source_readiness_bundle(
        ROOT,
        BILLING_SOURCE_ID,
        BILLING_SAMPLE,
        tmp_path / "failing-bundle",
        environment="staging",
        bundle_id="billing-source-activate-failing",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        replayed_at=REPLAYED_AT,
    )
