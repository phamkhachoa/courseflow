from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import hash_file, load_json
from enterprise_dp.contracts import load_yaml


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
PASSING_MAINTENANCE_STATUSES = {"passed", "not_required", "not_due"}
VALID_SOURCE_KINDS = {"ci_tool_output", "external_attestation", "synthetic_fixture"}


@dataclass(frozen=True)
class BronzeLakehouseOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_bronze_lakehouse_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    offset_ledger_paths: list[str | Path] | None = None,
    maintenance_evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> BronzeLakehouseOpsReportResult:
    report = build_bronze_lakehouse_ops_report(
        root,
        environment=environment,
        offset_ledger_paths=offset_ledger_paths,
        maintenance_evidence_path=maintenance_evidence_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return BronzeLakehouseOpsReportResult(output_path=target, report=report)


def build_bronze_lakehouse_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    offset_ledger_paths: list[str | Path] | None = None,
    maintenance_evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    sources = load_source_registry(platform_root)
    ledger_refs, ledger_index = load_offset_ledgers(offset_ledger_paths or [])
    maintenance_path = Path(maintenance_evidence_path) if maintenance_evidence_path else None
    maintenance = load_json(maintenance_path) if maintenance_path else None
    maintenance_index = maintenance_table_index(maintenance)
    global_checks = bronze_lakehouse_global_checks(
        maintenance,
        environment=environment,
        generated_at=generated,
    )
    table_rows = [
        bronze_lakehouse_table_row(
            source,
            ledger_index.get(str(source.get("sourceId") or "")),
            maintenance_index.get(bronze_target(source)),
            environment=environment,
        )
        for source in sorted(sources, key=lambda item: str(item.get("sourceId") or ""))
    ]
    failed_global = [check for check in global_checks if check.get("passed") is not True]
    p0_failed_tables = [
        row
        for row in table_rows
        if row.get("priority") == "P0" and row.get("passed") is not True
    ]
    warning_tables = [
        row
        for row in table_rows
        if row.get("priority") != "P0" and row.get("passed") is not True
    ]
    passed = not failed_global and not p0_failed_tables
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    return {
        "artifact_type": "bronze_lakehouse_ops_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "bronze-lakehouse-ops",
            environment,
            generated,
            ledger_refs,
            evidence_ref(maintenance_path, maintenance),
        ),
        "generated_at": generated,
        "environment": environment,
        "capability_id": "bronze-lakehouse-evidence",
        "readiness_state": readiness_state,
        "mode": "local_preflight" if environment == "local" and not offset_ledger_paths else "runtime_evidence",
        "inputs": {
            "offset_ledgers": ledger_refs,
            "maintenance_evidence": evidence_ref(maintenance_path, maintenance),
        },
        "checks": global_checks,
        "tables": table_rows,
        "decision_board": {
            "p0_failed_tables": [compact_table_row(row) for row in p0_failed_tables[:30]],
            "warning_tables": [compact_table_row(row) for row in warning_tables[:30]],
            "page_now": [
                action
                for row in p0_failed_tables
                for action in row.get("next_actions", [])
                if action.get("priority") == "P0"
            ][:30],
        },
        "summary": bronze_lakehouse_summary(table_rows, failed_global, p0_failed_tables, warning_tables),
        "passed": passed,
    }


def bronze_lakehouse_global_checks(
    maintenance: dict[str, Any] | None,
    *,
    environment: str,
    generated_at: str,
) -> list[dict[str, Any]]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    generated = parse_timestamp(generated_at)
    valid_until = parse_timestamp(maintenance.get("valid_until")) if isinstance(maintenance, dict) else None
    source_kind = maintenance.get("source_kind") if isinstance(maintenance, dict) else None
    return [
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check(
            "maintenance_evidence_attached_for_production_like",
            not production_like or maintenance is not None,
            {"environment": environment, "attached": maintenance is not None},
        ),
        check(
            "maintenance_artifact_type_valid",
            maintenance is None or maintenance.get("artifact_type") == "bronze_lakehouse_maintenance_evidence.v1",
            {"artifact_type": maintenance.get("artifact_type") if isinstance(maintenance, dict) else None},
        ),
        check(
            "maintenance_environment_matches",
            maintenance is None or maintenance.get("environment") == environment,
            {"expected": environment, "actual": maintenance.get("environment") if isinstance(maintenance, dict) else None},
        ),
        check(
            "maintenance_source_kind_valid",
            maintenance is None or maintenance.get("source_kind") in VALID_SOURCE_KINDS,
            {"source_kind": source_kind},
        ),
        check(
            "production_maintenance_not_synthetic",
            not production_like or (isinstance(source_kind, str) and source_kind in {"ci_tool_output", "external_attestation"}),
            {"source_kind": source_kind},
        ),
        check(
            "production_maintenance_not_expired",
            not production_like or (generated is not None and valid_until is not None and valid_until >= generated),
            {
                "generated_at": generated_at,
                "valid_until": maintenance.get("valid_until") if isinstance(maintenance, dict) else None,
            },
        ),
    ]


