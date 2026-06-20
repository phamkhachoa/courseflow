from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

from enterprise_dp.catalog import canonical_json, hash_file, load_json
from enterprise_dp.contracts import load_yaml
from enterprise_dp.semantic_metric_certification import (
    build_semantic_metric_certification_report,
    certification_rows_by_metric,
)
from enterprise_dp.semantic_metrics import validate_semantic_metric_registry
from enterprise_dp.semantic_views import build_semantic_view_manifest, validate_semantic_view_manifest


REPORT_VERSION = 1
SUPPORTED_ENVIRONMENTS = {"local", "staging", "prod"}
PRODUCTION_LIKE_ENVIRONMENTS = {"staging", "prod"}
PRODUCTION_METRIC_STATUSES = {"certified"}
LOCAL_METRIC_STATUSES = {"provisional", "certified"}


@dataclass(frozen=True)
class SemanticMetricServingOpsReportResult:
    output_path: Path
    report: dict[str, Any]


def write_semantic_metric_serving_ops_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str = "local",
    semantic_view_manifest_path: str | Path | None = None,
    metric_certification_report_path: str | Path | None = None,
    serving_deployment_evidence_path: str | Path | None = None,
    usage_evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> SemanticMetricServingOpsReportResult:
    report = build_semantic_metric_serving_ops_report(
        root,
        environment=environment,
        semantic_view_manifest_path=semantic_view_manifest_path,
        metric_certification_report_path=metric_certification_report_path,
        serving_deployment_evidence_path=serving_deployment_evidence_path,
        usage_evidence_path=usage_evidence_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return SemanticMetricServingOpsReportResult(output_path=target, report=report)


def build_semantic_metric_serving_ops_report(
    root: str | Path,
    *,
    environment: str = "local",
    semantic_view_manifest_path: str | Path | None = None,
    semantic_view_manifest: dict[str, Any] | None = None,
    metric_certification_report_path: str | Path | None = None,
    metric_certification_report: dict[str, Any] | None = None,
    serving_deployment_evidence_path: str | Path | None = None,
    usage_evidence_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    platform_root = Path(root)
    generated = generated_at or utc_now()
    registry_ref, registry = load_metric_registry(platform_root)
    manifest_ref, manifest = load_or_build_semantic_view_manifest(
        platform_root,
        semantic_view_manifest_path=semantic_view_manifest_path,
        semantic_view_manifest=semantic_view_manifest,
        generated_at=generated,
    )
    certification_ref, certification_report = load_or_build_metric_certification_report(
        platform_root,
        environment=environment,
        metric_certification_report_path=metric_certification_report_path,
        metric_certification_report=metric_certification_report,
        generated_at=generated,
    )
    deployment_ref, deployment_evidence = load_optional_json(serving_deployment_evidence_path)
    usage_ref, usage_evidence = load_optional_json(usage_evidence_path)
    metric_rows = [
        semantic_metric_row(
            metric,
            manifest_views_by_metric(manifest).get(str(metric.get("metricId")), []),
            certification_rows_by_metric(certification_report).get(str(metric.get("metricId"))),
            deployment_views_by_metric(deployment_evidence).get(str(metric.get("metricId")), []),
            usage_by_metric(usage_evidence).get(str(metric.get("metricId"))),
            environment=environment,
        )
        for metric in sorted(registry.get("metrics", []), key=lambda item: str(item.get("metricId")))
        if isinstance(metric, dict)
    ]
    global_checks = semantic_serving_global_checks(
        root=platform_root,
        environment=environment,
        registry_ref=registry_ref,
        manifest_ref=manifest_ref,
        manifest=manifest,
        certification_ref=certification_ref,
        certification_report=certification_report,
        deployment_ref=deployment_ref,
        deployment_evidence=deployment_evidence,
        usage_ref=usage_ref,
        usage_evidence=usage_evidence,
    )
    failed_global = [check for check in global_checks if check.get("passed") is not True]
    failed_metrics = [row for row in metric_rows if row.get("passed") is not True]
    passed = not failed_global and not failed_metrics
    readiness_state = (
        "local_preflight_ready"
        if passed and environment == "local"
        else ("production_like_ready" if passed else "not_ready")
    )
    return {
        "artifact_type": "semantic_metric_serving_ops_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id(
            "semantic-metric-serving-ops",
            environment,
            generated,
            registry_ref,
            manifest_ref,
            certification_ref,
            deployment_ref,
            usage_ref,
        ),
        "generated_at": generated,
        "environment": environment,
        "capability_id": "semantic-metric-serving",
        "readiness_state": readiness_state,
        "mode": "runtime_attested" if deployment_ref.get("attached") is True else "local_preflight",
        "inputs": {
            "semantic_metric_registry": registry_ref,
            "semantic_view_manifest": manifest_ref,
            "metric_certification_report": certification_ref,
            "serving_deployment_evidence": deployment_ref,
            "usage_evidence": usage_ref,
        },
        "checks": global_checks,
        "metrics": metric_rows,
        "decision_board": {
            "failed_metrics": [compact_metric_row(row) for row in failed_metrics[:50]],
            "page_now": [
                action
                for row in failed_metrics
                for action in row.get("next_actions", [])
                if isinstance(action, dict) and action.get("priority") == "P0"
            ][:50],
        },
        "summary": semantic_serving_summary(metric_rows, failed_global, certification_ref, deployment_ref, usage_ref),
        "passed": passed,
    }


def load_metric_registry(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    path = root / "platform" / "serving" / "semantic-metrics.yaml"
    payload = load_yaml(path)
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), list) else []
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "metric_count": len(metrics),
    }, payload


