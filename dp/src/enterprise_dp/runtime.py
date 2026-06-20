from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from enterprise_dp.contracts import (
    PRODUCT_CODE,
    ValidationResult,
    load_yaml,
    require_bool,
    require_int,
    require_string,
    require_string_list,
)
from enterprise_dp.environments import REQUIRED_ENVIRONMENTS, REQUIRED_P0_SERVICES


SERVICE_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
MODULE_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
VALID_RUNTIME_ROLES = {"control_plane", "data_plane", "governance_plane", "ops_plane", "serving_plane"}
VALID_PROFILE_TYPES = {"docker_compose", "opentofu", "terraform", "kubernetes"}
VALID_PROFILE_STATES = {"runnable_skeleton", "skeleton_not_applied", "declared_not_applied", "planned", "applied"}
VALID_MODULE_STATES = {"skeleton", "candidate", "conditional_future", "planned", "applied"}
MODULE_BLOCK = re.compile(r'(?m)^\s*module\s+"([^"]+)"\s*\{')
MODULE_BLOCK_BODY = re.compile(r'(?ms)^\s*module\s+"([^"]+)"\s*\{(.*?)^\s*\}')
MODULE_SOURCE = re.compile(r'(?m)^\s*source\s*=\s*"([^"]+)"')
SHA256_REFERENCE = re.compile(r"^sha256:[0-9a-f]{64}$")
REPORT_VERSION = 1
EVIDENCE_ARTIFACT_TYPES = {
    "iac_plan": "runtime_iac_plan_evidence.v1",
    "iac_apply": "runtime_iac_apply_evidence.v1",
    "drift_report": "runtime_iac_drift_report.v1",
    "backup_report": "runtime_backup_evidence.v1",
    "dr_report": "runtime_dr_evidence.v1",
    "health_report": "runtime_service_health_evidence.v1",
}
EVIDENCE_KINDS = {
    "iac_plan": "iac_plan",
    "iac_apply": "iac_apply",
    "drift_report": "drift_check",
    "backup_report": "backup_restore",
    "dr_report": "dr_exercise",
    "health_report": "service_health",
}
VALID_EVIDENCE_STATUSES = {"passed", "failed", "blocked", "not_applicable"}
VALID_EVIDENCE_SOURCE_KINDS = {"ci_tool_output", "external_attestation", "synthetic_fixture"}


@dataclass(frozen=True)
class RuntimeEvidencePackResult:
    output_dir: Path
    manifest_path: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RuntimeReadinessReportResult:
    output_path: Path
    report: dict[str, Any]


def validate_runtime_topology(root: Path) -> ValidationResult:
    result = ValidationResult()
    base = root / "platform" / "runtime"
    topology_path = base / "topology.yaml"
    iac_path = base / "iac-modules.yaml"
    if not base.is_dir():
        result.error(base, "platform/runtime directory is required")
        return result
    if not topology_path.is_file():
        result.error(topology_path, "runtime topology manifest is required")
        return result
    if not iac_path.is_file():
        result.error(iac_path, "runtime IaC module registry is required")
        return result

    environment_context = load_environment_context(root, result)

    result.checked_count += 1
    topology = load_yaml(topology_path)
    topology_context = validate_topology(root, topology_path, topology, environment_context, result)

    result.checked_count += 1
    iac_registry = load_yaml(iac_path)
    validate_iac_registry(root, iac_path, iac_registry, topology_context, result)
    return result


def load_environment_context(root: Path, result: ValidationResult) -> dict[str, dict[str, Any]]:
    context: dict[str, dict[str, Any]] = {}
    for environment in REQUIRED_ENVIRONMENTS:
        manifest_path = root / "platform" / "environments" / environment / "manifest.yaml"
        if not manifest_path.is_file():
            result.error(manifest_path, "environment manifest is required before runtime topology validation")
            continue
        manifest = load_yaml(manifest_path)
        services = {
            str(service.get("serviceId")): service
            for service in manifest.get("runtimeServices", [])
            if isinstance(service, dict) and isinstance(service.get("serviceId"), str)
        }
        context[environment] = {
            "path": manifest_path,
            "manifest": manifest,
            "services": services,
        }
    return context


def validate_topology(
    root: Path,
    path: Path,
    topology: dict[str, Any],
    environment_context: dict[str, dict[str, Any]],
    result: ValidationResult,
) -> dict[str, Any]:
    require_int(path, result, topology, "version", minimum=1)
    owner = require_string(path, result, topology, "owner")
    if owner and not PRODUCT_CODE.fullmatch(owner):
        result.error(path, "owner must be a platform team code like data-platform-team")
    for key in ("platform", "scope", "topologyStatus", "readinessClaim"):
        require_string(path, result, topology, key)

    profiles_by_environment = validate_topology_environments(root, path, topology.get("environments"), environment_context, result)
    service_ids = validate_runtime_services(path, topology.get("runtimeServices"), environment_context, result)
    return {
        "service_ids": service_ids,
        "profiles_by_environment": profiles_by_environment,
    }