def bronze_lakehouse_table_row(
    source: dict[str, Any],
    ledger_ref: dict[str, Any] | None,
    maintenance_row: dict[str, Any] | None,
    *,
    environment: str,
) -> dict[str, Any]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    source_id = str(source.get("sourceId") or "")
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    target = canonical.get("bronzeTarget")
    ledger = ledger_ref.get("ledger") if isinstance(ledger_ref, dict) else None
    ledger_target = ledger.get("target") if isinstance(ledger, dict) and isinstance(ledger.get("target"), dict) else {}
    ledger_counts = ledger.get("counts") if isinstance(ledger, dict) and isinstance(ledger.get("counts"), dict) else {}
    checks = [
        check("bronze_target_declared", non_empty(target), {"bronze_target": target}),
        check(
            "offset_ledger_attached",
            not production_like or isinstance(ledger, dict),
            {"source_id": source_id, "attached": isinstance(ledger, dict)},
        ),
        check(
            "offset_ledger_artifact_type_valid",
            ledger is None or ledger.get("artifact_type") == "source_offset_ledger.v1",
            {"artifact_type": ledger.get("artifact_type") if isinstance(ledger, dict) else None},
        ),
        check(
            "offset_ledger_environment_matches",
            ledger is None or ledger.get("environment") == environment,
            {"expected": environment, "actual": ledger.get("environment") if isinstance(ledger, dict) else None},
        ),
        check(
            "offset_ledger_source_matches",
            ledger is None or ledger.get("source_id") == source_id,
            {"expected": source_id, "actual": ledger.get("source_id") if isinstance(ledger, dict) else None},
        ),
        check(
            "offset_ledger_passed",
            ledger is None or ledger.get("passed") is True,
            {"passed": ledger.get("passed") if isinstance(ledger, dict) else None},
        ),
        check(
            "ledger_target_table_matches_source",
            ledger is None or ledger_target.get("target_table") == target,
            {"target_table": ledger_target.get("target_table"), "bronze_target": target},
        ),
        check(
            "ledger_table_format_iceberg",
            ledger is None or ledger_target.get("table_format") == "iceberg",
            {"table_format": ledger_target.get("table_format")},
        ),
        check(
            "ledger_commit_status_committed",
            ledger is None or ledger_target.get("commit_status") == "committed",
            {"commit_status": ledger_target.get("commit_status")},
        ),
        check(
            "ledger_quarantine_empty",
            ledger is None or ledger_counts.get("quarantined_record_count") == 0,
            {"quarantined_record_count": ledger_counts.get("quarantined_record_count")},
        ),
        check(
            "replay_proof_attached",
            ledger is None or not production_like or isinstance(ledger.get("replay"), dict),
            {"replay": ledger.get("replay") if isinstance(ledger, dict) else None},
        ),
        check(
            "iceberg_snapshot_metadata_present",
            ledger is None
            or not production_like
            or (
                non_empty(ledger_target.get("target_snapshot_id"))
                and non_empty(ledger_target.get("table_metadata_uri"))
                and is_hash(ledger_target.get("table_metadata_hash"))
            ),
            {
                "target_snapshot_id": ledger_target.get("target_snapshot_id"),
                "table_metadata_uri": ledger_target.get("table_metadata_uri"),
                "table_metadata_hash": ledger_target.get("table_metadata_hash"),
            },
        ),
        check(
            "maintenance_row_attached",
            not production_like or isinstance(maintenance_row, dict),
            {"table": target, "attached": isinstance(maintenance_row, dict)},
        ),
        check(
            "append_only_enforced",
            maintenance_row is None or maintenance_row.get("append_only_enforced") is True,
            {"append_only_enforced": maintenance_row.get("append_only_enforced") if isinstance(maintenance_row, dict) else None},
        ),
        check(
            "compaction_status_passing",
            maintenance_row is None or maintenance_status(maintenance_row, "compaction") in PASSING_MAINTENANCE_STATUSES,
            {"compaction_status": maintenance_status(maintenance_row, "compaction")},
        ),
        check(
            "snapshot_retention_status_passing",
            maintenance_row is None or maintenance_status(maintenance_row, "snapshot_retention") in PASSING_MAINTENANCE_STATUSES,
            {"snapshot_retention_status": maintenance_status(maintenance_row, "snapshot_retention")},
        ),
        check(
            "orphan_cleanup_status_passing",
            maintenance_row is None or maintenance_status(maintenance_row, "orphan_cleanup") in PASSING_MAINTENANCE_STATUSES,
            {"orphan_cleanup_status": maintenance_status(maintenance_row, "orphan_cleanup")},
        ),
        check(
            "iceberg_table_properties_ready",
            maintenance_row is None or table_properties_ready(maintenance_row),
            {"table_properties": maintenance_row.get("table_properties") if isinstance(maintenance_row, dict) else None},
        ),
    ]
    issues = table_issues(checks)
    return {
        "source_id": source_id,
        "priority": source.get("priority") or "P2",
        "product": source.get("product"),
        "domain": source.get("domain"),
        "source_status": source.get("status"),
        "topic": canonical.get("topic"),
        "bronze_target": target,
        "environment": environment,
        "offset_ledger": ledger_ref_summary(ledger_ref),
        "maintenance": maintenance_summary(maintenance_row),
        "checks": checks,
        "issues": issues,
        "risk_state": issues[0] if issues else "ok",
        "next_actions": next_actions(issues, source),
        "passed": not issues,
    }


