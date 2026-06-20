from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_dp.contracts import (
    DATA_PRODUCT_NAME,
    ValidationResult,
    load_yaml,
    require_bool,
    require_int,
    require_mapping,
    require_string,
    require_string_list,
)


PROFILE_ID_PREFIX = "p"
VALID_PROFILE_SEVERITIES = {"P0", "P1", "P2", "P3"}


def validate_quality_profile_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = quality_profile_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "platform/quality/profiles.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    profiles = registry.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        result.error(registry_path, "profiles must be a non-empty list")
        return result

    seen_ids: set[str] = set()
    for index, profile in enumerate(profiles):
        validate_quality_profile(root, registry_path, profile, index, seen_ids, result)
    return result


def validate_quality_profile(
    root: Path,
    registry_path: Path,
    profile: object,
    index: int,
    seen_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"profiles[{index}]"
    if not isinstance(profile, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    profile_id = require_string(registry_path, result, profile, "id", prefix)
    if profile_id:
        if not profile_id.startswith(PROFILE_ID_PREFIX) or "_" in profile_id:
            result.error(registry_path, f"{prefix}.id must be a kebab-case profile id starting with 'p'")
        if profile_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates profile {profile_id}")
        seen_ids.add(profile_id)

    for key in ("name", "owner", "description"):
        require_string(registry_path, result, profile, key, prefix)
    severity = require_string(registry_path, result, profile, "severity", prefix)
    if severity and severity not in VALID_PROFILE_SEVERITIES:
        result.error(registry_path, f"{prefix}.severity must be one of {sorted(VALID_PROFILE_SEVERITIES)}")

    applies_to = require_mapping(registry_path, result, profile, "appliesTo")
    if applies_to:
        require_string_list(registry_path, result, applies_to, "domains", f"{prefix}.appliesTo")
        require_string_list(registry_path, result, applies_to, "useCases", f"{prefix}.appliesTo")
        primary_outputs = require_string_list(registry_path, result, applies_to, "primaryOutputs", f"{prefix}.appliesTo")
        for data_product_name in primary_outputs or []:
            validate_profile_data_product(root, registry_path, result, f"{prefix}.appliesTo.primaryOutputs", data_product_name)

    thresholds = require_mapping(registry_path, result, profile, "thresholds")
    if thresholds:
        require_int(registry_path, result, thresholds, "maxQuarantineRows", minimum=0, prefix=f"{prefix}.thresholds")
        require_int(registry_path, result, thresholds, "minPrimaryOutputRows", minimum=1, prefix=f"{prefix}.thresholds")
        require_bool(registry_path, result, thresholds, "requireUpstreamQuality", f"{prefix}.thresholds")
        require_bool(registry_path, result, thresholds, "requireAllOutputLayersQuality", f"{prefix}.thresholds")
        require_bool(registry_path, result, thresholds, "requireContentHash", f"{prefix}.thresholds")

    outputs = require_string_list(registry_path, result, profile, "requiredOutputDataProducts", prefix) or []
    for data_product_name in outputs:
        validate_profile_data_product(root, registry_path, result, f"{prefix}.requiredOutputDataProducts", data_product_name)

    required_columns = profile.get("requiredColumns")
    if not isinstance(required_columns, dict) or not required_columns:
        result.error(registry_path, f"{prefix}.requiredColumns must be a non-empty object")
        return
    for data_product_name, columns in required_columns.items():
        if not isinstance(data_product_name, str):
            result.error(registry_path, f"{prefix}.requiredColumns keys must be data product names")
            continue
        validate_profile_data_product(root, registry_path, result, f"{prefix}.requiredColumns", data_product_name)
        if not isinstance(columns, list) or not columns or not all(isinstance(column, str) and column.strip() for column in columns):
            result.error(registry_path, f"{prefix}.requiredColumns[{data_product_name}] must be a non-empty string list")
            continue
        contract_columns = data_product_columns(root, data_product_name)
        missing_columns = sorted(set(columns) - contract_columns)
        if missing_columns:
            result.error(registry_path, f"{prefix}.requiredColumns[{data_product_name}] columns are missing from contract: {missing_columns}")


def evaluate_quality_profile(
    root: Path,
    *,
    profile_id: str | None,
    use_case_id: str,
    primary_output: str,
    output_data_products: list[str],
    ingestion_manifest: dict[str, Any] | None,
    pipeline_manifest: dict[str, Any],
) -> dict[str, Any]:
    if not profile_id:
        return {
            "profile_id": None,
            "passed": False,
            "checks": [
                check("profile_declared", False, {"reason": "quality_profile_missing"}),
            ],
        }
    profile = get_quality_profile(root, profile_id)
    thresholds = profile.get("thresholds", {})
    applies_to = profile.get("appliesTo", {})
    layers = pipeline_manifest.get("layers", {})
    primary_layer = layers.get(primary_output, {}) if isinstance(layers, dict) else {}
    required_outputs = profile.get("requiredOutputDataProducts", [])
    quarantine_rows = ingestion_manifest.get("quarantine", {}).get("row_count") if ingestion_manifest else 0
    output_quality = {
        data_product_name: layers.get(data_product_name, {}).get("quality_passed")
        for data_product_name in output_data_products
        if isinstance(layers, dict)
    }
    checks = [
        check("profile_declared", True, {}),
        check("use_case_allowed", use_case_id in applies_to.get("useCases", []), {"use_case_id": use_case_id}),
        check("primary_output_allowed", primary_output in applies_to.get("primaryOutputs", []), {"primary_output": primary_output}),
        check(
            "declared_outputs_cover_profile",
            set(required_outputs).issubset(set(output_data_products)),
            {"required_outputs": required_outputs, "declared_outputs": output_data_products},
        ),
        check(
            "quarantine_threshold",
            quarantine_rows <= int(thresholds.get("maxQuarantineRows", 0)),
            {"quarantine_rows": quarantine_rows, "max_quarantine_rows": thresholds.get("maxQuarantineRows")},
        ),
        check(
            "primary_output_min_rows",
            int(primary_layer.get("row_count") or 0) >= int(thresholds.get("minPrimaryOutputRows", 1)),
            {"primary_output_rows": primary_layer.get("row_count"), "min_primary_output_rows": thresholds.get("minPrimaryOutputRows")},
        ),
        check(
            "upstream_quality",
            thresholds.get("requireUpstreamQuality") is not True or pipeline_manifest.get("upstream_quality_passed") is not False,
            {"upstream_quality_passed": pipeline_manifest.get("upstream_quality_passed")},
        ),
        check(
            "output_layers_quality",
            thresholds.get("requireAllOutputLayersQuality") is not True or all(value is True for value in output_quality.values()),
            {"output_quality": output_quality},
        ),
        check(
            "output_content_hashes",
            thresholds.get("requireContentHash") is not True
            or all(bool(layers.get(data_product_name, {}).get("content_hash")) for data_product_name in output_data_products),
            {"outputs": output_data_products},
        ),
    ]
    return {
        "profile_id": profile_id,
        "profile_hash": hash_quality_profile_registry(root),
        "owner": profile.get("owner"),
        "severity": profile.get("severity"),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
    }


def load_quality_profile_registry(root: Path) -> dict[str, Any]:
    path = quality_profile_registry_path(root)
    if not path.is_file():
        return {}
    return load_yaml(path)


def quality_profile_registry_path(root: Path) -> Path:
    return root / "platform" / "quality" / "profiles.yaml"


def list_quality_profiles(root: Path) -> list[dict[str, Any]]:
    registry = load_quality_profile_registry(root)
    profiles = registry.get("profiles")
    return [profile for profile in profiles if isinstance(profile, dict)] if isinstance(profiles, list) else []


def get_quality_profile(root: Path, profile_id: str) -> dict[str, Any]:
    for profile in list_quality_profiles(root):
        if profile.get("id") == profile_id:
            return profile
    raise KeyError(f"quality profile is not registered: {profile_id}")


def load_quality_profile_ids(root: Path) -> set[str]:
    return {
        profile["id"]
        for profile in list_quality_profiles(root)
        if isinstance(profile.get("id"), str)
    }


def hash_quality_profile_registry(root: Path) -> str:
    from enterprise_dp.catalog import hash_file

    return hash_file(quality_profile_registry_path(root))


def validate_profile_data_product(
    root: Path,
    registry_path: Path,
    result: ValidationResult,
    prefix: str,
    data_product_name: str,
) -> None:
    if not DATA_PRODUCT_NAME.fullmatch(data_product_name):
        result.error(registry_path, f"{prefix} contains invalid data product name {data_product_name!r}")
    elif not data_product_contract_exists(root, data_product_name):
        result.error(registry_path, f"{prefix} references data product without a contract {data_product_name!r}")


def data_product_contract_exists(root: Path, data_product_name: str) -> bool:
    return any((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))


def data_product_columns(root: Path, data_product_name: str) -> set[str]:
    candidates = sorted((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))
    if not candidates:
        return set()
    contract = load_yaml(candidates[0])
    columns = contract.get("schema", {}).get("columns")
    if not isinstance(columns, list):
        return set()
    return {
        column["name"]
        for column in columns
        if isinstance(column, dict) and isinstance(column.get("name"), str)
    }
