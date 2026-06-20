from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from enterprise_dp.contracts import (
    DATA_PRODUCT_NAME,
    PRODUCT_CODE,
    TOPIC_NAME,
    VALID_CLASSIFICATIONS,
    ValidationResult,
    load_yaml,
    require_bool,
    require_mapping,
    require_string,
    require_string_list,
)


VALID_PRODUCT_STATUSES = {"draft", "pilot", "active", "deprecated"}
VALID_PUBLICATION_MODES = {
    "batch_connector",
    "cdc",
    "future_outbox_or_cdc",
    "http_event_collector",
    "manual_upload",
    "saas_connector",
    "transactional_outbox",
}
VALID_FIRST_SLICE_CONTRACT_STATUSES = {"planned", "existing"}
VALID_TENANT_ISOLATION_VALUES = {"REQUIRED", "AGGREGATE_ONLY", "NOT_REQUIRED"}


def scaffold_product_onboarding(
    root: str | Path,
    *,
    product_code: str,
    name: str,
    domains: list[str],
    business_sponsor: str,
    product_owner: str,
    technical_owner: str,
    data_steward: str = "enterprise-data-steward",
    status: str = "draft",
    default_data_residency: str = "REGION_CONTROLLED",
    enterprise_tenant_key: str = "tenant_id",
    product_org_key: str = "org_id",
    source_services: list[str] | None = None,
    publication_modes: list[str] | None = None,
    consumers: list[str] | None = None,
    classification: str = "CONFIDENTIAL",
    contains_pii: bool = True,
    tenant_isolation: str = "REQUIRED",
    default_retention_policy: str = "standard_personal_data_3y",
    default_access_personas: list[str] | None = None,
    consumer_contract: str = "catalog_registered_access_request_required",
    release_evidence_profile: str = "local-medallion-release.v1",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create the first product onboarding pack for a future enterprise product."""
    platform_root = Path(root)
    if not PRODUCT_CODE.fullmatch(product_code):
        raise ValueError("product_code must be a product code like enterprise-commerce")
    if not domains:
        raise ValueError("at least one domain is required")

    product_dir = platform_root / "products" / product_code
    onboarding_path = product_dir / "onboarding.yaml"
    readme_path = product_dir / "README.md"
    domain_readme_path = product_dir / "domains" / "README.md"
    use_case_readme_path = product_dir / "use-cases" / "README.md"
    if onboarding_path.exists() and not overwrite:
        raise FileExistsError(f"{onboarding_path} already exists; pass overwrite=True to replace it")

    entity_name = product_code.replace("-", "_")
    primary_domain = domains[0]
    onboarding = {
        "product": {
            "code": product_code,
            "name": name,
            "status": status,
            "businessSponsor": business_sponsor,
            "productOwner": product_owner,
            "technicalOwner": technical_owner,
            "dataSteward": data_steward,
            "defaultDataResidency": default_data_residency,
            "tenantModel": {
                "enterpriseTenantKey": enterprise_tenant_key,
                "productOrgKey": product_org_key,
            },
        },
        "domains": domains,
        "governance": {
            "classification": classification,
            "containsPii": contains_pii,
            "tenantIsolation": tenant_isolation,
            "defaultRetentionPolicy": default_retention_policy,
            "defaultAccessPersonas": default_access_personas
            or ["DataPlatformOperator", "DomainDataOwner"],
            "consumerContract": consumer_contract,
            "releaseEvidenceProfile": release_evidence_profile,
            "lineageRequired": True,
            "catalogRegistrationRequired": True,
            "dsarRequired": contains_pii,
        },
        "sourceSystems": [
            {
                "domain": primary_domain,
                "services": source_services or [f"{entity_name}-service"],
                "publicationModes": publication_modes or ["transactional_outbox", "cdc"],
            }
        ],
        "firstSlice": {
            "contractStatus": "planned",
            "topics": [f"{primary_domain}.{entity_name}.changed.v1"],
            "dataProducts": [
                f"bronze.events_{entity_name}_changed",
                f"silver.{entity_name}",
                f"gold.{entity_name}_daily_metrics",
            ],
        },
        "consumers": consumers or ["BI", "Compliance"],
    }

    product_dir.mkdir(parents=True, exist_ok=True)
    domain_readme_path.parent.mkdir(parents=True, exist_ok=True)
    use_case_readme_path.parent.mkdir(parents=True, exist_ok=True)
    onboarding_path.write_text(yaml.safe_dump(onboarding, sort_keys=False), encoding="utf-8")
    readme_path.write_text(product_readme(product_code, name), encoding="utf-8")
    domain_readme_path.write_text(product_domains_readme(product_code), encoding="utf-8")
    use_case_readme_path.write_text(product_use_cases_readme(product_code), encoding="utf-8")
    return {
        "product_code": product_code,
        "product_dir": product_dir.as_posix(),
        "onboarding_path": onboarding_path.as_posix(),
        "readme_path": readme_path.as_posix(),
        "domain_readme_path": domain_readme_path.as_posix(),
        "use_case_readme_path": use_case_readme_path.as_posix(),
        "first_slice_contract_status": "planned",
    }


def validate_product_onboarding_tree(root: Path) -> ValidationResult:
    result = ValidationResult()
    products_dir = root / "products"
    if not products_dir.exists():
        result.error(products_dir, "products directory is required")
        return result

    onboarding_files = sorted(products_dir.glob("*/onboarding.yaml"))
    if not onboarding_files:
        result.error(products_dir, "at least one product onboarding.yaml is required")
        return result

    onboarded_product_codes: set[str] = set()
    for path in onboarding_files:
        onboarding = load_yaml(path)
        result.checked_count += 1
        validate_product_onboarding(root, path, onboarding, result)
        product = onboarding.get("product")
        if isinstance(product, dict) and isinstance(product.get("code"), str):
            onboarded_product_codes.add(product["code"])

    validate_contract_product_coverage(root, onboarded_product_codes, load_enterprise_domain_codes(root), result)
    return result


def validate_product_onboarding(
    root: Path,
    path: Path,
    onboarding: dict[str, Any],
    result: ValidationResult,
) -> None:
    product = require_mapping(path, result, onboarding, "product")
    tenant_model = None
    if product:
        tenant_model = require_mapping(path, result, product, "tenantModel")
    domains = require_string_list(path, result, onboarding, "domains")
    governance = require_mapping(path, result, onboarding, "governance")
    source_systems = onboarding.get("sourceSystems")
    first_slice = require_mapping(path, result, onboarding, "firstSlice")
    require_string_list(path, result, onboarding, "consumers")

    if not all([product, domains, first_slice, governance]):
        return

    code = validate_product_metadata(path, product, tenant_model, result)
    if code:
        folder_code = path.parent.name
        if code != folder_code:
            result.error(path, f"product.code must match product folder name {folder_code!r}")

    domain_set = set(domains or [])
    validate_product_governance(root, path, governance, code, result)
    validate_source_systems(path, source_systems, domain_set, result)
    validate_first_slice(root, path, first_slice, code, result)


def validate_product_metadata(
    path: Path,
    product: dict[str, Any],
    tenant_model: dict[str, Any] | None,
    result: ValidationResult,
) -> str | None:
    code = require_string(path, result, product, "code", "product")
    if code and not PRODUCT_CODE.fullmatch(code):
        result.error(path, "product.code must be a product code like example-product")

    for key in (
        "name",
        "businessSponsor",
        "productOwner",
        "technicalOwner",
        "dataSteward",
        "defaultDataResidency",
    ):
        require_string(path, result, product, key, "product")

    status = require_string(path, result, product, "status", "product")
    if status and status not in VALID_PRODUCT_STATUSES:
        result.error(path, f"product.status must be one of {sorted(VALID_PRODUCT_STATUSES)}")

    if tenant_model:
        require_string(path, result, tenant_model, "enterpriseTenantKey", "product.tenantModel")
        require_string(path, result, tenant_model, "productOrgKey", "product.tenantModel")
    return code


def validate_product_governance(
    root: Path,
    path: Path,
    governance: dict[str, Any],
    product_code: str | None,
    result: ValidationResult,
) -> None:
    classification = require_string(path, result, governance, "classification", "governance")
    if classification and classification not in VALID_CLASSIFICATIONS:
        result.error(path, f"governance.classification must be one of {sorted(VALID_CLASSIFICATIONS)}")
    contains_pii = require_bool(path, result, governance, "containsPii", "governance")
    tenant_isolation = require_string(path, result, governance, "tenantIsolation", "governance")
    if tenant_isolation and tenant_isolation not in VALID_TENANT_ISOLATION_VALUES:
        result.error(path, f"governance.tenantIsolation must be one of {sorted(VALID_TENANT_ISOLATION_VALUES)}")
    if contains_pii is True and tenant_isolation != "REQUIRED":
        result.error(path, "governance.tenantIsolation must be REQUIRED when governance.containsPii=true")

    retention_policy = require_string(path, result, governance, "defaultRetentionPolicy", "governance")
    consumer_contract = require_string(path, result, governance, "consumerContract", "governance")
    release_profile = require_string(path, result, governance, "releaseEvidenceProfile", "governance")
    access_personas = require_string_list(path, result, governance, "defaultAccessPersonas", "governance")
    require_bool(path, result, governance, "lineageRequired", "governance")
    require_bool(path, result, governance, "catalogRegistrationRequired", "governance")
    dsar_required = require_bool(path, result, governance, "dsarRequired", "governance")
    if contains_pii is True and dsar_required is not True:
        result.error(path, "governance.dsarRequired must be true when governance.containsPii=true")

    persona_ids = registry_ids(root / "contracts" / "policies" / "access-personas.yaml", "personas")
    for persona in access_personas or []:
        if persona_ids and persona not in persona_ids:
            result.error(path, f"governance.defaultAccessPersonas references unknown persona {persona!r}")
    consumer_contract_ids = registry_ids(root / "contracts" / "policies" / "consumer-contracts.yaml", "contracts")
    if consumer_contract and consumer_contract_ids and consumer_contract not in consumer_contract_ids:
        result.error(path, f"governance.consumerContract references unknown contract {consumer_contract!r}")
    retention_policy_ids = registry_ids(root / "contracts" / "policies" / "retention-policies.yaml", "policies")
    if retention_policy and retention_policy_ids and retention_policy not in retention_policy_ids:
        result.error(path, f"governance.defaultRetentionPolicy references unknown policy {retention_policy!r}")
    release_profile_ids = registry_ids(root / "platform" / "observability" / "release-evidence-profiles.yaml", "profiles")
    if release_profile and release_profile_ids and release_profile not in release_profile_ids:
        result.error(path, f"governance.releaseEvidenceProfile references unknown profile {release_profile!r}")

    if product_code and retention_policy:
        maybe_warn_retention_policy_scope(root, path, product_code, retention_policy, result)


def validate_source_systems(
    path: Path,
    source_systems: object,
    domains: set[str],
    result: ValidationResult,
) -> None:
    if not isinstance(source_systems, list) or not source_systems:
        result.error(path, "sourceSystems must be a non-empty list")
        return
    for index, source in enumerate(source_systems):
        prefix = f"sourceSystems[{index}]"
        if not isinstance(source, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        domain = require_string(path, result, source, "domain", prefix)
        if domain and domain not in domains:
            result.error(path, f"{prefix}.domain must be listed in domains")
        require_string_list(path, result, source, "services", prefix)
        modes = require_string_list(path, result, source, "publicationModes", prefix)
        for mode in modes or []:
            if mode not in VALID_PUBLICATION_MODES:
                result.error(path, f"{prefix}.publicationModes contains unsupported mode {mode!r}")


def validate_first_slice(
    root: Path,
    path: Path,
    first_slice: dict[str, Any],
    product_code: str | None,
    result: ValidationResult,
) -> None:
    topics = require_string_list(path, result, first_slice, "topics", "firstSlice")
    data_products = require_string_list(path, result, first_slice, "dataProducts", "firstSlice")
    contract_status = first_slice.get("contractStatus", "existing")
    if not isinstance(contract_status, str) or contract_status not in VALID_FIRST_SLICE_CONTRACT_STATUSES:
        result.error(
            path,
            f"firstSlice.contractStatus must be one of {sorted(VALID_FIRST_SLICE_CONTRACT_STATUSES)}",
        )
        return
    for topic in topics or []:
        if not TOPIC_NAME.fullmatch(topic):
            result.error(path, f"firstSlice topic must be a topic name like product.entity.changed.v1: {topic!r}")
        elif contract_status == "existing":
            validate_topic_reference(root, path, topic, product_code, result)
    for data_product in data_products or []:
        if not DATA_PRODUCT_NAME.fullmatch(data_product):
            result.error(path, f"firstSlice data product must be bronze/silver/gold snake_case: {data_product!r}")
        elif contract_status == "existing":
            validate_data_product_reference(root, path, data_product, product_code, result)


def validate_topic_reference(
    root: Path,
    onboarding_path: Path,
    topic_name: str,
    product_code: str | None,
    result: ValidationResult,
) -> None:
    topic_path = root / "contracts" / "topics" / f"{topic_name}.yaml"
    if not topic_path.is_file():
        result.error(onboarding_path, f"firstSlice topic contract does not exist: {topic_name}")
        return
    topic = load_yaml(topic_path).get("topic")
    if isinstance(topic, dict) and product_code and topic.get("product") != product_code:
        result.error(onboarding_path, f"topic {topic_name} is not owned by product {product_code}")


def validate_data_product_reference(
    root: Path,
    onboarding_path: Path,
    data_product_name: str,
    product_code: str | None,
    result: ValidationResult,
) -> None:
    candidates = sorted((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))
    if not candidates:
        result.error(onboarding_path, f"firstSlice data product contract does not exist: {data_product_name}")
        return
    for contract_path in candidates:
        data_product = load_yaml(contract_path).get("dataProduct")
        if isinstance(data_product, dict) and product_code and data_product.get("product") != product_code:
            result.error(onboarding_path, f"data product {data_product_name} is not owned by product {product_code}")


def validate_contract_product_coverage(
    root: Path,
    onboarded_product_codes: set[str],
    enterprise_domain_codes: set[str],
    result: ValidationResult,
) -> None:
    for path in sorted((root / "contracts" / "topics").glob("*.yaml")):
        topic = load_yaml(path).get("topic")
        if isinstance(topic, dict):
            validate_product_domain_reference(
                path,
                "topic",
                topic.get("product"),
                topic.get("domain"),
                onboarded_product_codes,
                enterprise_domain_codes,
                result,
            )
    for path in sorted((root / "contracts" / "data-products").glob("*.yaml")):
        data_product = load_yaml(path).get("dataProduct")
        if isinstance(data_product, dict):
            validate_product_domain_reference(
                path,
                "data product",
                data_product.get("product"),
                data_product.get("domain"),
                onboarded_product_codes,
                enterprise_domain_codes,
                result,
            )


def validate_product_domain_reference(
    path: Path,
    contract_kind: str,
    product_code: object,
    domain: object,
    onboarded_product_codes: set[str],
    enterprise_domain_codes: set[str],
    result: ValidationResult,
) -> None:
    if isinstance(product_code, str) and product_code not in onboarded_product_codes:
        result.error(path, f"{contract_kind} product {product_code!r} must have products/{product_code}/onboarding.yaml")
    if isinstance(domain, str) and enterprise_domain_codes and domain not in enterprise_domain_codes:
        result.error(path, f"{contract_kind} domain {domain!r} must be listed in domains/registry.yaml")


def load_enterprise_domain_codes(root: Path) -> set[str]:
    registry_path = root / "domains" / "registry.yaml"
    if not registry_path.is_file():
        return set()
    registry = load_yaml(registry_path)
    domains = registry.get("domains")
    if not isinstance(domains, list):
        return set()
    return {
        domain["code"]
        for domain in domains
        if isinstance(domain, dict) and isinstance(domain.get("code"), str)
    }


def registry_ids(path: Path, list_key: str) -> set[str]:
    if not path.is_file():
        return set()
    registry = load_yaml(path)
    items = registry.get(list_key)
    if not isinstance(items, list):
        return set()
    return {
        item["id"]
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def maybe_warn_retention_policy_scope(
    root: Path,
    path: Path,
    product_code: str,
    retention_policy_id: str,
    result: ValidationResult,
) -> None:
    registry_path = root / "contracts" / "policies" / "retention-policies.yaml"
    if not registry_path.is_file():
        return
    policies = load_yaml(registry_path).get("policies")
    if not isinstance(policies, list):
        return
    for policy in policies:
        if not isinstance(policy, dict) or policy.get("id") != retention_policy_id:
            continue
        applies_to = policy.get("appliesTo")
        if not isinstance(applies_to, dict):
            return
        products = applies_to.get("products")
        if isinstance(products, list) and product_code not in products:
            result.warnings.append(
                f"{path}: governance.defaultRetentionPolicy {retention_policy_id!r} does not explicitly include product {product_code!r}"
            )
        return


def product_readme(product_code: str, name: str) -> str:
    return f"""# {name}

`{product_code}` is onboarded to the group enterprise data platform through `onboarding.yaml`.

Keep product-specific source-system notes, domain exceptions and first-slice planning here. Shared
platform controls remain under `dp/platform/`, `dp/contracts/` and `dp/governance/`.
"""


def product_domains_readme(product_code: str) -> str:
    return f"""# {product_code} Product Domains

Use this folder only for product-local source-domain notes. Enterprise data domains are registered in
`dp/domains/registry.yaml`.
"""


def product_use_cases_readme(product_code: str) -> str:
    return f"""# {product_code} Use Cases

Draft product-specific analytical use cases here before promoting them to the group-wide
`dp/use-cases/registry.yaml` portfolio.
"""
