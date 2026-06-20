from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from enterprise_dp.change_requests import (
    build_change_control_evidence_report,
    validate_change_request_registry,
    write_change_control_evidence_report,
)


ROOT = Path(__file__).resolve().parents[1]


def test_change_request_registry_is_valid() -> None:
    result = validate_change_request_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_prod_change_control_evidence_passes_for_approved_finance_publish() -> None:
    report = build_change_control_evidence_report(
        ROOT,
        request_id="publish_finance_benefit_reconciliation_prod",
        environment="prod",
        generated_at="2026-01-15T12:00:00Z",
    )

    assert report["artifact_type"] == "change_control_evidence.v1"
    assert report["passed"] is True
    assert report["summary"]["request_count"] == 1
    request = report["requests"][0]
    assert request["request_type"] == "data_product_publish"
    assert request["data_product"] == "gold.finance_benefit_reconciliation"
    assert "platform_owner" in request["approved_roles"]
    assert "security_owner" in request["approved_roles"]
    assert all(check["passed"] for check in request["checks"])


def test_change_control_blocks_self_approval_and_missing_required_evidence(tmp_path: Path) -> None:
    root = copy_minimal_platform_tree(tmp_path)
    path = root / "governance" / "change-requests.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    request = registry["change_requests"][0]
    request["requester"] = "enterprise-commerce-po"
    request["evidence"].pop("releaseEvidenceUri")
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    validation = validate_change_request_registry(root)
    assert any("approver must be different from requester" in error for error in validation.errors)
    assert any("evidence.releaseEvidenceUri is required" in error for error in validation.errors)

    report = build_change_control_evidence_report(
        root,
        request_id="publish_finance_benefit_reconciliation_prod",
        environment="prod",
        generated_at="2026-01-15T12:00:00Z",
    )

    assert report["passed"] is False
    failed_checks = {failure["check"] for failure in report["requests"][0]["failures"]}
    assert "maker_checker_separated" in failed_checks
    assert "required_evidence_present" in failed_checks


def test_change_control_evidence_report_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "change-control" / "report.json"
    result = write_change_control_evidence_report(
        ROOT,
        output_path,
        request_id="publish_finance_benefit_reconciliation_prod",
        environment="prod",
        generated_at="2026-01-15T12:00:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "change-control" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "change-control-check",
            "--root",
            str(ROOT),
            "--request-id",
            "publish_finance_benefit_reconciliation_prod",
            "--environment",
            "prod",
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-01-15T12:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["request_count"] == 1
    assert summary["failed_count"] == 0
    assert cli_output.is_file()


def copy_minimal_platform_tree(tmp_path: Path) -> Path:
    root = tmp_path / "dp"
    for folder in ("contracts", "governance", "products", "domains", "use-cases"):
        shutil.copytree(ROOT / folder, root / folder)
    return root
