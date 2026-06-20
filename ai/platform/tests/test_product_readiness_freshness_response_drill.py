from __future__ import annotations

from pathlib import Path

import yaml

from courseflow_ai_platform.product_readiness_freshness_incidents import (
    build_product_readiness_freshness_incident_export,
)
from courseflow_ai_platform.product_readiness_freshness_response_drill import (
    build_product_readiness_freshness_incident_response_drill_report,
    build_product_readiness_freshness_incident_response_drill_report_from_spec,
    build_product_readiness_freshness_incident_response_drill_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_product_readiness_freshness_response_drill_passes_baseline() -> None:
    report = build_product_readiness_freshness_incident_response_drill_report(
        ai_root(),
        generated_at="2026-06-17",
    )

    assert report.drill_status == "passed"
    assert report.current_incident_count == 0
    assert report.current_open_incident_count == 0
    assert report.scenario_count == 5
    assert report.p0_scenario_count == 1
    assert report.p1_scenario_count == 4
    assert report.failed_count == 0
    assert report.response_step_count == 8
    assert report.tenant_safe is True


def test_product_readiness_freshness_response_drill_validates_routes_and_steps() -> None:
    report = build_product_readiness_freshness_incident_response_drill_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    scenarios = {scenario.scenario_id: scenario for scenario in report.scenarios}

    route = scenarios["route-unreachable-p0"]
    assert route.condition == "product_readiness_runtime_route_unreachable"
    assert route.expected_severity == "p0"
    assert route.observed_owner_role == "Admin/Ops"
    assert route.observed_action == "triage_product_readiness_runtime_route"
    assert route.incident_status == "open"
    assert route.application_ref.startswith("product-readiness:")
    assert "detect" in route.runbook_step_ids
    assert "close" in route.runbook_step_ids

    audit_gap = scenarios["runtime-audit-gap-p1"]
    assert audit_gap.expected_severity == "p1"
    assert audit_gap.observed_action == "restore_product_readiness_audit_coverage"


def test_product_readiness_freshness_response_drill_blocks_missing_runbook_step() -> None:
    root = ai_root()
    runbook = load_yaml(
        root
        / "platform"
        / "operations"
        / "runbooks"
        / "product-readiness-freshness-incident-response-v1.yaml"
    )
    runbook["required_steps"] = [
        step for step in runbook["required_steps"] if step["step_id"] != "close"
    ]
    current_export = build_product_readiness_freshness_incident_export(
        root,
        as_of="2026-06-17",
    )

    report = build_product_readiness_freshness_incident_response_drill_report_from_spec(
        runbook,
        current_export=current_export,
        current_freshness_report=None,
        generated_at="2026-06-17",
        root=root,
    )

    assert report.drill_status == "blocked"
    assert report.failed_count == 5
    assert all(
        "runbook missing required steps: close" in scenario.validation_errors
        for scenario in report.scenarios
    )


def test_product_readiness_freshness_response_drill_snapshot_suppresses_raw_ids() -> None:
    snapshot = build_product_readiness_freshness_incident_response_drill_snapshot(
        ai_root(),
        generated_at="2026-06-17",
    )
    serialized = yaml.safe_dump(snapshot, sort_keys=True).lower()

    assert (
        snapshot["report_id"]
        == "product-readiness-freshness-incident-response-drill-v1"
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


def test_product_readiness_freshness_response_drill_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "product-readiness-freshness-incident-response-drill-v1.yaml"
    )
    generated = build_product_readiness_freshness_incident_response_drill_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated
