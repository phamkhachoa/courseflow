from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from enterprise_df.access_grants import (
    build_access_grant_evidence_report,
    evaluate_access_grants,
    validate_access_grant_registry,
    write_access_grant_evidence_report,
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
            "enterprise_df.cli",
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
