from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class RegistryValidationError(ValueError):
    """Raised when an AI Platform registry is structurally invalid."""


@dataclass(frozen=True, slots=True)
class RegistryValidationReport:
    product_count: int
    use_case_count: int
    capability_count: int
    model_family_count: int
    model_family_alias_count: int
    non_lms_use_case_count: int
    artifact_count: int

    def to_dict(self) -> dict[str, int]:
        return {
            "productCount": self.product_count,
            "useCaseCount": self.use_case_count,
            "capabilityCount": self.capability_count,
            "modelFamilyCount": self.model_family_count,
            "modelFamilyAliasCount": self.model_family_alias_count,
            "nonLmsUseCaseCount": self.non_lms_use_case_count,
            "artifactCount": self.artifact_count,
        }


def validate_registries(ai_root: Path | str) -> RegistryValidationReport:
    root = Path(ai_root)
    products_registry = load_yaml(root / "products" / "registry.yaml")
    use_case_registry = load_yaml(root / "use-cases" / "registry.yaml")
    capability_registry = load_yaml(root / "platform" / "capabilities" / "registry.yaml")
    model_family_registry = load_yaml(root / "model-families" / "registry.yaml")

    products = require_list(products_registry, "products", "products registry")
    use_cases = require_list(use_case_registry, "use_cases", "use-case registry")
    capabilities = require_list(capability_registry, "capabilities", "capability registry")
    model_families = require_list(model_family_registry, "families", "model-family registry")

    product_ids = require_unique_ids(products, "products registry")
    use_case_ids = require_unique_ids(use_cases, "use-case registry")
    require_unique_ids(capabilities, "capability registry")
    model_family_ids, model_family_aliases = collect_model_family_ids(model_families)

    platform_product = require_str(products_registry, "platform_product", "products registry")
    if platform_product not in product_ids:
        raise RegistryValidationError(
            f"products registry platform_product does not exist: {platform_product}"
        )

    registry_platform_product = require_str(
        use_case_registry,
        "platform_product",
        "use-case registry",
    )
    if registry_platform_product != platform_product:
        raise RegistryValidationError(
            "use-case registry platform_product must match products registry "
            f"({registry_platform_product!r} != {platform_product!r})"
        )

    product_use_case_refs = collect_product_use_case_refs(products)
    unknown_product_refs = sorted(product_use_case_refs - use_case_ids)
    if unknown_product_refs:
        raise RegistryValidationError(
            "products registry references unknown use cases: " + ", ".join(unknown_product_refs)
        )

    non_lms_use_cases = 0
    for use_case in use_cases:
        use_case_id = require_str(use_case, "id", "use case")
        product_id = use_case.get("product")
        if product_id is None and use_case_id.startswith("lms-"):
            product_id = "lms-courseflow"
        if not isinstance(product_id, str) or not product_id.strip():
            raise RegistryValidationError(f"use case {use_case_id} must define a product")
        if product_id not in product_ids:
            raise RegistryValidationError(
                f"use case {use_case_id} references unknown product: {product_id}"
            )
        if product_id != "lms-courseflow":
            non_lms_use_cases += 1
        require_str(use_case, "status", f"use case {use_case_id}")
        require_str(use_case, "name", f"use case {use_case_id}")
        validate_model_family_refs(use_case, use_case_id, model_family_ids | model_family_aliases)

    if non_lms_use_cases < 5:
        raise RegistryValidationError(
            "AI Platform must maintain at least five non-LMS candidate use cases"
        )

    artifact_count = 0
    for registry_name, rows in (
        ("products registry", products),
        ("capability registry", capabilities),
    ):
        for row in rows:
            artifacts = row.get("artifacts", [])
            if artifacts is None:
                continue
            if not isinstance(artifacts, list):
                raise RegistryValidationError(f"{registry_name} artifacts must be a list")
            for artifact in artifacts:
                if not isinstance(artifact, str) or not artifact.strip():
                    raise RegistryValidationError(f"{registry_name} artifact path must be a string")
                artifact_count += 1
                artifact_path = root / artifact
                if not artifact_path.exists():
                    raise RegistryValidationError(
                        f"{registry_name} artifact does not exist: {artifact}"
                    )

    return RegistryValidationReport(
        product_count=len(product_ids),
        use_case_count=len(use_case_ids),
        capability_count=len(capabilities),
        model_family_count=len(model_family_ids),
        model_family_alias_count=len(model_family_aliases),
        non_lms_use_case_count=non_lms_use_cases,
        artifact_count=artifact_count,
    )


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RegistryValidationError(f"registry file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise RegistryValidationError(f"registry file must contain a mapping: {path}")
    return loaded


def require_list(row: dict[str, Any], key: str, owner: str) -> list[dict[str, Any]]:
    value = row.get(key)
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} must define list field {key}")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise RegistryValidationError(f"{owner} {key}[{index}] must be a mapping")
        result.append(item)
    return result


