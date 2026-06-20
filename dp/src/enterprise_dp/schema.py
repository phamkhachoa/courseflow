from __future__ import annotations

from datetime import datetime
import re
from typing import Any
from uuid import UUID


def validate_json_schema(instance: Any, schema: dict[str, Any], *, path: str = "$") -> tuple[str, ...]:
    errors: list[str] = []
    _validate(instance, schema, path, errors)
    return tuple(errors)


def _validate(instance: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    if "anyOf" in schema:
        branches = schema["anyOf"]
        if isinstance(branches, list):
            branch_results: list[list[str]] = []
            for branch in branches:
                if not isinstance(branch, dict):
                    continue
                branch_errors: list[str] = []
                _validate(instance, branch, path, branch_errors)
                branch_results.append(branch_errors)
            if branch_results and not any(not branch_errors for branch_errors in branch_results):
                errors.append(f"{path} does not match any allowed schema branch")

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(instance, expected_type):
        errors.append(f"{path} must be {_format_type(expected_type)}")
        return

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and instance not in enum_values:
        errors.append(f"{path} must be one of {enum_values!r}")

    if isinstance(instance, str):
        _validate_string(instance, schema, path, errors)
    elif _is_number(instance):
        _validate_number(instance, schema, path, errors)

    if isinstance(instance, dict):
        _validate_object(instance, schema, path, errors)


def _validate_object(
    instance: dict[str, Any],
    schema: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    required = schema.get("required")
    if isinstance(required, list):
        for field in required:
            if isinstance(field, str) and field not in instance:
                errors.append(f"{path}.{field} is required")

    max_properties = schema.get("maxProperties")
    if isinstance(max_properties, int) and len(instance) > max_properties:
        errors.append(f"{path} must have at most {max_properties} properties")

    properties = schema.get("properties")
    known_properties = properties if isinstance(properties, dict) else {}
    for field, field_schema in known_properties.items():
        if field in instance and isinstance(field_schema, dict):
            _validate(instance[field], field_schema, f"{path}.{field}", errors)

    additional = schema.get("additionalProperties", True)
    extra_fields = sorted(set(instance) - set(known_properties))
    if additional is False and extra_fields:
        errors.append(f"{path} has unexpected properties: {', '.join(extra_fields)}")
    elif isinstance(additional, dict):
        for field in extra_fields:
            _validate(instance[field], additional, f"{path}.{field}", errors)


def _validate_string(instance: str, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    min_length = schema.get("minLength")
    if isinstance(min_length, int) and len(instance) < min_length:
        errors.append(f"{path} length must be >= {min_length}")
    max_length = schema.get("maxLength")
    if isinstance(max_length, int) and len(instance) > max_length:
        errors.append(f"{path} length must be <= {max_length}")
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and re.fullmatch(pattern, instance) is None:
        errors.append(f"{path} must match pattern {pattern!r}")

    string_format = schema.get("format")
    if string_format == "uuid":
        try:
            UUID(instance)
        except ValueError:
            errors.append(f"{path} must be a uuid")
    elif string_format == "date-time" and not _is_datetime(instance):
        errors.append(f"{path} must be an ISO-8601 date-time")


def _validate_number(instance: int | float, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    minimum = schema.get("minimum")
    if _is_number(minimum) and instance < minimum:
        errors.append(f"{path} must be >= {minimum}")
    maximum = schema.get("maximum")
    if _is_number(maximum) and instance > maximum:
        errors.append(f"{path} must be <= {maximum}")


def _matches_type(instance: Any, expected_type: object) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(instance, item) for item in expected_type)
    if expected_type == "object":
        return isinstance(instance, dict)
    if expected_type == "array":
        return isinstance(instance, list)
    if expected_type == "string":
        return isinstance(instance, str)
    if expected_type == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected_type == "number":
        return _is_number(instance)
    if expected_type == "boolean":
        return isinstance(instance, bool)
    if expected_type == "null":
        return instance is None
    return True


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_datetime(value: str) -> bool:
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return True


def _format_type(expected_type: object) -> str:
    if isinstance(expected_type, list):
        return " or ".join(str(item) for item in expected_type)
    return str(expected_type)
