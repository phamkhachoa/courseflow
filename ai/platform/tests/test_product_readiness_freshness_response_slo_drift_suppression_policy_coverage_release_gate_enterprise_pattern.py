from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from pathlib import Path

import yaml

from courseflow_ai_platform.registry import load_yaml
from courseflow_ai_platform.solution_blueprint import build_solution_blueprint_report

pattern = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_pattern"
)
effectiveness = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_effectiveness"
)

build_pattern = (
    pattern.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_pattern_report
)
build_pattern_from_reports = (
    pattern.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_pattern_report_from_reports
)
build_snapshot = (
    pattern.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_pattern_snapshot
)
build_effectiveness = (
    effectiveness.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_effectiveness_report
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_release_gate_pattern_expands_to_enterprise() -> None:
    report = build_pattern(ai_root(), generated_at="2026-06-17")

    assert report.expansion_status == "enterprise_pattern_expanded"
    assert report.release_gate_effectiveness_status == "effectiveness_monitored"
    assert report.release_gate_signal_count == 5
    assert report.release_gate_effective_signal_count == 5
    assert report.blueprint_count == 6
    assert report.ready_blueprint_count == 6
    assert report.non_lms_blueprint_count == 5
    assert report.product_count == 5
    assert report.non_lms_product_count == 4
    assert report.taxonomy_area_count == 9
    assert report.target_module_count == 13
    assert report.executable_module_count == 13
    assert report.evaluation_gate_count == 36
    assert report.assigned_use_case_count == 6
    assert report.blocked_assignment_count == 0
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == ("monitor_enterprise_release_gate_pattern_adoption",)


def test_release_gate_pattern_blocks_without_effectiveness_monitor() -> None:
    release_gate_effectiveness = build_effectiveness(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_pattern_from_reports(
        replace(release_gate_effectiveness, monitor_status="effectiveness_gap_detected"),
        solution_blueprint=build_solution_blueprint_report(ai_root()),
        generated_at="2026-06-17",
    )

    assert report.expansion_status == "blocked_by_release_gate_effectiveness"
    assert report.next_actions == (
        "expand_product_readiness_response_slo_drift_suppression_policy_"
        "coverage_release_gate_pattern_to_enterprise_use_cases",
    )


def test_release_gate_pattern_requires_non_lms_span() -> None:
    solution_blueprint = build_solution_blueprint_report(ai_root())
    report = build_pattern_from_reports(
        build_effectiveness(ai_root(), generated_at="2026-06-17"),
        solution_blueprint=replace(solution_blueprint, non_lms_count=4),
        generated_at="2026-06-17",
    )

    assert report.expansion_status == "insufficient_non_lms_use_cases"


def test_release_gate_pattern_detects_assignment_gap() -> None:
    solution_blueprint = build_solution_blueprint_report(ai_root())
    broken_blueprint = replace(
        solution_blueprint.blueprints[0],
        blueprint_status="needs_evaluation_strategy",
        blocking_reasons=("evaluation_gate_missing",),
    )
    report = build_pattern_from_reports(
        build_effectiveness(ai_root(), generated_at="2026-06-17"),
        solution_blueprint=replace(
            solution_blueprint,
            blueprints=(broken_blueprint, *solution_blueprint.blueprints[1:]),
            ready_count=5,
        ),
        generated_at="2026-06-17",
    )

    assert report.expansion_status == "blocked_by_solution_blueprint"
    assert report.blocked_assignment_count == 1
    assert report.assignments[0].expansion_ready is False


def test_release_gate_pattern_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-enterprise-pattern-v1"
    )
    assert snapshot["summary"]["expansion_status"] == "enterprise_pattern_expanded"
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert pattern.OPENAI_KEY_PATTERN.search(serialized) is None
    assert "api_key" not in serialized


def test_release_gate_pattern_raw_id_detector_catches_ids() -> None:
    report = build_pattern(ai_root(), generated_at="2026-06-17")
    leaked_assignment = replace(report.assignments[0], product="tenant-lms")

    assert pattern.count_raw_identifier_markers(report.assignments) == 0
    assert (
        pattern.count_raw_identifier_markers(
            (leaked_assignment, *report.assignments[1:])
        )
        == 1
    )


def test_release_gate_pattern_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    report_name = (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-enterprise-pattern-v1.yaml"
    )
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / report_name
    )
    generated = build_snapshot(root, generated_at="2026-06-17")

    assert checked_in == generated
