from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import re
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file
from enterprise_dp.contracts import ValidationResult, load_yaml, require_int, require_mapping, require_string, require_string_list
from enterprise_dp.semantic_metrics import validate_semantic_metric_registry


REPORT_VERSION = 1
CERTIFICATION_ID = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_CERTIFICATION_STATUSES = {"submitted", "approved", "rejected", "superseded"}
VALID_CHANGE_TYPES = {"initial_certification", "definition_change", "source_change", "deprecation"}
VALID_APPROVER_ROLES = {
    "data_steward",
    "domain_owner",
    "enterprise_data_council",
    "finance_controller",
    "platform_owner",
    "product_owner",
}
REQUIRED_EVIDENCE_KEYS = (
    "metricOwnerApprovalUri",
    "formulaReviewUri",
    "sourceLineageUri",
    "qualityDependencyUri",
    "impactAnalysisUri",
)
REQUIRED_DIFF_KEYS = ("baseline", "changedFields")


@dataclass(frozen=True)
class SemanticMetricCertificationReportResult:
    output_path: Path
    report: dict[str, Any]


def write_semantic_metric_certification_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    generated_at: str | None = None,
) -> SemanticMetricCertificationReportResult:
    report = build_semantic_metric_certification_report(root, environment=environment, generated_at=generated_at)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SemanticMetricCertificationReportResult(output_path=target, report=report)


def build_semantic_metric_certification_report(
    root: str | Path,
    *,
    environment: str = "local",
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    metric_registry_path = platform_root / "platform" / "serving" / "semantic-metrics.yaml"
    certification_path = certification_registry_path(platform_root)
    metric_registry = load_yaml(metric_registry_path) if metric_registry_path.is_file() else {"metrics": []}
    certification_registry = load_yaml(certification_path) if certification_path.is_file() else {"certifications": []}
    registry_validation = validate_semantic_metric_registry(platform_root)
    certification_validation = validate_semantic_metric_certification_registry(platform_root)
    metrics = [
        metric
        for metric in metric_registry.get("metrics", [])
        if isinstance(metric, dict) and isinstance(metric.get("metricId"), str)
    ]
    certifications = [
        item
        for item in certification_registry.get("certifications", [])
        if isinstance(item, dict)
    ]
    certification_index = approved_certification_index(certifications)
    metric_rows = [
        metric_certification_row(metric, certification_index.get(str(metric.get("metricId"))))
        for metric in sorted(metrics, key=lambda item: str(item.get("metricId")))
    ]
    global_checks = [
        check("semantic_metric_registry_valid", registry_validation.ok, {"errors": registry_validation.errors[:20]}),
        check("certification_registry_attached", certification_path.is_file(), {"uri": certification_path.as_posix()}),
        check("certification_registry_valid", certification_validation.ok, {"errors": certification_validation.errors[:20]}),
    ]
    failed_global = [item for item in global_checks if item.get("passed") is not True]
    failed_metrics = [item for item in metric_rows if item.get("passed") is not True]
    passed = not failed_global and not failed_metrics
    return {
        "artifact_type": "semantic_metric_certification_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "semantic-metric-certification",
            environment,
            generated,
            hash_file(metric_registry_path) if metric_registry_path.is_file() else None,
            hash_file(certification_path) if certification_path.is_file() else None,
        ),
        "generated_at": generated,
        "environment": environment,
        "capability_id": "semantic-metric-serving",
        "readiness_state": "certification_ready" if passed else "not_ready",
        "inputs": {
            "semantic_metric_registry": artifact_ref(metric_registry_path),
            "semantic_metric_certification_registry": artifact_ref(certification_path),
        },
        "checks": global_checks,
        "metrics": metric_rows,
        "decision_board": {
            "failed_metrics": [compact_metric_row(item) for item in failed_metrics[:50]],
            "page_now": [
                action
                for row in failed_metrics
                for action in row.get("next_actions", [])
                if isinstance(action, dict) and action.get("priority") == "P0"
            ][:50],
        },
        "summary": certification_summary(metric_rows, certifications, failed_global),
        "passed": passed,
    }


