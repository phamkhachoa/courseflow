from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

from enterprise_dp.semantic_metric_certification import (
    build_semantic_metric_certification_report,
    validate_semantic_metric_certification_registry,
    write_semantic_metric_certification_report,
)


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-17T10:30:00Z"


def test_repository_semantic_metric_certifications_are_valid() -> None:
    result = validate_semantic_metric_certification_registry(ROOT)

    assert result.errors == []
    assert result.checked_count >= 6


def test_semantic_metric_certification_report_passes_for_current_enterprise_metrics() -> None:
    report = build_semantic_metric_certification_report(
        ROOT,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert report["artifact_type"] == "semantic_metric_certification_report.v1"
    assert report["readiness_state"] == "certification_ready"
    assert report["passed"] is True
    assert report["summary"]["metric_count"] == 31
    assert report["summary"]["approved_metric_count"] == 31
    assert report["summary"]["approved_certification_count"] == 5
    assert report["summary"]["maker_checker_violation_count"] == 0
    revenue = metric_row(report, "revenue_net")
    assert revenue["status"] == "certified"
    assert revenue["certification"]["certification_id"] == "certify_finance_metrics_20260617"
    assert revenue["certification"]["approved_by"] != revenue["certification"]["requested_by"]
    assert "enterprise-kpi-scorecard" in revenue["certification"]["impact"]["useCases"]


def test_semantic_metric_certification_blocks_maker_checker_conflict(tmp_path: Path) -> None:
    root = copy_semantic_root(tmp_path)
    registry_path = root / "governance" / "semantic-metric-certifications.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registry["certifications"][0]["approvedBy"] = registry["certifications"][0]["requestedBy"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    report = build_semantic_metric_certification_report(root, environment="local", generated_at=GENERATED_AT)

    assert report["passed"] is False
    assert any("approvedBy must differ from requestedBy" in check["details"]["errors"][0] for check in report["checks"] if check["name"] == "certification_registry_valid")
    assert "maker_checker_violation" in metric_row(report, "revenue_net")["issues"]


def test_semantic_metric_certification_blocks_incomplete_impact_analysis(tmp_path: Path) -> None:
    root = copy_semantic_root(tmp_path)
    registry_path = root / "governance" / "semantic-metric-certifications.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registry["certifications"][0]["impact"]["useCases"] = ["enterprise-kpi-scorecard"]
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    report = build_semantic_metric_certification_report(root, environment="local", generated_at=GENERATED_AT)

    assert report["passed"] is False
    assert "impact_analysis_incomplete" in metric_row(report, "benefit_reconciliation_gap")["issues"]


def test_semantic_metric_certification_writer_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "certification" / "report.json"
    result = write_semantic_metric_certification_report(
        ROOT,
        output_path,
        environment="local",
        generated_at=GENERATED_AT,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "certification" / "cli-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "semantic-metric-certification-report",
            "--root",
            str(ROOT),
            "--output",
            str(cli_output),
            "--environment",
            "local",
            "--generated-at",
            GENERATED_AT,
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["passed"] is True
    assert summary["summary"]["approved_metric_count"] == 31
    assert cli_output.is_file()


def copy_semantic_root(tmp_path: Path) -> Path:
    root = tmp_path / "semantic-root"
    for directory in ("contracts", "domains", "governance", "use-cases"):
        shutil.copytree(ROOT / directory, root / directory)
    (root / "platform").mkdir(parents=True)
    shutil.copytree(ROOT / "platform" / "serving", root / "platform" / "serving")
    return root


def metric_row(report: dict[str, object], metric_id: str) -> dict[str, object]:
    rows = report["metrics"]
    assert isinstance(rows, list)
    return next(row for row in rows if isinstance(row, dict) and row["metric_id"] == metric_id)
