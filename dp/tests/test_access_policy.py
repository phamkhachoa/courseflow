from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from enterprise_dp.access_policies import evaluate_access_policy_contract, validate_access_policy_registry
from enterprise_dp.access_policy import build_access_policy_report, write_access_policy_report


ROOT = Path(__file__).resolve().parents[1]


def test_access_policy_report_passes_for_gold_recsys_contract() -> None:
    report = build_access_policy_report(
        ROOT,
        data_product_name="gold.recsys_interactions",
        environment="local",
        release_id="access-policy-pass",
        dataset_snapshot_id="snapshot-001",
        table_version="sha256:table",
        content_hash="sha256:content",
        row_count=3,
        generated_at="2026-01-15T10:00:00Z",
    )

    assert report["artifact_type"] == "access_policy_check.v1"
    assert report["passed"] is True
    assert report["policy"]["access_policy"] == "row_level_org_isolation"
    assert report["policy"]["policy_name"] == "Row Level Organization Isolation"
    assert report["policy"]["policy_version"] == 1
    assert report["policy"]["policy_severity"] == "P0"
    assert str(report["policy"]["policy_registry_hash"]).startswith("sha256:")
    assert str(report["policy"]["persona_registry_hash"]).startswith("sha256:")
    assert report["policy"]["required_columns"] == ["org_id"]
    assert "ApprovedMLConsumer" in report["policy"]["allowed_personas"]
    assert report["policy"]["consumer_contract_name"] == "Catalog Registered Access Request Required"
    assert report["policy"]["consumer_contract_version"] == 1
    assert str(report["policy"]["consumer_contract_registry_hash"]).startswith("sha256:")
    assert "catalog_access_request_id" in report["policy"]["consumer_contract_required_evidence"]
    assert report["dataset_snapshot_id"] == "snapshot-001"
    assert report["access_grants"]["passed"] is True
    assert report["access_grants"]["active_grant_count"] == 2
    assert sorted(report["access_grants"]["active_personas"]) == ["ApprovedBIConsumer", "ApprovedMLConsumer"]
    assert any(control["control"] == "registry_policy_active" and control["passed"] for control in report["controls_checked"])
    assert any(control["control"] == "registry_consumer_contract_active" and control["passed"] for control in report["controls_checked"])
    assert any(control["control"] == "registry_access_grants_cover_required_personas" and control["passed"] for control in report["controls_checked"])
    assert any(control["control"] == "row_level_org_isolation" and control["passed"] for control in report["controls_checked"])
    assert any(test_case["name"] == "cross_org_denied" for test_case in report["test_cases"])


def test_access_policy_report_blocks_row_level_policy_without_org_id(tmp_path: Path) -> None:
    root = tmp_path
    contracts_dir = root / "contracts" / "data-products"
    contracts_dir.mkdir(parents=True)
    shutil.copytree(ROOT / "contracts" / "policies", root / "contracts" / "policies")
    contract = yaml.safe_load((ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml").read_text())
    contract["schema"]["columns"] = [
        column for column in contract["schema"]["columns"] if column["name"] != "org_id"
    ]
    (contracts_dir / "gold.recsys_interactions.v1.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False),
        encoding="utf-8",
    )

    report = build_access_policy_report(root, data_product_name="gold.recsys_interactions")

    assert report["passed"] is False
    assert any(failure["control"] == "registry_required_columns_present" for failure in report["failures"])
    assert any(failure["control"] == "row_level_org_isolation" for failure in report["failures"])


def test_write_access_policy_report_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "access-policy" / "report.json"
    result = write_access_policy_report(
        ROOT,
        output_path,
        data_product_name="gold.recsys_interactions",
        release_id="cli-access-policy",
        generated_at="2026-01-15T10:00:00Z",
    )

    assert result.output_path == output_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "access-policy" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "access-policy-check",
            "--root",
            str(ROOT),
            "--data-product",
            "gold.recsys_interactions",
            "--output",
            str(cli_output),
            "--release-id",
            "cli-access-policy",
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
    assert summary["data_product"] == "gold.recsys_interactions"
    assert cli_output.is_file()


def test_access_policy_registry_is_valid_and_evaluator_enforces_required_columns() -> None:
    result = validate_access_policy_registry(ROOT)
    assert result.errors == []
    assert result.checked_count == 1

    contract = yaml.safe_load((ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml").read_text())
    columns_without_org = [
        column for column in contract["schema"]["columns"] if column["name"] != "org_id"
    ]

    evaluation = evaluate_access_policy_contract(
        ROOT,
        data_product_name="gold.recsys_interactions",
        layer=contract["dataProduct"]["layer"],
        privacy=contract["privacy"],
        serving=contract["serving"],
        columns=columns_without_org,
    )

    assert evaluation["passed"] is False
    assert any(
        check["name"] == "required_columns_present" and check["passed"] is False
        for check in evaluation["checks"]
    )
