from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from enterprise_df.environments import validate_environment_manifests, validate_environment_manifest
from enterprise_df.contracts import ValidationResult


ROOT = Path(__file__).resolve().parents[1]


def test_repository_environment_manifests_are_valid() -> None:
    result = validate_environment_manifests(ROOT)

    assert result.errors == []
    assert result.checked_count == 3


def test_environment_manifest_requires_all_p0_runtime_services() -> None:
    path = ROOT / "platform" / "environments" / "local" / "manifest.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["runtimeServices"] = [
        service
        for service in manifest["runtimeServices"]
        if service["serviceId"] != "schema_registry"
    ]
    result = ValidationResult()

    validate_environment_manifest(path, manifest, "local", result)

    assert any("missing required P0 services: schema_registry" in error for error in result.errors)


def test_environment_manifest_rejects_prod_with_local_evidence_or_secret_controls() -> None:
    path = ROOT / "platform" / "environments" / "prod" / "manifest.yaml"
    manifest = deepcopy(yaml.safe_load(path.read_text(encoding="utf-8")))
    manifest["evidenceMode"] = "developer_feedback"
    manifest["controls"]["secrets"] = "generated_test_values"
    result = ValidationResult()

    validate_environment_manifest(path, manifest, "prod", result)

    assert any("evidenceMode must be 'production_signoff'" in error for error in result.errors)
    assert any("staging/prod controls.secrets must not use generated test values" in error for error in result.errors)


def test_environment_manifest_requires_p0_services_to_be_required() -> None:
    path = ROOT / "platform" / "environments" / "staging" / "manifest.yaml"
    manifest = deepcopy(yaml.safe_load(path.read_text(encoding="utf-8")))
    for service in manifest["runtimeServices"]:
        if service["serviceId"] == "lakehouse_sql":
            service["required"] = False
            service["phase"] = "P1"
    result = ValidationResult()

    validate_environment_manifest(path, manifest, "staging", result)

    assert any("required must be true for P0 runtime service lakehouse_sql" in error for error in result.errors)
    assert any("phase must start with P0 for required runtime service lakehouse_sql" in error for error in result.errors)