def load_or_build_semantic_view_manifest(
    root: Path,
    *,
    semantic_view_manifest_path: str | Path | None,
    semantic_view_manifest: dict[str, Any] | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if semantic_view_manifest_path:
        path = Path(semantic_view_manifest_path)
        if not path.is_file():
            return {"attached": False, "uri": path.as_posix(), "missing": True}, None
        payload = load_json(path)
        return semantic_view_manifest_ref(payload, source="artifact", path=path), payload
    if isinstance(semantic_view_manifest, dict):
        return semantic_view_manifest_ref(semantic_view_manifest, source="provided", path=None), semantic_view_manifest
    try:
        payload = build_semantic_view_manifest(root, generated_at=generated_at)
    except ValueError as exc:
        payload = {
            "artifact_type": "semantic_views_manifest.v1",
            "generated_at": generated_at,
            "summary": {"metric_count": 0, "view_count": 0, "engines": []},
            "views": [],
            "build_error": str(exc),
        }
    return semantic_view_manifest_ref(payload, source="generated_from_root", path=None), payload


def load_or_build_metric_certification_report(
    root: Path,
    *,
    environment: str,
    metric_certification_report_path: str | Path | None,
    metric_certification_report: dict[str, Any] | None,
    generated_at: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if metric_certification_report_path:
        path = Path(metric_certification_report_path)
        if not path.is_file():
            return {"attached": False, "uri": path.as_posix(), "missing": True}, None
        payload = load_json(path)
        return metric_certification_report_ref(payload, source="artifact", path=path), payload
    if isinstance(metric_certification_report, dict):
        return metric_certification_report_ref(metric_certification_report, source="provided", path=None), metric_certification_report
    payload = build_semantic_metric_certification_report(root, environment=environment, generated_at=generated_at)
    return metric_certification_report_ref(payload, source="generated_from_root", path=None), payload


def semantic_view_manifest_ref(payload: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "attached": True,
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(payload),
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "registry_hash": payload.get("registry_hash"),
        "metric_count": summary.get("metric_count", 0),
        "view_count": summary.get("view_count", 0),
        "engines": summary.get("engines", []),
    }


def metric_certification_report_ref(payload: dict[str, Any], *, source: str, path: Path | None) -> dict[str, Any]:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    metric_registry_ref = mapping(mapping(payload, "inputs"), "semantic_metric_registry")
    certification_registry_ref = mapping(mapping(payload, "inputs"), "semantic_metric_certification_registry")
    return {
        "attached": True,
        "source": source,
        "uri": path.as_posix() if path else None,
        "hash": hash_file(path) if path else content_hash(payload),
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "environment": payload.get("environment"),
        "readiness_state": payload.get("readiness_state"),
        "passed": payload.get("passed"),
        "metric_registry_hash": metric_registry_ref.get("hash"),
        "certification_registry_hash": certification_registry_ref.get("hash"),
        "summary": summary,
    }


def load_optional_json(path_value: str | Path | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if path_value is None:
        return {"attached": False}, None
    path = Path(path_value)
    if not path.is_file():
        return {"attached": False, "uri": path.as_posix(), "missing": True}, None
    payload = load_json(path)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "attached": True,
        "uri": path.as_posix(),
        "hash": hash_file(path),
        "artifact_type": payload.get("artifact_type"),
        "generated_at": payload.get("generated_at"),
        "environment": payload.get("environment"),
        "passed": payload.get("passed"),
        "status": payload.get("status"),
        "summary": summary,
    }, payload


def semantic_serving_global_checks(
    *,
    root: Path,
    environment: str,
    registry_ref: dict[str, Any],
    manifest_ref: dict[str, Any],
    manifest: dict[str, Any] | None,
    certification_ref: dict[str, Any],
    certification_report: dict[str, Any] | None,
    deployment_ref: dict[str, Any],
    deployment_evidence: dict[str, Any] | None,
    usage_ref: dict[str, Any],
    usage_evidence: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    registry_validation = validate_semantic_metric_registry(root)
    manifest_validation = validate_semantic_view_manifest(manifest or {})
    deployment_summary = mapping(deployment_evidence or {}, "summary")
    usage_summary = mapping(usage_evidence or {}, "summary")
    return [
        check("environment_supported", environment in SUPPORTED_ENVIRONMENTS, {"environment": environment}),
        check("semantic_metric_registry_attached", registry_ref.get("attached") is True, registry_ref),
        check(
            "semantic_metric_registry_valid",
            registry_validation.ok,
            {"errors": registry_validation.errors[:20], "checked_count": registry_validation.checked_count},
        ),
        check(
            "semantic_view_manifest_attached_for_production_like",
            not production_like or manifest_ref.get("source") == "artifact",
            manifest_ref,
        ),
        check(
            "semantic_view_manifest_artifact_type_valid",
            manifest is None or manifest.get("artifact_type") == "semantic_views_manifest.v1",
            {"artifact_type": manifest.get("artifact_type") if isinstance(manifest, dict) else None},
        ),
        check(
            "semantic_view_manifest_valid",
            manifest_validation.ok,
            {"errors": manifest_validation.errors[:20], "checked_count": manifest_validation.checked_count},
        ),
        check(
            "semantic_view_manifest_registry_hash_matches",
            manifest is None or manifest.get("registry_hash") in {None, registry_ref.get("hash")},
            {"expected": registry_ref.get("hash"), "actual": manifest.get("registry_hash") if isinstance(manifest, dict) else None},
        ),
        check(
            "metric_certification_report_attached_for_production_like",
            not production_like or certification_ref.get("source") == "artifact",
            certification_ref,
        ),
        check(
            "metric_certification_artifact_type_valid",
            certification_report is None
            or certification_report.get("artifact_type") == "semantic_metric_certification_report.v1",
            {"artifact_type": certification_report.get("artifact_type") if isinstance(certification_report, dict) else None},
        ),
        check(
            "metric_certification_environment_matches",
            certification_report is None or certification_report.get("environment") == environment,
            {"expected": environment, "actual": certification_report.get("environment") if isinstance(certification_report, dict) else None},
        ),
        check(
            "metric_certification_registry_hash_matches",
            certification_report is None or certification_ref.get("metric_registry_hash") == registry_ref.get("hash"),
            {"expected": registry_ref.get("hash"), "actual": certification_ref.get("metric_registry_hash")},
        ),
        check(
            "metric_certification_report_passed",
            certification_report is None or certification_report.get("passed") is True,
            certification_ref.get("summary", {}),
        ),
        check(
            "serving_deployment_evidence_attached_for_production_like",
            not production_like or deployment_ref.get("attached") is True,
            deployment_ref,
        ),
        check(
            "serving_deployment_artifact_type_valid",
            deployment_evidence is None
            or deployment_evidence.get("artifact_type") == "semantic_serving_deployment_evidence.v1",
            {"artifact_type": deployment_evidence.get("artifact_type") if isinstance(deployment_evidence, dict) else None},
        ),
        check(
            "serving_deployment_environment_matches",
            deployment_evidence is None or deployment_evidence.get("environment") == environment,
            {"expected": environment, "actual": deployment_evidence.get("environment") if isinstance(deployment_evidence, dict) else None},
        ),
        check(
            "serving_deployment_manifest_hash_matches",
            deployment_evidence is None
            or (
                deployment_evidence.get("semantic_view_manifest_hash") == manifest_ref.get("hash")
                if production_like
                else deployment_evidence.get("semantic_view_manifest_hash") in {None, manifest_ref.get("hash")}
            ),
            {
                "expected": manifest_ref.get("hash"),
                "actual": deployment_evidence.get("semantic_view_manifest_hash") if isinstance(deployment_evidence, dict) else None,
            },
        ),
        check(
            "serving_deployment_passed",
            deployment_evidence is None
            or (
                deployment_evidence.get("passed") is True
                and int_value(deployment_summary.get("failed_view_count")) == 0
            ),
            deployment_summary,
        ),
        check(
            "usage_evidence_attached_for_production_like",
            not production_like or usage_ref.get("attached") is True,
            usage_ref,
        ),
        check(
            "usage_evidence_artifact_type_valid",
            usage_evidence is None or usage_evidence.get("artifact_type") == "semantic_metric_usage_evidence.v1",
            {"artifact_type": usage_evidence.get("artifact_type") if isinstance(usage_evidence, dict) else None},
        ),
        check(
            "usage_evidence_environment_matches",
            usage_evidence is None or usage_evidence.get("environment") == environment,
            {"expected": environment, "actual": usage_evidence.get("environment") if isinstance(usage_evidence, dict) else None},
        ),
        check(
            "usage_tracking_enabled",
            usage_evidence is None
            or (
                usage_evidence.get("passed") is True
                and int_value(usage_summary.get("usage_tracking_disabled_count")) == 0
            ),
            usage_summary,
        ),
    ]


def semantic_metric_row(
    metric: dict[str, Any],
    manifest_views: list[dict[str, Any]],
    certification_row: dict[str, Any] | None,
    deployment_views: list[dict[str, Any]],
    usage_row: dict[str, Any] | None,
    *,
    environment: str,
) -> dict[str, Any]:
    production_like = environment in PRODUCTION_LIKE_ENVIRONMENTS
    metric_id = str(metric.get("metricId"))
    status = str(metric.get("status") or "")
    certification_required = production_like or status == "certified"
    deployment_index = {
        (str(view.get("engine")), str(view.get("view_name"))): view
        for view in deployment_views
        if isinstance(view, dict)
    }
    expected_deployments = [
        deployment_index.get((str(view.get("engine")), str(view.get("view_name"))))
        for view in manifest_views
        if isinstance(view, dict)
    ]
    deployment_ready = bool(manifest_views) and all(
        isinstance(item, dict)
        and item.get("deployed") is True
        and item.get("smoke_test_passed") is True
        and item.get("access_policy_checked") is True
        for item in expected_deployments
    )
    checks = [
        check("metric_status_valid_for_local", status in LOCAL_METRIC_STATUSES, {"status": status}),
        check(
            "metric_certified_for_production_like",
            not production_like or status in PRODUCTION_METRIC_STATUSES,
            {"status": status, "required_statuses": sorted(PRODUCTION_METRIC_STATUSES)},
        ),
        check(
            "metric_certification_approved",
            not certification_required
            or (
                isinstance(certification_row, dict)
                and certification_row.get("passed") is True
                and mapping(certification_row, "certification").get("status") == "approved"
            ),
            {
                "attached": isinstance(certification_row, dict),
                "certification_id": mapping(certification_row or {}, "certification").get("certification_id"),
                "certification_status": mapping(certification_row or {}, "certification").get("status"),
                "certification_passed": certification_row.get("passed") if isinstance(certification_row, dict) else None,
            },
        ),
        check(
            "source_gold_bound",
            str(mapping(metric, "source").get("dataProduct", "")).startswith("gold."),
            {"source": mapping(metric, "source").get("dataProduct")},
        ),
        check("semantic_view_manifest_coverage", bool(manifest_views), {"view_count": len(manifest_views)}),
        check(
            "serving_deployment_present_for_production_like",
            not production_like or bool(deployment_views),
            {"deployment_view_count": len(deployment_views)},
        ),
        check(
            "serving_deployment_green",
            not deployment_views or deployment_ready,
            {
                "expected_view_count": len(manifest_views),
                "deployment_view_count": len(deployment_views),
                "failed_deployments": failed_deployments(manifest_views, deployment_index),
            },
        ),
        check(
            "usage_tracking_present_for_production_like",
            not production_like or isinstance(usage_row, dict),
            {"metric_id": metric_id},
        ),
        check(
            "usage_tracking_enabled_for_metric",
            usage_row is None or usage_row.get("usage_tracking_enabled") is True,
            {"usage_tracking_enabled": usage_row.get("usage_tracking_enabled") if isinstance(usage_row, dict) else None},
        ),
    ]
    issues = metric_issues(checks)
    return {
        "metric_id": metric_id,
        "name": metric.get("name"),
        "domain": metric.get("domain"),
        "owner": metric.get("owner"),
        "status": status,
        "source_data_product": mapping(metric, "source").get("dataProduct"),
        "freshness_slo_minutes": metric.get("freshnessSloMinutes"),
        "view_count": len(manifest_views),
        "certification": certification_summary_row(certification_row),
        "deployment_view_count": len(deployment_views),
        "usage": usage_summary(usage_row),
        "checks": checks,
        "issues": issues,
        "risk_state": issues[0] if issues else "ok",
        "next_actions": next_actions(issues, metric_id),
        "passed": not issues,
    }


def failed_deployments(
    manifest_views: list[dict[str, Any]],
    deployment_index: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    failed = []
    for view in manifest_views:
        if not isinstance(view, dict):
            continue
        key = (str(view.get("engine")), str(view.get("view_name")))
        deployed = deployment_index.get(key)
        if not isinstance(deployed, dict):
            failed.append({"engine": key[0], "view_name": key[1], "issue": "missing_deployment"})
        elif not (
            deployed.get("deployed") is True
            and deployed.get("smoke_test_passed") is True
            and deployed.get("access_policy_checked") is True
        ):
            failed.append(
                {
                    "engine": key[0],
                    "view_name": key[1],
                    "deployed": deployed.get("deployed"),
                    "smoke_test_passed": deployed.get("smoke_test_passed"),
                    "access_policy_checked": deployed.get("access_policy_checked"),
                }
            )
    return failed[:20]


def metric_issues(checks: list[dict[str, Any]]) -> list[str]:
    issue_map = {
        "metric_status_valid_for_local": "metric_lifecycle_invalid",
        "metric_certified_for_production_like": "metric_not_certified",
        "metric_certification_approved": "metric_certification_missing",
        "source_gold_bound": "source_gold_missing",
        "semantic_view_manifest_coverage": "semantic_view_missing",
        "serving_deployment_present_for_production_like": "serving_deployment_missing",
        "serving_deployment_green": "serving_deployment_failed",
        "usage_tracking_present_for_production_like": "usage_tracking_missing",
        "usage_tracking_enabled_for_metric": "usage_tracking_disabled",
    }
    return [
        issue_map[check["name"]]
        for check in checks
        if check.get("passed") is not True and check.get("name") in issue_map
    ]


def next_actions(issues: list[str], metric_id: str) -> list[dict[str, Any]]:
    actions = []
    if "metric_not_certified" in issues or "metric_lifecycle_invalid" in issues:
        actions.append({"priority": "P0", "action": "complete_metric_certification_workflow", "owner": "enterprise-reporting-team"})
    if "metric_certification_missing" in issues:
        actions.append({"priority": "P0", "action": "attach_metric_certification_report", "owner": "enterprise-reporting-team"})
    if "semantic_view_missing" in issues:
        actions.append({"priority": "P0", "action": "regenerate_semantic_view_manifest", "owner": "enterprise-reporting-team"})
    if any(issue.startswith("serving_deployment") for issue in issues):
        actions.append({"priority": "P0", "action": "deploy_and_smoke_test_semantic_views", "owner": "data-platform-team"})
    if any(issue.startswith("usage_tracking") for issue in issues):
        actions.append({"priority": "P0", "action": "enable_bi_metric_usage_tracking", "owner": "enterprise-reporting-team"})
    return actions or [{"priority": "P3", "action": "no_action", "owner": metric_id}]


def semantic_serving_summary(
    rows: list[dict[str, Any]],
    failed_global_checks: list[dict[str, Any]],
    certification_ref: dict[str, Any],
    deployment_ref: dict[str, Any],
    usage_ref: dict[str, Any],
) -> dict[str, Any]:
    failed_metrics = [row for row in rows if row.get("passed") is not True]
    return {
        "metric_count": len(rows),
        "failed_metric_count": len(failed_metrics),
        "global_failed_check_count": len(failed_global_checks),
        "certified_metric_count": sum(1 for row in rows if row.get("status") == "certified"),
        "provisional_metric_count": sum(1 for row in rows if row.get("status") == "provisional"),
        "certification_evidence_attached": certification_ref.get("attached") is True,
        "certification_evidence_source": certification_ref.get("source"),
        "certification_approved_metric_count": sum(
            1
            for row in rows
            if mapping(row, "certification").get("status") == "approved"
        ),
        "metric_certification_gap_count": sum(
            1
            for row in rows
            if "metric_certification_missing" in row.get("issues", [])
        ),
        "semantic_view_count": sum(int_value(row.get("view_count")) for row in rows),
        "deployment_evidence_attached": deployment_ref.get("attached") is True,
        "usage_evidence_attached": usage_ref.get("attached") is True,
        "serving_deployment_failed_count": sum(1 for row in rows if "serving_deployment_failed" in row.get("issues", [])),
        "usage_tracking_gap_count": sum(
            1
            for row in rows
            if "usage_tracking_missing" in row.get("issues", []) or "usage_tracking_disabled" in row.get("issues", [])
        ),
        "by_status": count_by(rows, "status"),
        "by_risk_state": count_by(rows, "risk_state"),
    }


def manifest_views_by_metric(manifest: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    rows = manifest.get("views") if isinstance(manifest, dict) else None
    index: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(rows, list):
        return index
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("metric_id"), str):
            index.setdefault(row["metric_id"], []).append(row)
    return index


def deployment_views_by_metric(report: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    rows = report.get("views") if isinstance(report, dict) else None
    index: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(rows, list):
        return index
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("metric_id"), str):
            index.setdefault(row["metric_id"], []).append(row)
    return index


def usage_by_metric(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    rows = report.get("metrics") if isinstance(report, dict) else None
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("metric_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("metric_id")
    }


def usage_summary(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"attached": False}
    return {
        "attached": True,
        "usage_tracking_enabled": row.get("usage_tracking_enabled"),
        "active_consumer_count": row.get("active_consumer_count"),
        "last_queried_at": row.get("last_queried_at"),
    }


def certification_summary_row(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"attached": False}
    certification = mapping(row, "certification")
    return {
        "attached": certification.get("attached") is True,
        "certification_id": certification.get("certification_id"),
        "status": certification.get("status"),
        "approved_by": certification.get("approved_by"),
        "approved_at": certification.get("approved_at"),
        "approver_role": certification.get("approver_role"),
        "definition_hash": row.get("definition_hash"),
        "issues": row.get("issues", []),
    }


def compact_metric_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "metric_id": row.get("metric_id"),
        "status": row.get("status"),
        "risk_state": row.get("risk_state"),
        "issues": row.get("issues", []),
        "next_actions": row.get("next_actions", []),
    }


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "passed": passed, "details": details}


def mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    return value if isinstance(value, dict) else {}


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
