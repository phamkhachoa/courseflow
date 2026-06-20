from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression import (
    PUBLISH_SUPPRESSION_POLICY_COVERAGE_SLO_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-slo-v1"
)
ATTACH_SUPPRESSION_POLICY_COVERAGE_SLO_TO_RELEASE_GOVERNANCE_ACTION = (
    "attach_product_readiness_response_slo_drift_suppression_policy_"
    "coverage_slo_to_release_governance"
)
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "sk-", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")
TARGET_COVERAGE_PCT = 100
TARGET_REGRESSION_PASS_PCT = 100
MAX_FAILED_COVERAGE_COUNT = 0
MAX_RAW_IDENTIFIER_COUNT = 0
REVIEW_CADENCE_DAYS = 30


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloObjective:
    objective_id: str
    objective_type: str
    target: str
    observed: str
    met: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidenceRefs": list(self.evidence_refs),
            "met": self.met,
            "objectiveId": self.objective_id,
            "objectiveType": self.objective_type,
            "observed": self.observed,
            "target": self.target,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "objective_type": self.objective_type,
            "target": self.target,
            "observed": self.observed,
            "met": self.met,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport:
    generated_at: str
    slo_status: str
    regression_status: str
    coverage_status: str
    scenario_class_count: int
    covered_scenario_count: int
    failed_coverage_count: int
    coverage_pct: int
    regression_check_count: int
    passed_regression_check_count: int
    failed_regression_check_count: int
    target_coverage_pct: int
    target_regression_pass_pct: int
    review_cadence_days: int
    objective_count: int
    met_objective_count: int
    failed_objective_count: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    objectives: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloObjective,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "coveragePct": self.coverage_pct,
            "coverageStatus": self.coverage_status,
            "coveredScenarioCount": self.covered_scenario_count,
            "failedCoverageCount": self.failed_coverage_count,
            "failedObjectiveCount": self.failed_objective_count,
            "failedRegressionCheckCount": self.failed_regression_check_count,
            "generatedAt": self.generated_at,
            "metObjectiveCount": self.met_objective_count,
            "nextActions": list(self.next_actions),
            "objectiveCount": self.objective_count,
            "objectives": [objective.to_dict() for objective in self.objectives],
            "passedRegressionCheckCount": self.passed_regression_check_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "regressionCheckCount": self.regression_check_count,
            "regressionStatus": self.regression_status,
            "reviewCadenceDays": self.review_cadence_days,
            "scenarioClassCount": self.scenario_class_count,
            "sloStatus": self.slo_status,
            "targetCoveragePct": self.target_coverage_pct,
            "targetRegressionPassPct": self.target_regression_pass_pct,
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "slo_status": self.slo_status,
                "regression_status": self.regression_status,
                "coverage_status": self.coverage_status,
                "scenario_class_count": self.scenario_class_count,
                "covered_scenario_count": self.covered_scenario_count,
                "failed_coverage_count": self.failed_coverage_count,
                "coverage_pct": self.coverage_pct,
                "regression_check_count": self.regression_check_count,
                "passed_regression_check_count": (
                    self.passed_regression_check_count
                ),
                "failed_regression_check_count": (
                    self.failed_regression_check_count
                ),
                "objective_count": self.objective_count,
                "met_objective_count": self.met_objective_count,
                "failed_objective_count": self.failed_objective_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "target_coverage_pct": self.target_coverage_pct,
                "target_regression_pass_pct": self.target_regression_pass_pct,
                "max_failed_coverage_count": MAX_FAILED_COVERAGE_COUNT,
                "max_raw_identifier_count": MAX_RAW_IDENTIFIER_COUNT,
                "review_cadence_days": self.review_cadence_days,
            },
            "action_queue": {
                "met": [
                    objective.objective_id
                    for objective in self.objectives
                    if objective.met
                ],
                "blocked": [
                    objective.objective_id
                    for objective in self.objectives
                    if not objective.met
                ],
                "next_actions": list(self.next_actions),
            },
            "objectives": [
                objective.to_snapshot_dict() for objective in self.objectives
            ],
        }