def validate_topology_environments(
    root: Path,
    path: Path,
    environments: object,
    environment_context: dict[str, dict[str, Any]],
    result: ValidationResult,
) -> dict[str, str]:
    if not isinstance(environments, list) or not environments:
        result.error(path, "environments must be a non-empty list")
        return {}

    seen: set[str] = set()
    profiles_by_environment: dict[str, str] = {}
    for index, entry in enumerate(environments):
        prefix = f"environments[{index}]"
        if not isinstance(entry, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        environment = require_string(path, result, entry, "environment", prefix)
        manifest = require_string(path, result, entry, "manifest", prefix)
        profile = require_string(path, result, entry, "iacProfile", prefix)
        require_string(path, result, entry, "deploymentMode", prefix)
        runtime_readiness = require_string(path, result, entry, "runtimeReadiness", prefix)
        evidence_mode = require_string(path, result, entry, "evidenceMode", prefix)
        if not environment:
            continue
        if environment not in REQUIRED_ENVIRONMENTS:
            result.error(path, f"{prefix}.environment must be one of {list(REQUIRED_ENVIRONMENTS)}")
            continue
        if environment in seen:
            result.error(path, f"{prefix}.environment duplicates {environment!r}")
        seen.add(environment)
        if profile:
            profiles_by_environment[environment] = profile
        context = environment_context.get(environment)
        if manifest:
            manifest_path = root / manifest
            if not manifest_path.is_file():
                result.error(path, f"{prefix}.manifest does not exist: {manifest}")
            expected = root / "platform" / "environments" / environment / "manifest.yaml"
            if manifest_path != expected:
                result.error(path, f"{prefix}.manifest must point to {expected.relative_to(root).as_posix()}")
        if context:
            environment_manifest = context["manifest"]
            if runtime_readiness and runtime_readiness != environment_manifest.get("runtimeReadiness"):
                result.error(path, f"{prefix}.runtimeReadiness must match environment manifest")
            if evidence_mode and evidence_mode != environment_manifest.get("evidenceMode"):
                result.error(path, f"{prefix}.evidenceMode must match environment manifest")

    missing = sorted(set(REQUIRED_ENVIRONMENTS) - seen)
    if missing:
        result.error(path, f"environments missing required environments: {', '.join(missing)}")
    return profiles_by_environment


def validate_runtime_services(
    path: Path,
    services: object,
    environment_context: dict[str, dict[str, Any]],
    result: ValidationResult,
) -> set[str]:
    if not isinstance(services, list) or not services:
        result.error(path, "runtimeServices must be a non-empty list")
        return set()

    seen: set[str] = set()
    for index, service in enumerate(services):
        prefix = f"runtimeServices[{index}]"
        if not isinstance(service, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        service_id = require_string(path, result, service, "serviceId", prefix)
        if not service_id:
            continue
        if not SERVICE_ID.fullmatch(service_id):
            result.error(path, f"{prefix}.serviceId must be snake_case")
        if service_id in seen:
            result.error(path, f"{prefix}.serviceId duplicates service {service_id!r}")
        seen.add(service_id)
        for key in (
            "capability",
            "technology",
            "phase",
            "runtimeRole",
            "iacModule",
            "haMode",
            "drTier",
            "dataClass",
            "networkZone",
            "identityMode",
            "secretsMode",
            "adoptionDecision",
        ):
            require_string(path, result, service, key, prefix)
        runtime_role = service.get("runtimeRole")
        if isinstance(runtime_role, str) and runtime_role not in VALID_RUNTIME_ROLES:
            result.error(path, f"{prefix}.runtimeRole must be one of {sorted(VALID_RUNTIME_ROLES)}")
        p0_required = require_bool(path, result, service, "p0Required", prefix)
        require_bool(path, result, service, "stateful", prefix)
        require_bool(path, result, service, "backupRequired", prefix)
        require_string_list(path, result, service, "evidenceKinds", prefix)
        validate_environment_overrides(path, service_id, service.get("environmentOverrides"), environment_context, prefix, result)
        if service_id in REQUIRED_P0_SERVICES:
            if p0_required is not True:
                result.error(path, f"{prefix}.p0Required must be true for P0 runtime service {service_id}")
            phase = service.get("phase")
            if not (isinstance(phase, str) and phase.startswith("P0")):
                result.error(path, f"{prefix}.phase must start with P0 for required runtime service {service_id}")
        validate_conditional_serving_decisions(path, service_id, service, prefix, result)

    missing = sorted(REQUIRED_P0_SERVICES - seen)
    if missing:
        result.error(path, f"runtimeServices missing required P0 services: {', '.join(missing)}")
    return seen


def validate_environment_overrides(
    path: Path,
    service_id: str,
    overrides: object,
    environment_context: dict[str, dict[str, Any]],
    prefix: str,
    result: ValidationResult,
) -> None:
    if not isinstance(overrides, dict):
        result.error(path, f"{prefix}.environmentOverrides must be an object")
        return
    for environment in REQUIRED_ENVIRONMENTS:
        override = overrides.get(environment)
        item_prefix = f"{prefix}.environmentOverrides.{environment}"
        if not isinstance(override, dict):
            result.error(path, f"{item_prefix} must be an object")
            continue
        for key in ("technology", "implementationStatus", "evidence"):
            require_string(path, result, override, key, item_prefix)
        manifest_service = environment_context.get(environment, {}).get("services", {}).get(service_id)
        if not manifest_service:
            result.error(path, f"{item_prefix} references service missing from {environment} environment manifest")
            continue
        for key in ("implementationStatus", "evidence"):
            if isinstance(override.get(key), str) and override[key] != manifest_service.get(key):
                result.error(path, f"{item_prefix}.{key} must match the {environment} environment manifest")


def validate_conditional_serving_decisions(
    path: Path,
    service_id: str,
    service: dict[str, Any],
    prefix: str,
    result: ValidationResult,
) -> None:
    technology = str(service.get("technology", ""))
    phase = str(service.get("phase", ""))
    decision = str(service.get("adoptionDecision", ""))
    p0_required = service.get("p0Required")
    if service_id == "semantic_lakehouse":
        if "Dremio" not in technology:
            result.error(path, f"{prefix}.technology must identify Dremio")
        if phase.startswith("P0") or p0_required is not False:
            result.error(path, f"{prefix} must keep Dremio outside the P0 required runtime")
        if "conditional" not in decision:
            result.error(path, f"{prefix}.adoptionDecision must be conditional for Dremio")
    if service_id == "distributed_htap":
        if "TiDB" not in technology:
            result.error(path, f"{prefix}.technology must identify TiDB")
        if not phase.startswith("P3") or p0_required is not False:
            result.error(path, f"{prefix} must keep TiDB as a conditional P3+ option")
        if "conditional" not in decision:
            result.error(path, f"{prefix}.adoptionDecision must be conditional for TiDB")


def validate_iac_registry(
    root: Path,
    path: Path,
    registry: dict[str, Any],
    topology_context: dict[str, Any],
    result: ValidationResult,
) -> None:
    require_int(path, result, registry, "version", minimum=1)
    owner = require_string(path, result, registry, "owner")
    if owner and not PRODUCT_CODE.fullmatch(owner):
        result.error(path, "owner must be a platform team code like data-platform-team")
    require_string(path, result, registry, "registryScope")

    profiles = validate_profiles(root, path, registry.get("profiles"), topology_context, result)
    modules = validate_modules(root, path, registry.get("modules"), topology_context.get("service_ids", set()), set(profiles), result)
    validate_iac_profile_module_coverage(root, path, profiles, modules, result)


def validate_profiles(
    root: Path,
    path: Path,
    profiles: object,
    topology_context: dict[str, Any],
    result: ValidationResult,
) -> dict[str, dict[str, Any]]:
    if not isinstance(profiles, list) or not profiles:
        result.error(path, "profiles must be a non-empty list")
        return {}

    seen: set[str] = set()
    profile_index: dict[str, dict[str, Any]] = {}
    profiles_by_environment: dict[str, str] = {}
    for index, profile in enumerate(profiles):
        prefix = f"profiles[{index}]"
        if not isinstance(profile, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        profile_id = require_string(path, result, profile, "profileId", prefix)
        environment = require_string(path, result, profile, "environment", prefix)
        profile_type = require_string(path, result, profile, "type", prefix)
        profile_path = require_string(path, result, profile, "path", prefix)
        state = require_string(path, result, profile, "state", prefix)
        require_string(path, result, profile, "readinessClaim", prefix)
        require_string_list(path, result, profile, "requiredEvidence", prefix)
        if profile_id:
            if not MODULE_ID.fullmatch(profile_id):
                result.error(path, f"{prefix}.profileId must be kebab-case")
            if profile_id in seen:
                result.error(path, f"{prefix}.profileId duplicates profile {profile_id!r}")
            seen.add(profile_id)
            profile_index[profile_id] = profile
        if environment:
            if environment not in REQUIRED_ENVIRONMENTS:
                result.error(path, f"{prefix}.environment must be one of {list(REQUIRED_ENVIRONMENTS)}")
            elif profile_id:
                profiles_by_environment[environment] = profile_id
        if profile_type and profile_type not in VALID_PROFILE_TYPES:
            result.error(path, f"{prefix}.type must be one of {sorted(VALID_PROFILE_TYPES)}")
        if state and state not in VALID_PROFILE_STATES:
            result.error(path, f"{prefix}.state must be one of {sorted(VALID_PROFILE_STATES)}")
        if profile_path and not (root / profile_path).is_file():
            result.error(path, f"{prefix}.path does not exist: {profile_path}")

    expected_profiles = topology_context.get("profiles_by_environment", {})
    for environment in REQUIRED_ENVIRONMENTS:
        if environment not in profiles_by_environment:
            result.error(path, f"profiles missing environment {environment!r}")
            continue
        expected = expected_profiles.get(environment)
        actual = profiles_by_environment[environment]
        if expected and actual != expected:
            result.error(path, f"profile for {environment} must match topology iacProfile {expected!r}")
    return profile_index


def validate_modules(
    root: Path,
    path: Path,
    modules: object,
    topology_service_ids: set[str],
    profile_ids: set[str],
    result: ValidationResult,
) -> list[dict[str, Any]]:
    if not isinstance(modules, list) or not modules:
        result.error(path, "modules must be a non-empty list")
        return []

    seen: set[str] = set()
    covered_services: set[str] = set()
    valid_modules: list[dict[str, Any]] = []
    for index, module in enumerate(modules):
        prefix = f"modules[{index}]"
        if not isinstance(module, dict):
            result.error(path, f"{prefix} must be an object")
            continue
        module_id = require_string(path, result, module, "moduleId", prefix)
        owner = require_string(path, result, module, "owner", prefix)
        state = require_string(path, result, module, "state", prefix)
        module_path = require_string(path, result, module, "path", prefix)
        service_ids = require_string_list(path, result, module, "serviceIds", prefix) or []
        module_profile_ids = require_string_list(path, result, module, "profileIds", prefix) or []
        require_string_list(path, result, module, "requiredControls", prefix)
        if module_id:
            if not MODULE_ID.fullmatch(module_id):
                result.error(path, f"{prefix}.moduleId must be kebab-case")
            if module_id in seen:
                result.error(path, f"{prefix}.moduleId duplicates module {module_id!r}")
            seen.add(module_id)
        if owner and not PRODUCT_CODE.fullmatch(owner):
            result.error(path, f"{prefix}.owner must be a team code like platform-engineering")
        if state and state not in VALID_MODULE_STATES:
            result.error(path, f"{prefix}.state must be one of {sorted(VALID_MODULE_STATES)}")
        if module_path and not (root / module_path).exists():
            result.error(path, f"{prefix}.path does not exist: {module_path}")
        for service_id in service_ids:
            if service_id not in topology_service_ids:
                result.error(path, f"{prefix}.serviceIds references unknown runtime service {service_id!r}")
            covered_services.add(service_id)
        for profile_id in module_profile_ids:
            if profile_id not in profile_ids:
                result.error(path, f"{prefix}.profileIds references unknown profile {profile_id!r}")
        valid_modules.append(module)

    missing_module_services = sorted(topology_service_ids - covered_services)
    if missing_module_services:
        result.error(path, f"modules missing runtime service coverage: {', '.join(missing_module_services)}")
    return valid_modules


def validate_iac_profile_module_coverage(
    root: Path,
    path: Path,
    profiles: dict[str, dict[str, Any]],
    modules: list[dict[str, Any]],
    result: ValidationResult,
) -> None:
    for profile_id, profile in profiles.items():
        profile_type = str(profile.get("type") or "")
        environment = str(profile.get("environment") or "")
        if profile_type not in {"opentofu", "terraform"} or environment == "local":
            continue
        profile_path = str(profile.get("path") or "")
        full_path = root / profile_path
        declared_labels = iac_profile_module_labels(full_path) if full_path.is_file() else set()
        declared_sources = iac_profile_module_sources(full_path) if full_path.is_file() else {}
        required_labels = required_iac_module_labels_for_profile(profile_id, modules)
        missing = sorted(required_labels - declared_labels)
        if missing:
            result.error(
                path,
                f"profile {profile_id!r} must declare OpenTofu/Terraform modules for P0 runtime services: {', '.join(missing)}",
            )
        for label in sorted(required_labels & declared_labels):
            source = declared_sources.get(label)
            if not source:
                result.error(path, f"profile {profile_id!r} module {label!r} must declare a source")
                continue
            if is_local_iac_module_source(source):
                source_path = (full_path.parent / source).resolve() if not Path(source).is_absolute() else Path(source)
                if not source_path.exists():
                    result.error(path, f"profile {profile_id!r} module {label!r} source does not exist: {source}")
                    continue
                try:
                    source_path.relative_to(root.resolve())
                except ValueError:
                    result.error(path, f"profile {profile_id!r} module {label!r} local source must stay under the dp root")


def iac_profile_module_labels(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return set(MODULE_BLOCK.findall(path.read_text(encoding="utf-8")))


def iac_profile_module_sources(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    sources: dict[str, str] = {}
    for label, body in MODULE_BLOCK_BODY.findall(path.read_text(encoding="utf-8")):
        match = MODULE_SOURCE.search(body)
        if match:
            sources[label] = match.group(1)
    return sources


def is_local_iac_module_source(source: str) -> bool:
    return source.startswith(("./", "../", "/"))


def required_iac_module_labels_for_profile(profile_id: str, modules: list[dict[str, Any]]) -> set[str]:
    labels: set[str] = set()
    for module in modules:
        profile_ids = module.get("profileIds")
        service_ids = module.get("serviceIds")
        module_id = module.get("moduleId")
        if (
            not isinstance(module_id, str)
            or not isinstance(profile_ids, list)
            or profile_id not in profile_ids
            or not isinstance(service_ids, list)
            or not any(service_id in REQUIRED_P0_SERVICES for service_id in service_ids if isinstance(service_id, str))
        ):
            continue
        labels.add(module_id.replace("-", "_"))
    return labels


def write_runtime_evidence_pack(
    root: str | Path,
    output_dir: str | Path,
    *,
    environment: str,
    source_kind: str,
    generated_at: str | None = None,
    valid_until: str | None = None,
    git_sha: str,
    ci_run_id: str,
    issuer_tool: str,
    issuer_tool_version: str,
    artifact_base_uri: str,
    change_request_id: str | None = None,
    include_dr: bool | None = None,
    plan_status: str = "succeeded",
    apply_status_value: str = "succeeded",
    drift_status_value: str = "clean",
    destructive_change_count: int = 0,
    drifted_resource_count: int = 0,
) -> RuntimeEvidencePackResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or utc_now()
    expires = valid_until or (parse_utc_time(generated) or datetime.now(UTC)).replace(microsecond=0).astimezone(UTC)
    if isinstance(expires, datetime):
        expires = (expires + timedelta(hours=24)).isoformat().replace("+00:00", "Z")

    topology_path = platform_root / "platform" / "runtime" / "topology.yaml"
    iac_path = platform_root / "platform" / "runtime" / "iac-modules.yaml"
    topology = load_yaml(topology_path)
    iac_registry = load_yaml(iac_path)
    env_entry = find_by_key(topology.get("environments", []), "environment", environment)
    if env_entry is None:
        raise ValueError(f"unknown runtime environment {environment!r}")
    profile = find_by_key(iac_registry.get("profiles", []), "profileId", env_entry.get("iacProfile"))
    if profile is None:
        raise ValueError(f"missing IaC profile for environment {environment!r}")
    if source_kind not in VALID_EVIDENCE_SOURCE_KINDS:
        raise ValueError(f"source_kind must be one of {sorted(VALID_EVIDENCE_SOURCE_KINDS)}")

    service_ids = sorted(REQUIRED_P0_SERVICES)
    stateful_services = sorted(
        str(service.get("serviceId"))
        for service in topology.get("runtimeServices", [])
        if (
            isinstance(service, dict)
            and service.get("serviceId") in REQUIRED_P0_SERVICES
            and service.get("stateful") is True
        )
    )
    profile_id = str(profile["profileId"])
    include_dr_report = environment == "prod" if include_dr is None else include_dr
    base = common_evidence_payload(
        environment=environment,
        profile_id=profile_id,
        source_kind=source_kind,
        generated_at=generated,
        valid_until=str(expires),
        git_sha=git_sha,
        ci_run_id=ci_run_id,
        issuer_tool=issuer_tool,
        issuer_tool_version=issuer_tool_version,
        artifact_base_uri=artifact_base_uri,
        change_request_id=change_request_id,
    )
    artifacts: dict[str, dict[str, Any]] = {
        "iac_plan": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["iac_plan"],
            "evidence_kind": EVIDENCE_KINDS["iac_plan"],
            "plan": {
                "status": plan_status,
                "plan_hash": stable_id("plan-hash", environment, git_sha, generated),
                "state_hash": stable_id("state-before", environment, git_sha, generated),
                "change_count": len(service_ids),
                "destructive_change_count": destructive_change_count,
                "replacement_count": 0,
            },
            "service_matrix": [
                {"service_id": service_id, "module_id": service_id.replace("_", "-"), "covered": True, "action": "update"}
                for service_id in service_ids
            ],
        },
        "iac_apply": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["iac_apply"],
            "evidence_kind": EVIDENCE_KINDS["iac_apply"],
            "apply": {
                "status": apply_status_value,
                "applied_plan_hash": stable_id("plan-hash", environment, git_sha, generated),
                "state_hash": stable_id("state-after", environment, git_sha, generated),
                "drift_status": drift_status_value,
            },
            "deployed_services": service_ids,
            "smoke_checks": [{"service_id": service_id, "status": "passed"} for service_id in service_ids],
        },
        "drift_report": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["drift_report"],
            "evidence_kind": EVIDENCE_KINDS["drift_report"],
            "drift": {"status": drift_status_value, "drifted_resource_count": drifted_resource_count},
            "service_matrix": [
                {"service_id": service_id, "module_id": service_id.replace("_", "-"), "covered": True}
                for service_id in service_ids
            ],
        },
        "backup_report": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["backup_report"],
            "evidence_kind": EVIDENCE_KINDS["backup_report"],
            "backups": [
                {"service_id": service_id, "status": "passed", "restore_tested": True}
                for service_id in stateful_services
            ],
        },
        "health_report": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["health_report"],
            "evidence_kind": EVIDENCE_KINDS["health_report"],
            "checks": [{"service_id": service_id, "status": "passed"} for service_id in service_ids],
        },
    }
    if include_dr_report:
        artifacts["dr_report"] = base | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["dr_report"],
            "evidence_kind": EVIDENCE_KINDS["dr_report"],
            "exercise": {"status": "passed", "rto_minutes": 60, "rpo_minutes": 15},
            "covered_services": service_ids,
        }

    artifact_paths: dict[str, Path] = {}
    for kind, artifact in artifacts.items():
        artifact = dict(artifact)
        artifact["evidence_id"] = stable_id(f"runtime-{kind}", environment, profile_id, generated, git_sha)
        filename = evidence_filename(kind)
        artifact["artifact_uri"] = f"{artifact_base_uri.rstrip('/')}/{filename}"
        artifact_path = target_dir / filename
        artifact_path.write_text(f"{canonical_json(artifact)}\n", encoding="utf-8")
        artifact_paths[kind] = artifact_path

    blockers = []
    if environment in {"staging", "prod"} and source_kind == "synthetic_fixture":
        blockers.append(
            {
                "blocker_id": "synthetic_fixture_not_production_evidence",
                "message": "Synthetic runtime evidence pack cannot be used for staging or production readiness.",
            }
        )
    if environment in {"staging", "prod"}:
        blockers.append(
            {
                "blocker_id": "normalized_iac_evidence_required",
                "message": "Staging and production signoff require runtime-evidence-normalize-iac artifacts bound to plan/state/health/backup source hashes.",
            }
        )

    manifest = {
        "artifact_type": "runtime_evidence_pack_manifest.v1",
        "manifest_version": 1,
        "manifest_id": stable_id("runtime-evidence-pack", environment, profile_id, generated, git_sha),
        "generated_at": generated,
        "environment": environment,
        "profile_id": profile_id,
        "source_kind": source_kind,
        "passed": not blockers,
        "blockers": blockers,
        "valid_until": str(expires),
        "topology_uri": topology_path.as_posix(),
        "topology_hash": hash_file(topology_path),
        "iac_registry_uri": iac_path.as_posix(),
        "iac_registry_hash": hash_file(iac_path),
        "required_p0_services": service_ids,
        "stateful_p0_services": stateful_services,
        "artifacts": {
            kind: {
                "path": path.as_posix(),
                "hash": hash_file(path),
                "artifact_type": artifacts[kind]["artifact_type"],
            }
            for kind, path in artifact_paths.items()
        },
        "readiness_args": readiness_args(environment, artifact_paths),
        "production_signoff_allowed": not blockers,
    }
    manifest_path = target_dir / "runtime-evidence-pack-manifest.json"
    manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return RuntimeEvidencePackResult(output_dir=target_dir, manifest_path=manifest_path, manifest=manifest)


