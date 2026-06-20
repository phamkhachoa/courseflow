from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.delivery_state_ledger import (
    DeliveryStateTransition,
    load_delivery_state_transitions,
)
from courseflow_ai_platform.operating_cockpit import (
    OperatingCockpitAction,
    OperatingCockpitReport,
    build_operating_cockpit_report,
)

ACTION_PHASES = {
    "activate_approved_artifact": "release_activation",
    "approve_media_privacy_review": "governance_review",
    "build_simulator_or_offline_policy_eval": "simulation_and_policy_eval",
    "complete_privacy_review": "governance_review",
    "complete_media_privacy_controls": "governance_review",
    "connect_serving_metrics_export": "runtime_observability",
    "connect_media_privacy_review_report": "governance_review",
    "connect_governance_evaluation_ops_report": "governance_review",
    "configure_llm_provider_budget_latency_alerts": "runtime_observability",
    "connect_llm_provider_cost_latency_metrics": "runtime_observability",
    "connect_llm_provider_runtime_probe_export": "runtime_observability",
    "configure_llm_provider_secret_rotation": "runtime_observability",
    "complete_governance_evaluation_guardrail_drills": "governance_review",
    "accept_governance_evaluation_incident_response_runbook_drill": (
        "governance_review"
    ),
    "accept_product_readiness_freshness_incident_response_drill_state": (
        "governance_review"
    ),
    "connect_governance_evaluation_incident_response_drill": "governance_review",
    "connect_product_readiness_freshness_incident_response_drill": (
        "governance_review"
    ),
    "fix_governance_evaluation_incident_response_runbook_drill": "governance_review",
    "fix_product_readiness_freshness_incident_response_drill": "governance_review",
    "run_llm_provider_alert_delivery_drill": "runtime_observability",
    "run_governance_evaluation_release_gate_alert_drill": "governance_review",
    "define_evaluation_strategy": "evaluation_design",
    "define_missing_data_contract": "data_contract_definition",
    "enable_model_audit_store": "runtime_observability",
    "harden_data_contract_for_production": "data_contract_hardening",
    "investigate_model_audit_failures": "runtime_observability",
    "investigate_model_serving_errors": "runtime_observability",
    "investigate_llm_provider_runtime_probe_failures": "runtime_observability",
    "investigate_governance_evaluation_ops_blocker": "governance_review",
    "keep_shadow_monitoring": "shadow_monitoring",
    "monitor_active_artifact": "release_monitoring",
    "plan_platform_runtime_build": "platform_runtime_build",
    "publish_artifact_manifest": "artifact_evidence",
    "publish_simulator_evidence": "simulation_evidence",
    "publish_solution_architecture": "solution_design",
    "record_serving_access_applied_checksum": "serving_access_governance",
    "review_promotion_request": "promotion_review",
    "resolve_media_privacy_blocker": "governance_review",
    "run_controlled_policy_applier": "serving_access_governance",
    "run_required_evaluation": "evaluation_evidence",
    "investigate_serving_access_policy_drift": "serving_access_governance",
}