def table_issues(checks: list[dict[str, Any]]) -> list[str]:
    issue_map = {
        "bronze_target_declared": "bronze_target_missing",
        "offset_ledger_attached": "offset_ledger_missing",
        "offset_ledger_artifact_type_valid": "offset_ledger_invalid",
        "offset_ledger_environment_matches": "offset_ledger_environment_mismatch",
        "offset_ledger_source_matches": "offset_ledger_source_mismatch",
        "offset_ledger_passed": "offset_ledger_failed",
        "ledger_target_table_matches_source": "ledger_target_mismatch",
        "ledger_table_format_iceberg": "table_format_not_iceberg",
        "ledger_commit_status_committed": "commit_not_committed",
        "ledger_quarantine_empty": "quarantine_not_empty",
        "replay_proof_attached": "replay_proof_missing",
        "iceberg_snapshot_metadata_present": "iceberg_snapshot_metadata_missing",
        "maintenance_row_attached": "maintenance_evidence_missing",
        "append_only_enforced": "append_only_not_enforced",
        "compaction_status_passing": "compaction_not_passing",
        "snapshot_retention_status_passing": "snapshot_retention_not_passing",
        "orphan_cleanup_status_passing": "orphan_cleanup_not_passing",
        "iceberg_table_properties_ready": "iceberg_properties_not_ready",
    }
    return [
        issue_map[check["name"]]
        for check in checks
        if check.get("passed") is not True and check.get("name") in issue_map
    ]


def next_actions(issues: list[str], source: dict[str, Any]) -> list[dict[str, Any]]:
    owner = source.get("product") or "data-platform-team"
    actions: list[dict[str, Any]] = []
    if any(issue.startswith("offset_ledger") or issue.startswith("ledger") for issue in issues):
        actions.append({"priority": "P0", "action": "attach_valid_source_offset_ledger", "owner": "data-platform-team"})
    if "replay_proof_missing" in issues:
        actions.append({"priority": "P0", "action": "attach_replay_proof", "owner": owner})
    if "iceberg_snapshot_metadata_missing" in issues or "table_format_not_iceberg" in issues or "commit_not_committed" in issues:
        actions.append({"priority": "P0", "action": "repair_iceberg_commit_evidence", "owner": "data-platform-team"})
    if any(issue.endswith("not_passing") or issue == "maintenance_evidence_missing" for issue in issues):
        actions.append({"priority": "P0", "action": "run_bronze_table_maintenance_evidence", "owner": "data-platform-team"})
    if "append_only_not_enforced" in issues or "iceberg_properties_not_ready" in issues:
        actions.append({"priority": "P0", "action": "enforce_bronze_table_properties", "owner": "data-platform-team"})
    return actions or [{"priority": "P3", "action": "no_action", "owner": owner}]


