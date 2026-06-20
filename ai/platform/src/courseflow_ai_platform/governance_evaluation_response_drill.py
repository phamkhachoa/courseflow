from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.governance_evaluation_incidents import (
    GovernanceEvaluationAlertDrillEvent,
    GovernanceEvaluationIncident,
    GovernanceEvaluationIncidentExport,
    build_governance_evaluation_incident_export,
    build_governance_evaluation_incident_export_from_report,
)
from courseflow_ai_platform.governance_evaluation_ops import (
    GovernanceEvaluationDrillItem,
    GovernanceEvaluationOpsReport,
)

REPORT_ID = "governance-evaluation-incident-response-drill-v1"
RUNBOOK_ID = "governance-evaluation-incident-response-v1"
RAW_IDENTIFIER_MARKERS = ("tenant-", "service:", "token", "secret", "sk-")


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationResponseDrillScenario:
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
class GovernanceEvaluationIncidentResponseDrillReport:
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
    scenarios: tuple[GovernanceEvaluationResponseDrillScenario, ...]

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


def build_governance_evaluation_incident_response_drill_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> GovernanceEvaluationIncidentResponseDrillReport:
    root = Path(ai_root)
    report_date = generated_at or date.today().isoformat()
    runbook = load_runbook_spec(default_runbook_spec_path(root))
    current_export = build_governance_evaluation_incident_export(
        root,
        as_of=report_date,
    )
    return build_governance_evaluation_incident_response_drill_report_from_spec(
        runbook,
        current_export=current_export,
        generated_at=report_date,
        root=root,
    )


def build_governance_evaluation_incident_response_drill_report_from_spec(
    runbook: dict[str, Any],
    *,
    current_export: GovernanceEvaluationIncidentExport,
    generated_at: str,
    root: Path | str | None = None,
) -> GovernanceEvaluationIncidentResponseDrillReport:
    root_path = Path(root) if root is not None else None
    runbook_id = normalized_string(runbook.get("runbook_id"), RUNBOOK_ID)
    step_ids = step_ids_from_runbook(runbook)
    expectations = expectations_from_runbook(runbook)
    scenarios = tuple(
        build_response_drill_scenario(
            expectation,
            runbook_step_ids=step_ids,
            generated_at=generated_at,
        )
        for expectation in expectations
    )
    raw_identifier_count = count_raw_identifier_markers(scenarios)
    tenant_safe = current_export.tenant_safe and raw_identifier_count == 0
    failed_count = sum(1 for scenario in scenarios if not scenario.passed)
    drill_status = "passed" if failed_count == 0 and tenant_safe else "blocked"
    return GovernanceEvaluationIncidentResponseDrillReport(
        generated_at=generated_at,
        drill_status=drill_status,
        runbook_id=runbook_id,
        runbook_path=relative_or_default(
            root_path,
            default_runbook_spec_path(root_path) if root_path is not None else None,
            "platform/operations/runbooks/governance-evaluation-incident-response-v1.yaml",
        ),
        human_runbook_path=relative_or_default(
            root_path,
            default_human_runbook_path(root_path) if root_path is not None else None,
            "runbooks/governance-evaluation-incident-response.md",
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
            "principal_ids",
            "tenant_ids",
            "request_bodies",
            "credential_values",
            "raw_drill_payloads",
        ),
        next_actions=tuple(
            str(action)
            for action in runbook.get("next_actions", ())
            if isinstance(action, str) and action.strip()
        ),
        scenarios=scenarios,
    )


def build_governance_evaluation_incident_response_drill_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_governance_evaluation_incident_response_drill_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_governance_evaluation_incident_response_drill_snapshot(
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
            build_governance_evaluation_incident_response_drill_snapshot(
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
) -> GovernanceEvaluationResponseDrillScenario:
    condition = require_string(expectation, "condition", "scenario expectation")
    expected_severity = require_string(expectation, "severity", condition)
    expected_owner_role = require_string(expectation, "owner_role", condition)
    expected_action = require_string(expectation, "action", condition)
    required_steps = tuple(
        str(step)
        for step in expectation.get("required_steps", ())
        if isinstance(step, str) and step.strip()
    )
    incident = synthetic_incident_for_condition(condition, generated_at=generated_at)
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
    return GovernanceEvaluationResponseDrillScenario(
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
            "runbook:governance-evaluation-incident-response-v1",
            "report:governance-evaluation-incident-export-v1",
            "policy:governance-evaluation-incident-policy-v1",
        ),
    )


