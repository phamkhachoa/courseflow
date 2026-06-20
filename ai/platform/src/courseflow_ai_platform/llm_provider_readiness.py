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
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml, require_str


@dataclass(frozen=True, slots=True)
class LlmProviderReadinessItem:
    provider_id: str
    active_provider: bool
    network_enabled: bool
    credential_mode: str
    credential_ref_scheme: str
    rotation_required: bool
    rotation_days: int
    deployment_checks: tuple[str, ...]
    readiness_status: str
    validation_errors: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activeProvider": self.active_provider,
            "credentialMode": self.credential_mode,
            "credentialRefScheme": self.credential_ref_scheme,
            "deploymentChecks": self.deployment_checks,
            "networkEnabled": self.network_enabled,
            "providerId": self.provider_id,
            "readinessStatus": self.readiness_status,
            "rotationDays": self.rotation_days,
            "rotationRequired": self.rotation_required,
            "validationErrors": self.validation_errors,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "active_provider": self.active_provider,
            "network_enabled": self.network_enabled,
            "credential_mode": self.credential_mode,
            "credential_ref_scheme": self.credential_ref_scheme,
            "rotation_required": self.rotation_required,
            "rotation_days": self.rotation_days,
            "deployment_checks": list(self.deployment_checks),
            "readiness_status": self.readiness_status,
            "validation_errors": list(self.validation_errors),
        }


@dataclass(frozen=True, slots=True)
class LlmProviderReadinessReport:
    generated_at: str
    policy_id: str
    readiness_status: str
    active_provider_count: int
    contract_stub_count: int
    live_provider_ready_count: int
    blocked_provider_count: int
    missing_provider_count: int
    plaintext_secret_count: int
    rotation_required_count: int
    deployment_check_count: int
    next_actions: tuple[str, ...]
    items: tuple[LlmProviderReadinessItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "activeProviderCount": self.active_provider_count,
            "blockedProviderCount": self.blocked_provider_count,
            "contractStubCount": self.contract_stub_count,
            "deploymentCheckCount": self.deployment_check_count,
            "generatedAt": self.generated_at,
            "items": [item.to_dict() for item in self.items],
            "liveProviderReadyCount": self.live_provider_ready_count,
            "missingProviderCount": self.missing_provider_count,
            "nextActions": self.next_actions,
            "plaintextSecretCount": self.plaintext_secret_count,
            "policyId": self.policy_id,
            "readinessStatus": self.readiness_status,
            "rotationRequiredCount": self.rotation_required_count,
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "report_id": "llm-provider-readiness-v1",
            "owner": "ai-platform",
            "generated_at": self.generated_at,
            "policy_id": self.policy_id,
            "summary": {
                "readiness_status": self.readiness_status,
                "active_provider_count": self.active_provider_count,
                "contract_stub_count": self.contract_stub_count,
                "live_provider_ready_count": self.live_provider_ready_count,
                "blocked_provider_count": self.blocked_provider_count,
                "missing_provider_count": self.missing_provider_count,
                "plaintext_secret_count": self.plaintext_secret_count,
                "rotation_required_count": self.rotation_required_count,
                "deployment_check_count": self.deployment_check_count,
            },
            "next_actions": list(self.next_actions),
            "items": [item.to_snapshot_dict() for item in self.items],
        }


