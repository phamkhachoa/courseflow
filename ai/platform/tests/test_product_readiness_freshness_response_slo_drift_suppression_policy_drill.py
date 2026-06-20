from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_alert_suppression_policy as policy,
)
from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_suppression_policy_drill as drill,
)
from courseflow_ai_platform.registry import load_yaml

build_drill_from_policy = (
    drill.build_suppression_policy_drill_report_from_policy
)
build_drill = (
    drill.build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report
)
build_snapshot = (
    drill.build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_snapshot
)
build_policy = (
    policy.build_product_readiness_freshness_response_slo_drift_suppression_policy_report
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_suppression_policy_drill_passes_rules() -> None:
    report = build_drill(
        ai_root(),
        generated_at="2026-06-17",
    )
    scenarios_by_case = {scenario.drill_case: scenario for scenario in report.scenarios}

    assert report.drill_status == "passed"
    assert report.policy_status == "suppression_policy_codified"
    assert report.rule_count == 1
    assert report.active_rule_count == 1
    assert report.scenario_count == 4
    assert report.expected_scenario_count == 4
    assert report.passed_count == 4
    assert report.failed_count == 0
    assert report.suppressed_count == 3
    assert report.escalation_preserved_count == 1
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "monitor_product_readiness_response_slo_drift_suppression_policy_effectiveness",
    )
    assert scenarios_by_case["under_threshold_suppressed"].observed_decision == (
        "suppressed"
    )
    assert scenarios_by_case["dedupe_window_suppressed"].observed_decision == (
        "suppressed"
    )
    assert scenarios_by_case["cooldown_window_suppressed"].observed_decision == (
        "suppressed"
    )
    assert scenarios_by_case["escalation_preserved"].observed_decision == "routed"
    assert scenarios_by_case["escalation_preserved"].observed_route == "admin-ops"


def test_response_slo_drift_suppression_policy_drill_blocks_when_policy_blocks() -> None:
    suppression_policy = build_policy(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_drill_from_policy(
        replace(suppression_policy, policy_status="blocked_by_calibration"),
        generated_at="2026-06-17",
    )

    assert report.drill_status == "blocked_by_policy"
    assert report.next_actions == (
        "exercise_product_readiness_response_slo_drift_suppression_policy_drill",
    )


def test_response_slo_drift_suppression_policy_drill_fails_without_escalation() -> None:
    suppression_policy = build_policy(
        ai_root(),
        generated_at="2026-06-17",
    )
    unsafe_rule = replace(
        suppression_policy.rules[0],
        preserve_escalation=False,
    )
    report = build_drill_from_policy(
        replace(suppression_policy, rules=(unsafe_rule,)),
        generated_at="2026-06-17",
    )
    failed = [scenario for scenario in report.scenarios if not scenario.passed]

    assert report.drill_status == "failed"
    assert report.failed_count == 1
    assert failed[0].drill_case == "escalation_preserved"
    assert failed[0].validation_errors == (
        "escalation preservation is not enabled",
    )


def test_response_slo_drift_suppression_policy_drill_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(
        ai_root(),
        generated_at="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1"
    )
    assert snapshot["summary"]["tenant_safe"] is True
    assert snapshot["summary"]["raw_identifier_count"] == 0
    assert "tenant-lms" not in serialized
    assert "tenant-support" not in serialized
    assert "service:" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "sk-" not in serialized
    assert "api_key" not in serialized


def test_response_slo_drift_suppression_policy_drill_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-slo-drift-suppression-policy-drill-v1.yaml"
    )
    generated = build_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
