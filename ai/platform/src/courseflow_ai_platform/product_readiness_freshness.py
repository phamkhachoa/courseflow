from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.ai_module_catalog import build_ai_module_catalog_report
from courseflow_ai_platform.model_audit import ModelAuditLedger
from courseflow_ai_platform.registry import load_yaml

REPORT_ID = "ai-platform-product-readiness-freshness-v1"
PRODUCT_READINESS_REPORT_ID = "ai-platform-product-readiness-v1"
ROUTE_PATH = "/v1/model-serving/product-readiness"
ROUTE = ("GET", ROUTE_PATH)
PROBE_MODEL_ID = "operations-demand-forecast-baseline-v1"
PROBE_REQUEST_ID = "req-product-readiness-freshness-0001"

ALIGNMENT_FIELDS = (
    "readiness_status",
    "required_gate_count",
    "passed_required_gate_count",
    "failed_required_gate_count",
    "action_required_count",
)


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessCheck:
    check_id: str
    check_status: str
    reason: str
    evidence_refs: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.check_status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkId": self.check_id,
            "evidenceRefs": list(self.evidence_refs),
            "reason": self.reason,
            "status": self.check_status,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "status": self.check_status,
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class AiPlatformProductReadinessFreshnessReport:
    generated_at: str
    freshness_status: str
    route_path: str
    route_registered: bool
    runtime_status_code: int
    runtime_report_id: str
    runtime_generated_at: str
    runtime_readiness_status: str
    static_snapshot_status: str
    static_report_id: str
    static_generated_at: str
    static_readiness_status: str
    required_spectrum_count: int
    covered_required_spectrum_count: int
    extended_module_count: int
    runtime_serving_metrics_connected: bool
    runtime_serving_request_count: int
    runtime_serving_audit_record_count: int
    runtime_serving_error_count: int
    runtime_serving_audit_failure_count: int
    failed_check_count: int
    checks: tuple[ProductReadinessFreshnessCheck, ...]
    source_reports: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [check.to_dict() for check in self.checks],
            "coveredRequiredSpectrumCount": self.covered_required_spectrum_count,
            "extendedModuleCount": self.extended_module_count,
            "failedCheckCount": self.failed_check_count,
            "freshnessStatus": self.freshness_status,
            "generatedAt": self.generated_at,
            "requiredSpectrumCount": self.required_spectrum_count,
            "routePath": self.route_path,
            "routeRegistered": self.route_registered,
            "runtimeGeneratedAt": self.runtime_generated_at,
            "runtimeReadinessStatus": self.runtime_readiness_status,
            "runtimeReportId": self.runtime_report_id,
            "runtimeServingAuditFailureCount": (
                self.runtime_serving_audit_failure_count
            ),
            "runtimeServingAuditRecordCount": self.runtime_serving_audit_record_count,
            "runtimeServingErrorCount": self.runtime_serving_error_count,
            "runtimeServingMetricsConnected": (
                self.runtime_serving_metrics_connected
            ),
            "runtimeServingRequestCount": self.runtime_serving_request_count,
            "runtimeStatusCode": self.runtime_status_code,
            "sourceReports": list(self.source_reports),
            "staticGeneratedAt": self.static_generated_at,
            "staticReadinessStatus": self.static_readiness_status,
            "staticReportId": self.static_report_id,
            "staticSnapshotStatus": self.static_snapshot_status,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "route": {
                "path": self.route_path,
                "registered": self.route_registered,
                "runtime_status_code": self.runtime_status_code,
            },
            "summary": {
                "freshness_status": self.freshness_status,
                "static_snapshot_status": self.static_snapshot_status,
                "runtime_report_id": self.runtime_report_id,
                "runtime_generated_at": self.runtime_generated_at,
                "runtime_readiness_status": self.runtime_readiness_status,
                "static_report_id": self.static_report_id,
                "static_generated_at": self.static_generated_at,
                "static_readiness_status": self.static_readiness_status,
                "required_spectrum_count": self.required_spectrum_count,
                "covered_required_spectrum_count": (
                    self.covered_required_spectrum_count
                ),
                "extended_module_count": self.extended_module_count,
                "runtime_serving_metrics_connected": (
                    self.runtime_serving_metrics_connected
                ),
                "runtime_serving_request_count": (
                    self.runtime_serving_request_count
                ),
                "runtime_serving_audit_record_count": (
                    self.runtime_serving_audit_record_count
                ),
                "runtime_serving_error_count": self.runtime_serving_error_count,
                "runtime_serving_audit_failure_count": (
                    self.runtime_serving_audit_failure_count
                ),
                "failed_check_count": self.failed_check_count,
            },
            "source_reports": list(self.source_reports),
            "checks": [check.to_snapshot_dict() for check in self.checks],
        }


