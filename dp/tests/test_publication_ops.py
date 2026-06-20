from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.publication_ops import (
    build_silver_gold_publication_ops_report,
    write_silver_gold_publication_ops_report,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-16T15:00:00Z"
DATA_PRODUCT = "gold.finance_benefit_reconciliation"
SNAPSHOT_ID = "iceberg-gold-finance-benefit-reconciliation-0001"
CONTENT_HASH = "sha256:1111111111111111111111111111111111111111111111111111111111111111"
SNAPSHOT_HASH = "sha256:2222222222222222222222222222222222222222222222222222222222222222"


def test_publication_ops_allows_local_preflight_without_evidence() -> None:
    report = build_silver_gold_publication_ops_report(
        ROOT,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert report["artifact_type"] == "silver_gold_publication_ops_report.v1"
    assert report["readiness_state"] == "local_preflight_ready"
    assert report["passed"] is True
    assert report["summary"]["failed_product_count"] == 0


def test_publication_ops_blocks_prod_without_release_promotion_activation_and_pointer() -> None:
    report = build_silver_gold_publication_ops_report(
        ROOT,
        environment="prod",
        generated_at=GENERATED_AT,
    )

    failed = {check["name"] for check in report["checks"] if check["passed"] is not True}
    assert report["passed"] is False
    assert report["readiness_state"] == "not_ready"
    assert {
        "release_evidence_attached_for_production_like",
        "promotion_manifest_attached_for_production_like",
        "activation_manifest_attached_for_production_like",
        "active_pointer_attached_for_production_like",
    } <= failed


def test_publication_ops_passes_with_complete_production_like_evidence(tmp_path: Path) -> None:
    artifacts = write_publication_artifacts(tmp_path, environment="prod")

    report = build_silver_gold_publication_ops_report(
        ROOT,
        environment="prod",
        release_evidence_paths=[artifacts["release"]],
        promotion_manifest_paths=[artifacts["promotion"]],
        activation_manifest_paths=[artifacts["activation"]],
        active_pointer_paths=[artifacts["pointer"]],
        generated_at=GENERATED_AT,
    )

    assert report["passed"] is True
    assert report["readiness_state"] == "production_like_ready"
    assert report["summary"]["failed_product_count"] == 0
    assert report["summary"]["active_pointer_attached_count"] == 1


def test_publication_ops_blocks_pointer_drift_and_missing_rollback(tmp_path: Path) -> None:
    artifacts = write_publication_artifacts(
        tmp_path,
        environment="prod",
        pointer_updates={
            "dataset_snapshot_id": "wrong-snapshot",
            "rollback_target": None,
        },
    )

    report = build_silver_gold_publication_ops_report(
        ROOT,
        environment="prod",
        release_evidence_paths=[artifacts["release"]],
        promotion_manifest_paths=[artifacts["promotion"]],
        activation_manifest_paths=[artifacts["activation"]],
        active_pointer_paths=[artifacts["pointer"]],
        generated_at=GENERATED_AT,
    )

    failed = report["decision_board"]["failed_products"][0]
    assert report["passed"] is False
    assert failed["data_product"] == DATA_PRODUCT
    assert set(failed["issues"]) >= {"active_pointer_drift", "rollback_target_missing"}


def test_publication_ops_blocks_failed_release_and_unapproved_promotion(tmp_path: Path) -> None:
    artifacts = write_publication_artifacts(
        tmp_path,
        environment="prod",
        release_updates={"release_passed": False},
        promotion_updates={"passed": False, "promotion_state": "blocked"},
        activation_updates={"passed": False, "activation_state": "blocked"},
    )

    report = build_silver_gold_publication_ops_report(
        ROOT,
        environment="prod",
        release_evidence_paths=[artifacts["release"]],
        promotion_manifest_paths=[artifacts["promotion"]],
        activation_manifest_paths=[artifacts["activation"]],
        active_pointer_paths=[artifacts["pointer"]],
        generated_at=GENERATED_AT,
    )

    failed = report["decision_board"]["failed_products"][0]
    assert report["passed"] is False
    assert set(failed["issues"]) >= {
        "release_failed",
        "promotion_failed",
        "promotion_not_approved",
        "activation_failed",
        "activation_not_activated",
    }


def test_publication_ops_writer_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "publication" / "local.json"
    result = write_silver_gold_publication_ops_report(
        ROOT,
        output_path,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "publication" / "prod.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "silver-gold-publication-ops-report",
            "--root",
            str(ROOT),
            "--environment",
            "prod",
            "--output",
            str(cli_output),
            "--generated-at",
            GENERATED_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["passed"] is False
    assert summary["summary"]["global_failed_check_count"] == 4
    assert cli_output.is_file()


def write_publication_artifacts(
    tmp_path: Path,
    *,
    environment: str,
    release_updates: dict[str, object] | None = None,
    promotion_updates: dict[str, object] | None = None,
    activation_updates: dict[str, object] | None = None,
    pointer_updates: dict[str, object] | None = None,
) -> dict[str, Path]:
    base = tmp_path / "publication"
    base.mkdir(parents=True, exist_ok=True)
    release = {
        "release_id": "prod-finance-release",
        "environment": environment,
        "generated_at": GENERATED_AT,
        "use_case_id": "finance-benefit-reconciliation",
        "runner_id": "finance.benefit_reconciliation.from_approved_bronze.v1",
        "primary_output": DATA_PRODUCT,
        "output_data_products": ["silver.finance_benefit_transactions", DATA_PRODUCT],
        "snapshot_evidence_uri": "evidence://snapshot/finance.json",
        "snapshot_evidence_hash": SNAPSHOT_HASH,
        "gates": [],
        "release_passed": True,
    }
    deep_update(release, release_updates or {})
    promotion = {
        "artifact_type": "release_promotion_manifest.v1",
        "manifest_version": 1,
        "promotion_id": "promotion-prod-finance",
        "promotion_state": "approved_for_activation",
        "generated_at": GENERATED_AT,
        "release_id": release["release_id"],
        "target_environment": environment,
        "release_environment": environment,
        "requested_by": "finance-data-engineer",
        "approver": "data-platform-sre",
        "change_ticket": "CHG-2001",
        "release_evidence_uri": "evidence://release/finance.json",
        "release_evidence_hash": SNAPSHOT_HASH,
        "source_release_passed": True,
        "use_case_id": release["use_case_id"],
        "runner_id": release["runner_id"],
        "output": {
            "data_product": DATA_PRODUCT,
            "dataset_snapshot_id": SNAPSHOT_ID,
            "content_hash": CONTENT_HASH,
            "row_count": 4,
        },
        "passed": True,
    }
    deep_update(promotion, promotion_updates or {})
    pointer = {
        "artifact_type": "release_active_pointer.v1",
        "pointer_version": 1,
        "activation_id": "activation-prod-finance",
        "environment": environment,
        "release_id": release["release_id"],
        "data_product": DATA_PRODUCT,
        "dataset_snapshot_id": SNAPSHOT_ID,
        "content_hash": CONTENT_HASH,
        "row_count": 4,
        "activated_at": GENERATED_AT,
        "activated_by": "release-manager",
        "promotion_manifest_uri": "evidence://promotion/finance.json",
        "promotion_manifest_hash": SNAPSHOT_HASH,
        "rollback_target": {
            "data_product": DATA_PRODUCT,
            "dataset_snapshot_id": "previous-snapshot",
            "content_hash": "sha256:3333333333333333333333333333333333333333333333333333333333333333",
        },
    }
    deep_update(pointer, pointer_updates or {})
    activation = {
        "artifact_type": "release_activation_manifest.v1",
        "manifest_version": 1,
        "activation_id": pointer["activation_id"],
        "activation_state": "activated",
        "generated_at": GENERATED_AT,
        "activated_by": "release-manager",
        "active_state_path": "active/prod-finance.json",
        "promotion_manifest_uri": "evidence://promotion/finance.json",
        "promotion_manifest_hash": SNAPSHOT_HASH,
        "promotion_id": promotion["promotion_id"],
        "release_id": release["release_id"],
        "target_environment": environment,
        "output": promotion["output"],
        "previous_active": pointer["rollback_target"],
        "active_pointer": pointer,
        "passed": True,
    }
    deep_update(activation, activation_updates or {})
    paths = {
        "release": base / "release.json",
        "promotion": base / "promotion.json",
        "activation": base / "activation.json",
        "pointer": base / "active-pointer.json",
    }
    for key, path in paths.items():
        path.write_text(json.dumps(locals()[key], sort_keys=True), encoding="utf-8")
    return paths


def deep_update(target: dict[str, object], updates: dict[str, object]) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value