def synthetic_incident_for_condition(
    condition: str,
    *,
    generated_at: str,
) -> GovernanceEvaluationIncident | None:
    ops_status = ops_status_for_condition(condition)
    report = synthetic_ops_report(ops_status)
    export = build_governance_evaluation_incident_export_from_report(
        ops_report=report,
        events=(
            GovernanceEvaluationAlertDrillEvent(
                event_id=f"prior-{condition}",
                occurred_at="2026-06-16T09:00:00Z",
                ops_status=ops_status,
                failed_drill_count=failed_drill_count_for_status(ops_status),
                unexpected_error_count=1
                if ops_status == "blocked_by_unexpected_governance_evaluation_error"
                else 0,
                evidence_refs=("report:governance-evaluation-service-v1",),
            ),
        ),
        as_of=generated_at,
    )
    return export.incidents[0] if export.incidents else None


def synthetic_ops_report(ops_status: str) -> GovernanceEvaluationOpsReport:
    failed_drill_count = failed_drill_count_for_status(ops_status)
    return GovernanceEvaluationOpsReport(
        ops_status=ops_status,
        policy_id="governance-evaluation-access-policy-v1",
        route_count=3,
        evaluation_count=20,
        promotion_count=4,
        assessment_count=3,
        approved_count=1,
        review_required_count=1,
        blocked_count=1,
        direct_identifier_rejection_count=0
        if ops_status == "attention_required_guardrail_drill_gap"
        else 1,
        secret_value_rejection_count=0
        if ops_status == "attention_required_guardrail_drill_gap"
        else 1,
        unexpected_error_count=1
        if ops_status == "blocked_by_unexpected_governance_evaluation_error"
        else 0,
        by_product={"lms-courseflow": 1, "support-platform": 2},
        by_use_case={
            "lms-related-course-recommendation": 1,
            "support-agent-assist": 2,
        },
        drills=tuple(
            GovernanceEvaluationDrillItem(
                scenario_id=f"synthetic-drill-{index}",
                product="support-platform",
                use_case_id="support-agent-assist",
                expected_decision="blocked",
                decision="review_required" if index < failed_drill_count else "blocked",
                ready_for_release=False,
                requires_human_review=True,
                blocked_reasons=(),
                passed=index >= failed_drill_count,
            )
            for index in range(1)
        ),
    )


def validate_incident_against_expectation(
    incident: GovernanceEvaluationIncident | None,
    *,
    expected_severity: str,
    expected_owner_role: str,
    expected_action: str,
    required_steps: tuple[str, ...],
    available_step_ids: tuple[str, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    if incident is None:
        return ("expected repeated-failure incident was not produced",)
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
    if not incident.application_ref.startswith("platform:"):
        errors.append("incident application_ref must use platform hash ref")
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


def ops_status_for_condition(condition: str) -> str:
    mapping = {
        "governance_evaluation_release_gate_mismatch": (
            "blocked_by_release_gate_drill_mismatch"
        ),
        "governance_evaluation_unexpected_error": (
            "blocked_by_unexpected_governance_evaluation_error"
        ),
        "governance_evaluation_guardrail_gap": (
            "attention_required_guardrail_drill_gap"
        ),
    }
    return mapping.get(condition, "blocked_by_release_gate_drill_mismatch")


def failed_drill_count_for_status(ops_status: str) -> int:
    return 1 if ops_status == "blocked_by_release_gate_drill_mismatch" else 0


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
    scenarios: tuple[GovernanceEvaluationResponseDrillScenario, ...],
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
        return Path("platform/operations/runbooks/governance-evaluation-incident-response-v1.yaml")
    return (
        root
        / "platform"
        / "operations"
        / "runbooks"
        / "governance-evaluation-incident-response-v1.yaml"
    )


def default_human_runbook_path(root: Path | None) -> Path:
    if root is None:
        return Path("runbooks/governance-evaluation-incident-response.md")
    return root / "runbooks" / "governance-evaluation-incident-response.md"


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "operations"
        / "reports"
        / "governance-evaluation-incident-response-drill-v1.yaml"
    )
