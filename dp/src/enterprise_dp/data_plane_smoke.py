from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.orchestration import UseCaseRunResult, run_use_case


DEFAULT_USE_CASE_ID = "finance-benefit-reconciliation"
DEFAULT_RELEASE_ID = "local-data-plane-smoke"
DEFAULT_INPUTS = {
    "finance-benefit-reconciliation": Path("samples/finance/benefit_settled.jsonl"),
    "ml-feature-governance": Path("samples/recommendation/tracking.jsonl"),
}


@dataclass(frozen=True)
class DataPlaneSmokeResult:
    output_path: Path
    report: dict[str, Any]


def write_data_plane_smoke_report(
    root: str | Path,
    output_path: str | Path,
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path,
    use_case_id: str = DEFAULT_USE_CASE_ID,
    release_id: str = DEFAULT_RELEASE_ID,
    runner_id: str | None = None,
    topic: str | None = None,
    primary_output: str | None = None,
    environment: str = "local",
    generated_at: str | None = None,
    ingested_at: str | None = None,
    built_at: str | None = None,
    evaluation_time: str | None = None,
    schema_id: str | None = None,
    snapshot_id: str | None = None,
) -> DataPlaneSmokeResult:
    platform_root = Path(root)
    source_path = _resolve_input_path(platform_root, use_case_id, input_path)
    target_dir = Path(output_dir)
    generated = generated_at or evaluation_time or built_at or ingested_at or _utc_now()

    run_result = run_use_case(
        platform_root,
        source_path,
        target_dir,
        use_case_id=use_case_id,
        release_id=release_id,
        runner_id=runner_id,
        topic=topic,
        primary_output=primary_output,
        environment=environment,
        ingested_at=ingested_at,
        built_at=built_at,
        evaluation_time=evaluation_time or generated,
        schema_id=schema_id,
        snapshot_id=snapshot_id,
    )

    report = build_data_plane_smoke_report(
        platform_root,
        run_result,
        source_path=source_path,
        output_dir=target_dir,
        generated_at=generated,
        environment=environment,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return DataPlaneSmokeResult(output_path=target, report=report)


def build_data_plane_smoke_report(
    root: str | Path,
    run_result: UseCaseRunResult,
    *,
    source_path: str | Path,
    output_dir: str | Path,
    generated_at: str,
    environment: str,
) -> dict[str, Any]:
    platform_root = Path(root)
    source = Path(source_path)
    target_dir = Path(output_dir)
    layer_reports = _layer_reports(platform_root, run_result)
    primary_layer = next(
        (layer for layer in layer_reports if layer["name"] == run_result.primary_output),
        layer_reports[-1] if layer_reports else None,
    )
    primary_rows = _read_jsonl(primary_layer["path"]) if primary_layer and primary_layer["exists"] else []
    query_smoke = _build_query_smoke(primary_rows, primary_output=run_result.primary_output)
    artifact_refs = _artifact_refs(run_result)
    failed_checks = _failed_checks(run_result, layer_reports, query_smoke)
    release_gates = {
        str(gate["gate_id"]): bool(gate["passed"])
        for gate in run_result.evidence.get("gates", [])
        if isinstance(gate, dict)
    }
    report = {
        "artifact_type": "data_plane_smoke_report.v1",
        "report_version": 1,
        "capability_id": "local-data-plane-runtime-smoke",
        "report_id": f"data-plane-smoke:{environment}:{run_result.use_case_id}:{run_result.release_id}",
        "generated_at": generated_at,
        "environment": environment,
        "release_id": run_result.release_id,
        "use_case_id": run_result.use_case_id,
        "runner_id": run_result.runner_id,
        "topic": run_result.topic,
        "primary_output": run_result.primary_output,
        "runtime_scope": {
            "mode": "local_ci_jsonl_medallion",
            "covered": [
                "contract_checked_source_events",
                "bronze_approved_quarantine_outputs",
                "silver_gold_pipeline_outputs",
                "catalog_lineage_bundle",
                "release_gate_evidence",
                "gold_query_smoke",
            ],
            "not_covered": [
                "live_kafka_redpanda_broker_flow",
                "iceberg_table_commit",
                "trino_or_dremio_sql_runtime_query",
                "dagster_or_airflow_run_history",
            ],
        },
        "input": {
            "path": source.as_posix(),
            "content_hash": hash_file(source),
            "row_count": _count_jsonl(source),
        },
        "output_dir": target_dir.as_posix(),
        "layers": layer_reports,
        "artifacts": artifact_refs,
        "release_gates": release_gates,
        "query_smoke": query_smoke,
        "summary": {
            "layer_count": len(layer_reports),
            "artifact_count": len(artifact_refs),
            "release_passed": bool(run_result.evidence.get("release_passed")),
            "all_layers_materialized": all(layer["passed"] for layer in layer_reports),
            "query_passed": bool(query_smoke["passed"]),
            "failed_check_count": len(failed_checks),
            "failed_checks": failed_checks,
        },
    }
    report["passed"] = (
        bool(run_result.evidence.get("release_passed"))
        and all(layer["passed"] for layer in layer_reports)
        and bool(query_smoke["passed"])
        and not failed_checks
    )
    return report


def _resolve_input_path(root: Path, use_case_id: str, input_path: str | Path | None) -> Path:
    if input_path is not None:
        source = Path(input_path)
        if source.is_absolute() or source.exists():
            return source
        return root / source
    default_input = DEFAULT_INPUTS.get(use_case_id)
    if default_input is None:
        raise ValueError(f"input_path is required for use case {use_case_id!r}")
    return root / default_input


def _layer_reports(root: Path, run_result: UseCaseRunResult) -> list[dict[str, Any]]:
    pipeline_output_dir = run_result.pipeline.manifest_path.parent.parent
    reports: list[dict[str, Any]] = []
    for layer_name, layer in run_result.pipeline.manifest.get("layers", {}).items():
        if not isinstance(layer, dict):
            continue
        path = _resolve_artifact_path(
            str(layer.get("path", "")),
            root=root,
            pipeline_output_dir=pipeline_output_dir,
        )
        exists = path.is_file()
        actual_rows = _count_jsonl(path) if exists else None
        actual_hash = hash_file(path) if exists else None
        manifest_rows = layer.get("row_count")
        manifest_hash = layer.get("content_hash")
        quality_passed = layer.get("quality_passed") is True
        report = {
            "name": layer_name,
            "path": path.as_posix(),
            "exists": exists,
            "manifest_row_count": manifest_rows,
            "actual_row_count": actual_rows,
            "row_count_matches": exists and manifest_rows == actual_rows,
            "manifest_hash": manifest_hash,
            "actual_hash": actual_hash,
            "hash_matches": exists and manifest_hash == actual_hash,
            "quality_passed": quality_passed,
            "quality_errors": layer.get("quality_errors", []),
        }
        report["passed"] = (
            exists
            and isinstance(actual_rows, int)
            and actual_rows > 0
            and report["row_count_matches"]
            and report["hash_matches"]
            and quality_passed
        )
        reports.append(report)
    return reports


def _resolve_artifact_path(value: str, *, root: Path, pipeline_output_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [
        path,
        root / path,
        pipeline_output_dir / path,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def _artifact_refs(run_result: UseCaseRunResult) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for name, path in (
        ("ingestion_manifest", run_result.ingestion.manifest_path if run_result.ingestion else None),
        ("pipeline_manifest", run_result.pipeline.manifest_path),
        ("catalog_bundle", run_result.catalog_bundle_path),
        ("release_evidence", run_result.evidence_path),
    ):
        if path is None:
            continue
        refs.append(_artifact_ref(name, Path(path)))
    return refs


def _artifact_ref(name: str, path: Path) -> dict[str, Any]:
    exists = path.is_file()
    return {
        "name": name,
        "path": path.as_posix(),
        "exists": exists,
        "content_hash": hash_file(path) if exists else None,
    }


def _failed_checks(
    run_result: UseCaseRunResult,
    layer_reports: list[dict[str, Any]],
    query_smoke: dict[str, Any],
) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    if not run_result.evidence.get("release_passed"):
        failed_gates = [
            gate.get("gate_id")
            for gate in run_result.evidence.get("gates", [])
            if isinstance(gate, dict) and gate.get("passed") is not True
        ]
        failed.append({"check": "release_gates", "failed_gates": failed_gates})
    for layer in layer_reports:
        if not layer["passed"]:
            failed.append(
                {
                    "check": "layer_materialization",
                    "layer": layer["name"],
                    "exists": layer["exists"],
                    "row_count_matches": layer["row_count_matches"],
                    "hash_matches": layer["hash_matches"],
                    "quality_passed": layer["quality_passed"],
                }
            )
    if not query_smoke["passed"]:
        failed.append({"check": "gold_query_smoke", "reason": query_smoke.get("reason")})
    return failed


def _build_query_smoke(rows: list[dict[str, Any]], *, primary_output: str) -> dict[str, Any]:
    if not rows:
        return {
            "passed": False,
            "reason": "primary output has no queryable rows",
            "row_count": 0,
        }
    if "gold.finance_benefit_reconciliation" == primary_output:
        return _finance_query_smoke(rows)
    if "gold.recsys_interactions" == primary_output:
        return _recommendation_query_smoke(rows)
    return _generic_query_smoke(rows, primary_output=primary_output)


def _finance_query_smoke(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, dict[str, Any]] = {}
    for row in rows:
        status = str(row.get("reconciliation_status") or "UNKNOWN")
        bucket = by_status.setdefault(
            status,
            {
                "reconciliation_status": status,
                "row_count": 0,
                "expected_amount_cents": 0,
                "actual_amount_cents": 0,
                "reconciliation_delta_cents": 0,
                "variance_points": 0,
            },
        )
        bucket["row_count"] += 1
        for field in (
            "expected_amount_cents",
            "actual_amount_cents",
            "reconciliation_delta_cents",
            "variance_points",
        ):
            bucket[field] += _number(row.get(field))
    result_rows = sorted(by_status.values(), key=lambda item: item["reconciliation_status"])
    return {
        "passed": bool(result_rows),
        "query_name": "finance_reconciliation_by_status",
        "row_count": len(rows),
        "result_row_count": len(result_rows),
        "result": result_rows,
    }


def _recommendation_query_smoke(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("course_id")), str(row.get("related_course_id")))
        bucket = by_pair.setdefault(
            key,
            {
                "course_id": key[0],
                "related_course_id": key[1],
                "interaction_count": 0,
                "interaction_weight": 0.0,
            },
        )
        bucket["interaction_count"] += 1
        bucket["interaction_weight"] += float(_number(row.get("event_weight")))
    result_rows = sorted(
        by_pair.values(),
        key=lambda item: (-item["interaction_weight"], item["course_id"], item["related_course_id"]),
    )
    return {
        "passed": bool(result_rows),
        "query_name": "recommendation_related_course_scores",
        "row_count": len(rows),
        "result_row_count": len(result_rows),
        "result": result_rows,
    }


def _generic_query_smoke(rows: list[dict[str, Any]], *, primary_output: str) -> dict[str, Any]:
    columns = sorted({key for row in rows for key in row})
    numeric_sums: dict[str, int | float] = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        if values and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values if value is not None):
            numeric_sums[column] = sum(_number(value) for value in values)
    return {
        "passed": True,
        "query_name": "generic_primary_output_profile",
        "primary_output": primary_output,
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": columns,
        "numeric_sums": numeric_sums,
    }


def _count_jsonl(path: str | Path) -> int:
    return len(_read_jsonl(path))


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{line_number}: JSONL record must be an object")
            records.append(record)
    return records


def _number(value: Any) -> int | float:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, (int, float)):
        return value
    return 0


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
