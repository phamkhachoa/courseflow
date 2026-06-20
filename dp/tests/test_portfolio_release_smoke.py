from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.portfolio_release_smoke import write_portfolio_release_smoke_report


ROOT = Path(__file__).resolve().parents[1]


def test_portfolio_release_smoke_covers_all_gold_release_evidence(tmp_path: Path) -> None:
    result = write_portfolio_release_smoke_report(
        ROOT,
        tmp_path / "portfolio-release-smoke-report.json",
        output_dir=tmp_path / "run",
        generated_at="2026-06-16T12:10:00Z",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    final = report["artifacts"]["final"]

    assert report == result.report
    assert report["artifact_type"] == "portfolio_release_smoke_report.v1"
    assert report["passed"] is True
    assert report["summary"]["release_evidence_count"] == 8
    assert report["summary"]["passed_release_count"] == 8
    assert report["summary"]["source_bridge_preflight_count"] == 3
    assert report["summary"]["source_bridge_preflight_passed_count"] == 3
    assert report["summary"]["source_bridge_bronze_ingestion_passed_count"] == 3
    assert report["summary"]["source_activation_count"] == 7
    assert report["summary"]["source_activation_passed_count"] == 7
    assert report["summary"]["source_activation_ops_passed"] is True
    assert report["summary"]["covered_gold_count"] == 12
    assert report["summary"]["gold_count"] == 12
    assert report["summary"]["missing_gold_outputs"] == []
    assert report["summary"]["final_gold_release_blocker_count"] == 0
    assert report["summary"]["final_runtime_lineage_blocker_count"] == 0
    assert report["summary"]["final_source_activation_blocker_count"] == 0
    assert report["summary"]["final_contract_active_blocker_count"] == 0
    assert {
        item["bronze_target"]
        for item in report["source_bridge_bronze_evidence"]
    } == {
        "bronze.events_course_published",
        "bronze.events_enrollment_completed",
        "bronze.events_gradebook_final_grade_updated",
    }
    assert Path(final["catalog_bundle"]["uri"]).is_file()
    assert Path(final["openlineage_events"]["uri"]).is_file()
    assert Path(final["quality_slo_ops"]["uri"]).is_file()
    assert Path(final["catalog_lineage_ops"]["uri"]).is_file()
    assert Path(final["control_tower"]["uri"]).is_file()
    assert all(Path(item["uri"]).is_file() for item in report["release_evidence"])
    assert all(Path(item["bridge_manifest_path"]).is_file() for item in report["source_bridge_bronze_evidence"])
    assert all(Path(item["bronze_manifest_path"]).is_file() for item in report["source_bridge_bronze_evidence"])
    assert all(Path(item["source_readiness_bundle_path"]).is_file() for item in report["source_activation_evidence"])
    assert all(Path(item["activation_manifest_path"]).is_file() for item in report["source_activation_evidence"])


def test_portfolio_release_smoke_cli_outputs_partner_review_summary(tmp_path: Path) -> None:
    output = tmp_path / "portfolio-release-smoke-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "portfolio-release-smoke",
            "--root",
            str(ROOT),
            "--output-dir",
            str(tmp_path / "run"),
            "--output",
            str(output),
            "--generated-at",
            "2026-06-16T12:10:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)

    assert summary["passed"] is True
    assert summary["release_evidence_count"] == 8
    assert summary["source_bridge_preflight_count"] == 3
    assert summary["source_bridge_bronze_ingestion_passed_count"] == 3
    assert summary["source_activation_count"] == 7
    assert summary["source_activation_passed_count"] == 7
    assert summary["source_activation_ops_passed"] is True
    assert summary["covered_gold_count"] == 12
    assert summary["gold_count"] == 12
    assert summary["final_gold_release_blocker_count"] == 0
    assert summary["final_runtime_lineage_blocker_count"] == 0
    assert summary["final_source_activation_blocker_count"] == 0
    assert summary["final_contract_active_blocker_count"] == 0
    assert output.is_file()
