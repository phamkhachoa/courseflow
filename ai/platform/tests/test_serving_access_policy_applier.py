from __future__ import annotations

from pathlib import Path

from courseflow_ai_platform.registry import load_yaml
from courseflow_ai_platform.serving_access_apply_ledger import stable_sha256
from courseflow_ai_platform.serving_access_policy_applier import (
    build_serving_access_policy_apply_report,
    write_serving_access_policy_from_ledger,
)


def test_serving_access_policy_applier_reports_ready_to_write() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_policy_apply_report(ai_root)

    assert report.apply_status == "ready_to_write"
    assert report.ready_application_count == 1
    assert report.blocked_count == 0
    assert report.checksum_mismatch_count == 0
    assert report.planned_operation_count == 1
    assert report.active_policy_would_change is True
    assert report.ready_application_ids == (
        "lms-sequence-risk-sandbox-tenant-apply-20260617",
    )
    assert report.validation_errors == ()


def test_serving_access_policy_applier_writes_to_explicit_target_without_mutating_active_policy(
    tmp_path: Path,
) -> None:
    ai_root = Path(__file__).resolve().parents[2]
    output_path = tmp_path / "model-serving-access-policy.yaml"

    result = write_serving_access_policy_from_ledger(
        ai_root,
        output_policy_path=output_path,
    )

    assert result.output_policy_path == str(output_path)
    written_policy = load_yaml(output_path)
    assert stable_sha256(written_policy) == result.applied_policy_sha256
    written_lms = find_principal(written_policy, "service:lms-courseflow-serving")
    assert written_lms["tenant_ids"] == ["tenant-lms", "tenant-lms-sandbox"]

    active_policy = load_yaml(
        ai_root / "platform" / "governance" / "policies" / "model-serving-access-policy.yaml"
    )
    active_lms = find_principal(active_policy, "service:lms-courseflow-serving")
    assert active_lms["tenant_ids"] == ["tenant-lms"]


def test_serving_access_policy_applier_report_targets_active_policy_by_default() -> None:
    ai_root = Path(__file__).resolve().parents[2]

    report = build_serving_access_policy_apply_report(ai_root)

    assert report.source_policy_path.endswith(
        "platform/governance/policies/model-serving-access-policy.yaml"
    )
    assert report.target_policy_path == report.source_policy_path


def find_principal(policy: dict[str, object], principal_id: str) -> dict[str, object]:
    principals = policy["principals"]
    assert isinstance(principals, list)
    for principal in principals:
        assert isinstance(principal, dict)
        if principal["principal_id"] == principal_id:
            return principal
    raise AssertionError(f"principal not found: {principal_id}")
