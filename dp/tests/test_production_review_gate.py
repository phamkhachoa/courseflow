from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from enterprise_dp.production_review_gate import build_production_review_gate_report


def test_source_onboarding_gate_passes_for_runtime_attested_full_p0_coverage(tmp_path: Path) -> None:
    manifest_path = write_review_manifest(tmp_path, source_onboarding_ready=True)

    report = build_production_review_gate_report(
        manifest_path,
        profile="source-onboarding",
        environment="staging",
        generated_at="2026-06-16T12:30:00Z",
    )

    assert report["passed"] is True
    assert report["failed_check_count"] == 0


def test_source_onboarding_gate_fails_closed_for_current_coverage_gap(tmp_path: Path) -> None:
    manifest_path = write_review_manifest(tmp_path, source_onboarding_ready=False)

    report = build_production_review_gate_report(
        manifest_path,
        profile="source-onboarding",
        environment="staging",
        generated_at="2026-06-16T12:30:00Z",
    )

    failed = {item["name"] for item in report["failed_checks"]}
    assert report["passed"] is False
    assert "source_activation_ops_passed" in failed
    assert "source_onboarding_release_gate_passed" in failed
    assert "source_activation_no_p0_unactivated" in failed
    assert "source_activation_no_pointer_issue" in failed
    assert "source_activation_no_evidence_integrity_issue" in failed
    assert "source_onboarding_no_p0_backlog" in failed
    assert report["summary"]["source_onboarding_release_gate_passed"] is False


def test_production_review_gate_cli_returns_nonzero_and_writes_artifact_for_failed_gate(tmp_path: Path) -> None:
    manifest_path = write_review_manifest(tmp_path, source_onboarding_ready=False)
    output_path = tmp_path / "gates" / "source-onboarding-gate.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise_dp.cli",
            "production-review-gate",
            "--manifest",
            str(manifest_path),
            "--profile",
            "source-onboarding",
            "--environment",
            "staging",
            "--output",
            str(output_path),
            "--generated-at",
            "2026-06-16T12:30:00Z",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert output_path.is_file()
    stdout = json.loads(completed.stdout)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout["passed"] is False
    assert artifact["artifact_type"] == "production_review_gate_report.v1"
    assert artifact["profile"] == "source-onboarding"
    assert artifact["passed"] is False


def test_code_control_plane_gate_uses_review_pack_verdict(tmp_path: Path) -> None:
    manifest_path = write_review_manifest(
        tmp_path,
        source_onboarding_ready=True,
        code_control_plane_ready=False,
    )

    report = build_production_review_gate_report(
        manifest_path,
        profile="code-control-plane",
        environment="staging",
        generated_at="2026-06-16T12:30:00Z",
    )

    failed = {item["name"] for item in report["failed_checks"]}
    assert report["passed"] is False
    assert failed == {"code_control_plane_ready_excluding_live_infra"}


def write_review_manifest(
    tmp_path: Path,
    *,
    source_onboarding_ready: bool,
    code_control_plane_ready: bool = True,
) -> Path:
    summary = source_onboarding_summary(source_onboarding_ready)
    manifest = {
        "artifact_type": "production_review_pack.v1",
        "report_version": 1,
        "generated_at": "2026-06-16T12:05:00Z",
        "environment": "staging",
        "verdict": {
            "partner_review_ready": True,
            "code_control_plane_ready_excluding_live_infra": code_control_plane_ready,
            "production_ready": False,
            "readiness_state": "not_ready",
        },
        "summary": summary,
        "p0_gap_backlog": [] if source_onboarding_ready else [
            {
                "priority": "P0",
                "source": "control_tower_blocker",
                "gap": "source_activation_ops_p0_clear",
                "capability_id": "source-onboarding",
            }
        ],
    }
    path = tmp_path / "production-review-pack.json"
    path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return path


def source_onboarding_summary(ready: bool) -> dict[str, object]:
    if ready:
        return {
            "control_tower_blocker_count": 3,
            "source_activation_ops_attached": True,
            "source_activation_ops_environment": "staging",
            "source_activation_ops_mode": "runtime_attested",
            "source_activation_ops_readiness_state": "production_like_ready",
            "source_activation_ops_passed": True,
            "source_onboarding_release_gate_passed": True,
            "source_activation_ops_p0_source_count": 8,
            "source_activation_ops_p0_active_count": 8,
            "source_activation_ops_p0_unactivated_count": 0,
            "source_activation_ops_p0_activation_gap_count": 0,
            "source_activation_ops_p0_critical_issue_count": 0,
            "source_activation_ops_critical_issue_count": 0,
            "source_activation_ops_pointer_issue_count": 0,
            "source_activation_ops_registry_drift_count": 0,
            "source_activation_ops_runtime_readiness_issue_count": 0,
            "source_activation_ops_p0_runtime_readiness_issue_count": 0,
            "source_activation_ops_evidence_integrity_issue_count": 0,
            "source_activation_ops_p0_evidence_integrity_issue_count": 0,
        }
    return {
        "control_tower_blocker_count": 60,
        "source_activation_ops_attached": True,
        "source_activation_ops_environment": "staging",
        "source_activation_ops_mode": "metadata_preflight",
        "source_activation_ops_readiness_state": "not_ready",
        "source_activation_ops_passed": False,
        "source_onboarding_release_gate_passed": False,
        "source_activation_ops_p0_source_count": 8,
        "source_activation_ops_p0_active_count": 1,
        "source_activation_ops_p0_unactivated_count": 7,
        "source_activation_ops_p0_activation_gap_count": 7,
        "source_activation_ops_p0_critical_issue_count": 8,
        "source_activation_ops_critical_issue_count": 8,
        "source_activation_ops_pointer_issue_count": 1,
        "source_activation_ops_registry_drift_count": 0,
        "source_activation_ops_runtime_readiness_issue_count": 0,
        "source_activation_ops_p0_runtime_readiness_issue_count": 0,
        "source_activation_ops_evidence_integrity_issue_count": 1,
        "source_activation_ops_p0_evidence_integrity_issue_count": 1,
    }
