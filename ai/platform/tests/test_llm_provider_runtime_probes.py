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
    build_llm_provider_runtime_probe_report,
    build_llm_provider_runtime_probe_report_from_policy,
    build_llm_provider_runtime_probe_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_llm_provider_runtime_probes_report_contract_stub_observability() -> None:
    report = build_llm_provider_runtime_probe_report(
        ai_root(),
        generated_at="2026-06-17",
    )
    payload = report.to_dict()

    assert payload["rolloutStatus"] == "contract_stub_observable"
    assert payload["providerCount"] == 2
    assert payload["contractStubCount"] == 2
    assert payload["liveProviderCount"] == 0
    assert payload["blockedProviderCount"] == 0
    assert payload["secretProbeRequiredCount"] == 0
    assert payload["costMonitoringProviderCount"] == 2
    assert payload["latencyMonitoringProviderCount"] == 2
    assert payload["totalEstimatedCostMicros"] == 0


def test_llm_provider_runtime_probe_blocks_live_provider_without_secret_probe() -> None:
    root = ai_root()
    provider_id = "contract-stub-llm-v1"
    access_policy = load_llm_adapter_access_policy(root)
    ops_policy = load_llm_provider_ops_policy(root, access_policy)
    readiness_policy = load_yaml(
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-credential-readiness.yaml"
    )
    probe_policy = load_yaml(
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-runtime-probe-policy.yaml"
    )
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
                credential_ref="vault://llm/providers/primary",
                cost=replace(
                    ops_config.cost,
                    input_micros_per_1k_tokens=500,
                    output_micros_per_1k_tokens=1500,
                ),
            ),
        },
    )
    readiness_policy = {
        **readiness_policy,
        "providers": [
            {
                **row,
                "credential_mode": "live_secret_ref",
                "credential_ref": "vault://llm/providers/primary",
                "rotation_required": True,
                "rotation_days": 30,
                "deployment_checks": readiness_policy["required_live_deployment_checks"],
            }
            if row["provider_id"] == provider_id
            else row
            for row in readiness_policy["providers"]
        ],
    }
    readiness_report = build_llm_provider_readiness_report_from_policy(
        readiness_policy,
        access_policy,
        ops_policy,
        generated_at="2026-06-17",
    )
    probe_policy = {
        **probe_policy,
        "providers": [
            {
                **row,
                "probe_mode": "live_runtime_probe",
                "runtime_secret_probe": "missing",
                "runtime_secret_ref_resolved": False,
                "network_egress_allowlisted": True,
                "sample_request_count": 1,
                "p95_latency_ms": 250,
                "estimated_cost_micros": 42,
                "probe_checks": probe_policy["required_live_probe_checks"],
            }
            if row["provider_id"] == provider_id
            else row
            for row in probe_policy["providers"]
        ],
    }

    report = build_llm_provider_runtime_probe_report_from_policy(
        probe_policy,
        access_policy,
        ops_policy,
        readiness_report,
        generated_at="2026-06-17",
    )

    assert report.rollout_status == "blocked"
    assert report.blocked_provider_count == 1
    item = next(item for item in report.items if item.provider_id == provider_id)
    assert item.readiness_status == "live_ready"
    assert item.rollout_status == "blocked"
    assert "runtime secret probe must resolve live secret ref" in item.validation_errors


def test_llm_provider_runtime_probe_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "operations"
        / "reports"
        / "llm-provider-runtime-probes-v1.yaml"
    )
    generated = build_llm_provider_runtime_probe_snapshot(root, generated_at="2026-06-17")

    assert checked_in == generated
