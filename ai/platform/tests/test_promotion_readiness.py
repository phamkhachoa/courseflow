from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.promotion_readiness import (
    build_promotion_readiness_report,
    build_promotion_readiness_snapshot,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml


def test_promotion_readiness_projects_admin_ops_release_state() -> None:
    report = build_promotion_readiness_report(Path(__file__).resolve().parents[2])

    assert report.promotion_count == 4
    assert report.ready_count == 4
    assert report.blocked_count == 0
    assert report.active_count == 1
    assert report.approved_count == 1
    assert report.shadow_count == 2
    assert report.non_lms_count == 2
    assert report.required_gate_count == 7
    assert report.gate_ready_count == report.required_gate_count
    assert report.rollback_required_count == 2
    assert report.rollback_ready_count == 2
    assert report.maker_checker_required is True
    assert report.maker_checker_satisfied_count == report.promotion_count
    assert report.max_gate_age_days == 30
    assert report.stale_gate_count == 0
    assert report.missing_gate_evaluated_at_count == 0
    assert report.max_artifact_age_days == 90
    assert report.stale_artifact_count == 0
    assert report.missing_artifact_created_at_count == 0


def test_promotion_readiness_items_expose_stage_and_gate_details() -> None:
    report = build_promotion_readiness_report(Path(__file__).resolve().parents[2])
    items = {item.promotion_id: item for item in report.items}

    recommendation = items["recommendation-item-cf-v1-active-baseline"]
    assert recommendation.stage_group == "active"
    assert recommendation.ready_for_stage is True
    assert recommendation.rollback_required is True
    assert recommendation.rollback_ready is True
    assert recommendation.blocked_reasons == ()
    assert recommendation.gates[0].status == "accepted_baseline"

    support = items["support-agent-assist-baseline-approved"]
    assert support.is_non_lms is True
    assert support.stage_group == "approved"
    assert support.required_gate_count == 2
    assert support.gate_ready_count == 2

    course_vector = items["course-content-vector-index-shadow"]
    assert course_vector.stage_group == "shadow"
    assert course_vector.rollback_required is False
    assert course_vector.rollback_ready is True
    assert {gate.status for gate in course_vector.gates} == {
        "accepted_contract_baseline",
        "accepted_shadow_baseline",
    }


def test_promotion_readiness_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "artifacts" / "promotions" / "reports" / (
            "promotion-readiness-v1.yaml"
        )
    )
    generated = build_promotion_readiness_snapshot(ai_root, generated_at="2026-06-16")

    assert checked_in == generated
    assert checked_in["action_queue"]["active_monitoring"] == [
        "recommendation-item-cf-v1-active-baseline"
    ]
    assert checked_in["action_queue"]["ready_to_activate"] == [
        "support-agent-assist-baseline-approved"
    ]
    assert checked_in["action_queue"]["blocked"] == []
    assert checked_in["freshness"]["max_gate_age_days"] == 30
    assert checked_in["freshness"]["stale_gate_count"] == 0
    assert checked_in["freshness"]["max_artifact_age_days"] == 90
    assert checked_in["freshness"]["stale_artifact_count"] == 0
    assert checked_in["items"][0]["artifact_freshness"]["age_days"] == 0
    assert checked_in["items"][0]["gate_readiness"]["gates"][0]["age_days"] == 0


def test_promotion_readiness_marks_unaccepted_gate_blocked(tmp_path: Path) -> None:
    write_minimal_promotion_tree(tmp_path, gate_status="pending_review")

    report = build_promotion_readiness_report(tmp_path)

    assert report.promotion_count == 1
    assert report.ready_count == 0
    assert report.blocked_count == 1
    assert report.gate_ready_count == 0
    assert report.items[0].ready_for_stage is False
    assert report.items[0].blocked_reasons == ("gate_not_ready",)


