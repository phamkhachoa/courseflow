from __future__ import annotations

import json
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
from courseflow_ai_platform.llm_provider_runtime_probes import (
    LlmProviderRuntimeProbeReport,
    build_llm_provider_runtime_probe_report,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str

SECRET_ROTATION_REPORT_ID = "llm-provider-secret-rotation-v1"
RAW_IDENTIFIER_MARKERS = ("sk-", "token=", "api_key", "provider_api_key", "tenant-")


@dataclass(frozen=True, slots=True)
class LlmProviderSecretRotationItem:
    provider_id: str
    active_provider: bool
    network_enabled: bool
    readiness_status: str
    runtime_rollout_status: str
    binding_mode: str
    credential_ref_scheme: str
    secret_ref_scheme: str
    secret_ref_resolved: bool
    rotation_interval_days: int
    rotation_automation_ref: str
    rotation_evidence_ref: str
    rotation_drill_status: str
    control_checks: tuple[str, ...]
    rotation_status: str
    validation_errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activeProvider": self.active_provider,
            "bindingMode": self.binding_mode,
            "controlChecks": self.control_checks,
            "credentialRefScheme": self.credential_ref_scheme,
            "networkEnabled": self.network_enabled,
            "providerId": self.provider_id,
            "readinessStatus": self.readiness_status,
            "rotationAutomationRef": self.rotation_automation_ref,
            "rotationDrillStatus": self.rotation_drill_status,
            "rotationEvidenceRef": self.rotation_evidence_ref,
            "rotationIntervalDays": self.rotation_interval_days,
            "rotationStatus": self.rotation_status,
            "runtimeRolloutStatus": self.runtime_rollout_status,
            "secretRefResolved": self.secret_ref_resolved,
            "secretRefScheme": self.secret_ref_scheme,
            "validationErrors": self.validation_errors,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "active_provider": self.active_provider,
            "network_enabled": self.network_enabled,
            "readiness_status": self.readiness_status,
            "runtime_rollout_status": self.runtime_rollout_status,
            "binding_mode": self.binding_mode,
            "credential_ref_scheme": self.credential_ref_scheme,
            "secret_ref_scheme": self.secret_ref_scheme,
            "secret_ref_resolved": self.secret_ref_resolved,
            "rotation_interval_days": self.rotation_interval_days,
            "rotation_automation_ref": self.rotation_automation_ref,
            "rotation_evidence_ref": self.rotation_evidence_ref,
            "rotation_drill_status": self.rotation_drill_status,
            "control_checks": list(self.control_checks),
            "rotation_status": self.rotation_status,
            "validation_errors": list(self.validation_errors),
        }


