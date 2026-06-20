from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from enterprise_dp.access_governance import (
    VALID_REGISTRY_STATUSES,
    VALID_SEVERITIES,
    load_access_persona_ids,
    validate_persona_references,
)
from enterprise_dp.contracts import (
    COLUMN_NAME,
    VALID_CLASSIFICATIONS,
    VALID_LAYERS,
    ValidationResult,
    load_yaml,
    require_bool,
    require_int,
    require_mapping,
    require_string,
    require_string_list,
)


def validate_access_policy_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = access_policy_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "contracts/policies/access-policies.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    policies = registry.get("policies")
    if not isinstance(policies, list) or not policies:
        result.error(registry_path, "policies must be a non-empty list")
        return result

    persona_ids = load_access_persona_ids(root)
    seen_ids: set[str] = set()
    for index, policy in enumerate(policies):
        validate_access_policy(registry_path, policy, index, seen_ids, persona_ids, result)
    return result


def validate_access_policy(
    registry_path: Path,
    policy: object,
    index: int,
    seen_ids: set[str],
    persona_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"policies[{index}]"
    if not isinstance(policy, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    policy_id = require_string(registry_path, result, policy, "id", prefix)
    if policy_id:
        if not COLUMN_NAME.fullmatch(policy_id):
            result.error(registry_path, f"{prefix}.id must be snake_case")
        if policy_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates policy {policy_id}")
        seen_ids.add(policy_id)
    for key in ("name", "owner", "description"):
        require_string(registry_path, result, policy, key, prefix)
    require_int(registry_path, result, policy, "policyVersion", minimum=1, prefix=prefix)
    status = require_string(registry_path, result, policy, "status", prefix)
    if status and status not in VALID_REGISTRY_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_REGISTRY_STATUSES)}")
    severity = require_string(registry_path, result, policy, "severity", prefix)
    if severity and severity not in VALID_SEVERITIES:
        result.error(registry_path, f"{prefix}.severity must be one of {sorted(VALID_SEVERITIES)}")
    require_string(registry_path, result, policy, "effectiveFrom", prefix)

    applies_to = require_mapping(registry_path, result, policy, "appliesTo")
    if applies_to:
        layers = require_string_list(registry_path, result, applies_to, "layers", f"{prefix}.appliesTo")
        for layer in layers or []:
            if layer not in VALID_LAYERS:
                result.error(registry_path, f"{prefix}.appliesTo.layers contains unsupported layer {layer!r}")
        classifications = require_string_list(registry_path, result, applies_to, "classifications", f"{prefix}.appliesTo")
        for classification in classifications or []:
            if classification not in VALID_CLASSIFICATIONS:
                result.error(registry_path, f"{prefix}.appliesTo.classifications contains unsupported classification {classification!r}")

    personas = require_string_list(registry_path, result, policy, "allowedPersonas", prefix)
    validate_persona_references(registry_path, result, personas or [], persona_ids, f"{prefix}.allowedPersonas")

    required_columns = policy.get("requiredColumns")
    if not isinstance(required_columns, list):
        result.error(registry_path, f"{prefix}.requiredColumns must be a list")
    elif not all(isinstance(column, str) and COLUMN_NAME.fullmatch(column) for column in required_columns):
        result.error(registry_path, f"{prefix}.requiredColumns must contain snake_case column names")

    controls = require_mapping(registry_path, result, policy, "controls")
    if controls:
        for key in (
            "requireTenantIsolation",
            "requireAuditLogging",
            "denyDirectIdentifiers",
            "requireConsumerContract",
            "requirePiiTagging",
        ):
            require_bool(registry_path, result, controls, key, f"{prefix}.controls")


