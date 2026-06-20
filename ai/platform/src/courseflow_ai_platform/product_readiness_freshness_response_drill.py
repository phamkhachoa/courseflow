from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.product_readiness_freshness import (
    AiPlatformProductReadinessFreshnessReport,
    ProductReadinessFreshnessCheck,
    load_ai_platform_product_readiness_freshness_report,
)
from courseflow_ai_platform.product_readiness_freshness_incidents import (
    ProductReadinessFreshnessIncident,
    ProductReadinessFreshnessIncidentExport,
    build_product_readiness_freshness_incident_export,
    build_product_readiness_freshness_incident_export_from_report,
)

REPORT_ID = "product-readiness-freshness-incident-response-drill-v1"
RUNBOOK_ID = "product-readiness-freshness-incident-response-v1"
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-", "api_key")


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseDrillScenario:
    scenario_id: str
    condition: str
    expected_severity: str
    expected_owner_role: str
    expected_action: str
    observed_severity: str
    observed_owner_role: str
    observed_action: str
    incident_status: str
    incident_id: str
    application_ref: str
    runbook_step_ids: tuple[str, ...]
    passed: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "applicationRef": self.application_ref,
            "condition": self.condition,
            "evidenceRefs": list(self.evidence_refs),
            "expectedAction": self.expected_action,
            "expectedOwnerRole": self.expected_owner_role,
            "expectedSeverity": self.expected_severity,
            "incidentId": self.incident_id,
            "incidentStatus": self.incident_status,
            "observedAction": self.observed_action,
            "observedOwnerRole": self.observed_owner_role,
            "observedSeverity": self.observed_severity,
            "passed": self.passed,
            "runbookStepIds": list(self.runbook_step_ids),
            "scenarioId": self.scenario_id,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "condition": self.condition,
            "expected_severity": self.expected_severity,
            "expected_owner_role": self.expected_owner_role,
            "expected_action": self.expected_action,
            "observed_severity": self.observed_severity,
            "observed_owner_role": self.observed_owner_role,
            "observed_action": self.observed_action,
            "incident_status": self.incident_status,
            "incident_id": self.incident_id,
            "application_ref": self.application_ref,
            "runbook_step_ids": list(self.runbook_step_ids),
            "passed": self.passed,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessIncidentResponseDrillReport:
    generated_at: str
    drill_status: str
    runbook_id: str
    runbook_path: str
    human_runbook_path: str
    response_step_count: int
    scenario_count: int
    passed_count: int
    failed_count: int
    p0_scenario_count: int
    p1_scenario_count: int
    current_incident_count: int
    current_open_incident_count: int
    tenant_safe: bool
    raw_identifier_count: int
    omitted_sensitive_fields: tuple[str, ...]
    next_actions: tuple[str, ...]
    scenarios: tuple[ProductReadinessFreshnessResponseDrillScenario, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "currentIncidentCount": self.current_incident_count,
            "currentOpenIncidentCount": self.current_open_incident_count,
            "drillStatus": self.drill_status,
            "failedCount": self.failed_count,
            "generatedAt": self.generated_at,
            "humanRunbookPath": self.human_runbook_path,
            "nextActions": list(self.next_actions),
            "omittedSensitiveFields": list(self.omitted_sensitive_fields),
            "p0ScenarioCount": self.p0_scenario_count,
            "p1ScenarioCount": self.p1_scenario_count,
            "passedCount": self.passed_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "responseStepCount": self.response_step_count,
            "runbookId": self.runbook_id,
            "runbookPath": self.runbook_path,
            "scenarioCount": self.scenario_count,
            "scenarios": [scenario.to_dict() for scenario in self.scenarios],
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "runbook_id": self.runbook_id,
            "runbook_path": self.runbook_path,
            "human_runbook_path": self.human_runbook_path,
            "summary": {
                "drill_status": self.drill_status,
                "response_step_count": self.response_step_count,
                "scenario_count": self.scenario_count,
                "passed_count": self.passed_count,
                "failed_count": self.failed_count,
                "p0_scenario_count": self.p0_scenario_count,
                "p1_scenario_count": self.p1_scenario_count,
                "current_incident_count": self.current_incident_count,
                "current_open_incident_count": self.current_open_incident_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
                "omitted_sensitive_fields": list(self.omitted_sensitive_fields),
            },
            "next_actions": list(self.next_actions),
            "scenarios": [scenario.to_snapshot_dict() for scenario in self.scenarios],
        }


