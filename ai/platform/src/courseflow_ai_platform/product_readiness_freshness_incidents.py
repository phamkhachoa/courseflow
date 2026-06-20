from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.product_readiness_freshness import (
    AiPlatformProductReadinessFreshnessReport,
    load_ai_platform_product_readiness_freshness_report,
)

REPORT_ID = "product-readiness-freshness-incident-export-v1"
DEFAULT_STALE_THRESHOLD_DAYS = 1
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-", "api_key")
EVIDENCE_REFS = (
    "platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml",
    "platform/product/reports/ai-platform-product-readiness-v1.yaml",
    "platform/operations/reports/admin-ops-dashboard-v1.html",
    "platform/operations/reports/admin-ops-dashboard-freshness-v1.yaml",
)


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessIncident:
    incident_id: str
    condition: str
    severity: str
    incident_status: str
    owner_role: str
    action: str
    application_ref: str
    freshness_status: str
    route_path: str
    runtime_status_code: int
    failed_check_count: int
    runtime_request_count: int
    runtime_audit_record_count: int
    runtime_error_count: int
    runtime_audit_failure_count: int
    age_days: int | None
    stale_threshold_days: int
    evidence_refs: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "ageDays": self.age_days,
            "applicationRef": self.application_ref,
            "condition": self.condition,
            "evidenceRefs": list(self.evidence_refs),
            "failedCheckCount": self.failed_check_count,
            "freshnessStatus": self.freshness_status,
            "incidentId": self.incident_id,
            "ownerRole": self.owner_role,
            "reason": self.reason,
            "routePath": self.route_path,
            "runtimeAuditFailureCount": self.runtime_audit_failure_count,
            "runtimeAuditRecordCount": self.runtime_audit_record_count,
            "runtimeErrorCount": self.runtime_error_count,
            "runtimeRequestCount": self.runtime_request_count,
            "runtimeStatusCode": self.runtime_status_code,
            "severity": self.severity,
            "staleThresholdDays": self.stale_threshold_days,
            "status": self.incident_status,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "condition": self.condition,
            "severity": self.severity,
            "status": self.incident_status,
            "owner_role": self.owner_role,
            "action": self.action,
            "application_ref": self.application_ref,
            "freshness_status": self.freshness_status,
            "route_path": self.route_path,
            "runtime_status_code": self.runtime_status_code,
            "failed_check_count": self.failed_check_count,
            "runtime_request_count": self.runtime_request_count,
            "runtime_audit_record_count": self.runtime_audit_record_count,
            "runtime_error_count": self.runtime_error_count,
            "runtime_audit_failure_count": self.runtime_audit_failure_count,
            "age_days": self.age_days,
            "stale_threshold_days": self.stale_threshold_days,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessIncidentExport:
    as_of: date
    freshness_status: str
    stale_threshold_days: int
    incident_count: int
    open_count: int
    watch_count: int
    p0_count: int
    p1_count: int
    p2_count: int
    tenant_safe: bool
    raw_identifier_count: int
    omitted_sensitive_fields: tuple[str, ...]
    by_condition: dict[str, int]
    by_severity: dict[str, int]
    by_status: dict[str, int]
    action_queue: dict[str, list[str]]
    incidents: tuple[ProductReadinessFreshnessIncident, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "actionQueue": self.action_queue,
            "asOf": self.as_of.isoformat(),
            "byCondition": self.by_condition,
            "bySeverity": self.by_severity,
            "byStatus": self.by_status,
            "freshnessStatus": self.freshness_status,
            "incidentCount": self.incident_count,
            "incidents": [incident.to_dict() for incident in self.incidents],
            "omittedSensitiveFields": list(self.omitted_sensitive_fields),
            "openCount": self.open_count,
            "p0Count": self.p0_count,
            "p1Count": self.p1_count,
            "p2Count": self.p2_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "staleThresholdDays": self.stale_threshold_days,
            "tenantSafe": self.tenant_safe,
            "watchCount": self.watch_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "as_of": self.as_of.isoformat(),
                "freshness_status": self.freshness_status,
                "incident_count": self.incident_count,
                "open_count": self.open_count,
                "watch_count": self.watch_count,
                "p0_count": self.p0_count,
                "p1_count": self.p1_count,
                "p2_count": self.p2_count,
                "stale_threshold_days": self.stale_threshold_days,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
                "omitted_sensitive_fields": list(self.omitted_sensitive_fields),
            },
            "by_condition": self.by_condition,
            "by_severity": self.by_severity,
            "by_status": self.by_status,
            "action_queue": self.action_queue,
            "incidents": [incident.to_snapshot_dict() for incident in self.incidents],
        }


