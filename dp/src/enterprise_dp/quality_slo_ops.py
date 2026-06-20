from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import build_catalog_bundle, canonical_json, hash_file, load_json
from enterprise_dp.quality_profiles import hash_quality_profile_registry, list_quality_profiles


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
QUALITY_GATE_IDS = {
    "P0-QUALITY",
    "P0-PIPELINE-QUALITY",
    "P0-QUALITY-PROFILE",
    "P0-OUTPUT-EVIDENCE",
    "P0-RELEASE-EVIDENCE-PROFILE",
}
FRESHNESS_GATE_IDS = {
    "P0-FRESHNESS",
    "P0-INGESTION-LAG",
}


@dataclass(frozen=True)
class QualitySloOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_quality_slo_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    catalog_bundle_path: str | Path | None = None,
    catalog_bundle: dict[str, Any] | None = None,
    release_evidence_paths: list[str | Path] | None = None,
    quality_runtime_evidence_path: str | Path | None = None,
    alert_evidence_path: str | Path | None = None,
    incident_report_path: str | Path | None = None,
    generated_at: str | None = None,
) -> QualitySloOpsReportResult:
    report = build_quality_slo_ops_report(
        root,
        environment=environment,
        catalog_bundle_path=catalog_bundle_path,
        catalog_bundle=catalog_bundle,
        release_evidence_paths=release_evidence_paths,
        quality_runtime_evidence_path=quality_runtime_evidence_path,
        alert_evidence_path=alert_evidence_path,
        incident_report_path=incident_report_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return QualitySloOpsReportResult(output_path=target, report=report)


def build_quality_slo_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    catalog_bundle_path: str | Path | None = None,
    catalog_bundle: dict[str, Any] | None = None,
    release_evidence_paths: list[str | Path] | None = None,
    quality_runtime_evidence_path: str | Path | None = None,
    alert_evidence_path: str | Path | None = None,
    incident_report_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    catalog_ref, catalog = load_or_build_catalog_bundle(
        platform_root,
        catalog_bundle_path=catalog_bundle_path,
        catalog_bundle=catalog_bundle,
        generated_at=generated,
    )
    release_refs, release_index = load_release_evidence(release_evidence_paths or [])
    runtime_ref, runtime_evidence = load_optional_json(quality_runtime_evidence_path)
    alert_ref, alert_evidence = load_optional_json(alert_evidence_path)
    incident_ref, incident_report = load_optional_json(incident_report_path)
    runtime_index = build_runtime_quality_index(runtime_evidence)
    profile_index = build_quality_profile_index(platform_root)
    product_rows = [
        quality_slo_product_row(
            data_product,
            release_index.get(str(data_product.get("name"))),
            runtime_index.get(str(data_product.get("name"))),
            profile_index.get(str(data_product.get("name")), []),
            environment=environment,
        )
        for data_product in sorted(catalog.get("data_products", []), key=lambda item: str(item.get("name")))
        if isinstance(data_product, dict)
    ]
    global_checks = quality_slo_global_checks(
        environment=environment,
        catalog_ref=catalog_ref,
        release_refs=release_refs,
        runtime_ref=runtime_ref,
        runtime_evidence=runtime_evidence,
        alert_ref=alert_ref,
        alert_evidence=alert_evidence,
        incident_ref=incident_ref,
        incident_report=incident_report,
    )
    failed_global = [check for check in global_checks if check.get("passed") is not True]
    failed_products = [row for row in product_rows if row.get("passed") is not True]
    passed = not failed_global and not failed_products
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    return {
        "artifact_type": "quality_slo_release_gates_ops_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "quality-slo-ops",
            environment,
            generated,
            catalog_ref,
            release_refs,
            runtime_ref,
            alert_ref,
            incident_ref,
        ),
        "generated_at": generated,
        "environment": environment,
        "capability_id": "quality-slo-release-gates",
        "readiness_state": readiness_state,
        "mode": "runtime_attested" if runtime_ref.get("attached") is True else "local_preflight",
        "inputs": {
            "catalog_bundle": catalog_ref,
            "release_evidence": release_refs,
            "quality_runtime_evidence": runtime_ref,
            "alert_evidence": alert_ref,
            "incident_report": incident_ref,
            "quality_profile_registry": {
                "hash": hash_quality_profile_registry(platform_root),
                "profile_count": len(list_quality_profiles(platform_root)),
            },
        },
        "checks": global_checks,
        "data_products": product_rows,
        "decision_board": {
            "failed_products": [compact_product_row(row) for row in failed_products[:30]],
            "page_now": [
                action
                for row in failed_products
                for action in row.get("next_actions", [])
                if isinstance(action, dict) and action.get("priority") == "P0"
            ][:30],
        },
        "summary": quality_slo_summary(
            product_rows,
            failed_global,
            release_refs,
            runtime_ref,
            alert_ref,
            incident_ref,
        ),
        "passed": passed,
    }