def bronze_lakehouse_summary(
    rows: list[dict[str, Any]],
    failed_global_checks: list[dict[str, Any]],
    p0_failed_tables: list[dict[str, Any]],
    warning_tables: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source_count": len(rows),
        "p0_source_count": sum(1 for row in rows if row.get("priority") == "P0"),
        "ledger_attached_count": sum(1 for row in rows if row.get("offset_ledger", {}).get("attached") is True),
        "maintenance_attached_count": sum(1 for row in rows if row.get("maintenance", {}).get("attached") is True),
        "p0_failed_table_count": len(p0_failed_tables),
        "warning_table_count": len(warning_tables),
        "global_failed_check_count": len(failed_global_checks),
        "by_priority": count_by(rows, "priority"),
        "by_risk_state": count_by(rows, "risk_state"),
    }


def load_offset_ledgers(paths: list[str | Path]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    refs = []
    index: dict[str, dict[str, Any]] = {}
    for value in paths:
        path = Path(value)
        ledger = load_json(path)
        source_id = ledger.get("source_id")
        ref = {
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "artifact_type": ledger.get("artifact_type"),
            "ledger_id": ledger.get("ledger_id"),
            "source_id": source_id,
            "environment": ledger.get("environment"),
            "passed": ledger.get("passed"),
            "target_table": ledger.get("target", {}).get("target_table") if isinstance(ledger.get("target"), dict) else None,
            "ledger": ledger,
        }
        refs.append({key: value for key, value in ref.items() if key != "ledger"})
        if isinstance(source_id, str) and source_id:
            index[source_id] = ref
    return refs, index


def load_source_registry(root: Path) -> list[dict[str, Any]]:
    registry = load_yaml(root / "platform" / "ingestion" / "source-registry.yaml")
    sources = registry.get("sources")
    return [source for source in sources if isinstance(source, dict)] if isinstance(sources, list) else []


def maintenance_table_index(maintenance: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(maintenance, dict) or not isinstance(maintenance.get("tables"), list):
        return {}
    return {
        str(row.get("table")): row
        for row in maintenance["tables"]
        if isinstance(row, dict) and isinstance(row.get("table"), str)
    }


def evidence_ref(path: Path | None, evidence: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "attached": path is not None,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path and path.is_file() else None,
        "artifact_type": evidence.get("artifact_type") if isinstance(evidence, dict) else None,
        "generated_at": evidence.get("generated_at") if isinstance(evidence, dict) else None,
        "valid_until": evidence.get("valid_until") if isinstance(evidence, dict) else None,
        "environment": evidence.get("environment") if isinstance(evidence, dict) else None,
        "source_kind": evidence.get("source_kind") if isinstance(evidence, dict) else None,
    }


def bronze_target(source: dict[str, Any]) -> str:
    canonical = source.get("canonical") if isinstance(source.get("canonical"), dict) else {}
    return str(canonical.get("bronzeTarget") or "")


def ledger_ref_summary(ref: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(ref, dict):
        return {"attached": False}
    return {
        "attached": True,
        "uri": ref.get("uri"),
        "hash": ref.get("hash"),
        "artifact_type": ref.get("artifact_type"),
        "ledger_id": ref.get("ledger_id"),
        "environment": ref.get("environment"),
        "passed": ref.get("passed"),
        "target_table": ref.get("target_table"),
    }


def maintenance_summary(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"attached": False}
    return {
        "attached": True,
        "table": row.get("table"),
        "append_only_enforced": row.get("append_only_enforced"),
        "compaction_status": maintenance_status(row, "compaction"),
        "snapshot_retention_status": maintenance_status(row, "snapshot_retention"),
        "orphan_cleanup_status": maintenance_status(row, "orphan_cleanup"),
        "table_properties_ready": table_properties_ready(row),
    }


def compact_table_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": row.get("source_id"),
        "priority": row.get("priority"),
        "product": row.get("product"),
        "domain": row.get("domain"),
        "topic": row.get("topic"),
        "bronze_target": row.get("bronze_target"),
        "risk_state": row.get("risk_state"),
        "issues": row.get("issues", []),
        "next_actions": row.get("next_actions", []),
    }


def maintenance_status(row: dict[str, Any] | None, key: str) -> str | None:
    if not isinstance(row, dict) or not isinstance(row.get(key), dict):
        return None
    value = row[key].get("status")
    return value if isinstance(value, str) else None


def table_properties_ready(row: dict[str, Any] | None) -> bool:
    if not isinstance(row, dict) or not isinstance(row.get("table_properties"), dict):
        return False
    properties = row["table_properties"]
    return (
        str(properties.get("format-version")) == "2"
        and int_value(properties.get("commit.retry.num-retries")) >= 4
        and int_value(properties.get("write.target-file-size-bytes")) >= 134_217_728
    )


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_hash(value: object) -> bool:
    return isinstance(value, str) and value.startswith("sha256:")


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def stable_id(*parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