def build_product_readiness_freshness_incident_export(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
    stale_threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS,
) -> ProductReadinessFreshnessIncidentExport:
    report_date = parse_report_date(as_of)
    return build_product_readiness_freshness_incident_export_from_report(
        load_ai_platform_product_readiness_freshness_report(ai_root),
        as_of=report_date,
        stale_threshold_days=stale_threshold_days,
    )


def build_product_readiness_freshness_incident_export_from_report(
    report: AiPlatformProductReadinessFreshnessReport | None,
    *,
    as_of: str | date | None = None,
    stale_threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS,
) -> ProductReadinessFreshnessIncidentExport:
    report_date = parse_report_date(as_of)
    incidents = build_incidents(
        report,
        as_of=report_date,
        stale_threshold_days=stale_threshold_days,
    )
    raw_identifier_count = count_raw_identifier_markers(incidents)
    return ProductReadinessFreshnessIncidentExport(
        as_of=report_date,
        freshness_status=report.freshness_status if report is not None else "missing",
        stale_threshold_days=stale_threshold_days,
        incident_count=len(incidents),
        open_count=count_status(incidents, "open"),
        watch_count=count_status(incidents, "watch"),
        p0_count=count_severity(incidents, "p0"),
        p1_count=count_severity(incidents, "p1"),
        p2_count=count_severity(incidents, "p2"),
        tenant_safe=raw_identifier_count == 0,
        raw_identifier_count=raw_identifier_count,
        omitted_sensitive_fields=(
            "tenant_ids",
            "principal_ids",
            "request_bodies",
            "credential_values",
            "raw_runtime_payloads",
        ),
        by_condition=count_by(incidents, "condition"),
        by_severity=count_by(incidents, "severity"),
        by_status=count_by(incidents, "incident_status"),
        action_queue=build_action_queue(incidents),
        incidents=incidents,
    )


def build_product_readiness_freshness_incident_export_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    as_of: str | date | None = None,
    stale_threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_product_readiness_freshness_incident_export(
        ai_root,
        as_of=as_of or generated_at,
        stale_threshold_days=stale_threshold_days,
    ).to_snapshot_dict(generated_at=report_date)


def write_product_readiness_freshness_incident_export_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
    as_of: str | date | None = None,
    stale_threshold_days: int = DEFAULT_STALE_THRESHOLD_DAYS,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_product_readiness_freshness_incident_export_snapshot(
                root,
                generated_at=generated_at,
                as_of=as_of,
                stale_threshold_days=stale_threshold_days,
            ),
            handle,
            sort_keys=False,
        )
    return target