def require_str(row: dict[str, Any], key: str, owner: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RegistryValidationError(f"{owner} must define non-empty string field {key}")
    return value.strip()


def require_unique_ids(rows: list[dict[str, Any]], owner: str) -> set[str]:
    ids: set[str] = set()
    for row in rows:
        row_id = require_str(row, "id", owner)
        if row_id in ids:
            raise RegistryValidationError(f"{owner} has duplicate id: {row_id}")
        ids.add(row_id)
    return ids


def collect_product_use_case_refs(products: list[dict[str, Any]]) -> set[str]:
    refs: set[str] = set()
    for product in products:
        product_id = require_str(product, "id", "product")
        use_cases = product.get("ai_use_cases", [])
        if use_cases is None:
            continue
        if not isinstance(use_cases, list):
            raise RegistryValidationError(f"product {product_id} ai_use_cases must be a list")
        for use_case in use_cases:
            if not isinstance(use_case, str) or not use_case.strip():
                raise RegistryValidationError(
                    f"product {product_id} ai_use_cases must contain strings"
                )
            refs.add(use_case.strip())
    return refs


def collect_model_family_ids(model_families: list[dict[str, Any]]) -> tuple[set[str], set[str]]:
    family_ids: set[str] = set()
    aliases: set[str] = set()
    for family in model_families:
        family_id = require_str(family, "id", "model family")
        if family_id in family_ids or family_id in aliases:
            raise RegistryValidationError(f"model-family registry has duplicate id: {family_id}")
        family_ids.add(family_id)
        require_str(family, "name", f"model family {family_id}")
        require_str(family, "category", f"model family {family_id}")
        require_str(family, "maturity", f"model family {family_id}")
        validate_optional_string_list(family, "methods", f"model family {family_id}")
        validate_optional_string_list(family, "use_cases", f"model family {family_id}")
        for alias in validate_optional_string_list(family, "aliases", f"model family {family_id}"):
            if alias in family_ids or alias in aliases:
                raise RegistryValidationError(
                    f"model-family registry has duplicate alias or id: {alias}"
                )
            aliases.add(alias)
    if len(family_ids) < 20:
        raise RegistryValidationError("model-family registry must define at least 20 AI families")
    return family_ids, aliases


def validate_model_family_refs(
    use_case: dict[str, Any],
    use_case_id: str,
    known_model_families: set[str],
) -> None:
    families = use_case.get("model_family", [])
    if families is None:
        return
    if not isinstance(families, list):
        raise RegistryValidationError(f"use case {use_case_id} model_family must be a list")
    for family in families:
        if not isinstance(family, str) or not family.strip():
            raise RegistryValidationError(
                f"use case {use_case_id} model_family must contain strings"
            )
        if family.strip() not in known_model_families:
            raise RegistryValidationError(
                f"use case {use_case_id} references unknown model family: {family}"
            )


def validate_optional_string_list(
    row: dict[str, Any],
    key: str,
    owner: str,
) -> list[str]:
    value = row.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise RegistryValidationError(f"{owner} {key} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RegistryValidationError(f"{owner} {key} must contain strings")
        result.append(item.strip())
    return result
