from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from enterprise_dp.access_governance import load_access_persona_ids
from enterprise_dp.contracts import (
    DATA_PRODUCT_NAME,
    TOPIC_NAME,
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
from enterprise_dp.pipelines import default_pipeline_registry
from enterprise_dp.quality_profiles import get_quality_profile, load_quality_profile_ids
from enterprise_dp.release_profiles import get_release_profile, load_release_profile_ids


USE_CASE_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_STATUSES = {"planned", "pilot", "active", "deprecated"}
VALID_CONTRACT_STATUSES = {"planned", "existing", "deprecated"}


def validate_use_case_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = root / "use-cases" / "registry.yaml"
    if not registry_path.is_file():
        result.error(registry_path, "use-cases/registry.yaml is required")
        return result

    result.checked_count += 1
    registry = load_yaml(registry_path)
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "portfolio_scope")
    use_cases = registry.get("useCases")
    if not isinstance(use_cases, list) or not use_cases:
        result.error(registry_path, "useCases must be a non-empty list")
        return result

    domain_codes = load_domain_codes(root)
    onboarded_products = load_product_codes(root)
    registered_pipeline_specs = {
        spec.runner_id: spec for spec in default_pipeline_registry().list_specs()
    }
    registered_personas = load_access_persona_ids(root)
    registered_quality_profiles = load_quality_profile_ids(root)
    registered_release_profiles = load_release_profile_ids(root)
    seen_ids: set[str] = set()
    for index, use_case in enumerate(use_cases):
        validate_use_case(
            root,
            registry_path,
            use_case,
            index,
            domain_codes,
            onboarded_products,
            registered_pipeline_specs,
            registered_personas,
            registered_quality_profiles,
            registered_release_profiles,
            seen_ids,
            result,
        )
    return result


def validate_use_case(
    root: Path,
    registry_path: Path,
    use_case: object,
    index: int,
    domain_codes: set[str],
    onboarded_products: set[str],
    registered_pipeline_specs: dict[str, Any],
    registered_personas: set[str],
    registered_quality_profiles: set[str],
    registered_release_profiles: set[str],
    seen_ids: set[str],
    result: ValidationResult,
) -> None:
    prefix = f"useCases[{index}]"
    if not isinstance(use_case, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return

    use_case_id = require_string(registry_path, result, use_case, "id", prefix)
    if use_case_id:
        if not USE_CASE_ID.fullmatch(use_case_id):
            result.error(registry_path, f"{prefix}.id must be kebab-case")
        if use_case_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates use case {use_case_id}")
        seen_ids.add(use_case_id)

    for key in ("name", "owner", "businessOutcome"):
        require_string(registry_path, result, use_case, key, prefix)

    domain = require_string(registry_path, result, use_case, "domain", prefix)
    if domain and domain_codes and domain not in domain_codes:
        result.error(registry_path, f"{prefix}.domain must be listed in domains/registry.yaml")

    priority = require_string(registry_path, result, use_case, "priority", prefix)
    if priority and priority not in VALID_PRIORITIES:
        result.error(registry_path, f"{prefix}.priority must be one of {sorted(VALID_PRIORITIES)}")

    status = require_string(registry_path, result, use_case, "status", prefix)
    if status and status not in VALID_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_STATUSES)}")

    for key in (
        "primaryConsumers",
        "sourceProducts",
        "sourceSystems",
        "kpis",
        "accessPersonas",
        "platformCapabilities",
        "releaseGates",
    ):
        require_string_list(registry_path, result, use_case, key, prefix)

    access_personas = use_case.get("accessPersonas")
    if registered_personas and isinstance(access_personas, list):
        for persona in access_personas:
            if isinstance(persona, str) and persona not in registered_personas:
                result.error(registry_path, f"{prefix}.accessPersonas references unknown persona {persona!r}")

    source_products = use_case.get("sourceProducts")
    if isinstance(source_products, list):
        for product_code in source_products:
            if isinstance(product_code, str) and product_code not in onboarded_products:
                result.error(registry_path, f"{prefix}.sourceProducts contains non-onboarded product {product_code!r}")

    pipeline_runners = use_case.get("pipelineRunners")
    registered_pipeline_runners = set(registered_pipeline_specs)
    if pipeline_runners is not None:
        runners = require_string_list(registry_path, result, use_case, "pipelineRunners", prefix)
        for runner_id in runners or []:
            if runner_id not in registered_pipeline_runners:
                result.error(registry_path, f"{prefix}.pipelineRunners contains unregistered runner {runner_id!r}")

    validate_use_case_data_products(root, registry_path, use_case, prefix, result)
    validate_use_case_implementation(
        root,
        registry_path,
        use_case,
        prefix,
        registered_pipeline_specs,
        registered_quality_profiles,
        registered_release_profiles,
        result,
    )
    validate_use_case_governance(registry_path, use_case, prefix, result)