def load_or_build_catalog_bundle(
    root: Path,
    *,
    catalog_bundle_path: str | Path | None,
    catalog_bundle: dict[str, Any] | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if catalog_bundle_path:
        path = Path(catalog_bundle_path)
        payload = load_json(path)
        return catalog_ref(payload, source="artifact", path=path), payload
    payload = catalog_bundle if isinstance(catalog_bundle, dict) else build_catalog_bundle(root, generated_at=generated_at)
    return catalog_ref(payload, source="generated_from_root", path=None), payload


def catalog_ref(payload: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "attached": True,
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(payload),
        "generated_at": payload.get("generated_at"),
        "data_product_count": summary.get("data_product_count", 0),
        "run_evidence_count": summary.get("run_evidence_count", 0),
    }


def load_optional_json(path_value: str | Path | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if path_value is None:
        return {"attached": False}, None
    path = Path(path_value)
    if not path.is_file():
        return {"attached": False, "uri": path.as_posix(), "missing": True}, None
    payload = load_json(path)
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "environment": payload.get("environment"),
        "passed": payload.get("passed"),
        "readiness_state": payload.get("readiness_state"),
    }, payload


def load_release_evidence(paths: list[str | Path]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    refs = []
    index: dict[str, dict[str, Any]] = {}
    for value in paths:
        path = Path(value)
        payload = load_json(path)
        covered = set()
        primary_output = payload.get("primary_output")
        if isinstance(primary_output, str):
            covered.add(primary_output)
        outputs = payload.get("output_data_products")
        if isinstance(outputs, list):
            covered.update(item for item in outputs if isinstance(item, str))
        ref = {
            "attached": True,
            "uri": path.as_posix(),
            "hash": hash_file(path),
            "release_id": payload.get("release_id"),
            "environment": payload.get("environment"),
            "use_case_id": payload.get("use_case_id"),
            "primary_output": primary_output,
            "output_data_products": sorted(covered),
            "release_passed": payload.get("release_passed"),
            "quality_profile_id": payload.get("quality_profile_id"),
            "quality_profile_hash": payload.get("quality_profile_hash"),
            "payload": payload,
        }
        refs.append({key: item for key, item in ref.items() if key != "payload"})
        for data_product in covered:
            index[data_product] = ref
    return refs, index


def quality_slo_global_checks(
    *,
    environment: str,
    catalog_ref: dict[str, Any],
    release_refs: list[dict[str, Any]],
    runtime_ref: dict[str, Any],
    runtime_evidence: dict[str, Any] | None,
    alert_ref: dict[str, Any],
    alert_evidence: dict[str, Any] | None,
    incident_ref: dict[str, Any],
    incident_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    runtime_summary = mapping(runtime_evidence or {}, "summary")
    alert_summary = mapping(alert_evidence or {}, "summary")
    incident_summary = mapping(incident_report or {}, "summary")
    return [
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check("catalog_bundle_attached", catalog_ref.get("attached") is True, catalog_ref),
        check(
            "release_evidence_attached_for_production_like",
            not production_like or bool(release_refs),
            {"release_count": len(release_refs)},
        ),
        check(
            "release_evidence_environment_matches",
            all(ref.get("environment") in {None, environment} for ref in release_refs),
            {"environments": sorted({str(ref.get("environment")) for ref in release_refs if ref.get("environment")})},
        ),
        check(
            "quality_runtime_evidence_attached_for_production_like",
            not production_like or runtime_ref.get("attached") is True,
            runtime_ref,
        ),
        check(
            "quality_runtime_artifact_type_valid",
            runtime_evidence is None or runtime_evidence.get("artifact_type") == "quality_runtime_evidence.v1",
            {"artifact_type": runtime_evidence.get("artifact_type") if isinstance(runtime_evidence, dict) else None},
        ),
        check(
            "quality_runtime_environment_matches",
            runtime_evidence is None or runtime_evidence.get("environment") == environment,
            {"expected": environment, "actual": runtime_evidence.get("environment") if isinstance(runtime_evidence, dict) else None},
        ),
        check(
            "quality_runtime_non_synthetic_for_production_like",
            not production_like or runtime_evidence is None or runtime_evidence.get("synthetic") is not True,
            {"synthetic": runtime_evidence.get("synthetic") if isinstance(runtime_evidence, dict) else None},
        ),
        check(
            "quality_runtime_passed",
            runtime_evidence is None
            or (
                runtime_evidence.get("passed") is True
                and int_value(runtime_summary.get("failed_check_count")) == 0
                and int_value(runtime_summary.get("freshness_breach_count")) == 0
            ),
            runtime_summary,
        ),
        check(
            "alert_evidence_attached_for_production_like",
            not production_like or alert_ref.get("attached") is True,
            alert_ref,
        ),
        check(
            "alert_evidence_artifact_type_valid",
            alert_evidence is None or alert_evidence.get("artifact_type") == "slo_alert_evidence.v1",
            {"artifact_type": alert_evidence.get("artifact_type") if isinstance(alert_evidence, dict) else None},
        ),
        check(
            "alert_evidence_environment_matches",
            alert_evidence is None or alert_evidence.get("environment") == environment,
            {"expected": environment, "actual": alert_evidence.get("environment") if isinstance(alert_evidence, dict) else None},
        ),
        check(
            "alert_state_green",
            alert_evidence is None
            or (
                alert_evidence.get("status") == "green"
                and int_value(alert_summary.get("open_p0_incident_count")) == 0
                and int_value(alert_summary.get("sla_breached_count")) == 0
            ),
            {"status": alert_evidence.get("status") if isinstance(alert_evidence, dict) else None, **alert_summary},
        ),
        check(
            "incident_report_artifact_type_valid",
            incident_report is None or incident_report.get("artifact_type") == "incident_slo_report.v1",
            {"artifact_type": incident_report.get("artifact_type") if isinstance(incident_report, dict) else None},
        ),
        check(
            "incident_report_environment_matches",
            incident_report is None or incident_report.get("environment") == environment,
            {"expected": environment, "actual": incident_report.get("environment") if isinstance(incident_report, dict) else None},
        ),
        check(
            "incident_report_p0_clear",
            incident_report is None
            or (
                int_value(incident_summary.get("open_p0_count")) == 0
                and int_value(incident_summary.get("sla_breached_count")) == 0
            ),
            incident_summary,
        ),
    ]


def quality_slo_product_row(
    data_product: dict[str, Any],
    release_ref: dict[str, Any] | None,
    runtime_row: dict[str, Any] | None,
    profile_ids: list[str],
    *,
    environment: str,
) -> dict[str, Any]:
    name = str(data_product.get("name"))
    layer = str(data_product.get("layer") or "")
    quality = mapping(data_product, "quality")
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    release = artifact_payload(release_ref)
    release_gates = release.get("gates", []) if isinstance(release, dict) and isinstance(release.get("gates"), list) else []
    freshness_age_seconds = runtime_row.get("age_seconds") if isinstance(runtime_row, dict) else None
    freshness_slo_seconds = runtime_row.get("slo_seconds") if isinstance(runtime_row, dict) else None
    checks = [
        check(
            "freshness_slo_declared",
            isinstance(quality.get("freshness_slo_minutes"), int) and quality.get("freshness_slo_minutes") > 0,
            {"freshness_slo_minutes": quality.get("freshness_slo_minutes")},
        ),
        check(
            "quality_checks_declared",
            isinstance(quality.get("checks"), list) and bool(quality.get("checks")),
            {"check_count": len(quality.get("checks", [])) if isinstance(quality.get("checks"), list) else 0},
        ),
        check("gold_quality_profile_attached", layer != "GOLD" or bool(profile_ids), {"profile_ids": profile_ids}),
        check(
            "release_evidence_attached_for_production_like",
            not production_like or isinstance(release, dict),
            {"data_product": name},
        ),
        check(
            "release_passed",
            release is None or release.get("release_passed") is True,
            {"release_passed": release.get("release_passed") if isinstance(release, dict) else None},
        ),
        check(
            "release_quality_gates_passed",
            release is None or gates_passed(release_gates, QUALITY_GATE_IDS),
            {"failed_gates": failed_gate_ids(release_gates, QUALITY_GATE_IDS)},
        ),
        check(
            "release_freshness_gates_passed",
            release is None or gates_passed(release_gates, FRESHNESS_GATE_IDS),
            {"failed_gates": failed_gate_ids(release_gates, FRESHNESS_GATE_IDS)},
        ),
        check(
            "runtime_quality_attached_for_production_like",
            not production_like or isinstance(runtime_row, dict),
            {"data_product": name},
        ),
        check(
            "runtime_quality_passed",
            runtime_row is None
            or (
                runtime_row.get("validation_passed") is True
                and int_value(runtime_row.get("failed_check_count")) == 0
            ),
            {
                "validation_passed": runtime_row.get("validation_passed") if isinstance(runtime_row, dict) else None,
                "failed_check_count": runtime_row.get("failed_check_count") if isinstance(runtime_row, dict) else None,
            },
        ),
        check(
            "runtime_freshness_green",
            runtime_row is None
            or (
                runtime_row.get("freshness_status") == "GREEN"
                and (
                    not isinstance(freshness_age_seconds, int | float)
                    or not isinstance(freshness_slo_seconds, int | float)
                    or freshness_age_seconds <= freshness_slo_seconds
                )
            ),
            {
                "freshness_status": runtime_row.get("freshness_status") if isinstance(runtime_row, dict) else None,
                "age_seconds": freshness_age_seconds,
                "slo_seconds": freshness_slo_seconds,
            },
        ),
    ]
    issues = product_issues(checks)
    return {
        "data_product": name,
        "layer": layer,
        "domain": data_product.get("domain"),
        "product": data_product.get("product"),
        "quality_profile_ids": profile_ids,
        "release": release_summary(release_ref),
        "runtime_quality": runtime_summary(runtime_row),
        "freshness_slo_minutes": quality.get("freshness_slo_minutes"),
        "checks": checks,
        "issues": issues,
        "risk_state": issues[0] if issues else "ok",
        "next_actions": next_actions(issues, name),
        "passed": not issues,
    }


def gates_passed(gates: list[Any], gate_ids: set[str]) -> bool:
    matched = [
        gate
        for gate in gates
        if isinstance(gate, dict) and gate.get("gate_id") in gate_ids
    ]
    return bool(matched) and all(gate.get("passed") is True for gate in matched)


def failed_gate_ids(gates: list[Any], gate_ids: set[str]) -> list[str]:
    return [
        str(gate.get("gate_id"))
        for gate in gates
        if isinstance(gate, dict)
        and gate.get("gate_id") in gate_ids
        and gate.get("passed") is not True
    ]


def product_issues(checks: list[dict[str, Any]]) -> list[str]:
    issue_map = {
        "freshness_slo_declared": "freshness_slo_missing",
        "quality_checks_declared": "quality_checks_missing",
        "gold_quality_profile_attached": "quality_profile_missing",
        "release_evidence_attached_for_production_like": "release_evidence_missing",
        "release_passed": "release_failed",
        "release_quality_gates_passed": "release_quality_failed",
        "release_freshness_gates_passed": "release_freshness_failed",
        "runtime_quality_attached_for_production_like": "runtime_quality_missing",
        "runtime_quality_passed": "runtime_quality_failed",
        "runtime_freshness_green": "runtime_freshness_breach",
    }
    return [
        issue_map[check["name"]]
        for check in checks
        if check.get("passed") is not True and check.get("name") in issue_map
    ]


def next_actions(issues: list[str], data_product: str) -> list[dict[str, Any]]:
    actions = []
    if any(issue in issues for issue in ("freshness_slo_missing", "quality_checks_missing", "quality_profile_missing")):
        actions.append({"priority": "P0", "action": "repair_quality_contract_or_profile", "owner": "data-platform-team"})
    if any(issue.startswith("release_") for issue in issues):
        actions.append({"priority": "P0", "action": "rerun_release_gates_and_attach_evidence", "owner": "data-platform-team"})
    if any(issue.startswith("runtime_quality") for issue in issues):
        actions.append({"priority": "P0", "action": "attach_runtime_quality_evidence", "owner": "data-platform-team"})
    if "runtime_freshness_breach" in issues:
        actions.append({"priority": "P0", "action": "restore_freshness_slo", "owner": "data-platform-team"})
    return actions or [{"priority": "P3", "action": "no_action", "owner": data_product}]


def quality_slo_summary(
    rows: list[dict[str, Any]],
    failed_global_checks: list[dict[str, Any]],
    release_refs: list[dict[str, Any]],
    runtime_ref: dict[str, Any],
    alert_ref: dict[str, Any],
    incident_ref: dict[str, Any],
) -> dict[str, Any]:
    failed_products = [row for row in rows if row.get("passed") is not True]
    return {
        "data_product_count": len(rows),
        "failed_product_count": len(failed_products),
        "global_failed_check_count": len(failed_global_checks),
        "release_evidence_count": len(release_refs),
        "release_failed_count": sum(1 for row in rows if "release_failed" in row.get("issues", [])),
        "release_quality_failed_count": sum(1 for row in rows if "release_quality_failed" in row.get("issues", [])),
        "release_freshness_failed_count": sum(1 for row in rows if "release_freshness_failed" in row.get("issues", [])),
        "runtime_quality_attached": runtime_ref.get("attached") is True,
        "runtime_quality_failed_count": sum(1 for row in rows if "runtime_quality_failed" in row.get("issues", [])),
        "runtime_freshness_breach_count": sum(1 for row in rows if "runtime_freshness_breach" in row.get("issues", [])),
        "quality_profile_gap_count": sum(1 for row in rows if "quality_profile_missing" in row.get("issues", [])),
        "alert_evidence_attached": alert_ref.get("attached") is True,
        "incident_report_attached": incident_ref.get("attached") is True,
        "by_risk_state": count_by(rows, "risk_state"),
    }


def build_runtime_quality_index(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    rows = report.get("data_products") if isinstance(report, dict) else None
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("data_product")): row
        for row in rows
        if isinstance(row, dict) and row.get("data_product")
    }


def build_quality_profile_index(root: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for profile in list_quality_profiles(root):
        profile_id = profile.get("id")
        if not isinstance(profile_id, str):
            continue
        covered = set()
        applies_to = mapping(profile, "appliesTo")
        required_columns = profile.get("requiredColumns") if isinstance(profile.get("requiredColumns"), dict) else {}
        covered.update(item for item in list_value(applies_to.get("primaryOutputs")) if isinstance(item, str))
        covered.update(item for item in list_value(profile.get("requiredOutputDataProducts")) if isinstance(item, str))
        covered.update(key for key in required_columns if isinstance(key, str))
        for data_product in covered:
            index.setdefault(data_product, []).append(profile_id)
    return {key: sorted(values) for key, values in index.items()}


def artifact_payload(ref: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(ref, dict):
        return None
    payload = ref.get("payload")
    return payload if isinstance(payload, dict) else None


def release_summary(ref: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(ref, dict):
        return {"attached": False}
    return {
        "attached": True,
        "uri": ref.get("uri"),
        "hash": ref.get("hash"),
        "release_id": ref.get("release_id"),
        "environment": ref.get("environment"),
        "release_passed": ref.get("release_passed"),
        "quality_profile_id": ref.get("quality_profile_id"),
    }


def runtime_summary(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"attached": False}
    return {
        "attached": True,
        "quality_tool": row.get("quality_tool"),
        "validation_passed": row.get("validation_passed"),
        "failed_check_count": row.get("failed_check_count"),
        "freshness_status": row.get("freshness_status"),
        "age_seconds": row.get("age_seconds"),
        "slo_seconds": row.get("slo_seconds"),
        "quarantine_row_count": row.get("quarantine_row_count"),
    }


def compact_product_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_product": row.get("data_product"),
        "risk_state": row.get("risk_state"),
        "issues": row.get("issues", []),
        "next_actions": row.get("next_actions", []),
    }


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def list_value(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def int_value(value: object) -> int:
    return value if isinstance(value, int) else 0


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def content_hash(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def stable_id(*parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
