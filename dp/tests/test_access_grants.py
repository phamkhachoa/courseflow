from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from enterprise_dp.access_grants import (
    build_access_grant_evidence_report,
    build_access_grant_ops_report,
    evaluate_access_grants,
    validate_access_grant_registry,
    write_access_grant_evidence_report,
    write_access_grant_ops_report,
)


ROOT = Path(__file__).resolve().parents[1]


def test_repository_access_grant_registry_is_valid() -> None:
    result = validate_access_grant_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_access_grant_evaluator_covers_required_recsys_personas() -> None:
    contract = yaml.safe_load((ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml").read_text())
    evaluation = evaluate_access_grants(
        ROOT,
        data_product_name="gold.recsys_interactions",
        serving=contract["serving"],
        evaluation_time="2026-01-15T10:00:00Z",
    )

    assert evaluation["passed"] is True
    assert evaluation["required_personas"] == ["ApprovedBIConsumer", "ApprovedMLConsumer"]
    assert evaluation["active_grant_count"] == 2
    assert sorted(evaluation["active_personas"]) == ["ApprovedBIConsumer", "ApprovedMLConsumer"]


def test_access_grant_evaluator_covers_required_sensitive_silver_personas() -> None:
    expectations = {
        "silver.customer_identity_link": ["ApprovedBIConsumer", "ApprovedMLConsumer"],
        "silver.identity_subject": ["ComplianceConsumer", "RiskOperator"],
        "silver.support_case": ["ApprovedBIConsumer", "ApprovedMLConsumer", "ComplianceConsumer"],
    }

    for data_product_name, personas in expectations.items():
        contract_path = ROOT / "contracts" / "data-products" / f"{data_product_name}.v1.yaml"
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

        evaluation = evaluate_access_grants(
            ROOT,
            data_product_name=data_product_name,
            serving=contract["serving"],
            evaluation_time="2026-01-15T10:00:00Z",
        )

        assert evaluation["passed"] is True, data_product_name
        assert evaluation["missing_personas"] == []
        assert evaluation["required_personas"] == personas
        assert sorted(evaluation["active_personas"]) == sorted(personas)


def test_access_grant_evaluator_blocks_missing_required_persona(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "contracts", tmp_path / "contracts")
    shutil.copytree(ROOT / "governance", tmp_path / "governance")
    path = tmp_path / "governance" / "access-grants.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    registry["grants"] = [
        grant
        for grant in registry["grants"]
        if not (grant["dataProduct"] == "gold.recsys_interactions" and grant["persona"] == "ApprovedMLConsumer")
    ]
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    contract = yaml.safe_load((ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml").read_text())

    evaluation = evaluate_access_grants(
        tmp_path,
        data_product_name="gold.recsys_interactions",
        serving=contract["serving"],
        evaluation_time="2026-01-15T10:00:00Z",
    )

    assert evaluation["passed"] is False
    assert evaluation["missing_personas"] == ["ApprovedMLConsumer"]


def test_access_grant_evidence_report_and_cli(tmp_path: Path) -> None:
    report = build_access_grant_evidence_report(
        ROOT,
        data_product_name="gold.recsys_interactions",
        environment="local",
        release_id="access-grant-pass",
        dataset_snapshot_id="snapshot-001",
        table_version="sha256:table",
        content_hash="sha256:content",
        generated_at="2026-01-15T10:00:00Z",
    )

    assert report["artifact_type"] == "access_grant_evidence.v1"
    assert report["passed"] is True
    assert report["active_grant_count"] == 2
    assert str(report["registries"]["access_grant_registry_hash"]).startswith("sha256:")
    assert any(decision["test"] == "cross_org_denied" and decision["decision"] == "DENY" for decision in report["runtime_audit"]["decisions"])

    output_path = tmp_path / "access-grant" / "report.json"
    result = write_access_grant_evidence_report(
        ROOT,
        output_path,
        data_product_name="gold.recsys_interactions",
        release_id="cli-access-grant",
        generated_at="2026-01-15T10:00:00Z",
    )
    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "access-grant" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "access-grant-check",
            "--root",
            str(ROOT),
            "--data-product",
            "gold.recsys_interactions",
            "--output",
            str(cli_output),
            "--release-id",
            "cli-access-grant",
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
    assert summary["active_grant_count"] == 2
    assert cli_output.is_file()


def test_access_grant_ops_report_surfaces_review_overdue_queue() -> None:
    report = build_access_grant_ops_report(
        ROOT,
        environment="local",
        generated_at="2026-06-16T12:00:00Z",
    )

    assert report["artifact_type"] == "access_grant_ops_report.v1"
    assert report["passed"] is True
    assert report["summary"]["active_grant_count"] > 0
    assert report["summary"]["p0_issue_count"] == 0
    assert report["summary"]["p1_issue_count"] > 0
    assert report["summary"]["review_overdue_count"] > 0
    assert "grant_recsys_gold_bi_2026" in report["decision_board"]["review_queue"]


def test_access_grant_ops_report_blocks_maker_checker_conflict(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "contracts", tmp_path / "contracts")
    shutil.copytree(ROOT / "governance", tmp_path / "governance")
    path = tmp_path / "governance" / "access-grants.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    registry["grants"][0]["approver"] = registry["grants"][0]["requester"]
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    report = build_access_grant_ops_report(
        tmp_path,
        environment="prod",
        generated_at="2026-06-16T12:00:00Z",
    )

    conflicted_grant = next(row for row in report["grants"] if row["grant_id"] == "grant_recsys_gold_bi_2026")
    assert report["passed"] is False
    assert report["summary"]["p0_issue_count"] == 1
    assert "grant_recsys_gold_bi_2026" in report["decision_board"]["page_now"]
    assert any(issue["id"] == "maker_checker_conflict" for issue in conflicted_grant["issues"])


def test_access_grant_ops_report_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "access-grant-ops" / "report.json"
    result = write_access_grant_ops_report(
        ROOT,
        output_path,
        environment="local",
        generated_at="2026-06-16T12:00:00Z",
    )
    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "access-grant-ops" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "access-grant-ops-report",
            "--root",
            str(ROOT),
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-06-16T12:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["summary"]["review_overdue_count"] > 0
    assert cli_output.is_file()
