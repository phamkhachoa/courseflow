from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from pathlib import Path

import yaml

from courseflow_ai_platform.registry import load_yaml

adoption = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_adoption"
)
pattern = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_pattern"
)

build_adoption = (
    adoption.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_report
)
build_adoption_from_pattern = (
    adoption.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_report_from_pattern
)
build_snapshot = (
    adoption.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_snapshot
)
build_pattern = (
    pattern.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_pattern_report
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_release_gate_pattern_adoption_is_monitored() -> None:
    report = build_adoption(ai_root(), generated_at="2026-06-17")

    assert report.adoption_status == "adoption_monitored"
    assert report.enterprise_pattern_status == "enterprise_pattern_expanded"
    assert report.blueprint_count == 6
    assert report.assigned_use_case_count == 6
    assert report.non_lms_blueprint_count == 5
    assert report.non_lms_product_count == 4
    assert report.taxonomy_area_count == 9
    assert report.target_module_count == 13
    assert report.executable_module_count == 13
    assert report.evaluation_gate_count == 36
    assert report.signal_count == 6
    assert report.adopted_signal_count == 6
    assert report.blocked_signal_count == 0
    assert report.adoption_pct == 100
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "publish_enterprise_release_gate_pattern_adoption_slo",
    )


def test_release_gate_pattern_adoption_blocks_without_enterprise_pattern() -> None:
    enterprise_pattern = build_pattern(ai_root(), generated_at="2026-06-17")
    report = build_adoption_from_pattern(
        replace(enterprise_pattern, expansion_status="enterprise_pattern_gap_detected"),
        generated_at="2026-06-17",
    )

    assert report.adoption_status == "blocked_by_enterprise_pattern"
    assert report.blocked_signal_count == 1
    assert report.next_actions == (
        "monitor_enterprise_release_gate_pattern_adoption",
    )


def test_release_gate_pattern_adoption_detects_assignment_gap() -> None:
    enterprise_pattern = build_pattern(ai_root(), generated_at="2026-06-17")
    report = build_adoption_from_pattern(
        replace(
            enterprise_pattern,
            assigned_use_case_count=5,
            blocked_assignment_count=1,
        ),
        generated_at="2026-06-17",
    )

    assert report.adoption_status == "adoption_gap_detected"
    assert report.blocked_signal_count == 1
    assert report.adopted_signal_count == 5


def test_release_gate_pattern_adoption_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-enterprise-adoption-v1"
    )
    assert snapshot["summary"]["adoption_status"] == "adoption_monitored"
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert adoption.OPENAI_KEY_PATTERN.search(serialized) is None
    assert "api_key" not in serialized


def test_release_gate_pattern_adoption_raw_id_detector_catches_ids() -> None:
    report = build_adoption(ai_root(), generated_at="2026-06-17")
    leaked_signal = replace(report.signals[0], observed="tenant-lms")

    assert adoption.count_raw_identifier_markers(report.signals) == 0
    assert (
        adoption.count_raw_identifier_markers(
            (leaked_signal, *report.signals[1:])
        )
        == 1
    )


def test_release_gate_pattern_adoption_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    report_name = (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-enterprise-adoption-v1.yaml"
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
