from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from courseflow_ai_platform.llm_provider_readiness import (
    normalize_string_tuple,
    require_bool,
    require_mapping_list,
    require_non_negative_int,
)
from courseflow_ai_platform.llm_provider_runtime_probes import (
    LlmProviderRuntimeProbeItem,
    LlmProviderRuntimeProbeReport,
    build_llm_provider_runtime_probe_report,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

ALERT_REPORT_ID = "llm-provider-alert-routing-v1"
RAW_IDENTIFIER_MARKERS = ("sk-", "token=", "api_key", "service:", "tenant-")


@dataclass(frozen=True, slots=True)
class LlmProviderAlertSink:
    sink_id: str
    sink_type: str
    destination_ref: str
    owner_role: str
    escalation_policy_ref: str
    tenant_safe: bool
    validation_errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "destinationRef": self.destination_ref,
            "escalationPolicyRef": self.escalation_policy_ref,
            "ownerRole": self.owner_role,
            "sinkId": self.sink_id,
            "sinkType": self.sink_type,
            "tenantSafe": self.tenant_safe,
            "validationErrors": self.validation_errors,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "sink_id": self.sink_id,
            "sink_type": self.sink_type,
            "destination_ref": self.destination_ref,
            "owner_role": self.owner_role,
            "escalation_policy_ref": self.escalation_policy_ref,
            "tenant_safe": self.tenant_safe,
            "validation_errors": list(self.validation_errors),
        }


@dataclass(frozen=True, slots=True)
class LlmProviderAlertRoute:
    provider_id: str
    runtime_rollout_status: str
    sink_id: str
    alert_route_ref: str
    budget_threshold_micros_per_day: int
    p95_latency_threshold_ms: int
    rotation_automation_ref: str
    rotation_evidence_ref: str
    alert_dimensions: tuple[str, ...]
    alert_route_status: str
    rotation_status: str
    validation_errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertDimensions": self.alert_dimensions,
            "alertRouteRef": self.alert_route_ref,
            "alertRouteStatus": self.alert_route_status,
            "budgetThresholdMicrosPerDay": self.budget_threshold_micros_per_day,
            "p95LatencyThresholdMs": self.p95_latency_threshold_ms,
            "providerId": self.provider_id,
            "rotationAutomationRef": self.rotation_automation_ref,
            "rotationEvidenceRef": self.rotation_evidence_ref,
            "rotationStatus": self.rotation_status,
            "runtimeRolloutStatus": self.runtime_rollout_status,
            "sinkId": self.sink_id,
            "validationErrors": self.validation_errors,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "runtime_rollout_status": self.runtime_rollout_status,
            "sink_id": self.sink_id,
            "alert_route_ref": self.alert_route_ref,
            "budget_threshold_micros_per_day": self.budget_threshold_micros_per_day,
            "p95_latency_threshold_ms": self.p95_latency_threshold_ms,
            "rotation_automation_ref": self.rotation_automation_ref,
            "rotation_evidence_ref": self.rotation_evidence_ref,
            "alert_dimensions": list(self.alert_dimensions),
            "alert_route_status": self.alert_route_status,
            "rotation_status": self.rotation_status,
            "validation_errors": list(self.validation_errors),
        }


