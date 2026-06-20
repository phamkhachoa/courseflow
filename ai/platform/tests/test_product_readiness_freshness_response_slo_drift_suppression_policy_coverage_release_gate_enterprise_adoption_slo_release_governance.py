from __future__ import annotations

from dataclasses import replace
from importlib import import_module
from pathlib import Path

import yaml

from courseflow_ai_platform.registry import load_yaml

gov = import_module(
    "courseflow_ai_platform."
    "product_readiness_freshness_response_slo_drift_suppression_policy_"
    "coverage_release_gate_enterprise_adoption_slo_release_governance"
)

build_governance = (
    gov.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_report
)
build_governance_from_slo = (
    gov.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_report_from_slo
)
build_snapshot = (
    gov.build_product_readiness_freshness_response_slo_drift_suppression_policy_coverage_release_gate_enterprise_adoption_slo_release_governance_snapshot
)


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_enterprise_adoption_slo_release_governance_is_attached() -> None:
    report = build_governance(ai_root(), generated_at="2026-06-17")

    assert report.release_governance_status == (
        "enterprise_adoption_slo_release_governance_attached"
    )
    assert report.slo_status == "adoption_slo_published"
    assert report.adoption_status == "adoption_monitored"
    assert report.enterprise_pattern_status == "enterprise_pattern_expanded"
    assert report.adoption_pct == 100
    assert report.target_adoption_pct == 100
    assert report.objective_count == 5
    assert report.met_objective_count == 5
    assert report.failed_objective_count == 0
    assert report.release_gate_count == 5
    assert report.attached_release_gate_count == 5
    assert report.failed_release_gate_count == 0
    assert report.review_cadence_days == 30
    assert report.tenant_safe is True
    assert report.raw_identifier_count == 0
    assert report.next_actions == (
        "exercise_enterprise_release_gate_pattern_adoption_slo_release_governance_drill",
    )


def test_enterprise_adoption_slo_release_governance_blocks_unpublished_slo() -> None:
    adoption_slo = (
        gov.build_enterprise_adoption_slo_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    report = build_governance_from_slo(
        replace(adoption_slo, slo_status="adoption_slo_at_risk"),
        generated_at="2026-06-17",
    )

    assert report.release_governance_status == "blocked_by_unpublished_adoption_slo"
    assert report.next_actions == (
        "attach_enterprise_release_gate_pattern_adoption_slo_to_release_governance",
    )


def test_enterprise_adoption_slo_release_governance_detects_attachment_gap() -> None:
    adoption_slo = (
        gov.build_enterprise_adoption_slo_report(
            ai_root(),
            generated_at="2026-06-17",
        )
    )
    report = build_governance_from_slo(
        replace(adoption_slo, met_objective_count=4, failed_objective_count=1),
        generated_at="2026-06-17",
    )

    assert report.release_governance_status == (
        "enterprise_adoption_slo_release_governance_attachment_incomplete"
    )
    assert report.failed_release_gate_count == 1
    assert report.gates[1].gate_id == (
        "enterprise-adoption-slo-objectives-release-governance-gate"
    )
    assert report.gates[1].attached is False


def test_enterprise_adoption_slo_release_governance_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_snapshot(ai_root(), generated_at="2026-06-17")
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert snapshot["report_id"] == (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-enterprise-adoption-slo-release-governance-v1"
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


def test_enterprise_adoption_slo_release_governance_raw_id_detector_ignores_labels() -> None:
    report = build_governance(ai_root(), generated_at="2026-06-17")
    leaked_gate = replace(report.gates[0], observed="tenant-lms")

    assert gov.count_raw_identifier_markers(report.gates) == 0
    assert (
        gov.count_raw_identifier_markers((leaked_gate, *report.gates[1:]))
        == 1
    )


def test_enterprise_adoption_slo_release_governance_snapshot_matches() -> None:
    root = ai_root()
    report_name = (
        "product-readiness-freshness-response-slo-drift-suppression-policy-"
        "coverage-release-gate-enterprise-adoption-slo-release-governance-v1.yaml"
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
