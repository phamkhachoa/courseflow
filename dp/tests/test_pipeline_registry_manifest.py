from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from enterprise_dp.contracts import ValidationResult
from enterprise_dp.pipeline_registry_manifest import (
    validate_pipeline_registry_manifest,
    validate_runner_entry,
    validation_context,
)
from enterprise_dp.pipelines import default_pipeline_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "platform" / "orchestration" / "pipeline-registry.yaml"


def test_repository_pipeline_registry_manifest_is_valid() -> None:
    result = validate_pipeline_registry_manifest(ROOT)
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    expected_runner_count = len(registry["runners"])

    assert result.errors == []
    assert result.checked_count >= expected_runner_count


def test_pipeline_registry_manifest_must_match_implemented_runner_outputs() -> None:
    runner = load_runner("finance.benefit_reconciliation.from_approved_bronze.v1")
    runner["outputDataProducts"] = ["gold.finance_benefit_reconciliation"]
    result = ValidationResult()

    validate_runner_entry(
        ROOT,
        REGISTRY_PATH,
        runner,
        0,
        set(),
        validation_context(ROOT),
        {spec.runner_id: spec for spec in default_pipeline_registry().list_specs()},
        result,
    )

    assert any("outputDataProducts must match implemented runner value" in error for error in result.errors)


def test_pipeline_registry_manifest_rejects_active_runner_without_python_registration() -> None:
    runner = load_runner("finance.benefit_reconciliation.from_approved_bronze.v1")
    runner["runnerId"] = "finance.missing_runner.v1"
    result = ValidationResult()

    validate_runner_entry(
        ROOT,
        REGISTRY_PATH,
        runner,
        0,
        set(),
        validation_context(ROOT),
        {spec.runner_id: spec for spec in default_pipeline_registry().list_specs()},
        result,
    )

    assert any("active but no Python runner is registered" in error for error in result.errors)


def test_pipeline_registry_manifest_rejects_unknown_use_case() -> None:
    runner = load_runner("recommendation.from_approved_bronze.v1")
    runner["useCases"] = ["unknown-use-case"]
    result = ValidationResult()

    validate_runner_entry(
        ROOT,
        REGISTRY_PATH,
        runner,
        0,
        set(),
        validation_context(ROOT),
        {spec.runner_id: spec for spec in default_pipeline_registry().list_specs()},
        result,
    )

    assert any("useCases contains unknown use case" in error for error in result.errors)


def load_runner(runner_id: str) -> dict:
    registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    for runner in registry["runners"]:
        if runner["runnerId"] == runner_id:
            return deepcopy(runner)
    raise AssertionError(f"runner not found: {runner_id}")