def build_product_readiness_freshness_incident_response_drill_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessIncidentResponseDrillReport:
    root = Path(ai_root)
    report_date = generated_at or date.today().isoformat()
    runbook = load_runbook_spec(default_runbook_spec_path(root))
    current_export = build_product_readiness_freshness_incident_export(
        root,
        as_of=report_date,
    )
    current_freshness_report = load_ai_platform_product_readiness_freshness_report(root)
    return build_product_readiness_freshness_incident_response_drill_report_from_spec(
        runbook,
        current_export=current_export,
        current_freshness_report=current_freshness_report,
        generated_at=report_date,
        root=root,
    )


def build_product_readiness_freshness_incident_response_drill_report_from_spec(
    runbook: dict[str, Any],
    *,
    current_export: ProductReadinessFreshnessIncidentExport,
    current_freshness_report: AiPlatformProductReadinessFreshnessReport | None,
    generated_at: str,
    root: Path | str | None = None,
) -> ProductReadinessFreshnessIncidentResponseDrillReport:
    root_path = Path(root) if root is not None else None
    runbook_id = normalized_string(runbook.get("runbook_id"), RUNBOOK_ID)
    step_ids = step_ids_from_runbook(runbook)
    expectations = expectations_from_runbook(runbook)
    scenarios = tuple(
        build_response_drill_scenario(
            expectation,
            runbook_step_ids=step_ids,
            generated_at=generated_at,
            base_report=current_freshness_report,
        )
        for expectation in expectations
    )
    raw_identifier_count = count_raw_identifier_markers(scenarios)
    tenant_safe = current_export.tenant_safe and raw_identifier_count == 0
    failed_count = sum(1 for scenario in scenarios if not scenario.passed)
    drill_status = "passed" if failed_count == 0 and tenant_safe else "blocked"
    return ProductReadinessFreshnessIncidentResponseDrillReport(
        generated_at=generated_at,
        drill_status=drill_status,
        runbook_id=runbook_id,
        runbook_path=relative_or_default(
            root_path,
            default_runbook_spec_path(root_path) if root_path is not None else None,
            "platform/operations/runbooks/product-readiness-freshness-incident-response-v1.yaml",
        ),
        human_runbook_path=relative_or_default(
            root_path,
            default_human_runbook_path(root_path) if root_path is not None else None,
            "runbooks/product-readiness-freshness-incident-response.md",
        ),
        response_step_count=len(step_ids),
        scenario_count=len(scenarios),
        passed_count=sum(1 for scenario in scenarios if scenario.passed),
        failed_count=failed_count,
        p0_scenario_count=sum(
            1 for scenario in scenarios if scenario.expected_severity == "p0"
        ),
        p1_scenario_count=sum(
            1 for scenario in scenarios if scenario.expected_severity == "p1"
        ),
        current_incident_count=current_export.incident_count,
        current_open_incident_count=current_export.open_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        omitted_sensitive_fields=(
            "tenant_ids",
            "principal_ids",
            "request_bodies",
            "credential_values",
            "raw_runtime_payloads",
        ),
        next_actions=tuple(
            str(action)
            for action in runbook.get("next_actions", ())
            if isinstance(action, str) and action.strip()
        ),
        scenarios=scenarios,
    )


def build_product_readiness_freshness_incident_response_drill_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_product_readiness_freshness_incident_response_drill_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_product_readiness_freshness_incident_response_drill_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_product_readiness_freshness_incident_response_drill_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


