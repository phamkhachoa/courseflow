from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.orchestration import run_use_case
from enterprise_dp.promotion import (
    build_release_activation_manifest,
    build_release_promotion_manifest,
    write_release_activation_manifest,
    write_release_promotion_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
FINANCE_SAMPLE_INPUT = ROOT / "samples" / "finance" / "benefit_settled.jsonl"
FINANCE_INGESTED_AT = "2026-01-15T09:15:05Z"
FINANCE_BUILT_AT = "2026-01-15T09:15:10Z"
FINANCE_EVALUATION_TIME = "2026-01-15T09:15:15Z"


def test_release_promotion_manifest_approves_passing_release(tmp_path: Path) -> None:
    run = run_finance_release(tmp_path / "run", release_id="local-finance-promotion-pass")
    result = write_release_promotion_manifest(
        run.evidence_path,
        tmp_path / "promotion" / "manifest.json",
        target_environment="local",
        requested_by="finance-data-engineer",
        approver="data-platform-sre",
        generated_at="2026-01-15T09:16:00Z",
        change_ticket="CHG-1001",
    )

    manifest = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert manifest == result.manifest
    assert manifest["artifact_type"] == "release_promotion_manifest.v1"
    assert manifest["promotion_state"] == "approved_for_activation"
    assert manifest["passed"] is True
    assert manifest["release_id"] == "local-finance-promotion-pass"
    assert manifest["output"]["data_product"] == "gold.finance_benefit_reconciliation"
    assert manifest["output"]["content_hash"].startswith("sha256:")
    assert manifest["gate_summary"]["failed_count"] == 0


def test_release_promotion_blocks_maker_checker_violation(tmp_path: Path) -> None:
    run = run_finance_release(tmp_path / "run", release_id="local-finance-promotion-maker-checker")

    manifest = build_release_promotion_manifest(
        run.evidence,
        release_evidence_path=run.evidence_path,
        target_environment="local",
        requested_by="same-user",
        approver="same-user",
        generated_at="2026-01-15T09:16:00Z",
    )
    failures = {failure["check"] for failure in manifest["failures"]}

    assert manifest["passed"] is False
    assert manifest["promotion_state"] == "blocked"
    assert "maker_checker_separated" in failures


def test_release_promotion_blocks_failed_release_gates(tmp_path: Path) -> None:
    run = run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        tmp_path / "run",
        use_case_id="finance-benefit-reconciliation",
        release_id="local-finance-promotion-failed-gate",
        environment="local",
        ingested_at="2026-01-15T09:40:00Z",
        built_at="2026-01-15T09:40:05Z",
        evaluation_time="2026-01-15T09:40:10Z",
    )

    manifest = build_release_promotion_manifest(
        run.evidence,
        release_evidence_path=run.evidence_path,
        target_environment="local",
        requested_by="finance-data-engineer",
        approver="data-platform-sre",
        generated_at="2026-01-15T09:41:00Z",
    )
    failures = {failure["check"] for failure in manifest["failures"]}

    assert manifest["passed"] is False
    assert manifest["promotion_state"] == "blocked"
    assert "release_passed" in failures
    assert "all_release_gates_passed" in failures
    assert "P0-INGESTION-LAG" in manifest["gate_summary"]["failed_gates"]


def test_release_promote_cli(tmp_path: Path) -> None:
    run = run_finance_release(tmp_path / "run", release_id="cli-finance-promotion-pass")
    output_path = tmp_path / "promotion" / "cli-manifest.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "release-promote",
            "--release-evidence",
            str(run.evidence_path),
            "--output",
            str(output_path),
            "--target-environment",
            "local",
            "--requested-by",
            "finance-data-engineer",
            "--approver",
            "data-platform-sre",
            "--generated-at",
            "2026-01-15T09:16:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["promotion_state"] == "approved_for_activation"
    assert output_path.is_file()


