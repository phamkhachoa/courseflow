from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from courseflow_ai_platform.llm_provider_adapter import (
    load_llm_adapter_access_policy,
    load_llm_provider_ops_policy,
)
from courseflow_ai_platform.llm_provider_readiness import (
    build_llm_provider_readiness_report_from_policy,
)
from courseflow_ai_platform.llm_provider_runtime_probes import (
    build_llm_provider_runtime_probe_report_from_policy,
)
from courseflow_ai_platform.llm_provider_secret_rotation import (
    build_llm_provider_secret_rotation_report,
    build_llm_provider_secret_rotation_report_from_policy,
    build_llm_provider_secret_rotation_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_llm_provider_secret_rotation_reports_contract_stub_controls() -> None:
    report = build_llm_provider_secret_rotation_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["secretRotationStatus"] == "contract_stub_rotation_controls_ready"
    assert payload["providerCount"] == 2
    assert payload["contractStubProviderCount"] == 2
    assert payload["liveProviderCount"] == 0
    assert payload["blockedProviderCount"] == 0
    assert payload["secretManagerBindingCount"] == 0
    assert payload["rotationAutomationProviderCount"] == 0
    assert payload["rotationEvidenceProviderCount"] == 0
    assert payload["plaintextSecretCount"] == 0
    assert payload["tenantSafe"] is True
    assert payload["rawIdentifierCount"] == 0
    assert all(
        item["rotationStatus"] == "contract_stub_not_required"
        for item in payload["items"]
    )


def test_llm_provider_secret_rotation_blocks_plaintext_live_secret() -> None:
    root = ai_root()
    provider_id = "contract-stub-llm-v1"
    credential_ref = "vault://llm/providers/primary"
    access_policy, ops_policy = live_policy_pair(
        root,
        provider_id=provider_id,
        credential_ref=credential_ref,
    )
    readiness_policy = live_readiness_policy(
        root,
        provider_id=provider_id,
        credential_ref=credential_ref,
    )
    probe_policy = live_probe_policy(root, provider_id=provider_id)
    secret_policy = live_secret_rotation_policy(
        root,
        provider_id=provider_id,
        secret_ref="sk-live-secret",
    )
    readiness_report = build_llm_provider_readiness_report_from_policy(
        readiness_policy,
        access_policy,
        ops_policy,
        generated_at="2026-06-17",
    )
    runtime_report = build_llm_provider_runtime_probe_report_from_policy(
        probe_policy,
        access_policy,
        ops_policy,
        readiness_report,
        generated_at="2026-06-17",
    )

    report = build_llm_provider_secret_rotation_report_from_policy(
        secret_policy,
        access_policy,
        ops_policy,
        readiness_report,
        runtime_report,
        generated_at="2026-06-17",
    )

    assert report.secret_rotation_status == "blocked"
    assert report.blocked_provider_count == 1
    assert report.plaintext_secret_count == 1
    item = next(item for item in report.items if item.provider_id == provider_id)
    assert item.secret_ref_scheme == "plaintext"
    assert "secret ref must not be plaintext" in item.validation_errors


def test_llm_provider_secret_rotation_accepts_live_vault_binding() -> None:
    root = ai_root()
    provider_id = "contract-stub-llm-v1"
    credential_ref = "vault://llm/providers/primary"
    access_policy, ops_policy = live_policy_pair(
        root,
        provider_id=provider_id,
        credential_ref=credential_ref,
    )
    readiness_policy = live_readiness_policy(
        root,
        provider_id=provider_id,
        credential_ref=credential_ref,
    )
    probe_policy = live_probe_policy(root, provider_id=provider_id)
    secret_policy = live_secret_rotation_policy(
        root,
        provider_id=provider_id,
        secret_ref=credential_ref,
    )
    readiness_report = build_llm_provider_readiness_report_from_policy(
        readiness_policy,
        access_policy,
        ops_policy,
        generated_at="2026-06-17",
    )
    runtime_report = build_llm_provider_runtime_probe_report_from_policy(
        probe_policy,
        access_policy,
        ops_policy,
        readiness_report,
        generated_at="2026-06-17",
    )

    report = build_llm_provider_secret_rotation_report_from_policy(
        secret_policy,
        access_policy,
        ops_policy,
        readiness_report,
        runtime_report,
        generated_at="2026-06-17",
    )

    assert report.secret_rotation_status == "live_rotation_ready"
    assert report.live_provider_count == 1
    assert report.secret_manager_binding_count == 1
    assert report.secret_ref_resolved_count == 1
    assert report.rotation_automation_provider_count == 1
    assert report.rotation_evidence_provider_count == 1
    assert report.rotation_drill_passed_count == 1
    item = next(item for item in report.items if item.provider_id == provider_id)
    assert item.rotation_status == "live_rotation_ready"
    assert item.validation_errors == ()


def test_llm_provider_secret_rotation_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "governance"
        / "reports"
        / "llm-provider-secret-rotation-v1.yaml"
    )
    generated = build_llm_provider_secret_rotation_snapshot(
        root,
        generated_at="2026-06-17",
    )

    assert checked_in == generated


