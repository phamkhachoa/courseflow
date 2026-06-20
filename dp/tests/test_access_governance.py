from __future__ import annotations

from pathlib import Path
import shutil

import yaml

from enterprise_dp.access_governance import (
    evaluate_consumer_contract_reference,
    validate_access_persona_registry,
    validate_consumer_contract_registry,
)
from enterprise_dp.contracts import validate_contract_tree
from enterprise_dp.usecases import validate_use_case_registry


ROOT = Path(__file__).resolve().parents[1]


def test_repository_access_governance_registries_are_valid() -> None:
    persona_result = validate_access_persona_registry(ROOT)
    contract_result = validate_consumer_contract_registry(ROOT)

    assert persona_result.errors == []
    assert persona_result.checked_count == 1
    assert contract_result.errors == []
    assert contract_result.checked_count == 1


def test_consumer_contract_evaluator_blocks_persona_outside_contract() -> None:
    contract = yaml.safe_load((ROOT / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml").read_text())
    contract["serving"]["accessPersonas"] = ["UnknownExecutive"]

    evaluation = evaluate_consumer_contract_reference(
        ROOT,
        data_product_name="gold.recsys_interactions",
        layer=contract["dataProduct"]["layer"],
        privacy=contract["privacy"],
        serving=contract["serving"],
    )

    assert evaluation["passed"] is False
    assert any(
        check["name"] == "consumer_contract_allows_personas" and check["passed"] is False
        for check in evaluation["checks"]
    )


def test_contract_tree_rejects_unknown_consumer_contract(tmp_path: Path) -> None:
    copy_minimal_contract_tree(ROOT, tmp_path)
    path = tmp_path / "contracts" / "data-products" / "gold.recsys_interactions.v1.yaml"
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    contract["serving"]["consumerContract"] = "missing_consumer_contract"
    path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    result = validate_contract_tree(tmp_path)

    assert any("serving.consumerContract references unregistered contract" in error for error in result.errors)


def test_use_case_registry_rejects_unknown_access_persona(tmp_path: Path) -> None:
    copy_minimal_use_case_tree(ROOT, tmp_path)
    path = tmp_path / "use-cases" / "registry.yaml"
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    registry["useCases"][0]["accessPersonas"] = ["UnknownPersona"]
    path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")

    result = validate_use_case_registry(tmp_path)

    assert any("accessPersonas references unknown persona" in error for error in result.errors)


def copy_minimal_contract_tree(source_root: Path, target_root: Path) -> None:
    for relative in (
        "contracts/policies/access-personas.yaml",
        "contracts/policies/consumer-contracts.yaml",
        "contracts/policies/access-policies.yaml",
        "contracts/policies/retention-policies.yaml",
        "contracts/data-products/gold.recsys_interactions.v1.yaml",
        "contracts/topics/recommendation.tracking.v1.yaml",
        "contracts/events/recommendation.tracking.v1.schema.json",
        "contracts/event-envelope.v1.schema.json",
    ):
        source = source_root / relative
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def copy_minimal_use_case_tree(source_root: Path, target_root: Path) -> None:
    for directory in ("contracts", "domains", "products", "use-cases"):
        shutil.copytree(source_root / directory, target_root / directory)