def load_ai_platform_product_readiness_freshness_report(
    ai_root: Path | str,
) -> AiPlatformProductReadinessFreshnessReport | None:
    path = default_report_path(Path(ai_root))
    if not path.exists():
        return None
    return ai_platform_product_readiness_freshness_report_from_snapshot(load_yaml(path))


def ai_platform_product_readiness_freshness_report_from_snapshot(
    row: dict[str, Any],
) -> AiPlatformProductReadinessFreshnessReport:
    route = mapping_or_empty(row.get("route"))
    summary = mapping_or_empty(row.get("summary"))
    return AiPlatformProductReadinessFreshnessReport(
        generated_at=normalized_string(row.get("generated_at")),
        freshness_status=normalized_string(summary.get("freshness_status")),
        route_path=normalized_string(route.get("path")),
        route_registered=bool(route.get("registered")),
        runtime_status_code=non_negative_int(route.get("runtime_status_code")),
        runtime_report_id=normalized_string(summary.get("runtime_report_id")),
        runtime_generated_at=normalized_string(summary.get("runtime_generated_at")),
        runtime_readiness_status=normalized_string(
            summary.get("runtime_readiness_status")
        ),
        static_snapshot_status=normalized_string(summary.get("static_snapshot_status")),
        static_report_id=normalized_string(summary.get("static_report_id")),
        static_generated_at=normalized_string(summary.get("static_generated_at")),
        static_readiness_status=normalized_string(
            summary.get("static_readiness_status")
        ),
        required_spectrum_count=non_negative_int(
            summary.get("required_spectrum_count")
        ),
        covered_required_spectrum_count=non_negative_int(
            summary.get("covered_required_spectrum_count")
        ),
        extended_module_count=non_negative_int(summary.get("extended_module_count")),
        runtime_serving_metrics_connected=bool(
            summary.get("runtime_serving_metrics_connected")
        ),
        runtime_serving_request_count=non_negative_int(
            summary.get("runtime_serving_request_count")
        ),
        runtime_serving_audit_record_count=non_negative_int(
            summary.get("runtime_serving_audit_record_count")
        ),
        runtime_serving_error_count=non_negative_int(
            summary.get("runtime_serving_error_count")
        ),
        runtime_serving_audit_failure_count=non_negative_int(
            summary.get("runtime_serving_audit_failure_count")
        ),
        failed_check_count=non_negative_int(summary.get("failed_check_count")),
        checks=tuple(
            product_readiness_freshness_check_from_snapshot(check)
            for check in row.get("checks", ())
            if isinstance(check, dict)
        ),
        source_reports=tuple(
            source
            for source in row.get("source_reports", ())
            if isinstance(source, str) and source
        ),
    )


def product_readiness_freshness_check_from_snapshot(
    row: dict[str, Any],
) -> ProductReadinessFreshnessCheck:
    return ProductReadinessFreshnessCheck(
        check_id=normalized_string(row.get("check_id")),
        check_status=normalized_string(row.get("status")),
        reason=normalized_string(row.get("reason")),
        evidence_refs=tuple(
            ref
            for ref in row.get("evidence_refs", ())
            if isinstance(ref, str) and ref
        ),
    )


