from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.coverage_taxonomy import (
    ALLOWED_RUNTIME_STATUSES,
    REQUIRED_TAXONOMY_AREAS,
    validate_coverage_taxonomy,
)


def test_business_capability_coverage_validates_full_ai_spectrum() -> None:
    report = validate_coverage_taxonomy(Path(__file__).resolve().parents[2])
    payload = report.to_dict()
    areas = {module["taxonomyArea"] for module in payload["modules"]}

    assert report.module_count >= 13
    assert report.required_area_count == len(REQUIRED_TAXONOMY_AREAS)
    assert report.missing_required_areas == ()
    assert REQUIRED_TAXONOMY_AREAS <= areas
    assert report.lms_module_count == report.module_count
    assert report.enterprise_module_count == report.module_count
    assert report.implemented_baseline_count >= 2
    assert report.executable_gate_count >= 5
    assert report.privacy_gated_count == 0
    assert report.simulator_required_count == 0
    assert report.evaluation_gate_count >= 18
    assert set(report.runtime_status_counts) == ALLOWED_RUNTIME_STATUSES
    assert report.runtime_status_counts["service_integrated"] == 14
    assert report.runtime_status_counts["runtime_library"] == 0
    assert report.runtime_status_counts["shadow_artifact"] == 0
    assert report.runtime_status_counts["registry_only"] == 0


def test_business_capability_coverage_exposes_user_facing_statuses() -> None:
    report = validate_coverage_taxonomy(Path(__file__).resolve().parents[2])
    statuses = {module.coverage_status for module in report.modules}
    runtime_statuses = {module.runtime_status for module in report.modules}

    assert {
        "implemented_baseline",
        "executable_gate",
    } <= statuses
    assert "privacy_gated" not in statuses
    assert "simulator_required" not in statuses
    assert "registered_roadmap" not in statuses
    assert runtime_statuses == {"service_integrated"}
    assert "runtime_library" not in runtime_statuses
    assert "registry_only" not in runtime_statuses
    assert "shadow_artifact" not in runtime_statuses