def validate_use_case_implementation(
    root: Path,
    registry_path: Path,
    use_case: dict[str, Any],
    prefix: str,
    registered_pipeline_specs: dict[str, Any],
    registered_quality_profiles: set[str],
    registered_release_profiles: set[str],
    result: ValidationResult,
) -> None:
    implementation = use_case.get("implementation")
    if implementation is None:
        return
    if not isinstance(implementation, dict):
        result.error(registry_path, f"{prefix}.implementation must be an object")
        return

    pipelines = implementation.get("pipelines")
    if not isinstance(pipelines, list) or not pipelines:
        result.error(registry_path, f"{prefix}.implementation.pipelines must be a non-empty list")
        return

    raw_runner_ids = use_case.get("pipelineRunners")
    declared_runner_ids = {
        runner_id for runner_id in raw_runner_ids if isinstance(runner_id, str)
    } if isinstance(raw_runner_ids, list) else set()
    declared_data_products = use_case_declared_data_product_names(use_case)
    topic_names = load_topic_names(root)
    for index, pipeline in enumerate(pipelines):
        item_prefix = f"{prefix}.implementation.pipelines[{index}]"
        if not isinstance(pipeline, dict):
            result.error(registry_path, f"{item_prefix} must be an object")
            continue

        runner_id = require_string(registry_path, result, pipeline, "runnerId", item_prefix)
        spec = registered_pipeline_specs.get(runner_id or "")
        if runner_id and spec is None:
            result.error(registry_path, f"{item_prefix}.runnerId contains unregistered runner {runner_id!r}")
        if runner_id and declared_runner_ids and runner_id not in declared_runner_ids:
            result.error(registry_path, f"{item_prefix}.runnerId must also be listed in pipelineRunners")

        input_topics = optional_string_list(registry_path, result, pipeline, "inputTopics", item_prefix)
        input_data_products = optional_string_list(registry_path, result, pipeline, "inputDataProducts", item_prefix)
        output_data_products = require_string_list(registry_path, result, pipeline, "outputDataProducts", item_prefix) or []
        primary_output = require_string(registry_path, result, pipeline, "primaryOutput", item_prefix)
        quality_profile = require_string(registry_path, result, pipeline, "qualityProfile", item_prefix)
        release_profile = require_string(registry_path, result, pipeline, "releaseEvidenceProfile", item_prefix)

        if spec and spec.input_kind in {"approved_bronze_jsonl", "raw_event_jsonl"} and not input_topics:
            result.error(registry_path, f"{item_prefix}.inputTopics is required for event-backed runner {runner_id!r}")

        for topic_name in input_topics or []:
            if not TOPIC_NAME.fullmatch(topic_name):
                result.error(registry_path, f"{item_prefix}.inputTopics contains invalid topic name {topic_name!r}")
            elif topic_names and topic_name not in topic_names:
                result.error(registry_path, f"{item_prefix}.inputTopics contains topic without a contract {topic_name!r}")
        if spec and spec.input_topics and set(input_topics or []) != set(spec.input_topics):
            result.error(registry_path, f"{item_prefix}.inputTopics must match registered runner input topics")

        for data_product_name in input_data_products or []:
            validate_implementation_data_product(root, registry_path, result, item_prefix, data_product_name)
            if data_product_name not in declared_data_products:
                result.error(registry_path, f"{item_prefix}.inputDataProducts contains data product not listed on the use case {data_product_name!r}")
        if spec and spec.input_data_products and set(input_data_products or []) != set(spec.input_data_products):
            result.error(registry_path, f"{item_prefix}.inputDataProducts must match registered runner input data products")

        for data_product_name in output_data_products:
            validate_implementation_data_product(root, registry_path, result, item_prefix, data_product_name)
            if data_product_name not in declared_data_products:
                result.error(registry_path, f"{item_prefix}.outputDataProducts contains data product not listed on the use case {data_product_name!r}")
        if spec and set(output_data_products) != set(spec.output_data_products):
            result.error(registry_path, f"{item_prefix}.outputDataProducts must match registered runner outputs")

        if primary_output:
            validate_implementation_data_product(root, registry_path, result, item_prefix, primary_output)
            if primary_output not in output_data_products:
                result.error(registry_path, f"{item_prefix}.primaryOutput must be included in outputDataProducts")
            if spec and spec.primary_output and primary_output != spec.primary_output:
                result.error(registry_path, f"{item_prefix}.primaryOutput must match registered runner primary output")

        if quality_profile:
            if quality_profile not in registered_quality_profiles:
                result.error(registry_path, f"{item_prefix}.qualityProfile contains unregistered quality profile {quality_profile!r}")
            else:
                validate_quality_profile_scope(root, registry_path, result, item_prefix, quality_profile, use_case, primary_output)
        if release_profile:
            if release_profile not in registered_release_profiles:
                result.error(registry_path, f"{item_prefix}.releaseEvidenceProfile contains unregistered release evidence profile {release_profile!r}")
            else:
                validate_release_profile_scope(root, registry_path, result, item_prefix, release_profile, use_case, spec)