def test_promotion_readiness_marks_stale_gate_blocked(tmp_path: Path) -> None:
    write_minimal_promotion_tree(
        tmp_path,
        gate_status="accepted_baseline",
        gate_evaluated_at="2026-01-01",
        max_gate_age_days=30,
    )

    report = build_promotion_readiness_report(tmp_path, as_of="2026-06-16")

    assert report.promotion_count == 1
    assert report.ready_count == 0
    assert report.blocked_count == 1
    assert report.gate_ready_count == 0
    assert report.stale_gate_count == 1
    assert report.items[0].gates[0].status_ready is True
    assert report.items[0].gates[0].fresh is False
    assert report.items[0].blocked_reasons == ("gate_evidence_stale",)


def test_promotion_readiness_marks_stale_artifact_blocked(tmp_path: Path) -> None:
    write_minimal_promotion_tree(
        tmp_path,
        artifact_created_at="2026-01-01",
        gate_evaluated_at="2026-06-16",
        max_artifact_age_days=30,
        max_gate_age_days=30,
    )

    report = build_promotion_readiness_report(tmp_path, as_of="2026-06-16")

    assert report.promotion_count == 1
    assert report.ready_count == 0
    assert report.blocked_count == 1
    assert report.stale_artifact_count == 1
    assert report.stale_gate_count == 0
    assert report.items[0].artifact_fresh is False
    assert report.items[0].gates[0].fresh is True
    assert report.items[0].blocked_reasons == ("artifact_evidence_stale",)


def test_promotion_readiness_rejects_unknown_artifact(tmp_path: Path) -> None:
    write_minimal_promotion_tree(tmp_path, artifact_id="missing-artifact")

    with pytest.raises(RegistryValidationError, match="unknown artifact_id"):
        build_promotion_readiness_report(tmp_path)


def write_minimal_promotion_tree(
    root: Path,
    *,
    artifact_id: str = "test-artifact",
    artifact_created_at: str | None = None,
    gate_status: str = "accepted_baseline",
    gate_evaluated_at: str | None = None,
    max_artifact_age_days: int | None = None,
    max_gate_age_days: int | None = None,
) -> None:
    manifest_dir = root / "platform" / "artifacts" / "manifests"
    promotion_dir = root / "platform" / "artifacts" / "promotions"
    report_dir = root / "platform" / "evaluation" / "reports"
    manifest_dir.mkdir(parents=True)
    promotion_dir.mkdir(parents=True)
    report_dir.mkdir(parents=True)

    (manifest_dir / "test-artifact.yaml").write_text(
        f"""
version: 1
artifact_id: test-artifact
model_id: test-model-v1
artifact_type: source_algorithm
product: support-platform
use_case_id: support-test-use-case
{f'created_at: "{artifact_created_at}"' if artifact_created_at else ''}
""".lstrip(),
        encoding="utf-8",
    )
    (report_dir / "test-eval.yaml").write_text(
        f"""
version: 1
status: {gate_status}
{f'evaluated_at: "{gate_evaluated_at}"' if gate_evaluated_at else ''}
""".lstrip(),
        encoding="utf-8",
    )
    readiness_lines: list[str] = []
    if max_gate_age_days is not None:
        readiness_lines.extend(
            [
                f"    max_gate_age_days: {max_gate_age_days}",
                "    stale_gate_blocks_release: true",
            ]
        )
    if max_artifact_age_days is not None:
        readiness_lines.extend(
            [
                f"    max_artifact_age_days: {max_artifact_age_days}",
                "    stale_artifact_blocks_release: true",
            ]
        )
    readiness_policy = (
        "\n  readiness:\n" + "\n".join(readiness_lines)
        if readiness_lines
        else ""
    )
    (promotion_dir / "registry.yaml").write_text(
        f"""
version: 1
owner: ai-platform
policy:
  maker_checker_required: true
{readiness_policy.rstrip()}
  require_rollback_target_for:
    - active_baseline
  allowed_stages:
    - shadow
    - active_baseline
promotions:
  - promotion_id: test-promotion
    artifact_id: {artifact_id}
    artifact_manifest: platform/artifacts/manifests/test-artifact.yaml
    product: support-platform
    use_case_id: support-test-use-case
    stage: shadow
    requested_by: ai-engineering
    approved_by: governance-reviewer
    approved_at: "2026-06-16"
    rollback_target_artifact_id: test-artifact
    required_gates:
      - platform/evaluation/reports/test-eval.yaml
""".lstrip(),
        encoding="utf-8",
    )