@dataclass(frozen=True, slots=True)
class LlmProviderAlertRoutingReport:
    generated_at: str
    policy_id: str
    runtime_probe_report_id: str
    runtime_rollout_status: str
    alert_routing_status: str
    provider_count: int
    routed_provider_count: int
    sink_count: int
    valid_sink_count: int
    live_provider_count: int
    contract_stub_provider_count: int
    rotation_automation_provider_count: int
    blocked_route_count: int
    tenant_safe: bool
    raw_identifier_count: int
    omitted_sensitive_fields: tuple[str, ...]
    next_actions: tuple[str, ...]
    sinks: tuple[LlmProviderAlertSink, ...]
    routes: tuple[LlmProviderAlertRoute, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "alertRoutingStatus": self.alert_routing_status,
            "blockedRouteCount": self.blocked_route_count,
            "contractStubProviderCount": self.contract_stub_provider_count,
            "generatedAt": self.generated_at,
            "items": [route.to_dict() for route in self.routes],
            "liveProviderCount": self.live_provider_count,
            "nextActions": self.next_actions,
            "omittedSensitiveFields": list(self.omitted_sensitive_fields),
            "policyId": self.policy_id,
            "providerCount": self.provider_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "rotationAutomationProviderCount": (
                self.rotation_automation_provider_count
            ),
            "routedProviderCount": self.routed_provider_count,
            "runtimeProbeReportId": self.runtime_probe_report_id,
            "runtimeRolloutStatus": self.runtime_rollout_status,
            "sinkCount": self.sink_count,
            "sinks": [sink.to_dict() for sink in self.sinks],
            "tenantSafe": self.tenant_safe,
            "validSinkCount": self.valid_sink_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": ALERT_REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "policy_id": self.policy_id,
            "runtime_probe_report_id": self.runtime_probe_report_id,
            "summary": {
                "alert_routing_status": self.alert_routing_status,
                "runtime_rollout_status": self.runtime_rollout_status,
                "provider_count": self.provider_count,
                "routed_provider_count": self.routed_provider_count,
                "sink_count": self.sink_count,
                "valid_sink_count": self.valid_sink_count,
                "live_provider_count": self.live_provider_count,
                "contract_stub_provider_count": self.contract_stub_provider_count,
                "rotation_automation_provider_count": (
                    self.rotation_automation_provider_count
                ),
                "blocked_route_count": self.blocked_route_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
                "omitted_sensitive_fields": list(self.omitted_sensitive_fields),
            },
            "next_actions": list(self.next_actions),
            "sinks": [sink.to_snapshot_dict() for sink in self.sinks],
            "routes": [route.to_snapshot_dict() for route in self.routes],
        }


def build_llm_provider_alert_routing_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> LlmProviderAlertRoutingReport:
    root = Path(ai_root)
    runtime_probe_report = build_llm_provider_runtime_probe_report(
        root,
        generated_at=generated_at,
    )
    policy = load_yaml(default_policy_path(root))
    report_date = generated_at or date.today().isoformat()
    return build_llm_provider_alert_routing_report_from_policy(
        policy,
        runtime_probe_report,
        generated_at=report_date,
    )


