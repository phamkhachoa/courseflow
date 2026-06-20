from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

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


PERSONA_ID = re.compile(r"^[A-Z][A-Za-z0-9]*$")
VALID_REGISTRY_STATUSES = {"draft", "active", "deprecated"}
VALID_SEVERITIES = {"P0", "P1", "P2"}
VALID_PERSONA_CATEGORIES = {
    "compliance",
    "consumer",
    "domain-owner",
    "executive",
    "platform",
    "risk",
}
VALID_ACCESS_MODES = {"admin", "approve", "audit", "operate", "read", "write"}


def validate_access_persona_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = access_persona_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "contracts/policies/access-personas.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    personas = registry.get("personas")
    if not isinstance(personas, list) or not personas:
        result.error(registry_path, "personas must be a non-empty list")
        return result

    seen_ids: set[str] = set()
    for index, persona in enumerate(personas):
        validate_access_persona(registry_path, persona, index, seen_ids, result)
    return result


def validate_access_persona(
    registry_path: Path,
    persona: object,
    index: int,
    seen_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"personas[{index}]"
    if not isinstance(persona, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    persona_id = require_string(registry_path, result, persona, "id", prefix)
    if persona_id:
        if not PERSONA_ID.fullmatch(persona_id):
            result.error(registry_path, f"{prefix}.id must be PascalCase")
        if persona_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates persona {persona_id}")
        seen_ids.add(persona_id)
    for key in ("name", "owner", "description"):
        require_string(registry_path, result, persona, key, prefix)
    status = require_string(registry_path, result, persona, "status", prefix)
    if status and status not in VALID_REGISTRY_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_REGISTRY_STATUSES)}")
    category = require_string(registry_path, result, persona, "category", prefix)
    if category and category not in VALID_PERSONA_CATEGORIES:
        result.error(registry_path, f"{prefix}.category must be one of {sorted(VALID_PERSONA_CATEGORIES)}")
    require_bool(registry_path, result, persona, "approvalRequired", prefix)
    validate_layer_list(registry_path, result, persona, "allowedLayers", prefix)
    validate_classification_list(registry_path, result, persona, "allowedClassifications", prefix)
    validate_access_mode_list(registry_path, result, persona, "defaultAccessModes", prefix)


def validate_consumer_contract_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = consumer_contract_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "contracts/policies/consumer-contracts.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    contracts = registry.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        result.error(registry_path, "contracts must be a non-empty list")
        return result

    persona_ids = load_access_persona_ids(root)
    seen_ids: set[str] = set()
    for index, contract in enumerate(contracts):
        validate_consumer_contract(registry_path, contract, index, seen_ids, persona_ids, result)
    return result


def validate_consumer_contract(
    registry_path: Path,
    contract: object,
    index: int,
    seen_ids: set[str],
    persona_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"contracts[{index}]"
    if not isinstance(contract, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    contract_id = require_string(registry_path, result, contract, "id", prefix)
    if contract_id:
        if not COLUMN_NAME.fullmatch(contract_id):
            result.error(registry_path, f"{prefix}.id must be snake_case")
        if contract_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates consumer contract {contract_id}")
        seen_ids.add(contract_id)
    for key in ("name", "owner", "description", "effectiveFrom"):
        require_string(registry_path, result, contract, key, prefix)
    require_int(registry_path, result, contract, "contractVersion", minimum=1, prefix=prefix)
    status = require_string(registry_path, result, contract, "status", prefix)
    if status and status not in VALID_REGISTRY_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_REGISTRY_STATUSES)}")
    severity = require_string(registry_path, result, contract, "severity", prefix)
    if severity and severity not in VALID_SEVERITIES:
        result.error(registry_path, f"{prefix}.severity must be one of {sorted(VALID_SEVERITIES)}")

    applies_to = require_mapping(registry_path, result, contract, "appliesTo")
    if applies_to:
        validate_layer_list(registry_path, result, applies_to, "layers", f"{prefix}.appliesTo")
        validate_classification_list(registry_path, result, applies_to, "classifications", f"{prefix}.appliesTo")

    personas = require_string_list(registry_path, result, contract, "allowedPersonas", prefix)
    validate_persona_references(registry_path, result, personas or [], persona_ids, f"{prefix}.allowedPersonas")
    validate_access_mode_list(registry_path, result, contract, "allowedAccessModes", prefix)
    evidence = require_string_list(registry_path, result, contract, "requiredEvidence", prefix)
    for evidence_item in evidence or []:
        if not COLUMN_NAME.fullmatch(evidence_item):
            result.error(registry_path, f"{prefix}.requiredEvidence contains non-snake-case evidence {evidence_item!r}")

    controls = require_mapping(registry_path, result, contract, "controls")
    if controls:
        for key in (
            "requireCatalogRegistration",
            "requireBusinessJustification",
            "requireOwnerApproval",
            "requireDataStewardApproval",
            "requireExpiryDate",
            "requireAuditLogging",
        ):
            require_bool(registry_path, result, controls, key, f"{prefix}.controls")
        require_int(registry_path, result, controls, "maxAccessDays", minimum=1, prefix=f"{prefix}.controls")
        require_int(registry_path, result, controls, "reviewCadenceDays", minimum=1, prefix=f"{prefix}.controls")


