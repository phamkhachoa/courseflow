from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
import csv
import io

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.event_backbone_smoke import CommandRunner, execute_step, resolve_compose_path, run_command, stable_id
from enterprise_dp.orchestrated_publication_smoke import (
    DEFAULT_RELEASE_ID as DEFAULT_PUBLICATION_RELEASE_ID,
    write_orchestrated_publication_smoke_report,
)
from enterprise_dp.quality_slo_ops import build_quality_slo_ops_report, write_quality_slo_ops_report
from enterprise_dp.trino_iceberg_minio_smoke import DEFAULT_POSTGRES_SERVICE, DEFAULT_SERVICE
from enterprise_dp.trino_sql_smoke import execute_trino_sql, wait_for_trino


DEFAULT_RELEASE_ID = "local-live-quality-slo-smoke"
DEFAULT_ORCHESTRATED_PUBLICATION_REPORT = (
    "build/orchestrated-publication-smoke/orchestrated-publication-smoke-report.json"
)
DEFAULT_DATA_PRODUCT = "gold.finance_benefit_reconciliation"
DEFAULT_FRESHNESS_SLO_SECONDS = 900

TrinoExecutor = Callable[[str, str], Any]


@dataclass(frozen=True)
class LiveQualitySloSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_live_quality_slo_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    output_dir: str | Path,
    orchestrated_publication_smoke_report_path: str | Path | None = None,
    compose_file: str | Path | None = None,
    trino_service: str = DEFAULT_SERVICE,
    iceberg_postgres_service: str = DEFAULT_POSTGRES_SERVICE,
    release_id: str = DEFAULT_RELEASE_ID,
    environment: str = "local",
    generated_at: str | None = None,
    data_product: str = DEFAULT_DATA_PRODUCT,
    freshness_slo_seconds: int = DEFAULT_FRESHNESS_SLO_SECONDS,
    command_runner: CommandRunner | None = None,
    command_timeout_seconds: int = 180,
    wait_attempts: int = 12,
    wait_interval_seconds: float = 2.0,
    start_runtime: bool = True,
    trino_executor_override: TrinoExecutor | None = None,
    orchestrated_publication_report_override: dict[str, Any] | None = None,
) -> LiveQualitySloSmokeResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or utc_now()
    compose_path = resolve_compose_path(platform_root, compose_file)
    runner = command_runner or run_command
    command_log: list[dict[str, Any]] = []
    failed_checks: list[dict[str, Any]] = []

    publication_path, publication_report = load_or_create_orchestrated_publication_report(
        platform_root,
        target_dir,
        orchestrated_publication_smoke_report_path=orchestrated_publication_smoke_report_path,
        orchestrated_publication_report_override=orchestrated_publication_report_override,
        environment=environment,
        generated_at=generated,
        command_timeout_seconds=command_timeout_seconds,
    )

    publication_ref = publication_report.get("publication") if isinstance(publication_report.get("publication"), dict) else {}
    gold_layer = publication_ref.get("layers", {}).get(data_product) if isinstance(publication_ref.get("layers"), dict) else {}
    if not isinstance(gold_layer, dict):
        gold_layer = {}
    gold_table = str(gold_layer.get("iceberg_table") or "")
    paths = quality_slo_paths(target_dir)
    release_evidence_path = resolve_artifact_path(platform_root, publication_ref.get("release"))
    catalog_bundle_path = resolve_artifact_path(platform_root, publication_ref.get("catalog_bundle"))

    try:
        if not gold_table:
            raise RuntimeError(f"Missing Iceberg table reference for {data_product}")
        if release_evidence_path is None or not release_evidence_path.is_file():
            raise RuntimeError("Missing release evidence from orchestrated publication report")
        if catalog_bundle_path is None or not catalog_bundle_path.is_file():
            raise RuntimeError("Missing catalog bundle from orchestrated publication report")
        if start_runtime and trino_executor_override is None:
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
                    iceberg_postgres_service,
                    trino_service,
                ],
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step="compose_up_live_quality_slo_runtime",
            )
            wait_for_trino(
                command_log,
                runner,
                compose_path=compose_path,
                service=trino_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                attempts=wait_attempts,
                interval_seconds=wait_interval_seconds,
            )

        def trino_executor(sql: str, step: str) -> Any:
            if trino_executor_override is not None:
                return trino_executor_override(sql, step)
            return execute_trino_sql(
                command_log,
                runner,
                compose_path=compose_path,
                service=trino_service,
                cwd=platform_root,
                timeout_seconds=command_timeout_seconds,
                step=step,
                sql=sql,
            )

        metrics = query_gold_quality_metrics(
            trino_executor,
            gold_table=gold_table,
            generated_at=generated,
            freshness_slo_seconds=freshness_slo_seconds,
        )
        quality_checks = evaluate_quality_checks(metrics)
        runtime_evidence = write_quality_runtime_evidence(
            paths["quality_runtime"],
            environment=environment,
            generated_at=generated,
            data_product=data_product,
            gold_table=gold_table,
            metrics=metrics,
            quality_checks=quality_checks,
        )
        alert_evidence = write_slo_alert_evidence(
            paths["alert"],
            environment=environment,
            generated_at=generated,
            data_product=data_product,
            runtime_evidence=runtime_evidence,
        )
        quality_ops = write_quality_slo_ops_report(
            platform_root,
            paths["quality_ops"],
            environment=environment,
            catalog_bundle_path=catalog_bundle_path,
            release_evidence_paths=[release_evidence_path],
            quality_runtime_evidence_path=paths["quality_runtime"],
            alert_evidence_path=paths["alert"],
            generated_at=generated,
        )
        negative_probes = write_negative_probes(
            platform_root,
            paths,
            environment=environment,
            generated_at=generated,
            data_product=data_product,
            gold_table=gold_table,
            catalog_bundle_path=catalog_bundle_path,
            release_evidence_path=release_evidence_path,
            metrics=metrics,
        )
    except Exception as exc:
        metrics = {}
        quality_checks = []
        runtime_evidence = {}
        alert_evidence = {}
        quality_ops = None
        negative_probes = {}
        failed_checks.append({"check": "live_quality_slo_runtime", "message": f"{type(exc).__name__}: {exc}"})

    failed_checks.extend(
        live_quality_failed_checks(
            publication_report=publication_report,
            metrics=metrics,
            quality_checks=quality_checks,
            runtime_evidence=runtime_evidence,
            alert_evidence=alert_evidence,
            quality_ops=quality_ops.report if quality_ops else {},
            negative_probes=negative_probes,
        )
    )
    report = build_live_quality_slo_report(
        root=platform_root,
        output_dir=target_dir,
        generated_at=generated,
        environment=environment,
        release_id=release_id,
        data_product=data_product,
        compose_path=compose_path,
        trino_service=trino_service,
        iceberg_postgres_service=iceberg_postgres_service,
        publication_path=publication_path,
        publication_report=publication_report,
        gold_table=gold_table,
        metrics=metrics,
        quality_checks=quality_checks,
        runtime_evidence=runtime_evidence,
        alert_evidence=alert_evidence,
        quality_ops=quality_ops.report if quality_ops else {},
        paths=paths,
        negative_probes=negative_probes,
        command_log=command_log,
        failed_checks=failed_checks,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return LiveQualitySloSmokeResult(output_path=target, report=report)


def load_or_create_orchestrated_publication_report(
    root: Path,
    output_dir: Path,
    *,
    orchestrated_publication_smoke_report_path: str | Path | None,
    orchestrated_publication_report_override: dict[str, Any] | None,
    environment: str,
    generated_at: str,
    command_timeout_seconds: int,
) -> tuple[Path | None, dict[str, Any]]:
    if orchestrated_publication_report_override is not None:
        return None, orchestrated_publication_report_override
    path_value = orchestrated_publication_smoke_report_path or DEFAULT_ORCHESTRATED_PUBLICATION_REPORT
    path = Path(path_value)
    if not path.is_absolute():
        path = root / path
    if path.is_file():
        return path, load_json(path)
    result = write_orchestrated_publication_smoke_report(
        root,
        output_dir / "orchestrated-publication-smoke-report.json",
        output_dir=output_dir / "orchestrated-publication-run",
        release_id=DEFAULT_PUBLICATION_RELEASE_ID,
        environment=environment,
        generated_at=generated_at,
        command_timeout_seconds=command_timeout_seconds,
    )
    return result.output_path, result.report


def query_gold_quality_metrics(
    trino_executor: TrinoExecutor,
    *,
    gold_table: str,
    generated_at: str,
    freshness_slo_seconds: int,
) -> dict[str, Any]:
    sql = f"""
SELECT
  COUNT(*) AS row_count,
  COUNT(DISTINCT reconciliation_id) AS distinct_reconciliation_id_count,
  COALESCE(SUM(CASE WHEN reconciliation_id IS NULL OR product_id IS NULL OR org_id IS NULL OR order_id IS NULL OR payment_id IS NULL THEN 1 ELSE 0 END), 0) AS required_null_count,
  COALESCE(SUM(CASE WHEN variance_amount_cents <> actual_amount_cents - expected_amount_cents THEN 1 ELSE 0 END), 0) AS variance_amount_mismatch_count,
  COALESCE(SUM(CASE WHEN variance_points <> actual_points - expected_points THEN 1 ELSE 0 END), 0) AS variance_points_mismatch_count,
  COALESCE(SUM(CASE WHEN quality_passed = false OR quality_passed IS NULL THEN 1 ELSE 0 END), 0) AS quality_failed_count,
  CAST(MAX(built_at) AS VARCHAR) AS max_built_at
FROM {gold_table}
""".strip()
    stdout = command_stdout(trino_executor(sql, "query_live_gold_quality_metrics"))
    row = parse_single_csv_row(stdout)
    row_count = int_value(row[0])
    distinct_count = int_value(row[1])
    max_built_at = row[6] if len(row) > 6 and row[6] else None
    age_seconds = freshness_age_seconds(generated_at, max_built_at)
    return {
        "row_count": row_count,
        "distinct_reconciliation_id_count": distinct_count,
        "duplicate_reconciliation_id_count": max(row_count - distinct_count, 0),
        "required_null_count": int_value(row[2]),
        "variance_amount_mismatch_count": int_value(row[3]),
        "variance_points_mismatch_count": int_value(row[4]),
        "quality_failed_count": int_value(row[5]),
        "max_built_at": max_built_at,
        "age_seconds": age_seconds,
        "slo_seconds": freshness_slo_seconds,
    }


def evaluate_quality_checks(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        check("row_count_positive", int_value(metrics.get("row_count")) > 0, {"row_count": metrics.get("row_count")}),
        check(
            "reconciliation_id_unique",
            int_value(metrics.get("duplicate_reconciliation_id_count")) == 0,
            {"duplicate_count": metrics.get("duplicate_reconciliation_id_count")},
        ),
        check(
            "required_fields_not_null",
            int_value(metrics.get("required_null_count")) == 0,
            {"required_null_count": metrics.get("required_null_count")},
        ),
        check(
            "variance_amount_invariant",
            int_value(metrics.get("variance_amount_mismatch_count")) == 0,
            {"mismatch_count": metrics.get("variance_amount_mismatch_count")},
        ),
        check(
            "variance_points_invariant",
            int_value(metrics.get("variance_points_mismatch_count")) == 0,
            {"mismatch_count": metrics.get("variance_points_mismatch_count")},
        ),
        check(
            "quality_passed_all_rows",
            int_value(metrics.get("quality_failed_count")) == 0,
            {"quality_failed_count": metrics.get("quality_failed_count")},
        ),
        check(
            "freshness_slo_green",
            isinstance(metrics.get("age_seconds"), int)
            and int_value(metrics.get("age_seconds")) <= int_value(metrics.get("slo_seconds")),
            {"age_seconds": metrics.get("age_seconds"), "slo_seconds": metrics.get("slo_seconds")},
        ),
    ]


def write_quality_runtime_evidence(
    path: Path,
    *,
    environment: str,
    generated_at: str,
    data_product: str,
    gold_table: str,
    metrics: dict[str, Any],
    quality_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed = [item for item in quality_checks if item.get("passed") is not True]
    freshness_breach = any(item["name"] == "freshness_slo_green" for item in failed)
    row = {
        "data_product": data_product,
        "runtime_table": gold_table,
        "quality_tool": "trino_sql_runtime_checks",
        "quality_profile_id": "p0-gold-finance-reconciliation",
        "validation_passed": not failed,
        "failed_check_count": len(failed),
        "freshness_status": "RED" if freshness_breach else "GREEN",
        "age_seconds": metrics.get("age_seconds"),
        "slo_seconds": metrics.get("slo_seconds"),
        "quarantine_row_count": 0,
        "row_count": metrics.get("row_count", 0),
        "checks": quality_checks,
    }
    evidence = {
        "artifact_type": "quality_runtime_evidence.v1",
        "report_version": 1,
        "evidence_id": stable_id("quality-runtime", environment, data_product, metrics),
        "environment": environment,
        "generated_at": generated_at,
        "quality_tool": "trino_sql_runtime_checks",
        "synthetic": False,
        "summary": {
            "data_product_count": 1,
            "failed_check_count": len(failed),
            "freshness_breach_count": 1 if freshness_breach else 0,
            "row_count": metrics.get("row_count", 0),
        },
        "data_products": [row],
        "passed": not failed,
    }
    write_json(path, evidence)
    return evidence


def write_slo_alert_evidence(
    path: Path,
    *,
    environment: str,
    generated_at: str,
    data_product: str,
    runtime_evidence: dict[str, Any],
) -> dict[str, Any]:
    runtime_summary = runtime_evidence.get("summary") if isinstance(runtime_evidence.get("summary"), dict) else {}
    failed_count = int_value(runtime_summary.get("failed_check_count"))
    freshness_breach_count = int_value(runtime_summary.get("freshness_breach_count"))
    green = failed_count == 0 and freshness_breach_count == 0
    evidence = {
        "artifact_type": "slo_alert_evidence.v1",
        "report_version": 1,
        "environment": environment,
        "generated_at": generated_at,
        "status": "green" if green else "red",
        "data_product": data_product,
        "summary": {
            "open_p0_incident_count": 0 if green else 1,
            "sla_breached_count": freshness_breach_count,
            "failed_quality_check_count": failed_count,
            "burn_rate_status": "green" if green else "red",
        },
        "alerts": [],
        "passed": green,
    }
    write_json(path, evidence)
    return evidence


def write_negative_probes(
    root: Path,
    paths: dict[str, Path],
    *,
    environment: str,
    generated_at: str,
    data_product: str,
    gold_table: str,
    catalog_bundle_path: Path,
    release_evidence_path: Path,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    corrupt_metrics = {**metrics, "required_null_count": int_value(metrics.get("required_null_count")) + 1}
    corrupt_checks = evaluate_quality_checks(corrupt_metrics)
    corrupt_runtime = write_quality_runtime_evidence(
        paths["negative_corrupt_runtime"],
        environment=environment,
        generated_at=generated_at,
        data_product=data_product,
        gold_table=gold_table,
        metrics=corrupt_metrics,
        quality_checks=corrupt_checks,
    )
    corrupt_alert = write_slo_alert_evidence(
        paths["negative_corrupt_alert"],
        environment=environment,
        generated_at=generated_at,
        data_product=data_product,
        runtime_evidence=corrupt_runtime,
    )
    corrupt_report = build_quality_slo_ops_report(
        root,
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        release_evidence_paths=[release_evidence_path],
        quality_runtime_evidence_path=paths["negative_corrupt_runtime"],
        alert_evidence_path=paths["negative_corrupt_alert"],
        generated_at=generated_at,
    )

    stale_metrics = {
        **metrics,
        "age_seconds": int_value(metrics.get("slo_seconds")) + 1,
    }
    stale_checks = evaluate_quality_checks(stale_metrics)
    stale_runtime = write_quality_runtime_evidence(
        paths["negative_stale_runtime"],
        environment=environment,
        generated_at=generated_at,
        data_product=data_product,
        gold_table=gold_table,
        metrics=stale_metrics,
        quality_checks=stale_checks,
    )
    stale_alert = write_slo_alert_evidence(
        paths["negative_stale_alert"],
        environment=environment,
        generated_at=generated_at,
        data_product=data_product,
        runtime_evidence=stale_runtime,
    )
    stale_report = build_quality_slo_ops_report(
        root,
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        release_evidence_paths=[release_evidence_path],
        quality_runtime_evidence_path=paths["negative_stale_runtime"],
        alert_evidence_path=paths["negative_stale_alert"],
        generated_at=generated_at,
    )

    red_alert = {
        "artifact_type": "slo_alert_evidence.v1",
        "report_version": 1,
        "environment": environment,
        "generated_at": generated_at,
        "status": "red",
        "data_product": data_product,
        "summary": {"open_p0_incident_count": 1, "sla_breached_count": 1, "burn_rate_status": "red"},
        "passed": False,
    }
    write_json(paths["negative_red_alert"], red_alert)
    red_alert_report = build_quality_slo_ops_report(
        root,
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        release_evidence_paths=[release_evidence_path],
        quality_runtime_evidence_path=paths["quality_runtime"],
        alert_evidence_path=paths["negative_red_alert"],
        generated_at=generated_at,
    )

    env_mismatch_runtime = {**load_json(paths["quality_runtime"]), "environment": "staging" if environment != "staging" else "prod"}
    write_json(paths["negative_env_runtime"], env_mismatch_runtime)
    env_mismatch_report = build_quality_slo_ops_report(
        root,
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        release_evidence_paths=[release_evidence_path],
        quality_runtime_evidence_path=paths["negative_env_runtime"],
        alert_evidence_path=paths["alert"],
        generated_at=generated_at,
    )

    missing_alert_report = build_quality_slo_ops_report(
        root,
        environment="prod",
        catalog_bundle_path=catalog_bundle_path,
        release_evidence_paths=[release_evidence_path],
        quality_runtime_evidence_path=paths["quality_runtime"],
        generated_at=generated_at,
    )

    return {
        "corrupt_gold_null_negative_test_passed": corrupt_report.get("passed") is False
        and contains_issue(corrupt_report, "runtime_quality_failed"),
        "stale_freshness_negative_test_passed": stale_report.get("passed") is False
        and contains_issue(stale_report, "runtime_freshness_breach"),
        "red_alert_negative_test_passed": red_alert_report.get("passed") is False
        and failed_global_check(red_alert_report, "alert_state_green"),
        "environment_mismatch_negative_test_passed": env_mismatch_report.get("passed") is False
        and failed_global_check(env_mismatch_report, "quality_runtime_environment_matches"),
        "missing_alert_production_like_negative_test_passed": missing_alert_report.get("passed") is False
        and failed_global_check(missing_alert_report, "alert_evidence_attached_for_production_like"),
    }


def live_quality_failed_checks(
    *,
    publication_report: dict[str, Any],
    metrics: dict[str, Any],
    quality_checks: list[dict[str, Any]],
    runtime_evidence: dict[str, Any],
    alert_evidence: dict[str, Any],
    quality_ops: dict[str, Any],
    negative_probes: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if publication_report.get("passed") is not True:
        failed.append({"check": "orchestrated_publication_passed", "passed": publication_report.get("passed")})
    if int_value(metrics.get("row_count")) <= 0:
        failed.append({"check": "live_gold_row_count_positive", "row_count": metrics.get("row_count")})
    failed_quality = [item for item in quality_checks if item.get("passed") is not True]
    if failed_quality:
        failed.append({"check": "live_gold_quality_checks_passed", "failed_quality_checks": failed_quality})
    if runtime_evidence.get("passed") is not True:
        failed.append({"check": "quality_runtime_evidence_passed", "summary": runtime_evidence.get("summary")})
    if alert_evidence.get("passed") is not True:
        failed.append({"check": "slo_alert_evidence_green", "summary": alert_evidence.get("summary")})
    if quality_ops.get("passed") is not True:
        failed.append({"check": "quality_slo_ops_passed", "summary": quality_ops.get("summary")})
    for key, value in sorted(negative_probes.items()):
        if value is not True:
            failed.append({"check": key, "passed": value})
    return failed


def build_live_quality_slo_report(
    *,
    root: Path,
    output_dir: Path,
    generated_at: str,
    environment: str,
    release_id: str,
    data_product: str,
    compose_path: Path,
    trino_service: str,
    iceberg_postgres_service: str,
    publication_path: Path | None,
    publication_report: dict[str, Any],
    gold_table: str,
    metrics: dict[str, Any],
    quality_checks: list[dict[str, Any]],
    runtime_evidence: dict[str, Any],
    alert_evidence: dict[str, Any],
    quality_ops: dict[str, Any],
    paths: dict[str, Path],
    negative_probes: dict[str, Any],
    command_log: list[dict[str, Any]],
    failed_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    quality_summary = runtime_evidence.get("summary") if isinstance(runtime_evidence.get("summary"), dict) else {}
    ops_summary = quality_ops.get("summary") if isinstance(quality_ops.get("summary"), dict) else {}
    summary = {
        "target_data_product": data_product,
        "gold_table": gold_table,
        "gold_row_count": metrics.get("row_count", 0),
        "quality_runtime_passed": runtime_evidence.get("passed"),
        "quality_runtime_failed_check_count": quality_summary.get("failed_check_count", 0),
        "freshness_breach_count": quality_summary.get("freshness_breach_count", 0),
        "slo_alert_passed": alert_evidence.get("passed"),
        "quality_slo_ops_passed": quality_ops.get("passed"),
        "quality_slo_ops_failed_product_count": ops_summary.get("failed_product_count", 0),
        "quality_slo_ops_global_failed_check_count": ops_summary.get("global_failed_check_count", 0),
        **negative_probes,
        "failed_check_count": len(failed_checks),
        "failed_checks": failed_checks,
    }
    return {
        "artifact_type": "live_quality_slo_smoke_report.v1",
        "report_version": 1,
        "capability_ids": ["quality-slo-release-gates"],
        "report_id": stable_id("live-quality-slo-smoke", environment, release_id, data_product),
        "generated_at": generated_at,
        "environment": environment,
        "release_id": release_id,
        "data_product": data_product,
        "runtime_scope": {
            "mode": "local_trino_iceberg_quality_slo_gate",
            "covered": [
                "gold_iceberg_table_queried_through_trino",
                "runtime_quality_checks_from_live_gold",
                "quality_runtime_evidence_generated",
                "slo_alert_evidence_generated",
                "quality_slo_release_gates_ops_report_generated",
                "corrupt_gold_negative_control",
                "stale_freshness_negative_control",
                "red_alert_negative_control",
                "environment_mismatch_negative_control",
                "missing_alert_production_like_negative_control",
            ],
            "not_covered": [
                "managed_great_expectations_or_soda_runner",
                "production_alertmanager_or_pagerduty_route",
                "multi_product_runtime_quality_rollout",
                "production_slo_burn_rate_monitoring",
            ],
        },
        "runtime": {
            "compose_file": compose_path.as_posix(),
            "trino_service": trino_service,
            "iceberg_postgres_service": iceberg_postgres_service,
            "root": root.as_posix(),
            "output_dir": output_dir.as_posix(),
        },
        "orchestrated_publication": {
            "path": publication_path.as_posix() if publication_path else None,
            "hash": hash_file(publication_path) if publication_path and publication_path.is_file() else None,
            "passed": publication_report.get("passed"),
        },
        "artifacts": {
            "quality_runtime_evidence": artifact_ref(paths["quality_runtime"], runtime_evidence),
            "slo_alert_evidence": artifact_ref(paths["alert"], alert_evidence),
            "quality_slo_ops": artifact_ref(paths["quality_ops"], quality_ops),
        },
        "metrics": metrics,
        "quality_checks": quality_checks,
        "negative_probes": negative_probes,
        "commands": command_log,
        "summary": summary,
        "passed": not failed_checks,
    }


def quality_slo_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "quality_runtime": output_dir / "quality" / "quality-runtime-evidence.json",
        "alert": output_dir / "quality" / "slo-alert-evidence.json",
        "quality_ops": output_dir / "quality" / "quality-slo-ops.json",
        "negative_corrupt_runtime": output_dir / "negative" / "corrupt-quality-runtime-evidence.json",
        "negative_corrupt_alert": output_dir / "negative" / "corrupt-slo-alert-evidence.json",
        "negative_stale_runtime": output_dir / "negative" / "stale-quality-runtime-evidence.json",
        "negative_stale_alert": output_dir / "negative" / "stale-slo-alert-evidence.json",
        "negative_red_alert": output_dir / "negative" / "red-slo-alert-evidence.json",
        "negative_env_runtime": output_dir / "negative" / "env-mismatch-quality-runtime-evidence.json",
    }


def resolve_artifact_path(root: Path, ref: Any) -> Path | None:
    if not isinstance(ref, dict) or not isinstance(ref.get("uri"), str):
        return None
    path = Path(ref["uri"])
    return path if path.is_absolute() else root / path


def artifact_ref(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "uri": path.as_posix(),
        "hash": hash_file(path) if path.is_file() else None,
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "environment": payload.get("environment"),
        "passed": payload.get("passed"),
        "readiness_state": payload.get("readiness_state"),
    }


def failed_global_check(report: dict[str, Any], name: str) -> bool:
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    return any(isinstance(item, dict) and item.get("name") == name and item.get("passed") is not True for item in checks)


def contains_issue(report: dict[str, Any], issue: str) -> bool:
    rows = report.get("data_products") if isinstance(report.get("data_products"), list) else []
    return any(isinstance(row, dict) and issue in row.get("issues", []) for row in rows)


def command_stdout(result: Any) -> str:
    return result.stdout if hasattr(result, "stdout") else str(result or "")


def parse_single_csv_row(stdout: str) -> list[str]:
    for row in csv.reader(io.StringIO(stdout)):
        if row:
            return [cell.strip() for cell in row]
    return []


def freshness_age_seconds(generated_at: str, max_built_at: str | None) -> int | None:
    if not max_built_at:
        return None
    generated = parse_timestamp(generated_at)
    built = parse_timestamp(max_built_at)
    if generated is None or built is None:
        return None
    return max(int((generated - built).total_seconds()), 0)


def parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def int_value(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip().strip('"')
        if stripped.startswith("-") and stripped[1:].isdigit():
            return int(stripped)
        if stripped.isdigit():
            return int(stripped)
    return 0


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{canonical_json(payload)}\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