def test_release_activation_manifest_writes_active_pointer_state(tmp_path: Path) -> None:
    run = run_finance_release(tmp_path / "run", release_id="local-finance-activation-pass")
    promotion = write_release_promotion_manifest(
        run.evidence_path,
        tmp_path / "promotion" / "manifest.json",
        target_environment="local",
        requested_by="finance-data-engineer",
        approver="data-platform-sre",
        generated_at="2026-01-15T09:16:00Z",
    )
    active_state_path = tmp_path / "active" / "finance-benefit-reconciliation.json"

    result = write_release_activation_manifest(
        promotion.output_path,
        tmp_path / "activation" / "manifest.json",
        active_state_path=active_state_path,
        activated_by="release-manager",
        generated_at="2026-01-15T09:17:00Z",
    )

    manifest = json.loads(result.output_path.read_text(encoding="utf-8"))
    active_pointer = json.loads(active_state_path.read_text(encoding="utf-8"))

    assert manifest == result.manifest
    assert manifest["artifact_type"] == "release_activation_manifest.v1"
    assert manifest["activation_state"] == "activated"
    assert manifest["passed"] is True
    assert active_pointer == manifest["active_pointer"]
    assert active_pointer["artifact_type"] == "release_active_pointer.v1"
    assert active_pointer["release_id"] == "local-finance-activation-pass"
    assert active_pointer["data_product"] == "gold.finance_benefit_reconciliation"
    assert active_pointer["content_hash"] == promotion.manifest["output"]["content_hash"]
    assert active_pointer["rollback_target"] is None


def test_release_activation_blocks_unapproved_promotion_without_writing_active_state(tmp_path: Path) -> None:
    run = run_finance_release(tmp_path / "run", release_id="local-finance-activation-blocked")
    promotion = write_release_promotion_manifest(
        run.evidence_path,
        tmp_path / "promotion" / "blocked-manifest.json",
        target_environment="local",
        requested_by="same-user",
        approver="same-user",
        generated_at="2026-01-15T09:16:00Z",
    )
    active_state_path = tmp_path / "active" / "blocked.json"

    result = write_release_activation_manifest(
        promotion.output_path,
        tmp_path / "activation" / "blocked-manifest.json",
        active_state_path=active_state_path,
        activated_by="release-manager",
        generated_at="2026-01-15T09:17:00Z",
    )
    failures = {failure["check"] for failure in result.manifest["failures"]}

    assert result.manifest["passed"] is False
    assert result.manifest["activation_state"] == "blocked"
    assert "promotion_passed" in failures
    assert "promotion_approved_for_activation" in failures
    assert not active_state_path.exists()


def test_release_activation_requires_prod_rollback_target(tmp_path: Path) -> None:
    run = run_finance_release(tmp_path / "run", release_id="prod-finance-activation-no-rollback")
    promotion = write_release_promotion_manifest(
        run.evidence_path,
        tmp_path / "promotion" / "manifest.json",
        target_environment="local",
        requested_by="finance-data-engineer",
        approver="data-platform-sre",
        generated_at="2026-01-15T09:16:00Z",
    )
    production_promotion = {**promotion.manifest, "target_environment": "prod"}
    production_promotion_path = tmp_path / "promotion" / "production-manifest.json"
    production_promotion_path.write_text(json.dumps(production_promotion), encoding="utf-8")

    manifest = build_release_activation_manifest(
        production_promotion,
        promotion_manifest_path=production_promotion_path,
        active_state_path=tmp_path / "active" / "production.json",
        previous_state=None,
        activated_by="release-manager",
        generated_at="2026-01-15T09:17:00Z",
    )
    failures = {failure["check"] for failure in manifest["failures"]}

    assert manifest["passed"] is False
    assert manifest["activation_state"] == "blocked"
    assert "prod_has_rollback_target" in failures


def test_release_activate_cli(tmp_path: Path) -> None:
    run = run_finance_release(tmp_path / "run", release_id="cli-finance-activation-pass")
    promotion = write_release_promotion_manifest(
        run.evidence_path,
        tmp_path / "promotion" / "cli-promotion-manifest.json",
        target_environment="local",
        requested_by="finance-data-engineer",
        approver="data-platform-sre",
        generated_at="2026-01-15T09:16:00Z",
    )
    output_path = tmp_path / "activation" / "cli-activation-manifest.json"
    active_state_path = tmp_path / "active" / "cli-active-pointer.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "release-activate",
            "--promotion-manifest",
            str(promotion.output_path),
            "--output",
            str(output_path),
            "--active-state",
            str(active_state_path),
            "--activated-by",
            "release-manager",
            "--generated-at",
            "2026-01-15T09:17:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["activation_state"] == "activated"
    assert output_path.is_file()
    assert active_state_path.is_file()


def run_finance_release(output_dir: Path, *, release_id: str):
    return run_use_case(
        ROOT,
        FINANCE_SAMPLE_INPUT,
        output_dir,
        use_case_id="finance-benefit-reconciliation",
        release_id=release_id,
        environment="local",
        ingested_at=FINANCE_INGESTED_AT,
        built_at=FINANCE_BUILT_AT,
        evaluation_time=FINANCE_EVALUATION_TIME,
    )
