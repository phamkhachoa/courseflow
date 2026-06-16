from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_df.capabilities import build_capability_maturity_report, validate_capability_registry, write_capability_maturity_report


ROOT = Path(__file__).resolve().parents[1]


def test_capability_registry_is_valid() -> None:
    result = validate_capability_registry(ROOT)

    assert result.errors == []
    assert result.checked_count == 1


def test_capability_maturity_report_identifies_p0_gaps(tmp_path: Path) -> None:
    report = build_capability_maturity_report(
        ROOT,
        phase="P0",
        generated_at="2026-06-16T10:00:00Z",
    )

    assert report["artifact_type"] == "capability_maturity_report.v1"
    assert report["phase_filter"] == "P0"
    assert report["readiness_state"] == "not_ready"
    assert report["p0_ready"] is False
    assert report["passed"] is False
    assert report["summary"]["capability_count"] >= 8
    assert report["summary"]["target_gap_count"] >= 1
    blocker_ids = {blocker["capability_id"] for blocker in report["blockers"]}
    assert "platform-runtime-iac" in blocker_ids
    assert "event-cdc-ingestion-runtime" in blocker_ids


def test_capability_maturity_report_writer_and_cli(tmp_path: Path) -> None:
    output_path = tmp_path / "capabilities" / "p0-report.json"
    result = write_capability_maturity_report(
        ROOT,
        output_path,
        phase="P0",
        generated_at="2026-06-16T10:00:00Z",
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == result.report

    cli_output = tmp_path / "capabilities" / "cli-p0-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_df.cli",
            "capability-maturity-report",
            "--root",
            str(ROOT),
            "--phase",
            "P0",
            "--output",
            str(cli_output),
            "--generated-at",
            "2026-06-16T10:00:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["readiness_state"] == "not_ready"
    assert summary["p0_ready"] is False
    assert summary["passed"] is False
    assert summary["blocker_count"] >= 1
    assert cli_output.is_file()