def build_llm_provider_alert_routing_report_from_policy(
    policy: dict[str, Any],
    runtime_probe_report: LlmProviderRuntimeProbeReport,
    *,
    generated_at: str,
) -> LlmProviderAlertRoutingReport:
    allowed_sink_ref_schemes = normalize_string_tuple(
        policy.get("allowed_sink_ref_schemes", [])
    )
    allowed_rotation_ref_schemes = normalize_string_tuple(
        policy.get("allowed_rotation_ref_schemes", [])
    )
    if not allowed_sink_ref_schemes:
        raise RegistryValidationError(
            "llm provider alert policy must define allowed sink ref schemes"
        )
    if not allowed_rotation_ref_schemes:
        raise RegistryValidationError(
            "llm provider alert policy must define allowed rotation ref schemes"
        )
    min_budget_threshold = require_positive_int(
        policy,
        "min_budget_threshold_micros_per_day",
        "llm provider alert policy",
    )
    max_p95_latency_threshold_ms = require_positive_int(
        policy,
        "max_p95_latency_threshold_ms",
        "llm provider alert policy",
    )
    required_alert_dimensions = set(
        normalize_string_tuple(policy.get("required_alert_dimensions", []))
    )
    next_actions = normalize_string_tuple(policy.get("next_actions", []))
    sink_rows = require_mapping_list(policy, "sinks", "llm provider alert policy")
    route_rows = require_mapping_list(policy, "routes", "llm provider alert policy")
    sinks = tuple(
        sorted(
            (
                build_alert_sink(row, allowed_sink_ref_schemes=allowed_sink_ref_schemes)
                for row in sink_rows
            ),
            key=lambda sink: sink.sink_id,
        )
    )
    sinks_by_id = {sink.sink_id: sink for sink in sinks}
    route_rows_by_provider = {
        require_str(row, "provider_id", "llm provider alert route"): row
        for row in route_rows
    }
    routes = tuple(
        sorted(
            (
                build_alert_route(
                    runtime_item,
                    route_rows_by_provider.get(runtime_item.provider_id),
                    sinks_by_id=sinks_by_id,
                    allowed_sink_ref_schemes=allowed_sink_ref_schemes,
                    allowed_rotation_ref_schemes=allowed_rotation_ref_schemes,
                    min_budget_threshold=min_budget_threshold,
                    max_p95_latency_threshold_ms=max_p95_latency_threshold_ms,
                    required_alert_dimensions=required_alert_dimensions,
                )
                for runtime_item in runtime_probe_report.items
            ),
            key=lambda route: route.provider_id,
        )
    )
    raw_identifier_count = count_raw_identifier_markers(sinks, routes)
    tenant_safe = raw_identifier_count == 0
    blocked_route_count = sum(
        1 for route in routes if route.alert_route_status == "blocked"
    )
    routed_provider_count = sum(
        1
        for route in routes
        if route.alert_route_status
        in {"contract_stub_alert_configured", "live_alert_ready"}
    )
    alert_routing_status = derive_alert_routing_status(
        provider_count=len(routes),
        routed_provider_count=routed_provider_count,
        blocked_route_count=blocked_route_count,
        live_provider_count=runtime_probe_report.live_provider_count,
        contract_stub_provider_count=runtime_probe_report.contract_stub_count,
        tenant_safe=tenant_safe,
    )
    return LlmProviderAlertRoutingReport(
        generated_at=generated_at,
        policy_id=require_str(policy, "policy_id", "llm provider alert policy"),
        runtime_probe_report_id="llm-provider-runtime-probes-v1",
        runtime_rollout_status=runtime_probe_report.rollout_status,
        alert_routing_status=alert_routing_status,
        provider_count=len(routes),
        routed_provider_count=routed_provider_count,
        sink_count=len(sinks),
        valid_sink_count=sum(1 for sink in sinks if not sink.validation_errors),
        live_provider_count=runtime_probe_report.live_provider_count,
        contract_stub_provider_count=runtime_probe_report.contract_stub_count,
        rotation_automation_provider_count=sum(
            1 for route in routes if route.rotation_status == "automation_configured"
        ),
        blocked_route_count=blocked_route_count,
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        omitted_sensitive_fields=(
            "credential_ref",
            "secret_values",
            "prompt_payload",
            "provider_api_key",
        ),
        next_actions=next_actions,
        sinks=sinks,
        routes=routes,
    )


def build_alert_sink(
    row: dict[str, Any],
    *,
    allowed_sink_ref_schemes: tuple[str, ...],
) -> LlmProviderAlertSink:
    sink_id = require_str(row, "sink_id", "llm provider alert sink")
    destination_ref = require_str(row, "destination_ref", f"alert sink {sink_id}")
    escalation_policy_ref = require_str(
        row,
        "escalation_policy_ref",
        f"alert sink {sink_id}",
    )
    tenant_safe = require_bool(row, "tenant_safe", f"alert sink {sink_id}")
    errors: list[str] = []
    if not starts_with_any(destination_ref, allowed_sink_ref_schemes):
        errors.append("destination ref must use an allowed alert sink scheme")
    if not starts_with_any(escalation_policy_ref, allowed_sink_ref_schemes):
        errors.append("escalation policy ref must use an allowed alert sink scheme")
    if not tenant_safe:
        errors.append("alert sink must be marked tenant safe")
    if contains_raw_identifier_marker(destination_ref):
        errors.append("destination ref must not expose raw service or tenant identifiers")
    return LlmProviderAlertSink(
        sink_id=sink_id,
        sink_type=require_str(row, "sink_type", f"alert sink {sink_id}"),
        destination_ref=destination_ref,
        owner_role=require_str(row, "owner_role", f"alert sink {sink_id}"),
        escalation_policy_ref=escalation_policy_ref,
        tenant_safe=tenant_safe,
        validation_errors=tuple(errors),
    )


