from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .product_readiness_freshness_response_slo_drift_suppression_policy_coverage import (
    MONITOR_SUPPRESSION_POLICY_COVERAGE_REGRESSION_ACTION,
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport,
    build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report,
)

REPORT_ID = (
    "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-regression-v1"
)
PUBLISH_SUPPRESSION_POLICY_COVERAGE_SLO_ACTION = (
    "publish_product_readiness_response_slo_drift_suppression_policy_coverage_slo"
)
RAW_IDENTIFIER_MARKERS = ("service:", "token", "secret", "sk-", "api_key")
TENANT_IDENTIFIER_PATTERN = re.compile(r"\btenant-[a-z0-9][a-z0-9_-]*")
SAFE_TENANT_MARKERS = ("tenant-safe", "tenant-safety")
MIN_SCENARIO_CLASS_COUNT = 5
MIN_COVERAGE_PCT = 100
MIN_ACTIVE_POLICY_SCENARIO_COUNT = 1
MIN_EFFECTIVE_SIGNAL_COUNT = 4
MIN_EXPLICIT_NON_WATCH_SCENARIO_COUNT = 4


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionCheck:
    check_id: str
    check_type: str
    expected: str
    observed: str
    passed: bool
    validation_errors: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkId": self.check_id,
            "checkType": self.check_type,
            "evidenceRefs": list(self.evidence_refs),
            "expected": self.expected,
            "observed": self.observed,
            "passed": self.passed,
            "validationErrors": list(self.validation_errors),
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "check_type": self.check_type,
            "expected": self.expected,
            "observed": self.observed,
            "passed": self.passed,
            "validation_errors": list(self.validation_errors),
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport:
    generated_at: str
    regression_status: str
    coverage_status: str
    scenario_class_count: int
    covered_scenario_count: int
    failed_coverage_count: int
    active_policy_scenario_count: int
    explicit_non_watch_scenario_count: int
    effective_signal_count: int
    coverage_pct: int
    regression_check_count: int
    passed_regression_check_count: int
    failed_regression_check_count: int
    tenant_safe: bool
    raw_identifier_count: int
    next_actions: tuple[str, ...]
    checks: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionCheck,
        ...,
    ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activePolicyScenarioCount": self.active_policy_scenario_count,
            "coveragePct": self.coverage_pct,
            "coverageStatus": self.coverage_status,
            "coveredScenarioCount": self.covered_scenario_count,
            "checks": [check.to_dict() for check in self.checks],
            "effectiveSignalCount": self.effective_signal_count,
            "explicitNonWatchScenarioCount": (
                self.explicit_non_watch_scenario_count
            ),
            "failedCoverageCount": self.failed_coverage_count,
            "failedRegressionCheckCount": self.failed_regression_check_count,
            "generatedAt": self.generated_at,
            "nextActions": list(self.next_actions),
            "passedRegressionCheckCount": self.passed_regression_check_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "regressionCheckCount": self.regression_check_count,
            "regressionStatus": self.regression_status,
            "scenarioClassCount": self.scenario_class_count,
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "summary": {
                "regression_status": self.regression_status,
                "coverage_status": self.coverage_status,
                "scenario_class_count": self.scenario_class_count,
                "covered_scenario_count": self.covered_scenario_count,
                "failed_coverage_count": self.failed_coverage_count,
                "active_policy_scenario_count": self.active_policy_scenario_count,
                "explicit_non_watch_scenario_count": (
                    self.explicit_non_watch_scenario_count
                ),
                "effective_signal_count": self.effective_signal_count,
                "coverage_pct": self.coverage_pct,
                "regression_check_count": self.regression_check_count,
                "passed_regression_check_count": (
                    self.passed_regression_check_count
                ),
                "failed_regression_check_count": (
                    self.failed_regression_check_count
                ),
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
            },
            "thresholds": {
                "min_scenario_class_count": MIN_SCENARIO_CLASS_COUNT,
                "min_coverage_pct": MIN_COVERAGE_PCT,
                "min_active_policy_scenario_count": MIN_ACTIVE_POLICY_SCENARIO_COUNT,
                "min_effective_signal_count": MIN_EFFECTIVE_SIGNAL_COUNT,
                "min_explicit_non_watch_scenario_count": (
                    MIN_EXPLICIT_NON_WATCH_SCENARIO_COUNT
                ),
            },
            "action_queue": {
                "passed": [check.check_id for check in self.checks if check.passed],
                "blocked": [
                    check.check_id for check in self.checks if not check.passed
                ],
                "next_actions": list(self.next_actions),
            },
            "checks": [check.to_snapshot_dict() for check in self.checks],
        }