def evaluate_consumer_contract_reference(
    root: Path,
    *,
    data_product_name: str,
    layer: str | None,
    privacy: dict[str, Any],
    serving: dict[str, Any],
) -> dict[str, Any]:
    contract_id = serving.get("consumerContract")
    if not isinstance(contract_id, str):
        return {
            "contract_id": None,
            "passed": False,
            "checks": [check("consumer_contract_declared", False, {"reason": "consumer_contract_missing"})],
        }
    contract = get_consumer_contract(root, contract_id)
    registry = load_consumer_contract_registry(root)
    registry_hash = hash_consumer_contract_registry(root)
    serving_personas = serving.get("accessPersonas") if isinstance(serving.get("accessPersonas"), list) else []
    allowed_personas = set(contract.get("allowedPersonas", []))
    applies_to = contract.get("appliesTo", {})
    controls = contract.get("controls", {})
    checks = [
        check("consumer_contract_declared", True, {}),
        check("consumer_contract_active", contract.get("status") == "active", {"status": contract.get("status")}),
        check("consumer_contract_applies_to_layer", layer in applies_to.get("layers", []), {"layer": layer}),
        check(
            "consumer_contract_applies_to_classification",
            privacy.get("classification") in applies_to.get("classifications", []),
            {"classification": privacy.get("classification")},
        ),
        check(
            "consumer_contract_allows_personas",
            set(serving_personas).issubset(allowed_personas),
            {"serving_personas": serving_personas, "allowed_personas": sorted(allowed_personas)},
        ),
        check(
            "consumer_contract_requires_catalog_registration",
            controls.get("requireCatalogRegistration") is True,
            {"requireCatalogRegistration": controls.get("requireCatalogRegistration")},
        ),
        check(
            "consumer_contract_requires_audit_logging",
            controls.get("requireAuditLogging") is True,
            {"requireAuditLogging": controls.get("requireAuditLogging")},
        ),
    ]
    return {
        "contract_id": contract_id,
        "contract_name": contract.get("name"),
        "contract_version": contract.get("contractVersion"),
        "contract_status": contract.get("status"),
        "contract_severity": contract.get("severity"),
        "contract_owner": contract.get("owner"),
        "contract_effective_from": contract.get("effectiveFrom"),
        "contract_registry_scope": registry.get("registry_scope"),
        "contract_registry_hash": registry_hash,
        "data_product": data_product_name,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "allowed_personas": contract.get("allowedPersonas", []),
        "allowed_access_modes": contract.get("allowedAccessModes", []),
        "required_evidence": contract.get("requiredEvidence", []),
        "resolved_controls": controls,
    }


def validate_persona_references(
    path: Path,
    result: ValidationResult,
    personas: list[str],
    persona_ids: set[str],
    prefix: str,
) -> None:
    if not persona_ids:
        result.error(path, f"{prefix} cannot be validated because access persona registry is empty or missing")
        return
    for persona in personas:
        if persona not in persona_ids:
            result.error(path, f"{prefix} references unknown persona {persona!r}")


def validate_layer_list(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    prefix: str,
) -> None:
    layers = require_string_list(path, result, mapping, key, prefix)
    for layer in layers or []:
        if layer not in VALID_LAYERS:
            result.error(path, f"{prefix}.{key} contains unsupported layer {layer!r}")


def validate_classification_list(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    prefix: str,
) -> None:
    classifications = require_string_list(path, result, mapping, key, prefix)
    for classification in classifications or []:
        if classification not in VALID_CLASSIFICATIONS:
            result.error(path, f"{prefix}.{key} contains unsupported classification {classification!r}")


def validate_access_mode_list(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    prefix: str,
) -> None:
    modes = require_string_list(path, result, mapping, key, prefix)
    for mode in modes or []:
        if mode not in VALID_ACCESS_MODES:
            result.error(path, f"{prefix}.{key} contains unsupported access mode {mode!r}")


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
    }


def access_persona_registry_path(root: Path) -> Path:
    return root / "contracts" / "policies" / "access-personas.yaml"


def consumer_contract_registry_path(root: Path) -> Path:
    return root / "contracts" / "policies" / "consumer-contracts.yaml"


def load_access_persona_registry(root: Path) -> dict[str, Any]:
    path = access_persona_registry_path(root)
    if not path.is_file():
        return {}
    return load_yaml(path)


def list_access_personas(root: Path) -> list[dict[str, Any]]:
    registry = load_access_persona_registry(root)
    personas = registry.get("personas")
    return [persona for persona in personas if isinstance(persona, dict)] if isinstance(personas, list) else []


def load_access_persona_ids(root: Path) -> set[str]:
    return {
        persona["id"]
        for persona in list_access_personas(root)
        if isinstance(persona.get("id"), str)
    }


def load_consumer_contract_registry(root: Path) -> dict[str, Any]:
    path = consumer_contract_registry_path(root)
    if not path.is_file():
        return {}
    return load_yaml(path)


def list_consumer_contracts(root: Path) -> list[dict[str, Any]]:
    registry = load_consumer_contract_registry(root)
    contracts = registry.get("contracts")
    return [contract for contract in contracts if isinstance(contract, dict)] if isinstance(contracts, list) else []


def get_consumer_contract(root: Path, contract_id: str) -> dict[str, Any]:
    for contract in list_consumer_contracts(root):
        if contract.get("id") == contract_id:
            return contract
    raise KeyError(f"consumer contract is not registered: {contract_id}")


def load_consumer_contract_ids(root: Path) -> set[str]:
    return {
        contract["id"]
        for contract in list_consumer_contracts(root)
        if isinstance(contract.get("id"), str)
    }


def hash_access_persona_registry(root: Path) -> str:
    return hash_file(access_persona_registry_path(root))


def hash_consumer_contract_registry(root: Path) -> str:
    return hash_file(consumer_contract_registry_path(root))


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"
