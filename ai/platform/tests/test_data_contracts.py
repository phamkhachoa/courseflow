from __future__ import annotations

from pathlib import Path

import pytest

from courseflow_ai_platform.data_contracts import (
    build_data_contract_coverage_report,
    build_data_contract_coverage_snapshot,
)
from courseflow_ai_platform.registry import RegistryValidationError, load_yaml


def test_data_contract_coverage_maps_blueprint_data_domains() -> None:
    report = build_data_contract_coverage_report(Path(__file__).resolve().parents[2])
    payload = report.to_dict()

    assert payload["contractCount"] == 7
    assert payload["activeContractCount"] == 3
    assert payload["draftContractCount"] == 4
    assert payload["privacyGatedContractCount"] == 0
    assert payload["simulatorGatedContractCount"] == 0
    assert payload["requestCount"] == 6
    assert payload["designReadyRequestCount"] == 6
    assert payload["productionReadyRequestCount"] == 3
    assert payload["missingRequestCount"] == 0
    assert payload["domainCount"] == 16
    assert payload["mappedDomainCount"] == 16
    assert payload["missingDomainCount"] == 0
    assert payload["actionQueue"]["needsProductionHardening"] == [
        "enterprise-knowledge-assistant-discovery",
        "operations-routing-optimization-simulator",
        "finance-payment-fraud-scoring-discovery",
    ]


def test_data_contract_coverage_exposes_gated_enterprise_requests() -> None:
    report = build_data_contract_coverage_report(Path(__file__).resolve().parents[2])
    items = {item.request_id: item for item in report.items}

    assert items["finance-document-intelligence-discovery"].privacy_gated is False
    assert items["finance-document-intelligence-discovery"].production_ready is True
    assert items["operations-routing-optimization-simulator"].simulator_gated is False
    assert items["operations-routing-optimization-simulator"].design_ready is True
    assert items["lms-at-risk-prediction-baseline"].production_ready is True
    assert items["support-sla-risk-discovery"].production_ready is True
    assert items["finance-payment-fraud-scoring-discovery"].design_ready is True
    assert items["finance-payment-fraud-scoring-discovery"].production_ready is False


def test_data_contract_coverage_snapshot_matches_checked_in_report() -> None:
    ai_root = Path(__file__).resolve().parents[2]
    checked_in = load_yaml(
        ai_root
        / "platform"
        / "data-contracts"
        / "reports"
        / "data-contract-coverage-v1.yaml"
    )
    generated = build_data_contract_coverage_snapshot(ai_root, generated_at="2026-06-17")

    assert checked_in["summary"] == generated["summary"]
    assert checked_in["action_queue"] == generated["action_queue"]
    assert checked_in["contracts"] == generated["contracts"]
    assert checked_in["items"] == generated["items"]


def test_data_contract_coverage_rejects_unknown_domain(tmp_path: Path) -> None:
    write_minimal_data_contract_tree(tmp_path)

    report = build_data_contract_coverage_report(tmp_path)
    assert report.missing_domain_count == 1
    assert report.items[0].missing_domains == ("unknown_events",)


def test_data_contract_coverage_rejects_product_mismatch(tmp_path: Path) -> None:
    write_minimal_data_contract_tree(tmp_path, contract_product="other-product")

    with pytest.raises(RegistryValidationError, match="product does not match"):
        build_data_contract_coverage_report(tmp_path)


def write_minimal_data_contract_tree(
    root: Path,
    *,
    contract_product: str = "p1",
) -> None:
    (root / "products").mkdir(parents=True)
    (root / "use-cases").mkdir(parents=True)
    (root / "contracts" / "features").mkdir(parents=True)
    (root / "platform" / "data-contracts").mkdir(parents=True)
    (root / "platform" / "intake").mkdir(parents=True)

    (root / "products" / "registry.yaml").write_text(
        """
version: 1
owner: ai-platform
platform_product: p1
products:
  - id: p1
    name: Product
    type: product
    status: candidate
    owner: product-owner
    ai_use_cases:
      - u1
  - id: other-product
    name: Other Product
    type: product
    status: candidate
    owner: other-owner
""",
        encoding="utf-8",
    )
    (root / "use-cases" / "registry.yaml").write_text(
        """
version: 1
owner: ai-platform
platform_product: p1
use_cases:
  - id: u1
    name: Use Case
    status: proposed
    product: p1
""",
        encoding="utf-8",
    )
    (root / "contracts" / "features" / "known-features.v1.yaml").write_text(
        f"""
version: 1
contract: known_features
owner: ai-platform
producer: p1
consumer: ai-platform
product: {contract_product}
entities:
  tenant:
    key: tenant_id
    pii_class: none
feature_groups:
  known_events:
    freshness: 24h
    features:
      - event_count
    consumers:
      - u1
privacy:
  tenant_isolation_required: true
quality:
  require_not_null_keys: true
""",
        encoding="utf-8",
    )
    (root / "platform" / "data-contracts" / "registry.yaml").write_text(
        """
version: 1
owner: ai-platform
policy:
  allowed_statuses:
    - active
  design_ready_statuses:
    - active
  production_ready_statuses:
    - active
contracts:
  - contract_id: known-features-v1
    name: Known Features
    status: active
    product: p1
    path: contracts/features/known-features.v1.yaml
    use_cases:
      - u1
    data_domains:
      - known_events
    owner_role: Product
""",
        encoding="utf-8",
    )
    (root / "platform" / "intake" / "use-case-requests.yaml").write_text(
        """
version: 1
owner: ai-platform
policy:
  allowed_statuses:
    - ready_for_solution_design
  allowed_priorities:
    - p1
  required_roles:
    - po_ba
    - sa_ai_platform
    - sa_ai_engineer
requests:
  - request_id: r1
    product: p1
    use_case_id: u1
    submitted_at: "2026-06-17"
    submitted_by: product-owner
    business_owner: product-owner
    priority: p1
    status: ready_for_solution_design
    objective: Ship a validated capability.
    target_modules:
      - m1
    requested_capabilities:
      - scoring
    expected_business_kpis:
      - cycle_time
    data_domains:
      - known_events
      - unknown_events
    constraints:
      - human_review
""",
        encoding="utf-8",
    )
