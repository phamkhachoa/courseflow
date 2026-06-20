from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.live_lakehouse_smoke import write_live_lakehouse_smoke_report
from enterprise_dp.trino_sql_smoke import CommandResult, write_trino_sql_runtime_smoke_report


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"
QUERY_OUTPUT = (
    '"EXCEPTION","3","17000","16500","-500","-120"\n'
    '"MATCHED","1","8000","8000","0","0"\n'
)


def test_trino_sql_runtime_smoke_loads_gold_rows_and_queries_trino(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live" / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live" / "run",
        release_id="trino-sql-smoke-test",
        generated_at=GENERATED_AT,
    )
    runner = FakeTrinoRunner()

    result = write_trino_sql_runtime_smoke_report(
        ROOT,
        tmp_path / "trino" / "trino-sql-runtime-smoke-report.json",
        output_dir=tmp_path / "trino" / "run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="trino-sql-smoke-test",
        generated_at=GENERATED_AT,
        command_runner=runner,
        wait_interval_seconds=0,
    )

    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "trino_sql_runtime_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_trino_memory_catalog_sql"
    assert "trino_iceberg_connector" in report["runtime_scope"]["not_covered"]
    assert report["trino"]["catalog"] == "memory"
    assert report["summary"]["row_count"] == 4
    assert report["summary"]["query_engine"] == "trino"
    assert report["summary"]["query_mode"] == "memory_catalog"
    assert report["summary"]["query_passed"] is True
    assert report["summary"]["result_row_count"] == 2
    assert report["query_probe"]["result"] == report["expected_query_probe"]
    assert any("INSERT INTO memory.enterprise_dp_smoke.finance_benefit_reconciliation" in sql for sql in runner.sql)


def test_trino_sql_runtime_smoke_fails_when_trino_is_unavailable(tmp_path: Path) -> None:
    live = write_live_lakehouse_smoke_report(
        ROOT,
        tmp_path / "live" / "live-lakehouse-smoke-report.json",
        output_dir=tmp_path / "live" / "run",
        release_id="trino-sql-smoke-fail",
        generated_at=GENERATED_AT,
    )

    result = write_trino_sql_runtime_smoke_report(
        ROOT,
        tmp_path / "trino" / "trino-sql-runtime-smoke-report.json",
        output_dir=tmp_path / "trino" / "run",
        live_lakehouse_smoke_report_path=live.output_path,
        release_id="trino-sql-smoke-fail",
        generated_at=GENERATED_AT,
        command_runner=UnavailableTrinoRunner(),
        wait_attempts=2,
        wait_interval_seconds=0,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["failed_check_count"] >= 1
    assert any(item["check"] == "trino_runtime_command" for item in result.report["summary"]["failed_checks"])
    assert result.output_path.is_file()


class FakeTrinoRunner:
    def __init__(self) -> None:
        self.sql: list[str] = []

    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        if args[-1] == "trino":
            return CommandResult(tuple(args), 0, "started", "")
        sql = args[-1]
        self.sql.append(sql)
        if sql == "SELECT 1":
            return CommandResult(tuple(args), 0, '"1"\n', "")
        if "INSERT INTO" in sql:
            return CommandResult(tuple(args), 0, "DROP TABLE\nCREATE SCHEMA\nCREATE TABLE\nINSERT: 4 rows\n", "")
        if "GROUP BY reconciliation_status" in sql:
            return CommandResult(tuple(args), 0, QUERY_OUTPUT, "")
        raise AssertionError(f"unexpected command: {args}")


class UnavailableTrinoRunner:
    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        if args[-1] == "trino":
            return CommandResult(tuple(args), 0, "started", "")
        return CommandResult(tuple(args), 1, "", "Trino server is still initializing")
