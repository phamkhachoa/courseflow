from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.catalog import canonical_json
from enterprise_dp.dagster_orchestration_smoke import write_dagster_orchestration_smoke_report
from enterprise_dp.live_lakehouse_smoke import write_live_lakehouse_smoke_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"


def test_dagster_orchestration_smoke_records_run_history(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live" / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live" / "run",
        release_id="dagster-smoke-test",
        generated_at=GENERATED_AT,
    )
    object_report = write_report(
        tmp_path / "object" / "object-store-commit-smoke-report.json",
        {
            "artifact_type": "object_store_commit_smoke_report.v1",
            "generated_at": GENERATED_AT,
            "passed": True,
            "summary": {
                "object_count": 3,
                "uploaded_object_count": 3,
                "readback_passed_count": 3,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )
    trino_report = write_report(
        tmp_path / "trino" / "trino-sql-runtime-smoke-report.json",
        {
            "artifact_type": "trino_sql_runtime_smoke_report.v1",
            "generated_at": GENERATED_AT,
            "passed": True,
            "summary": {
                "row_count": 4,
                "result_row_count": 2,
                "query_passed": True,
                "failed_check_count": 0,
                "failed_checks": [],
            },
        },
    )

    result = write_dagster_orchestration_smoke_report(
        ROOT,
        tmp_path / "dagster" / "dagster-orchestration-smoke-report.json",
        output_dir=tmp_path / "dagster" / "run",
        live_lakehouse_smoke_report_path=live.output_path,
        object_store_smoke_report_path=object_report,
        trino_sql_smoke_report_path=trino_report,
        release_id="dagster-smoke-test",
        generated_at=GENERATED_AT,
    )
    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "dagster_orchestration_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_dagster_in_process_run_history"
    assert "production_backfill_materialization_history" in report["runtime_scope"]["not_covered"]
    assert report["summary"]["run_status"] == "SUCCESS"
    assert report["summary"]["event_count"] > 0
    assert report["summary"]["op_success_count"] >= 4
    assert report["summary"]["validated_report_count"] == 3
    assert report["input_evidence"]["live_lakehouse_smoke"]["attached"] is True
    assert report["input_evidence"]["object_store_commit_smoke"]["attached"] is True
    assert report["input_evidence"]["trino_sql_runtime_smoke"]["attached"] is True
    assert any(event["event_type"] == "STEP_SUCCESS" for event in report["event_log"])


def test_dagster_orchestration_smoke_fails_when_runtime_evidence_is_missing(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live" / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live" / "run",
        release_id="dagster-smoke-missing-evidence",
        generated_at=GENERATED_AT,
    )

    result = write_dagster_orchestration_smoke_report(
        ROOT,
        tmp_path / "dagster" / "dagster-orchestration-smoke-report.json",
        output_dir=tmp_path / "dagster" / "run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="dagster-smoke-missing-evidence",
        generated_at=GENERATED_AT,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["run_status"] == "SUCCESS"
    assert result.report["summary"]["failed_check_count"] == 2
    failed_checks = result.report["summary"]["failed_checks"]
    assert any(item["check"] == "object_store_commit_smoke_attached" for item in failed_checks)
    assert any(item["check"] == "trino_sql_runtime_smoke_attached" for item in failed_checks)
    assert result.output_path.is_file()


def write_report(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")
    return path