ACTION_ACCEPTANCE_CRITERIA = {
    "activate_approved_artifact": (
        "Activation decision is recorded with approver and timestamp.",
        "Rollback target remains valid after activation.",
        "Operating cockpit moves the artifact into active monitoring.",
    ),
    "approve_media_privacy_review": (
        "Media privacy decision is recorded with reviewer and timestamp.",
        "All required control evidence remains linked to the review.",
        "Raw media processing remains blocked unless the review is approved.",
    ),
    "build_simulator_or_offline_policy_eval": (
        "Simulator or offline policy evaluator is registered.",
        "Safety constraints and exploration budget are documented.",
        "Shadow policy gate is available before online activation.",
    ),
    "complete_privacy_review": (
        "Privacy review decision is linked to the use case or artifact.",
        "Retention, deletion/export impact and human-review obligations are documented.",
        "The relevant intake queue no longer reports a privacy blocker.",
    ),
    "complete_media_privacy_controls": (
        "Missing raw-media controls have evidence refs.",
        "Retention, access, redaction, audit and HITL obligations are documented.",
        "Media privacy review report moves the request out of waiting controls.",
    ),
    "connect_media_privacy_review_report": (
        "Media privacy review report is generated and current.",
        "Operating cockpit includes raw-media review status and action queues.",
        "Admin/Ops can inspect raw-media approval blockers without source code.",
    ),
    "connect_governance_evaluation_ops_report": (
        "Governance evaluation ops report is generated and current.",
        "Operating cockpit includes governance evaluation release-gate status.",
        "Admin/Ops can inspect release-gate drill health without source code.",
    ),
    "connect_serving_metrics_export": (
        "Gateway metrics snapshot is available to the operating cockpit.",
        "Request, error, fallback and audit counters are grouped by model.",
        "Admin/Ops can see runtime serving health in the cockpit report.",
    ),
    "configure_llm_provider_budget_latency_alerts": (
        "Provider cost and latency thresholds are linked to the runtime probe report.",
        "Admin/Ops alert ownership and escalation routing are documented.",
        "Operating cockpit exposes the LLM provider alert configuration action.",
    ),
    "connect_llm_provider_cost_latency_metrics": (
        "Provider cost and latency metrics are available for every active provider.",
        "Runtime probe report shows no observability gaps.",
        "Admin/Ops can inspect provider-level cost and latency evidence.",
    ),
    "connect_llm_provider_runtime_probe_export": (
        "LLM provider runtime probe report is generated and current.",
        "Operating cockpit includes LLM provider rollout status.",
        "Admin/Ops dashboard freshness checks include the updated cockpit source.",
    ),
    "configure_llm_provider_secret_rotation": (
        "Live provider secret refs are bound to an approved secret manager scheme.",
        "Rotation automation and evidence refs are configured before live rollout.",
        "No provider secret value or prompt payload is stored in platform reports.",
    ),
    "complete_governance_evaluation_guardrail_drills": (
        "Approved, review-required and blocked release-gate drills pass.",
        "Direct-identifier and secret-value rejection drills are present.",
        "Governance evaluation ops status returns to release_gate_observable.",
    ),
    "accept_governance_evaluation_incident_response_runbook_drill": (
        "Governance Evaluation incident response drill report is current and passed.",
        "P0/P1 repeated-failure scenarios map to Admin/Ops actions and runbook steps.",
        "Acceptance evidence excludes raw tenant, principal, request and credential values.",
    ),
    "accept_product_readiness_freshness_incident_response_drill_state": (
        "Product Readiness Freshness incident response drill report is current and passed.",
        "P0/P1 freshness, route, snapshot and audit-gap scenarios map to runbook steps.",
        "Acceptance evidence excludes raw tenant, principal, request and credential values.",
    ),
    "connect_governance_evaluation_incident_response_drill": (
        "Governance Evaluation response drill report is generated and current.",
        "Admin/Ops dashboard freshness includes the response drill source.",
        "Runbook drill status is visible without reading source code.",
    ),
    "connect_product_readiness_freshness_incident_response_drill": (
        "Product Readiness Freshness response drill report is generated and current.",
        "Admin/Ops dashboard freshness includes the product response drill source.",
        "Runbook drill status is visible without reading source code.",
    ),
    "fix_governance_evaluation_incident_response_runbook_drill": (
        "Blocked response drill scenarios have remediation owners.",
        "Runbook steps cover detect, acknowledge, assign, contain, remediate, "
        "verify, communicate and close.",
        "Response drill report returns to passed before acceptance.",
    ),
    "fix_product_readiness_freshness_incident_response_drill": (
        "Blocked Product Readiness Freshness drill scenarios have remediation owners.",
        "Runbook steps cover detect, acknowledge, assign, contain, remediate, "
        "verify, communicate and close.",
        "Response drill report returns to passed before acceptance.",
    ),
    "run_llm_provider_alert_delivery_drill": (
        "Provider alert routes are configured for every observable LLM provider.",
        "Admin/Ops can trigger or simulate the provider budget/latency route.",
        "Alert evidence remains tenant-safe and excludes credential or prompt payloads.",
    ),
    "run_governance_evaluation_release_gate_alert_drill": (
        "Governance evaluation release-gate alert path is triggered or simulated.",
        "Approved, review-required and blocked decisions route to the expected owner.",
        "Alert evidence remains tenant-safe and excludes identity or secret payloads.",
    ),
    "define_evaluation_strategy": (
        "Offline or shadow evaluation gate is registered.",
        "Golden dataset or governed snapshot source is identified.",
        "Thresholds and owner-on-failure are documented.",
    ),
    "define_missing_data_contract": (
        "Data contract registry includes the missing data domains.",
        "Contract file defines entities, feature groups, privacy and quality sections.",
        "Data contract coverage reports zero missing domains for the request.",
    ),
    "enable_model_audit_store": (
        "Model serving gateway is configured with a model audit store.",
        "Audit record count matches serving request count for regulated traffic.",
        "Audit retention, export and deletion behavior is verified.",
    ),
    "harden_data_contract_for_production": (
        "Draft contract reaches active or an explicit gated status.",
        "Freshness and parity evidence is attached.",
        "Owner-on-failure and production data lineage are documented.",
    ),
    "investigate_model_audit_failures": (
        "Audit write failure cause is identified and documented.",
        "Regulated workflows are switched to fail-closed or explicitly accepted.",
        "Audit failure counters return to zero after remediation.",
    ),
    "investigate_model_serving_errors": (
        "Error or fallback cause is linked to model, payload or dependency evidence.",
        "Fallback behavior and human-review routing are verified.",
        "Serving error counters return below the accepted threshold.",
    ),
    "investigate_llm_provider_runtime_probe_failures": (
        "Blocked provider probe failures are triaged by provider ID.",
        "Secret probe, egress, Prompt Gateway, cost and latency checks are remediated.",
        "Runtime probe report no longer blocks live rollout.",
    ),
    "investigate_governance_evaluation_ops_blocker": (
        "Blocked governance evaluation drill cause is identified and documented.",
        "Release-gate decision, privacy rejection or metrics failure is remediated.",
        "Governance evaluation ops report no longer blocks release observability.",
    ),
    "keep_shadow_monitoring": (
        "Shadow metrics are collected against the required gates.",
        "Regression or tenant-isolation findings are triaged.",
        "Promotion intake is created if the shadow artifact is ready to advance.",
    ),
    "monitor_active_artifact": (
        "Latency, error, fallback and quality signals are monitored.",
        "Rollback target remains available.",
        "Incidents create follow-up backlog items.",
    ),
    "plan_platform_runtime_build": (
        "Runtime build path is documented for the target taxonomy module.",
        "Required artifact, serving and evaluation contracts are identified.",
        "Capability maturity is updated after implementation evidence exists.",
    ),
    "publish_artifact_manifest": (
        "Artifact manifest exists with checksum and model/use-case lineage.",
        "Model card or vector-index manifest is linked.",
        "Promotion intake can resolve the artifact blocker.",
    ),
    "publish_simulator_evidence": (
        "Simulator evidence is linked to the candidate policy artifact.",
        "Offline policy metrics and safety constraints are accepted.",
        "Promotion intake can resolve the simulator blocker.",
    ),
    "publish_solution_architecture": (
        "Solution architecture is linked to the request.",
        "Data, evaluation, artifact and serving paths are identified.",
        "Backlog items exist for the next implementation slice.",
    ),
    "record_serving_access_applied_checksum": (
        "Apply ledger records the applied policy checksum.",
        "Applied timestamp and reviewer evidence are present.",
        "Reconciliation report no longer shows a ledger update blocker.",
    ),
    "review_promotion_request": (
        "Maker-checker review decision is recorded.",
        "Required gates and rollback evidence are accepted or blocked with reasons.",
        "Promotion registry is updated when the request is approved.",
    ),
    "resolve_media_privacy_blocker": (
        "Validation errors or blocked processing modes are removed or explicitly rejected.",
        "Governance decision explains whether raw media remains blocked.",
        "Report no longer shows blocked media privacy reviews.",
    ),
    "run_controlled_policy_applier": (
        "Controlled applier writes the proposed policy to an explicit target.",
        "Source and proposed policy checksums match the apply ledger.",
        "Reconciliation report moves the application out of pending apply.",
    ),
    "run_required_evaluation": (
        "Required evaluation report exists and passes thresholds.",
        "Dataset or snapshot lineage is linked.",
        "Promotion intake can resolve the evaluation blocker.",
    ),
    "investigate_serving_access_policy_drift": (
        "Active policy drift source is identified.",
        "Policy change is linked to an approved ledger entry or rolled back.",
        "Reconciliation report returns to pending, update-required or reconciled status.",
    ),
}


@dataclass(frozen=True, slots=True)
class DeliveryBacklogItem:
    backlog_id: str
    title: str
    source: str
    action_id: str
    action_type: str
    delivery_phase: str
    owner_role: str
    priority: str
    status: str
    ready_to_start: bool
    monitoring_item: bool
    blocker: str
    refs: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "acceptanceCriteria": list(self.acceptance_criteria),
            "actionId": self.action_id,
            "actionType": self.action_type,
            "backlogId": self.backlog_id,
            "blocker": self.blocker,
            "deliveryPhase": self.delivery_phase,
            "monitoringItem": self.monitoring_item,
            "ownerRole": self.owner_role,
            "priority": self.priority,
            "readyToStart": self.ready_to_start,
            "refs": list(self.refs),
            "source": self.source,
            "status": self.status,
            "title": self.title,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "backlog_id": self.backlog_id,
            "title": self.title,
            "source": self.source,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "delivery_phase": self.delivery_phase,
            "owner_role": self.owner_role,
            "priority": self.priority,
            "status": self.status,
            "ready_to_start": self.ready_to_start,
            "monitoring_item": self.monitoring_item,
            "blocker": self.blocker,
            "refs": list(self.refs),
            "acceptance_criteria": list(self.acceptance_criteria),
        }


@dataclass(frozen=True, slots=True)
class DeliveryBacklogReport:
    item_count: int
    ready_to_start_count: int
    monitoring_count: int
    blocked_count: int
    p0_count: int
    p1_count: int
    p2_count: int
    p3_count: int
    by_source: dict[str, int]
    by_phase: dict[str, int]
    by_owner_role: dict[str, int]
    by_status: dict[str, int]
    items: tuple[DeliveryBacklogItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "blockedCount": self.blocked_count,
            "byOwnerRole": self.by_owner_role,
            "byPhase": self.by_phase,
            "bySource": self.by_source,
            "byStatus": self.by_status,
            "itemCount": self.item_count,
            "items": [item.to_dict() for item in self.items],
            "monitoringCount": self.monitoring_count,
            "p0Count": self.p0_count,
            "p1Count": self.p1_count,
            "p2Count": self.p2_count,
            "p3Count": self.p3_count,
            "readyToStartCount": self.ready_to_start_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "delivery-backlog-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "item_count": self.item_count,
                "ready_to_start_count": self.ready_to_start_count,
                "monitoring_count": self.monitoring_count,
                "blocked_count": self.blocked_count,
                "p0_count": self.p0_count,
                "p1_count": self.p1_count,
                "p2_count": self.p2_count,
                "p3_count": self.p3_count,
            },
            "by_source": self.by_source,
            "by_phase": self.by_phase,
            "by_owner_role": self.by_owner_role,
            "by_status": self.by_status,
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_delivery_backlog_report(
    ai_root: Path | str,
    *,
    as_of: str | date | None = None,
    apply_state_ledger: bool = True,
) -> DeliveryBacklogReport:
    cockpit = build_operating_cockpit_report(ai_root, as_of=as_of)
    state_transitions = (
        load_delivery_state_transitions(ai_root) if apply_state_ledger else ()
    )
    return build_delivery_backlog_report_from_cockpit(
        cockpit,
        state_transitions=state_transitions,
    )