@dataclass(frozen=True, slots=True)
class LlmProviderSecretRotationReport:
    generated_at: str
    policy_id: str
    readiness_policy_id: str
    runtime_probe_report_id: str
    secret_rotation_status: str
    provider_count: int
    live_provider_count: int
    contract_stub_provider_count: int
    blocked_provider_count: int
    secret_manager_binding_count: int
    secret_ref_resolved_count: int
    rotation_automation_provider_count: int
    rotation_evidence_provider_count: int
    rotation_drill_passed_count: int
    plaintext_secret_count: int
    tenant_safe: bool
    raw_identifier_count: int
    omitted_sensitive_fields: tuple[str, ...]
    next_actions: tuple[str, ...]
    items: tuple[LlmProviderSecretRotationItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "blockedProviderCount": self.blocked_provider_count,
            "contractStubProviderCount": self.contract_stub_provider_count,
            "generatedAt": self.generated_at,
            "items": [item.to_dict() for item in self.items],
            "liveProviderCount": self.live_provider_count,
            "nextActions": self.next_actions,
            "omittedSensitiveFields": list(self.omitted_sensitive_fields),
            "plaintextSecretCount": self.plaintext_secret_count,
            "policyId": self.policy_id,
            "providerCount": self.provider_count,
            "rawIdentifierCount": self.raw_identifier_count,
            "readinessPolicyId": self.readiness_policy_id,
            "rotationAutomationProviderCount": (
                self.rotation_automation_provider_count
            ),
            "rotationDrillPassedCount": self.rotation_drill_passed_count,
            "rotationEvidenceProviderCount": self.rotation_evidence_provider_count,
            "runtimeProbeReportId": self.runtime_probe_report_id,
            "secretManagerBindingCount": self.secret_manager_binding_count,
            "secretRefResolvedCount": self.secret_ref_resolved_count,
            "secretRotationStatus": self.secret_rotation_status,
            "tenantSafe": self.tenant_safe,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": SECRET_ROTATION_REPORT_ID,
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "policy_id": self.policy_id,
            "readiness_policy_id": self.readiness_policy_id,
            "runtime_probe_report_id": self.runtime_probe_report_id,
            "summary": {
                "secret_rotation_status": self.secret_rotation_status,
                "provider_count": self.provider_count,
                "live_provider_count": self.live_provider_count,
                "contract_stub_provider_count": self.contract_stub_provider_count,
                "blocked_provider_count": self.blocked_provider_count,
                "secret_manager_binding_count": self.secret_manager_binding_count,
                "secret_ref_resolved_count": self.secret_ref_resolved_count,
                "rotation_automation_provider_count": (
                    self.rotation_automation_provider_count
                ),
                "rotation_evidence_provider_count": (
                    self.rotation_evidence_provider_count
                ),
                "rotation_drill_passed_count": self.rotation_drill_passed_count,
                "plaintext_secret_count": self.plaintext_secret_count,
                "tenant_safe": self.tenant_safe,
                "raw_identifier_count": self.raw_identifier_count,
                "omitted_sensitive_fields": list(self.omitted_sensitive_fields),
            },
            "next_actions": list(self.next_actions),
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_llm_provider_secret_rotation_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> LlmProviderSecretRotationReport:
    root = Path(ai_root)
    access_policy = load_llm_adapter_access_policy(root)
    ops_policy = load_llm_provider_ops_policy(root, access_policy)
    readiness_report = build_llm_provider_readiness_report(
        root,
        generated_at=generated_at,
    )
    runtime_probe_report = build_llm_provider_runtime_probe_report(
        root,
        generated_at=generated_at,
    )
    policy = load_yaml(default_policy_path(root))
    report_date = generated_at or date.today().isoformat()
    return build_llm_provider_secret_rotation_report_from_policy(
        policy,
        access_policy,
        ops_policy,
        readiness_report,
        runtime_probe_report,
        generated_at=report_date,
    )


def build_llm_provider_secret_rotation_report_from_policy(
    policy: dict[str, Any],
    access_policy: LlmAdapterAccessPolicy,
    ops_policy: LlmProviderOpsPolicy,
    readiness_report: LlmProviderReadinessReport,
    runtime_probe_report: LlmProviderRuntimeProbeReport,
    *,
    generated_at: str,
) -> LlmProviderSecretRotationReport:
    allowed_secret_ref_schemes = normalize_string_tuple(
        policy.get("allowed_secret_ref_schemes", [])
    )
    allowed_rotation_ref_schemes = normalize_string_tuple(
        policy.get("allowed_rotation_ref_schemes", [])
    )
    allowed_evidence_ref_schemes = normalize_string_tuple(
        policy.get("allowed_evidence_ref_schemes", [])
    )
    if not allowed_secret_ref_schemes:
        raise RegistryValidationError(
            "llm provider secret rotation policy must define allowed secret schemes"
        )
    if not allowed_rotation_ref_schemes:
        raise RegistryValidationError(
            "llm provider secret rotation policy must define allowed rotation schemes"
        )
    if not allowed_evidence_ref_schemes:
        raise RegistryValidationError(
            "llm provider secret rotation policy must define allowed evidence schemes"
        )
    max_rotation_days = require_positive_int(
        policy,
        "max_rotation_days",
        "llm provider secret rotation policy",
    )
    required_live_controls = set(
        normalize_string_tuple(policy.get("required_live_controls", []))
    )
    next_actions = normalize_string_tuple(policy.get("next_actions", []))
    provider_rows = require_mapping_list(
        policy,
        "providers",
        "llm provider secret rotation policy",
    )
    provider_rows_by_id = {
        require_str(row, "provider_id", "llm provider secret rotation provider"): row
        for row in provider_rows
    }
    readiness_by_provider = {item.provider_id: item for item in readiness_report.items}
    runtime_by_provider = {item.provider_id: item for item in runtime_probe_report.items}
    items = tuple(
        sorted(
            (
                build_secret_rotation_item(
                    provider_id,
                    provider_rows_by_id.get(provider_id),
                    access_policy=access_policy,
                    ops_policy=ops_policy,
                    readiness_by_provider=readiness_by_provider,
                    runtime_by_provider=runtime_by_provider,
                    allowed_secret_ref_schemes=allowed_secret_ref_schemes,
                    allowed_rotation_ref_schemes=allowed_rotation_ref_schemes,
                    allowed_evidence_ref_schemes=allowed_evidence_ref_schemes,
                    max_rotation_days=max_rotation_days,
                    required_live_controls=required_live_controls,
                )
                for provider_id in access_policy.providers
            ),
            key=lambda item: item.provider_id,
        )
    )
    raw_identifier_count = count_raw_identifier_markers(items)
    tenant_safe = raw_identifier_count == 0
    blocked_provider_count = sum(1 for item in items if item.rotation_status == "blocked")
    live_provider_count = sum(1 for item in items if item.network_enabled)
    contract_stub_provider_count = sum(
        1 for item in items if item.rotation_status == "contract_stub_not_required"
    )
    secret_rotation_status = derive_secret_rotation_status(
        provider_count=len(items),
        blocked_provider_count=blocked_provider_count,
        live_provider_count=live_provider_count,
        contract_stub_provider_count=contract_stub_provider_count,
        tenant_safe=tenant_safe,
    )
    return LlmProviderSecretRotationReport(
        generated_at=generated_at,
        policy_id=require_str(policy, "policy_id", "llm provider secret rotation policy"),
        readiness_policy_id=readiness_report.policy_id,
        runtime_probe_report_id="llm-provider-runtime-probes-v1",
        secret_rotation_status=secret_rotation_status,
        provider_count=len(items),
        live_provider_count=live_provider_count,
        contract_stub_provider_count=contract_stub_provider_count,
        blocked_provider_count=blocked_provider_count,
        secret_manager_binding_count=sum(
            1 for item in items if item.binding_mode == "live_secret_manager"
        ),
        secret_ref_resolved_count=sum(1 for item in items if item.secret_ref_resolved),
        rotation_automation_provider_count=sum(
            1
            for item in items
            if item.rotation_automation_ref != "not_required"
            and item.rotation_status != "blocked"
        ),
        rotation_evidence_provider_count=sum(
            1
            for item in items
            if item.rotation_evidence_ref != "not_required"
            and item.rotation_status != "blocked"
        ),
        rotation_drill_passed_count=sum(
            1 for item in items if item.rotation_drill_status == "passed"
        ),
        plaintext_secret_count=sum(
            1
            for item in items
            if item.secret_ref_scheme == "plaintext"
            or any("plaintext" in error for error in item.validation_errors)
        ),
        tenant_safe=tenant_safe,
        raw_identifier_count=raw_identifier_count,
        omitted_sensitive_fields=(
            "secret_value",
            "provider_api_key",
            "access_token",
            "prompt_payload",
        ),
        next_actions=next_actions,
        items=items,
    )


def build_secret_rotation_item(
    provider_id: str,
    row: dict[str, Any] | None,
    *,
    access_policy: LlmAdapterAccessPolicy,
    ops_policy: LlmProviderOpsPolicy,
    readiness_by_provider: dict[str, Any],
    runtime_by_provider: dict[str, Any],
    allowed_secret_ref_schemes: tuple[str, ...],
    allowed_rotation_ref_schemes: tuple[str, ...],
    allowed_evidence_ref_schemes: tuple[str, ...],
    max_rotation_days: int,
    required_live_controls: set[str],
) -> LlmProviderSecretRotationItem:
    provider = access_policy.providers[provider_id]
    ops_config = ops_policy.resolve_provider(provider_id)
    readiness_item = readiness_by_provider.get(provider_id)
    runtime_item = runtime_by_provider.get(provider_id)
    if row is None:
        return missing_secret_rotation_item(
            provider_id,
            network_enabled=provider.network_enabled,
            readiness_status=(
                readiness_item.readiness_status
                if readiness_item is not None
                else "missing"
            ),
            runtime_rollout_status=(
                runtime_item.rollout_status if runtime_item is not None else "missing"
            ),
        )

    binding_mode = require_str(row, "binding_mode", f"llm provider {provider_id}")
    secret_ref = require_str(row, "secret_ref", f"llm provider {provider_id}")
    secret_ref_resolved = require_bool(
        row,
        "secret_ref_resolved",
        f"llm provider {provider_id}",
    )
    rotation_interval_days = require_non_negative_int(
        row,
        "rotation_interval_days",
        f"llm provider {provider_id}",
    )
    rotation_automation_ref = require_str(
        row,
        "rotation_automation_ref",
        f"llm provider {provider_id}",
    )
    rotation_evidence_ref = require_str(
        row,
        "rotation_evidence_ref",
        f"llm provider {provider_id}",
    )
    rotation_drill_status = require_str(
        row,
        "rotation_drill_status",
        f"llm provider {provider_id}",
    )
    control_checks = normalize_string_tuple(row.get("control_checks", []))
    credential_ref_scheme = credential_scheme(ops_config.credential_ref)
    secret_ref_scheme = credential_scheme(secret_ref)
    readiness_status = (
        readiness_item.readiness_status if readiness_item is not None else "missing"
    )
    runtime_rollout_status = (
        runtime_item.rollout_status if runtime_item is not None else "missing"
    )
    errors: list[str] = []

    if secret_ref != ops_config.credential_ref:
        errors.append("secret ref must match provider ops credential ref")
    if secret_ref_scheme == "plaintext":
        errors.append("secret ref must not be plaintext")
    if contains_raw_identifier_marker(secret_ref):
        errors.append("secret ref must not expose raw tenant, token or API key markers")
    if readiness_item is None:
        errors.append("missing provider credential readiness item")
    elif readiness_status == "blocked":
        errors.append("provider credential readiness is blocked")
    if runtime_item is None:
        errors.append("missing provider runtime probe item")
    elif runtime_rollout_status == "blocked":
        errors.append("provider runtime probe is blocked")

    if provider.network_enabled:
        validate_live_provider_rotation(
            errors,
            binding_mode=binding_mode,
            secret_ref_scheme=secret_ref_scheme,
            secret_ref_resolved=secret_ref_resolved,
            rotation_interval_days=rotation_interval_days,
            rotation_automation_ref=rotation_automation_ref,
            rotation_evidence_ref=rotation_evidence_ref,
            rotation_drill_status=rotation_drill_status,
            control_checks=control_checks,
            runtime_item=runtime_item,
            allowed_secret_ref_schemes=allowed_secret_ref_schemes,
            allowed_rotation_ref_schemes=allowed_rotation_ref_schemes,
            allowed_evidence_ref_schemes=allowed_evidence_ref_schemes,
            max_rotation_days=max_rotation_days,
            required_live_controls=required_live_controls,
        )
    else:
        validate_contract_stub_rotation(
            errors,
            binding_mode=binding_mode,
            secret_ref_scheme=secret_ref_scheme,
            secret_ref_resolved=secret_ref_resolved,
            rotation_interval_days=rotation_interval_days,
            rotation_automation_ref=rotation_automation_ref,
            rotation_evidence_ref=rotation_evidence_ref,
            rotation_drill_status=rotation_drill_status,
            control_checks=control_checks,
        )

    rotation_status = (
        "blocked"
        if errors
        else "live_rotation_ready"
        if provider.network_enabled
        else "contract_stub_not_required"
    )
    return LlmProviderSecretRotationItem(
        provider_id=provider_id,
        active_provider=True,
        network_enabled=provider.network_enabled,
        readiness_status=readiness_status,
        runtime_rollout_status=runtime_rollout_status,
        binding_mode=binding_mode,
        credential_ref_scheme=credential_ref_scheme,
        secret_ref_scheme=secret_ref_scheme,
        secret_ref_resolved=secret_ref_resolved,
        rotation_interval_days=rotation_interval_days,
        rotation_automation_ref=rotation_automation_ref,
        rotation_evidence_ref=rotation_evidence_ref,
        rotation_drill_status=rotation_drill_status,
        control_checks=control_checks,
        rotation_status=rotation_status,
        validation_errors=tuple(errors),
    )


def validate_live_provider_rotation(
    errors: list[str],
    *,
    binding_mode: str,
    secret_ref_scheme: str,
    secret_ref_resolved: bool,
    rotation_interval_days: int,
    rotation_automation_ref: str,
    rotation_evidence_ref: str,
    rotation_drill_status: str,
    control_checks: tuple[str, ...],
    runtime_item: Any,
    allowed_secret_ref_schemes: tuple[str, ...],
    allowed_rotation_ref_schemes: tuple[str, ...],
    allowed_evidence_ref_schemes: tuple[str, ...],
    max_rotation_days: int,
    required_live_controls: set[str],
) -> None:
    if binding_mode != "live_secret_manager":
        errors.append("network provider must use live_secret_manager binding mode")
    if not starts_with_any(secret_ref_scheme, allowed_secret_ref_schemes):
        errors.append("live secret ref must use an allowed secret manager scheme")
    if not secret_ref_resolved:
        errors.append("live secret ref must resolve in runtime environment")
    if runtime_item is None or not runtime_item.runtime_secret_ref_resolved:
        errors.append("runtime secret probe must resolve the live secret ref")
    if rotation_interval_days <= 0 or rotation_interval_days > max_rotation_days:
        errors.append("rotation interval days must be within policy maximum")
    if not starts_with_any(rotation_automation_ref, allowed_rotation_ref_schemes):
        errors.append("rotation automation ref must use an allowed rotation scheme")
    if not starts_with_any(rotation_evidence_ref, allowed_evidence_ref_schemes):
        errors.append("rotation evidence ref must use an allowed evidence scheme")
    if rotation_drill_status != "passed":
        errors.append("live provider rotation drill must pass before rollout")
    missing_controls = sorted(required_live_controls - set(control_checks))
    if missing_controls:
        errors.append("missing live rotation controls: " + ", ".join(missing_controls))
    if contains_raw_identifier_marker(rotation_automation_ref):
        errors.append("rotation automation ref must not expose raw identifiers")
    if contains_raw_identifier_marker(rotation_evidence_ref):
        errors.append("rotation evidence ref must not expose raw identifiers")


def validate_contract_stub_rotation(
    errors: list[str],
    *,
    binding_mode: str,
    secret_ref_scheme: str,
    secret_ref_resolved: bool,
    rotation_interval_days: int,
    rotation_automation_ref: str,
    rotation_evidence_ref: str,
    rotation_drill_status: str,
    control_checks: tuple[str, ...],
) -> None:
    if binding_mode != "not_required":
        errors.append("contract stub provider must not declare live secret binding")
    if secret_ref_scheme != "local://":
        errors.append("contract stub provider must keep a local no-secret ref")
    if secret_ref_resolved:
        errors.append("contract stub provider must not resolve a live secret ref")
    if rotation_interval_days != 0:
        errors.append("contract stub provider rotation interval must be zero")
    if rotation_automation_ref != "not_required":
        errors.append("contract stub provider must not declare rotation automation")
    if rotation_evidence_ref != "not_required":
        errors.append("contract stub provider must not declare rotation evidence")
    if rotation_drill_status != "not_required":
        errors.append("contract stub provider must not declare a rotation drill")
    if "contract_stub_no_network" not in control_checks:
        errors.append("contract stub no-network control is required")
    if "no_plaintext_secret_material" not in control_checks:
        errors.append("contract stub no-plaintext control is required")


def missing_secret_rotation_item(
    provider_id: str,
    *,
    network_enabled: bool,
    readiness_status: str,
    runtime_rollout_status: str,
) -> LlmProviderSecretRotationItem:
    return LlmProviderSecretRotationItem(
        provider_id=provider_id,
        active_provider=True,
        network_enabled=network_enabled,
        readiness_status=readiness_status,
        runtime_rollout_status=runtime_rollout_status,
        binding_mode="missing",
        credential_ref_scheme="missing",
        secret_ref_scheme="missing",
        secret_ref_resolved=False,
        rotation_interval_days=0,
        rotation_automation_ref="missing",
        rotation_evidence_ref="missing",
        rotation_drill_status="missing",
        control_checks=(),
        rotation_status="blocked",
        validation_errors=("missing secret rotation policy entry",),
    )


def derive_secret_rotation_status(
    *,
    provider_count: int,
    blocked_provider_count: int,
    live_provider_count: int,
    contract_stub_provider_count: int,
    tenant_safe: bool,
) -> str:
    if blocked_provider_count or not tenant_safe:
        return "blocked"
    if provider_count == 0:
        return "not_configured"
    if live_provider_count:
        return "live_rotation_ready"
    if contract_stub_provider_count:
        return "contract_stub_rotation_controls_ready"
    return "not_configured"


def count_raw_identifier_markers(
    items: tuple[LlmProviderSecretRotationItem, ...],
) -> int:
    serialized = json.dumps(
        {"items": [item.to_snapshot_dict() for item in items]},
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


def build_llm_provider_secret_rotation_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_llm_provider_secret_rotation_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_llm_provider_secret_rotation_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    payload = build_llm_provider_secret_rotation_snapshot(
        root,
        generated_at=generated_at,
    )
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
        / "llm-provider-secret-rotation-policy.yaml"
    )


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "llm-provider-secret-rotation-v1.yaml"
    )