def validate_quality_profile_scope(
    root: Path,
    registry_path: Path,
    result: ValidationResult,
    prefix: str,
    quality_profile_id: str,
    use_case: dict[str, Any],
    primary_output: str | None,
) -> None:
    profile = get_quality_profile(root, quality_profile_id)
    applies_to = profile.get("appliesTo", {})
    use_case_id = use_case.get("id")
    domain = use_case.get("domain")
    if isinstance(applies_to, dict):
        if isinstance(use_case_id, str) and use_case_id not in applies_to.get("useCases", []):
            result.error(registry_path, f"{prefix}.qualityProfile does not apply to use case {use_case_id!r}")
        if isinstance(domain, str) and domain not in applies_to.get("domains", []):
            result.error(registry_path, f"{prefix}.qualityProfile does not apply to domain {domain!r}")
        if primary_output and primary_output not in applies_to.get("primaryOutputs", []):
            result.error(registry_path, f"{prefix}.qualityProfile does not apply to primary output {primary_output!r}")


def validate_release_profile_scope(
    root: Path,
    registry_path: Path,
    result: ValidationResult,
    prefix: str,
    release_profile_id: str,
    use_case: dict[str, Any],
    spec: Any,
) -> None:
    profile = get_release_profile(root, release_profile_id)
    applies_to = profile.get("appliesTo", {})
    use_case_id = use_case.get("id")
    runner_input_kind = getattr(spec, "input_kind", None)
    if isinstance(applies_to, dict):
        if isinstance(use_case_id, str) and use_case_id not in applies_to.get("useCases", []):
            result.error(registry_path, f"{prefix}.releaseEvidenceProfile does not apply to use case {use_case_id!r}")
        if runner_input_kind and runner_input_kind not in applies_to.get("runnerInputKinds", []):
            result.error(registry_path, f"{prefix}.releaseEvidenceProfile does not apply to runner input kind {runner_input_kind!r}")


def optional_string_list(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    prefix: str,
) -> list[str] | None:
    if key not in mapping:
        return None
    return require_string_list(path, result, mapping, key, prefix)


