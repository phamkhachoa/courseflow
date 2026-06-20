from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.llm_provider_adapter import (
    LlmAdapterAccessPolicy,
    LlmProviderOpsPolicy,
    load_llm_adapter_access_policy,
    load_llm_provider_ops_policy,
)
from courseflow_ai_platform.llm_provider_readiness import (
    LlmProviderReadinessReport,
    build_llm_provider_readiness_report,
    credential_scheme,
    normalize_string_tuple,
    require_bool,
    require_mapping_list,
    require_non_negative_int,
)
from courseflow_ai_platform.registry import load_yaml, require_str


@dataclass(frozen=True, slots=True)
class LlmProviderRuntimeProbeItem:
    provider_id: str
    active_provider: bool
    network_enabled: bool
    readiness_status: str
    credential_ref_scheme: str
    probe_mode: str
    runtime_secret_probe: str
    runtime_secret_ref_resolved: bool
    network_egress_allowlisted: bool
    prompt_gateway_mandatory: bool
    cost_monitoring_enabled: bool
    latency_monitoring_enabled: bool
    sample_request_count: int
    p95_latency_ms: int
    estimated_cost_micros: int
    rollout_status: str
    validation_errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activeProvider": self.active_provider,
            "costMonitoringEnabled": self.cost_monitoring_enabled,
            "credentialRefScheme": self.credential_ref_scheme,
            "estimatedCostMicros": self.estimated_cost_micros,
            "latencyMonitoringEnabled": self.latency_monitoring_enabled,
            "networkEgressAllowlisted": self.network_egress_allowlisted,
            "networkEnabled": self.network_enabled,
            "p95LatencyMs": self.p95_latency_ms,
            "probeMode": self.probe_mode,
            "promptGatewayMandatory": self.prompt_gateway_mandatory,
            "providerId": self.provider_id,
            "readinessStatus": self.readiness_status,
            "rolloutStatus": self.rollout_status,
            "runtimeSecretProbe": self.runtime_secret_probe,
            "runtimeSecretRefResolved": self.runtime_secret_ref_resolved,
            "sampleRequestCount": self.sample_request_count,
            "validationErrors": self.validation_errors,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "active_provider": self.active_provider,
            "network_enabled": self.network_enabled,
            "readiness_status": self.readiness_status,
            "credential_ref_scheme": self.credential_ref_scheme,
            "probe_mode": self.probe_mode,
            "runtime_secret_probe": self.runtime_secret_probe,
            "runtime_secret_ref_resolved": self.runtime_secret_ref_resolved,
            "network_egress_allowlisted": self.network_egress_allowlisted,
            "prompt_gateway_mandatory": self.prompt_gateway_mandatory,
            "cost_monitoring_enabled": self.cost_monitoring_enabled,
            "latency_monitoring_enabled": self.latency_monitoring_enabled,
            "sample_request_count": self.sample_request_count,
            "p95_latency_ms": self.p95_latency_ms,
            "estimated_cost_micros": self.estimated_cost_micros,
            "rollout_status": self.rollout_status,
            "validation_errors": list(self.validation_errors),
        }


