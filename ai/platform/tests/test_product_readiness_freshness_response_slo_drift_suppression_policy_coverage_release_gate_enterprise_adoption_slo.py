from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from pathlib import Path

import yaml

from courseflow_ai_platform.registry import load_yaml

slo = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_"
    "suppression_policy_coverage_release_gate_enterprise_adoption_slo"
)

build_slo = (
    slo.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_report
)
build_slo_from_adoption = (
    slo.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_report_from_adoption
)
build_snapshot = (
    slo.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_snapshot
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_enterprise_release_gate_pattern_adoption_slo_is_published() -> None:
    report = build_slo(ai_root(), generated_at="2026-06-17")

    assert report.slo_status == "adoption_slo_published"
    assert report.adoption_status == "adoption_monitored"
    assert report.enterprise_pattern_status == "enterprise_pattern_expanded"
    assert report.adoption_pct == 100
    assert report.target_adoption_pct == 100
    assert report.signal_count == 6
    assert report.adopted_signal_count == 6
    assert report.blocked_signal_count == 0
    assert report.non_lms_blueprint_count == 5
    assert report.non_lms_product_count == 4
    assert report.taxonomy_area_count == 9
    assert report.evaluation_gate_count == 36
    assert report.objective_count == 5
    assert report.met_objective_count == 5
    assert report.failed_objective_count == 0
    assert report.review_cadence_days == 30
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "attach_enterprise_release_gate_pattern_adoption_slo_to_release_governance",
    )


def test_enterprise_release_gate_pattern_adoption_slo_blocks_on_adoption_gap() -> None:
    adoption = (
        slo.build_enterprise_adoption_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    report = build_slo_from_adoption(
        replace(
            adoption,
            adoption_status="adoption_gap_detected",
            adoption_pct=83,
            adopted_signal_count=5,
            blocked_signal_count=1,
        ),
        generated_at="2026-06-17",
    )

    assert report.slo_status == "blocked_by_adoption_monitor"
    assert report.next_actions == (
        "publish_enterprise_release_gate_pattern_adoption_slo",
    )


def test_enterprise_release_gate_pattern_adoption_slo_detects_span_risk() -> None:
    adoption = (
        slo.build_enterprise_adoption_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    report = build_slo_from_adoption(
        replace(adoption, non_lms_product_count=3),
        generated_at="2026-06-17",
    )

    assert report.slo_status == "adoption_slo_at_risk"
    assert report.failed_objective_count == 1
    assert report.objectives[1].objective_id == "enterprise-product-span-slo"
    assert report.objectives[1].met is False


def test_enterprise_release_gate_pattern_adoption_slo_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-enterprise-adoption-slo-v1"
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


def test_enterprise_release_gate_pattern_adoption_slo_raw_id_detector_ignores_labels() -> None:
    report = build_slo(ai_root(), generated_at="2026-06-17")
    leaked_objective = replace(report.objectives[0], observed="tenant-lms")

    assert slo.count_raw_identifier_markers(report.objectives) == 0
    assert (
        slo.count_raw_identifier_markers(
            (leaked_objective, *report.objectives[1:])
        )
        == 1
    )


def test_enterprise_release_gate_pattern_adoption_slo_snapshot_matches() -> None:
    root = ai_root()
    report_name = (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-enterprise-adoption-slo-v1.yaml"
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
