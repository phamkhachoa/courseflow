from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.capability_taxonomy import (
    REQUIRED_CAPABILITY_AREAS,
    build_ai_capability_taxonomy_report,
    build_ai_capability_taxonomy_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def test_ai_capability_taxonomy_covers_model_and_platform_areas() -> None:
    report = build_ai_capability_taxonomy_report(Path(__file__).resolve().parents[2])
    payload = report.to_dict()

    assert payload["areaCount"] == 15
    assert payload["requiredAreaCount"] == len(REQUIRED_CAPABILITY_AREAS)
    assert payload["requiredAreaCoveredCount"] == 13
    assert payload["missingRequiredAreas"] == []
    assert payload["modelAreaCount"] == 10
    assert payload["platformAreaCount"] == 5
    assert payload["p1GapAreaCount"] == 0
    assert payload["byAreaType"] == {"model": 10, "platform": 5}
    assert payload["byRuntimeStatus"] == {
        "runtime_library": 1,
        "service_integrated": 12,
        "tooling": 2,
    }


def test_ai_capability_taxonomy_exposes_enterprise_platform_controls() -> None:
    report = build_ai_capability_taxonomy_report(Path(__file__).resolve().parents[2])
    areas = {area.area_id: area for area in report.areas}

    assert areas["responsible_ai"].area_type == "platform"
    assert areas["responsible_ai"].runtime_status == "service_integrated"
    assert areas["responsible_ai"].capability_count >= 4
    assert areas["mlops"].gap_count >= 1
    assert areas["feature_store"].readiness_status == "design_ready"
    assert areas["evaluation"].evaluation_gate_count >= 4
    assert areas["evaluation"].runtime_status == "service_integrated"
    assert areas["serving"].runtime_status == "runtime_library"


def test_ai_capability_taxonomy_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "coverage"
        / "reports"
        / "ai-capability-taxonomy-v1.yaml"
    )
    generated = build_ai_capability_taxonomy_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["by_area_type"] == generated["by_area_type"]
    assert checked_in["by_runtime_status"] == generated["by_runtime_status"]
    assert checked_in["areas"] == generated["areas"]
