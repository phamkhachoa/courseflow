from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.governance_evaluation_service import (
    GOVERNANCE_EVALUATION_ASSESS_SCOPE,
    GovernanceEvaluationPrivacyError,
    GovernanceEvaluationRuntime,
)


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationDrillItem:
    scenario_id: str
    product: str
    use_case_id: str
    expected_decision: str
    decision: str
    ready_for_release: bool
    requires_human_review: bool
    blocked_reasons: tuple[str, ...]
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "blockedReasons": list(self.blocked_reasons),
            "decision": self.decision,
            "expectedDecision": self.expected_decision,
            "passed": self.passed,
            "product": self.product,
            "readyForRelease": self.ready_for_release,
            "requiresHumanReview": self.requires_human_review,
            "scenarioId": self.scenario_id,
            "useCaseId": self.use_case_id,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "product": self.product,
            "use_case_id": self.use_case_id,
            "expected_decision": self.expected_decision,
            "decision": self.decision,
            "ready_for_release": self.ready_for_release,
            "requires_human_review": self.requires_human_review,
            "blocked_reasons": list(self.blocked_reasons),
            "passed": self.passed,
        }


@dataclass(frozen=True, slots=True)
class GovernanceEvaluationOpsReport:
    ops_status: str
    policy_id: str
    route_count: int
    evaluation_count: int
    promotion_count: int
    assessment_count: int
    approved_count: int
    review_required_count: int
    blocked_count: int
    direct_identifier_rejection_count: int
    secret_value_rejection_count: int
    unexpected_error_count: int
    by_product: dict[str, int]
    by_use_case: dict[str, int]
    drills: tuple[GovernanceEvaluationDrillItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "approvedCount": self.approved_count,
            "assessmentCount": self.assessment_count,
            "blockedCount": self.blocked_count,
            "byProduct": self.by_product,
            "byUseCase": self.by_use_case,
            "directIdentifierRejectionCount": self.direct_identifier_rejection_count,
            "drills": [drill.to_dict() for drill in self.drills],
            "evaluationCount": self.evaluation_count,
            "opsStatus": self.ops_status,
            "policyId": self.policy_id,
            "promotionCount": self.promotion_count,
            "reviewRequiredCount": self.review_required_count,
            "routeCount": self.route_count,
            "secretValueRejectionCount": self.secret_value_rejection_count,
            "unexpectedErrorCount": self.unexpected_error_count,
        }

    def to_snapshot_dict(self, *, generated_at: str) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "governance-evaluation-service-v1",
            "owner": "ai-platform",
            "generated_at": generated_at,
            "summary": {
                "ops_status": self.ops_status,
                "policy_id": self.policy_id,
                "route_count": self.route_count,
                "evaluation_count": self.evaluation_count,
                "promotion_count": self.promotion_count,
                "assessment_count": self.assessment_count,
                "approved_count": self.approved_count,
                "review_required_count": self.review_required_count,
                "blocked_count": self.blocked_count,
                "direct_identifier_rejection_count": (
                    self.direct_identifier_rejection_count
                ),
                "secret_value_rejection_count": self.secret_value_rejection_count,
                "unexpected_error_count": self.unexpected_error_count,
            },
            "by_product": self.by_product,
            "by_use_case": self.by_use_case,
            "drills": [drill.to_snapshot_dict() for drill in self.drills],
        }


def build_governance_evaluation_ops_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> GovernanceEvaluationOpsReport:
    report_date = generated_at or date.today().isoformat()
    runtime = GovernanceEvaluationRuntime(ai_root)
    health = runtime.health()
    drills = tuple(run_release_gate_drills(runtime, as_of=report_date))
    run_privacy_guardrail_drills(runtime, as_of=report_date)
    metrics = runtime.snapshot_metrics()
    unexpected_errors = (
        metrics.error_count
        - metrics.direct_identifier_rejection_count
        - metrics.secret_value_rejection_count
    )
    return GovernanceEvaluationOpsReport(
        ops_status=derive_ops_status(
            drills,
            approved_count=metrics.approved_count,
            review_required_count=metrics.review_required_count,
            blocked_count=metrics.blocked_count,
            direct_identifier_rejection_count=(
                metrics.direct_identifier_rejection_count
            ),
            secret_value_rejection_count=metrics.secret_value_rejection_count,
            unexpected_error_count=unexpected_errors,
        ),
        policy_id=str(health["policyId"]),
        route_count=int(health["routeCount"]),
        evaluation_count=int(health["evaluationCount"]),
        promotion_count=int(health["promotionCount"]),
        assessment_count=metrics.assessment_count,
        approved_count=metrics.approved_count,
        review_required_count=metrics.review_required_count,
        blocked_count=metrics.blocked_count,
        direct_identifier_rejection_count=metrics.direct_identifier_rejection_count,
        secret_value_rejection_count=metrics.secret_value_rejection_count,
        unexpected_error_count=unexpected_errors,
        by_product=metrics.by_product,
        by_use_case=metrics.by_use_case,
        drills=drills,
    )


