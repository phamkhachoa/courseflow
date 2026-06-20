from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.data_plane_smoke import write_data_plane_smoke_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"
INGESTED_AT = "2026-01-15T09:15:05Z"
BUILT_AT = "2026-01-15T09:15:10Z"
EVALUATION_TIME = "2026-01-15T09:15:15Z"


def test_data_plane_smoke_writes_finance_report_with_query_evidence(tmp_path: Path) -> None:
    result = write_data_plane_smoke_report(
        ROOT,
        tmp_path / "data-plane-smoke-report.json",
        output_dir=tmp_path / "run",
        release_id="finance-data-plane-smoke-test",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
        schema_id="registry:finance.benefit_settled.v1:1",
        snapshot_id="finance-benefit-smoke-test",
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))
    layers = {layer["name"]: layer for layer in report["layers"]}

    assert report == result.report
    assert report["artifact_type"] == "data_plane_smoke_report.v1"
    assert report["passed"] is True
    assert report["use_case_id"] == "finance-benefit-reconciliation"
    assert report["primary_output"] == "gold.finance_benefit_reconciliation"
    assert report["runtime_scope"]["mode"] == "local_ci_jsonl_medallion"
    assert "live_kafka_redpanda_broker_flow" in report["runtime_scope"]["not_covered"]
    assert layers["bronze.events_benefit_settled"]["actual_row_count"] == 4
    assert layers["silver.finance_benefit_transactions"]["passed"] is True
    assert layers["gold.finance_benefit_reconciliation"]["manifest_hash"] == layers["gold.finance_benefit_reconciliation"]["actual_hash"]
    assert report["summary"]["failed_check_count"] == 0
    assert report["query_smoke"]["query_name"] == "finance_reconciliation_by_status"
    assert report["query_smoke"]["result_row_count"] >= 1
    assert report["release_gates"]["P0-PIPELINE-QUALITY"] is True


def test_data_plane_smoke_cli_uses_default_finance_sample(tmp_path: Path) -> None:
    output = tmp_path / "smoke" / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "data-plane-smoke",
            "--root",
            str(ROOT),
            "--output-dir",
            str(tmp_path / "run"),
            "--output",
            str(output),
            "--release-id",
            "cli-finance-data-plane-smoke",
            "--generated-at",
            GENERATED_AT,
            "--ingested-at",
            INGESTED_AT,
            "--built-at",
            BUILT_AT,
            "--evaluation-time",
            EVALUATION_TIME,
            "--schema-id",
            "registry:finance.benefit_settled.v1:1",
            "--snapshot-id",
            "finance-benefit-cli-smoke",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    cli_output = json.loads(completed.stdout)
    report = json.loads(output.read_text(encoding="utf-8"))

    assert cli_output["passed"] is True
    assert cli_output["use_case_id"] == "finance-benefit-reconciliation"
    assert cli_output["query_name"] == "finance_reconciliation_by_status"
    assert report["passed"] is True
    assert Path(report["artifacts"][0]["path"]).is_file()


def test_data_plane_smoke_reports_failed_release_gates(tmp_path: Path) -> None:
    source = tmp_path / "invalid.jsonl"
    sample = (ROOT / "samples" / "finance" / "benefit_settled.jsonl").read_text(encoding="utf-8").splitlines()[0]
    record = json.loads(sample)
    record["headers"] = {"Authorization": "secret-token"}
    source.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    result = write_data_plane_smoke_report(
        ROOT,
        tmp_path / "failed-report.json",
        input_path=source,
        output_dir=tmp_path / "run",
        release_id="finance-data-plane-smoke-fail",
        generated_at=GENERATED_AT,
        ingested_at=INGESTED_AT,
        built_at=BUILT_AT,
        evaluation_time=EVALUATION_TIME,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["failed_check_count"] >= 1
    assert result.report["release_gates"]["P0-PIPELINE-QUALITY"] is False
    assert any(check["check"] == "release_gates" for check in result.report["summary"]["failed_checks"])
