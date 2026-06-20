from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_dp.contracts import (
    ValidationResult,
    load_yaml,
    require_bool,
    require_int,
    require_mapping,
    require_string,
    require_string_list,
)


VALID_PROFILE_STATUSES = {"draft", "active", "deprecated"}


def validate_release_profile_registry(root: Path) -> ValidationResult:
    result = ValidationResult()
    registry_path = release_profile_registry_path(root)
    if not registry_path.is_file():
        result.error(registry_path, "platform/observability/release-evidence-profiles.yaml is required")
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
        validate_release_profile(registry_path, profile, index, seen_ids, result)
    return result


def validate_release_profile(
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
        if ".v" not in profile_id:
            result.error(registry_path, f"{prefix}.id must include a version suffix like .v1")
        if profile_id in seen_ids:
            result.error(registry_path, f"{prefix}.id duplicates profile {profile_id}")
        seen_ids.add(profile_id)
    for key in ("name", "owner", "description"):
        require_string(registry_path, result, profile, key, prefix)
    status = require_string(registry_path, result, profile, "status", prefix)
    if status and status not in VALID_PROFILE_STATUSES:
        result.error(registry_path, f"{prefix}.status must be one of {sorted(VALID_PROFILE_STATUSES)}")

    applies_to = require_mapping(registry_path, result, profile, "appliesTo")
    if applies_to:
        require_string_list(registry_path, result, applies_to, "useCases", f"{prefix}.appliesTo")
        require_string_list(registry_path, result, applies_to, "runnerInputKinds", f"{prefix}.appliesTo")

    require_string_list(registry_path, result, profile, "requiredGates", prefix)
    require_string_list(registry_path, result, profile, "requiredArtifacts", prefix)

    production = require_mapping(registry_path, result, profile, "productionEvidenceRequirements")
    if production:
        for key in (
            "codeCommitSha",
            "schemaRegistryReportUri",
            "schemaRegistryReportHash",
            "validatorOutputUri",
            "accessPolicyCheckId",
            "accessPolicyReportUri",
            "accessPolicyReportHash",
            "accessGrantEvidenceUri",
            "accessGrantEvidenceHash",
            "retentionEvidenceUri",
            "retentionEvidenceHash",
            "snapshotEvidenceUri",
            "snapshotEvidenceHash",
            "approver",
        ):
            require_bool(registry_path, result, production, key, f"{prefix}.productionEvidenceRequirements")

    local = require_mapping(registry_path, result, profile, "localEvidenceRequirements")
    if local:
        require_bool(registry_path, result, local, "schemaRegistryReportUri", f"{prefix}.localEvidenceRequirements")
        require_bool(registry_path, result, local, "accessPolicyReportUri", f"{prefix}.localEvidenceRequirements")
        require_bool(registry_path, result, local, "accessGrantEvidenceUri", f"{prefix}.localEvidenceRequirements")
        require_bool(registry_path, result, local, "retentionEvidenceUri", f"{prefix}.localEvidenceRequirements")


def evaluate_release_profile(
    root: Path,
    *,
    profile_id: str | None,
    use_case_id: str,
    runner_input_kind: str | None,
    environment: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    if not profile_id:
        return {
            "profile_id": None,
            "passed": False,
            "checks": [
                check("profile_declared", False, {"reason": "release_evidence_profile_missing"}),
            ],
        }
    profile = get_release_profile(root, profile_id)
    applies_to = profile.get("appliesTo", {})
    gates_by_id = {
        gate.get("gate_id"): gate
        for gate in evidence.get("gates", [])
        if isinstance(gate, dict)
    }
    required_gates = [
        gate_id for gate_id in profile.get("requiredGates", [])
        if isinstance(gate_id, str) and gate_id != "P0-RELEASE-EVIDENCE-PROFILE"
    ]
    artifacts = evidence.get("artifacts", {})
    checks = [
        check("profile_declared", True, {}),
        check("profile_active", profile.get("status") == "active", {"status": profile.get("status")}),
        check("use_case_allowed", use_case_id in applies_to.get("useCases", []), {"use_case_id": use_case_id}),
        check(
            "runner_input_kind_allowed",
            runner_input_kind in applies_to.get("runnerInputKinds", []),
            {"runner_input_kind": runner_input_kind},
        ),
        check(
            "required_gates_passed",
            all(gates_by_id.get(gate_id, {}).get("passed") is True for gate_id in required_gates),
            {
                "required_gates": required_gates,
                "gate_results": {
                    gate_id: gates_by_id.get(gate_id, {}).get("passed")
                    for gate_id in required_gates
                },
            },
        ),
        check(
            "required_artifacts_present",
            required_artifacts_present(profile.get("requiredArtifacts", []), evidence, artifacts),
            {
                "required_artifacts": profile.get("requiredArtifacts", []),
                "artifact_keys": sorted(str(key) for key in artifacts.keys()),
            },
        ),
    ]
    checks.extend(evidence_requirement_checks(profile, evidence, environment))
    return {
        "profile_id": profile_id,
        "profile_hash": hash_release_profile_registry(root),
        "owner": profile.get("owner"),
        "status": profile.get("status"),
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }


def evidence_requirement_checks(
    profile: dict[str, Any],
    evidence: dict[str, Any],
    environment: str,
) -> list[dict[str, Any]]:
    is_production_like = environment not in {"local", "dev"}
    requirements = (
        profile.get("productionEvidenceRequirements", {})
        if is_production_like
        else profile.get("localEvidenceRequirements", {})
    )
    field_map = {
        "codeCommitSha": "code_commit_sha",
        "schemaRegistryReportUri": "schema_registry_report_uri",
        "schemaRegistryReportHash": "schema_registry_report_hash",
        "validatorOutputUri": "validator_output_uri",
        "accessPolicyCheckId": "access_policy_check_id",
        "accessPolicyReportUri": "access_policy_report_uri",
        "accessPolicyReportHash": "access_policy_report_hash",
        "accessGrantEvidenceUri": "access_grant_evidence_uri",
        "accessGrantEvidenceHash": "access_grant_evidence_hash",
        "retentionEvidenceUri": "retention_evidence_uri",
        "retentionEvidenceHash": "retention_evidence_hash",
        "snapshotEvidenceUri": "snapshot_evidence_uri",
        "snapshotEvidenceHash": "snapshot_evidence_hash",
        "approver": "approver",
    }
    checks = []
    for requirement_key, evidence_key in field_map.items():
        if requirements.get(requirement_key) is True:
            checks.append(
                check(
                    f"evidence_{evidence_key}",
                    bool(evidence.get(evidence_key)),
                    {"environment": environment, "required": True},
                )
            )
    return checks


def required_artifacts_present(
    required_artifacts: object,
    evidence: dict[str, Any],
    artifacts: object,
) -> bool:
    if not isinstance(required_artifacts, list):
        return False
    artifact_mapping = artifacts if isinstance(artifacts, dict) else {}
    for key in required_artifacts:
        if not isinstance(key, str):
            return False
        if key in artifact_mapping:
            if not artifact_mapping.get(key):
                return False
            continue
        if key in evidence:
            if not evidence.get(key):
                return False
            continue
        return False
    return True


def check(name: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "details": details,
    }


def release_profile_registry_path(root: Path) -> Path:
    return root / "platform" / "observability" / "release-evidence-profiles.yaml"


def load_release_profile_registry(root: Path) -> dict[str, Any]:
    path = release_profile_registry_path(root)
    if not path.is_file():
        return {}
    return load_yaml(path)


def list_release_profiles(root: Path) -> list[dict[str, Any]]:
    registry = load_release_profile_registry(root)
    profiles = registry.get("profiles")
    return [profile for profile in profiles if isinstance(profile, dict)] if isinstance(profiles, list) else []


def get_release_profile(root: Path, profile_id: str) -> dict[str, Any]:
    for profile in list_release_profiles(root):
        if profile.get("id") == profile_id:
            return profile
    raise KeyError(f"release evidence profile is not registered: {profile_id}")


def load_release_profile_ids(root: Path) -> set[str]:
    return {
        profile["id"]
        for profile in list_release_profiles(root)
        if isinstance(profile.get("id"), str)
    }


def hash_release_profile_registry(root: Path) -> str:
    from enterprise_dp.catalog import hash_file

    return hash_file(release_profile_registry_path(root))
