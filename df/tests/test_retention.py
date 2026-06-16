from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_df.retention import (
    build_retention_evidence_report,
    evaluate_retention_contract,
    validate_retention_policy_registry,
    write_retention_evidence_report,
)
from enterprise_df.release import _retention_evidence_gate


ROOT = Path(__file__).resolve().parents[1]


def test_repository_retention_policy_registry_is_valid() -> None:
    result = validate_retention_policy_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_retention_evaluator_selects_gold_ml_feature_policy() -> None:
    contract = yaml.safe_load((ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml").read_text())
    evaluation = evaluate_retention_contract(
        ROOT,
        artifact_name="gold.recsys_interactions",
        artifact_type="data_product",
        layer=contract["dataProduct"]["layer"],
        domain=contract["dataProduct"]["domain"],
        product=contract["dataProduct"]["product"],
        privacy=contract["privacy"],
    )

    assert evaluation["passed"] is True
    assert evaluation["policy_id"] == "certified_ml_feature_2y"
    assert str(evaluation["registry_hash"]).startswith("sha256:")


def test_retention_evaluator_selects_non_personal_finance_aggregate_policy() -> None:
    contract = yaml.safe_load((ROOT / "contracts" / "data-products" / "gold.finance_revenue_daily.v1.yaml").read_text())
    evaluation = evaluate_retention_contract(
        ROOT,
        artifact_name="gold.finance_revenue_daily",
        artifact_type="data_product",
        layer=contract["dataProduct"]["layer"],
        domain=contract["dataProduct"]["domain"],
        product=contract["dataProduct"]["product"],
        privacy=contract["privacy"],
    )

    assert evaluation["passed"] is True
    assert evaluation["policy_id"] == "non_personal_finance_aggregate_7y"


def test_retention_evaluator_blocks_contract_over_policy_limit() -> None:
    contract = yaml.safe_load((ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml").read_text())
    contract["privacy"]["retentionDays"] = 1096
    evaluation = evaluate_retention_contract(
        ROOT,
        artifact_name="gold.recsys_interactions",
        artifact_type="data_product",
        layer=contract["dataProduct"]["layer"],
        domain=contract["dataProduct"]["domain"],
        product=contract["dataProduct"]["product"],
        privacy=contract["privacy"],
    )

    assert evaluation["passed"] is False
    assert any(
        check["name"] == "retention_days_within_policy" and check["passed"] is False
        for check in evaluation["checks"]
    )


def test_retention_evidence_report_and_cli(tmp_path: Path) -> None:
    report = build_retention_evidence_report(
        ROOT,
        data_product_name="gold.recsys_interactions",
        environment="local",
        release_id="retention-pass",
        dataset_snapshot_id="snapshot-001",
        table_version="sha256:table",
        content_hash="sha256:content",
        row_count=3,
        generated_at="2026-01-15T10:00:00Z",
    )

    assert report["artifact_type"] == "retention_erasure_evidence.v1"
    assert report["passed"] is True
    assert report["policy"]["policy_id"] == "certified_ml_feature_2y"
    assert report["privacy"]["subject_keys"][0]["name"] == "learner_id_hash"
    assert report["privacy"]["subject_keys"][0]["column"] == "learner_id_hash"
    assert report["privacy"]["erasure_mode"] == "SUBJECT_DELETE"
    assert report["evidence"]["expired_record_scan"]["expired_record_count"] == 0
    assert report["evidence"]["subject_key_coverage"]["coverage_percent"] == 100.0
    assert report["evidence"]["erasure_request_replay"]["replay_passed"] is True
    assert report["evidence"]["residual_subject_scan"]["residual_match_count"] == 0

    output_path = tmp_path / "retention" / "report.json"
    result = write_retention_evidence_report(
        ROOT,
        output_path,
        data_product_name="gold.recsys_interactions",
        release_id="cli-retention",
        generated_at="2026-01-15T10:00:00Z",
    )
    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "retention" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "retention-check",
            "--root",
            str(ROOT),
            "--data-product",
            "gold.recsys_interactions",
            "--output",
            str(cli_output),
            "--release-id",
            "cli-retention",
            "--generated-at",
            "2026-01-15T10:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["policy_id"] == "certified_ml_feature_2y"
    assert cli_output.is_file()


def test_retention_evidence_report_uses_external_job_evidence_input(tmp_path: Path) -> None:
    evidence_input = tmp_path / "retention" / "job-evidence.json"
    write_retention_job_evidence(evidence_input)

    report = build_retention_evidence_report(
        ROOT,
        data_product_name="gold.recsys_interactions",
        environment="prod",
        release_id="retention-prod-pass",
        dataset_snapshot_id="snapshot-001",
        table_version="sha256:table",
        content_hash="sha256:content",
        row_count=3,
        generated_at="2026-01-15T10:00:00Z",
        evidence_input_path=evidence_input,
    )

    assert report["passed"] is True
    assert report["evidence_source"]["type"] == "external_input"
    assert report["evidence_source"]["hash"].startswith("sha256:")
    assert report["evidence_source"]["artifact_type"] == "retention_erasure_job_evidence.v1"
    assert report["evidence"]["retention_job_run_id"]["job_run_id"] == "retention-job-001"


def test_production_retention_evidence_requires_external_input() -> None:
    report = build_retention_evidence_report(
        ROOT,
        data_product_name="gold.recsys_interactions",
        environment="prod",
        release_id="retention-prod-missing-input",
        generated_at="2026-01-15T10:00:00Z",
    )

    assert report["passed"] is False
    assert report["evidence_source"]["type"] == "synthetic_local"
    assert any(
        failure["check"] == "production_retention_evidence_input_required"
        for failure in report["failures"]
    )


def test_production_retention_evidence_requires_release_snapshot_and_hash_binding(tmp_path: Path) -> None:
    evidence_input = tmp_path / "retention" / "job-evidence.json"
    write_retention_job_evidence(evidence_input)

    report = build_retention_evidence_report(
        ROOT,
        data_product_name="gold.recsys_interactions",
        environment="prod",
        generated_at="2026-01-15T10:00:00Z",
        evidence_input_path=evidence_input,
    )
    failed_checks = {failure["check"] for failure in report["failures"]}

    assert report["passed"] is False
    assert "production_retention_release_id_required" in failed_checks
    assert "production_retention_dataset_snapshot_id_required" in failed_checks
    assert "production_retention_table_version_required" in failed_checks
    assert "production_retention_content_hash_required" in failed_checks


def test_retention_evidence_report_fails_external_scan_and_legal_hold(tmp_path: Path) -> None:
    evidence_input = tmp_path / "retention" / "bad-job-evidence.json"
    write_retention_job_evidence(
        evidence_input,
        expired_record_count=2,
        residual_match_count=1,
        active_legal_hold_count=1,
        replay_passed=False,
    )

    report = build_retention_evidence_report(
        ROOT,
        data_product_name="gold.recsys_interactions",
        environment="prod",
        release_id="retention-prod-fail",
        dataset_snapshot_id="snapshot-001",
        table_version="sha256:table",
        content_hash="sha256:content",
        generated_at="2026-01-15T10:00:00Z",
        evidence_input_path=evidence_input,
    )

    failed_checks = {failure["check"] for failure in report["failures"]}

    assert report["passed"] is False
    assert "retention_expired_record_scan_clean" in failed_checks
    assert "erasure_replay_passed_when_required" in failed_checks
    assert "residual_subject_scan_clean" in failed_checks
    assert "legal_hold_check_clear" in failed_checks


def test_retention_evidence_report_rejects_invalid_external_timestamp(tmp_path: Path) -> None:
    evidence_input = tmp_path / "retention" / "bad-timestamp-evidence.json"
    write_retention_job_evidence(evidence_input)
    payload = json.loads(evidence_input.read_text(encoding="utf-8"))
    payload["generated_at"] = "not-a-timestamp"
    evidence_input.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    report = build_retention_evidence_report(
        ROOT,
        data_product_name="gold.recsys_interactions",
        environment="prod",
        release_id="retention-prod-pass",
        dataset_snapshot_id="snapshot-001",
        table_version="sha256:table",
        content_hash="sha256:content",
        generated_at="2026-01-15T10:00:00Z",
        evidence_input_path=evidence_input,
    )

    assert report["passed"] is False
    assert any(
        failure["check"] == "retention_evidence_input_generated_at_valid"
        for failure in report["failures"]
    )


def test_retention_cli_accepts_evidence_input(tmp_path: Path) -> None:
    evidence_input = tmp_path / "retention" / "job-evidence.json"
    write_retention_job_evidence(evidence_input)
    cli_output = tmp_path / "retention" / "cli-with-input.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "retention-check",
            "--root",
            str(ROOT),
            "--data-product",
            "gold.recsys_interactions",
            "--output",
            str(cli_output),
            "--environment",
            "prod",
            "--release-id",
            "retention-prod-pass",
            "--dataset-snapshot-id",
            "snapshot-001",
            "--table-version",
            "sha256:table",
            "--content-hash",
            "sha256:content",
            "--evidence-input",
            str(evidence_input),
            "--generated-at",
            "2026-01-15T10:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert json.loads(cli_output.read_text(encoding="utf-8"))["evidence_source"]["type"] == "external_input"


def test_retention_release_gate_rejects_local_synthetic_report_for_prod(tmp_path: Path) -> None:
    local_report = write_retention_evidence_report(
        ROOT,
        tmp_path / "retention" / "local-synthetic.json",
        data_product_name="gold.recsys_interactions",
        environment="local",
        release_id="retention-prod-release",
        generated_at="2026-01-15T10:00:00Z",
    )

    gate = _retention_evidence_gate(local_report.output_path.as_posix(), None, environment="prod")

    assert gate.passed is False
    assert gate.details["environment_matches_release"] is False
    assert gate.details["production_uses_external_input"] is False


def test_retention_release_gate_rejects_unbound_fake_report(tmp_path: Path) -> None:
    fake_report = {
        "artifact_type": "retention_erasure_evidence.v1",
        "passed": True,
        "environment": "prod",
        "release_id": "retention-prod-release",
        "data_product": "gold.fake_interactions",
        "dataset_snapshot_id": "snapshot-001",
        "table_version": "sha256:content",
        "content_hash": "sha256:content",
        "evidence_source": {"type": "external_input", "verified": True},
        "policy": {"policy_id": "certified_ml_feature_2y"},
        "failures": [],
    }
    report_path = tmp_path / "retention" / "fake-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(fake_report, sort_keys=True), encoding="utf-8")

    gate = _retention_evidence_gate(
        report_path.as_posix(),
        None,
        environment="prod",
        release_id="retention-prod-release",
        data_product="gold.recsys_interactions",
        dataset_snapshot_id="snapshot-001",
        content_hash="sha256:content",
    )

    assert gate.passed is False
    assert gate.details["data_product_matches"] is False


def write_retention_job_evidence(
    path: Path,
    *,
    expired_record_count: int = 0,
    coverage_percent: float = 100.0,
    replay_passed: bool = True,
    residual_match_count: int = 0,
    active_legal_hold_count: int = 0,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_type": "retention_erasure_job_evidence.v1",
        "producer": "retention-orchestrator",
        "generated_at": "2026-01-15T09:59:00Z",
        "data_product": "gold.recsys_interactions",
        "release_id": "retention-prod-pass",
        "dataset_snapshot_id": "snapshot-001",
        "table_version": "sha256:table",
        "content_hash": "sha256:content",
        "evidence": {
            "retention_job_run_id": {
                "id": "retention-job-001",
                "status": "passed",
                "job_run_id": "retention-job-001",
                "observed_at": "2026-01-15T09:59:00Z",
            },
            "subject_key_coverage": {
                "id": "coverage-001",
                "status": "passed",
                "coverage_percent": coverage_percent,
                "observed_at": "2026-01-15T09:59:00Z",
            },
            "expired_record_scan": {
                "id": "expired-scan-001",
                "status": "passed",
                "expired_record_count": expired_record_count,
                "observed_at": "2026-01-15T09:59:00Z",
            },
            "erasure_request_replay": {
                "id": "erasure-replay-001",
                "status": "passed" if replay_passed else "failed",
                "sample_request_count": 3,
                "replay_passed": replay_passed,
                "observed_at": "2026-01-15T09:59:00Z",
            },
            "residual_subject_scan": {
                "id": "residual-scan-001",
                "status": "passed",
                "residual_match_count": residual_match_count,
                "observed_at": "2026-01-15T09:59:00Z",
            },
            "legal_hold_check": {
                "id": "legal-hold-001",
                "status": "passed",
                "active_legal_hold_count": active_legal_hold_count,
                "observed_at": "2026-01-15T09:59:00Z",
            },
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
