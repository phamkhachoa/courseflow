from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.governance_evaluation_ops import (
    build_governance_evaluation_ops_report,
    build_governance_evaluation_ops_snapshot,
    write_governance_evaluation_ops_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def test_governance_evaluation_ops_report_runs_release_gate_drills() -> None:
    report = build_governance_evaluation_ops_report(
        Path(__file__).resolve().parents[2],
        generated_at="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["opsStatus"] == "release_gate_observable"
    assert payload["routeCount"] == 3
    assert payload["evaluationCount"] == 20
    assert payload["promotionCount"] == 4
    assert payload["assessmentCount"] == 3
    assert payload["approvedCount"] == 1
    assert payload["reviewRequiredCount"] == 1
    assert payload["blockedCount"] == 1
    assert payload["directIdentifierRejectionCount"] == 1
    assert payload["secretValueRejectionCount"] == 1
    assert payload["unexpectedErrorCount"] == 0
    assert {item["decision"] for item in payload["drills"]} == {
        "approved",
        "blocked",
        "review_required",
    }


def test_governance_evaluation_ops_write_snapshot(tmp_path: Path) -> None:
    output_path = tmp_path / "governance-evaluation-service.yaml"

    written = write_governance_evaluation_ops_snapshot(
        Path(__file__).resolve().parents[2],
        output_path,
        generated_at="2026-06-17",
    )
    payload = load_yaml(written)

    assert written == output_path
    assert payload["report_id"] == "governance-evaluation-service-v1"
    assert payload["summary"]["ops_status"] == "release_gate_observable"
    assert payload["summary"]["assessment_count"] == 3


def test_governance_evaluation_ops_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "governance"
        / "reports"
        / "governance-evaluation-service-v1.yaml"
    )
    generated = build_governance_evaluation_ops_snapshot(
        ai_root,
        generated_at="2026-06-17",
    )

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["by_product"] == generated["by_product"]
    assert checked_in["by_use_case"] == generated["by_use_case"]
    assert checked_in["drills"] == generated["drills"]