def build_alert_route(
    runtime_item: LlmProviderRuntimeProbeItem,
    row: dict[str, Any] | None,
    *,
    sinks_by_id: dict[str, LlmProviderAlertSink],
    allowed_sink_ref_schemes: tuple[str, ...],
    allowed_rotation_ref_schemes: tuple[str, ...],
    min_budget_threshold: int,
    max_p95_latency_threshold_ms: int,
    required_alert_dimensions: set[str],
) -> LlmProviderAlertRoute:
    if row is None:
        return missing_alert_route(runtime_item)
    sink_id = require_str(row, "sink_id", f"alert route {runtime_item.provider_id}")
    alert_route_ref = require_str(
        row,
        "alert_route_ref",
        f"alert route {runtime_item.provider_id}",
    )
    budget_threshold = require_positive_int(
        row,
        "budget_threshold_micros_per_day",
        f"alert route {runtime_item.provider_id}",
    )
    p95_threshold = require_positive_int(
        row,
        "p95_latency_threshold_ms",
        f"alert route {runtime_item.provider_id}",
    )
    rotation_automation_ref = require_str(
        row,
        "rotation_automation_ref",
        f"alert route {runtime_item.provider_id}",
    )
    rotation_evidence_ref = require_str(
        row,
        "rotation_evidence_ref",
        f"alert route {runtime_item.provider_id}",
    )
    alert_dimensions = normalize_string_tuple(row.get("alert_dimensions", []))
    errors: list[str] = []
    sink = sinks_by_id.get(sink_id)
    if sink is None:
        errors.append("alert route references unknown sink")
    elif sink.validation_errors:
        errors.append("alert route sink is not valid")
    if not starts_with_any(alert_route_ref, allowed_sink_ref_schemes):
        errors.append("alert route ref must use an allowed alert sink scheme")
    if budget_threshold < min_budget_threshold:
        errors.append("budget threshold must meet policy minimum")
    if p95_threshold > max_p95_latency_threshold_ms:
        errors.append("latency threshold exceeds policy maximum")
    if p95_threshold < runtime_item.p95_latency_ms:
        errors.append("latency threshold is below observed provider p95")
    if not runtime_item.cost_monitoring_enabled:
        errors.append("runtime probe must expose provider cost monitoring")
    if not runtime_item.latency_monitoring_enabled:
        errors.append("runtime probe must expose provider latency monitoring")
    if runtime_item.rollout_status == "blocked":
        errors.append("runtime probe blocks provider rollout")
    missing_dimensions = sorted(required_alert_dimensions - set(alert_dimensions))
    if missing_dimensions:
        errors.append("missing alert dimensions: " + ", ".join(missing_dimensions))
    if contains_raw_identifier_marker(alert_route_ref):
        errors.append("alert route ref must not expose raw service or tenant identifiers")
    rotation_status = derive_rotation_status(
        runtime_item,
        rotation_automation_ref=rotation_automation_ref,
        rotation_evidence_ref=rotation_evidence_ref,
        allowed_rotation_ref_schemes=allowed_rotation_ref_schemes,
        errors=errors,
    )
    alert_route_status = (
        "blocked"
        if errors
        else "live_alert_ready"
        if runtime_item.network_enabled
        else "contract_stub_alert_configured"
    )
    return LlmProviderAlertRoute(
        provider_id=runtime_item.provider_id,
        runtime_rollout_status=runtime_item.rollout_status,
        sink_id=sink_id,
        alert_route_ref=alert_route_ref,
        budget_threshold_micros_per_day=budget_threshold,
        p95_latency_threshold_ms=p95_threshold,
        rotation_automation_ref=rotation_automation_ref,
        rotation_evidence_ref=rotation_evidence_ref,
        alert_dimensions=alert_dimensions,
        alert_route_status=alert_route_status,
        rotation_status=rotation_status,
        validation_errors=tuple(errors),
    )


