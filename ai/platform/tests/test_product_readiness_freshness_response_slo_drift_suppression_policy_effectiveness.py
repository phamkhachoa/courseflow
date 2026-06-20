from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import yaml

from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_suppression_policy_drill as drill,
)
from courseflow_ai_platform import (
    product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness as eff,
)
from courseflow_ai_platform.registry import load_yaml

build_effectiveness = (
    eff.build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_report
)
build_effectiveness_from_drill = eff.build_suppression_policy_effectiveness_report_from_drill
build_snapshot = (
    eff.build_product_readiness_freshness_response_slo_drift_suppression_policy_effectiveness_snapshot
)
build_drill = (
    drill.build_product_readiness_freshness_response_slo_drift_suppression_policy_drill_report
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_response_slo_drift_suppression_policy_effectiveness_is_monitored() -> None:
    report = build_effectiveness(ai_root(), generated_at="2026-06-17")

    assert report.monitor_status == "effectiveness_monitored"
    assert report.drill_status == "passed"
    assert report.policy_status == "suppression_policy_codified"
    assert report.rule_count == 1
    assert report.active_rule_count == 1
    assert report.signal_count == 4
    assert report.effective_signal_count == 4
    assert report.failed_signal_count == 0
    assert report.suppression_candidate_count == 3
    assert report.suppressed_signal_count == 3
    assert report.escalation_signal_count == 1
    assert report.escalation_preserved_count == 1
    assert report.suppression_effectiveness_pct == 100
    assert report.escalation_preservation_pct == 100
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "expand_product_readiness_response_slo_drift_suppression_policy_coverage",
    )
    assert {signal.signal_type for signal in report.signals} == {
        "noise_reduction",
        "escalation_preservation",
    }


def test_response_slo_drift_suppression_policy_effectiveness_blocks_on_drill() -> None:
    drill_report = build_drill(
        ai_root(),
        generated_at="2026-06-17",
    )
    report = build_effectiveness_from_drill(
        replace(drill_report, drill_status="blocked_by_policy"),
        generated_at="2026-06-17",
    )

    assert report.monitor_status == "blocked_by_drill"
    assert report.next_actions == (
        "monitor_product_readiness_response_slo_drift_suppression_policy_effectiveness",
    )


def test_response_slo_drift_suppression_policy_effectiveness_fails_lost_escalation() -> None:
    drill_report = build_drill(
        ai_root(),
        generated_at="2026-06-17",
    )
    lost_escalation = replace(
        drill_report.scenarios[-1],
        observed_decision="suppressed",
        observed_route="",
    )
    report = build_effectiveness_from_drill(
        replace(
            drill_report,
            scenarios=(*drill_report.scenarios[:-1], lost_escalation),
        ),
        generated_at="2026-06-17",
    )

    assert report.monitor_status == "effectiveness_failed"
    assert report.failed_signal_count == 1
    assert report.escalation_preservation_pct == 0


def test_response_slo_drift_suppression_policy_effectiveness_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1"
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


def test_response_slo_drift_suppression_policy_effectiveness_snapshot_matches() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-response-slo-drift-suppression-policy-effectiveness-v1.yaml"
    )
    generated = build_snapshot(root, generated_at="2026-06-17")

    assert checked_in == generated