def build_response_drill_scenario(
    expectation: dict[str, Any],
    *,
    runbook_step_ids: tuple[str, ...],
    generated_at: str,
    base_report: AiPlatformProductReadinessFreshnessReport | None,
) -> ProductReadinessFreshnessResponseDrillScenario:
    condition = require_string(expectation, "condition", "scenario expectation")
    expected_severity = require_string(expectation, "severity", condition)
    expected_owner_role = require_string(expectation, "owner_role", condition)
    expected_action = require_string(expectation, "action", condition)
    required_steps = tuple(
        str(step)
        for step in expectation.get("required_steps", ())
        if isinstance(step, str) and step.strip()
    )
    incident = synthetic_incident_for_condition(
        condition,
        generated_at=generated_at,
        base_report=base_report,
    )
    validation_errors = list(
        validate_incident_against_expectation(
            incident,
            expected_severity=expected_severity,
            expected_owner_role=expected_owner_role,
            expected_action=expected_action,
            required_steps=required_steps,
            available_step_ids=runbook_step_ids,
        )
    )
    return ProductReadinessFreshnessResponseDrillScenario(
        scenario_id=normalized_string(
            expectation.get("scenario_id"),
            f"{condition}-response-drill",
        ),
        condition=condition,
        expected_severity=expected_severity,
        expected_owner_role=expected_owner_role,
        expected_action=expected_action,
        observed_severity=incident.severity if incident is not None else "",
        observed_owner_role=incident.owner_role if incident is not None else "",
        observed_action=incident.action if incident is not None else "",
        incident_status=incident.incident_status if incident is not None else "",
        incident_id=incident.incident_id if incident is not None else "",
        application_ref=incident.application_ref if incident is not None else "",
        runbook_step_ids=required_steps,
        passed=not validation_errors,
        validation_errors=tuple(validation_errors),
        evidence_refs=(
            "runbook:product-readiness-freshness-incident-response-v1",
            "report:product-readiness-freshness-incident-export-v1",
            "report:ai-platform-product-readiness-freshness-v1",
        ),
    )


def synthetic_incident_for_condition(
    condition: str,
    *,
    generated_at: str,
    base_report: AiPlatformProductReadinessFreshnessReport | None,
) -> ProductReadinessFreshnessIncident | None:
    report = synthetic_freshness_report_for_condition(
        condition,
        generated_at=generated_at,
        base_report=base_report,
    )
    export = build_product_readiness_freshness_incident_export_from_report(
        report,
        as_of=generated_at,
    )
    return export.incidents[0] if export.incidents else None


def synthetic_freshness_report_for_condition(
    condition: str,
    *,
    generated_at: str,
    base_report: AiPlatformProductReadinessFreshnessReport | None,
) -> AiPlatformProductReadinessFreshnessReport | None:
    if condition == "product_readiness_freshness_report_missing":
        return None
    report = base_report or default_freshness_report(generated_at)
    if condition == "product_readiness_freshness_report_stale":
        return replace(
            report,
            generated_at="2026-06-16",
            failed_check_count=max(1, report.failed_check_count),
        )
    if condition == "product_readiness_runtime_route_unreachable":
        return replace(
            report,
            freshness_status="route_unreachable",
            route_registered=False,
            runtime_status_code=503,
            failed_check_count=max(1, report.failed_check_count),
        )
    if condition == "product_readiness_static_snapshot_stale":
        return replace(
            report,
            freshness_status="static_snapshot_stale",
            static_snapshot_status="stale",
            static_generated_at="2026-06-16",
            failed_check_count=max(1, report.failed_check_count),
        )
    if condition == "product_readiness_runtime_error_or_audit_failure":
        return replace(
            report,
            runtime_serving_error_count=1,
            runtime_serving_audit_failure_count=1,
            failed_check_count=max(1, report.failed_check_count),
        )
    if condition == "product_readiness_runtime_audit_gap":
        return replace(
            report,
            runtime_serving_request_count=max(2, report.runtime_serving_request_count),
            runtime_serving_audit_record_count=1,
            failed_check_count=max(1, report.failed_check_count),
        )
    return replace(
        report,
        failed_check_count=max(1, report.failed_check_count),
    )