def build_ai_platform_product_readiness_freshness_report(
    ai_root: Path | str,
    *,
    generated_at: str | date | None = None,
) -> AiPlatformProductReadinessFreshnessReport:
    from courseflow_ai_platform.model_serving_adapter import (
        MODEL_SERVING_ADAPTER_ROUTES,
        ModelServingHostedAdapter,
    )

    root = Path(ai_root)
    report_date = parse_report_date(generated_at).isoformat()
    static_snapshot_path = default_product_readiness_report_path(root)
    static_snapshot = (
        load_yaml(static_snapshot_path) if static_snapshot_path.exists() else {}
    )
    static_summary = mapping_or_empty(static_snapshot.get("summary"))
    static_report_id = normalized_string(static_snapshot.get("report_id"))
    static_generated_at = normalized_string(static_snapshot.get("generated_at"))
    static_snapshot_status = derive_static_snapshot_status(
        present=static_snapshot_path.exists(),
        report_id=static_report_id,
        generated_at=static_generated_at,
        expected_generated_at=report_date,
    )

    catalog = build_ai_module_catalog_report(root)
    adapter = ModelServingHostedAdapter(root, audit_store=ModelAuditLedger())
    invocation_response = adapter.handle_request(
        "POST",
        "/v1/model-invocations",
        product_readiness_probe_body(),
    )
    runtime_response = adapter.product_readiness(generated_at=report_date)
    runtime_summary = mapping_or_empty(runtime_response.body.get("summary"))

    runtime_report_id = normalized_string(runtime_response.body.get("report_id"))
    runtime_generated_at = normalized_string(runtime_response.body.get("generated_at"))
    runtime_readiness_status = normalized_string(runtime_summary.get("readiness_status"))
    static_readiness_status = normalized_string(static_summary.get("readiness_status"))
    route_registered = ROUTE in MODEL_SERVING_ADAPTER_ROUTES
    runtime_request_count = non_negative_int(
        runtime_summary.get("serving_request_count")
    )
    runtime_audit_record_count = non_negative_int(
        runtime_summary.get("serving_audit_record_count")
    )
    runtime_error_count = non_negative_int(runtime_summary.get("serving_error_count"))
    runtime_audit_failure_count = non_negative_int(
        runtime_summary.get("serving_audit_failure_count")
    )
    runtime_metrics_connected = bool(
        runtime_summary.get("serving_metrics_connected")
    )

    checks = (
        build_check(
            check_id="static_snapshot_current",
            passed=static_snapshot_status == "current",
            reason=(
                "Checked-in product readiness snapshot is current."
                if static_snapshot_status == "current"
                else f"Static snapshot status is {static_snapshot_status}."
            ),
            evidence_refs=("platform/product/reports/ai-platform-product-readiness-v1.yaml",),
        ),
        build_check(
            check_id="runtime_route_reachable",
            passed=(
                route_registered
                and invocation_response.status_code == 200
                and runtime_response.status_code == 200
                and runtime_report_id == PRODUCT_READINESS_REPORT_ID
                and runtime_generated_at == report_date
            ),
            reason=(
                f"{ROUTE_PATH} returned {runtime_response.status_code} after "
                f"probe invocation {invocation_response.status_code}."
            ),
            evidence_refs=(
                "platform/src/courseflow_ai_platform/model_serving_adapter.py",
                "services/model-serving-service/service.yaml",
            ),
        ),
        build_check(
            check_id="runtime_serving_metrics_live",
            passed=(
                runtime_metrics_connected
                and runtime_request_count >= 1
                and runtime_audit_record_count >= runtime_request_count
                and runtime_error_count == 0
                and runtime_audit_failure_count == 0
            ),
            reason=(
                f"{runtime_request_count} runtime requests, "
                f"{runtime_audit_record_count} audit records, "
                f"{runtime_error_count} errors and "
                f"{runtime_audit_failure_count} audit failures."
            ),
            evidence_refs=(
                "platform/src/courseflow_ai_platform/model_audit.py",
                "platform/src/courseflow_ai_platform/model_serving.py",
            ),
        ),
        build_check(
            check_id="static_runtime_gate_alignment",
            passed=gate_alignment_matches(static_summary, runtime_summary),
            reason="Static and runtime readiness gate summaries align.",
            evidence_refs=(
                "platform/product/reports/ai-platform-product-readiness-v1.yaml",
                "platform/src/courseflow_ai_platform/product_readiness.py",
            ),
        ),
        build_check(
            check_id="required_ai_spectrum_runtime_ready",
            passed=(
                catalog.required_spectrum_covered_count
                == catalog.required_spectrum_count
                and catalog.platform_readiness_status == "runtime_ready"
                and not catalog.first_runtime_candidate_ids
            ),
            reason=(
                f"{catalog.required_spectrum_covered_count}/"
                f"{catalog.required_spectrum_count} required spectrum areas "
                f"covered; {catalog.extended_module_count} extended modules."
            ),
            evidence_refs=(
                "platform/coverage/reports/ai-module-catalog-v1.yaml",
                "platform/coverage/reports/ai-capability-taxonomy-v1.yaml",
            ),
        ),
    )
    failed_check_count = sum(1 for check in checks if not check.passed)
    return AiPlatformProductReadinessFreshnessReport(
        generated_at=report_date,
        freshness_status=derive_freshness_status(
            failed_check_count=failed_check_count,
            route_registered=route_registered,
            runtime_status_code=runtime_response.status_code,
            static_snapshot_status=static_snapshot_status,
        ),
        route_path=ROUTE_PATH,
        route_registered=route_registered,
        runtime_status_code=runtime_response.status_code,
        runtime_report_id=runtime_report_id,
        runtime_generated_at=runtime_generated_at,
        runtime_readiness_status=runtime_readiness_status,
        static_snapshot_status=static_snapshot_status,
        static_report_id=static_report_id,
        static_generated_at=static_generated_at,
        static_readiness_status=static_readiness_status,
        required_spectrum_count=catalog.required_spectrum_count,
        covered_required_spectrum_count=catalog.required_spectrum_covered_count,
        extended_module_count=catalog.extended_module_count,
        runtime_serving_metrics_connected=runtime_metrics_connected,
        runtime_serving_request_count=runtime_request_count,
        runtime_serving_audit_record_count=runtime_audit_record_count,
        runtime_serving_error_count=runtime_error_count,
        runtime_serving_audit_failure_count=runtime_audit_failure_count,
        failed_check_count=failed_check_count,
        checks=checks,
        source_reports=(
            "platform/product/reports/ai-platform-product-readiness-v1.yaml",
            "platform/coverage/reports/ai-module-catalog-v1.yaml",
            "platform/coverage/reports/ai-capability-taxonomy-v1.yaml",
            "services/model-serving-service/service.yaml",
        ),
    )


