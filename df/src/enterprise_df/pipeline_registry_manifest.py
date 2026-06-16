from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_df.contracts import (
    DATA_PRODUCT_NAME,
    PRODUCT_CODE,
    TOPIC_NAME,
    ValidationResult,
    load_yaml,
    require_int,
    require_mapping,
    require_string,
    require_string_list,
)
from enterprise_df.pipelines import PipelineSpec, default_pipeline_registry
from enterprise_df.products import load_enterprise_domain_codes


VALID_IMPLEMENTATION_STATUSES = {"planned", "active", "deprecated"}
VALID_INPUT_KINDS = {"raw_event_jsonl", "approved_bronze_jsonl", "data_product_snapshot", "semantic_metric_snapshot"}


def validate_pipeline_registry_manifest(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = root / "platform" / "orchestration" / "pipeline-registry.yaml"
    if not registry_path.is_file():
        result.error(registry_path, "platform/orchestration/pipeline-registry.yaml is required")
        return result

    registry = load_yaml(registry_path)
    result.checked_count += 1
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registryScope")
    require_string(registry_path, result, registry, "owner")
    require_string(registry_path, result, registry, "description")
    runners = registry.get("runners")
    if not isinstance(runners, list) or not runners:
        result.error(registry_path, "runners must be a non-empty list")
        return result

    context = validation_context(root)
    implemented_specs = {
        spec.runner_id: spec for spec in default_pipeline_registry().list_specs()
    }
    manifest_runner_ids: set[str] = set()
    active_runner_ids: set[str] = set()
    for index, runner in enumerate(runners):
        result.checked_count += 1
        runner_id, status = validate_runner_entry(
            root,
            registry_path,
            runner,
            index,
            manifest_runner_ids,
            context,
            implemented_specs,
            result,
        )
        if runner_id and status == "active":
            active_runner_ids.add(runner_id)

    missing_active = sorted(set(implemented_specs) - active_runner_ids)
    for runner_id in missing_active:
        result.error(registry_path, f"implemented runner missing active manifest entry: {runner_id}")
    return result


def validation_context(root: Path) -> dict[str, Any]:
    return {
        "products": load_product_codes(root),
        "domains": load_enterprise_domain_codes(root),
        "topics": load_topic_names(root),
        "data_products": load_data_product_names(root),
        "use_cases": load_use_case_ids(root),
    }


def validate_runner_entry(
    root: Path,
    registry_path: Path,
    runner: object,
    index: int,
    seen: set[str],
    context: dict[str, Any],
    implemented_specs: dict[str, PipelineSpec],
    result: ValidationResult,
) -> tuple[str | None, str | None]:
    prefix = f"runners[{index}]"
    if not isinstance(runner, dict):
        result.error(registry_path, f"{prefix} must be an object")
        return None, None

    runner_id = require_string(registry_path, result, runner, "runnerId", prefix)
    if runner_id:
        if runner_id in seen:
            result.error(registry_path, f"{prefix}.runnerId duplicates runner {runner_id}")
        seen.add(runner_id)
    status = require_string(registry_path, result, runner, "implementationStatus", prefix)
    if status and status not in VALID_IMPLEMENTATION_STATUSES:
        result.error(registry_path, f"{prefix}.implementationStatus must be one of {sorted(VALID_IMPLEMENTATION_STATUSES)}")
    require_string(registry_path, result, runner, "name", prefix)
    require_string(registry_path, result, runner, "description", prefix)
    product = require_string(registry_path, result, runner, "product", prefix)
    if product:
        if not PRODUCT_CODE.fullmatch(product):
            result.error(registry_path, f"{prefix}.product must be a product code like example-product")
        elif product not in context["products"]:
            result.error(registry_path, f"{prefix}.product must have products/{product}/onboarding.yaml")
    domain = require_string(registry_path, result, runner, "domain", prefix)
    if domain and domain not in context["domains"]:
        result.error(registry_path, f"{prefix}.domain must be listed in domains/registry.yaml")
    input_kind = require_string(registry_path, result, runner, "inputKind", prefix)
    if input_kind and input_kind not in VALID_INPUT_KINDS:
        result.error(registry_path, f"{prefix}.inputKind must be one of {sorted(VALID_INPUT_KINDS)}")

    use_cases = require_string_list(registry_path, result, runner, "useCases", prefix) or []
    for use_case_id in use_cases:
        if use_case_id not in context["use_cases"]:
            result.error(registry_path, f"{prefix}.useCases contains unknown use case {use_case_id!r}")

    input_topics = optional_string_list(registry_path, result, runner, "inputTopics", prefix)
    for topic_name in input_topics:
        if not TOPIC_NAME.fullmatch(topic_name):
            result.error(registry_path, f"{prefix}.inputTopics contains invalid topic name {topic_name!r}")
        elif topic_name not in context["topics"]:
            result.error(registry_path, f"{prefix}.inputTopics contains topic without a contract {topic_name!r}")

    input_data_products = optional_string_list(registry_path, result, runner, "inputDataProducts", prefix)
    validate_data_product_list(registry_path, result, prefix, "inputDataProducts", input_data_products, context["data_products"])
    output_data_products = require_string_list(registry_path, result, runner, "outputDataProducts", prefix) or []
    validate_data_product_list(registry_path, result, prefix, "outputDataProducts", output_data_products, context["data_products"])
    primary_output = require_string(registry_path, result, runner, "primaryOutput", prefix)
    if primary_output:
        if primary_output not in output_data_products:
            result.error(registry_path, f"{prefix}.primaryOutput must be included in outputDataProducts")
        validate_data_product_list(registry_path, result, prefix, "primaryOutput", [primary_output], context["data_products"])

    evidence_capabilities = require_string_list(registry_path, result, runner, "evidenceCapabilities", prefix) or []
    required_options = optional_string_list(registry_path, result, runner, "requiredOptions", prefix)
    optional_options = optional_string_list(registry_path, result, runner, "optionalOptions", prefix)
    execution = require_mapping(registry_path, result, runner, "execution")
    if execution:
        require_string(registry_path, result, execution, "module", f"{prefix}.execution")
        require_string(registry_path, result, execution, "class", f"{prefix}.execution")

    if runner_id and status == "active":
        spec = implemented_specs.get(runner_id)
        if spec is None:
            result.error(registry_path, f"{prefix}.runnerId is active but no Python runner is registered: {runner_id}")
        else:
            validate_against_implemented_spec(
                registry_path,
                result,
                prefix,
                runner,
                spec,
                input_topics=input_topics,
                input_data_products=input_data_products,
                output_data_products=output_data_products,
                evidence_capabilities=evidence_capabilities,
                required_options=required_options,
                optional_options=optional_options,
            )
    return runner_id, status


def validate_against_implemented_spec(
    registry_path: Path,
    result: ValidationResult,
    prefix: str,
    runner: dict[str, Any],
    spec: PipelineSpec,
    *,
    input_topics: list[str],
    input_data_products: list[str],
    output_data_products: list[str],
    evidence_capabilities: list[str],
    required_options: list[str],
    optional_options: list[str],
) -> None:
    scalar_fields = {
        "name": spec.name,
        "description": spec.description,
        "product": spec.product,
        "domain": spec.domain,
        "inputKind": spec.input_kind,
        "primaryOutput": spec.primary_output,
    }
    for field, expected in scalar_fields.items():
        if runner.get(field) != expected:
            result.error(registry_path, f"{prefix}.{field} must match implemented runner value {expected!r}")
    list_fields = {
        "useCases": list(spec.use_cases),
        "inputTopics": list(spec.input_topics),
        "inputDataProducts": list(spec.input_data_products),
        "outputDataProducts": list(spec.output_data_products),
        "evidenceCapabilities": list(spec.evidence_capabilities),
        "requiredOptions": list(spec.required_options),
        "optionalOptions": list(spec.optional_options),
    }
    actual_lists = {
        "useCases": runner.get("useCases") if isinstance(runner.get("useCases"), list) else [],
        "inputTopics": input_topics,
        "inputDataProducts": input_data_products,
        "outputDataProducts": output_data_products,
        "evidenceCapabilities": evidence_capabilities,
        "requiredOptions": required_options,
        "optionalOptions": optional_options,
    }
    for field, expected in list_fields.items():
        if actual_lists[field] != expected:
            result.error(registry_path, f"{prefix}.{field} must match implemented runner value {expected!r}")


def validate_data_product_list(
    registry_path: Path,
    result: ValidationResult,
    prefix: str,
    field: str,
    data_products: list[str],
    registered_data_products: set[str],
) -> None:
    for data_product in data_products:
        if not DATA_PRODUCT_NAME.fullmatch(data_product):
            result.error(registry_path, f"{prefix}.{field} contains invalid data product name {data_product!r}")
        elif data_product not in registered_data_products:
            result.error(registry_path, f"{prefix}.{field} contains data product without a contract {data_product!r}")


def optional_string_list(path: Path, result: ValidationResult, mapping: dict[str, Any], key: str, prefix: str) -> list[str]:
    value = mapping.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        result.error(path, f"{prefix}.{key} must be a list")
        return []
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            result.error(path, f"{prefix}.{key}[{index}] must be a non-empty string")
            continue
        items.append(item)
    return items


def load_product_codes(root: Path) -> set[str]:
    product_codes: set[str] = set()
    for path in sorted((root / "products").glob("*/onboarding.yaml")):
        product = load_yaml(path).get("product")
        if isinstance(product, dict) and isinstance(product.get("code"), str):
            product_codes.add(product["code"])
    return product_codes


def load_topic_names(root: Path) -> set[str]:
    topic_names: set[str] = set()
    for path in sorted((root / "contracts" / "topics").glob("*.yaml")):
        topic = load_yaml(path).get("topic")
        if isinstance(topic, dict) and isinstance(topic.get("name"), str):
            topic_names.add(topic["name"])
    return topic_names


def load_data_product_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in sorted((root / "contracts" / "data-products").glob("*.yaml")):
        data_product = load_yaml(path).get("dataProduct")
        if isinstance(data_product, dict) and isinstance(data_product.get("name"), str):
            names.add(data_product["name"])
    return names


def load_use_case_ids(root: Path) -> set[str]:
    registry_path = root / "use-cases" / "registry.yaml"
    if not registry_path.is_file():
        return set()
    use_cases = load_yaml(registry_path).get("useCases")
    if not isinstance(use_cases, list):
        return set()
    return {
        use_case["id"]
        for use_case in use_cases
        if isinstance(use_case, dict) and isinstance(use_case.get("id"), str)
    }