def live_policy_pair(
    root: Path,
    *,
    provider_id: str,
    credential_ref: str,
):
    access_policy = load_llm_adapter_access_policy(root)
    ops_policy = load_llm_provider_ops_policy(root, access_policy)
    access_policy = replace(
        access_policy,
        providers={
            **access_policy.providers,
            provider_id: replace(
                access_policy.providers[provider_id],
                network_enabled=True,
            ),
        },
    )
    ops_config = ops_policy.providers[provider_id]
    ops_policy = replace(
        ops_policy,
        providers={
            **ops_policy.providers,
            provider_id: replace(
                ops_config,
                credential_ref=credential_ref,
                cost=replace(
                    ops_config.cost,
                    input_micros_per_1k_tokens=500,
                    output_micros_per_1k_tokens=1500,
                ),
            ),
        },
    )
    return access_policy, ops_policy


def live_readiness_policy(
    root: Path,
    *,
    provider_id: str,
    credential_ref: str,
) -> dict:
    policy = load_yaml(
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-credential-readiness.yaml"
    )
    return {
        **policy,
        "providers": [
            {
                **row,
                "credential_mode": "live_secret_ref",
                "credential_ref": credential_ref,
                "rotation_required": True,
                "rotation_days": 30,
                "deployment_checks": policy["required_live_deployment_checks"],
            }
            if row["provider_id"] == provider_id
            else row
            for row in policy["providers"]
        ],
    }


def live_probe_policy(root: Path, *, provider_id: str) -> dict:
    policy = load_yaml(
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-runtime-probe-policy.yaml"
    )
    return {
        **policy,
        "providers": [
            {
                **row,
                "probe_mode": "live_runtime_probe",
                "runtime_secret_probe": "passed",
                "runtime_secret_ref_resolved": True,
                "network_egress_allowlisted": True,
                "sample_request_count": 1,
                "p95_latency_ms": 250,
                "estimated_cost_micros": 42,
                "probe_checks": policy["required_live_probe_checks"],
            }
            if row["provider_id"] == provider_id
            else row
            for row in policy["providers"]
        ],
    }


def live_secret_rotation_policy(
    root: Path,
    *,
    provider_id: str,
    secret_ref: str,
) -> dict:
    policy = load_yaml(
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-secret-rotation-policy.yaml"
    )
    return {
        **policy,
        "providers": [
            {
                **row,
                "binding_mode": "live_secret_manager",
                "secret_ref": secret_ref,
                "secret_ref_resolved": True,
                "rotation_interval_days": 30,
                "rotation_automation_ref": (
                    "rotation://ai-platform/llm-provider/primary"
                ),
                "rotation_evidence_ref": (
                    "evidence://ai-platform/llm-provider/primary/rotation"
                ),
                "rotation_drill_status": "passed",
                "control_checks": policy["required_live_controls"],
            }
            if row["provider_id"] == provider_id
            else row
            for row in policy["providers"]
        ],
    }
