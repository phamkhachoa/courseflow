from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_alert_calibration as cal,
)
from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_alert_suppression_policy as policy,
)
from courseflow_ai_platform.registry import load_yaml

build_policy_from_calibration = (
    policy.build_product_readiness_freshness_response_slo_drift_suppression_policy_report_from_calibration
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_suppression_policy_codifies_quiet_watch_alert() -> None:
    report = policy.build_product_readiness_freshness_response_slo_drift_suppression_policy_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    rule = report.rules[0]

    assert report.policy_status == "suppression_policy_codified"
    assert report.calibration_status == "calibrated_with_watch"
    assert report.rule_count == 1
    assert report.active_rule_count == 1
    assert report.failed_rule_count == 0
    assert report.dedupe_window_minutes == 30
    assert report.cooldown_minutes == 60
    assert report.escalation_floor_pct == 100
    assert report.preserve_escalation_count == 1
    assert report.suppress_under_threshold_count == 1
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "exercise_product_readiness_response_slo_drift_suppression_policy_drill",
    )
    assert rule.rule_id == (
        "prf-response-slo-drift-route-unreachable-p0-suppression-policy"
    )
    assert rule.alert_id == "prf-response-slo-drift-route-unreachable-p0"
    assert rule.policy_mode == "dedupe_watch_noise"
    assert rule.trigger_floor_pct == 80
    assert rule.escalation_floor_pct == 100
    assert rule.preserve_escalation is True
    assert rule.suppress_under_threshold is True
    assert rule.rule_status == "active"
    assert rule.passed is True
    assert rule.validation_errors == ()


def test_response_slo_drift_suppression_policy_blocks_when_calibration_blocks() -> None:
    calibration = cal.build_product_readiness_freshness_response_slo_drift_alert_calibration_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_policy_from_calibration(
        replace(calibration, calibration_status="blocked_by_alert_drill"),
        generated_at="2026-06-17",
    )

    assert report.policy_status == "blocked_by_calibration"
    assert report.next_actions == (
        "codify_product_readiness_response_slo_drift_alert_suppression_policy",
    )


def test_response_slo_drift_suppression_policy_fails_noisy_rule() -> None:
    calibration = cal.build_product_readiness_freshness_response_slo_drift_alert_calibration_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    noisy_item = replace(calibration.items[0], noise_status="noisy")
    report = build_policy_from_calibration(
        replace(calibration, items=(noisy_item,)),
        generated_at="2026-06-17",
    )

    assert report.policy_status == "policy_failed"
    assert report.failed_rule_count == 1
    assert report.rules[0].rule_status == "blocked"
    assert report.rules[0].validation_errors == (
        "expected quiet noise status, observed noisy",
    )


def test_response_slo_drift_suppression_policy_snapshot_suppresses_raw_ids() -> None:
    snapshot = (
        policy.build_product_readiness_freshness_response_slo_drift_suppression_policy_snapshot(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1"
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


def test_response_slo_drift_suppression_policy_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-slo-drift-alert-suppression-policy-v1.yaml"
    )
    generated = (
        policy.build_product_readiness_freshness_response_slo_drift_suppression_policy_snapshot(
            root,
            generated_at="2026-06-17",
        )
    )

    assert checked_in == generated
