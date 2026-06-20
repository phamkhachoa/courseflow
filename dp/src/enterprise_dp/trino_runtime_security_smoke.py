from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.live_lakehouse_smoke import DEFAULT_GENERATED_AT
from enterprise_dp.trino_iceberg_minio_smoke import (
    DEFAULT_CATALOG,
    DEFAULT_POSTGRES_SERVICE,
    DEFAULT_SCHEMA,
    DEFAULT_SERVICE,
    DEFAULT_TABLE,
    write_trino_iceberg_minio_smoke_report,
)
from enterprise_dp.trino_sql_smoke import (
    CommandResult,
    CommandRunner,
    execute_step,
    resolve_compose_path,
    run_command,
    sql_identifier,
    wait_for_trino,
)


DEFAULT_ALLOWED_USER = "dp_allowed"
DEFAULT_DENIED_USER = "dp_denied"
DEFAULT_UNKNOWN_USER = "dp_unknown"
DEFAULT_ROW_FILTER_USER = "dp_row_filter"
DEFAULT_MASKED_USER = "dp_masked"
DEFAULT_SECURITY_PROBE_TABLE = "finance_benefit_security_probe"
SECURITY_PROBE_ROWS = (
    ("org-allowed", "beneficiary-alpha", "SETTLED", 1000),
    ("org-allowed", "beneficiary-beta", "SETTLED", 2000),
    ("org-denied", "beneficiary-gamma", "SETTLED", 3000),
    ("org-denied", "beneficiary-delta", "REVERSED", -500),
)


