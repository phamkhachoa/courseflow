from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from enterprise_dp.access_governance import load_access_persona_ids
from enterprise_dp.contracts import (
    DATA_PRODUCT_NAME,
    PRODUCT_CODE,
    ValidationResult,
    load_yaml,
    require_int,
    require_mapping,
    require_string,
    require_string_list,
)
from enterprise_dp.products import load_enterprise_domain_codes


METRIC_ID = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_METRIC_STATUSES = {"draft", "provisional", "certified", "deprecated"}
VALID_CALCULATION_TYPES = {"aggregate_sql"}
VALID_FILTER_OPERATORS = {"equals", "in", "not_in", "gt", "gte", "lt", "lte"}
VALID_MATERIALIZATIONS = {"virtual", "materialized", "hot_mart"}


def validate_semantic_metric_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = root / "platform" / "serving" / "semantic-metrics.yaml"
    if not registry_path.is_file():
        result.error(registry_path, "platform/serving/semantic-metrics.yaml is required")
        return result

    registry = load_yaml(registry_path)
    result.checked_count += 1
    require_int(registry_path, result, registry, "version", minimum=1)
    require_string(registry_path, result, registry, "registryScope")
    require_string(registry_path, result, registry, "owner")
    require_string(registry_path, result, registry, "description")
    metrics = registry.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        result.error(registry_path, "metrics must be a non-empty list")
        return result

    context = validation_context(root)
    seen: set[str] = set()
    for index, metric in enumerate(metrics):
        result.checked_count += 1
        validate_metric_entry(registry_path, metric, index, seen, context, result)
    return result


def validation_context(root: Path) -> dict[str, Any]:
    return {
        "domains": load_enterprise_domain_codes(root),
        "data_products": load_data_product_contracts(root),
        "use_cases": load_use_case_ids(root),
        "personas": load_access_persona_ids(root),
    }


def validate_metric_entry(
    path: Path,
    metric: object,
    index: int,
    seen: set[str],
    context: dict[str, Any],
    result: ValidationResult,
) -> None:
    prefix = f"metrics[{index}]"
    if not isinstance(metric, dict):
        result.error(path, f"{prefix} must be an object")
        return

    metric_id = require_string(path, result, metric, "metricId", prefix)
    if metric_id:
        if not METRIC_ID.fullmatch(metric_id):
            result.error(path, f"{prefix}.metricId must be snake_case")
        if metric_id in seen:
            result.error(path, f"{prefix}.metricId duplicates metric {metric_id}")
        seen.add(metric_id)
    for key in ("name", "owner"):
        require_string(path, result, metric, key, prefix)
    domain = require_string(path, result, metric, "domain", prefix)
    if domain and domain not in context["domains"]:
        result.error(path, f"{prefix}.domain must be listed in domains/registry.yaml")
    status = require_string(path, result, metric, "status", prefix)
    if status and status not in VALID_METRIC_STATUSES:
        result.error(path, f"{prefix}.status must be one of {sorted(VALID_METRIC_STATUSES)}")

    source = require_mapping(path, result, metric, "source")
    calculation = require_mapping(path, result, metric, "calculation")
    serving = require_mapping(path, result, metric, "serving")
    grain = require_string_list(path, result, metric, "grain", prefix) or []
    dimensions = require_string_list(path, result, metric, "dimensions", prefix) or []
    use_cases = require_string_list(path, result, metric, "useCases", prefix) or []
    consumers = require_string_list(path, result, metric, "consumers", prefix) or []
    require_int(path, result, metric, "freshnessSloMinutes", minimum=1, prefix=prefix)
    if not all([source, calculation, serving]):
        return

    data_product_name = validate_source(path, source, prefix, context, result)
    columns = context["data_products"].get(data_product_name, {}).get("columns", set()) if data_product_name else set()
    validate_columns_exist(path, result, prefix, "grain", grain, columns)
    validate_columns_exist(path, result, prefix, "dimensions", dimensions, columns)
    validate_calculation(path, calculation, prefix, columns, result)
    validate_filters(path, metric.get("filters"), prefix, columns, result)
    validate_use_cases(path, use_cases, prefix, context["use_cases"], result)
    validate_consumers(path, consumers, prefix, context["personas"], result)
    validate_serving(path, serving, prefix, metric_id, result)


def validate_source(
    path: Path,
    source: dict[str, Any],
    prefix: str,
    context: dict[str, Any],
    result: ValidationResult,
) -> str | None:
    data_product = require_string(path, result, source, "dataProduct", f"{prefix}.source")
    if data_product:
        if not DATA_PRODUCT_NAME.fullmatch(data_product):
            result.error(path, f"{prefix}.source.dataProduct must be a data product name")
        elif data_product not in context["data_products"]:
            result.error(path, f"{prefix}.source.dataProduct contract does not exist: {data_product}")
        else:
            product_contract = context["data_products"][data_product]
            if product_contract["layer"] != "GOLD":
                result.error(path, f"{prefix}.source.dataProduct must be a GOLD data product")
    time_column = require_string(path, result, source, "timeColumn", f"{prefix}.source")
    if data_product in context["data_products"] and time_column:
        columns = context["data_products"][data_product]["columns"]
        if time_column not in columns:
            result.error(path, f"{prefix}.source.timeColumn must exist in {data_product}")
    return data_product