def write_runtime_iac_evidence_pack(
    root: str | Path,
    output_dir: str | Path,
    *,
    environment: str,
    plan_json_path: str | Path,
    state_json_path: str | Path,
    health_checks_path: str | Path,
    backup_checks_path: str | Path,
    dr_exercise_path: str | Path | None = None,
    resource_map_path: str | Path | None = None,
    source_kind: str,
    generated_at: str | None = None,
    valid_until: str | None = None,
    git_sha: str,
    ci_run_id: str,
    issuer_tool: str,
    issuer_tool_version: str,
    artifact_base_uri: str,
    change_request_id: str | None = None,
) -> RuntimeEvidencePackResult:
    platform_root = Path(root)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or utc_now()
    expires = valid_until or (parse_utc_time(generated) or datetime.now(UTC)).replace(microsecond=0).astimezone(UTC)
    if isinstance(expires, datetime):
        expires = (expires + timedelta(hours=24)).isoformat().replace("+00:00", "Z")

    topology_path = platform_root / "platform" / "runtime" / "topology.yaml"
    iac_path = platform_root / "platform" / "runtime" / "iac-modules.yaml"
    topology = load_yaml(topology_path)
    iac_registry = load_yaml(iac_path)
    env_entry = find_by_key(topology.get("environments", []), "environment", environment)
    if env_entry is None:
        raise ValueError(f"unknown runtime environment {environment!r}")
    profile = find_by_key(iac_registry.get("profiles", []), "profileId", env_entry.get("iacProfile"))
    if profile is None:
        raise ValueError(f"missing IaC profile for environment {environment!r}")
    if source_kind not in {"ci_tool_output", "external_attestation"}:
        raise ValueError("runtime_iac_evidence_pack requires ci_tool_output or external_attestation source_kind")

    plan_path = resolve_input_path(platform_root, plan_json_path)
    state_path = resolve_input_path(platform_root, state_json_path)
    health_path = resolve_input_path(platform_root, health_checks_path)
    backup_path = resolve_input_path(platform_root, backup_checks_path)
    dr_path = resolve_input_path(platform_root, dr_exercise_path) if dr_exercise_path else None
    plan_json = load_json_object(plan_path, "plan_json")
    state_json = load_json_object(state_path, "state_json")
    health_json = load_json_object(health_path, "health_checks")
    backup_json = load_json_object(backup_path, "backup_checks")
    dr_json = load_json_object(dr_path, "dr_exercise") if dr_path else None

    required_services = sorted(REQUIRED_P0_SERVICES)
    stateful_services = sorted(
        str(service.get("serviceId"))
        for service in topology.get("runtimeServices", [])
        if (
            isinstance(service, dict)
            and service.get("serviceId") in REQUIRED_P0_SERVICES
            and service.get("stateful") is True
        )
    )
    mappings = runtime_resource_mappings(iac_registry, resource_map_path=resolve_input_path(platform_root, resource_map_path) if resource_map_path else None)
    plan_matrix, plan_summary = normalize_plan_resource_changes(plan_json, mappings, required_services)
    deployed_services = sorted(
        service_id
        for service_id in required_services
        if service_id in services_from_state(state_json, mappings)
    )
    drift_matrix, drift_summary = normalize_drift(plan_json, mappings, required_services)
    profile_id = str(profile["profileId"])
    base = common_evidence_payload(
        environment=environment,
        profile_id=profile_id,
        source_kind=source_kind,
        generated_at=generated,
        valid_until=str(expires),
        git_sha=git_sha,
        ci_run_id=ci_run_id,
        issuer_tool=issuer_tool,
        issuer_tool_version=issuer_tool_version,
        artifact_base_uri=artifact_base_uri,
        change_request_id=change_request_id,
        command="enterprise-dp runtime-evidence-normalize-iac",
    )
    plan_hash = f"sha256:{hash_file(plan_path)}"
    state_hash = f"sha256:{hash_file(state_path)}"
    artifacts: dict[str, dict[str, Any]] = {
        "iac_plan": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["iac_plan"],
            "evidence_kind": EVIDENCE_KINDS["iac_plan"],
            "artifact_sha256": plan_hash,
            "source_artifact_uri": plan_path.as_posix(),
            "source_artifact_hash": plan_hash,
            "plan": {
                "status": "succeeded",
                "plan_hash": plan_hash,
                "state_hash": state_hash,
                "change_count": plan_summary["change_count"],
                "destructive_change_count": plan_summary["destructive_change_count"],
                "replacement_count": plan_summary["replacement_count"],
            },
            "service_matrix": plan_matrix,
        },
        "iac_apply": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["iac_apply"],
            "evidence_kind": EVIDENCE_KINDS["iac_apply"],
            "artifact_sha256": state_hash,
            "source_artifact_uri": state_path.as_posix(),
            "source_artifact_hash": state_hash,
            "apply": {
                "status": "succeeded",
                "applied_plan_hash": plan_hash,
                "state_hash": state_hash,
                "drift_status": drift_summary["status"],
            },
            "deployed_services": deployed_services,
            "smoke_checks": health_json.get("checks", []),
        },
        "drift_report": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["drift_report"],
            "evidence_kind": EVIDENCE_KINDS["drift_report"],
            "artifact_sha256": plan_hash,
            "source_artifact_uri": plan_path.as_posix(),
            "source_artifact_hash": plan_hash,
            "drift": {"status": drift_summary["status"], "drifted_resource_count": drift_summary["drifted_resource_count"]},
            "service_matrix": drift_matrix,
        },
        "backup_report": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["backup_report"],
            "evidence_kind": EVIDENCE_KINDS["backup_report"],
            "artifact_sha256": f"sha256:{hash_file(backup_path)}",
            "source_artifact_uri": backup_path.as_posix(),
            "source_artifact_hash": f"sha256:{hash_file(backup_path)}",
            "backups": backup_json.get("backups", []),
        },
        "health_report": base
        | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["health_report"],
            "evidence_kind": EVIDENCE_KINDS["health_report"],
            "artifact_sha256": f"sha256:{hash_file(health_path)}",
            "source_artifact_uri": health_path.as_posix(),
            "source_artifact_hash": f"sha256:{hash_file(health_path)}",
            "checks": health_json.get("checks", []),
        },
    }
    if dr_json is not None:
        artifacts["dr_report"] = base | {
            "artifact_type": EVIDENCE_ARTIFACT_TYPES["dr_report"],
            "evidence_kind": EVIDENCE_KINDS["dr_report"],
            "artifact_sha256": f"sha256:{hash_file(dr_path)}" if dr_path else None,
            "source_artifact_uri": dr_path.as_posix() if dr_path else None,
            "source_artifact_hash": f"sha256:{hash_file(dr_path)}" if dr_path else None,
            "exercise": dr_json.get("exercise", {}),
            "covered_services": dr_json.get("covered_services", []),
        }

    artifact_paths: dict[str, Path] = {}
    for kind, artifact in artifacts.items():
        artifact = dict(artifact)
        artifact["evidence_id"] = stable_id(f"runtime-normalized-{kind}", environment, profile_id, generated, git_sha)
        filename = evidence_filename(kind)
        artifact["artifact_uri"] = f"{artifact_base_uri.rstrip('/')}/{filename}"
        artifact_path = target_dir / filename
        artifact_path.write_text(f"{canonical_json(artifact)}\n", encoding="utf-8")
        artifact_paths[kind] = artifact_path

    manifest = {
        "artifact_type": "runtime_iac_normalized_evidence_pack_manifest.v1",
        "manifest_version": 1,
        "manifest_id": stable_id("runtime-iac-normalized-evidence-pack", environment, profile_id, generated, git_sha),
        "generated_at": generated,
        "environment": environment,
        "profile_id": profile_id,
        "source_kind": source_kind,
        "passed": True,
        "blockers": [],
        "valid_until": str(expires),
        "topology_uri": topology_path.as_posix(),
        "topology_hash": hash_file(topology_path),
        "iac_registry_uri": iac_path.as_posix(),
        "iac_registry_hash": hash_file(iac_path),
        "source_inputs": {
            "plan_json": {"path": plan_path.as_posix(), "hash": hash_file(plan_path)},
            "state_json": {"path": state_path.as_posix(), "hash": hash_file(state_path)},
            "health_checks": {"path": health_path.as_posix(), "hash": hash_file(health_path)},
            "backup_checks": {"path": backup_path.as_posix(), "hash": hash_file(backup_path)},
            "dr_exercise": {"path": dr_path.as_posix(), "hash": hash_file(dr_path)} if dr_path else None,
            "resource_map": {"path": resolve_input_path(platform_root, resource_map_path).as_posix(), "hash": hash_file(resolve_input_path(platform_root, resource_map_path))} if resource_map_path else None,
        },
        "required_p0_services": required_services,
        "stateful_p0_services": stateful_services,
        "plan_summary": plan_summary,
        "drift_summary": drift_summary,
        "deployed_services": deployed_services,
        "artifacts": {
            kind: {
                "path": path.as_posix(),
                "hash": hash_file(path),
                "artifact_type": artifacts[kind]["artifact_type"],
            }
            for kind, path in artifact_paths.items()
        },
        "readiness_args": readiness_args(environment, artifact_paths),
        "production_signoff_allowed": source_kind != "synthetic_fixture",
    }
    manifest_path = target_dir / "runtime-evidence-pack-manifest.json"
    manifest_path.write_text(f"{canonical_json(manifest)}\n", encoding="utf-8")
    return RuntimeEvidencePackResult(output_dir=target_dir, manifest_path=manifest_path, manifest=manifest)


