from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_df.contracts import PRODUCT_CODE, ValidationResult, load_yaml


REQUIRED_ENVIRONMENTS = ("local", "staging", "prod")
VALID_TIERS = {"local", "staging", "prod"}
EXPECTED_EVIDENCE_MODES = {
    "local": "developer_feedback",
    "staging": "production_like_preflight",
    "prod": "production_signoff",
}
REQUIRED_P0_SERVICES = {
    "event_backbone",
    "outbox_relay",
    "cdc",
    "schema_registry",
    "object_storage",
    "table_format",
    "batch_processing",
    "sql_transform",
    "orchestration",
    "data_quality",
    "lakehouse_sql",
    "observability",
}


def validate_environment_manifests(root: Path) -> ValidationResult:
    result = ValidationResult()
    base = root / "platform" / "environments"
    if not base.is_dir():
        result.error(base, "platform/environments directory is required")
        return result

    for environment in REQUIRED_ENVIRONMENTS:
        manifest_path = base / environment / "manifest.yaml"
        if not manifest_path.is_file():
            result.error(manifest_path, "environment manifest is required")
            continue
        result.checked_count += 1
        validate_environment_manifest(manifest_path, load_yaml(manifest_path), environment, result)
    return result


def validate_environment_manifest(
    path: Path,
    manifest: dict[str, Any],
    expected_environment: str,
    result: ValidationResult,
) -> None:
    require_int(path, result, manifest, "version", minimum=1)
    environment = require_string(path, result, manifest, "environment")
    if environment and environment != expected_environment:
        result.error(path, f"environment must match folder name {expected_environment!r}")
    tier = require_string(path, result, manifest, "tier")
    if tier and tier not in VALID_TIERS:
        result.error(path, f"tier must be one of {sorted(VALID_TIERS)}")
    if environment and tier and environment != tier:
        result.error(path, "environment and tier must match for local, staging and prod manifests")
    owner = require_string(path, result, manifest, "owner")
    if owner and not PRODUCT_CODE.fullmatch(owner):
        result.error(path, "owner must be a platform team code like data-platform-team")
    evidence_mode = require_string(path, result, manifest, "evidenceMode")
    expected_mode = EXPECTED_EVIDENCE_MODES.get(expected_environment)
    if evidence_mode and expected_mode and evidence_mode != expected_mode:
        result.error(path, f"evidenceMode must be {expected_mode!r} for {expected_environment}")
    require_string(path, result, manifest, "runtimeReadiness")
    require_string(path, result, manifest, "description")
    validate_controls(path, manifest.get("controls"), result, expected_environment)
    validate_runtime_services(path, manifest.get("runtimeServices"), result)


def validate_controls(path: Path, controls: object, result: ValidationResult, environment: str) -> None:
    if not isinstance(controls, dict):
        result.error(path, "controls must be an object")
        return
    for key in ("serviceIdentity", "secrets", "storageEncryption", "networkExposure", "piiPolicy"):
        require_string(path, result, controls, key, prefix="controls")
    if environment in {"staging", "prod"}:
        if controls.get("secrets") == "generated_test_values":
            result.error(path, "staging/prod controls.secrets must not use generated test values")
        if controls.get("storageEncryption") != "required":
            result.error(path, "staging/prod controls.storageEncryption must be required")


def validate_runtime_services(path: Path, services: object, result: ValidationResult) -> None:
    if not isinstance(services, list) or not services:
        result.error(path, "runtimeServices must be a non-empty list")
        return

    seen: set[str] = set()
    for index, service in enumerate(services):
        prefix = f"runtimeServices[{index}]"
        if not isinstance(service, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        service_id = require_string(path, result, service, "serviceId", prefix=prefix)
        if service_id:
            if service_id in seen:
                result.error(path, f"{prefix}.serviceId duplicates service {service_id}")
            seen.add(service_id)
        for key in ("capability", "technology", "phase", "implementationStatus", "evidence"):
            require_string(path, result, service, key, prefix=prefix)
        required = service.get("required")
        if not isinstance(required, bool):
            result.error(path, f"{prefix}.required must be a boolean")
        if service_id in REQUIRED_P0_SERVICES:
            if required is not True:
                result.error(path, f"{prefix}.required must be true for P0 runtime service {service_id}")
            phase = service.get("phase")
            if not (isinstance(phase, str) and phase.startswith("P0")):
                result.error(path, f"{prefix}.phase must start with P0 for required runtime service {service_id}")

    missing_services = sorted(REQUIRED_P0_SERVICES - seen)
    if missing_services:
        result.error(path, f"runtimeServices missing required P0 services: {', '.join(missing_services)}")


def require_int(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    *,
    minimum: int,
) -> int | None:
    value = mapping.get(key)
    if not isinstance(value, int):
        result.error(path, f"{key} must be an integer")
        return None
    if value < minimum:
        result.error(path, f"{key} must be >= {minimum}")
    return value


def require_string(
    path: Path,
    result: ValidationResult,
    mapping: dict[str, Any],
    key: str,
    *,
    prefix: str | None = None,
) -> str | None:
    value = mapping.get(key)
    field = f"{prefix}.{key}" if prefix else key
    if not isinstance(value, str) or not value.strip():
        result.error(path, f"{field} must be a non-empty string")
        return None
    return value