@dataclass(frozen=True, slots=True)
class LlmProviderRuntimeProbeReport:
    generated_at: str
    policy_id: str
    readiness_policy_id: str
    ops_policy_id: str
    rollout_status: str
    provider_count: int
    live_provider_count: int
    contract_stub_count: int
    blocked_provider_count: int
    secret_probe_required_count: int
    secret_probe_passed_count: int
    cost_monitoring_provider_count: int
    latency_monitoring_provider_count: int
    prompt_gateway_probe_passed_count: int
    total_estimated_cost_micros: int
    max_p95_latency_ms: int
    next_actions: tuple[str, ...]
    items: tuple[LlmProviderRuntimeProbeItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "blockedProviderCount": self.blocked_provider_count,
            "contractStubCount": self.contract_stub_count,
            "costMonitoringProviderCount": self.cost_monitoring_provider_count,
            "generatedAt": self.generated_at,
            "items": [item.to_dict() for item in self.items],
            "latencyMonitoringProviderCount": self.latency_monitoring_provider_count,
            "liveProviderCount": self.live_provider_count,
            "maxP95LatencyMs": self.max_p95_latency_ms,
            "nextActions": self.next_actions,
            "opsPolicyId": self.ops_policy_id,
            "policyId": self.policy_id,
            "promptGatewayProbePassedCount": self.prompt_gateway_probe_passed_count,
            "providerCount": self.provider_count,
            "readinessPolicyId": self.readiness_policy_id,
            "rolloutStatus": self.rollout_status,
            "secretProbePassedCount": self.secret_probe_passed_count,
            "secretProbeRequiredCount": self.secret_probe_required_count,
            "totalEstimatedCostMicros": self.total_estimated_cost_micros,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "llm-provider-runtime-probes-v1",
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "policy_id": self.policy_id,
            "readiness_policy_id": self.readiness_policy_id,
            "ops_policy_id": self.ops_policy_id,
            "summary": {
                "rollout_status": self.rollout_status,
                "provider_count": self.provider_count,
                "live_provider_count": self.live_provider_count,
                "contract_stub_count": self.contract_stub_count,
                "blocked_provider_count": self.blocked_provider_count,
                "secret_probe_required_count": self.secret_probe_required_count,
                "secret_probe_passed_count": self.secret_probe_passed_count,
                "cost_monitoring_provider_count": self.cost_monitoring_provider_count,
                "latency_monitoring_provider_count": (
                    self.latency_monitoring_provider_count
                ),
                "prompt_gateway_probe_passed_count": (
                    self.prompt_gateway_probe_passed_count
                ),
                "total_estimated_cost_micros": self.total_estimated_cost_micros,
                "max_p95_latency_ms": self.max_p95_latency_ms,
            },
            "next_actions": list(self.next_actions),
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_llm_provider_runtime_probe_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> LlmProviderRuntimeProbeReport:
    root = Path(ai_root)
    access_policy = load_llm_adapter_access_policy(root)
    ops_policy = load_llm_provider_ops_policy(root, access_policy)
    readiness_report = build_llm_provider_readiness_report(
        root,
        generated_at=generated_at,
    )
    probe_policy = load_yaml(default_policy_path(root))
    report_date = generated_at or date.today().isoformat()
    return build_llm_provider_runtime_probe_report_from_policy(
        probe_policy,
        access_policy,
        ops_policy,
        readiness_report,
        generated_at=report_date,
    )


def build_llm_provider_runtime_probe_report_from_policy(
    probe_policy: dict[str, Any],
    access_policy: LlmAdapterAccessPolicy,
    ops_policy: LlmProviderOpsPolicy,
    readiness_report: LlmProviderReadinessReport,
    *,
    generated_at: str,
) -> LlmProviderRuntimeProbeReport:
    max_allowed_p95_latency_ms = require_non_negative_int(
        probe_policy,
        "max_allowed_p95_latency_ms",
        "llm provider runtime probe policy",
    )
    required_live_probe_checks = set(
        normalize_string_tuple(probe_policy.get("required_live_probe_checks", []))
    )
    next_actions = normalize_string_tuple(probe_policy.get("next_actions", []))
    provider_rows = require_mapping_list(
        probe_policy,
        "providers",
        "llm provider runtime probe policy",
    )
    provider_rows_by_id = {
        require_str(row, "provider_id", "llm provider runtime probe provider"): row
        for row in provider_rows
    }
    readiness_by_provider = {
        item.provider_id: item for item in readiness_report.items
    }
    items = tuple(
        sorted(
            (
                build_probe_item(
                    provider_id,
                    provider_rows_by_id.get(provider_id),
                    access_policy=access_policy,
                    ops_policy=ops_policy,
                    readiness_report=readiness_report,
                    readiness_by_provider=readiness_by_provider,
                    required_live_probe_checks=required_live_probe_checks,
                    max_allowed_p95_latency_ms=max_allowed_p95_latency_ms,
                )
                for provider_id in access_policy.providers
            ),
            key=lambda item: item.provider_id,
        )
    )
    blocked_provider_count = sum(1 for item in items if item.rollout_status == "blocked")
    live_provider_count = sum(1 for item in items if item.network_enabled)
    contract_stub_count = sum(
        1 for item in items if item.rollout_status == "contract_stub_observable"
    )
    secret_probe_required_count = sum(1 for item in items if item.network_enabled)
    secret_probe_passed_count = sum(
        1
        for item in items
        if item.network_enabled
        and item.runtime_secret_probe == "passed"
        and item.runtime_secret_ref_resolved
    )
    rollout_status = derive_rollout_status(
        blocked_provider_count=blocked_provider_count,
        live_provider_count=live_provider_count,
        contract_stub_count=contract_stub_count,
    )
    return LlmProviderRuntimeProbeReport(
        generated_at=generated_at,
        policy_id=require_str(probe_policy, "policy_id", "llm provider probe policy"),
        readiness_policy_id=readiness_report.policy_id,
        ops_policy_id=ops_policy.policy_id,
        rollout_status=rollout_status,
        provider_count=len(items),
        live_provider_count=live_provider_count,
        contract_stub_count=contract_stub_count,
        blocked_provider_count=blocked_provider_count,
        secret_probe_required_count=secret_probe_required_count,
        secret_probe_passed_count=secret_probe_passed_count,
        cost_monitoring_provider_count=sum(
            1 for item in items if item.cost_monitoring_enabled
        ),
        latency_monitoring_provider_count=sum(
            1 for item in items if item.latency_monitoring_enabled
        ),
        prompt_gateway_probe_passed_count=sum(
            1 for item in items if item.prompt_gateway_mandatory
        ),
        total_estimated_cost_micros=sum(item.estimated_cost_micros for item in items),
        max_p95_latency_ms=max((item.p95_latency_ms for item in items), default=0),
        next_actions=next_actions,
        items=items,
    )


def build_probe_item(
    provider_id: str,
    row: dict[str, Any] | None,
    *,
    access_policy: LlmAdapterAccessPolicy,
    ops_policy: LlmProviderOpsPolicy,
    readiness_report: LlmProviderReadinessReport,
    readiness_by_provider: dict[str, Any],
    required_live_probe_checks: set[str],
    max_allowed_p95_latency_ms: int,
) -> LlmProviderRuntimeProbeItem:
    provider = access_policy.providers[provider_id]
    ops_config = ops_policy.resolve_provider(provider_id)
    readiness_item = readiness_by_provider.get(provider_id)
    readiness_status = (
        readiness_item.readiness_status if readiness_item is not None else "missing"
    )
    errors: list[str] = []
    if row is None:
        return missing_probe_item(provider_id, provider.network_enabled)
    probe_mode = require_str(row, "probe_mode", f"llm provider probe {provider_id}")
    runtime_secret_probe = require_str(
        row,
        "runtime_secret_probe",
        f"llm provider probe {provider_id}",
    )
    runtime_secret_ref_resolved = require_bool(
        row,
        "runtime_secret_ref_resolved",
        f"llm provider probe {provider_id}",
    )
    network_egress_allowlisted = require_bool(
        row,
        "network_egress_allowlisted",
        f"llm provider probe {provider_id}",
    )
    prompt_gateway_mandatory = require_bool(
        row,
        "prompt_gateway_mandatory",
        f"llm provider probe {provider_id}",
    )
    cost_monitoring_enabled = require_bool(
        row,
        "cost_monitoring_enabled",
        f"llm provider probe {provider_id}",
    )
    latency_monitoring_enabled = require_bool(
        row,
        "latency_monitoring_enabled",
        f"llm provider probe {provider_id}",
    )
    sample_request_count = require_non_negative_int(
        row,
        "sample_request_count",
        f"llm provider probe {provider_id}",
    )
    p95_latency_ms = require_non_negative_int(
        row,
        "p95_latency_ms",
        f"llm provider probe {provider_id}",
    )
    estimated_cost_micros = require_non_negative_int(
        row,
        "estimated_cost_micros",
        f"llm provider probe {provider_id}",
    )
    probe_checks = set(normalize_string_tuple(row.get("probe_checks", [])))

    if readiness_item is None:
        errors.append("missing credential readiness item")
    elif readiness_status == "blocked":
        errors.append("credential readiness report blocks provider")
    if readiness_report.readiness_status == "blocked":
        errors.append("credential readiness report is blocked")
    prompt_gateway_required = (
        access_policy.prompt_gateway_required
        and ops_policy.prompt_gateway_required_before_provider
    )
    if not prompt_gateway_required:
        errors.append("prompt gateway must be required by access and ops policies")
    if not prompt_gateway_mandatory:
        errors.append("prompt gateway mandatory probe must pass")
    if not cost_monitoring_enabled:
        errors.append("provider cost monitoring must be enabled")
    if not latency_monitoring_enabled:
        errors.append("provider latency monitoring must be enabled")
    if p95_latency_ms > max_allowed_p95_latency_ms:
        errors.append("provider p95 latency exceeds maximum")

    if provider.network_enabled:
        if probe_mode != "live_runtime_probe":
            errors.append("network provider must use live_runtime_probe mode")
        if runtime_secret_probe != "passed" or not runtime_secret_ref_resolved:
            errors.append("runtime secret probe must resolve live secret ref")
        if not network_egress_allowlisted:
            errors.append("network provider egress allowlist probe must pass")
        missing_checks = sorted(required_live_probe_checks - probe_checks)
        if missing_checks:
            errors.append("missing live runtime probe checks: " + ", ".join(missing_checks))
        if sample_request_count <= 0:
            errors.append("live provider must have probe sample traffic")
        if (
            ops_config.cost.input_micros_per_1k_tokens <= 0
            and ops_config.cost.output_micros_per_1k_tokens <= 0
        ):
            errors.append("live provider must configure non-zero cost rates")
    else:
        if probe_mode != "contract_stub":
            errors.append("contract stub provider must use contract_stub probe mode")
        if runtime_secret_probe != "not_required":
            errors.append("contract stub provider must not require runtime secret probe")
        if runtime_secret_ref_resolved:
            errors.append("contract stub provider must not resolve a live secret ref")
        if "contract_stub_no_network" not in probe_checks:
            errors.append("contract stub no-network probe check is required")

    rollout_status = (
        "blocked"
        if errors
        else "live_rollout_ready"
        if provider.network_enabled
        else "contract_stub_observable"
    )
    return LlmProviderRuntimeProbeItem(
        provider_id=provider_id,
        active_provider=True,
        network_enabled=provider.network_enabled,
        readiness_status=readiness_status,
        credential_ref_scheme=credential_scheme(ops_config.credential_ref),
        probe_mode=probe_mode,
        runtime_secret_probe=runtime_secret_probe,
        runtime_secret_ref_resolved=runtime_secret_ref_resolved,
        network_egress_allowlisted=network_egress_allowlisted,
        prompt_gateway_mandatory=prompt_gateway_mandatory,
        cost_monitoring_enabled=cost_monitoring_enabled,
        latency_monitoring_enabled=latency_monitoring_enabled,
        sample_request_count=sample_request_count,
        p95_latency_ms=p95_latency_ms,
        estimated_cost_micros=estimated_cost_micros,
        rollout_status=rollout_status,
        validation_errors=tuple(errors),
    )


def missing_probe_item(provider_id: str, network_enabled: bool) -> LlmProviderRuntimeProbeItem:
    return LlmProviderRuntimeProbeItem(
        provider_id=provider_id,
        active_provider=True,
        network_enabled=network_enabled,
        readiness_status="missing",
        credential_ref_scheme="missing",
        probe_mode="missing",
        runtime_secret_probe="missing",
        runtime_secret_ref_resolved=False,
        network_egress_allowlisted=False,
        prompt_gateway_mandatory=False,
        cost_monitoring_enabled=False,
        latency_monitoring_enabled=False,
        sample_request_count=0,
        p95_latency_ms=0,
        estimated_cost_micros=0,
        rollout_status="blocked",
        validation_errors=("missing runtime probe policy entry",),
    )


def derive_rollout_status(
    *,
    blocked_provider_count: int,
    live_provider_count: int,
    contract_stub_count: int,
) -> str:
    if blocked_provider_count:
        return "blocked"
    if live_provider_count:
        return "live_rollout_ready"
    if contract_stub_count:
        return "contract_stub_observable"
    return "not_configured"


def build_llm_provider_runtime_probe_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_llm_provider_runtime_probe_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_llm_provider_runtime_probe_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    payload = build_llm_provider_runtime_probe_snapshot(root, generated_at=generated_at)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
    return target


def default_policy_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-runtime-probe-policy.yaml"
    )


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "operations"
        / "reports"
        / "llm-provider-runtime-probes-v1.yaml"
    )
