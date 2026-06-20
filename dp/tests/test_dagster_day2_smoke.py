from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.dagster_day2_smoke import DEFAULT_PARTITIONS, write_dagster_day2_smoke_report


ROOT = Path(__file__).resolve().parents[1]


def test_dagster_day2_smoke_writes_retry_tick_and_backfill_evidence(tmp_path: Path) -> None:
    result = write_dagster_day2_smoke_report(
        ROOT,
        tmp_path / "dagster-day2-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="dagster-day2-test",
        generated_at="2026-01-15T09:15:20Z",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    summary = report["summary"]
    schedule_ref = report["schedule_tick_history"]
    backfill_ref = report["backfill_materialization_history"]

    assert report == result.report
    assert report["artifact_type"] == "dagster_day2_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_dagster_in_process_day2_controls"
    assert "distributed_executor_or_kubernetes_run_launcher" in report["runtime_scope"]["not_covered"]
    assert "dagster_daemon_ha" in report["runtime_scope"]["not_covered"]
    assert summary["run_status"] == "SUCCESS"
    assert summary["schedule_tick_history_passed"] is True
    assert summary["schedule_tick_count"] == 1
    assert summary["retry_event_count"] == 1
    assert summary["retry_restart_count"] == 1
    assert summary["retry_policy_backoff_seconds"] > 0
    assert summary["retry_policy_verified"] is True
    assert summary["backfill_partition_count"] == len(DEFAULT_PARTITIONS)
    assert summary["asset_materialization_event_count"] == len(DEFAULT_PARTITIONS)
    assert summary["backfill_materialization_history_passed"] is True
    assert summary["distributed_executor_verified"] is False
    assert summary["failed_check_count"] == 0
    assert Path(schedule_ref["uri"]).is_file()
    assert Path(backfill_ref["uri"]).is_file()

    schedule_history = json.loads(Path(schedule_ref["uri"]).read_text(encoding="utf-8"))
    backfill_history = json.loads(Path(backfill_ref["uri"]).read_text(encoding="utf-8"))

    assert schedule_history["artifact_type"] == "dagster_schedule_tick_history.v1"
    assert schedule_history["ticks"][0]["run_id"] == summary["run_id"]
    assert schedule_history["ticks"][0]["status"] == "SUCCESS"
    assert backfill_history["artifact_type"] == "dagster_backfill_materialization_history.v1"
    assert backfill_history["run_id"] == summary["run_id"]
    assert {item["partition"] for item in backfill_history["materializations"]} == set(DEFAULT_PARTITIONS)