def build_incidents(
    report: AiPlatformProductReadinessFreshnessReport | None,
    *,
    as_of: date,
    stale_threshold_days: int,
) -> tuple[ProductReadinessFreshnessIncident, ...]:
    if report is None:
        return (
            build_incident(
                condition="product_readiness_freshness_report_missing",
                severity="p1",
                action="restore_product_readiness_freshness_report",
                freshness_status="missing",
                route_path="",
                runtime_status_code=0,
                failed_check_count=1,
                runtime_request_count=0,
                runtime_audit_record_count=0,
                runtime_error_count=0,
                runtime_audit_failure_count=0,
                age_days=None,
                stale_threshold_days=stale_threshold_days,
                reason="Product readiness freshness snapshot is missing.",
            ),
        )
    report_age_days = age_days(report.generated_at, as_of=as_of)
    if report_age_days is not None and report.generated_at != as_of.isoformat():
        return (
            incident_from_report(
                report,
                condition="product_readiness_freshness_report_stale",
                severity="p1",
                action="refresh_product_readiness_freshness_report",
                age_days=report_age_days,
                stale_threshold_days=stale_threshold_days,
                reason=(
                    "Product readiness freshness report date does not match the "
                    "current Admin/Ops reporting date."
                ),
            ),
        )
    if (
        not report.route_registered
        or report.runtime_status_code != 200
        or report.freshness_status == "route_unreachable"
    ):
        return (
            incident_from_report(
                report,
                condition="product_readiness_runtime_route_unreachable",
                severity="p0",
                action="triage_product_readiness_runtime_route",
                age_days=report_age_days,
                stale_threshold_days=stale_threshold_days,
                reason="Runtime product readiness route is unreachable or unhealthy.",
            ),
        )
    if (
        report.static_snapshot_status != "current"
        or report.freshness_status == "static_snapshot_stale"
    ):
        return (
            incident_from_report(
                report,
                condition="product_readiness_static_snapshot_stale",
                severity="p1",
                action="refresh_product_readiness_snapshots",
                age_days=age_days(report.static_generated_at, as_of=as_of),
                stale_threshold_days=stale_threshold_days,
                reason="Static product readiness snapshot is stale or invalid.",
            ),
        )
    if (
        report.runtime_serving_error_count > 0
        or report.runtime_serving_audit_failure_count > 0
    ):
        return (
            incident_from_report(
                report,
                condition="product_readiness_runtime_error_or_audit_failure",
                severity="p1",
                action="triage_product_readiness_runtime_metrics",
                age_days=report_age_days,
                stale_threshold_days=stale_threshold_days,
                reason="Runtime product readiness probe recorded serving errors or audit failures.",
            ),
        )
    if report.runtime_serving_audit_record_count < report.runtime_serving_request_count:
        return (
            incident_from_report(
                report,
                condition="product_readiness_runtime_audit_gap",
                severity="p1",
                action="restore_product_readiness_audit_coverage",
                age_days=report_age_days,
                stale_threshold_days=stale_threshold_days,
                reason="Runtime product readiness requests are not fully covered by audit records.",
            ),
        )
    if report.failed_check_count > 0:
        return (
            incident_from_report(
                report,
                condition="product_readiness_freshness_check_failed",
                severity="p1",
                action="inspect_product_readiness_freshness_checks",
                age_days=report_age_days,
                stale_threshold_days=stale_threshold_days,
                reason="Product readiness freshness report has failed checks.",
            ),
        )
    return ()


def incident_from_report(
    report: AiPlatformProductReadinessFreshnessReport,
    *,
    condition: str,
    severity: str,
    action: str,
    age_days: int | None,
    stale_threshold_days: int,
    reason: str,
) -> ProductReadinessFreshnessIncident:
    return build_incident(
        condition=condition,
        severity=severity,
        action=action,
        freshness_status=report.freshness_status,
        route_path=report.route_path,
        runtime_status_code=report.runtime_status_code,
        failed_check_count=report.failed_check_count,
        runtime_request_count=report.runtime_serving_request_count,
        runtime_audit_record_count=report.runtime_serving_audit_record_count,
        runtime_error_count=report.runtime_serving_error_count,
        runtime_audit_failure_count=report.runtime_serving_audit_failure_count,
        age_days=age_days,
        stale_threshold_days=stale_threshold_days,
        reason=reason,
    )