def common_evidence_payload(
    *,
    environment: str,
    profile_id: str,
    source_kind: str,
    generated_at: str,
    valid_until: str,
    git_sha: str,
    ci_run_id: str,
    issuer_tool: str,
    issuer_tool_version: str,
    artifact_base_uri: str,
    change_request_id: str | None,
    command: str = "enterprise-dp runtime-evidence-pack",
) -> dict[str, Any]:
    is_sample = source_kind == "synthetic_fixture"
    is_production_like = environment in {"staging", "prod"}
    payload: dict[str, Any] = {
        "schema_version": 1,
        "environment": environment,
        "profile_id": profile_id,
        "source_kind": source_kind,
        "sample": is_sample,
        "production_evidence": not is_sample,
        "readiness_claim": (
            "sample_contract_only_not_production_evidence"
            if is_sample and is_production_like
            else "machine_readable_runtime_evidence"
        ),
        "status": "blocked" if is_sample and is_production_like else "passed",
        "generated_at": generated_at,
        "valid_until": valid_until,
        "issuer": {"tool": issuer_tool, "tool_version": issuer_tool_version, "ci_run_id": ci_run_id},
        "git_sha": git_sha,
        "artifact_uri": artifact_base_uri.rstrip("/"),
        "artifact_sha256": "sha256:normalized-runtime-evidence",
        "command": command,
        "exit_code": 0,
        "redacted": True,
    }
    if change_request_id:
        payload["change_request_id"] = change_request_id
    return payload