def build_suppression_policy_coverage_regression_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
    coverage: (
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport
        | None
    ) = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport:
    coverage_report = coverage or (
        build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_report(
            ai_root,
            generated_at=generated_at,
        )
    )
    return build_suppression_policy_coverage_regression_report_from_coverage(
        coverage_report,
        generated_at=generated_at,
    )


def build_suppression_policy_coverage_regression_report_from_coverage(
    coverage: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport,
    *,
    generated_at: str | None = None,
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport:
    report_date = generated_at or coverage.generated_at
    checks = build_regression_checks(coverage)
    raw_identifier_count = count_raw_identifier_markers(checks)
    tenant_safe = (
        coverage.tenant_safe
        and coverage.raw_identifier_count == 0
        and raw_identifier_count == 0
    )
    failed_regression_check_count = sum(1 for check in checks if not check.passed)
    regression_status = derive_regression_status(
        coverage,
        failed_regression_check_count=failed_regression_check_count,
        tenant_safe=tenant_safe,
    )
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionReport(
        generated_at=report_date,
        regression_status=regression_status,
        coverage_status=coverage.coverage_status,
        scenario_class_count=coverage.scenario_class_count,
        covered_scenario_count=coverage.covered_scenario_count,
        failed_coverage_count=coverage.failed_coverage_count,
        active_policy_scenario_count=coverage.active_policy_scenario_count,
        explicit_non_watch_scenario_count=(
            coverage.explicit_non_watch_scenario_count
        ),
        effective_signal_count=coverage.effective_signal_count,
        coverage_pct=coverage.coverage_pct,
        regression_check_count=len(checks),
        passed_regression_check_count=sum(1 for check in checks if check.passed),
        failed_regression_check_count=failed_regression_check_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        next_actions=regression_next_actions(regression_status),
        checks=checks,
    )


def build_regression_checks(
    coverage: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport,
) -> tuple[
    ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionCheck,
    ...,
]:
    evidence_refs = (
        "platform/operations/reports/"
        "product-readiness-freshness-response-slo-drift-suppression-policy-coverage-v1.yaml",
        "platform/operations/reports/"
        "product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml",
        "platform/operations/reports/"
        "product-readiness-freshness-response-trends-v1.yaml",
        "platform/operations/reports/admin-ops-dashboard-v1.html",
    )
    return (
        build_regression_check(
            check_id="coverage-status-stable",
            check_type="coverage_status",
            expected="coverage_expanded",
            observed=coverage.coverage_status,
            passed=coverage.coverage_status == "coverage_expanded",
            failure_message=(
                f"expected coverage_expanded, observed {coverage.coverage_status}"
            ),
            evidence_refs=evidence_refs,
        ),
        build_regression_check(
            check_id="scenario-class-floor-stable",
            check_type="scenario_class_floor",
            expected=f">={MIN_SCENARIO_CLASS_COUNT}",
            observed=str(coverage.scenario_class_count),
            passed=coverage.scenario_class_count >= MIN_SCENARIO_CLASS_COUNT,
            failure_message=(
                "scenario class count fell below regression baseline "
                f"{MIN_SCENARIO_CLASS_COUNT}"
            ),
            evidence_refs=evidence_refs,
        ),
        build_regression_check(
            check_id="scenario-coverage-full",
            check_type="scenario_coverage",
            expected="covered_scenario_count == scenario_class_count",
            observed=f"{coverage.covered_scenario_count}/{coverage.scenario_class_count}",
            passed=(
                coverage.covered_scenario_count == coverage.scenario_class_count
                and coverage.failed_coverage_count == 0
            ),
            failure_message="not every response SLO scenario class is covered",
            evidence_refs=evidence_refs,
        ),
        build_regression_check(
            check_id="coverage-pct-floor-stable",
            check_type="coverage_pct_floor",
            expected=f">={MIN_COVERAGE_PCT}",
            observed=str(coverage.coverage_pct),
            passed=coverage.coverage_pct >= MIN_COVERAGE_PCT,
            failure_message="coverage percentage fell below regression floor",
            evidence_refs=evidence_refs,
        ),
        build_regression_check(
            check_id="active-policy-watch-guard-stable",
            check_type="active_policy_watch_guard",
            expected=(
                f"active>={MIN_ACTIVE_POLICY_SCENARIO_COUNT};"
                f"signals>={MIN_EFFECTIVE_SIGNAL_COUNT}"
            ),
            observed=(
                f"active={coverage.active_policy_scenario_count};"
                f"signals={coverage.effective_signal_count}"
            ),
            passed=(
                coverage.active_policy_scenario_count
                >= MIN_ACTIVE_POLICY_SCENARIO_COUNT
                and coverage.effective_signal_count >= MIN_EFFECTIVE_SIGNAL_COUNT
            ),
            failure_message=(
                "watch scenario lost active policy or effective signal coverage"
            ),
            evidence_refs=evidence_refs,
        ),
        build_regression_check(
            check_id="explicit-non-watch-exclusions-stable",
            check_type="explicit_non_watch_exclusion_guard",
            expected=f">={MIN_EXPLICIT_NON_WATCH_SCENARIO_COUNT}",
            observed=str(coverage.explicit_non_watch_scenario_count),
            passed=(
                coverage.explicit_non_watch_scenario_count
                >= MIN_EXPLICIT_NON_WATCH_SCENARIO_COUNT
            ),
            failure_message="explicit non-watch exclusions fell below baseline",
            evidence_refs=evidence_refs,
        ),
        build_regression_check(
            check_id="tenant-safety-stable",
            check_type="tenant_safety",
            expected="tenant_safe=true; raw_identifier_count=0",
            observed=(
                f"tenant_safe={str(coverage.tenant_safe).lower()};"
                f"raw_identifier_count={coverage.raw_identifier_count}"
            ),
            passed=coverage.tenant_safe and coverage.raw_identifier_count == 0,
            failure_message="coverage regression report must remain tenant-safe",
            evidence_refs=evidence_refs,
        ),
    )


def build_regression_check(
    *,
    check_id: str,
    check_type: str,
    expected: str,
    observed: str,
    passed: bool,
    failure_message: str,
    evidence_refs: tuple[str, ...],
) -> ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionCheck:
    return ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionCheck(
        check_id=check_id,
        check_type=check_type,
        expected=expected,
        observed=observed,
        passed=passed,
        validation_errors=() if passed else (failure_message,),
        evidence_refs=evidence_refs,
    )


def derive_regression_status(
    coverage: ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageReport,
    *,
    failed_regression_check_count: int,
    tenant_safe: bool,
) -> str:
    if not tenant_safe:
        return "blocked_by_tenant_safety"
    if coverage.coverage_status != "coverage_expanded":
        return "blocked_by_coverage"
    if failed_regression_check_count:
        return "coverage_regression_detected"
    return "regression_monitored"


def regression_next_actions(regression_status: str) -> tuple[str, ...]:
    if regression_status == "regression_monitored":
        return (PUBLISH_SUPPRESSION_POLICY_COVERAGE_SLO_ACTION,)
    return (MONITOR_SUPPRESSION_POLICY_COVERAGE_REGRESSION_ACTION,)


def count_raw_identifier_markers(
    checks: tuple[
        ProductReadinessFreshnessResponseSloDriftSuppressionPolicyCoverageRegressionCheck,
        ...,
    ],
) -> int:
    payload = json.dumps(
        [check.to_snapshot_dict() for check in checks],
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
    "suppression_policy_coverage_regression_report"
] = build_suppression_policy_coverage_regression_report


def build_suppression_policy_coverage_regression_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return (
        build_suppression_policy_coverage_regression_report(
            ai_root,
            generated_at=generated_at,
        ).to_snapshot_dict()
    )


globals()[
    "build_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_regression_snapshot"
] = build_suppression_policy_coverage_regression_snapshot


def write_suppression_policy_coverage_regression_snapshot(
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
            build_suppression_policy_coverage_regression_snapshot(
                root,
                generated_at=generated_at,
            ),
            handle,
            sort_keys=False,
        )
    return target


globals()[
    "write_product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_regression_snapshot"
] = write_suppression_policy_coverage_regression_snapshot


def default_snapshot_path(ai_root: Path) -> Path:
    return (
        ai_root
        / "platform"
        / "operations"
        / "reports"
        / f"{REPORT_ID}.yaml"
    )