def validate_implementation_data_product(
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


def validate_use_case_data_products(
    root: Path,
    registry_path: Path,
    use_case: dict[str, Any],
    prefix: str,
    result: ValidationResult,
) -> None:
    data_products = use_case.get("dataProducts")
    if not isinstance(data_products, list) or not data_products:
        result.error(registry_path, f"{prefix}.dataProducts must be a non-empty list")
        return

    for index, data_product in enumerate(data_products):
        item_prefix = f"{prefix}.dataProducts[{index}]"
        if not isinstance(data_product, dict):
            result.error(registry_path, f"{item_prefix} must be an object")
            continue
        name = require_string(registry_path, result, data_product, "name", item_prefix)
        layer = require_string(registry_path, result, data_product, "layer", item_prefix)
        contract_status = require_string(registry_path, result, data_product, "contractStatus", item_prefix)

        if name and not DATA_PRODUCT_NAME.fullmatch(name):
            result.error(registry_path, f"{item_prefix}.name must look like bronze|silver|gold.dataset_name")
        if layer and layer not in VALID_LAYERS:
            result.error(registry_path, f"{item_prefix}.layer must be one of {sorted(VALID_LAYERS)}")
        if name and layer and not name.startswith(f"{layer.lower()}."):
            result.error(registry_path, f"{item_prefix}.layer must match the data product name prefix")
        if contract_status and contract_status not in VALID_CONTRACT_STATUSES:
            result.error(registry_path, f"{item_prefix}.contractStatus must be one of {sorted(VALID_CONTRACT_STATUSES)}")
        if name and contract_status == "existing" and not data_product_contract_exists(root, name):
            result.error(registry_path, f"{item_prefix}.contractStatus=existing but contract does not exist for {name}")


def validate_use_case_governance(
    registry_path: Path,
    use_case: dict[str, Any],
    prefix: str,
    result: ValidationResult,
) -> None:
    governance = require_mapping(registry_path, result, use_case, "governance")
    if not governance:
        return
    classification = require_string(registry_path, result, governance, "classification", f"{prefix}.governance")
    if classification and classification not in VALID_CLASSIFICATIONS:
        result.error(registry_path, f"{prefix}.governance.classification must be one of {sorted(VALID_CLASSIFICATIONS)}")
    require_string(registry_path, result, governance, "dataResidency", f"{prefix}.governance")
    require_bool(registry_path, result, governance, "containsPii", f"{prefix}.governance")
    require_string(registry_path, result, governance, "tenantIsolation", f"{prefix}.governance")


def load_domain_codes(root: Path) -> set[str]:
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


def load_product_codes(root: Path) -> set[str]:
    product_codes: set[str] = set()
    for path in sorted((root / "products").glob("*/onboarding.yaml")):
        onboarding = load_yaml(path)
        product = onboarding.get("product")
        if isinstance(product, dict) and isinstance(product.get("code"), str):
            product_codes.add(product["code"])
    return product_codes


def data_product_contract_exists(root: Path, data_product_name: str) -> bool:
    return any((root / "contracts" / "data-products").glob(f"{data_product_name}.v*.yaml"))


def load_use_case_registry(root: Path) -> dict[str, Any]:
    return load_yaml(root / "use-cases" / "registry.yaml")


def list_use_cases(root: Path) -> list[dict[str, Any]]:
    registry = load_use_case_registry(root)
    use_cases = registry.get("useCases")
    return [item for item in use_cases if isinstance(item, dict)] if isinstance(use_cases, list) else []


def get_use_case(root: Path, use_case_id: str) -> dict[str, Any]:
    for use_case in list_use_cases(root):
        if use_case.get("id") == use_case_id:
            return use_case
    raise KeyError(f"use case is not registered: {use_case_id}")


def get_use_case_pipeline(
    root: Path,
    use_case_id: str,
    *,
    runner_id: str | None = None,
) -> dict[str, Any]:
    use_case = get_use_case(root, use_case_id)
    implementation = use_case.get("implementation")
    pipelines = implementation.get("pipelines") if isinstance(implementation, dict) else None
    if not isinstance(pipelines, list) or not pipelines:
        raise ValueError(f"use case has no implementation pipelines: {use_case_id}")

    candidates = [pipeline for pipeline in pipelines if isinstance(pipeline, dict)]
    if runner_id:
        for pipeline in candidates:
            if pipeline.get("runnerId") == runner_id:
                return pipeline
        raise ValueError(f"use case {use_case_id!r} does not declare runner {runner_id!r}")
    if len(candidates) == 1:
        return candidates[0]
    runner_ids = [str(pipeline.get("runnerId")) for pipeline in candidates]
    raise ValueError(f"use case {use_case_id!r} requires runner_id disambiguation; candidates={runner_ids}")


def use_case_declared_data_product_names(use_case: dict[str, Any]) -> set[str]:
    data_products = use_case.get("dataProducts")
    if not isinstance(data_products, list):
        return set()
    return {
        item["name"]
        for item in data_products
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }


def load_topic_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in sorted((root / "contracts" / "topics").glob("*.yaml")):
        contract = load_yaml(path)
        topic_name = contract.get("topic", {}).get("name")
        if isinstance(topic_name, str):
            names.add(topic_name)
    return names