def evidence_filename(kind: str) -> str:
    return {
        "iac_plan": "runtime-iac-plan.json",
        "iac_apply": "runtime-iac-apply.json",
        "drift_report": "runtime-drift-report.json",
        "backup_report": "runtime-backup-report.json",
        "dr_report": "runtime-dr-report.json",
        "health_report": "runtime-health-report.json",
    }[kind]


def readiness_args(environment: str, artifact_paths: dict[str, Path]) -> list[str]:
    args = [
        "runtime-readiness-check",
        "--environment",
        environment,
    ]
    option_by_kind = {
        "iac_plan": "--iac-plan",
        "iac_apply": "--iac-apply",
        "drift_report": "--drift-report",
        "backup_report": "--backup-report",
        "dr_report": "--dr-report",
        "health_report": "--health-report",
    }
    for kind in ("iac_plan", "iac_apply", "drift_report", "backup_report", "dr_report", "health_report"):
        if kind in artifact_paths:
            args.extend([option_by_kind[kind], artifact_paths[kind].as_posix()])
    return args


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"{label} file does not exist: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def runtime_resource_mappings(iac_registry: dict[str, Any], *, resource_map_path: Path | None = None) -> list[dict[str, str]]:
    mappings: list[dict[str, str]] = []
    if resource_map_path is not None:
        registry = load_yaml(resource_map_path)
        entries = registry.get("mappings")
        if not isinstance(entries, list) or not entries:
            raise ValueError("runtime resource map must contain a non-empty mappings list")
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"runtime resource map mappings[{index}] must be an object")
            service_id = entry.get("serviceId") or entry.get("service_id")
            prefixes = entry.get("addressPrefixes") or entry.get("address_prefixes")
            if not isinstance(service_id, str) or not service_id.strip():
                raise ValueError(f"runtime resource map mappings[{index}].serviceId must be a non-empty string")
            if not isinstance(prefixes, list) or not prefixes:
                raise ValueError(f"runtime resource map mappings[{index}].addressPrefixes must be a non-empty list")
            for prefix in prefixes:
                if not isinstance(prefix, str) or not prefix.strip():
                    raise ValueError(f"runtime resource map mappings[{index}].addressPrefixes must contain strings")
                mappings.append({"service_id": service_id, "address_prefix": prefix})
        return mappings

    for module in iac_registry.get("modules", []):
        if not isinstance(module, dict):
            continue
        module_id = module.get("moduleId")
        service_ids = module.get("serviceIds")
        if not isinstance(module_id, str) or not isinstance(service_ids, list):
            continue
        prefixes = {
            f"module.{module_id}",
            f"module.{module_id.replace('-', '_')}",
        }
        for service_id in service_ids:
            if not isinstance(service_id, str):
                continue
            for prefix in prefixes | {f"module.{service_id}", service_id}:
                mappings.append({"service_id": service_id, "address_prefix": prefix})
    return mappings


