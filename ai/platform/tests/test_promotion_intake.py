from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.promotion_intake import (
    build_promotion_intake_report,
    build_promotion_intake_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def test_promotion_intake_projects_request_queue() -> None:
    report = build_promotion_intake_report(Path(__file__).resolve().parents[2])
    queue = report.to_dict()["actionQueue"]

    assert report.request_count == 5
    assert report.ready_count == 3
    assert report.waiting_count == 2
    assert report.non_lms_count == 4
    assert report.artifact_known_count == 3
    assert report.gate_count == 7
    assert report.ready_gate_count == 5
    assert queue["readyForApproval"] == [
        "support-agent-assist-active-request",
        "finance-document-intelligence-privacy-request",
        "operations-routing-rl-simulator-request",
    ]
    assert queue["waitingForArtifact"] == ["lms-at-risk-baseline-shadow-request"]
    assert queue["waitingForEvaluation"] == ["finance-anomaly-shadow-request"]
    assert queue["waitingForPrivacyReview"] == []
    assert queue["waitingForSimulator"] == []
    assert queue["blocked"] == []


def test_promotion_intake_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root / "platform" / "artifacts" / "promotions" / "reports" / (
            "promotion-intake-v1.yaml"
        )
    )
    generated = build_promotion_intake_snapshot(ai_root, generated_at="2026-06-16")

    assert checked_in == generated
    assert checked_in["summary"]["ready_count"] == 3
    assert checked_in["action_queue"]["ready_for_approval"] == [
        "support-agent-assist-active-request",
        "finance-document-intelligence-privacy-request",
        "operations-routing-rl-simulator-request",
    ]


def test_promotion_intake_ready_request_with_missing_artifact_is_blocked(
    tmp_path: Path,
) -> None:
    write_minimal_intake_tree(tmp_path)

    report = build_promotion_intake_report(tmp_path)

    assert report.request_count == 1
    assert report.ready_count == 0
    assert report.blocked_count == 1
    assert report.requests[0].blocking_reasons == (
        "artifact_manifest_missing",
        "evaluation_gate_not_ready",
    )


def write_minimal_intake_tree(root: Path) -> None:
    (root / "platform" / "artifacts" / "promotions").mkdir(parents=True)
    (root / "platform" / "artifacts" / "manifests").mkdir(parents=True)
    (root / "products").mkdir()
    (root / "use-cases").mkdir()

    (root / "products" / "registry.yaml").write_text(
        """
version: 1
owner: ai-platform
products:
  - id: support-platform
    name: Support Platform
""".lstrip(),
        encoding="utf-8",
    )
    (root / "use-cases" / "registry.yaml").write_text(
        """
version: 1
owner: ai-platform
use_cases:
  - id: support-agent-assist
    name: Support Agent Assist
    status: proposed
    product: support-platform
""".lstrip(),
        encoding="utf-8",
    )
    (root / "platform" / "artifacts" / "promotions" / "registry.yaml").write_text(
        """
version: 1
owner: ai-platform
policy:
  maker_checker_required: true
  require_rollback_target_for: []
  allowed_stages:
    - shadow
promotions: []
""".lstrip(),
        encoding="utf-8",
    )
    (root / "platform" / "artifacts" / "promotions" / "requests.yaml").write_text(
        """
version: 1
owner: ai-platform
policy:
  allowed_statuses:
    - ready_for_approval
  allowed_request_types:
    - promote_to_shadow
  allowed_requested_stages:
    - shadow
  ready_statuses:
    - ready_for_approval
requests:
  - request_id: missing-artifact-request
    request_type: promote_to_shadow
    product: support-platform
    use_case_id: support-agent-assist
    artifact_id: missing-artifact
    requested_stage: shadow
    status: ready_for_approval
    submitted_by: support-product
    business_owner: support-product
    submitted_at: "2026-06-16"
    required_gates:
      - platform/evaluation/reports/missing.yaml
""".lstrip(),
        encoding="utf-8",
    )