def default_freshness_report(generated_at: str) -> AiPlatformProductReadinessFreshnessReport:
    return AiPlatformProductReadinessFreshnessReport(
        generated_at=generated_at,
        freshness_status="current",
        route_path="/v1/model-serving/product-readiness",
        route_registered=True,
        runtime_status_code=200,
        runtime_report_id="ai-platform-product-readiness-v1",
        runtime_generated_at=generated_at,
        runtime_readiness_status="stakeholder_ready_with_followups",
        static_snapshot_status="current",
        static_report_id="ai-platform-product-readiness-v1",
        static_generated_at=generated_at,
        static_readiness_status="stakeholder_ready_with_followups",
        required_spectrum_count=8,
        covered_required_spectrum_count=8,
        extended_module_count=6,
        runtime_serving_metrics_connected=True,
        runtime_serving_request_count=1,
        runtime_serving_audit_record_count=1,
        runtime_serving_error_count=0,
        runtime_serving_audit_failure_count=0,
        failed_check_count=0,
        checks=(
            ProductReadinessFreshnessCheck(
                check_id="synthetic_product_readiness_freshness",
                check_status="passed",
                reason="Synthetic drill baseline is current.",
                evidence_refs=(
                    "platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml",
                ),
            ),
        ),
        source_reports=(
            "platform/product/reports/ai-platform-product-readiness-v1.yaml",
            "platform/product/reports/ai-platform-product-readiness-freshness-v1.yaml",
        ),
    )


def validate_incident_against_expectation(
    incident: ProductReadinessFreshnessIncident | None,
    *,
    expected_severity: str,
    expected_owner_role: str,
    expected_action: str,
    required_steps: tuple[str, ...],
    available_step_ids: tuple[str, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    if incident is None:
        return ("expected product-readiness freshness incident was not produced",)
    if incident.incident_status != "open":
        errors.append("incident must be open for response drill")
    if incident.severity != expected_severity:
        errors.append(
            f"expected severity {expected_severity}, observed {incident.severity}"
        )
    if incident.owner_role != expected_owner_role:
        errors.append(
            f"expected owner {expected_owner_role}, observed {incident.owner_role}"
        )
    if incident.action != expected_action:
        errors.append(f"expected action {expected_action}, observed {incident.action}")
    if not incident.application_ref.startswith("product-readiness:"):
        errors.append("incident application_ref must use product-readiness hash ref")
    missing_steps = sorted(set(required_steps) - set(available_step_ids))
    if missing_steps:
        errors.append("runbook missing required steps: " + ", ".join(missing_steps))
    if len(required_steps) < 5:
        errors.append("scenario must require at least five response steps")
    return tuple(errors)


def expectations_from_runbook(runbook: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    raw_expectations = runbook.get("scenario_expectations")
    if not isinstance(raw_expectations, list):
        return ()
    return tuple(
        expectation
        for expectation in raw_expectations
        if isinstance(expectation, dict)
    )


def step_ids_from_runbook(runbook: dict[str, Any]) -> tuple[str, ...]:
    raw_steps = runbook.get("required_steps")
    if not isinstance(raw_steps, list):
        return ()
    return tuple(
        require_string(step, "step_id", "runbook step")
        for step in raw_steps
        if isinstance(step, dict)
    )


def load_runbook_spec(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        return {}
    return payload


def require_string(row: dict[str, Any], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{owner} must define non-empty string field {key}")
    return value.strip()


def normalized_string(value: Any, default: str) -> str:
    if not isinstance(value, str) or not value.strip():
        return default
    return value.strip()


def count_raw_identifier_markers(
    scenarios: tuple[ProductReadinessFreshnessResponseDrillScenario, ...],
) -> int:
    payload = json.dumps(
        [scenario.to_snapshot_dict() for scenario in scenarios],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    return sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def relative_or_default(
    root: Path | None,
    path: Path | None,
    default: str,
) -> str:
    if root is None or path is None:
        return default
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def default_runbook_spec_path(root: Path | None) -> Path:
    if root is None:
        return Path(
            "platform/operations/runbooks/product-readiness-freshness-incident-response-v1.yaml"
        )
    return (
        root
        / "platform"
        / "operations"
        / "runbooks"
        / "product-readiness-freshness-incident-response-v1.yaml"
    )


def default_human_runbook_path(root: Path | None) -> Path:
    if root is None:
        return Path("runbooks/product-readiness-freshness-incident-response.md")
    return root / "runbooks" / "product-readiness-freshness-incident-response.md"


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