def build_suppression_policy_coverage_slo_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    regression: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport
        | None
    ) = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport:
    regression_report = regression or (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_regression_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return build_suppression_policy_coverage_slo_report_from_regression(
        regression_report,
        generated_at=generated_at,
    )


def build_suppression_policy_coverage_slo_report_from_regression(
    regression: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport
    ),
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport:
    report_date = generated_at or regression.generated_at
    objectives = build_slo_objectives(regression)
    raw_identifier_count = count_raw_identifier_markers(objectives)
    tenant_safe = (
        regression.tenant_safe
        and regression.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_objective_count = sum(1 for objective in objectives if not objective.met)
    met_objective_count = len(objectives) - failed_objective_count
    slo_status = derive_slo_status(
        regression,
        failed_objective_count=failed_objective_count,
        tenant_safe=tenant_safe,
    )
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloReport(
        generated_at=report_date,
        slo_status=slo_status,
        regression_status=regression.regression_status,
        coverage_status=regression.coverage_status,
        scenario_class_count=regression.scenario_class_count,
        covered_scenario_count=regression.covered_scenario_count,
        failed_coverage_count=regression.failed_coverage_count,
        coverage_pct=regression.coverage_pct,
        regression_check_count=regression.regression_check_count,
        passed_regression_check_count=regression.passed_regression_check_count,
        failed_regression_check_count=regression.failed_regression_check_count,
        target_coverage_pct=TARGET_COVERAGE_PCT,
        target_regression_pass_pct=TARGET_REGRESSION_PASS_PCT,
        review_cadence_days=REVIEW_CADENCE_DAYS,
        objective_count=len(objectives),
        met_objective_count=met_objective_count,
        failed_objective_count=failed_objective_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=slo_next_actions(slo_status),
        objectives=objectives,
    )


def build_slo_objectives(
    regression: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport
    ),
) -> tuple[
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloObjective,
    ...,
]:
    evidence_refs = (
        "platform/operations/reports/"
        "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
        "platform/operations/reports/"
        "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1.yaml",
        "platform/operations/reports/admin-ops-dashboard-v1.html",
    )
    return (
        build_slo_objective(
            objective_id="scenario-coverage-slo",
            objective_type="scenario_coverage",
            target=(
                f"coverage_pct>={TARGET_COVERAGE_PCT};"
                f"failed_coverage_count<={MAX_FAILED_COVERAGE_COUNT}"
            ),
            observed=(
                f"coverage_pct={regression.coverage_pct};"
                f"covered={regression.covered_scenario_count}/"
                f"{regression.scenario_class_count};"
                f"failed={regression.failed_coverage_count}"
            ),
            met=(
                regression.coverage_pct >= TARGET_COVERAGE_PCT
                and regression.failed_coverage_count <= MAX_FAILED_COVERAGE_COUNT
                and regression.covered_scenario_count
                == regression.scenario_class_count
            ),
            failure_message="coverage SLO requires every scenario class covered",
            evidence_refs=evidence_refs,
        ),
        build_slo_objective(
            objective_id="coverage-regression-health-slo",
            objective_type="regression_health",
            target=(
                "regression_status=regression_monitored;"
                f"pass_pct>={TARGET_REGRESSION_PASS_PCT}"
            ),
            observed=(
                f"regression_status={regression.regression_status};"
                f"passed={regression.passed_regression_check_count}/"
                f"{regression.regression_check_count};"
                f"failed={regression.failed_regression_check_count}"
            ),
            met=(
                regression.regression_status == "regression_monitored"
                and regression.failed_regression_check_count == 0
                and regression.passed_regression_check_count
                == regression.regression_check_count
            ),
            failure_message="coverage regression monitor must remain fully green",
            evidence_refs=evidence_refs,
        ),
        build_slo_objective(
            objective_id="tenant-safety-slo",
            objective_type="tenant_safety",
            target=(
                "tenant_safe=true;"
                f"raw_identifier_count<={MAX_RAW_IDENTIFIER_COUNT}"
            ),
            observed=(
                f"tenant_safe={str(regression.tenant_safe).lower()};"
                f"raw_identifier_count={regression.raw_identifier_count}"
            ),
            met=(
                regression.tenant_safe
                and regression.raw_identifier_count <= MAX_RAW_IDENTIFIER_COUNT
            ),
            failure_message="coverage SLO publication must be tenant-safe",
            evidence_refs=evidence_refs,
        ),
        build_slo_objective(
            objective_id="owner-cadence-slo",
            objective_type="owner_cadence",
            target=f"review_cadence_days<={REVIEW_CADENCE_DAYS};dashboard_panel=true",
            observed=(
                f"review_cadence_days={REVIEW_CADENCE_DAYS};"
                "owner=SA AI Platform + Admin/Ops;dashboard_panel=true"
            ),
            met=regression.regression_status == "regression_monitored",
            failure_message="coverage SLO needs a monitored dashboard owner cadence",
            evidence_refs=evidence_refs,
        ),
    )


def build_slo_objective(
    *,
    objective_id: str,
    objective_type: str,
    target: str,
    observed: str,
    met: bool,
    failure_message: str,
    evidence_refs: tuple[str, ...],
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloObjective:
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloObjective(
        objective_id=objective_id,
        objective_type=objective_type,
        target=target,
        observed=observed,
        met=met,
        validation_errors=() if met else (failure_message,),
        evidence_refs=evidence_refs,
    )


def derive_slo_status(
    regression: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport
    ),
    *,
    failed_objective_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if regression.regression_status != "regression_monitored":
        return "blocked_by_regression"
    if failed_objective_count:
        return "coverage_slo_at_risk"
    return "coverage_slo_published"


def slo_next_actions(slo_status: str) -> tuple[str, ...]:
    if slo_status == "coverage_slo_published":
        return (ATTACH_SUPPRESSION_POLICY_COVERAGE_SLO_TO_RELEASE_GOVERNANCE_ACTION,)
    return (PUBLISH_SUPPRESSION_POLICY_COVERAGE_SLO_ACTION,)


def count_raw_identifier_markers(
    objectives: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageSloObjective,
        ...,
    ],
) -> int:
    payload = json.dumps(
        [objective.to_snapshot_dict() for objective in objectives],
        ensure_ascii=True,
        sort_keys=True,
    ).lower()
    marker_count = sum(payload.count(marker) for marker in RAW_IDENTIFIER_MARKERS)
    tenant_identifier_count = sum(
        1
        for match in TENANT_IDENTIFIER_PATTERN.findall(payload)
        if not match.startswith(SAFE_TENANT_MARKERS)
    )
    return marker_count + tenant_identifier_count


globals()[
    "build_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_slo_report"
] = build_suppression_policy_coverage_slo_report


def build_suppression_policy_coverage_slo_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_suppression_policy_coverage_slo_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_slo_snapshot"
] = build_suppression_policy_coverage_slo_snapshot


def write_suppression_policy_coverage_slo_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path else default_snapshot_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            build_suppression_policy_coverage_slo_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_slo_snapshot"
] = write_suppression_policy_coverage_slo_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