def validate_semantic_metric_certification_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    path = certification_registry_path(root)
    if not path.is_file():
        result.error(path, "governance/semantic-metric-certifications.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(path)
    require_int(path, result, registry, "version", minimum=1)
    require_string(path, result, registry, "registry_scope")
    require_string(path, result, registry, "owner")
    certifications = registry.get("certifications")
    if not isinstance(certifications, list) or not certifications:
        result.error(path, "certifications must be a non-empty list")
        return result

    metric_registry = load_yaml(root / "platform" / "serving" / "semantic-metrics.yaml")
    metrics = {
        str(metric["metricId"]): metric
        for metric in metric_registry.get("metrics", [])
        if isinstance(metric, dict) and isinstance(metric.get("metricId"), str)
    }
    approved_seen: dict[str, str] = {}
    seen_ids: set[str] = set()
    for index, certification in enumerate(certifications):
        result.checked_count += 1
        validate_certification_entry(path, certification, index, metrics, approved_seen, seen_ids, result)
    return result


def validate_certification_entry(
    path: Path,
    certification: object,
    index: int,
    metrics: dict[str, dict[str, Any]],
    approved_seen: dict[str, str],
    seen_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"certifications[{index}]"
    if not isinstance(certification, dict):
        result.error(path, f"{prefix} must be an object")
        return

    certification_id = require_string(path, result, certification, "certificationId", prefix)
    if certification_id:
        if not CERTIFICATION_ID.fullmatch(certification_id):
            result.error(path, f"{prefix}.certificationId must be snake_case")
        if certification_id in seen_ids:
            result.error(path, f"{prefix}.certificationId duplicates {certification_id!r}")
        seen_ids.add(certification_id)

    status = require_string(path, result, certification, "status", prefix)
    if status and status not in VALID_CERTIFICATION_STATUSES:
        result.error(path, f"{prefix}.status must be one of {sorted(VALID_CERTIFICATION_STATUSES)}")
    change_type = require_string(path, result, certification, "changeType", prefix)
    if change_type and change_type not in VALID_CHANGE_TYPES:
        result.error(path, f"{prefix}.changeType must be one of {sorted(VALID_CHANGE_TYPES)}")

    metric_ids = require_string_list(path, result, certification, "metricIds", prefix) or []
    if not metric_ids:
        result.error(path, f"{prefix}.metricIds must be non-empty")
    if len(metric_ids) != len(set(metric_ids)):
        result.error(path, f"{prefix}.metricIds must not contain duplicates")
    for metric_id in metric_ids:
        if metric_id not in metrics:
            result.error(path, f"{prefix}.metricIds references unknown metric {metric_id!r}")
        if status == "approved":
            previous = approved_seen.get(metric_id)
            if previous:
                result.error(path, f"{prefix}.metricIds has multiple approved certifications for {metric_id!r}: {previous}")
            approved_seen[metric_id] = certification_id or prefix

    requester = require_string(path, result, certification, "requestedBy", prefix)
    approver = require_string(path, result, certification, "approvedBy", prefix)
    require_string(path, result, certification, "requestedAt", prefix)
    require_string(path, result, certification, "approvedAt", prefix)
    require_string(path, result, certification, "reason", prefix)
    approver_role = require_string(path, result, certification, "approverRole", prefix)
    if approver_role and approver_role not in VALID_APPROVER_ROLES:
        result.error(path, f"{prefix}.approverRole must be one of {sorted(VALID_APPROVER_ROLES)}")
    if status == "approved" and requester and approver and requester == approver:
        result.error(path, f"{prefix}.approvedBy must differ from requestedBy for maker-checker")

    evidence = require_mapping(path, result, certification, "evidence")
    if evidence is not None:
        validate_required_mapping_strings(path, result, evidence, REQUIRED_EVIDENCE_KEYS, f"{prefix}.evidence")
    diff = require_mapping(path, result, certification, "diff")
    if diff is not None:
        validate_required_mapping_strings(path, result, diff, REQUIRED_DIFF_KEYS, f"{prefix}.diff")
        changed_fields = diff.get("changedFields")
        if not isinstance(changed_fields, list) or not changed_fields:
            result.error(path, f"{prefix}.diff.changedFields must be a non-empty list")
    impact = require_mapping(path, result, certification, "impact")
    if impact is not None:
        validate_impact(path, result, impact, metric_ids, metrics, prefix)


def validate_required_mapping_strings(
    path: Path,
    result: ValidationResult,
    mapping_value: dict[str, Any],
    keys: tuple[str, ...],
    prefix: str,
) -> None:
    for key in keys:
        value = mapping_value.get(key)
        if isinstance(value, list):
            if not value or not all(isinstance(item, str) and item.strip() for item in value):
                result.error(path, f"{prefix}.{key} must be a non-empty string list")
        elif not isinstance(value, str) or not value.strip():
            result.error(path, f"{prefix}.{key} is required")


def validate_impact(
    path: Path,
    result: ValidationResult,
    impact: dict[str, Any],
    metric_ids: list[str],
    metrics: dict[str, dict[str, Any]],
    prefix: str,
) -> None:
    use_cases = require_string_list(path, result, impact, "useCases", f"{prefix}.impact") or []
    consumers = require_string_list(path, result, impact, "consumers", f"{prefix}.impact") or []
    source_products = require_string_list(path, result, impact, "sourceDataProducts", f"{prefix}.impact") or []
    expected_use_cases = sorted({
        str(use_case)
        for metric_id in metric_ids
        for use_case in list_value(metrics.get(metric_id, {}).get("useCases"))
    })
    expected_consumers = sorted({
        str(consumer)
        for metric_id in metric_ids
        for consumer in list_value(metrics.get(metric_id, {}).get("consumers"))
    })
    expected_sources = sorted({
        str(source.get("dataProduct"))
        for metric_id in metric_ids
        for source in [mapping(metrics.get(metric_id, {}), "source")]
        if source.get("dataProduct")
    })
    for missing in sorted(set(expected_use_cases) - set(use_cases)):
        result.error(path, f"{prefix}.impact.useCases must include {missing!r}")
    for missing in sorted(set(expected_consumers) - set(consumers)):
        result.error(path, f"{prefix}.impact.consumers must include {missing!r}")
    for missing in sorted(set(expected_sources) - set(source_products)):
        result.error(path, f"{prefix}.impact.sourceDataProducts must include {missing!r}")


def metric_certification_row(metric: dict[str, Any], certification: dict[str, Any] | None) -> dict[str, Any]:
    metric_id = str(metric.get("metricId"))
    checks = [
        check("metric_status_certified", metric.get("status") == "certified", {"status": metric.get("status")}),
        check("certification_present", isinstance(certification, dict), {"metric_id": metric_id}),
        check(
            "certification_approved",
            isinstance(certification, dict) and certification.get("status") == "approved",
            {"status": certification.get("status") if isinstance(certification, dict) else None},
        ),
        check(
            "maker_checker_separated",
            isinstance(certification, dict)
            and non_empty(certification.get("requestedBy"))
            and non_empty(certification.get("approvedBy"))
            and certification.get("requestedBy") != certification.get("approvedBy"),
            {
                "requested_by": certification.get("requestedBy") if isinstance(certification, dict) else None,
                "approved_by": certification.get("approvedBy") if isinstance(certification, dict) else None,
            },
        ),
        check("required_evidence_complete", evidence_complete(certification), compact_evidence(certification)),
        check("diff_attached", diff_complete(certification), compact_diff(certification)),
        check("impact_covers_metric", impact_covers_metric(metric, certification), compact_impact(certification)),
    ]
    issues = certification_issues(checks)
    return {
        "metric_id": metric_id,
        "name": metric.get("name"),
        "domain": metric.get("domain"),
        "owner": metric.get("owner"),
        "status": metric.get("status"),
        "source_data_product": mapping(metric, "source").get("dataProduct"),
        "definition_hash": content_hash(metric),
        "certification": compact_certification(certification),
        "checks": checks,
        "issues": issues,
        "risk_state": issues[0] if issues else "ok",
        "next_actions": certification_next_actions(issues, metric_id),
        "passed": not issues,
    }


def approved_certification_index(certifications: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for certification in certifications:
        if certification.get("status") != "approved":
            continue
        for metric_id in list_value(certification.get("metricIds")):
            index.setdefault(str(metric_id), certification)
    return index


def certification_rows_by_metric(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    rows = report.get("metrics") if isinstance(report, dict) else None
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("metric_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("metric_id")
    }


def certification_summary(
    rows: list[dict[str, Any]],
    certifications: list[dict[str, Any]],
    failed_global_checks: list[dict[str, Any]],
) -> dict[str, Any]:
    failed_rows = [row for row in rows if row.get("passed") is not True]
    approved_rows = [row for row in rows if row.get("certification", {}).get("status") == "approved"]
    return {
        "metric_count": len(rows),
        "approved_metric_count": len(approved_rows),
        "uncertified_metric_count": len(rows) - len(approved_rows),
        "certification_count": len(certifications),
        "approved_certification_count": sum(1 for item in certifications if item.get("status") == "approved"),
        "failed_metric_count": len(failed_rows),
        "global_failed_check_count": len(failed_global_checks),
        "maker_checker_violation_count": sum(1 for row in rows if "maker_checker_violation" in row.get("issues", [])),
        "by_status": count_by(rows, "status"),
        "by_risk_state": count_by(rows, "risk_state"),
    }


def evidence_complete(certification: dict[str, Any] | None) -> bool:
    evidence = mapping(certification or {}, "evidence")
    return all(non_empty(evidence.get(key)) for key in REQUIRED_EVIDENCE_KEYS)


def diff_complete(certification: dict[str, Any] | None) -> bool:
    diff = mapping(certification or {}, "diff")
    return non_empty(diff.get("baseline")) and bool(list_value(diff.get("changedFields")))


def impact_covers_metric(metric: dict[str, Any], certification: dict[str, Any] | None) -> bool:
    impact = mapping(certification or {}, "impact")
    expected_use_cases = set(str(item) for item in list_value(metric.get("useCases")))
    expected_consumers = set(str(item) for item in list_value(metric.get("consumers")))
    expected_sources = {str(mapping(metric, "source").get("dataProduct"))}
    return (
        expected_use_cases.issubset(set(str(item) for item in list_value(impact.get("useCases"))))
        and expected_consumers.issubset(set(str(item) for item in list_value(impact.get("consumers"))))
        and expected_sources.issubset(set(str(item) for item in list_value(impact.get("sourceDataProducts"))))
    )


def certification_issues(checks: list[dict[str, Any]]) -> list[str]:
    issue_map = {
        "metric_status_certified": "metric_not_marked_certified",
        "certification_present": "certification_missing",
        "certification_approved": "certification_not_approved",
        "maker_checker_separated": "maker_checker_violation",
        "required_evidence_complete": "certification_evidence_missing",
        "diff_attached": "metric_diff_missing",
        "impact_covers_metric": "impact_analysis_incomplete",
    }
    return [
        issue_map[check["name"]]
        for check in checks
        if check.get("passed") is not True and check.get("name") in issue_map
    ]


def certification_next_actions(issues: list[str], metric_id: str) -> list[dict[str, Any]]:
    actions = []
    if "metric_not_marked_certified" in issues or "certification_missing" in issues or "certification_not_approved" in issues:
        actions.append({"priority": "P0", "metric_id": metric_id, "action": "complete_metric_certification_workflow", "owner": "enterprise-reporting-team"})
    if "maker_checker_violation" in issues:
        actions.append({"priority": "P0", "metric_id": metric_id, "action": "reapprove_with_separation_of_duties", "owner": "enterprise-data-council"})
    if "certification_evidence_missing" in issues or "metric_diff_missing" in issues or "impact_analysis_incomplete" in issues:
        actions.append({"priority": "P0", "metric_id": metric_id, "action": "complete_certification_evidence_pack", "owner": "metric-owner"})
    return actions or [{"priority": "P3", "metric_id": metric_id, "action": "no_action", "owner": "metric-owner"}]


def compact_metric_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_id": row.get("metric_id"),
        "status": row.get("status"),
        "certification_id": row.get("certification", {}).get("certification_id"),
        "risk_state": row.get("risk_state"),
        "issues": row.get("issues", []),
        "next_actions": row.get("next_actions", []),
    }


def compact_certification(certification: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(certification, dict):
        return {"attached": False}
    return {
        "attached": True,
        "certification_id": certification.get("certificationId"),
        "status": certification.get("status"),
        "change_type": certification.get("changeType"),
        "requested_by": certification.get("requestedBy"),
        "requested_at": certification.get("requestedAt"),
        "approved_by": certification.get("approvedBy"),
        "approved_at": certification.get("approvedAt"),
        "approver_role": certification.get("approverRole"),
        "reason": certification.get("reason"),
        "evidence": compact_evidence(certification),
        "diff": compact_diff(certification),
        "impact": compact_impact(certification),
    }


def compact_evidence(certification: dict[str, Any] | None) -> dict[str, Any]:
    evidence = mapping(certification or {}, "evidence")
    return {key: evidence.get(key) for key in REQUIRED_EVIDENCE_KEYS}


def compact_diff(certification: dict[str, Any] | None) -> dict[str, Any]:
    diff = mapping(certification or {}, "diff")
    return {key: diff.get(key) for key in ("baseline", "changedFields", "impactSummary")}


def compact_impact(certification: dict[str, Any] | None) -> dict[str, Any]:
    impact = mapping(certification or {}, "impact")
    return {
        "useCases": list_value(impact.get("useCases")),
        "consumers": list_value(impact.get("consumers")),
        "sourceDataProducts": list_value(impact.get("sourceDataProducts")),
    }


def artifact_ref(path: Path) -> dict[str, Any]:
    return {
        "attached": path.is_file(),
        "uri": path.as_posix(),
        "hash": hash_file(path) if path.is_file() else None,
    }


def certification_registry_path(root: Path) -> Path:
    return root / "governance" / "semantic-metric-certifications.yaml"


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


def list_value(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def non_empty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def content_hash(value: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()}"


def stable_id(*parts: Any) -> str:
    return hashlib.sha256(canonical_json(parts).encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