def build_incident(
    *,
    condition: str,
    severity: str,
    action: str,
    freshness_status: str,
    route_path: str,
    runtime_status_code: int,
    failed_check_count: int,
    runtime_request_count: int,
    runtime_audit_record_count: int,
    runtime_error_count: int,
    runtime_audit_failure_count: int,
    age_days: int | None,
    stale_threshold_days: int,
    reason: str,
) -> ProductReadinessFreshnessIncident:
    return ProductReadinessFreshnessIncident(
        incident_id=incident_id_for(condition),
        condition=condition,
        severity=severity,
        incident_status="open",
        owner_role="Admin/Ops",
        action=action,
        application_ref=application_ref_for(REPORT_ID),
        freshness_status=freshness_status,
        route_path=route_path,
        runtime_status_code=runtime_status_code,
        failed_check_count=failed_check_count,
        runtime_request_count=runtime_request_count,
        runtime_audit_record_count=runtime_audit_record_count,
        runtime_error_count=runtime_error_count,
        runtime_audit_failure_count=runtime_audit_failure_count,
        age_days=age_days,
        stale_threshold_days=stale_threshold_days,
        evidence_refs=EVIDENCE_REFS,
        reason=reason,
    )


def application_ref_for(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"product-readiness:{digest}"


def incident_id_for(condition: str) -> str:
    digest = hashlib.sha256(f"{REPORT_ID}:{condition}".encode()).hexdigest()[:16]
    return f"prf-{digest}-{condition.replace('_', '-')}"


def count_raw_identifier_markers(
    incidents: tuple[ProductReadinessFreshnessIncident, ...],
) -> int:
    payload = json.dumps(
        [incident.to_snapshot_dict() for incident in incidents],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def build_action_queue(
    incidents: tuple[ProductReadinessFreshnessIncident, ...],
) -> dict[str, list[str]]:
    queue = {
        "open": ids_for_status(incidents, "open"),
        "watch": ids_for_status(incidents, "watch"),
        "p0": ids_for_severity(incidents, "p0"),
        "p1": ids_for_severity(incidents, "p1"),
        "p2": ids_for_severity(incidents, "p2"),
    }
    for condition in (
        "product_readiness_freshness_report_missing",
        "product_readiness_freshness_report_stale",
        "product_readiness_runtime_route_unreachable",
        "product_readiness_static_snapshot_stale",
        "product_readiness_runtime_error_or_audit_failure",
        "product_readiness_runtime_audit_gap",
        "product_readiness_freshness_check_failed",
    ):
        queue[condition] = ids_for_condition(incidents, condition)
    return queue


def ids_for_status(
    incidents: tuple[ProductReadinessFreshnessIncident, ...],
    status: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.incident_status == status]


def ids_for_severity(
    incidents: tuple[ProductReadinessFreshnessIncident, ...],
    severity: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.severity == severity]


def ids_for_condition(
    incidents: tuple[ProductReadinessFreshnessIncident, ...],
    condition: str,
) -> list[str]:
    return [incident.incident_id for incident in incidents if incident.condition == condition]


def count_status(
    incidents: tuple[ProductReadinessFreshnessIncident, ...],
    status: str,
) -> int:
    return len(ids_for_status(incidents, status))


def count_severity(
    incidents: tuple[ProductReadinessFreshnessIncident, ...],
    severity: str,
) -> int:
    return len(ids_for_severity(incidents, severity))


def count_by(
    incidents: tuple[ProductReadinessFreshnessIncident, ...],
    attribute: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for incident in incidents:
        value = getattr(incident, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def age_days(value: str, *, as_of: date) -> int | None:
    try:
        return max(0, (as_of - date.fromisoformat(value[:10])).days)
    except ValueError:
        return None


def parse_report_date(value: str | date | None) -> date:
    if isinstance(value, date):
        return value
    if value is None:
        return date.today()
    return date.fromisoformat(value[:10])


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