def missing_alert_route(
    runtime_item: LlmProviderRuntimeProbeItem,
) -> LlmProviderAlertRoute:
    return LlmProviderAlertRoute(
        provider_id=runtime_item.provider_id,
        runtime_rollout_status=runtime_item.rollout_status,
        sink_id="missing",
        alert_route_ref="missing",
        budget_threshold_micros_per_day=0,
        p95_latency_threshold_ms=0,
        rotation_automation_ref="missing",
        rotation_evidence_ref="missing",
        alert_dimensions=(),
        alert_route_status="blocked",
        rotation_status="missing",
        validation_errors=("missing alert route policy entry",),
    )


def derive_rotation_status(
    runtime_item: LlmProviderRuntimeProbeItem,
    *,
    rotation_automation_ref: str,
    rotation_evidence_ref: str,
    allowed_rotation_ref_schemes: tuple[str, ...],
    errors: list[str],
) -> str:
    if runtime_item.network_enabled:
        automation_configured = starts_with_any(
            rotation_automation_ref,
            allowed_rotation_ref_schemes,
        )
        evidence_configured = starts_with_any(
            rotation_evidence_ref,
            allowed_rotation_ref_schemes,
        )
        if not automation_configured:
            errors.append("live provider rotation automation ref is required")
        if not evidence_configured:
            errors.append("live provider rotation evidence ref is required")
        return (
            "automation_configured"
            if automation_configured and evidence_configured
            else "missing"
        )
    if rotation_automation_ref != "not_required" or rotation_evidence_ref != "not_required":
        errors.append("contract stub provider must not declare live rotation refs")
    return "not_required"


def derive_alert_routing_status(
    *,
    provider_count: int,
    routed_provider_count: int,
    blocked_route_count: int,
    live_provider_count: int,
    contract_stub_provider_count: int,
    tenant_safe: bool,
) -> str:
    if blocked_route_count or not tenant_safe:
        return "blocked"
    if provider_count == 0:
        return "not_configured"
    if routed_provider_count < provider_count:
        return "attention_required_alert_route_gap"
    if live_provider_count:
        return "live_alert_ready"
    if contract_stub_provider_count:
        return "contract_stub_alerts_configured"
    return "not_configured"


def count_raw_identifier_markers(
    sinks: tuple[LlmProviderAlertSink, ...],
    routes: tuple[LlmProviderAlertRoute, ...],
) -> int:
    serialized = json.dumps(
        {
            "sinks": [sink.to_snapshot_dict() for sink in sinks],
            "routes": [route.to_snapshot_dict() for route in routes],
        },
        sort_keys=True,
    ).lower()
    return sum(serialized.count(marker) for marker in RAW_IDENTIFIER_MARKERS)


def contains_raw_identifier_marker(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in RAW_IDENTIFIER_MARKERS)


def starts_with_any(value: str, prefixes: tuple[str, ...]) -> bool:
    return any(value.startswith(prefix) for prefix in prefixes)


def require_positive_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = require_non_negative_int(row, key, owner)
    if value <= 0:
        raise RegistryValidationError(f"{owner} must define positive integer field {key}")
    return value


def build_llm_provider_alert_routing_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_llm_provider_alert_routing_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_llm_provider_alert_routing_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    payload = build_llm_provider_alert_routing_snapshot(root, generated_at=generated_at)
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
        / "llm-provider-alert-routing-policy.yaml"
    )


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "operations"
        / "reports"
        / "llm-provider-alert-routing-v1.yaml"
    )
