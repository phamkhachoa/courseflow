from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_dp.contracts import (
    PRODUCT_CODE,
    ValidationResult,
    load_yaml,
    require_int,
    require_string,
    require_string_list,
)


VALID_DOMAIN_STATUSES = {"planned", "pilot", "active", "deprecated"}


def validate_domain_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = root / "domains" / "registry.yaml"
    if not registry_path.is_file():
        result.error(registry_path, "domains/registry.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registry_scope")
    first_product = require_string(registry_path, result, registry, "first_product_pilot")
    if first_product:
        if not PRODUCT_CODE.fullmatch(first_product):
            result.error(registry_path, "first_product_pilot must be a product code like example-product")
        if not (root / "products" / first_product / "onboarding.yaml").is_file():
            result.error(registry_path, f"first_product_pilot is not onboarded: {first_product}")

    domains = registry.get("domains")
    if not isinstance(domains, list) or not domains:
        result.error(registry_path, "domains must be a non-empty list")
        return result

    seen: set[str] = set()
    for index, domain in enumerate(domains):
        validate_domain_entry(root, registry_path, domain, index, seen, result)
    return result


def validate_domain_entry(
    root: Path,
    registry_path: Path,
    domain: object,
    index: int,
    seen: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"domains[{index}]"
    if not isinstance(domain, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    code = require_string(registry_path, result, domain, "code", prefix)
    if code:
        if not PRODUCT_CODE.fullmatch(code):
            result.error(registry_path, f"{prefix}.code must be a domain code like product-analytics")
        if code in seen:
            result.error(registry_path, f"{prefix}.code duplicates domain {code}")
        seen.add(code)
        readme = root / "domains" / code / "README.md"
        if not readme.is_file():
            result.error(registry_path, f"{prefix}.code must have domains/{code}/README.md")

    for key in ("name", "business_capability", "pilot_product_contribution"):
        require_string(registry_path, result, domain, key, prefix)

    status = require_string(registry_path, result, domain, "status", prefix)
    if status and status not in VALID_DOMAIN_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_DOMAIN_STATUSES)}")

    require_string_list(registry_path, result, domain, "first_data_products", prefix)
    require_string_list(registry_path, result, domain, "first_consumers", prefix)
    require_string_list(registry_path, result, domain, "future_onboarding_products", prefix)