def build_delivery_backlog_report_from_cockpit(
    cockpit: OperatingCockpitReport,
    *,
    state_transitions: tuple[DeliveryStateTransition, ...] = (),
) -> DeliveryBacklogReport:
    seen_action_ids: set[str] = set()
    items: list[DeliveryBacklogItem] = []
    for index, action in enumerate(cockpit.actions, start=1):
        if action.action_id in seen_action_ids:
            raise ValueError(f"duplicate cockpit action id: {action.action_id}")
        seen_action_ids.add(action.action_id)
        items.append(build_delivery_backlog_item(index, action))

    item_tuple = apply_delivery_state_transitions(tuple(items), state_transitions)
    return DeliveryBacklogReport(
        item_count=len(item_tuple),
        ready_to_start_count=sum(1 for item in item_tuple if item.ready_to_start),
        monitoring_count=sum(1 for item in item_tuple if item.monitoring_item),
        blocked_count=sum(1 for item in item_tuple if item.status == "blocked"),
        p0_count=count_priority(item_tuple, "p0"),
        p1_count=count_priority(item_tuple, "p1"),
        p2_count=count_priority(item_tuple, "p2"),
        p3_count=count_priority(item_tuple, "p3"),
        by_source=count_by(item_tuple, "source"),
        by_phase=count_by(item_tuple, "delivery_phase"),
        by_owner_role=count_by(item_tuple, "owner_role"),
        by_status=count_by(item_tuple, "status"),
        items=item_tuple,
    )


