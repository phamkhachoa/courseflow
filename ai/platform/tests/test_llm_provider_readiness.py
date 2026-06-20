from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from courseflow_ai_platform.llm_provider_adapter import (
    load_llm_adapter_access_policy,
    load_llm_provider_ops_policy,
)
from courseflow_ai_platform.llm_provider_readiness import (
    build_llm_provider_readiness_report,
    build_llm_provider_readiness_report_from_policy,
    build_llm_provider_readiness_snapshot,
)
from courseflow_ai_platform.registry import load_yaml


def ai_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_llm_provider_readiness_reports_contract_stub_state() -> None:
    report = build_llm_provider_readiness_report(ai_root(), generated_at="2026-06-17")
    payload = report.to_dict()

    assert payload["readinessStatus"] == "contract_stub_ready"
    assert payload["activeProviderCount"] == 2
    assert payload["contractStubCount"] == 2
    assert payload["liveProviderReadyCount"] == 0
    assert payload["blockedProviderCount"] == 0
    assert payload["plaintextSecretCount"] == 0
    assert all(item["credentialRefScheme"] == "local://" for item in payload["items"])


def test_llm_provider_readiness_blocks_plaintext_live_credential() -> None:
    root = ai_root()
    readiness_policy = load_yaml(
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-credential-readiness.yaml"
    )
    access_policy = load_llm_adapter_access_policy(root)
    ops_policy = load_llm_provider_ops_policy(root, access_policy)
    provider_id = "contract-stub-llm-v1"
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
    ops_policy = replace(
        ops_policy,
        providers={
            **ops_policy.providers,
            provider_id: replace(
                ops_policy.providers[provider_id],
                credential_ref="sk-live-secret",
            ),
        },
    )
    readiness_policy = {
        **readiness_policy,
        "providers": [
            {
                **row,
                "credential_mode": "live_secret_ref",
                "credential_ref": "sk-live-secret",
                "rotation_required": True,
                "rotation_days": 90,
                "deployment_checks": readiness_policy["required_live_deployment_checks"],
            }
            if row["provider_id"] == provider_id
            else row
            for row in readiness_policy["providers"]
        ],
    }

    report = build_llm_provider_readiness_report_from_policy(
        readiness_policy,
        access_policy,
        ops_policy,
        generated_at="2026-06-17",
    )

    assert report.readiness_status == "blocked"
    assert report.blocked_provider_count == 1
    assert report.plaintext_secret_count == 1
    item = next(item for item in report.items if item.provider_id == provider_id)
    assert item.credential_ref_scheme == "plaintext"
    assert "credential ref must be a secret URI" in item.validation_errors[0]


def test_llm_provider_readiness_snapshot_matches_checked_in_report() -> None:
    root = ai_root()
    checked_in = load_yaml(
        root
        / "platform"
        / "governance"
        / "reports"
        / "llm-provider-readiness-v1.yaml"
    )
    generated = build_llm_provider_readiness_snapshot(root, generated_at="2026-06-17")

    assert checked_in == generated