def build_ai_platform_product_readiness_freshness_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | date | None = None,
    report: AiPlatformProductReadinessFreshnessReport | None = None,
) -> dict[str, Any]:
    freshness_report = report or build_ai_platform_product_readiness_freshness_report(
        ai_root,
        generated_at=generated_at,
    )
    return freshness_report.to_snapshot_dict()


def write_ai_platform_product_readiness_freshness_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | date | None = None,
    report: AiPlatformProductReadinessFreshnessReport | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path else default_report_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_ai_platform_product_readiness_freshness_snapshot(
        root,
        generated_at=generated_at,
        report=report,
    )
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            snapshot,
            handle,
            sort_keys=False,
            allow_unicode=False,
        )
    return target


def product_readiness_probe_body() -> dict[str, Any]:
    return {
        "requestId": PROBE_REQUEST_ID,
        "tenantId": "tenant-ops",
        "modelId": PROBE_MODEL_ID,
        "payload": {
            "tenant_id": "tenant-ops",
            "forecast_id": "fc-product-readiness-freshness",
            "queue_id": "support-identity",
            "historical_demand": [78, 82, 84, 96, 114, 132],
            "planned_capacity": 110,
            "backlog_open_items": 28,
            "avg_handle_minutes": 52,
            "seasonal_index": 1.08,
            "special_event": True,
            "incident_open": True,
            "forecast_horizon_days": 7,
            "service_level_target": 0.92,
        },
    }


def build_check(
    *,
    check_id: str,
    passed: bool,
    reason: str,
    evidence_refs: tuple[str, ...],
) -> ProductReadinessFreshnessCheck:
    return ProductReadinessFreshnessCheck(
        check_id=check_id,
        check_status="passed" if passed else "failed",
        reason=reason,
        evidence_refs=evidence_refs,
    )


def derive_static_snapshot_status(
    *,
    present: bool,
    report_id: str,
    generated_at: str,
    expected_generated_at: str,
) -> str:
    if not present:
        return "missing"
    if report_id != PRODUCT_READINESS_REPORT_ID:
        return "invalid_report"
    if generated_at != expected_generated_at:
        return "stale"
    return "current"


def derive_freshness_status(
    *,
    failed_check_count: int,
    route_registered: bool,
    runtime_status_code: int,
    static_snapshot_status: str,
) -> str:
    if failed_check_count == 0:
        return "current"
    if not route_registered or runtime_status_code != 200:
        return "route_unreachable"
    if static_snapshot_status != "current":
        return "static_snapshot_stale"
    return "attention_required"


def gate_alignment_matches(
    static_summary: dict[str, Any],
    runtime_summary: dict[str, Any],
) -> bool:
    return all(
        normalized_string(static_summary.get(field))
        == normalized_string(runtime_summary.get(field))
        for field in ALIGNMENT_FIELDS
    )


def mapping_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def normalized_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def default_report_path(root: Path) -> Path:
    return root / "platform" / "product" / "reports" / f"{REPORT_ID}.yaml"


def default_product_readiness_report_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "product"
        / "reports"
        / f"{PRODUCT_READINESS_REPORT_ID}.yaml"
    )


def parse_report_date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)