@dataclass(frozen=True)
class TrinoRuntimeSecuritySmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_trino_runtime_security_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    trino_iceberg_minio_smoke_report_path: str | Path | None = None,
    compose_file: str | Path | None = None,
    service: str = DEFAULT_SERVICE,
    postgres_service: str = DEFAULT_POSTGRES_SERVICE,
    catalog: str = DEFAULT_CATALOG,
    schema: str = DEFAULT_SCHEMA,
    table: str = DEFAULT_TABLE,
    security_probe_table: str = DEFAULT_SECURITY_PROBE_TABLE,
    allowed_user: str = DEFAULT_ALLOWED_USER,
    denied_user: str = DEFAULT_DENIED_USER,
    unknown_user: str = DEFAULT_UNKNOWN_USER,
    row_filter_user: str = DEFAULT_ROW_FILTER_USER,
    masked_user: str = DEFAULT_MASKED_USER,
    use_case_id: str = "finance-benefit-reconciliation",
    release_id: str = "local-trino-runtime-security-smoke",
    environment: str = "local",
    generated_at: str | None = None,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 12,
    wait_interval_seconds: float = 2.0,
    start_runtime: bool = True,
) -> TrinoRuntimeSecuritySmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    generated = generated_at or DEFAULT_GENERATED_AT
    upstream_path, upstream_report = load_or_create_trino_iceberg_report(
        platform_root,
        target_dir,
        trino_iceberg_minio_smoke_report_path=trino_iceberg_minio_smoke_report_path,
        compose_file=compose_file,
        service=service,
        postgres_service=postgres_service,
        catalog=catalog,
        schema=schema,
        table=table,
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=generated,
        command_runner=command_runner,
        command_timeout_seconds=command_timeout_seconds,
        wait_attempts=wait_attempts,
        wait_interval_seconds=wait_interval_seconds,
        start_runtime=start_runtime,
    )
    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    safe_catalog = sql_identifier(catalog)
    safe_schema = sql_identifier(schema)
    safe_table = sql_identifier(table)
    safe_security_probe_table = sql_identifier(security_probe_table)
    qualified_table = f"{safe_catalog}.{safe_schema}.{safe_table}"
    qualified_security_probe_table = f"{safe_catalog}.{safe_schema}.{safe_security_probe_table}"
    upstream_summary = upstream_report.get("summary") if isinstance(upstream_report.get("summary"), dict) else {}
    source_row_count = int_value(upstream_summary.get("row_count", 0))
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []
    identity_probe: dict[str, Any] = {"passed": False}
    allowed_probe: dict[str, Any] = {"passed": False}
    allowed_write_deny_probe: dict[str, Any] = {"passed": False}
    denied_probe: dict[str, Any] = {"passed": False}
    unknown_probe: dict[str, Any] = {"passed": False}
    security_probe_admin: dict[str, Any] = {"passed": False}
    row_filter_probe: dict[str, Any] = {"passed": False}
    column_mask_probe: dict[str, Any] = {"passed": False}
    audit_events_path = target_dir / "audit" / "trino-runtime-security-audit.jsonl"
    audit_manifest_path = target_dir / "audit" / "trino-runtime-security-audit-manifest.json"
    audit_sink: dict[str, Any] = {"passed": False}

    try:
        if start_runtime:
            execute_step(
                command_log,
                runner,
                [
                    "docker",
                    "compose",
                    "-f",
                    compose_path.as_posix(),
                    "up",
                    "-d",
                    "minio",
                    postgres_service,
                    service,
                ],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="compose_up",
            )
            execute_step(
                command_log,
                runner,
                [
                    "docker",
                    "compose",
                    "-f",
                    compose_path.as_posix(),
                    "up",
                    "-d",
                    "--force-recreate",
                    service,
                ],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="force_recreate_trino_for_policy_reload",
            )
        wait_for_trino(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            attempts=wait_attempts,
            interval_seconds=wait_interval_seconds,
        )
        identity_probe = current_user_probe(
            execute_trino_sql_as_user(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="allowed_user_identity_probe",
                user=allowed_user,
                sql="SELECT current_user",
            ),
            expected_user=allowed_user,
        )
        execute_trino_sql_as_user(
            command_log,
            runner,
            compose_path=compose_path,
            service=service,
            cwd=platform_root,
            timeout_seconds=command_timeout_seconds,
            step="create_security_probe_table",
            user="trino",
            sql=create_security_probe_table_sql(qualified_security_probe_table),
        )
        allowed_probe = allowed_select_probe(
            execute_trino_sql_as_user(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="allowed_user_select_probe",
                user=allowed_user,
                sql=f"SELECT COUNT(*) FROM {qualified_table}",
            ),
            expected_count=source_row_count,
        )
        allowed_write_deny_probe = denied_statement_probe(
            execute_trino_sql_as_user(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="allowed_user_insert_denied_probe",
                user=allowed_user,
                sql=f"INSERT INTO {qualified_table} VALUES ('POLICY_PROBE', 0, 0, 0, 0)",
                raise_on_error=False,
            )
        )
        denied_probe = denied_select_probe(
            execute_trino_sql_as_user(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="denied_user_select_probe",
                user=denied_user,
                sql=f"SELECT COUNT(*) FROM {qualified_table}",
                raise_on_error=False,
            )
        )
        unknown_probe = denied_statement_probe(
            execute_trino_sql_as_user(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="unknown_user_default_deny_probe",
                user=unknown_user,
                sql=f"SELECT COUNT(*) FROM {qualified_table}",
                raise_on_error=False,
            )
        )
        security_probe_admin = security_probe_values_probe(
            execute_trino_sql_as_user(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="admin_security_probe_unfiltered",
                user="trino",
                sql=security_probe_distinct_values_sql(qualified_security_probe_table, "beneficiary_id_hash"),
            ),
            expected_count=len(SECURITY_PROBE_ROWS),
            expected_values=sorted(row[1] for row in SECURITY_PROBE_ROWS),
            probe_name="admin_cleartext_unfiltered_probe",
        )
        row_filter_probe = security_probe_values_probe(
            execute_trino_sql_as_user(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="row_filter_user_probe",
                user=row_filter_user,
                sql=security_probe_distinct_values_sql(qualified_security_probe_table, "org_id"),
            ),
            expected_count=2,
            expected_values=["org-allowed"],
            probe_name="row_level_filter_probe",
        )
        column_mask_probe = security_probe_values_probe(
            execute_trino_sql_as_user(
                command_log,
                runner,
                compose_path=compose_path,
                service=service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="masked_user_probe",
                user=masked_user,
                sql=security_probe_distinct_values_sql(qualified_security_probe_table, "beneficiary_id_hash"),
            ),
            expected_count=len(SECURITY_PROBE_ROWS),
            expected_values=["MASKED"],
            probe_name="column_mask_probe",
        )
    except RuntimeError as exc:
        failed_checks.append({"check": "trino_runtime_security_command", "message": str(exc)})
    failed_checks.extend(
        failed_runtime_security_checks(
            upstream_report=upstream_report,
            identity_probe=identity_probe,
            allowed_probe=allowed_probe,
            allowed_write_deny_probe=allowed_write_deny_probe,
            denied_probe=denied_probe,
            unknown_probe=unknown_probe,
            security_probe_admin=security_probe_admin,
            row_filter_probe=row_filter_probe,
            column_mask_probe=column_mask_probe,
            source_row_count=source_row_count,
        )
    )
    row_filter_passed = row_filter_probe.get("passed") is True
    column_mask_passed = column_mask_probe.get("passed") is True
    audit_sink = write_runtime_security_audit_sink(
        audit_events_path,
        audit_manifest_path,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        use_case_id=use_case_id,
        qualified_table=qualified_table,
        qualified_security_probe_table=qualified_security_probe_table,
        allowed_user=allowed_user,
        denied_user=denied_user,
        unknown_user=unknown_user,
        row_filter_user=row_filter_user,
        masked_user=masked_user,
        identity_probe=identity_probe,
        allowed_probe=allowed_probe,
        allowed_write_deny_probe=allowed_write_deny_probe,
        denied_probe=denied_probe,
        unknown_probe=unknown_probe,
        security_probe_admin=security_probe_admin,
        row_filter_probe=row_filter_probe,
        column_mask_probe=column_mask_probe,
    )
    if audit_sink.get("passed") is not True:
        failed_checks.append(
            {
                "check": "runtime_security_audit_sink_passed",
                "event_count": audit_sink.get("event_count", 0),
                "failed_event_count": audit_sink.get("failed_event_count", 0),
            }
        )
    audit_sink_passed = audit_sink.get("passed") is True
    covered_scope = [
        "trino_file_system_access_control_loaded",
        "trino_allowed_user_identity_bound_to_query",
        "allowed_user_select_query_succeeded",
        "allowed_user_write_query_blocked",
        "denied_user_select_query_blocked",
        "unknown_user_default_deny_verified",
        "access_denied_error_verified",
        "policy_targets_iceberg_gold_table",
    ]
    if row_filter_passed:
        covered_scope.append("row_level_filter_enforced_on_security_probe_table")
    if column_mask_passed:
        covered_scope.append("column_mask_enforced_on_security_probe_table")
    if audit_sink_passed:
        covered_scope.append("local_centralized_runtime_security_audit_sink_written")
    not_covered_scope = [
        "keycloak_or_oidc_authentication",
        "ranger_or_opa_policy_decision_point",
        "policy_admin_maker_checker",
        "production_secret_rotation",
    ]
    if not audit_sink_passed:
        not_covered_scope.append("centralized_audit_sink")
    if not row_filter_passed:
        not_covered_scope.append("row_level_filter_enforcement")
    if not column_mask_passed:
        not_covered_scope.append("column_masking_enforcement")
    report = {
        "artifact_type": "trino_runtime_security_smoke_report.v1",
        "report_version": 1,
        "capability_id": "runtime-security-enforcement",
        "report_id": f"trino-runtime-security-smoke:{environment}:{use_case_id}:{release_id}",
        "generated_at": generated,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "primary_output": upstream_report.get("primary_output"),
        "runtime_scope": {
            "mode": "local_trino_file_system_access_control_authorization_filters_masks",
            "covered": covered_scope,
            "not_covered": not_covered_scope,
        },
        "trino": {
            "compose_file": compose_path.as_posix(),
            "service": service,
            "catalog": safe_catalog,
            "schema": safe_schema,
            "table": safe_table,
            "security_probe_table": safe_security_probe_table,
            "qualified_table": qualified_table,
            "qualified_security_probe_table": qualified_security_probe_table,
            "allowed_user": allowed_user,
            "denied_user": denied_user,
            "unknown_user": unknown_user,
            "row_filter_user": row_filter_user,
            "masked_user": masked_user,
            "access_control": {
                "type": "file_system_access_control",
                "properties": policy_file_ref(platform_root, "platform/runtime/local/trino/access-control.properties"),
                "rules": policy_file_ref(platform_root, "platform/runtime/local/trino/access-control-rules.json"),
                "reload_strategy": "docker_compose_force_recreate_trino",
            },
        },
        "trino_iceberg_minio_smoke": {
            "path": upstream_path.as_posix(),
            "hash": hash_file(upstream_path),
            "passed": upstream_report.get("passed") is True,
        },
        "source_table": {
            "row_count": source_row_count,
            "query_mode": upstream_summary.get("query_mode"),
        },
        "identity_probe": identity_probe,
        "allowed_select_probe": allowed_probe,
        "allowed_write_deny_probe": allowed_write_deny_probe,
        "denied_select_probe": denied_probe,
        "unknown_user_deny_probe": unknown_probe,
        "security_probe_admin": security_probe_admin,
        "row_filter_probe": row_filter_probe,
        "column_mask_probe": column_mask_probe,
        "audit_sink": {
            "mode": "local_jsonl_structured_runtime_security_audit",
            "events_path": audit_events_path.as_posix(),
            "events_hash": hash_file(audit_events_path) if audit_events_path.is_file() else None,
            "manifest_path": audit_manifest_path.as_posix(),
            "manifest_hash": hash_file(audit_manifest_path) if audit_manifest_path.is_file() else None,
            "passed": audit_sink.get("passed") is True,
            "event_count": audit_sink.get("event_count", 0),
            "failed_event_count": audit_sink.get("failed_event_count", 0),
        },
        "commands": command_log,
        "summary": {
            "query_engine": "trino",
            "query_mode": "iceberg_jdbc_catalog_minio_s3_file_access_control",
            "source_row_count": source_row_count,
            "allowed_user": allowed_user,
            "denied_user": denied_user,
            "unknown_user": unknown_user,
            "row_filter_user": row_filter_user,
            "masked_user": masked_user,
            "identity_bound": identity_probe.get("passed") is True,
            "allowed_query_passed": allowed_probe.get("passed") is True,
            "allowed_write_blocked": allowed_write_deny_probe.get("blocked") is True,
            "denied_query_blocked": denied_probe.get("blocked") is True,
            "unknown_user_blocked": unknown_probe.get("blocked") is True,
            "security_probe_admin_unfiltered": security_probe_admin.get("passed") is True,
            "row_level_filter_enforced": row_filter_passed,
            "column_masking_enforced": column_mask_passed,
            "centralized_audit_sink_passed": audit_sink_passed,
            "runtime_security_audit_event_count": audit_sink.get("event_count", 0),
            "runtime_security_audit_failed_event_count": audit_sink.get("failed_event_count", 0),
            "access_denied_verified": denied_probe.get("access_denied_verified") is True,
            "all_access_denied_errors_verified": all(
                probe.get("access_denied_verified") is True
                for probe in (allowed_write_deny_probe, denied_probe, unknown_probe)
            ),
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = not failed_checks
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return TrinoRuntimeSecuritySmokeResult(output_path=target, report=report)


def load_or_create_trino_iceberg_report(
    platform_root: Path,
    target_dir: Path,
    *,
    trino_iceberg_minio_smoke_report_path: str | Path | None,
    compose_file: str | Path | None,
    service: str,
    postgres_service: str,
    catalog: str,
    schema: str,
    table: str,
    use_case_id: str,
    release_id: str,
    environment: str,
    generated_at: str,
    command_runner: CommandRunner | None,
    command_timeout_seconds: int,
    wait_attempts: int,
    wait_interval_seconds: float,
    start_runtime: bool,
) -> tuple[Path, dict[str, Any]]:
    if trino_iceberg_minio_smoke_report_path:
        report_path = Path(trino_iceberg_minio_smoke_report_path)
        return report_path, load_json(report_path)
    result = write_trino_iceberg_minio_smoke_report(
        platform_root,
        target_dir / "trino-iceberg-minio-smoke-report.json",
        output_dir=target_dir / "trino-iceberg-minio-run",
        compose_file=compose_file,
        service=service,
        postgres_service=postgres_service,
        catalog=catalog,
        schema=schema,
        table=table,
        use_case_id=use_case_id,
        release_id=release_id,
        environment=environment,
        generated_at=generated_at,
        command_runner=command_runner,
        command_timeout_seconds=command_timeout_seconds,
        wait_attempts=wait_attempts,
        wait_interval_seconds=wait_interval_seconds,
        start_runtime=start_runtime,
    )
    return result.output_path, result.report


def execute_trino_sql_as_user(
    command_log: list[dict[str, Any]],
    runner: CommandRunner,
    *,
    compose_path: Path,
    service: str,
    cwd: Path,
    timeout_seconds: int,
    step: str,
    user: str,
    sql: str,
    raise_on_error: bool = True,
) -> CommandResult:
    return execute_step(
        command_log,
        runner,
        [
            "docker",
            "compose",
            "-f",
            compose_path.as_posix(),
            "exec",
            "-T",
            service,
            "trino",
            "--user",
            user,
            "--execute",
            sql,
        ],
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        step=step,
        raise_on_error=raise_on_error,
    )


def current_user_probe(result: CommandResult, *, expected_user: str) -> dict[str, Any]:
    actual = parse_single_text(result.stdout)
    return {
        "passed": result.returncode == 0 and actual == expected_user,
        "expected_user": expected_user,
        "actual_user": actual,
        "returncode": result.returncode,
    }


def allowed_select_probe(result: CommandResult, *, expected_count: int) -> dict[str, Any]:
    actual_count = parse_single_int(result.stdout)
    return {
        "passed": result.returncode == 0 and actual_count == expected_count and expected_count > 0,
        "expected_count": expected_count,
        "actual_count": actual_count,
        "returncode": result.returncode,
    }


def create_security_probe_table_sql(qualified_table: str) -> str:
    values = ", ".join(
        f"('{org_id}', '{beneficiary_id_hash}', '{settlement_status}', {amount_cents})"
        for org_id, beneficiary_id_hash, settlement_status, amount_cents in SECURITY_PROBE_ROWS
    )
    return " ".join(
        [
            f"DROP TABLE IF EXISTS {qualified_table}",
            f"; CREATE TABLE {qualified_table} ("
            "org_id varchar, "
            "beneficiary_id_hash varchar, "
            "settlement_status varchar, "
            "amount_cents bigint"
            ") WITH (format='PARQUET')",
            f"; INSERT INTO {qualified_table} VALUES {values}",
        ]
    )


def security_probe_distinct_values_sql(qualified_table: str, column: str) -> str:
    safe_column = sql_identifier(column)
    return (
        "SELECT CAST(COUNT(*) AS VARCHAR) || '|' || "
        f"COALESCE(array_join(array_sort(array_agg(DISTINCT {safe_column})), ','), '') "
        f"FROM {qualified_table}"
    )


def security_probe_values_probe(
    result: CommandResult,
    *,
    expected_count: int,
    expected_values: list[str],
    probe_name: str,
) -> dict[str, Any]:
    actual_count, actual_values = parse_count_and_values(result.stdout)
    return {
        "passed": result.returncode == 0 and actual_count == expected_count and actual_values == expected_values,
        "name": probe_name,
        "expected_count": expected_count,
        "actual_count": actual_count,
        "expected_values": expected_values,
        "actual_values": actual_values,
        "returncode": result.returncode,
        "error_preview": (result.stderr or "").strip()[:500],
    }


def write_runtime_security_audit_sink(
    events_path: Path,
    manifest_path: Path,
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    qualified_table: str,
    qualified_security_probe_table: str,
    allowed_user: str,
    denied_user: str,
    unknown_user: str,
    row_filter_user: str,
    masked_user: str,
    identity_probe: dict[str, Any],
    allowed_probe: dict[str, Any],
    allowed_write_deny_probe: dict[str, Any],
    denied_probe: dict[str, Any],
    unknown_probe: dict[str, Any],
    security_probe_admin: dict[str, Any],
    row_filter_probe: dict[str, Any],
    column_mask_probe: dict[str, Any],
) -> dict[str, Any]:
    events = runtime_security_audit_events(
        generated_at=generated_at,
        environment=environment,
        release_id=release_id,
        use_case_id=use_case_id,
        qualified_table=qualified_table,
        qualified_security_probe_table=qualified_security_probe_table,
        allowed_user=allowed_user,
        denied_user=denied_user,
        unknown_user=unknown_user,
        row_filter_user=row_filter_user,
        masked_user=masked_user,
        identity_probe=identity_probe,
        allowed_probe=allowed_probe,
        allowed_write_deny_probe=allowed_write_deny_probe,
        denied_probe=denied_probe,
        unknown_probe=unknown_probe,
        security_probe_admin=security_probe_admin,
        row_filter_probe=row_filter_probe,
        column_mask_probe=column_mask_probe,
    )
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("".join(f"{canonical_json(event)}\n" for event in events), encoding="utf-8")
    failed_event_count = sum(1 for event in events if event.get("passed") is not True)
    manifest = {
        "artifact_type": "runtime_security_audit_sink_manifest.v1",
        "report_version": 1,
        "audit_sink_id": stable_id("runtime-security-audit-sink", environment, release_id, use_case_id, events),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "mode": "local_jsonl_structured_runtime_security_audit",
        "events": {
            "path": events_path.as_posix(),
            "hash": hash_file(events_path),
            "event_count": len(events),
            "failed_event_count": failed_event_count,
        },
        "coverage": {
            "identity_binding": has_passed_event(events, "identity_binding"),
            "allowed_read": has_passed_event(events, "allowed_read"),
            "read_only_write_denial": has_passed_event(events, "read_only_write_denial"),
            "explicit_denied_read": has_passed_event(events, "explicit_denied_read"),
            "unknown_user_default_deny": has_passed_event(events, "unknown_user_default_deny"),
            "admin_cleartext_baseline": has_passed_event(events, "admin_cleartext_baseline"),
            "row_level_filter": has_passed_event(events, "row_level_filter"),
            "column_mask": has_passed_event(events, "column_mask"),
        },
    }
    manifest["passed"] = (
        manifest["events"]["event_count"] == 8
        and manifest["events"]["failed_event_count"] == 0
        and all(manifest["coverage"].values())
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return {
        "passed": manifest["passed"],
        "event_count": manifest["events"]["event_count"],
        "failed_event_count": manifest["events"]["failed_event_count"],
        "events_path": events_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "events_hash": manifest["events"]["hash"],
        "manifest_hash": hash_file(manifest_path),
    }


def runtime_security_audit_events(
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    qualified_table: str,
    qualified_security_probe_table: str,
    allowed_user: str,
    denied_user: str,
    unknown_user: str,
    row_filter_user: str,
    masked_user: str,
    identity_probe: dict[str, Any],
    allowed_probe: dict[str, Any],
    allowed_write_deny_probe: dict[str, Any],
    denied_probe: dict[str, Any],
    unknown_probe: dict[str, Any],
    security_probe_admin: dict[str, Any],
    row_filter_probe: dict[str, Any],
    column_mask_probe: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        audit_event(
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            probe="identity_binding",
            principal=allowed_user,
            action="identity.bind",
            resource="trino.current_user",
            expected_decision="ALLOW",
            actual_decision="ALLOW" if identity_probe.get("passed") is True else "MISMATCH",
            passed=identity_probe.get("passed") is True,
            evidence=identity_probe,
        ),
        audit_event(
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            probe="allowed_read",
            principal=allowed_user,
            action="data.read",
            resource=qualified_table,
            expected_decision="ALLOW",
            actual_decision="ALLOW" if allowed_probe.get("passed") is True else "MISMATCH",
            passed=allowed_probe.get("passed") is True,
            evidence=count_evidence(allowed_probe),
        ),
        audit_event(
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            probe="read_only_write_denial",
            principal=allowed_user,
            action="data.write",
            resource=qualified_table,
            expected_decision="DENY",
            actual_decision="DENY" if allowed_write_deny_probe.get("access_denied_verified") is True else "MISMATCH",
            passed=allowed_write_deny_probe.get("access_denied_verified") is True,
            evidence=deny_evidence(allowed_write_deny_probe),
        ),
        audit_event(
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            probe="explicit_denied_read",
            principal=denied_user,
            action="data.read",
            resource=qualified_table,
            expected_decision="DENY",
            actual_decision="DENY" if denied_probe.get("access_denied_verified") is True else "MISMATCH",
            passed=denied_probe.get("access_denied_verified") is True,
            evidence=deny_evidence(denied_probe),
        ),
        audit_event(
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            probe="unknown_user_default_deny",
            principal=unknown_user,
            action="data.read",
            resource=qualified_table,
            expected_decision="DENY",
            actual_decision="DENY" if unknown_probe.get("access_denied_verified") is True else "MISMATCH",
            passed=unknown_probe.get("access_denied_verified") is True,
            evidence=deny_evidence(unknown_probe),
        ),
        audit_event(
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            probe="admin_cleartext_baseline",
            principal="trino",
            action="security_probe.baseline_read",
            resource=qualified_security_probe_table,
            expected_decision="ALLOW",
            actual_decision="ALLOW" if security_probe_admin.get("passed") is True else "MISMATCH",
            passed=security_probe_admin.get("passed") is True,
            evidence=values_evidence(security_probe_admin),
        ),
        audit_event(
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            probe="row_level_filter",
            principal=row_filter_user,
            action="data.read_filtered",
            resource=qualified_security_probe_table,
            expected_decision="FILTER",
            actual_decision="FILTER" if row_filter_probe.get("passed") is True else "MISMATCH",
            passed=row_filter_probe.get("passed") is True,
            evidence=values_evidence(row_filter_probe),
        ),
        audit_event(
            generated_at=generated_at,
            environment=environment,
            release_id=release_id,
            use_case_id=use_case_id,
            probe="column_mask",
            principal=masked_user,
            action="data.read_masked",
            resource=qualified_security_probe_table,
            expected_decision="MASK",
            actual_decision="MASK" if column_mask_probe.get("passed") is True else "MISMATCH",
            passed=column_mask_probe.get("passed") is True,
            evidence=values_evidence(column_mask_probe),
        ),
    ]


def audit_event(
    *,
    generated_at: str,
    environment: str,
    release_id: str,
    use_case_id: str,
    probe: str,
    principal: str,
    action: str,
    resource: str,
    expected_decision: str,
    actual_decision: str,
    passed: bool,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    event = {
        "artifact_type": "runtime_security_audit_event.v1",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "use_case_id": use_case_id,
        "probe": probe,
        "principal": principal,
        "action": action,
        "resource": resource,
        "expected_decision": expected_decision,
        "actual_decision": actual_decision,
        "passed": passed,
        "evidence": evidence,
    }
    return {"event_id": stable_id("runtime-security-audit-event", event), **event}


def count_evidence(probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "expected_count": probe.get("expected_count"),
        "actual_count": probe.get("actual_count"),
        "returncode": probe.get("returncode"),
    }


def deny_evidence(probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "blocked": probe.get("blocked"),
        "access_denied_verified": probe.get("access_denied_verified"),
        "returncode": probe.get("returncode"),
        "error_hash": stable_id("access-denied-error", probe.get("error_preview")),
    }


def values_evidence(probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "expected_count": probe.get("expected_count"),
        "actual_count": probe.get("actual_count"),
        "expected_values_hash": stable_id("values", probe.get("expected_values", [])),
        "actual_values_hash": stable_id("values", probe.get("actual_values", [])),
        "returncode": probe.get("returncode"),
    }


def has_passed_event(events: list[dict[str, Any]], probe: str) -> bool:
    return any(event.get("probe") == probe and event.get("passed") is True for event in events)


def denied_select_probe(result: CommandResult) -> dict[str, Any]:
    return denied_statement_probe(result)


def denied_statement_probe(result: CommandResult) -> dict[str, Any]:
    error_text = (result.stderr or result.stdout).strip()
    access_denied = "access denied" in error_text.lower()
    return {
        "passed": result.returncode != 0 and access_denied,
        "blocked": result.returncode != 0,
        "access_denied_verified": access_denied,
        "returncode": result.returncode,
        "error_preview": error_text[:500],
    }


def failed_runtime_security_checks(
    *,
    upstream_report: dict[str, Any],
    identity_probe: dict[str, Any],
    allowed_probe: dict[str, Any],
    allowed_write_deny_probe: dict[str, Any],
    denied_probe: dict[str, Any],
    unknown_probe: dict[str, Any],
    security_probe_admin: dict[str, Any],
    row_filter_probe: dict[str, Any],
    column_mask_probe: dict[str, Any],
    source_row_count: int,
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if upstream_report.get("passed") is not True:
        failed.append({"check": "trino_iceberg_minio_smoke_passed", "passed": upstream_report.get("passed")})
    if source_row_count <= 0:
        failed.append({"check": "source_row_count_positive", "actual": source_row_count})
    if identity_probe.get("passed") is not True:
        failed.append(
            {
                "check": "allowed_user_identity_bound",
                "expected_user": identity_probe.get("expected_user"),
                "actual_user": identity_probe.get("actual_user"),
            }
        )
    if allowed_probe.get("passed") is not True:
        failed.append(
            {
                "check": "allowed_user_select_query",
                "expected_count": allowed_probe.get("expected_count"),
                "actual_count": allowed_probe.get("actual_count"),
                "returncode": allowed_probe.get("returncode"),
            }
        )
    if allowed_write_deny_probe.get("blocked") is not True:
        failed.append({"check": "allowed_user_write_blocked", "returncode": allowed_write_deny_probe.get("returncode")})
    if allowed_write_deny_probe.get("access_denied_verified") is not True:
        failed.append(
            {"check": "allowed_user_write_access_denied_error", "error_preview": allowed_write_deny_probe.get("error_preview")}
        )
    if denied_probe.get("blocked") is not True:
        failed.append({"check": "denied_user_select_blocked", "returncode": denied_probe.get("returncode")})
    if denied_probe.get("access_denied_verified") is not True:
        failed.append({"check": "denied_user_access_denied_error", "error_preview": denied_probe.get("error_preview")})
    if unknown_probe.get("blocked") is not True:
        failed.append({"check": "unknown_user_default_deny", "returncode": unknown_probe.get("returncode")})
    if unknown_probe.get("access_denied_verified") is not True:
        failed.append({"check": "unknown_user_access_denied_error", "error_preview": unknown_probe.get("error_preview")})
    if security_probe_admin.get("passed") is not True:
        failed.append(
            {
                "check": "security_probe_admin_unfiltered_baseline",
                "expected_count": security_probe_admin.get("expected_count"),
                "actual_count": security_probe_admin.get("actual_count"),
                "expected_values": security_probe_admin.get("expected_values"),
                "actual_values": security_probe_admin.get("actual_values"),
            }
        )
    if row_filter_probe.get("passed") is not True:
        failed.append(
            {
                "check": "row_level_filter_enforced",
                "expected_count": row_filter_probe.get("expected_count"),
                "actual_count": row_filter_probe.get("actual_count"),
                "expected_values": row_filter_probe.get("expected_values"),
                "actual_values": row_filter_probe.get("actual_values"),
                "error_preview": row_filter_probe.get("error_preview"),
            }
        )
    if column_mask_probe.get("passed") is not True:
        failed.append(
            {
                "check": "column_masking_enforced",
                "expected_count": column_mask_probe.get("expected_count"),
                "actual_count": column_mask_probe.get("actual_count"),
                "expected_values": column_mask_probe.get("expected_values"),
                "actual_values": column_mask_probe.get("actual_values"),
                "error_preview": column_mask_probe.get("error_preview"),
            }
        )
    return failed


def policy_file_ref(platform_root: Path, relative_path: str) -> dict[str, Any]:
    path = platform_root / relative_path
    return {
        "path": relative_path,
        "hash": hash_file(path) if path.is_file() else None,
        "exists": path.is_file(),
    }


def parse_single_int(stdout: str) -> int:
    value = parse_single_text(stdout)
    return int(value) if value.isdigit() else 0


def parse_single_text(stdout: str) -> str:
    for line in stdout.splitlines():
        stripped = line.strip().strip('"')
        if stripped:
            return stripped
    return ""


def parse_count_and_values(stdout: str) -> tuple[int, list[str]]:
    text = parse_single_text(stdout)
    if "|" not in text:
        return 0, []
    count_text, values_text = text.split("|", 1)
    values = [value for value in values_text.split(",") if value]
    return int(count_text) if count_text.isdigit() else 0, values


def stable_id(*parts: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0
