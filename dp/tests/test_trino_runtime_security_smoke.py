from __future__ import annotations

import json
from pathlib import Path

from enterprise_dp.trino_runtime_security_smoke import write_trino_runtime_security_smoke_report
from enterprise_dp.trino_sql_smoke import CommandResult


ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-01-15T09:15:20Z"


def test_trino_runtime_security_smoke_verifies_allow_deny_and_default_deny(tmp_path: Path) -> None:
    upstream_path = write_upstream_report(tmp_path)
    runner = FakeRuntimeSecurityRunner()

    result = write_trino_runtime_security_smoke_report(
        ROOT,
        tmp_path / "security" / "trino-runtime-security-smoke-report.json",
        output_dir=tmp_path / "security" / "run",
        trino_iceberg_minio_smoke_report_path=upstream_path,
        release_id="runtime-security-test",
        generated_at=GENERATED_AT,
        command_runner=runner,
        wait_interval_seconds=0,
    )
    report = json.loads(result.output_path.read_text(encoding="utf-8"))

    assert report == result.report
    assert report["artifact_type"] == "trino_runtime_security_smoke_report.v1"
    assert report["passed"] is True
    assert report["runtime_scope"]["mode"] == "local_trino_file_system_access_control_authorization_filters_masks"
    assert "runtime_security_enforcement" not in report["runtime_scope"]["not_covered"]
    assert "row_level_filter_enforcement" not in report["runtime_scope"]["not_covered"]
    assert "column_masking_enforcement" not in report["runtime_scope"]["not_covered"]
    assert report["summary"]["source_row_count"] == 4
    assert report["summary"]["identity_bound"] is True
    assert report["summary"]["allowed_query_passed"] is True
    assert report["summary"]["allowed_write_blocked"] is True
    assert report["summary"]["denied_query_blocked"] is True
    assert report["summary"]["unknown_user_blocked"] is True
    assert report["summary"]["security_probe_admin_unfiltered"] is True
    assert report["summary"]["row_level_filter_enforced"] is True
    assert report["summary"]["column_masking_enforced"] is True
    assert report["summary"]["centralized_audit_sink_passed"] is True
    assert report["summary"]["runtime_security_audit_event_count"] == 8
    assert report["summary"]["runtime_security_audit_failed_event_count"] == 0
    assert report["audit_sink"]["passed"] is True
    assert Path(report["audit_sink"]["events_path"]).is_file()
    assert Path(report["audit_sink"]["manifest_path"]).is_file()
    audit_events = [
        json.loads(line)
        for line in Path(report["audit_sink"]["events_path"]).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert {event["probe"] for event in audit_events} == {
        "identity_binding",
        "allowed_read",
        "read_only_write_denial",
        "explicit_denied_read",
        "unknown_user_default_deny",
        "admin_cleartext_baseline",
        "row_level_filter",
        "column_mask",
    }
    assert all(event["passed"] is True for event in audit_events)
    assert report["row_filter_probe"]["actual_count"] == 2
    assert report["row_filter_probe"]["actual_values"] == ["org-allowed"]
    assert report["column_mask_probe"]["actual_count"] == 4
    assert report["column_mask_probe"]["actual_values"] == ["MASKED"]
    assert report["summary"]["all_access_denied_errors_verified"] is True
    assert report["trino"]["access_control"]["rules"]["exists"] is True
    assert any("--user" in command["args"] for command in report["commands"])
    assert any("allowed_user_insert_denied_probe" == command["step"] for command in report["commands"])


def test_trino_runtime_security_smoke_fails_when_denied_user_can_select(tmp_path: Path) -> None:
    upstream_path = write_upstream_report(tmp_path)

    result = write_trino_runtime_security_smoke_report(
        ROOT,
        tmp_path / "security" / "trino-runtime-security-smoke-report.json",
        output_dir=tmp_path / "security" / "run",
        trino_iceberg_minio_smoke_report_path=upstream_path,
        release_id="runtime-security-fail",
        generated_at=GENERATED_AT,
        command_runner=OpenDeniedUserRunner(),
        wait_interval_seconds=0,
    )

    assert result.report["passed"] is False
    assert result.report["summary"]["denied_query_blocked"] is False
    assert any(item["check"] == "denied_user_select_blocked" for item in result.report["summary"]["failed_checks"])
    assert result.output_path.is_file()


def write_upstream_report(tmp_path: Path) -> Path:
    path = tmp_path / "trino-iceberg-minio-smoke-report.json"
    path.write_text(
        json.dumps(
            {
                "artifact_type": "trino_iceberg_minio_smoke_report.v1",
                "passed": True,
                "primary_output": "gold.finance_benefit_reconciliation",
                "summary": {
                    "row_count": 4,
                    "query_mode": "iceberg_jdbc_catalog_minio_s3",
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


class FakeRuntimeSecurityRunner:
    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        if "up" in args:
            return CommandResult(tuple(args), 0, "started", "")
        sql = args[-1]
        user = args[args.index("--user") + 1] if "--user" in args else "trino"
        if sql == "SELECT 1":
            return CommandResult(tuple(args), 0, '"1"\n', "")
        if sql == "SELECT current_user" and user == "dp_allowed":
            return CommandResult(tuple(args), 0, '"dp_allowed"\n', "")
        if sql.startswith("DROP TABLE IF EXISTS") and "finance_benefit_security_probe" in sql and user == "trino":
            return CommandResult(tuple(args), 0, "DROP TABLE\nCREATE TABLE\nINSERT: 4 rows\n", "")
        if sql.startswith("SELECT COUNT(*)") and user == "dp_allowed":
            return CommandResult(tuple(args), 0, '"4"\n', "")
        if sql.startswith("INSERT INTO") and user == "dp_allowed":
            return CommandResult(tuple(args), 1, "", "Access Denied: Cannot insert into table")
        if sql.startswith("SELECT COUNT(*)") and user == "dp_denied":
            return CommandResult(tuple(args), 1, "", "Access Denied: Cannot select from table")
        if sql.startswith("SELECT COUNT(*)") and user == "dp_unknown":
            return CommandResult(tuple(args), 1, "", "Access Denied: Cannot access catalog iceberg")
        if "array_sort(array_agg(DISTINCT beneficiary_id_hash))" in sql and user == "trino":
            return CommandResult(tuple(args), 0, '"4|beneficiary-alpha,beneficiary-beta,beneficiary-delta,beneficiary-gamma"\n', "")
        if "array_sort(array_agg(DISTINCT org_id))" in sql and user == "dp_row_filter":
            return CommandResult(tuple(args), 0, '"2|org-allowed"\n', "")
        if "array_sort(array_agg(DISTINCT beneficiary_id_hash))" in sql and user == "dp_masked":
            return CommandResult(tuple(args), 0, '"4|MASKED"\n', "")
        raise AssertionError(f"unexpected command: {args}")


class OpenDeniedUserRunner(FakeRuntimeSecurityRunner):
    def __call__(self, args: list[str], input_text: str | None, cwd: Path, timeout_seconds: int) -> CommandResult:
        if "--user" in args and args[args.index("--user") + 1] == "dp_denied" and args[-1].startswith("SELECT COUNT(*)"):
            return CommandResult(tuple(args), 0, '"4"\n', "")
        return super().__call__(args, input_text, cwd, timeout_seconds)