def normalize_plan_resource_changes(
    plan_json: dict[str, Any],
    mappings: list[dict[str, str]],
    required_services: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    changes = plan_json.get("resource_changes")
    if not isinstance(changes, list):
        raise ValueError("plan_json.resource_changes must be a list")
    services_seen: set[str] = set()
    change_count = 0
    destructive_count = 0
    replacement_count = 0
    action_by_service: dict[str, set[str]] = {service_id: set() for service_id in required_services}
    module_by_service: dict[str, str] = {}
    for index, change in enumerate(changes):
        if not isinstance(change, dict):
            raise ValueError(f"plan_json.resource_changes[{index}] must be an object")
        address = change.get("address")
        actions = ((change.get("change") or {}).get("actions") if isinstance(change.get("change"), dict) else None)
        if not isinstance(address, str):
            raise ValueError(f"plan_json.resource_changes[{index}].address must be a string")
        if not isinstance(actions, list) or not all(isinstance(action, str) for action in actions):
            raise ValueError(f"plan_json.resource_changes[{index}].change.actions must be a string list")
        service_id = service_for_address(address, mappings)
        if service_id is None and change.get("mode") != "data":
            raise ValueError(f"plan_json.resource_changes[{index}].address is not mapped to a runtime service: {address}")
        if service_id in required_services:
            services_seen.add(service_id)
            module_by_service[service_id] = module_from_address(address)
            action_by_service[service_id].update(actions)
        if actions != ["no-op"]:
            change_count += 1
        if "delete" in actions:
            destructive_count += 1
        if "delete" in actions and "create" in actions:
            replacement_count += 1
    matrix = [
        {
            "service_id": service_id,
            "module_id": module_by_service.get(service_id, service_id.replace("_", "-")),
            "covered": service_id in services_seen,
            "action": ",".join(sorted(action_by_service[service_id])) if action_by_service[service_id] else "missing",
        }
        for service_id in required_services
    ]
    summary = {
        "format_version": plan_json.get("format_version"),
        "terraform_version": plan_json.get("terraform_version"),
        "change_count": change_count,
        "destructive_change_count": destructive_count,
        "replacement_count": replacement_count,
    }
    return matrix, summary


def normalize_drift(
    plan_json: dict[str, Any],
    mappings: list[dict[str, str]],
    required_services: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    drift_items = plan_json.get("resource_drift", [])
    if drift_items is None:
        drift_items = []
    if not isinstance(drift_items, list):
        raise ValueError("plan_json.resource_drift must be a list when present")
    drifted_services: set[str] = set()
    for index, item in enumerate(drift_items):
        if not isinstance(item, dict):
            raise ValueError(f"plan_json.resource_drift[{index}] must be an object")
        address = item.get("address")
        actions = ((item.get("change") or {}).get("actions") if isinstance(item.get("change"), dict) else [])
        if not isinstance(address, str):
            raise ValueError(f"plan_json.resource_drift[{index}].address must be a string")
        if actions == ["no-op"]:
            continue
        service_id = service_for_address(address, mappings)
        if service_id is None and item.get("mode") != "data":
            raise ValueError(f"plan_json.resource_drift[{index}].address is not mapped to a runtime service: {address}")
        if service_id in required_services:
            drifted_services.add(service_id)
    matrix = [
        {
            "service_id": service_id,
            "module_id": service_id.replace("_", "-"),
            "covered": True,
            "drifted": service_id in drifted_services,
        }
        for service_id in required_services
    ]
    summary = {
        "status": "clean" if not drifted_services else "drifted",
        "drifted_resource_count": len(drifted_services),
        "drifted_services": sorted(drifted_services),
    }
    return matrix, summary


def services_from_state(state_json: dict[str, Any], mappings: list[dict[str, str]]) -> set[str]:
    values = state_json.get("values")
    if not isinstance(values, dict):
        raise ValueError("state_json.values must be an object")
    root_module = values.get("root_module")
    if not isinstance(root_module, dict):
        raise ValueError("state_json.values.root_module must be an object")
    services: set[str] = set()
    for address in iter_state_resource_addresses(root_module):
        service_id = service_for_address(address, mappings)
        if service_id is None:
            raise ValueError(f"state_json resource address is not mapped to a runtime service: {address}")
        if service_id:
            services.add(service_id)
    return services


def iter_state_resource_addresses(module: dict[str, Any]) -> list[str]:
    addresses: list[str] = []
    resources = module.get("resources", [])
    if isinstance(resources, list):
        for resource in resources:
            if isinstance(resource, dict) and isinstance(resource.get("address"), str):
                addresses.append(resource["address"])
    child_modules = module.get("child_modules", [])
    if isinstance(child_modules, list):
        for child in child_modules:
            if isinstance(child, dict):
                addresses.extend(iter_state_resource_addresses(child))
    return addresses


def service_for_address(address: str, mappings: list[dict[str, str]]) -> str | None:
    matches = [
        mapping
        for mapping in mappings
        if address == mapping["address_prefix"] or address.startswith(f"{mapping['address_prefix']}.")
    ]
    if not matches:
        return None
    best = max(matches, key=lambda item: len(item["address_prefix"]))
    return best["service_id"]


def module_from_address(address: str) -> str:
    parts = address.split(".")
    if parts and parts[0] == "module" and len(parts) > 1:
        return parts[1].replace("_", "-")
    return parts[0].replace("_", "-")


def write_runtime_readiness_report(
    root: str | Path,
    output_path: str | Path,
    *,
    environment: str,
    iac_plan_path: str | Path | None = None,
    iac_apply_path: str | Path | None = None,
    drift_report_path: str | Path | None = None,
    backup_report_path: str | Path | None = None,
    dr_report_path: str | Path | None = None,
    health_report_path: str | Path | None = None,
    generated_at: str | None = None,
) -> RuntimeReadinessReportResult:
    platform_root = Path(root)
    report = build_runtime_readiness_report(
        platform_root,
        environment=environment,
        iac_plan_path=iac_plan_path,
        iac_apply_path=iac_apply_path,
        drift_report_path=drift_report_path,
        backup_report_path=backup_report_path,
        dr_report_path=dr_report_path,
        health_report_path=health_report_path,
        generated_at=generated_at,
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"{canonical_json(report)}\n", encoding="utf-8")
    return RuntimeReadinessReportResult(output_path=target, report=report)


def build_runtime_readiness_report(
    root: Path,
    *,
    environment: str,
    iac_plan_path: str | Path | None = None,
    iac_apply_path: str | Path | None = None,
    drift_report_path: str | Path | None = None,
    backup_report_path: str | Path | None = None,
    dr_report_path: str | Path | None = None,
    health_report_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated = generated_at or utc_now()
    validation = validate_runtime_topology(root)
    topology_path = root / "platform" / "runtime" / "topology.yaml"
    iac_path = root / "platform" / "runtime" / "iac-modules.yaml"
    topology = load_yaml(topology_path) if topology_path.is_file() else {}
    iac_registry = load_yaml(iac_path) if iac_path.is_file() else {}
    env_entry = find_by_key(topology.get("environments", []), "environment", environment)
    profile = find_by_key(iac_registry.get("profiles", []), "profileId", env_entry.get("iacProfile") if env_entry else None)
    manifest_path = root / str(env_entry.get("manifest")) if env_entry and env_entry.get("manifest") else None
    env_manifest = load_yaml(manifest_path) if manifest_path and manifest_path.is_file() else {}
    required_p0_services = sorted(REQUIRED_P0_SERVICES)
    stateful_p0_services = sorted(
        str(service.get("serviceId"))
        for service in topology.get("runtimeServices", [])
        if (
            isinstance(service, dict)
            and service.get("serviceId") in REQUIRED_P0_SERVICES
            and service.get("stateful") is True
        )
    )
    evidence_inputs = load_runtime_evidence_inputs(
        root,
        environment=environment,
        profile_id=profile.get("profileId") if profile else None,
        as_of=generated,
        paths={
            "iac_plan": iac_plan_path,
            "iac_apply": iac_apply_path,
            "drift_report": drift_report_path,
            "backup_report": backup_report_path,
            "dr_report": dr_report_path,
            "health_report": health_report_path,
        },
    )
    service_matrix = build_service_matrix(required_p0_services, stateful_p0_services, evidence_inputs)
    gates = runtime_readiness_gates(
        validation,
        environment,
        env_manifest,
        env_entry,
        profile,
        evidence_inputs,
        service_matrix,
    )
    failures = list(validation.errors)
    failures.extend(gate["message"] for gate in gates if gate["status"] == "failed")
    passed = not failures
    report = {
        "artifact_type": "runtime_readiness_report.v1",
        "report_version": REPORT_VERSION,
        "report_id": stable_id("runtime-readiness", topology_path, environment, generated),
        "generated_at": generated,
        "environment": environment,
        "readiness_state": readiness_state(environment, passed),
        "passed": passed,
        "topology_uri": topology_path.as_posix(),
        "topology_hash": hash_file(topology_path) if topology_path.is_file() else None,
        "iac_registry_uri": iac_path.as_posix(),
        "iac_registry_hash": hash_file(iac_path) if iac_path.is_file() else None,
        "environment_manifest_uri": manifest_path.as_posix() if manifest_path else None,
        "environment_manifest_hash": hash_file(manifest_path) if manifest_path and manifest_path.is_file() else None,
        "runtime_readiness": env_manifest.get("runtimeReadiness"),
        "evidence_mode": env_manifest.get("evidenceMode"),
        "iac_profile": profile or {},
        "inputs": evidence_inputs,
        "summary": {
            "topology_service_count": len(topology.get("runtimeServices", []) if isinstance(topology.get("runtimeServices"), list) else []),
            "required_p0_service_count": len(REQUIRED_P0_SERVICES),
            "stateful_p0_service_count": len(stateful_p0_services),
            "deployed_service_count": len([item for item in service_matrix if item["apply_covered"]]),
            "healthy_service_count": len([item for item in service_matrix if item["health_passed"]]),
            "validation_error_count": len(validation.errors),
            "failed_gate_count": len([gate for gate in gates if gate["status"] == "failed"]),
        },
        "service_matrix": service_matrix,
        "gates": gates,
        "blockers": [
            {
                "gate_id": gate["gate_id"],
                "message": gate["message"],
            }
            for gate in gates
            if gate["status"] == "failed"
        ],
        "failures": failures,
        "warnings": validation.warnings,
    }
    return report


def runtime_readiness_gates(
    validation: ValidationResult,
    environment: str,
    env_manifest: dict[str, Any],
    env_entry: dict[str, Any] | None,
    profile: dict[str, Any] | None,
    evidence_inputs: dict[str, dict[str, Any]],
    service_matrix: list[dict[str, Any]],
) -> list[dict[str, str]]:
    gates: list[dict[str, str]] = []
    gates.append(gate("runtime_topology_validated", not validation.errors, "Runtime topology and IaC registry validate as code."))
    gates.append(gate("environment_binding_declared", bool(env_entry), f"{environment} topology binding exists."))
    gates.append(gate("iac_profile_declared", bool(profile), f"{environment} IaC profile exists."))
    if profile:
        gates.append(gate("iac_profile_path_exists", bool(profile.get("path")), "IaC profile path is declared."))
    controls = env_manifest.get("controls") if isinstance(env_manifest.get("controls"), dict) else {}
    gates.append(gate("service_identity_declared", bool(controls.get("serviceIdentity")), "Service identity control is declared."))
    gates.append(gate("secrets_control_declared", bool(controls.get("secrets")), "Secrets control is declared."))
    if environment == "local":
        gates.append(gate("local_preflight_allowed", env_manifest.get("runtimeReadiness") == "local_preflight_only", "Local readiness is developer preflight only."))
        gates.append(gate("synthetic_data_only", env_manifest.get("evidenceMode") == "developer_feedback", "Local evidence cannot be used for production signoff."))
    else:
        plan = evidence_inputs["iac_plan"]
        apply = evidence_inputs["iac_apply"]
        drift = evidence_inputs["drift_report"]
        backup = evidence_inputs["backup_report"]
        health = evidence_inputs["health_report"]
        dr = evidence_inputs["dr_report"]
        gates.append(evidence_gate(plan, "iac_plan_evidence_valid", "Production-like environments require valid IaC plan evidence."))
        gates.append(evidence_gate(apply, "iac_apply_evidence_valid", "Production-like environments require valid IaC apply evidence."))
        gates.append(evidence_gate(drift, "drift_report_valid", "Production-like environments require valid drift evidence."))
        gates.append(evidence_gate(backup, "backup_report_valid", "Production-like environments require valid backup evidence."))
        gates.append(evidence_gate(health, "service_health_report_valid", "Production-like environments require valid service health evidence."))
        gates.append(gate("runtime_iac_deployed", apply["passed"] and apply_status(apply) == "succeeded", "Production-like environments require reviewed IaC apply evidence."))
        gates.append(gate("iac_plan_succeeded", plan["passed"] and nested_value(plan.get("payload"), "plan", "status") == "succeeded", "IaC plan evidence must have status succeeded."))
        gates.append(gate("iac_apply_succeeded", apply["passed"] and apply_status(apply) == "succeeded", "IaC apply evidence must have status succeeded."))
        gates.append(gate("drift_clean", drift["passed"] and drift_status(drift) == "clean", "Runtime drift report must be clean."))
        gates.append(gate("required_service_plan_coverage", all(item["plan_covered"] for item in service_matrix), "IaC plan evidence must cover every required P0 runtime service."))
        gates.append(gate("required_service_apply_coverage", all(item["apply_covered"] for item in service_matrix), "IaC apply evidence must deploy every required P0 runtime service."))
        gates.append(gate("service_health_passed", all(item["health_passed"] for item in service_matrix), "Service health evidence must pass for every required P0 runtime service."))
        gates.append(gate("stateful_backup_evidence_passed", all(item["backup_passed"] for item in service_matrix if item["backup_required"]), "Backup evidence must pass for every stateful required P0 runtime service."))
        gates.append(gate("secrets_externalized", controls.get("secrets") == "external_secret_manager_required", "Production-like environments require external secret manager controls."))
        gates.append(gate("storage_encryption_required", controls.get("storageEncryption") == "required", "Production-like environments require storage encryption."))
        gates.append(gate("private_network_required", controls.get("networkExposure") == "private_network", "Production-like environments require private network exposure."))
        if environment == "prod":
            gates.append(gate("no_destructive_prod_plan", plan["passed"] and destructive_change_count(plan) == 0, "Production IaC plan must not contain destructive changes without separate change-control evidence."))
        if environment == "prod":
            gates.append(evidence_gate(dr, "dr_report_valid", "Production requires valid DR exercise evidence before runtime signoff."))
            gates.append(gate("dr_test_passed", dr["passed"] and dr_status(dr) == "passed", "Production requires DR exercise evidence before runtime signoff."))
            gates.append(gate("dr_service_coverage", dr["passed"] and dr_services_cover_required(dr, [item["service_id"] for item in service_matrix]), "DR exercise evidence must cover every required P0 runtime service."))
    return gates


def load_runtime_evidence_inputs(
    root: Path,
    *,
    environment: str,
    profile_id: str | None,
    as_of: str,
    paths: dict[str, str | Path | None],
) -> dict[str, dict[str, Any]]:
    return {
        kind: load_runtime_evidence(
            root,
            kind=kind,
            path_value=path_value,
            environment=environment,
            profile_id=profile_id,
            as_of=as_of,
        )
        for kind, path_value in paths.items()
    }


def load_runtime_evidence(
    root: Path,
    *,
    kind: str,
    path_value: str | Path | None,
    environment: str,
    profile_id: str | None,
    as_of: str,
) -> dict[str, Any]:
    expected_type = EVIDENCE_ARTIFACT_TYPES[kind]
    entry: dict[str, Any] = {
        "kind": kind,
        "artifact_type": expected_type,
        "path": None,
        "hash": None,
        "provided": False,
        "passed": False,
        "errors": [],
        "payload": {},
    }
    if path_value is None:
        return entry
    path = resolve_input_path(root, path_value)
    entry["path"] = path.as_posix()
    if not path.is_file():
        entry["errors"].append(f"{kind} evidence file does not exist: {path}")
        return entry
    entry["provided"] = True
    entry["hash"] = hash_file(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        entry["errors"].append(f"{kind} evidence is not valid JSON: {exc.msg}")
        return entry
    if not isinstance(payload, dict):
        entry["errors"].append(f"{kind} evidence must be a JSON object")
        return entry
    entry["payload"] = payload
    if payload.get("artifact_type") != expected_type:
        entry["errors"].append(f"{kind} artifact_type must be {expected_type!r}")
    validate_common_evidence_fields(kind, payload, entry["errors"], as_of)
    if payload.get("environment") != environment:
        entry["errors"].append(f"{kind} environment must be {environment!r}")
    if profile_id and payload.get("profile_id") != profile_id:
        entry["errors"].append(f"{kind} profile_id must be {profile_id!r}")
    if not isinstance(payload.get("evidence_id"), str) or not payload.get("evidence_id", "").strip():
        entry["errors"].append(f"{kind} evidence_id must be a non-empty string")
    if not isinstance(payload.get("generated_at"), str) or not payload.get("generated_at", "").strip():
        entry["errors"].append(f"{kind} generated_at must be a non-empty string")
    validate_evidence_specifics(kind, payload, entry["errors"])
    entry["passed"] = not entry["errors"]
    return entry


def validate_common_evidence_fields(kind: str, payload: dict[str, Any], errors: list[str], as_of: str) -> None:
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, int) or schema_version < 1:
        errors.append(f"{kind} schema_version must be an integer >= 1")
    evidence_kind = payload.get("evidence_kind")
    if evidence_kind != EVIDENCE_KINDS[kind]:
        errors.append(f"{kind} evidence_kind must be {EVIDENCE_KINDS[kind]!r}")
    status = payload.get("status")
    if status not in VALID_EVIDENCE_STATUSES:
        errors.append(f"{kind} status must be one of {sorted(VALID_EVIDENCE_STATUSES)}")
    elif status != "passed":
        errors.append(f"{kind} status must be passed for runtime readiness")
    for key in ("valid_until", "git_sha", "artifact_uri", "artifact_sha256"):
        require_payload_string(payload, key, kind, errors)
    source_kind = payload.get("source_kind")
    if source_kind not in VALID_EVIDENCE_SOURCE_KINDS:
        errors.append(f"{kind} source_kind must be one of {sorted(VALID_EVIDENCE_SOURCE_KINDS)}")
    if payload.get("environment") in {"staging", "prod"} and source_kind == "synthetic_fixture":
        errors.append(f"{kind} synthetic_fixture evidence cannot be used for production-like runtime readiness")
    if payload.get("environment") in {"staging", "prod"}:
        validate_production_like_iac_source(kind, payload, errors)
    if payload.get("environment") == "prod":
        require_payload_string(payload, "change_request_id", kind, errors)
    require_payload_string(payload, "command", kind, errors)
    exit_code = payload.get("exit_code")
    if not isinstance(exit_code, int):
        errors.append(f"{kind}.exit_code must be an integer")
    elif exit_code != 0:
        errors.append(f"{kind}.exit_code must be 0 for runtime readiness")
    if payload.get("redacted") is not True:
        errors.append(f"{kind}.redacted must be true")
    issuer = payload.get("issuer")
    if not isinstance(issuer, dict):
        errors.append(f"{kind}.issuer must be an object")
    else:
        for key in ("tool", "tool_version", "ci_run_id"):
            require_payload_string(issuer, key, f"{kind}.issuer", errors)
    valid_until = payload.get("valid_until")
    if isinstance(valid_until, str) and valid_until.strip() and evidence_expired(valid_until, as_of):
        errors.append(f"{kind} valid_until has expired")


def validate_production_like_iac_source(kind: str, payload: dict[str, Any], errors: list[str]) -> None:
    if payload.get("command") != "enterprise-dp runtime-evidence-normalize-iac":
        errors.append(f"{kind} production-like readiness requires evidence from enterprise-dp runtime-evidence-normalize-iac")
    for key in ("source_artifact_uri", "source_artifact_hash"):
        require_payload_string(payload, key, kind, errors)
    source_hash = payload.get("source_artifact_hash")
    if isinstance(source_hash, str) and source_hash.strip() and not SHA256_REFERENCE.fullmatch(source_hash):
        errors.append(f"{kind}.source_artifact_hash must be a sha256:<64 hex> reference")
    artifact_hash = payload.get("artifact_sha256")
    if isinstance(artifact_hash, str) and artifact_hash.strip() and not SHA256_REFERENCE.fullmatch(artifact_hash):
        errors.append(f"{kind}.artifact_sha256 must be a sha256:<64 hex> reference")


def validate_evidence_specifics(kind: str, payload: dict[str, Any], errors: list[str]) -> None:
    if kind == "iac_plan":
        plan = payload.get("plan")
        if not isinstance(plan, dict):
            errors.append("iac_plan plan must be an object")
        else:
            require_payload_string(plan, "status", "iac_plan.plan", errors)
            require_payload_string(plan, "plan_hash", "iac_plan.plan", errors)
            require_payload_int(plan, "destructive_change_count", "iac_plan.plan", errors)
        validate_service_matrix_payload(payload.get("service_matrix"), "iac_plan.service_matrix", errors)
    elif kind == "iac_apply":
        apply = payload.get("apply")
        if not isinstance(apply, dict):
            errors.append("iac_apply apply must be an object")
        else:
            require_payload_string(apply, "status", "iac_apply.apply", errors)
            require_payload_string(apply, "applied_plan_hash", "iac_apply.apply", errors)
            require_payload_string(apply, "state_hash", "iac_apply.apply", errors)
        validate_string_list_payload(payload.get("deployed_services"), "iac_apply.deployed_services", errors)
    elif kind == "drift_report":
        drift = payload.get("drift")
        if not isinstance(drift, dict):
            errors.append("drift_report drift must be an object")
        else:
            require_payload_string(drift, "status", "drift_report.drift", errors)
            require_payload_int(drift, "drifted_resource_count", "drift_report.drift", errors)
        validate_service_matrix_payload(payload.get("service_matrix"), "drift_report.service_matrix", errors, require_covered=False)
    elif kind == "backup_report":
        backups = payload.get("backups")
        if not isinstance(backups, list) or not backups:
            errors.append("backup_report backups must be a non-empty list")
        else:
            for index, backup in enumerate(backups):
                if not isinstance(backup, dict):
                    errors.append(f"backup_report.backups[{index}] must be an object")
                    continue
                require_payload_string(backup, "service_id", f"backup_report.backups[{index}]", errors)
                require_payload_string(backup, "status", f"backup_report.backups[{index}]", errors)
                if not isinstance(backup.get("restore_tested"), bool):
                    errors.append(f"backup_report.backups[{index}].restore_tested must be a boolean")
    elif kind == "dr_report":
        exercise = payload.get("exercise")
        if not isinstance(exercise, dict):
            errors.append("dr_report exercise must be an object")
        else:
            require_payload_string(exercise, "status", "dr_report.exercise", errors)
            require_payload_int(exercise, "rto_minutes", "dr_report.exercise", errors)
            require_payload_int(exercise, "rpo_minutes", "dr_report.exercise", errors)
        validate_string_list_payload(payload.get("covered_services"), "dr_report.covered_services", errors)
    elif kind == "health_report":
        checks = payload.get("checks")
        if not isinstance(checks, list) or not checks:
            errors.append("health_report checks must be a non-empty list")
        else:
            for index, check in enumerate(checks):
                if not isinstance(check, dict):
                    errors.append(f"health_report.checks[{index}] must be an object")
                    continue
                require_payload_string(check, "service_id", f"health_report.checks[{index}]", errors)
                require_payload_string(check, "status", f"health_report.checks[{index}]", errors)


def build_service_matrix(
    required_p0_services: list[str],
    stateful_p0_services: list[str],
    evidence_inputs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    plan_services = service_ids_from_matrix(evidence_inputs["iac_plan"].get("payload", {}).get("service_matrix"))
    apply_services = set(evidence_inputs["iac_apply"].get("payload", {}).get("deployed_services") or [])
    health_services = passed_health_services(evidence_inputs["health_report"].get("payload", {}).get("checks"))
    backup_services = passed_backup_services(evidence_inputs["backup_report"].get("payload", {}).get("backups"))
    stateful = set(stateful_p0_services)
    return [
        {
            "service_id": service_id,
            "backup_required": service_id in stateful,
            "plan_covered": service_id in plan_services,
            "apply_covered": service_id in apply_services,
            "health_passed": service_id in health_services,
            "backup_passed": service_id not in stateful or service_id in backup_services,
        }
        for service_id in required_p0_services
    ]


def service_ids_from_matrix(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        str(item.get("service_id"))
        for item in value
        if isinstance(item, dict) and item.get("covered") is True and isinstance(item.get("service_id"), str)
    }


def passed_health_services(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        str(item.get("service_id"))
        for item in value
        if isinstance(item, dict) and item.get("status") == "passed" and isinstance(item.get("service_id"), str)
    }


def passed_backup_services(value: object) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {
        str(item.get("service_id"))
        for item in value
        if (
            isinstance(item, dict)
            and item.get("status") == "passed"
            and item.get("restore_tested") is True
            and isinstance(item.get("service_id"), str)
        )
    }


def evidence_gate(evidence: dict[str, Any], gate_id: str, fallback_message: str) -> dict[str, str]:
    if evidence["passed"]:
        return gate(gate_id, True, fallback_message)
    errors = evidence.get("errors") or [fallback_message]
    return gate(gate_id, False, "; ".join(str(error) for error in errors))


def apply_status(evidence: dict[str, Any]) -> str | None:
    return nested_value(evidence.get("payload"), "apply", "status")


def drift_status(evidence: dict[str, Any]) -> str | None:
    return nested_value(evidence.get("payload"), "drift", "status")


def dr_status(evidence: dict[str, Any]) -> str | None:
    return nested_value(evidence.get("payload"), "exercise", "status")


def destructive_change_count(evidence: dict[str, Any]) -> int | None:
    value = nested_value(evidence.get("payload"), "plan", "destructive_change_count")
    return value if isinstance(value, int) else None


def dr_services_cover_required(evidence: dict[str, Any], required_services: list[str]) -> bool:
    covered = set(evidence.get("payload", {}).get("covered_services") or [])
    return set(required_services).issubset(covered)


def nested_value(value: object, first_key: str, second_key: str) -> Any:
    if not isinstance(value, dict):
        return None
    nested = value.get(first_key)
    if not isinstance(nested, dict):
        return None
    return nested.get(second_key)


def require_payload_string(mapping: dict[str, Any], key: str, prefix: str, errors: list[str]) -> None:
    if not isinstance(mapping.get(key), str) or not mapping.get(key, "").strip():
        errors.append(f"{prefix}.{key} must be a non-empty string")


def require_payload_int(mapping: dict[str, Any], key: str, prefix: str, errors: list[str]) -> None:
    value = mapping.get(key)
    if not isinstance(value, int) or value < 0:
        errors.append(f"{prefix}.{key} must be a non-negative integer")


def validate_string_list_payload(value: object, prefix: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix} must be a non-empty list")
        return
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{prefix}[{index}] must be a non-empty string")


def validate_service_matrix_payload(
    value: object,
    prefix: str,
    errors: list[str],
    *,
    require_covered: bool = True,
) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix} must be a non-empty list")
        return
    for index, item in enumerate(value):
        item_prefix = f"{prefix}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be an object")
            continue
        require_payload_string(item, "service_id", item_prefix, errors)
        require_payload_string(item, "module_id", item_prefix, errors)
        if require_covered and not isinstance(item.get("covered"), bool):
            errors.append(f"{item_prefix}.covered must be a boolean")


def resolve_input_path(root: Path, path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return root / path


def evidence_expired(valid_until: str, as_of: str) -> bool:
    valid_until_time = parse_utc_time(valid_until)
    as_of_time = parse_utc_time(as_of)
    if valid_until_time is None or as_of_time is None:
        return False
    return valid_until_time < as_of_time


def parse_utc_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def gate(gate_id: str, passed: bool, message: str) -> dict[str, str]:
    return {
        "gate_id": gate_id,
        "status": "passed" if passed else "failed",
        "message": message,
    }


def readiness_state(environment: str, passed: bool) -> str:
    if passed and environment == "local":
        return "local_preflight_ready"
    if passed:
        return "production_like_ready"
    if environment == "local":
        return "local_preflight_not_ready"
    return "production_like_not_ready"


def find_by_key(items: object, key: str, value: object) -> dict[str, Any] | None:
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get(key) == value:
            return item
    return None


def canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, *parts: object) -> str:
    payload = "|".join(str(part) for part in parts)
    return f"{prefix}-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