def build_llm_provider_readiness_report(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> LlmProviderReadinessReport:
    root = Path(ai_root)
    access_policy = load_llm_adapter_access_policy(root)
    ops_policy = load_llm_provider_ops_policy(root, access_policy)
    readiness_policy = load_yaml(default_policy_path(root))
    report_date = generated_at or date.today().isoformat()
    return build_llm_provider_readiness_report_from_policy(
        readiness_policy,
        access_policy,
        ops_policy,
        generated_at=report_date,
    )


def build_llm_provider_readiness_report_from_policy(
    readiness_policy: dict[str, Any],
    access_policy: LlmAdapterAccessPolicy,
    ops_policy: LlmProviderOpsPolicy,
    *,
    generated_at: str,
) -> LlmProviderReadinessReport:
    allowed_live_schemes = normalize_string_tuple(
        readiness_policy.get("allowed_live_credential_ref_schemes", [])
    )
    if not allowed_live_schemes:
        raise RegistryValidationError(
            "llm provider readiness policy must define allowed live credential schemes"
        )
    max_rotation_days = require_non_negative_int(
        readiness_policy,
        "max_rotation_days",
        "llm provider readiness policy",
    )
    required_live_deployment_checks = set(
        normalize_string_tuple(readiness_policy.get("required_live_deployment_checks", []))
    )
    next_actions = normalize_string_tuple(readiness_policy.get("next_actions", []))
    provider_rows = require_mapping_list(
        readiness_policy,
        "providers",
        "llm provider readiness policy",
    )
    provider_rows_by_id = {
        require_str(row, "provider_id", "llm provider readiness provider"): row
        for row in provider_rows
    }
    items: list[LlmProviderReadinessItem] = []
    missing_provider_count = 0
    for provider_id, provider in access_policy.providers.items():
        row = provider_rows_by_id.get(provider_id)
        if row is None:
            missing_provider_count += 1
            items.append(
                LlmProviderReadinessItem(
                    provider_id=provider_id,
                    active_provider=True,
                    network_enabled=provider.network_enabled,
                    credential_mode="missing",
                    credential_ref_scheme="missing",
                    rotation_required=provider.network_enabled,
                    rotation_days=0,
                    deployment_checks=(),
                    readiness_status="blocked",
                    validation_errors=("missing credential readiness entry",),
                )
            )
            continue
        item = build_readiness_item(
            row,
            access_policy=access_policy,
            ops_policy=ops_policy,
            allowed_live_schemes=allowed_live_schemes,
            max_rotation_days=max_rotation_days,
            required_live_deployment_checks=required_live_deployment_checks,
        )
        items.append(item)
    blocked_provider_count = sum(1 for item in items if item.readiness_status == "blocked")
    plaintext_secret_count = sum(
        1
        for item in items
        if any("credential ref must be a secret URI" in error for error in item.validation_errors)
    )
    contract_stub_count = sum(
        1 for item in items if item.readiness_status == "contract_stub_ready"
    )
    live_provider_ready_count = sum(
        1 for item in items if item.readiness_status == "live_ready"
    )
    readiness_status = derive_readiness_status(
        blocked_provider_count=blocked_provider_count,
        live_provider_ready_count=live_provider_ready_count,
        contract_stub_count=contract_stub_count,
    )
    return LlmProviderReadinessReport(
        generated_at=generated_at,
        policy_id=require_str(readiness_policy, "policy_id", "llm provider readiness policy"),
        readiness_status=readiness_status,
        active_provider_count=len(access_policy.providers),
        contract_stub_count=contract_stub_count,
        live_provider_ready_count=live_provider_ready_count,
        blocked_provider_count=blocked_provider_count,
        missing_provider_count=missing_provider_count,
        plaintext_secret_count=plaintext_secret_count,
        rotation_required_count=sum(1 for item in items if item.rotation_required),
        deployment_check_count=sum(len(item.deployment_checks) for item in items),
        next_actions=next_actions,
        items=tuple(sorted(items, key=lambda item: item.provider_id)),
    )


def build_readiness_item(
    row: dict[str, Any],
    *,
    access_policy: LlmAdapterAccessPolicy,
    ops_policy: LlmProviderOpsPolicy,
    allowed_live_schemes: tuple[str, ...],
    max_rotation_days: int,
    required_live_deployment_checks: set[str],
) -> LlmProviderReadinessItem:
    provider_id = require_str(row, "provider_id", "llm provider readiness provider")
    provider = access_policy.providers.get(provider_id)
    if provider is None:
        raise RegistryValidationError(
            f"llm provider readiness references unknown provider: {provider_id}"
        )
    ops_config = ops_policy.resolve_provider(provider_id)
    credential_mode = require_str(row, "credential_mode", f"llm provider {provider_id}")
    credential_ref = require_str(row, "credential_ref", f"llm provider {provider_id}")
    rotation_required = require_bool(row, "rotation_required", f"llm provider {provider_id}")
    rotation_days = require_non_negative_int(row, "rotation_days", f"llm provider {provider_id}")
    deployment_checks = normalize_string_tuple(row.get("deployment_checks", []))
    errors: list[str] = []
    credential_ref_scheme = credential_scheme(credential_ref)
    if credential_ref != ops_config.credential_ref:
        errors.append("credential ref must match provider ops policy")
    if provider.network_enabled:
        if credential_mode != "live_secret_ref":
            errors.append("network provider must use live_secret_ref credential mode")
        if not any(credential_ref.startswith(scheme) for scheme in allowed_live_schemes):
            errors.append("credential ref must be a secret URI from an allowed scheme")
        if not rotation_required:
            errors.append("network provider must require credential rotation")
        if rotation_days <= 0 or rotation_days > max_rotation_days:
            errors.append("rotation days must be within live provider maximum")
        missing_checks = sorted(required_live_deployment_checks - set(deployment_checks))
        if missing_checks:
            errors.append("missing live deployment checks: " + ", ".join(missing_checks))
    else:
        if credential_mode != "local_stub":
            errors.append("contract stub provider must use local_stub credential mode")
        if credential_ref_scheme != "local://":
            errors.append("contract stub provider must use local credential ref")
    readiness_status = (
        "blocked"
        if errors
        else "live_ready"
        if provider.network_enabled
        else "contract_stub_ready"
    )
    return LlmProviderReadinessItem(
        provider_id=provider_id,
        active_provider=True,
        network_enabled=provider.network_enabled,
        credential_mode=credential_mode,
        credential_ref_scheme=credential_ref_scheme,
        rotation_required=rotation_required,
        rotation_days=rotation_days,
        deployment_checks=deployment_checks,
        readiness_status=readiness_status,
        validation_errors=tuple(errors),
    )


def build_llm_provider_readiness_snapshot(
    ai_root: Path | str,
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_llm_provider_readiness_report(
        ai_root,
        generated_at=generated_at,
    ).to_snapshot_dict()


def write_llm_provider_readiness_snapshot(
    ai_root: Path | str,
    output_path: Path | str | None = None,
    *,
    generated_at: str | None = None,
) -> Path:
    root = Path(ai_root)
    target = Path(output_path) if output_path is not None else default_snapshot_path(root)
    payload = build_llm_provider_readiness_snapshot(root, generated_at=generated_at)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
    return target


def derive_readiness_status(
    *,
    blocked_provider_count: int,
    live_provider_ready_count: int,
    contract_stub_count: int,
) -> str:
    if blocked_provider_count:
        return "blocked"
    if live_provider_ready_count:
        return "live_ready"
    if contract_stub_count:
        return "contract_stub_ready"
    return "not_configured"


def credential_scheme(credential_ref: str) -> str:
    if "://" not in credential_ref:
        return "plaintext"
    return credential_ref.split("://", maxsplit=1)[0] + "://"


def normalize_string_tuple(value: object | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list | tuple):
        raise RegistryValidationError("readiness policy values must be strings or lists")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(
                "readiness policy list values must be non-empty strings"
            )
        result.append(item.strip())
    return tuple(result)


def require_bool(row: dict[str, Any], key: str, owner: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise RegistryValidationError(f"{owner} must define boolean field {key}")
    return value


def require_non_negative_int(row: dict[str, Any], key: str, owner: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise RegistryValidationError(
            f"{owner} must define non-negative integer field {key}"
        )
    return value


def require_mapping_list(row: dict[str, Any], key: str, owner: str) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def default_policy_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "policies"
        / "llm-provider-credential-readiness.yaml"
    )


def default_snapshot_path(root: Path) -> Path:
    return (
        root
        / "platform"
        / "governance"
        / "reports"
        / "llm-provider-readiness-v1.yaml"
    )