def build_governance_evaluation_ops_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report_date = generated_at or date.today().isoformat()
    return build_governance_evaluation_ops_report(
        ai_root,
        generated_at=report_date,
    ).to_snapshot_dict(generated_at=report_date)


def write_governance_evaluation_ops_snapshot(
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
            build_governance_evaluation_ops_snapshot(root, generated_at=generated_at),
            handle,
            sort_keys=False,
        )
    return target


def run_release_gate_drills(
    runtime: GovernanceEvaluationRuntime,
    *,
    as_of: str,
) -> list[GovernanceEvaluationDrillItem]:
    drills: list[GovernanceEvaluationDrillItem] = []
    for scenario in drill_scenarios(as_of):
        response = runtime.assess(
            scenario["body"],
            scenario["principal"],
        )
        expected = str(scenario["expected_decision"])
        drills.append(
            GovernanceEvaluationDrillItem(
                scenario_id=str(scenario["scenario_id"]),
                product=response.product,
                use_case_id=response.use_case_id,
                expected_decision=expected,
                decision=response.decision,
                ready_for_release=response.ready_for_release,
                requires_human_review=response.requires_human_review,
                blocked_reasons=response.blocked_reasons,
                passed=response.decision == expected,
            )
        )
    return drills


def run_privacy_guardrail_drills(
    runtime: GovernanceEvaluationRuntime,
    *,
    as_of: str,
) -> None:
    for body in (
        {
            **support_release_body(as_of=as_of),
            "email": "agent@example.com",
        },
        {
            **support_release_body(as_of=as_of),
            "apiKey": "sk-not-allowed",
        },
    ):
        try:
            runtime.assess(body, support_principal())
        except GovernanceEvaluationPrivacyError:
            continue
        raise AssertionError("expected governance evaluation privacy drill rejection")


def drill_scenarios(as_of: str) -> tuple[dict[str, Any], ...]:
    return (
        {
            "scenario_id": "lms-recommendation-active-baseline",
            "expected_decision": "approved",
            "body": {
                "tenantId": "tenant-lms",
                "product": "lms-courseflow",
                "useCaseId": "lms-related-course-recommendation",
                "promotionId": "recommendation-item-cf-v1-active-baseline",
                "asOf": as_of,
            },
            "principal": {
                "principalId": "service:lms-courseflow-governance-evaluation",
                "scopes": [GOVERNANCE_EVALUATION_ASSESS_SCOPE],
                "tenantIds": ["tenant-lms"],
                "productIds": ["lms-courseflow"],
                "useCaseIds": ["lms-related-course-recommendation"],
            },
        },
        {
            "scenario_id": "support-agent-assist-approved-baseline",
            "expected_decision": "review_required",
            "body": support_release_body(as_of=as_of),
            "principal": support_principal(),
        },
        {
            "scenario_id": "support-agent-assist-external-auto-send",
            "expected_decision": "blocked",
            "body": {
                **support_release_body(as_of=as_of),
                "externalAutoSend": True,
            },
            "principal": support_principal(),
        },
    )


def support_release_body(*, as_of: str) -> dict[str, Any]:
    return {
        "tenantId": "tenant-support",
        "product": "support-platform",
        "useCaseId": "support-agent-assist",
        "promotionId": "support-agent-assist-baseline-approved",
        "riskLevel": "high",
        "asOf": as_of,
    }


def support_principal() -> dict[str, Any]:
    return {
        "principalId": "service:support-platform-governance-evaluation",
        "scopes": [GOVERNANCE_EVALUATION_ASSESS_SCOPE],
        "tenantIds": ["tenant-support"],
        "productIds": ["support-platform"],
        "useCaseIds": ["support-agent-assist"],
    }


def derive_ops_status(
    drills: tuple[GovernanceEvaluationDrillItem, ...],
    *,
    approved_count: int,
    review_required_count: int,
    blocked_count: int,
    direct_identifier_rejection_count: int,
    secret_value_rejection_count: int,
    unexpected_error_count: int,
) -> str:
    if unexpected_error_count:
        return "blocked_by_unexpected_governance_evaluation_error"
    if not all(drill.passed for drill in drills):
        return "blocked_by_release_gate_drill_mismatch"
    if not (
        approved_count
        and review_required_count
        and blocked_count
        and direct_identifier_rejection_count
        and secret_value_rejection_count
    ):
        return "attention_required_guardrail_drill_gap"
    return "release_gate_observable"


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "governance-evaluation-service-v1.yaml"
    )