def evaluate_access_policy_contract(
    root: Path,
    *,
    data_product_name: str,
    layer: str | None,
    privacy: dict[str, Any],
    serving: dict[str, Any],
    columns: list[dict[str, Any]],
) -> dict[str, Any]:
    policy_id = serving.get("accessPolicy")
    if not isinstance(policy_id, str):
        return {
            "policy_id": None,
            "passed": False,
            "checks": [
                check("policy_declared", False, {"reason": "access_policy_missing"}),
            ],
        }
    policy = get_access_policy(root, policy_id)
    registry = load_access_policy_registry(root)
    registry_hash = hash_access_policy_registry(root)
    column_names = {
        column.get("name")
        for column in columns
        if isinstance(column, dict) and isinstance(column.get("name"), str)
    }
    serving_personas = serving.get("accessPersonas") if isinstance(serving.get("accessPersonas"), list) else []
    policy_personas = set(policy.get("allowedPersonas", []))
    applies_to = policy.get("appliesTo", {})
    controls = policy.get("controls", {})
    pii_columns = [column.get("name") for column in columns if column.get("pii") is True]
    direct_identifiers = sorted(str(name) for name in column_names if name in direct_identifier_columns())
    checks = [
        check("policy_declared", True, {}),
        check("policy_active", policy.get("status") == "active", {"status": policy.get("status")}),
        check("policy_applies_to_layer", layer in applies_to.get("layers", []), {"layer": layer}),
        check(
            "policy_applies_to_classification",
            privacy.get("classification") in applies_to.get("classifications", []),
            {"classification": privacy.get("classification")},
        ),
        check(
            "personas_allowed_by_policy",
            set(serving_personas).issubset(policy_personas),
            {"serving_personas": serving_personas, "allowed_personas": sorted(policy_personas)},
        ),
        check(
            "required_columns_present",
            set(policy.get("requiredColumns", [])).issubset(column_names),
            {"required_columns": policy.get("requiredColumns", []), "columns": sorted(str(name) for name in column_names)},
        ),
        check(
            "tenant_isolation_required",
            controls.get("requireTenantIsolation") is not True or privacy.get("tenantIsolation") == "REQUIRED",
            {"tenant_isolation": privacy.get("tenantIsolation")},
        ),
        check(
            "consumer_contract_required",
            controls.get("requireConsumerContract") is not True or bool(serving.get("consumerContract")),
            {"consumer_contract": serving.get("consumerContract")},
        ),
        check(
            "pii_tagging_required",
            controls.get("requirePiiTagging") is not True or privacy.get("containsPii") is not True or bool(pii_columns),
            {"pii_columns": pii_columns},
        ),
        check(
            "direct_identifiers_denied",
            controls.get("denyDirectIdentifiers") is not True or not direct_identifiers,
            {"direct_identifier_columns": direct_identifiers},
        ),
    ]
    return {
        "policy_id": policy_id,
        "policy_hash": registry_hash,
        "policy_registry_hash": registry_hash,
        "policy_registry_scope": registry.get("registry_scope"),
        "policy_name": policy.get("name"),
        "policy_version": policy.get("policyVersion"),
        "status": policy.get("status"),
        "severity": policy.get("severity"),
        "owner": policy.get("owner"),
        "effective_from": policy.get("effectiveFrom"),
        "data_product": data_product_name,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "required_columns": policy.get("requiredColumns", []),
        "allowed_personas": policy.get("allowedPersonas", []),
        "resolved_controls": controls,
    }


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
    }


def access_policy_registry_path(root: Path) -> Path:
    return root / "contracts" / "policies" / "access-policies.yaml"


def load_access_policy_registry(root: Path) -> dict[str, Any]:
    path = access_policy_registry_path(root)
    if not path.is_file():
        return {}
    return load_yaml(path)


def list_access_policies(root: Path) -> list[dict[str, Any]]:
    registry = load_access_policy_registry(root)
    policies = registry.get("policies")
    return [policy for policy in policies if isinstance(policy, dict)] if isinstance(policies, list) else []


def get_access_policy(root: Path, policy_id: str) -> dict[str, Any]:
    for policy in list_access_policies(root):
        if policy.get("id") == policy_id:
            return policy
    raise KeyError(f"access policy is not registered: {policy_id}")


def load_access_policy_ids(root: Path) -> set[str]:
    return {
        policy["id"]
        for policy in list_access_policies(root)
        if isinstance(policy.get("id"), str)
    }


def hash_access_policy_registry(root: Path) -> str:
    digest = hashlib.sha256()
    with access_policy_registry_path(root).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def direct_identifier_columns() -> set[str]:
    return {
        "email",
        "first_name",
        "full_name",
        "last_name",
        "name",
        "phone",
        "profile_id",
        "student_id",
        "user_id",
    }