def validate_calculation(
    path: Path,
    calculation: dict[str, Any],
    prefix: str,
    columns: set[str],
    result: ValidationResult,
) -> None:
    calculation_type = require_string(path, result, calculation, "type", f"{prefix}.calculation")
    if calculation_type and calculation_type not in VALID_CALCULATION_TYPES:
        result.error(path, f"{prefix}.calculation.type must be one of {sorted(VALID_CALCULATION_TYPES)}")
    expression = require_string(path, result, calculation, "expressionSql", f"{prefix}.calculation")
    referenced_columns = require_string_list(path, result, calculation, "referencedColumns", f"{prefix}.calculation") or []
    require_string(path, result, calculation, "unit", f"{prefix}.calculation")
    validate_columns_exist(path, result, prefix, "calculation.referencedColumns", referenced_columns, columns)
    if expression:
        missing_from_expression = [
            column
            for column in referenced_columns
            if not re.search(rf"\b{re.escape(column)}\b", expression)
        ]
        if missing_from_expression:
            result.error(path, f"{prefix}.calculation.expressionSql does not mention referenced columns: {', '.join(missing_from_expression)}")


def validate_filters(path: Path, filters: object, prefix: str, columns: set[str], result: ValidationResult) -> None:
    if filters is None:
        return
    if not isinstance(filters, list):
        result.error(path, f"{prefix}.filters must be a list")
        return
    for index, item in enumerate(filters):
        item_prefix = f"{prefix}.filters[{index}]"
        if not isinstance(item, dict):
            result.error(path, f"{item_prefix} must be an object")
            continue
        column = require_string(path, result, item, "column", item_prefix)
        if column and column not in columns:
            result.error(path, f"{item_prefix}.column must exist in source data product")
        operator = require_string(path, result, item, "operator", item_prefix)
        if operator and operator not in VALID_FILTER_OPERATORS:
            result.error(path, f"{item_prefix}.operator must be one of {sorted(VALID_FILTER_OPERATORS)}")
        require_string_list(path, result, item, "values", item_prefix)


def validate_use_cases(path: Path, use_cases: list[str], prefix: str, registered_use_cases: set[str], result: ValidationResult) -> None:
    for use_case_id in use_cases:
        if use_case_id not in registered_use_cases:
            result.error(path, f"{prefix}.useCases contains unknown use case {use_case_id!r}")


def validate_consumers(path: Path, consumers: list[str], prefix: str, personas: set[str], result: ValidationResult) -> None:
    for consumer in consumers:
        if consumer not in personas:
            result.error(path, f"{prefix}.consumers references unknown persona {consumer!r}")


def validate_serving(path: Path, serving: dict[str, Any], prefix: str, metric_id: str | None, result: ValidationResult) -> None:
    trino_view = require_string(path, result, serving, "trinoView", f"{prefix}.serving")
    dremio_dataset = require_string(path, result, serving, "dremioVirtualDataset", f"{prefix}.serving")
    materialization = require_string(path, result, serving, "materialization", f"{prefix}.serving")
    if materialization and materialization not in VALID_MATERIALIZATIONS:
        result.error(path, f"{prefix}.serving.materialization must be one of {sorted(VALID_MATERIALIZATIONS)}")
    if metric_id:
        expected_suffix = f".{metric_id}"
        if trino_view and not trino_view.endswith(expected_suffix):
            result.error(path, f"{prefix}.serving.trinoView must end with {expected_suffix}")
        if dremio_dataset and not dremio_dataset.endswith(expected_suffix):
            result.error(path, f"{prefix}.serving.dremioVirtualDataset must end with {expected_suffix}")


def validate_columns_exist(
    path: Path,
    result: ValidationResult,
    prefix: str,
    field: str,
    column_names: list[str],
    columns: set[str],
) -> None:
    for column in column_names:
        if column not in columns:
            result.error(path, f"{prefix}.{field} references unknown source column {column!r}")


def load_data_product_contracts(root: Path) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "contracts" / "data-products").glob("*.yaml")):
        contract = load_yaml(path)
        product = contract.get("dataProduct")
        schema = contract.get("schema")
        if not isinstance(product, dict) or not isinstance(schema, dict):
            continue
        name = product.get("name")
        if not isinstance(name, str):
            continue
        columns = schema.get("columns")
        contracts[name] = {
            "layer": product.get("layer"),
            "columns": {
                column["name"]
                for column in columns
                if isinstance(column, dict) and isinstance(column.get("name"), str)
            },
        }
    return contracts


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