def build_delivery_backlog_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_delivery_backlog_report(ai_root, as_of=report_date).to_snapshot_dict(
        generated_at=report_date
    )


def write_delivery_backlog_snapshot(
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
            build_delivery_backlog_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def build_delivery_backlog_item(
    index: int,
    action: OperatingCockpitAction,
) -> DeliveryBacklogItem:
    phase = ACTION_PHASES.get(action.action_type, "platform_delivery")
    acceptance_criteria = ACTION_ACCEPTANCE_CRITERIA.get(
        action.action_type,
        ("Owner confirms completion evidence.",),
    )
    status = action.status
    return DeliveryBacklogItem(
        backlog_id=f"AIP-BLG-{index:04d}",
        title=build_title(action),
        source=action.source,
        action_id=action.action_id,
        action_type=action.action_type,
        delivery_phase=phase,
        owner_role=action.owner_role,
        priority=action.priority,
        status=status,
        ready_to_start=ready_to_start_for_status(status),
        monitoring_item=monitoring_item_for_status(status),
        blocker=action.reason if status in {"blocked", "waiting", "draft"} else "",
        refs=action.refs,
        acceptance_criteria=acceptance_criteria,
    )


def build_title(action: OperatingCockpitAction) -> str:
    action_label = action.action_type.replace("_", " ").title()
    ref_label = ", ".join(action.refs)
    return f"{action_label}: {ref_label}"


def apply_delivery_state_transitions(
    items: tuple[DeliveryBacklogItem, ...],
    transitions: tuple[DeliveryStateTransition, ...],
) -> tuple[DeliveryBacklogItem, ...]:
    if not transitions:
        return items
    transition_by_action_id = {transition.action_id: transition for transition in transitions}
    return tuple(
        apply_delivery_state_transition(item, transition_by_action_id.get(item.action_id))
        for item in items
    )


def apply_delivery_state_transition(
    item: DeliveryBacklogItem,
    transition: DeliveryStateTransition | None,
) -> DeliveryBacklogItem:
    if transition is None:
        return item
    status = transition.target_status
    return replace(
        item,
        status=status,
        ready_to_start=ready_to_start_for_status(status),
        monitoring_item=monitoring_item_for_status(status),
        blocker="",
    )


def ready_to_start_for_status(status: str) -> bool:
    return status in {"ready", "waiting", "draft"}


def monitoring_item_for_status(status: str) -> bool:
    return status in {"active", "shadow"}


def count_priority(items: tuple[DeliveryBacklogItem, ...], priority: str) -> int:
    return sum(1 for item in items if item.priority == priority)


def count_by(items: tuple[DeliveryBacklogItem, ...], attribute: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = getattr(item, attribute)
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def default_snapshot_path(root: Path) -> Path:
    return root / "platform" / "delivery" / "reports" / "delivery-backlog-v1.yaml"
